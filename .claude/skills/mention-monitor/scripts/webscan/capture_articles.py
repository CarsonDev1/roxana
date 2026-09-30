"""Capture web articles (candidates.jsonl from discover.py) into bundles — headless Chrome, no login, no Facebook.

python capture_articles.py <web_dir> [--max N]

Per article, <web_dir>/bundles/<key>/: article_01.png (title + article body only, 1x; tall pages split into parts),
article.txt (full text), article.html (page source), meta.json (final/canonical url, title, site, author,
published, relevance). Not about the case → meta.json {"relevant": false} (kept as a record of what was checked).
Resumable; 3–7 s between pages; a captcha/anti-bot page stops the run (exit 3).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import random
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import Project, match_keywords, normalize_url, setup_stdout  # noqa: E402

MAX_PART = 5000  # px — ảnh dài hơn thì chụp thành nhiều phần liên tiếp

EXTRACT = r"""
() => {
  const meta = (sel) => { const e = document.querySelector(sel); return e ? (e.content || e.getAttribute('content') || e.innerText || '').trim() : null; };
  let ld = null;
  for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
    try { const j = JSON.parse(s.textContent); const arr = Array.isArray(j) ? j : (j['@graph'] || [j]);
      ld = arr.find(x => /Article|NewsArticle|BlogPosting/i.test(x['@type'] || '')) || ld; } catch (e) {}
  }
  // Khối nội dung: chấm điểm cha/ông của mỗi đoạn văn theo độ dài chữ (kiểu Readability), lấy khối điểm cao nhất.
  const score = new Map();
  const outside = (p) => { // đoạn nằm trong khối phụ (cột bên, tin liên quan, bình luận, menu, chân trang)
    for (let e = p.parentElement; e && e !== document.body; e = e.parentElement) {
      if (e.matches('aside, nav, footer') || [...e.classList].some(c => /^(sidebar|side-bar|related|comment|box-comment|footer)/i.test(c))) return true;
    }
    return false;
  };
  for (const p of document.querySelectorAll('p, [itemprop="articleBody"] div')) {
    const t = p.innerText ? p.innerText.trim().length : 0;
    if (t < 40 || outside(p)) continue;
    const a = p.parentElement, b = a && a.parentElement;
    if (a) score.set(a, (score.get(a) || 0) + t);
    if (b) score.set(b, (score.get(b) || 0) + t / 2);
  }
  let body = document.body, best = 0;
  for (const [el, s] of score) if (s > best && el !== document.body) { best = s; body = el; }
  const h1s = [...document.querySelectorAll('h1')].filter(h => h.getClientRects().length);
  const br = body.getBoundingClientRect();
  const h1 = h1s.find(h => { const r = h.getBoundingClientRect(); return r.top <= br.top + 5 && br.top - r.bottom < 900 && r.right > br.left && r.left < br.right; })
          || h1s[0] || null;
  const top = h1 && h1.getBoundingClientRect().top < br.top ? h1 : body;
  const r1 = top.getBoundingClientRect(), r2 = body.getBoundingClientRect();
  // bề ngang theo khối nội dung (tiêu đề có thể trải hết trang); tiêu đề chỉ quyết định mép trên
  const left = Math.max(0, Math.min(r2.left, r1.width < r2.width * 1.4 ? r1.left : r2.left) - 8);
  const right = Math.min(document.documentElement.clientWidth, Math.max(r2.right, r1.width < r2.width * 1.4 ? r1.right : r2.right) + 8);
  const author = (ld && (Array.isArray(ld.author) ? ld.author.map(a => a.name).join(', ') : ld.author && ld.author.name))
    || meta('meta[name="author"]') || meta('meta[property="article:author"]') || null;
  return {
    canonical: (document.querySelector('link[rel="canonical"]') || {}).href || location.href, final: location.href,
    title: meta('meta[property="og:title"]') || (h1 && h1.innerText.trim()) || document.title,
    site: meta('meta[property="og:site_name"]') || location.hostname,
    author, published: (ld && ld.datePublished) || meta('meta[property="article:published_time"]') || meta('meta[itemprop="datePublished"]') || meta('time[datetime]') && document.querySelector('time[datetime]').getAttribute('datetime'),
    modified: (ld && ld.dateModified) || meta('meta[property="article:modified_time"]'),
    text: (h1 ? h1.innerText.trim() + '\n\n' : '') + body.innerText.trim(),
    region: {x: left, y: r1.top + scrollY - 8, width: right - left, height: r2.bottom - r1.top + 16},
    body_is_page: body === document.body,
  };
}
"""
BLOCK = ("captcha", "Just a moment", "Checking your browser", "Access denied", "unusual traffic")


def key_of(url: str) -> str:
    return hashlib.sha1(normalize_url(url).encode()).hexdigest()[:16]


def main(argv=None) -> int:
    setup_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("web_dir")
    ap.add_argument("--max", type=int, default=0)
    args = ap.parse_args(argv)
    web = Path(args.web_dir)
    config = Project().load_config()
    cands = [json.loads(l) for l in (web / "candidates.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    root = web / "bundles"
    index_f = web / "captured_index.json"  # link ứng viên → bundle (link Google News chuyển hướng khác link cuối)
    index = json.loads(index_f.read_text(encoding="utf-8")) if index_f.exists() else {}
    done = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 1000}, locale="vi-VN",
                                  user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0 Safari/537.36")
        page = ctx.new_page()
        cdp = ctx.new_cdp_session(page)
        for c in cands:
            if c["url"] in index:
                continue
            if "facebook.com" in c["url"]:
                index[c["url"]] = {"skipped": "facebook — thuộc luồng Facebook"}
                continue
            try:
                page.goto(c["url"], wait_until="domcontentloaded", timeout=60000)
                if "news.google.com" in page.url:  # trang chuyển hướng của Google News
                    page.wait_for_url(lambda u: "news.google.com" not in u, timeout=30000)
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_timeout(random.randint(2500, 4000))
                title = page.title()
                if any(b.lower() in (title + page.evaluate("document.body.innerText.slice(0,2000)")).lower() for b in BLOCK):
                    index[c["url"]] = {"blocked": page.url}
                    continue
                info = page.evaluate(EXTRACT)
            except Exception as exc:
                index[c["url"]] = {"error": f"{type(exc).__name__}: {str(exc)[:200]}"}
                index_f.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
                continue
            final = info["canonical"] or info["final"]
            key = key_of(final)
            out = root / key
            matched, lacking = match_keywords(f"{info['title']}\n{info['text']}", config)
            meta = {**info, "candidate": c, "key": key, "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S+07:00"),
                    "keywords": matched, "lacking_context": lacking, "relevant": bool(matched)}
            meta.pop("text")
            out.mkdir(parents=True, exist_ok=True)
            if matched and not (out / "meta.json").exists():
                (out / "article.txt").write_text(info["text"], encoding="utf-8")
                (out / "article.html").write_text(page.content(), encoding="utf-8")
                reg = info["region"]
                parts, y, n = [], reg["y"], 0
                while y < reg["y"] + reg["height"] and n < 20:
                    h = min(MAX_PART, reg["y"] + reg["height"] - y)
                    n += 1
                    shot = out / f"article_{n:02d}.png"
                    data = cdp.send("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True,
                                                              "clip": {"x": reg["x"], "y": y, "width": reg["width"], "height": h, "scale": 1}})["data"]
                    shot.write_bytes(base64.b64decode(data))
                    parts.append({"file": str(shot), "at": time.strftime("%H:%M:%S")})
                    y += h
                meta["shots"] = parts
            (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
            index[c["url"]] = {"key": key, "relevant": bool(matched)}
            index_f.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
            done += 1
            print(json.dumps({"done": done, "site": info["site"], "relevant": bool(matched), "title": info["title"][:80]},
                             ensure_ascii=False), flush=True)
            if args.max and done >= args.max:
                break
            page.wait_for_timeout(random.randint(3000, 7000))
        browser.close()
    print(json.dumps({"status": "ok", "done": done}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
