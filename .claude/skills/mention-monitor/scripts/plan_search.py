"""Build the Facebook search matrix (facebook.md §1) as a task list with ready-to-open URLs.

python plan_search.py [--project P] [--from-year 2017] [--to-year 2026] > tasks.json
Every term of every keyword group, accented and unaccented; posts per year + "recent"; groups/pages/videos/photos;
hashtags for the roxana/tuongphong/naviland groups. Terms starting with "#" are used for hashtags only.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from datetime import datetime
from urllib.parse import quote

from common import TZ, Project, setup_stdout, strip_accents

SECTIONS = ("groups", "pages", "videos", "photos")
HASHTAG_GROUPS = ("roxana", "tuongphong", "naviland")


def year_filter(year: int) -> str:
    args = {"start_year": str(year), "start_month": f"{year}-1", "end_year": str(year), "end_month": f"{year}-12",
            "start_day": f"{year}-1-1", "end_day": f"{year}-12-31"}
    inner = json.dumps({"name": "creation_time", "args": json.dumps(args, separators=(",", ":"))}, separators=(",", ":"))
    return base64.b64encode(json.dumps({"rp_creation_time:0": inner}, separators=(",", ":")).encode()).decode()


def recent_filter() -> str:
    inner = json.dumps({"name": "recent_posts", "args": ""}, separators=(",", ":"))
    return base64.b64encode(json.dumps({"recent_posts:0": inner}, separators=(",", ":")).encode()).decode()


def queries(config: dict) -> list[tuple[str, str]]:
    seen, out = set(), []
    for g in config["keyword_groups"]:
        for term in g["terms"]:
            if term.startswith("#"):
                continue
            for q in (term, strip_accents(term)):
                if q.lower() not in seen:
                    seen.add(q.lower())
                    out.append((g["id"], q))
    return out


def hashtags(config: dict) -> list[tuple[str, str]]:
    seen, out = set(), []
    for g in config["keyword_groups"]:
        if g["id"] not in HASHTAG_GROUPS:
            continue
        for term in g["terms"]:
            tag = strip_accents(term).lstrip("#").replace(" ", "").lower()
            if tag and tag not in seen:
                seen.add(tag)
                out.append((g["id"], tag))
    return out


def plan(config: dict, from_year: int, to_year: int) -> list[dict]:
    tasks = []
    for gid, q in queries(config):
        base = f"https://www.facebook.com/search/posts/?q={quote(q)}"
        for y in range(to_year, from_year - 1, -1):
            tasks.append({"kind": "search", "section": "posts", "query": q, "group": gid, "filters": {"year": y},
                          "url": f"{base}&filters={year_filter(y)}"})
        tasks.append({"kind": "search", "section": "posts", "query": q, "group": gid, "filters": {"sort": "recent"},
                      "url": f"{base}&filters={recent_filter()}"})
    for gid, q in queries(config):
        for sec in SECTIONS:
            tasks.append({"kind": "search", "section": sec, "query": q, "group": gid,
                          "url": f"https://www.facebook.com/search/{sec}/?q={quote(q)}"})
    for gid, tag in hashtags(config):
        tasks.append({"kind": "search", "section": "hashtag", "query": f"#{tag}", "group": gid,
                      "url": f"https://www.facebook.com/hashtag/{tag}"})
    return tasks


def main(argv=None) -> int:
    setup_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--project")
    ap.add_argument("--from-year", type=int, default=2017)
    ap.add_argument("--to-year", type=int, default=datetime.now(TZ).year)
    args = ap.parse_args(argv)
    project = Project(args.project) if args.project else Project()
    print(json.dumps(plan(project.load_config(), args.from_year, args.to_year), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
