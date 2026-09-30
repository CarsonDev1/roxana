"""Read model for the Excel builder and status reports, assembled from raw records."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class View:
    sources: list[dict] = field(default_factory=list)
    comments: list[dict] = field(default_factory=list)
    containers: list[dict] = field(default_factory=list)
    search_logs: list[dict] = field(default_factory=list)
    rechecks: list[dict] = field(default_factory=list)
    exclusions: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    changes: list[dict] = field(default_factory=list)
    by_id: dict[str, dict] = field(default_factory=dict)
    superseded: set[str] = field(default_factory=set)
    warnings: list[str] = field(default_factory=list)


def needs_join(container: dict) -> bool:
    return container.get("privacy") == "private" and container.get("joined") != "yes"


def _initial_metrics(rec: dict) -> dict:
    if rec.get("record_type") == "comment":
        return {"reactions": rec.get("reactions"), "reply_count": rec.get("reply_count")}
    return dict(rec.get("metrics") or {})


def _tree_order(comments: list[dict]) -> list[dict]:
    by_source: dict[str, list[dict]] = {}
    for c in comments:
        by_source.setdefault(c.get("source_id") or "", []).append(c)
    ordered: list[dict] = []
    for sid in sorted(by_source):
        group = sorted(by_source[sid], key=lambda c: c["id"])
        ids = {c["id"] for c in group}
        children: dict[str | None, list[dict]] = {}
        for c in group:
            parent = c.get("parent_comment_id")
            children.setdefault(parent if parent in ids else None, []).append(c)

        def walk(node: dict) -> None:
            ordered.append(node)
            for child in children.get(node["id"], []):
                walk(child)

        for root in children.get(None, []):
            walk(root)
    return ordered


def build_view(records: list[dict], warnings: list[str] | None = None) -> View:
    view = View(warnings=list(warnings or []))
    by_type: dict[str, list[dict]] = {}
    for rec in records:
        by_type.setdefault(rec.get("record_type"), []).append(rec)

    items: dict[str, dict] = {}
    for rtype in ("source", "comment", "container"):
        for rec in by_type.get(rtype, []):
            item = dict(rec)
            item.update(status="active", last_checked_at=None, all_evidence=list(rec.get("evidence") or []),
                        evidence_groups=[list(rec.get("evidence") or [])],
                        current_metrics=_initial_metrics(rec))
            items[item["id"]] = item

    view.superseded = {r["supersedes"] for r in by_type.get("source", []) if r.get("supersedes")}
    view.rechecks = sorted(by_type.get("recheck", []), key=lambda r: (r.get("checked_at") or "", r.get("id") or ""))
    for chk in view.rechecks:
        target = items.get(chk.get("target_id"))
        if target is None:
            view.warnings.append(f"{chk.get('id')} trỏ tới {chk.get('target_id')} không có trong kho — bỏ qua")
            continue
        before = dict(target["current_metrics"])
        new_metrics = {k: v for k, v in (chk.get("metrics") or {}).items() if v is not None}
        target["status"] = chk.get("status", "active")
        target["last_checked_at"] = chk.get("checked_at")
        target["all_evidence"].extend(chk.get("evidence") or [])
        target["current_metrics"].update(new_metrics)
        if chk.get("new_text") is not None:
            target["current_text"] = chk["new_text"]
        if chk.get("updates"):
            target.update(chk["updates"])
        if chk.get("scroll_refs"):
            target["scroll_refs"] = chk["scroll_refs"]
        if chk.get("evidence"):
            target["evidence_groups"].append(list(chk["evidence"]))
        grew = any(isinstance(v, (int, float)) and isinstance(before.get(k), (int, float)) and v > before[k]
                   for k, v in new_metrics.items())
        if chk.get("status") in ("edited", "deleted", "unavailable") or grew or chk.get("updates"):
            view.changes.append({**chk, "_target": target, "_metrics_grew": grew})

    view.sources = sorted((items[r["id"]] for r in by_type.get("source", []) if r["id"] not in view.superseded),
                          key=lambda s: s["id"])
    view.comments = _tree_order([items[r["id"]] for r in by_type.get("comment", [])])
    counts: dict[str, int] = {}
    for c in view.comments:
        counts[c["source_id"]] = counts.get(c["source_id"], 0) + 1
    for s in view.sources:
        s["comments_collected"] = counts.get(s["id"], 0)
    view.containers = sorted((items[r["id"]] for r in by_type.get("container", [])), key=lambda c: c["id"])
    view.search_logs = sorted(by_type.get("search_log", []), key=lambda r: (r.get("started_at") or "", r["id"]))
    view.exclusions = sorted(by_type.get("exclusion", []), key=lambda r: r["id"])
    view.events = sorted(by_type.get("event", []),
                         key=lambda e: (e.get("sort_key") or e.get("date") or "9999", e["id"]))
    view.by_id = items
    return view
