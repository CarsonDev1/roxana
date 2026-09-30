"""Walk a group/page feed (or a search result list) and list every post: permalink, exact time, author, snippet.

python collect_feed.py <url> <out.jsonl> [--max N] [--stop-known K --known <file with one url per line>]

Read-only: only scrolls and hovers (hovering the timestamp link is what makes Facebook reveal the permalink and
the exact-time tooltip). One JSON line per post is appended immediately, so an interrupted walk loses nothing.
Stops on: end of feed (no new posts after several scrolls), --max, K consecutive already-known posts,
or any block/checkpoint/login signal (exit code 3 — the caller must stop the run and tell the user).
"""
import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from window import own_window, request_stop, stop_requested  # noqa: E402

BLOCK_SIGNS = ("tạm thời bị chặn", "temporarily blocked", "checkpoint", "xác minh danh tính", "captcha",
               "Bạn đang đi quá nhanh", "You're going too fast", "Đăng nhập Facebook", "Log in to Facebook")
POST_RE = re.compile(r"/(?:groups/[^/]+/(?:posts|permalink)/\d+|permalink\.php\?|[^/?]+/posts/[^/?]+|photo/?\?fbid=|"
                     r"reel/\d+|watch/?\?v=|videos/\d+|share/)")

# Link riêng của BÀI (không phải của ảnh/reel bên trong bài)
PERMA_RE = re.compile(r"/groups/[^/]+/(?:posts|permalink)/\d+|/permalink\.php\?|facebook\.com/[^/?]+/posts/[^/?]+|/story\.php\?")
TIME_LINK_RE = re.compile(r"facebook\.com/(?:groups/[^/?]+/?|[^/?]+/?)\?__cft__")

HEADER = r"""
() => {
  const h1 = document.querySelector('h1');
  const txt = document.body.innerText;
  const privacy = /Nhóm Riêng tư|Private group/i.test(txt) ? 'private' : /Nhóm Công khai|Public group/i.test(txt) ? 'public' : 'unknown';
  const m = txt.match(/([\d.,]+\s*[KkNn]?)\s*(thành viên|members)/);
  const join = [...document.querySelectorAll('[role="button"]')].map(b => b.innerText.trim())
      .find(t => /^(Tham gia nhóm|Join group|Đã tham gia|Joined|Đã gửi yêu cầu|Hủy yêu cầu)$/.test(t)) || null;
  return {name: h1 ? h1.innerText.trim() : document.title, privacy, members: m ? m[1] : null, join_button: join};
}
"""

MESSAGE = r"""
(el) => {
  const msg = el.querySelector('[data-ad-rendering-role="story_message"], [data-ad-preview="message"], [data-ad-comet-preview="message"]');
  const author = [...el.querySelectorAll('a[href*="/user/"], h2 a, h3 a, h4 a')].map(a => a.innerText.trim()).find(Boolean) || null;
  const media = [...el.querySelectorAll('a[href]')].map(a => a.href)
      .filter(h => /\/photo\/?\?fbid=|\/reel\/|\/watch\/?\?v=|\/videos\//.test(h)).map(h => h.split('&__cft__')[0].split('?__cft__')[0]);
  const imgs = [...el.querySelectorAll('img')].filter(i => i.naturalWidth > 200).map(i => i.alt).filter(Boolean);
  return {author, message: msg ? msg.innerText.trim() : null, media: [...new Set(media)].slice(0, 20), image_alts: imgs.slice(0, 20),
          text: el.innerText.split('\n').filter(l => l.trim() && l.trim() !== 'Facebook').join('\n').slice(0, 4000)};
}
"""


def blocked(page) -> str | None:
    if "checkpoint" in page.url or "/login" in page.url:
        return page.url
    body = page.evaluate("document.body.innerText.slice(0, 5000)")
    return next((s for s in BLOCK_SIGNS if s.lower() in body.lower()), None)


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("out")
    ap.add_argument("--max", type=int, default=0)
    ap.add_argument("--stop-known", type=int, default=0)
    ap.add_argument("--known")
    ap.add_argument("--own-window", action="store_true", help="mở cửa sổ Chrome riêng (chạy song song)")
    ap.add_argument("--media-fallback", action="store_true", help="không có link bài thì lấy link video/ảnh")
    ap.add_argument("--items", help="CSS selector của từng mục (mặc định: tự nhận: div[aria-posinset] hoặc con của [role=feed])")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        done = {json.loads(l)["permalink"] for l in out.read_text(encoding="utf-8").splitlines() if l.strip()}
    known = set(Path(args.known).read_text(encoding="utf-8").split()) if args.known else set()
    started = time.strftime("%Y-%m-%dT%H:%M:%S+07:00")

    with sync_playwright() as pw:
        b = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
        if args.own_window:
            p, close_window = own_window(b)
        else:
            p, close_window = [q for q in b.contexts[0].pages if not q.url.startswith("devtools")][-1], (lambda: None)
            p.bring_to_front()
        p.goto(args.url, wait_until="domcontentloaded", timeout=60000)
        p.wait_for_timeout(5000)
        if (why := blocked(p)):
            request_stop(f"collect_feed {args.url}: {why}")
            print(json.dumps({"status": "blocked", "reason": why}, ensure_ascii=False)); close_window(); return 3
        meta = {"url": args.url, "started_at": started, **p.evaluate(HEADER)}
        (out.with_suffix(".meta.json")).write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

        sel = args.items or ("div[aria-posinset]" if p.locator("div[aria-posinset]").count()
                             else '[role="feed"] > div, [role="main"] div[role="article"]')
        processed, stall, new, known_run, last_count = set(), 0, 0, 0, 0
        reached_end = False
        with open(out, "a", encoding="utf-8") as f:
            while True:
                arts = p.locator(sel)
                n = arts.count()
                for i in range(n):
                    art = arts.nth(i)
                    pos = art.get_attribute("aria-posinset") or str(i + 1)
                    if not art.inner_text(timeout=2000).strip():
                        continue  # khung trống / đang tải
                    if pos in processed:
                        continue
                    processed.add(pos)
                    try:
                        art.scroll_into_view_if_needed(timeout=5000)
                    except Exception:
                        continue
                    p.wait_for_timeout(random.randint(500, 1100))
                    permalink, tooltip = None, None
                    links = art.locator("a[href]")
                    for j in range(min(links.count(), 60)):
                        a = links.nth(j)
                        try:
                            if not a.is_visible() or a.inner_text().strip():
                                continue
                            href = a.get_attribute("href") or ""
                            # Link mốc thời gian: chưa rê chuột thì là "?__cft__…", "#…" hoặc trang nhóm/trang
                            if not (href.startswith("?") or href.startswith("#") or TIME_LINK_RE.search(href)):
                                continue
                            a.hover(timeout=3000)
                            p.wait_for_timeout(1200)
                            href = a.get_attribute("href") or ""
                            if PERMA_RE.search(href):
                                permalink = href.split("?__cft__")[0].split("&__cft__")[0]
                                tooltip = p.evaluate("[...document.querySelectorAll('[role=tooltip]')].map(e=>e.innerText.trim()).filter(Boolean).pop() || null")
                                break
                        except Exception:
                            continue
                    p.mouse.move(5, 5)
                    if not permalink:  # dự phòng: mã bài nằm trong link bình luận xem trước hoặc link ảnh (set=gm./pcb.)
                        hrefs = art.evaluate("el => [...el.querySelectorAll('a[href]')].map(a => a.href)")
                        gid = re.search(r"/groups/([^/?#]+)", args.url)
                        for h in hrefs:
                            m = re.search(r"(https://www\.facebook\.com/groups/[^/]+/(?:posts|permalink)/\d+)/?\?(?:comment_id|reply)", h)
                            if m:
                                permalink = m.group(1) + "/"
                                break
                        if not permalink and gid:
                            for h in hrefs:
                                m = re.search(r"set=(?:gm|pcb)\.(\d+)", h)
                                if m:
                                    permalink = f"https://www.facebook.com/groups/{gid.group(1)}/posts/{m.group(1)}/"
                                    break
                    info = art.evaluate(MESSAGE)
                    if not permalink and args.media_fallback:
                        media = art.evaluate(r"el => [...el.querySelectorAll('a[href]')].map(a => a.href).find(h => /\/(reel|videos)\/|\/watch\/?\?v=|\/photo\/?\?fbid=/.test(h)) || null")
                        if media:
                            permalink = media.split("&__cft__")[0].split("?__cft__")[0]
                    if not permalink:
                        permalink = f"{args.url}#pos{pos}"  # không lấy được link riêng — ghi lại để xử lý tay
                    if permalink in done:
                        continue
                    if permalink in known:
                        known_run += 1
                        if args.stop_known and known_run >= args.stop_known:
                            break
                        continue
                    known_run = 0
                    done.add(permalink)
                    f.write(json.dumps({"pos": int(pos), "permalink": permalink, "tooltip": tooltip,
                                        "seen_at": time.strftime("%Y-%m-%dT%H:%M:%S+07:00"), **info},
                                       ensure_ascii=False) + "\n")
                    f.flush()
                    new += 1
                    if args.max and new >= args.max:
                        break
                if (args.max and new >= args.max) or (args.stop_known and known_run >= args.stop_known):
                    break
                if (why := blocked(p)):
                    request_stop(f"collect_feed {args.url}: {why}")
                    print(json.dumps({"status": "blocked", "reason": why, "new": new}, ensure_ascii=False)); close_window(); return 3
                if stop_requested():
                    print(json.dumps({"status": "stopped", "new": new}, ensure_ascii=False)); close_window(); return 3
                p.mouse.wheel(0, random.randint(1400, 2200))
                p.wait_for_timeout(random.randint(2500, 4500))
                count = p.locator(sel).count()
                last_pos = max((int(x) for x in processed), default=0)
                stall = stall + 1 if count <= last_count and last_pos >= count else 0
                last_count = max(last_count, count)
                end_text = p.evaluate("/Hết bài viết|Không còn bài viết|No more posts|End of results|Hết kết quả/i.test(document.body.innerText)")
                if stall >= 4 or end_text:
                    reached_end = True
                    break
        meta.update(ended_at=time.strftime("%Y-%m-%dT%H:%M:%S+07:00"), new=new, reached_end=reached_end,
                    posts_seen=len(processed))
        out.with_suffix(".meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({"status": "ok", **meta}, ensure_ascii=False))
        close_window()
    return 0


if __name__ == "__main__":
    sys.exit(main())
