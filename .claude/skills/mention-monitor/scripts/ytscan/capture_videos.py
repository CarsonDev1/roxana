"""Capture YouTube videos (candidates.jsonl from discover.py) with every comment — headless Chrome, no login, read-only.

python capture_videos.py <yt_dir> [--max N] [--max-comments N]

Per video, <yt_dir>/bundles/<video id>/:
- video_NN.png: the player + title, channel, date, views and the expanded description only (site header hidden)
- video.txt: title + full description · meta.json: id, link, channel, exact publish time, views, likes, length, relevance
- comments.json: every comment and reply (id, author, channel link, text with emoji, time shown, likes, parent)
- cscroll_NN.png: the comment column scrolled step by step; log.json lists which comment ids each image shows
Not about the case (title/description/tags) → meta.json {"relevant": false}, nothing else. Resumable; a captcha or
"unusual traffic" page stops the run (exit 3).
"""
from __future__ import annotations

import argparse
import base64
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import TZ, Project, match_keywords, setup_stdout  # noqa: E402

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0 Safari/537.36"
BLOCK = ("unusual traffic", "lưu lượng truy cập bất thường", "not a robot")
MAX_PART = 5000
HIDE = "#masthead-container, ytd-popup-container, tp-yt-iron-overlay-backdrop {visibility: hidden !important}"

PLAYER = r"""
() => {
  const r = window.ytInitialPlayerResponse || {}, v = r.videoDetails || {}, m = (r.microformat || {}).playerMicroformatRenderer || {};
  const like = [...document.querySelectorAll('like-button-view-model button, #segmented-like-button button')]
      .map(b => b.getAttribute('aria-label') || '').find(Boolean) || null;
  return {id: v.videoId, title: v.title, channel: v.author, channel_id: v.channelId, description: v.shortDescription || '',
          views: v.viewCount ? +v.viewCount : null, length_s: v.lengthSeconds ? +v.lengthSeconds : null, tags: v.keywords || [],
          published: m.publishDate || m.uploadDate || null, channel_url: m.ownerProfileUrl || null, category: m.category || null,
          live: !!v.isLiveContent, like_label: like, playable: (r.playabilityStatus || {}).status || null};
}
"""

# Chữ bình luận gồm cả emoji (YouTube vẽ emoji bằng <img alt>)
READ = r"""
() => {
  const txt = (el) => { if (!el) return ''; const c = el.cloneNode(true); c.querySelectorAll('img').forEach(i => i.replaceWith(i.alt || ''));
                        return c.innerText.trim(); };
  const out = [], seen = new Set();
  for (const c of document.querySelectorAll('ytd-comment-view-model, ytd-comment-renderer')) {
    const t = c.querySelector('#published-time-text a, .published-time-text a');
    const id = t ? new URL(t.href).searchParams.get('lc') : null;
    if (!id || seen.has(id)) continue;  // phản hồi có mã dạng "<mã bình luận gốc>.<mã phản hồi>"
    seen.add(id);
    const a = c.querySelector('#author-text');
    out.push({yt_comment_id: id, author: a ? a.innerText.trim() : null, author_href: a ? a.href : null,
              text: txt(c.querySelector('#content-text')), time_text: t ? t.innerText.trim() : null,
              likes: ((c.querySelector('#vote-count-middle') || {}).innerText || '').trim() || '0',
              is_reply: id.includes('.'), parent_yt_comment_id: id.includes('.') ? id.split('.')[0] : null,
              pinned: !!c.querySelector('#pinned-comment-badge ytd-pinned-comment-badge-renderer'),
              by_owner: !!c.querySelector('#author-comment-badge ytd-author-comment-badge-renderer')});
  }
  return out;
}
"""

VISIBLE = r"""
(top) => [...document.querySelectorAll('ytd-comment-view-model, ytd-comment-renderer')].filter(c => {
  const r = c.getBoundingClientRect(); return r.height > 0 && r.top >= top - 2 && r.top < innerHeight - 20;
}).map(c => { const t = c.querySelector('#published-time-text a, .published-time-text a'); return t ? new URL(t.href).searchParams.get('lc') : null; })
  .filter(Boolean)
"""


def _iso(s: str | None) -> str | None:
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:  # chỉ có ngày
        return None
    return d.astimezone(TZ).isoformat(timespec="seconds")


def shoot(cdp, out: Path, prefix: str, x: float, y: float, w: float, h: float) -> list[dict]:
    parts, n, end = [], 0, y + h
    while y < end and n < 20:
        hh = min(MAX_PART, end - y)
        n += 1
        f = out / f"{prefix}_{n:02d}.png"
        data = cdp.send("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True,
                                                   "clip": {"x": x, "y": y, "width": w, "height": hh, "scale": 1}})["data"]
        f.write_bytes(base64.b64decode(data))
        parts.append({"shot": f.name, "at": time.strftime("%H:%M:%S")})
        y += hh
    return parts


def load_comments(page, limit: int) -> dict:
    """Cuộn tới cuối phần bình luận và mở mọi nhánh phản hồi."""
    page.evaluate("document.querySelector('#comments') && document.querySelector('#comments').scrollIntoView()")
    page.wait_for_timeout(3000)
    if not page.locator("ytd-comments-header-renderer").count():
        page.mouse.wheel(0, 1200)
        page.wait_for_timeout(3000)
    header = page.evaluate("(document.querySelector('ytd-comments-header-renderer #count') || {}).innerText || null")
    disabled = page.evaluate("!!document.querySelector('ytd-comments #message, ytd-message-renderer') "
                             "&& /tắt bình luận|turned off/i.test(document.querySelector('ytd-comments').innerText)")
    last, stall = 0, 0
    while stall < 4:
        page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
        page.wait_for_timeout(random.randint(1800, 2800))
        n = page.locator("ytd-comment-thread-renderer").count()
        stall = stall + 1 if n <= last else 0
        last = max(last, n)
        if n >= limit:
            break
    clicks = 0
    # Nút "N phản hồi" chỉ hiện khi bình luận nằm trong màn hình: đưa từng bình luận có nút vào giữa màn hình rồi bấm
    for _ in range(30):
        pressed = 0
        for i in range(page.locator("ytd-comment-thread-renderer").count()):
            has = page.evaluate(r"""(i) => {
              const th = document.querySelectorAll('ytd-comment-thread-renderer')[i];
              if (!th || !th.querySelector('#more-replies, #more-replies-sub-thread, ytd-continuation-item-renderer')) return false;
              th.scrollIntoView({block: 'center'});
              return true;
            }""", i)
            if not has:
                continue
            page.wait_for_timeout(400)
            k = page.evaluate(r"""(i) => {
              const th = document.querySelectorAll('ytd-comment-thread-renderer')[i];
              const btns = [...th.querySelectorAll('button')].filter(b => {
                const host = b.closest('#more-replies, #more-replies-sub-thread, ytd-continuation-item-renderer');
                const t = (b.innerText || b.getAttribute('aria-label') || '').trim();
                return host && b.offsetParent !== null && /phản hồi|replies|Hiện thêm|Show more/i.test(t) && !/^Ẩn|^Hide/i.test(t)
                       && !b.dataset.mmClicked;
              });
              btns.forEach(b => { b.dataset.mmClicked = '1'; b.click(); });
              return btns.length;
            }""", i)
            if k:
                pressed += k
                page.wait_for_timeout(random.randint(1500, 2200))
        clicks += pressed
        if not pressed or clicks > 800:
            break
    return {"count_shown": header, "threads": last, "reply_clicks": clicks, "comments_disabled": bool(disabled)}


def main(argv=None) -> int:
    setup_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("yt_dir")
    ap.add_argument("--max", type=int, default=0)
    ap.add_argument("--max-comments", type=int, default=1500)
    args = ap.parse_args(argv)
    yt = Path(args.yt_dir)
    config = Project().load_config()
    cands = [json.loads(l) for l in (yt / "candidates.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    root = yt / "bundles"
    done = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 1000}, locale="vi-VN", user_agent=UA)
        page = ctx.new_page()
        cdp = ctx.new_cdp_session(page)
        for c in cands:
            out = root / c["video_id"]
            if (out / "meta.json").exists():
                continue
            started = time.strftime("%Y-%m-%dT%H:%M:%S+07:00")
            try:
                page.goto(f"https://www.youtube.com/watch?v={c['video_id']}&hl=vi&gl=VN", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(random.randint(4000, 5500))
                if any(b in page.evaluate("document.body.innerText.slice(0, 3000)").lower() for b in BLOCK):
                    print(json.dumps({"status": "blocked", "video": c["video_id"]}, ensure_ascii=False))
                    return 3
                info = page.evaluate(PLAYER)
            except Exception as exc:
                print(json.dumps({"video": c["video_id"], "error": f"{type(exc).__name__}: {str(exc)[:160]}"}, ensure_ascii=False))
                continue
            try:
                out.mkdir(parents=True, exist_ok=True)
                text = f"{info.get('title') or ''}\n\n{info.get('description') or ''}".strip()
                matched, lacking = match_keywords(f"{text}\n{' '.join(info.get('tags') or [])}", config)
                meta = {"video_id": c["video_id"], "url": f"https://www.youtube.com/watch?v={c['video_id']}", "shorts": c.get("shorts"),
                        **{k: info.get(k) for k in ("title", "channel", "channel_id", "channel_url", "views", "length_s", "tags",
                                                    "category", "live", "like_label", "playable")},
                        "published_raw": info.get("published"), "published": _iso(info.get("published")),
                        "candidate": c, "captured_at": started, "keywords": matched, "lacking_context": lacking,
                        "relevant": bool(matched) and info.get("playable") == "OK"}
                if not meta["relevant"]:
                    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
                    done += 1
                    continue
                (out / "video.txt").write_text(text, encoding="utf-8")
                page.add_style_tag(content=HIDE)
                page.evaluate("document.querySelector('video') && document.querySelector('video').pause()")
                for sel in ("ytd-watch-metadata #description-inline-expander #expand", "ytd-text-inline-expander #expand"):
                    try:
                        if page.locator(sel).first.is_visible():
                            page.locator(sel).first.click(timeout=3000)
                            page.wait_for_timeout(1200)
                            break
                    except Exception:
                        pass
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(800)
                reg = page.evaluate("""() => { const p = document.querySelector('#player-container-outer, #player') , m = document.querySelector('ytd-watch-metadata');
                    const a = p.getBoundingClientRect(), b = m.getBoundingClientRect();
                    return {x: Math.min(a.left, b.left) - 4 + scrollX, y: a.top + scrollY - 4, w: Math.max(a.right, b.right) - Math.min(a.left, b.left) + 8,
                            h: b.bottom - a.top + 8}; }""")
                steps = [{"kind": "post", "shows": f"Video — khung phát, tiêu đề, kênh, ngày đăng, mô tả (phần {i}/{{n}})", **s}
                         for i, s in enumerate(shoot(cdp, out, "video", reg["x"], reg["y"], reg["w"], reg["h"]), 1)]
                for s in steps:
                    s["shows"] = s["shows"].replace("{n}", str(len(steps)))
                cinfo = load_comments(page, args.max_comments)
                # bình luận dài bị rút gọn ("Đọc thêm") → mở hết để ảnh chụp có đủ chữ
                page.evaluate("""() => document.querySelectorAll('ytd-comment-view-model #more, ytd-comment-renderer #more, '
                    + 'ytd-comment-view-model ytd-expander tp-yt-paper-button#more').forEach(b => {
                      if (b.offsetParent !== null && !b.hidden) b.click(); })""")
                page.wait_for_timeout(1000)
                comments = page.evaluate(READ)
                # ảnh cuộn cột bình luận: mỗi ảnh một khung màn hình, ghi lại bình luận nào nằm trong ảnh
                box = page.evaluate("(() => { const r = document.querySelector('#comments').getBoundingClientRect(); "
                                    "return {x: r.left + scrollX, top: r.top + scrollY, bottom: r.bottom + scrollY, w: r.width}; })()")
                vh = page.evaluate("innerHeight")
                y, n, last_sy = box["top"], 0, -1
                while y < box["bottom"] and n < 400 and comments:
                    page.evaluate(f"window.scrollTo(0, {y})")
                    page.wait_for_timeout(600)
                    sy = page.evaluate("scrollY")
                    ids = page.evaluate(VISIBLE, 0)
                    n += 1
                    f = out / f"cscroll_{n:02d}.png"
                    h = min(vh, box["bottom"] - sy)
                    data = cdp.send("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False,
                                                              "clip": {"x": box["x"] - 4, "y": sy, "width": box["w"] + 8,
                                                                       "height": max(min(h, vh), 50), "scale": 1}})["data"]
                    f.write_bytes(base64.b64decode(data))
                    steps.append({"kind": "cscroll", "shot": f.name, "at": time.strftime("%H:%M:%S"), "comments": ids,
                                  "shows": f"Bình luận — ảnh cuộn {n}"})
                    if sy + vh >= box["bottom"] or sy <= last_sy:  # hết cột bình luận, hoặc trang không cuộn thêm được
                        break
                    last_sy = sy
                    y = sy + vh - 80
                for s in steps:
                    if s["kind"] == "cscroll":
                        s["shows"] = s["shows"] + f"/{n}"
                (out / "comments.json").write_text(json.dumps(comments, ensure_ascii=False, indent=1), encoding="utf-8")
                (out / "log.json").write_text(json.dumps({"started_at": started, "ended_at": time.strftime("%Y-%m-%dT%H:%M:%S+07:00"),
                                                          "steps": steps, **cinfo, "comments_read": len(comments)},
                                                         ensure_ascii=False, indent=1), encoding="utf-8")
                meta["shots"] = [s["shot"] for s in steps if s["kind"] == "post"]
                (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
                done += 1
                print(json.dumps({"done": done, "video": c["video_id"], "title": (info.get("title") or "")[:70],
                                  "comments": len(comments), "shown": cinfo["count_shown"]}, ensure_ascii=False), flush=True)
            except Exception as exc:  # một video lỗi → ghi lại, sang video sau (lần chạy sau thử lại)
                print(json.dumps({"video": c["video_id"], "error": f"{type(exc).__name__}: {str(exc)[:160]}"}, ensure_ascii=False), flush=True)
                if (out / "meta.json").exists() and not json.loads((out / "meta.json").read_text(encoding="utf-8")).get("relevant"):
                    pass
                else:
                    (out / "meta.json").unlink(missing_ok=True)
                continue
            if args.max and done >= args.max:
                break
            page.wait_for_timeout(random.randint(3000, 6000))
        browser.close()
    print(json.dumps({"status": "ok", "done": done}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
