"""Merge feed + search result files into one capture list; name-only matches go to an exclusion list.

python select_candidates.py <run_dir>
Reads <run_dir>/feeds/*.jsonl (posts of dedicated groups: all kept) and <run_dir>/search/*.jsonl (kept only when
the snippet/author/group matches a keyword group, respecting requires_context). Writes
<run_dir>/capture_list.jsonl (unique permalinks, feed first) and <run_dir>/exclusions.jsonl (url, excerpt ≤100,
keywords, reason — never the poster's name).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from common import Project, match_keywords, normalize_url, setup_stdout


def _lines(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def select(run_dir: Path, config: dict) -> dict:
    keep, excluded, seen = [], [], set()
    for f in sorted((run_dir / "feeds").glob("*.jsonl")):
        for d in _lines(f):
            key = normalize_url(d["permalink"])
            if "#pos" in d["permalink"] or key in seen:
                continue
            seen.add(key)
            keep.append({**d, "origin_list": f.name})
    for f in sorted((run_dir / "search").glob("*.jsonl")):
        for d in _lines(f):
            if "permalink" not in d or "#pos" in d["permalink"]:
                continue
            key = normalize_url(d["permalink"])
            if key in seen:
                continue
            text = " ".join(filter(None, [d.get("message"), d.get("text")]))
            matched, lacking = match_keywords(text, config)
            seen.add(key)
            if matched:
                keep.append({**d, "origin_list": f.name, "keywords": matched})
            elif lacking:
                excluded.append({"url": d["permalink"], "excerpt": " ".join(text.split())[:100], "keywords_matched": lacking,
                                 "reason": "Trùng tên — không có từ ngữ cảnh của vụ việc", "search_file": f.name})
            # không khớp từ khoá nào (Facebook trả kết quả lân cận) → bỏ qua, không phải trùng tên
    (run_dir / "capture_list.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in keep), encoding="utf-8")
    (run_dir / "exclusions.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in excluded), encoding="utf-8")
    return {"capture": len(keep), "excluded": len(excluded)}


def main(argv=None) -> int:
    setup_stdout()
    run_dir = Path((argv or sys.argv[1:])[0])
    print(json.dumps(select(run_dir, Project().load_config()), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
