"""Re-check relevance of captured, not-yet-applied web bundles with the current matcher and config.

python rematch.py <web_dir> [--do]   (without --do: only report)

A bundle that no longer matches gets meta.json "relevant": false plus a "rematch" note (so apply_all skips it; the
screenshots stay as a record of what was checked). A bare name found without case context (weak_terms /
requires_context) is also listed in <web_dir>/exclusions.json as exclusion drafts (no author names).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import Project, match_keywords, setup_stdout  # noqa: E402


def main(argv=None) -> int:
    setup_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("web_dir")
    ap.add_argument("--do", action="store_true")
    args = ap.parse_args(argv)
    web = Path(args.web_dir)
    config = Project().load_config()
    excl_f = web / "exclusions.json"
    excl = json.loads(excl_f.read_text(encoding="utf-8")) if excl_f.exists() else []
    known = {e["url"] for e in excl}
    dropped = []
    for d in sorted((web / "bundles").iterdir()):
        mf = d / "meta.json"
        if not mf.exists() or (d / "applied.json").exists():
            continue
        m = json.loads(mf.read_text(encoding="utf-8"))
        if not m.get("relevant") or not (d / "article.txt").exists():
            continue
        text = (d / "article.txt").read_text(encoding="utf-8")
        matched, lacking = match_keywords(f"{m.get('title') or ''}\n{text}", config)
        if matched:
            continue
        dropped.append({"bundle": d.name, "site": m.get("site"), "title": (m.get("title") or "")[:80], "lacking": lacking})
        if not args.do:
            continue
        m["rematch"] = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+07:00"), "previous_keywords": m.get("keywords"),
                        "keywords": [], "lacking_context": lacking}
        m["relevant"], m["keywords"], m["lacking_context"] = False, [], lacking
        mf.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
        url = m.get("canonical") or m.get("final")
        if lacking and url not in known:
            known.add(url)
            excl.append({"record_type": "exclusion", "platform": "web", "url": url,
                         "excerpt": (m.get("title") or "")[:100], "keywords_matched": lacking,
                         "reason": "Chỉ trùng tên (người, địa danh, nhân vật khác) — bài không nhắc tới dự án/vụ việc"})
    if args.do:
        excl_f.write_text(json.dumps(excl, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"dropped": len(dropped), "exclusions": sum(1 for x in dropped if x["lacking"]), "items": dropped},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
