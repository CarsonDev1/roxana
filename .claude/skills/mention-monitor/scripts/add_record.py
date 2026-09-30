"""Add records to the append-only store, or check whether something is already stored.

Usage (--project goes BEFORE the sub-command; default project = folder containing .claude):
  python add_record.py [--project D:\\Roxana] add --run RUN-2026-09-29-01 --json runs/RUN-2026-09-29-01/pending/x.json
  python add_record.py [--project D:\\Roxana] check --url <url> | --text "<snippet>" | --key-of <record.json>

`add` takes one record or an array and prints one result per record:
  {"index", "status": "added", "id", "evidence_paths", "supersedes"?}
  {"index", "status": "duplicate", "existing_id"}
  {"index", "status": "invalid", "errors": [...]}
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import sys
from pathlib import Path

from PIL import Image

from common import (IdAllocator, Project, append_records, dedupe_key, fold, normalize_author_url, normalize_url,
                    now_iso, read_records, setup_stdout, sha256_file, today_str)
from schema import validate

_LONE_SURROGATE = re.compile(r"[\ud800-\udfff]")


def _scrub(value):
    """Drop lone surrogates (they cannot be written as UTF-8 and would abort the whole batch)."""
    if isinstance(value, str):
        return _LONE_SURROGATE.sub("", value)
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    if isinstance(value, dict):
        return {_scrub(k): _scrub(v) for k, v in value.items()}
    return value


def _is_image(path: Path) -> bool:
    try:
        with Image.open(path) as im:
            im.verify()
        return True
    except Exception:  # PIL raises many types for truncated / non-image files
        return False


def _normalize_authors(rec: dict) -> None:
    if isinstance(rec.get("author_url"), str) and rec["author_url"]:
        rec["author_url"] = normalize_author_url(rec["author_url"])
    shared = rec.get("shared_from")
    if isinstance(shared, dict) and isinstance(shared.get("author_url"), str) and shared["author_url"]:
        shared["author_url"] = normalize_author_url(shared["author_url"])


def _key_index(records: list[dict]) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for rec in records:
        key = rec.get("dedupe_key") or dedupe_key(rec)
        if not key:
            continue
        current = index.get(key)
        if current is None or (current.get("origin") == "legacy" and rec.get("origin") != "legacy"):
            index[key] = rec
    return index


def _cscroll_files(records: list[dict]) -> dict[str, set[str]]:
    """source id -> canonical paths of its comment-scroll screenshots (its own evidence and its rechecks')."""
    files: dict[str, set[str]] = {}
    for rec in records:
        if rec.get("record_type") == "source":
            owner = rec.get("id")
        elif rec.get("record_type") == "recheck":
            owner = rec.get("target_id")
        else:
            continue
        for item in rec.get("evidence") or []:
            if item.get("kind") == "cscroll":
                files.setdefault(owner, set()).add(item["file"])
    return files


def _platform_of(rec: dict, by_id: dict[str, dict]) -> str | None:
    if rec.get("platform"):
        return rec["platform"]
    target = by_id.get(rec.get("source_id") or rec.get("target_id") or "")
    return target.get("platform") if target else None


def _resolve_batch_refs(rec: dict, batch_ids: list[str | None]) -> list[str]:
    value = rec.get("parent_comment_id")
    if not (isinstance(value, str) and value.startswith("@")):
        return []
    try:
        j = int(value[1:])
    except ValueError:
        return [f"parent_comment_id={value!r}: tham chiếu @ không hợp lệ"]
    if not 0 <= j < len(batch_ids):
        return [f"parent_comment_id={value!r}: chỉ được trỏ tới bản ghi đứng trước trong cùng mảng"]
    if batch_ids[j] is None:
        return [f"parent_comment_id={value!r}: bản ghi được trỏ tới không hợp lệ nên bản ghi này cũng bị từ chối"]
    rec["parent_comment_id"] = batch_ids[j]
    return []


def _check_references(project: Project, rec: dict, by_id: dict[str, dict],
                      cscroll: dict[str, set[str]]) -> list[str]:
    errors: list[str] = []
    for item in rec.get("evidence") or []:
        if item.get("file") and not project.resolve(item["file"]).is_file():
            errors.append(f"Không tìm thấy file ảnh: {item['file']}")
        elif item.get("file") and not _is_image(project.resolve(item["file"])):
            errors.append(f"File không phải ảnh đọc được (rỗng, hỏng hoặc PDF…): {item['file']} — chụp lại; "
                          "tài liệu PDF thì chụp màn hình trang đang mở")
    if rec.get("snapshot_file") and not project.resolve(rec["snapshot_file"]).is_file():
        errors.append(f"Không tìm thấy file bản chữ: {rec['snapshot_file']}")
    for field in ("container_id", "target_id", "parent_comment_id"):
        ref = rec.get(field)
        if ref and ref not in by_id:
            errors.append(f"{field}={ref} không có trong kho")
    if rec.get("record_type") == "comment":
        sid = rec.get("source_id")
        if sid not in by_id:
            errors.append(f"source_id={sid} không có trong kho")
        else:
            allowed = cscroll.get(sid, set())
            for ref in rec.get("scroll_refs") or []:
                path = (ref.get("file") or "").replace("\\", "/")
                ref["file"] = path
                if path not in allowed:
                    errors.append(f"scroll_refs: {path} không phải ảnh cuộn bình luận của {sid} — "
                                  "dùng đường dẫn trong evidence_paths trả về khi ghi bài")
    sup = rec.get("supersedes")
    if sup:
        target = by_id.get(sup, {})
        if target.get("record_type") != "source" or target.get("origin") != "legacy":
            errors.append(f"supersedes={sup} phải là mã một bài nhập từ file cũ (origin=legacy)")
    return errors


def _import_evidence(project: Project, rec: dict, platform: str, day: str) -> list[dict]:
    dest_dir = project.screenshots_dir(platform, day)
    dest_dir.mkdir(parents=True, exist_ok=True)
    counters: dict[str, int] = {}
    stored = []
    for item in rec.get("evidence") or []:
        kind = item["kind"]
        counters[kind] = counters.get(kind, 0) + 1
        src = project.resolve(item["file"])
        dest = dest_dir / f"{rec['id']}_{kind}_{counters[kind]:02d}{src.suffix.lower() or '.png'}"
        shutil.copy2(src, dest)
        stored.append({**item, "file": project.rel(dest), "sha256": sha256_file(dest),
                       "captured_at": (item.get("captured_at") or rec.get("captured_at")
                                       or rec.get("checked_at") or now_iso()),
                       "capture_tool": item.get("capture_tool", "claude-in-chrome")})
    return stored


def _import_snapshot(project: Project, rec: dict, platform: str, day: str) -> None:
    text = rec.pop("snapshot_text", None)
    source_file = rec.get("snapshot_file")
    if text is None and not source_file:
        return
    dest_dir = project.snapshots_dir(platform, day)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{rec['id']}.txt"
    if text is not None:
        dest.write_text(text, encoding="utf-8")
    else:
        shutil.copy2(project.resolve(source_file), dest)
    rec["snapshot_file"] = project.rel(dest)
    rec["snapshot_sha256"] = sha256_file(dest)


def add_records(project: Project, incoming: list[dict], run_id: str, config: dict) -> list[dict]:
    records, _ = read_records(project.records_path)
    by_id = {r["id"]: r for r in records if r.get("id")}
    index = _key_index(records)
    cscroll = _cscroll_files(records)
    alloc = IdAllocator(records)
    day = today_str()
    results: list[dict] = []
    to_write: list[dict] = []
    batch_ids: list[str | None] = []
    occurrences: dict[str, int] = {}

    for i, raw in enumerate(incoming):
        if not isinstance(raw, dict):
            results.append({"index": i, "status": "invalid", "errors": ["Mỗi phần tử phải là một object JSON {...}"]})
            batch_ids.append(None)
            continue
        rec = _scrub(copy.deepcopy(raw))
        rec.setdefault("origin", "scan")
        rec.setdefault("run_id", run_id)
        errors = _resolve_batch_refs(rec, batch_ids)
        if not errors:
            errors = validate(rec, config)
        if not errors:
            errors = _check_references(project, rec, by_id, cscroll)
        if not errors:
            _normalize_authors(rec)
        if errors:
            results.append({"index": i, "status": "invalid", "errors": errors})
            batch_ids.append(None)
            continue

        key = dedupe_key(rec)
        if key and key.startswith("cmt:"):
            occurrences[key] = occurrences.get(key, 0) + 1
            key = f"{key}#{occurrences[key]}"
        existing = index.get(key) if key else None
        if existing is not None:
            if existing.get("origin") == "legacy" and rec["origin"] == "scan" and rec["record_type"] == "source":
                rec["supersedes"] = existing["id"]
            else:
                results.append({"index": i, "status": "duplicate", "existing_id": existing["id"]})
                batch_ids.append(existing["id"])
                continue

        platform = _platform_of(rec, by_id)
        if rec["record_type"] == "comment":
            rec.setdefault("platform", platform)
        rec["id"] = alloc.next(rec["record_type"], platform)
        rec["recorded_at"] = now_iso()
        if key:
            rec["dedupe_key"] = key
        if rec.get("evidence"):
            rec["evidence"] = _import_evidence(project, rec, platform or "other", day)
        _import_snapshot(project, rec, platform or "other", day)

        by_id[rec["id"]] = rec
        if key:
            index[key] = rec
        for owner, files in _cscroll_files([rec]).items():
            cscroll.setdefault(owner, set()).update(files)
        to_write.append(rec)
        batch_ids.append(rec["id"])
        result = {"index": i, "status": "added", "id": rec["id"],
                  "evidence_paths": [e["file"] for e in rec.get("evidence") or []]}
        if rec.get("supersedes"):
            result["supersedes"] = rec["supersedes"]
        results.append(result)

    append_records(project.records_path, to_write)
    return results


def check(project: Project, url: str | None = None, text: str | None = None,
          record: dict | None = None) -> dict:
    records, _ = read_records(project.records_path)
    if url:
        target = normalize_url(url)
        matches = [r for r in records if r.get("url") and normalize_url(r["url"]) == target]
    elif text:
        needle = fold(text)
        matches = [r for r in records if needle and needle in fold(r.get("text"))]
    else:
        key = dedupe_key(record or {})
        index = _key_index(records)
        hit = (index.get(key) or index.get(f"{key}#1")) if key else None
        matches = [hit] if hit else []
    return {"found": bool(matches),
            "matches": [{"id": r["id"], "record_type": r.get("record_type"), "origin": r.get("origin"),
                         "url": r.get("url")} for r in matches]}


def main(argv: list[str] | None = None) -> int:
    setup_stdout()
    parser = argparse.ArgumentParser(description="Ghi bản ghi vào kho / kiểm tra đã có chưa")
    parser.add_argument("--project", help="thư mục dự án (mặc định: thư mục chứa .claude)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_add = sub.add_parser("add")
    p_add.add_argument("--run", required=True)
    p_add.add_argument("--json", required=True, help="file JSON (1 object hoặc mảng), hoặc - để đọc stdin")
    p_check = sub.add_parser("check")
    group = p_check.add_mutually_exclusive_group(required=True)
    group.add_argument("--url")
    group.add_argument("--text")
    group.add_argument("--key-of", dest="key_of")
    args = parser.parse_args(argv)
    project = Project(args.project) if args.project else Project()

    if args.cmd == "add":
        raw = sys.stdin.read() if args.json == "-" else Path(args.json).read_text(encoding="utf-8")
        data = json.loads(raw)
        results = add_records(project, data if isinstance(data, list) else [data], args.run, project.load_config())
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0
    record = json.loads(Path(args.key_of).read_text(encoding="utf-8")) if args.key_of else None
    print(json.dumps(check(project, url=args.url, text=args.text, record=record), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
