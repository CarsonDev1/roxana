"""Run helpers: store stats, recheck-due list, progress file, end-of-run report.

Usage (--project goes BEFORE the sub-command):
  python status.py stats
  python status.py recheck-due --run RUN-2026-10-11-01
  python status.py progress --run RUN-... [--init full|update] [--add-tasks tasks.json]
                            [--set T001=done[:LOG-000001]] [--note "..."]
  python status.py report --run RUN-...
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from common import TZ, Project, now_iso, parse_iso, read_records, setup_stdout
from schema import label
from view import View, build_view, needs_join

TASK_STATUSES = {"pending", "done", "blocked"}
TASK_IDENTITY = ("kind", "section", "query", "filters", "container_id", "url", "target_id")
PRIORITY = {"cao": 0, "legacy": 1, "trung_binh": 2, "thap": 3}


def load_view(project: Project) -> View:
    records, warnings = read_records(project.records_path)
    return build_view(records, warnings)


def stats(view: View) -> dict:
    return {
        "sources": len(view.sources), "comments": len(view.comments), "containers": len(view.containers),
        "containers_need_join": sum(1 for c in view.containers if needs_join(c)),
        "search_logs": len(view.search_logs), "exclusions": len(view.exclusions), "events": len(view.events),
        "legacy_sources_pending": sum(1 for s in view.sources if s.get("origin") == "legacy"),
        "sources_by_platform": dict(Counter(s.get("platform") for s in view.sources)),
        "by_importance": dict(Counter(x.get("importance") for x in view.sources + view.comments)),
        "warnings": view.warnings,
    }


def _excerpt(text, n: int = 80) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[:n] + "…"


def _issues(issues) -> str:
    return "; ".join(map(str, issues)) if isinstance(issues, list) else (issues or "")


def recheck_due(view: View, config: dict, run_id: str, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(TZ)
    policy = config.get("recheck_policy_days", {"cao": 0, "trung_binh": 30, "thap": 90})
    checked = {r.get("target_id") for r in view.rechecks if r.get("run_id") == run_id}
    due = []
    for s in view.sources:
        if s["status"] == "deleted" or s["id"] in checked or s.get("run_id") == run_id:
            continue
        entry = {"id": s["id"], "url": s.get("url"), "url_kind": s.get("url_kind"),
                 "importance": s.get("importance"), "container_name": s.get("container_name"),
                 "text_excerpt": _excerpt(s.get("text")), "last_checked": s.get("last_checked_at") or s.get("captured_at")}
        if s.get("origin") == "legacy":
            due.append({**entry, "priority": PRIORITY["legacy"],
                        "reason": "Từ file cũ — cần chụp ảnh và ghi bản quét thay thế"})
            continue
        days = policy.get(s.get("importance"), 30)
        last = parse_iso(entry["last_checked"])
        if last is None or (now - last).days >= days:
            due.append({**entry, "priority": PRIORITY.get(s.get("importance"), 2),
                        "reason": f"Mức {label('importance', s.get('importance'))}: kiểm tra lại sau {days} ngày"})
    due.sort(key=lambda d: (d["priority"], d["id"]))
    for d in due:
        d.pop("priority")
    return due


def _progress_path(project: Project, run_id: str) -> Path:
    return project.run_dir(run_id) / "progress.json"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def load_progress(project: Project, run_id: str) -> dict:
    path = _progress_path(project, run_id)
    if not path.exists():
        raise FileNotFoundError(f"Chưa có progress cho {run_id} — chạy progress --init trước")
    return json.loads(path.read_text(encoding="utf-8"))


def init_progress(project: Project, run_id: str, mode: str) -> dict:
    path = _progress_path(project, run_id)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if mode not in ("full", "update"):
        raise ValueError(f"mode phải là full hoặc update, không phải {mode!r}")
    data = {"run_id": run_id, "mode": mode, "started_at": now_iso(), "tasks": []}
    _write_json(path, data)
    return data


def _identity(task: dict) -> str:
    return json.dumps({k: task.get(k) for k in TASK_IDENTITY}, sort_keys=True, ensure_ascii=False)


def add_tasks(project: Project, run_id: str, tasks: list[dict]) -> dict:
    data = load_progress(project, run_id)
    seen = {_identity(t) for t in data["tasks"]}
    for task in tasks:
        ident = _identity(task)
        if ident in seen:
            continue
        seen.add(ident)
        data["tasks"].append({**task, "id": f"T{len(data['tasks']) + 1:03d}", "status": "pending", "log_id": None})
    _write_json(_progress_path(project, run_id), data)
    return data


def set_task(project: Project, run_id: str, task_id: str, new_status: str,
             log_id: str | None = None, note: str | None = None) -> dict:
    if new_status not in TASK_STATUSES:
        raise ValueError(f"trạng thái task phải là {', '.join(sorted(TASK_STATUSES))}, không phải {new_status!r}")
    data = load_progress(project, run_id)
    for task in data["tasks"]:
        if task["id"] == task_id:
            task["status"] = new_status
            if log_id:
                task["log_id"] = log_id
            if note:
                task["note"] = note
            _write_json(_progress_path(project, run_id), data)
            return data
    raise ValueError(f"Không có task {task_id} trong {run_id}")


def summary(progress: dict) -> dict:
    tasks = progress["tasks"]
    count = Counter(t["status"] for t in tasks)
    return {"total": len(tasks), "done": count["done"], "pending": count["pending"], "blocked": count["blocked"],
            "next": [t for t in tasks if t["status"] == "pending"][:10]}


def _task_text(task: dict) -> str:
    parts = [label("section", task["section"]) if task.get("section") else task.get("kind"),
             task.get("container_id"), f"\"{task['query']}\"" if task.get("query") else None,
             ", ".join(f"{k}={v}" for k, v in (task.get("filters") or {}).items()) or None,
             task.get("url"), task.get("target_id")]
    return " · ".join(str(p) for p in parts if p)


def report(project: Project, view: View, config: dict, run_id: str) -> Path:
    path = _progress_path(project, run_id)
    progress = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    lines = [f"# Báo cáo lần quét {run_id}", ""]
    if progress:
        lines += [f"- Chế độ: {'Quét toàn bộ' if progress['mode'] == 'full' else 'Cập nhật'}",
                  f"- Bắt đầu: {progress['started_at']}"]
    lines.append(f"- Lập báo cáo lúc: {now_iso()}")

    new_sources = [s for s in view.sources if s.get("run_id") == run_id]
    new_comments = [c for c in view.comments if c.get("run_id") == run_id]
    new_containers = [c for c in view.containers if c.get("run_id") == run_id]
    logs = [r for r in view.search_logs if r.get("run_id") == run_id]
    exclusions = [r for r in view.exclusions if r.get("run_id") == run_id]
    lines += ["", "## Kết quả",
              f"- Nguồn mới: {len(new_sources)}",
              f"- Bình luận mới: {len(new_comments)}",
              f"- Nhóm/trang mới: {len(new_containers)}",
              f"- Lần tìm kiếm: {len(logs)} (kết quả trùng: {sum(r.get('results_duplicate') or 0 for r in logs)})",
              f"- Kết quả loại trừ (trùng tên): {len(exclusions)}"]

    important = [x for x in new_sources + new_comments if x.get("importance") == "cao"]
    lines += ["", "## Nội dung quan trọng mới (mức cao)"]
    lines += [f"- {x['id']} — {x.get('author_name', '')} — {_excerpt(x.get('text'))} — "
              f"{x.get('url') or x.get('source_id')}" for x in important] or ["- Không có"]

    lines += ["", "## Thay đổi phát hiện"]
    changes = []
    for c in view.changes:
        if c.get("run_id") != run_id:
            continue
        extra = " (tương tác tăng)" if c.get("_metrics_grew") else ""
        if c.get("updates"):
            extra += " — cập nhật " + ", ".join(f"{k}={v}" for k, v in c["updates"].items())
        changes.append(f"- {c['target_id']}: {label('recheck_status', c.get('status'))}{extra}")
    lines += changes or ["- Không có"]

    lines += ["", "## Nhóm kín cần xin vào (anh/chị tự xin vào, lần cập nhật sau sẽ quét)"]
    lines += [f"- {c.get('name')} — {c.get('url')}" for c in view.containers if needs_join(c)] or ["- Không có"]

    lines += ["", "## Chưa quét được / giới hạn"]
    gaps = [f"- {r['id']} · {label('section', r.get('section'))} · \"{r.get('query', '')}\": "
            f"{_issues(r.get('issues')) or 'chưa cuộn tới hết kết quả'}"
            for r in logs if r.get("issues") or not r.get("reached_end")]
    if progress:
        for t in progress["tasks"]:
            if t["status"] == "done":
                continue
            state = "bị chặn" if t["status"] == "blocked" else "chưa làm"
            gaps.append(f"- Task {t['id']} ({_task_text(t)}): {state}"
                        + (f" — {t['note']}" if t.get("note") else ""))
    lines += gaps or ["- Không có"]

    if view.warnings:
        lines += ["", "## Cảnh báo dữ liệu"] + [f"- {w}" for w in view.warnings]

    out = project.run_dir(run_id) / "report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    setup_stdout()
    parser = argparse.ArgumentParser(description="Thống kê kho, tiến độ, danh sách kiểm tra lại, báo cáo")
    parser.add_argument("--project", help="thư mục dự án (mặc định: thư mục chứa .claude)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("stats")
    p_due = sub.add_parser("recheck-due")
    p_due.add_argument("--run", required=True)
    p_prog = sub.add_parser("progress")
    p_prog.add_argument("--run", required=True)
    p_prog.add_argument("--init", choices=["full", "update"])
    p_prog.add_argument("--add-tasks", dest="add_tasks")
    p_prog.add_argument("--set", dest="set_task", help="T001=done hoặc T001=done:LOG-000001")
    p_prog.add_argument("--note")
    p_rep = sub.add_parser("report")
    p_rep.add_argument("--run", required=True)
    args = parser.parse_args(argv)
    project = Project(args.project) if args.project else Project()

    if args.cmd == "stats":
        out = stats(load_view(project))
    elif args.cmd == "recheck-due":
        out = recheck_due(load_view(project), project.load_config(), args.run)
    elif args.cmd == "progress":
        if args.init:
            init_progress(project, args.run, args.init)
        if args.add_tasks:
            add_tasks(project, args.run, json.loads(Path(args.add_tasks).read_text(encoding="utf-8")))
        if args.set_task:
            task_id, _, rest = args.set_task.partition("=")
            new_status, _, log_id = rest.partition(":")
            set_task(project, args.run, task_id, new_status, log_id or None, args.note)
        out = summary(load_progress(project, args.run))
    else:
        out = {"file": str(report(project, load_view(project), project.load_config(), args.run))}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
