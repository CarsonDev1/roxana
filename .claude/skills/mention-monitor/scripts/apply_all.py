"""Write every classified bundle (cls.json present, applied.json absent) into the store.

python apply_all.py --run RUN [--web <run>/web/bundles] [--fb <run>/bundles --containers <map.json>]
python apply_all.py --run RUN --pending   → lists bundles still waiting for a cls.json (to hand to classifiers)

Web bundles → apply_article; Facebook bundles → apply_bundle (container id/name looked up by group id in the
permalink via --containers {"<group id>": {"id": "FB-G0001", "name": "..."}}). Results go to applied.json in the bundle
(including invalid ones, so errors are visible and can be fixed then re-applied by deleting applied.json).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from bundle_to_records import apply_article, apply_bundle
from common import Project, setup_stdout


def web_ready(d: Path) -> bool:
    m = d / "meta.json"
    return m.exists() and json.loads(m.read_text(encoding="utf-8")).get("relevant") and (d / "article.txt").exists()


def fb_ready(d: Path) -> bool:
    log = d / "log.json"
    return log.exists() and not json.loads(log.read_text(encoding="utf-8")).get("unavailable")


def main(argv=None) -> int:
    setup_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--web")
    ap.add_argument("--fb")
    ap.add_argument("--containers")
    ap.add_argument("--pending", action="store_true")
    ap.add_argument("--events", action="store_true", help="ghi luôn các mốc trong cls.json (mặc định: không — gom lại thành dòng thời gian chuẩn trước)")
    args = ap.parse_args(argv)
    project = Project()
    groups = json.loads(Path(args.containers).read_text(encoding="utf-8")) if args.containers else {}
    todo = []
    if args.web:
        todo += [("web", d) for d in sorted(Path(args.web).iterdir()) if d.is_dir() and web_ready(d)]
    if args.fb:
        todo += [("fb", d) for d in sorted(Path(args.fb).iterdir()) if d.is_dir() and fb_ready(d)]
    if args.pending:
        print(json.dumps([str(d) for _, d in todo if not (d / "cls.json").exists()], ensure_ascii=False, indent=1))
        return 0
    summary = {"added": 0, "duplicate": 0, "invalid": 0, "errors": []}
    for kind, d in todo:
        if not (d / "cls.json").exists() or (d / "applied.json").exists():
            continue
        cls = json.loads((d / "cls.json").read_text(encoding="utf-8"))
        try:
            if kind == "web":
                res = {"source": apply_article(project, d, cls, args.run)}
            else:
                feed = json.loads((d / "feed.json").read_text(encoding="utf-8"))
                gid = (re.search(r"/groups/([^/]+)/", feed["permalink"]) or [None, None])[1]
                g = groups.get(gid) or {}
                res = apply_bundle(project, d, cls, args.run, container_id=g.get("id"), container_name=g.get("name"))
            if args.events and res["source"]["status"] == "added" and cls.get("events"):  # mốc dòng thời gian rút ra từ bài
                from add_record import add_records
                evs = [{"record_type": "event", "related_ids": [res["source"]["id"]], **e} for e in cls["events"]]
                res["events"] = add_records(project, evs, args.run, project.load_config())
        except ValueError as exc:
            res = {"source": {"status": "invalid", "errors": [str(exc)]}}
        (d / "applied.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        st = res["source"]["status"]
        summary[st] = summary.get(st, 0) + 1
        bad = [c for c in res.get("comments", []) if c["status"] == "invalid"]
        if st == "invalid" or bad:
            summary["errors"].append({"bundle": d.name, "source": res["source"].get("errors"),
                                      "comments": [c.get("errors") for c in bad][:3]})
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
