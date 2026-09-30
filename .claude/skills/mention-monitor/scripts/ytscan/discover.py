"""Find YouTube videos about the case — headless Chrome, no login, read-only.

python discover.py <yt_dir> [--scrolls N]

Every term in config.json (terms + weak_terms, with and without accents) is searched twice: by relevance and newest
first. Each result (video or Short) whose title/snippet/channel mentions a term — or a bare name that still needs
context — goes to <yt_dir>/candidates.jsonl (one line per video id). Every search → <yt_dir>/discover_log.jsonl.
Resumable (searches already in the log are skipped). A captcha / "unusual traffic" page stops the run (exit 3).
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import Project, match_keywords, setup_stdout, strip_accents  # noqa: E402

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0 Safari/537.36"
ORDERS = {"relevance": "", "newest": "CAI%253D"}
BLOCK = ("unusual traffic", "lưu lượng truy cập bất thường", "captcha", "not a robot")
VID = re.compile(r"(?:watch\?v=|/shorts/)([\w-]{11})")

RESULTS = r"""
() => {
  const out = [];
  const items = document.querySelectorAll('ytd-video-renderer, ytm-shorts-lockup-view-model, yt-lockup-view-model, ytd-reel-item-renderer');
  for (const el of items) {
    const a = el.querySelector('a[href*="/watch?v="], a[href*="/shorts/"]');
    if (!a) continue;
    const title = (el.querySelector('#video-title') || {}).innerText || (el.querySelector('h3, [role="heading"]') || {}).innerText
                  || a.getAttribute('title') || a.innerText;
    const ch = el.querySelector('#channel-name a, ytd-channel-name a');
    out.push({href: a.href, title: (title || '').trim(), channel: ch ? ch.innerText.trim() : null, channel_url: ch ? ch.href : null,
              meta: ((el.querySelector('#metadata-line') || {}).innerText || '').trim(),
              snippet: (el.innerText || '').replace(/\s+\n/g, '\n').trim().slice(0, 600),
              shorts: a.href.includes('/shorts/')});
  }
  return out;
}
"""


def terms(config: dict) -> list[str]:
    seen, out = set(), []
    for g in config["keyword_groups"]:
        for t in g["terms"] + g.get("weak_terms", []):
            for q in (t, strip_accents(t)):
                if q.lower() not in seen:
                    seen.add(q.lower())
                    out.append(q)
    return out


def main(argv=None) -> int:
    setup_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("yt_dir")
    ap.add_argument("--scrolls", type=int, default=15)
    ap.add_argument("--max-queries", type=int, default=0, help="thử nhanh: dừng sau N lượt tìm")
    args = ap.parse_args(argv)
    yt = Path(args.yt_dir)
    yt.mkdir(parents=True, exist_ok=True)
    config = Project().load_config()
    cand_f, log_f = yt / "candidates.jsonl", yt / "discover_log.jsonl"
    known = {json.loads(l)["video_id"] for l in cand_f.read_text(encoding="utf-8").splitlines() if l.strip()} \
        if cand_f.exists() else set()
    done = {(e["query"], e["order"]) for e in (json.loads(l) for l in log_f.read_text(encoding="utf-8").splitlines() if l.strip())} \
        if log_f.exists() else set()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 1000}, locale="vi-VN", user_agent=UA)
        page = ctx.new_page()
        ran = 0
        for q in terms(config):
            for order, sp in ORDERS.items():
                if (q, order) in done or (args.max_queries and ran >= args.max_queries):
                    continue
                ran += 1
                at = time.strftime("%Y-%m-%dT%H:%M:%S+07:00")
                url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(q)}&hl=vi&gl=VN" + (f"&sp={sp}" if sp else "")
                entry = {"engine": "youtube", "query": q, "order": order, "at": at, "url": url}
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(random.randint(3000, 4500))
                    if any(b in page.evaluate("document.body.innerText.slice(0, 3000)").lower() for b in BLOCK):
                        entry["error"] = "blocked"
                        log_f.open("a", encoding="utf-8").write(json.dumps(entry, ensure_ascii=False) + "\n")
                        print(json.dumps({"status": "blocked", "query": q}, ensure_ascii=False))
                        return 3
                    last, stall = 0, 0
                    for _ in range(args.scrolls):
                        page.mouse.wheel(0, 4000)
                        page.wait_for_timeout(random.randint(1500, 2500))
                        n = page.locator("ytd-video-renderer, ytm-shorts-lockup-view-model, yt-lockup-view-model").count()
                        stall = stall + 1 if n <= last else 0
                        last = max(last, n)
                        if stall >= 2 or page.locator("ytd-message-renderer, #message").filter(has_text=re.compile("Không có kết quả|No more results")).count():
                            break
                    rows = page.evaluate(RESULTS)
                except Exception as exc:
                    entry["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
                    log_f.open("a", encoding="utf-8").write(json.dumps(entry, ensure_ascii=False) + "\n")
                    continue
                seen_ids, new = set(), 0
                with cand_f.open("a", encoding="utf-8") as f:
                    for r in rows:
                        m = VID.search(r["href"])
                        if not m or m.group(1) in seen_ids:
                            continue
                        vid = m.group(1)
                        seen_ids.add(vid)
                        matched, lacking = match_keywords(f"{r['title']}\n{r['snippet']}\n{r.get('channel') or ''}", config)
                        if vid in known or not (matched or lacking):
                            continue
                        known.add(vid)
                        new += 1
                        f.write(json.dumps({"video_id": vid, "url": f"https://www.youtube.com/watch?v={vid}", **r,
                                            "keywords": matched, "lacking_context": lacking, "query": q, "order": order,
                                            "found_at": at}, ensure_ascii=False) + "\n")
                entry.update(results=len(seen_ids), new=new, reached_end=stall >= 2)
                log_f.open("a", encoding="utf-8").write(json.dumps(entry, ensure_ascii=False) + "\n")
                print(json.dumps({"query": q, "order": order, "results": len(seen_ids), "new": new}, ensure_ascii=False), flush=True)
                page.wait_for_timeout(random.randint(3000, 6000))
        browser.close()
    print(json.dumps({"status": "ok", "candidates": len(known)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
