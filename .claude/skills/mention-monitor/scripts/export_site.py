"""Export the read model to output/site/data.json for the local web viewer (web/).

Usage: python export_site.py [--project D:\\...]
Prints {"status": "ok", "file", "counts", "warnings"}.
The web app only displays this file; every merge rule (rechecks, supersedes, newest capture) lives in view.py.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

from common import Project, fold, now_iso, parse_iso, read_records, setup_stdout
from schema import DESCRIPTIONS, LABELS
from view import View, build_view, needs_join
from xlsx_helpers import make_thumbnail

SCHEMA_VERSION = 1
LIST_THUMB, EVIDENCE_THUMB = 240, 480
EXCLUSION_KEYS = ("id", "recorded_at", "url", "excerpt", "keywords_matched", "reason")
UNKNOWN_MONTH = "unknown"


def month_of(value, precision) -> str:
    dt = parse_iso(value)
    if dt is None or precision in (None, "year", "unknown"):
        return UNKNOWN_MONTH
    return dt.strftime("%Y-%m")


class Exporter:
    def __init__(self, project: Project, config: dict, view: View):
        self.project, self.config, self.view = project, config, view
        self.warnings = list(view.warnings)

    # ---- images -------------------------------------------------------------------------------------------
    def image(self, evidence: dict | None, width: int = LIST_THUMB) -> dict | None:
        if not evidence:
            return None
        thumb = None
        src = self.project.resolve(evidence["file"])
        if src.is_file():
            try:
                thumb = self.project.rel(make_thumbnail(src, self.project.thumbs_dir, width))
            except Exception:  # ảnh hỏng không được làm hỏng cả lần xuất
                self.warnings.append(f"Ảnh không đọc được, không tạo ảnh thu nhỏ: {evidence['file']}")
        else:
            self.warnings.append(f"Thiếu file ảnh: {evidence['file']}")
        return {k: evidence.get(k) for k in ("file", "sha256", "captured_at", "kind", "shows", "capture_tool")} | {
            "thumb": thumb}

    @staticmethod
    def newest(item: dict, kinds: tuple[str, ...]) -> dict | None:
        for group in reversed(item.get("evidence_groups") or []):
            for e in group:
                if e.get("kind") in kinds:
                    return e
        return None

    def main_image(self, item: dict, width: int = LIST_THUMB) -> dict | None:
        return self.image(self.newest(item, ("post",)) or self.newest(item, ("attach", "cscroll", "comment")), width)

    # ---- records ------------------------------------------------------------------------------------------
    def source(self, s: dict) -> dict:
        attach_text = " ".join((a.get("description") or "") + " " + (a.get("transcribed_text") or "")
                               for a in s.get("attachments") or [] if isinstance(a, dict))
        return {
            **{k: s.get(k) for k in (
                "id", "platform", "content_type", "url", "url_kind", "container_id", "container_name", "author_name",
                "author_url", "author_kind", "author_badge", "posted_at_raw", "posted_at", "posted_at_precision",
                "text", "attachments", "shared_from", "keywords_matched", "entities_mentioned", "topics", "tone",
                "claim_type", "importance", "importance_reason", "status", "last_checked_at", "captured_at", "run_id",
                "origin", "supersedes", "notes", "snapshot_file", "snapshot_sha256", "comments_collected")},
            "current_text": s.get("current_text"),
            "metrics": s.get("current_metrics") or {},
            "metrics_history": s.get("metrics_history") or [],
            "month": month_of(s.get("posted_at"), s.get("posted_at_precision")),
            "main_image": self.main_image(s),
            "captures": [{**c, "images": [self.image(e) for e in c["images"]]} for c in s.get("captures") or []],
            "search": fold(" ".join(filter(None, [s.get("text"), s.get("current_text"), s.get("author_name"),
                                                   s.get("container_name"), attach_text, s.get("id")]))),
        }

    def comment(self, c: dict, order: int) -> dict:
        return {
            **{k: c.get(k) for k in (
                "id", "source_id", "parent_comment_id", "depth", "url", "fb_comment_id", "author_name", "author_url",
                "author_kind", "author_badge", "posted_at_raw", "posted_at", "posted_at_precision", "text",
                "attachments", "keywords_matched", "entities_mentioned", "topics", "tone", "claim_type", "importance",
                "importance_reason", "status", "last_checked_at", "captured_at", "run_id", "notes", "scroll_refs")},
            "order": order,
            "reactions": (c.get("current_metrics") or {}).get("reactions"),
            "reply_count": (c.get("current_metrics") or {}).get("reply_count"),
            "month": month_of(c.get("posted_at"), c.get("posted_at_precision")),
            "own_image": self.image(self.newest(c, ("comment",))),
            "search": fold(" ".join(filter(None, [c.get("text"), c.get("author_name"), c.get("id")]))),
        }

    def container(self, c: dict, counts: Counter) -> dict:
        return {**{k: c.get(k) for k in (
            "id", "platform", "kind", "name", "url", "privacy", "joined", "scan_mode", "topic_dedicated",
            "member_count", "member_count_at", "last_scanned_at", "notes", "status")},
            "needs_join": needs_join(c), "source_count": counts.get(c["id"], 0)}

    def change(self, r: dict) -> dict:
        target = r["_target"]
        return {**{k: r.get(k) for k in ("id", "target_id", "checked_at", "status", "new_text", "metrics", "updates",
                                         "notes")},
                "target_type": target.get("record_type"), "metrics_grew": r.get("_metrics_grew", False),
                "images": [self.image(e) for e in r.get("evidence") or []]}

    # ---- aggregates ---------------------------------------------------------------------------------------
    def people(self, items: list[dict]) -> list[dict]:
        people: dict[str, dict] = {}
        for x in items:
            key = x.get("author_url") or "name:" + (x.get("author_name") or "")
            p = people.setdefault(key, {"key": key, "name": x.get("author_name") or "", "url": x.get("author_url"),
                                        "kind": x.get("author_kind"), "posts": 0, "comments": 0, "dates": [],
                                        "platforms": set(), "ids": []})
            p["posts" if x["record_type"] == "source" else "comments"] += 1
            p["ids"].append(x["id"])
            if x.get("posted_at"):
                p["dates"].append(x["posted_at"])
            if x.get("platform"):
                p["platforms"].add(x["platform"])
        out = []
        for p in people.values():
            dates = sorted(p.pop("dates"))
            out.append({**p, "platforms": sorted(p["platforms"]), "first": dates[0] if dates else None,
                        "last": dates[-1] if dates else None})
        return sorted(out, key=lambda p: (-(p["posts"] + p["comments"]), fold(p["name"])))

    def parties(self, items: list[dict]) -> list[dict]:
        out = []
        for party in self.config.get("key_parties", []):
            hits = [x for x in items if party["id"] in (x.get("entities_mentioned") or [])]
            dates = sorted(x["posted_at"] for x in hits if x.get("posted_at"))
            out.append({**{k: party.get(k) for k in ("id", "name", "label", "kind", "role", "primary",
                                                     "press_sources", "keyword_group")},
                        "mentions": len(hits), "first": dates[0] if dates else None,
                        "last": dates[-1] if dates else None})
        return out

    def gaps(self, latest_run: str | None) -> list[dict]:
        gaps = [{"id": r["id"], "section": r.get("section"), "query": r.get("query"),
                 "issue": ("; ".join(map(str, r["issues"])) if isinstance(r.get("issues"), list)
                           else r.get("issues")) or "Chưa cuộn tới hết kết quả"}
                for r in self.view.search_logs if r.get("issues") or not r.get("reached_end")]
        progress = self.project.run_dir(latest_run) / "progress.json" if latest_run else None
        if progress and progress.is_file():
            for t in json.loads(progress.read_text(encoding="utf-8")).get("tasks", []):
                if t.get("status") != "done":
                    what = " · ".join(str(v) for v in (t.get("section") or t.get("kind"), t.get("container_id"),
                                                       t.get("query"), t.get("url")) if v)
                    gaps.append({"id": t["id"], "section": t.get("section"), "query": what,
                                 "issue": ("Bị chặn" if t["status"] == "blocked" else "Chưa làm")
                                 + (f" — {t['note']}" if t.get("note") else "")})
        return gaps

    def stats(self, sources: list[dict], comments: list[dict]) -> dict:
        items = sources + comments
        view = self.view
        runs = sorted({r["run_id"] for r in view.sources + view.comments + view.search_logs + view.rechecks
                       if r.get("run_id") and r.get("origin") != "legacy" and r["run_id"] != "LEGACY-IMPORT"})
        latest = runs[-1] if runs else None
        months = Counter(x["month"] for x in items)
        by_party = Counter(pid for x in items for pid in x.get("entities_mentioned") or [])
        return {
            "totals": {"sources": len(sources), "comments": len(comments), "containers": len(view.containers),
                       "need_join": sum(1 for c in view.containers if needs_join(c)),
                       "exclusions": len(view.exclusions), "high": sum(1 for x in items if x.get("importance") == "cao"),
                       "events": len(view.events)},
            "by_platform": dict(Counter(s.get("platform") for s in sources)),
            "by_tone": dict(Counter(x.get("tone") for x in items if x.get("tone"))),
            "by_importance": dict(Counter(x.get("importance") for x in items if x.get("importance"))),
            "by_month": [{"month": m, "count": months[m]} for m in sorted(set(months) - {UNKNOWN_MONTH})]
                        + [{"month": UNKNOWN_MONTH, "count": months.get(UNKNOWN_MONTH, 0)}],
            "by_party": {p["id"]: by_party.get(p["id"], 0) for p in self.config.get("key_parties", [])},
            "latest_run": latest, "runs": runs,
            "new_in_latest_run": {"sources": sum(1 for s in sources if latest and s.get("run_id") == latest),
                                  "comments": sum(1 for c in comments if latest and c.get("run_id") == latest)},
            "gaps": self.gaps(latest),
        }

    def evidence(self) -> list[dict]:
        out = []
        for x in self.view.sources + self.view.comments:
            if x.get("importance") != "cao":
                continue
            ev = self.newest(x, ("comment",)) if x["record_type"] == "comment" else (
                self.newest(x, ("post",)) or self.newest(x, ("attach", "cscroll")))
            text = x.get("text") or ""
            out.append({"id": x["id"], "type": x["record_type"], "source_id": x.get("source_id"),
                        "image": self.image(ev, EVIDENCE_THUMB), "summary": text if len(text) <= 300 else text[:300] + "…",
                        "author_name": x.get("author_name"), "url": x.get("url"), "posted_at_raw": x.get("posted_at_raw"),
                        "posted_at": x.get("posted_at"), "posted_at_precision": x.get("posted_at_precision"),
                        "reason": x.get("importance_reason"), "captured_at": x.get("captured_at"),
                        "container_name": x.get("container_name")})
        return out

    def build(self) -> dict:
        view = self.view
        sources = [self.source(s) for s in view.sources]
        comments = [self.comment(c, i) for i, c in enumerate(view.comments)]
        counts = Counter(s.get("container_id") for s in view.sources if s.get("container_id"))
        return {
            "schema_version": SCHEMA_VERSION, "generated_at": now_iso(),
            "project_name": self.config.get("project_name", ""), "disclaimer": self.config.get("disclaimer"),
            "labels": LABELS, "descriptions": DESCRIPTIONS,
            "keyword_groups": [{"id": g["id"], "label": g["label"]} for g in self.config.get("keyword_groups", [])],
            "parties": self.parties(view.sources + view.comments),
            "sources": sources, "comments": comments,
            "containers": [self.container(c, counts) for c in view.containers],
            "events": [{k: e.get(k) for k in ("id", "date_raw", "date", "sort_key", "description", "source_text",
                                               "related_ids", "reliability", "origin")} for e in view.events],
            "search_logs": [{k: r.get(k) for k in (
                "id", "run_id", "platform", "scope", "container_id", "section", "query", "filters", "started_at",
                "ended_at", "results_seen", "results_new", "results_duplicate", "results_excluded", "reached_end",
                "issues", "notes")} for r in view.search_logs],
            "changes": [self.change(r) for r in view.changes],
            "exclusions": [{k: r.get(k) for k in EXCLUSION_KEYS} for r in view.exclusions],
            "people": self.people(view.sources + view.comments),
            "stats": self.stats(sources, comments),
            "evidence": self.evidence(),
            "warnings": self.warnings,
        }


def export(project: Project) -> dict:
    config = project.load_config()
    records, warnings = read_records(project.records_path)
    exporter = Exporter(project, config, build_view(records, warnings))
    data = exporter.build()
    out = project.root / "output" / "site" / "data.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, out)
    return {"status": "ok", "file": str(out),
            "counts": {k: len(data[k]) for k in ("sources", "comments", "containers", "events", "evidence")},
            "warnings": data["warnings"]}


def main(argv: list[str] | None = None) -> int:
    setup_stdout()
    parser = argparse.ArgumentParser(description="Xuất dữ liệu cho web xem kết quả (output/site/data.json)")
    parser.add_argument("--project", help="thư mục dự án (mặc định: thư mục chứa .claude)")
    args = parser.parse_args(argv)
    project = Project(args.project) if args.project else Project()
    print(json.dumps(export(project), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
