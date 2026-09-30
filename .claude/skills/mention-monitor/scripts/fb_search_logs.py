"""Turn a run's Facebook scan logs (feeds/*.meta.json + search/done.json) into search_log records.

python fb_search_logs.py --run RUN [--add]   (without --add: writes <run>/pending/search_logs_fb.json only)

Group feeds → section group_feed (scope container); search tasks → their section (in_group_search: scope container).
container_id is looked up in the store by group id. results_new / results_duplicate: links not seen / already seen in an
earlier log of this run (in started_at order). Safe to re-run: search_log records are deduplicated.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from add_record import add_records
from common import Project, normalize_url, read_records, setup_stdout

GID = re.compile(r"/groups/([^/?#]+)")


def _rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _link(r: dict) -> str:
    link = r.get("permalink") or r.get("url") or ""
    return f"#pos{r.get('pos')}" if "#pos" in link or not link else normalize_url(link)


def _items(path: Path) -> list[str]:
    return [_link(r) for r in _rows(path)]


def build(project: Project, run: str) -> list[dict]:
    rd = project.run_dir(run)
    containers = {}
    for r in read_records(project.records_path)[0]:
        if r.get("record_type") == "container" and (m := GID.search(r.get("url") or "")):
            containers[m.group(1)] = r["id"]
    logs = []
    for meta_f in sorted((rd / "feeds").glob("group_*.meta.json")):
        gid = meta_f.name[len("group_"):-len(".meta.json")]
        meta = json.loads(meta_f.read_text(encoding="utf-8"))
        rows = _rows(meta_f.with_name(f"group_{gid}.jsonl"))
        passes = meta.pop("passes", []) + [meta]  # mỗi lượt cuộn (kể cả lượt nối tiếp) là một dòng nhật ký
        for k, ps in enumerate(passes):
            upto = passes[k + 1]["started_at"] if k + 1 < len(passes) else "9999"
            since = ps["started_at"] if k else ""  # lượt đầu gồm cả dòng ghi trước khi meta có lịch sử lượt
            items = [_link(r) for r in rows if since <= (r.get("seen_at") or "") < upto]
            issues = []
            if not ps.get("ended_at"):
                issues.append("Lượt cuộn feed dừng giữa chừng (không có dòng kết thúc) — chưa chắc đã tới bài cũ nhất")
            missing = sum(1 for i in items if i.startswith("#pos"))
            if missing:
                issues.append(f"{missing} bài không lấy được link riêng (Facebook không hiện link khi rê chuột)")
            if ps.get("item_errors"):
                issues.append(f"{ps['item_errors']} bài bỏ qua do lỗi khi đọc (bài bị gỡ khỏi trang lúc cuộn)")
            logs.append(({"record_type": "search_log", "platform": "facebook", "scope": "container",
                          "section": "group_feed", "query": "(feed nhóm, sắp theo mới nhất)" + (" — lượt nối tiếp" if k else ""),
                          "container_id": containers.get(gid), "started_at": ps["started_at"], "ended_at": ps.get("ended_at"),
                          "results_seen": ps.get("posts_seen") or len(items), "reached_end": bool(ps.get("reached_end")),
                          "issues": issues or None}, items))
    done_f = rd / "search" / "done.json"
    for task in (json.loads(done_f.read_text(encoding="utf-8")).values() if done_f.exists() else []):
        items = _items(rd / "search" / task["file"])
        in_group = task.get("kind") == "container"
        logs.append(({"record_type": "search_log", "platform": "facebook", "scope": "container" if in_group else "global",
                      "section": task["section"], "query": task["query"], "filters": task.get("filters") or None,
                      "container_id": containers.get(task.get("group_id")) if in_group else None,
                      "started_at": task["started_at"], "ended_at": task.get("ended_at"),
                      "results_seen": task.get("results_seen") or len(items), "reached_end": bool(task.get("reached_end")),
                      "issues": None}, items))
    logs.sort(key=lambda x: x[0]["started_at"])
    seen: set[str] = set()
    out = []
    for rec, items in logs:
        links = [i for i in items if not i.startswith("#pos")]
        new = [i for i in dict.fromkeys(links) if i not in seen]
        rec["results_new"], rec["results_duplicate"] = len(new), len(set(links)) - len(new)
        seen.update(links)
        out.append({k: v for k, v in rec.items() if v is not None})
    return out


def main(argv=None) -> int:
    setup_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--add", action="store_true")
    args = ap.parse_args(argv)
    project = Project()
    recs = build(project, args.run)
    out = project.run_dir(args.run) / "pending" / "search_logs_fb.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")
    summary = {"logs": len(recs), "file": str(out)}
    if args.add:
        res = add_records(project, recs, args.run, project.load_config())
        summary["status"] = {s: sum(1 for r in res if r["status"] == s) for s in {r["status"] for r in res}}
        summary["errors"] = [r for r in res if r["status"] == "invalid"][:5]
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
