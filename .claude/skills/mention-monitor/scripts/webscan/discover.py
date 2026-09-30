"""Find web mentions (press + other sites) for every keyword term — no Facebook involved.

python discover.py <out_dir> [--from-year 2017] [--to-year 2026] [--sources news,web]

news: Google News RSS per term × year (after:/before:) — press articles; ~100 items per request, hence per year.
web:  DuckDuckGo HTML results (up to 5 pages, following the page's own "next" form) — forums, blogs, other sites.
Writes <out_dir>/candidates.jsonl (one line per unique link: url, title, source_name, published, snippet, query,
engine) and <out_dir>/discover_log.jsonl (one line per request). Resumable. A captcha/anomaly page stops that
source (never bypassed).
"""
from __future__ import annotations

import argparse
import html
import json
import random
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import TZ, Project, setup_stdout, strip_accents  # noqa: E402

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0 Safari/537.36"


def terms(config: dict) -> list[tuple[str, str]]:
    seen, out = set(), []
    for g in config["keyword_groups"]:
        for t in g["terms"] + g.get("weak_terms", []):
            if t.startswith("#"):
                continue
            for q in (t, strip_accents(t)):
                if q.lower() not in seen:
                    seen.add(q.lower())
                    out.append((g["id"], q))
    return out


def fetch(url: str, data: bytes | None = None) -> bytes:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept-Language": "vi-VN,vi;q=0.9"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()


def google_news(query: str, year: int | None) -> list[dict]:
    q = f'"{query}"' + (f" after:{year}-01-01 before:{year + 1}-01-01" if year else "")
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q, "hl": "vi", "gl": "VN", "ceid": "VN:vi"})
    root = ET.fromstring(fetch(url))
    out = []
    for it in root.findall(".//item"):
        pub = it.findtext("pubDate")
        try:
            pub = parsedate_to_datetime(pub).astimezone(TZ).isoformat(timespec="seconds") if pub else None
        except Exception:
            pass
        out.append({"url": it.findtext("link"), "title": html.unescape(it.findtext("title") or ""),
                    "source_name": it.findtext("source"), "published": pub, "engine": "google_news"})
    return out


def ddg(query: str, pages: int = 5) -> list[dict]:
    out, form = [], {"q": f'"{query}"', "kl": "vn-vi"}
    for _ in range(pages):
        body = fetch("https://html.duckduckgo.com/html/", urllib.parse.urlencode(form).encode()).decode("utf-8", "replace")
        if re.search(r"anomaly|captcha|unusual traffic", body, re.I):
            raise RuntimeError("ddg: yêu cầu xác minh (captcha) — dừng nguồn này, không vượt qua")
        for m in re.finditer(r'class="result__a" href="([^"]+)"[^>]*>(.*?)</a>(.*?)(?=class="result__a"|$)', body, re.S):
            href = html.unescape(m.group(1))
            real = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg", [href])[0]
            snip = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', m.group(3), re.S)
            out.append({"url": real, "title": html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip(),
                        "snippet": html.unescape(re.sub(r"<[^>]+>", "", snip.group(1))).strip() if snip else None,
                        "engine": "ddg"})
        nxt = [f for f in re.findall(r"<form[^>]*>(.*?)</form>", body, re.S) if re.search(r'value="(Next|Trang sau|Tiếp)', f)]
        if not nxt:
            break
        form = dict(re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]*)"', nxt[-1]))
        time.sleep(random.uniform(4, 8))
    return out


def main(argv=None) -> int:
    setup_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--from-year", type=int, default=2017)
    ap.add_argument("--to-year", type=int, default=datetime.now(TZ).year)
    ap.add_argument("--sources", default="news,web")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cand_f, log_f = out / "candidates.jsonl", out / "discover_log.jsonl"
    seen = {json.loads(l)["url"] for l in cand_f.read_text(encoding="utf-8").splitlines() if l.strip()} if cand_f.exists() else set()
    done = {(d["engine"], d["query"], d.get("year")) for d in
            (json.loads(l) for l in log_f.read_text(encoding="utf-8").splitlines() if l.strip()) if not d.get("error")} \
        if log_f.exists() else set()
    sources = set(args.sources.split(","))
    jobs = []
    for gid, q in terms(Project().load_config()):
        if "news" in sources:
            jobs += [("google_news", gid, q, y) for y in [None] + list(range(args.to_year, args.from_year - 1, -1))]
        if "web" in sources:
            jobs.append(("ddg", gid, q, None))
    blocked = set()
    with open(cand_f, "a", encoding="utf-8") as cf, open(log_f, "a", encoding="utf-8") as lf:
        for engine, gid, q, year in jobs:
            if (engine, q, year) in done or engine in blocked:
                continue
            entry = {"engine": engine, "query": q, "group": gid, "year": year,
                     "at": datetime.now(TZ).isoformat(timespec="seconds")}
            try:
                res = google_news(q, year) if engine == "google_news" else ddg(q)
                new = 0
                for r in res:
                    if r["url"] and r["url"] not in seen:
                        seen.add(r["url"])
                        cf.write(json.dumps({**r, "query": q, "group": gid}, ensure_ascii=False) + "\n")
                        new += 1
                cf.flush()
                entry.update(results=len(res), new=new)
            except Exception as exc:
                entry.update(error=str(exc)[:300])
                if "captcha" in str(exc):
                    blocked.add(engine)
            lf.write(json.dumps(entry, ensure_ascii=False) + "\n")
            lf.flush()
            print(json.dumps(entry, ensure_ascii=False), flush=True)
            time.sleep(random.uniform(2.5, 6) if engine == "google_news" else random.uniform(10, 20))
    print(json.dumps({"status": "ok", "candidates": len(seen), "blocked_sources": sorted(blocked)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
