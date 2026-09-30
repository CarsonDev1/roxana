"""Capture every post listed in one or more feed files (from collect_feed.py) into per-post bundles.

python capture_batch.py <bundles_dir> <feed.jsonl> [<feed.jsonl> ...] [--max N]

Per post, bundles_dir/<post-key>/ gets: post/cscroll screenshots (post area only), snapshot text, comments.json,
times.json (exact comment times from tooltips), attach_NN.png for images Facebook labels as text/documents,
feed.json (the feed line) and log.json. A bundle with log.json is complete and skipped on re-run.
Read-only; waits 3–8 s between posts; exit code 3 on any block/checkpoint/login signal.
"""
import argparse
import base64
import json
import random
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capture_post import capture  # noqa: E402
from capture_photo import LARGEST_IMAGE  # noqa: E402
from collect_feed import blocked  # noqa: E402

DOC_ALT = re.compile(r"văn bản|text|tài liệu|document|giấy|biên bản|thông báo", re.I)


def key_of(permalink: str) -> str:
    m = re.search(r"/(?:posts|permalink)/(\d+)", permalink) or re.search(r"fbid=(\d+)", permalink) \
        or re.search(r"/posts/([\w]+)", permalink) or re.search(r"(\d{8,})", permalink)
    return (m.group(1) if m else re.sub(r"\W+", "_", permalink))[-60:]


def comment_times(p) -> list[dict]:
    dialog = p.locator('[role="dialog"]').filter(has=p.locator('div[role="article"]')).last
    links = dialog.locator('div[role="article"] a[href*="comment_id="]')
    out = []
    for i in range(links.count()):
        a = links.nth(i)
        try:
            label = a.inner_text().strip()
            if not a.is_visible() or not re.match(r"^\d+\s*(giây|phút|giờ|ngày|tuần|tháng|năm)|^Vừa xong", label):
                continue
            a.scroll_into_view_if_needed(timeout=3000)
            a.hover(timeout=3000)
            tip = None
            for _ in range(6):  # tooltip đôi khi hiện chậm
                p.wait_for_timeout(600)
                tip = p.evaluate("[...document.querySelectorAll('[role=tooltip]')].map(e=>e.innerText.trim()).filter(Boolean).pop() || null")
                if tip:
                    break
            href = a.get_attribute("href") or ""
            cid = (re.search(r"[?&]comment_id=(\d+)", href) or [None, None])[1]
            rid = (re.search(r"reply_comment_id=(\d+)", href) or [None, None])[1]
            out.append({"label": label, "fb_comment_id": rid or cid, "tooltip": tip})
            p.mouse.move(5, 5)
            p.wait_for_timeout(250)
        except Exception:
            continue
    return out


def shoot_photos(b, p, media: list[str], alts: list[str], out_dir: Path) -> list[dict]:
    """Ảnh đính kèm Facebook gắn nhãn là văn bản/tài liệu → chụp riêng ảnh (2x) để chép chữ."""
    shots = []
    photos = [m for m in media if "/photo" in m]
    if not photos or not any(DOC_ALT.search(a or "") for a in alts):
        return shots
    cdp = b.contexts[0].new_cdp_session(p)
    for i, url in enumerate(photos[:12], 1):
        try:
            p.goto(url, wait_until="domcontentloaded", timeout=60000)
            p.wait_for_timeout(random.randint(3000, 5000))
            box = p.evaluate(LARGEST_IMAGE)
            if not box:
                continue
            clip = {k: box[k] for k in ("x", "y", "width", "height")}
            path = out_dir / f"attach_{i:02d}.png"
            data = cdp.send("Page.captureScreenshot", {"format": "png", "clip": {**clip, "scale": 2}})["data"]
            path.write_bytes(base64.b64decode(data))
            shots.append({"file": str(path), "url": url, "alt": box.get("alt"), "at": time.strftime("%H:%M:%S")})
        except Exception as exc:
            shots.append({"url": url, "error": str(exc)[:200]})
    return shots


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("bundles")
    ap.add_argument("feeds", nargs="+")
    ap.add_argument("--max", type=int, default=0)
    args = ap.parse_args(argv)
    root = Path(args.bundles)
    items = []
    for f in args.feeds:
        for line in Path(f).read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                d["feed_file"] = f
                items.append(d)
    todo = [d for d in items if "#pos" not in d["permalink"] and not (root / key_of(d["permalink"]) / "log.json").exists()]
    done = 0
    with sync_playwright() as pw:
        b = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
        p = [q for q in b.contexts[0].pages if not q.url.startswith("devtools")][-1]
        p.bring_to_front()
        for d in todo:
            out = root / key_of(d["permalink"])
            out.mkdir(parents=True, exist_ok=True)
            (out / "feed.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            try:
                p.goto(d["permalink"], wait_until="domcontentloaded", timeout=60000)
                p.wait_for_timeout(random.randint(3500, 6000))
                if (why := blocked(p)):
                    print(json.dumps({"status": "blocked", "reason": why, "done": done}, ensure_ascii=False))
                    return 3
                unavailable = p.evaluate("/Nội dung này hiện không khả dụng|This content isn't available|Bạn hiện không xem được nội dung này/i.test(document.body.innerText)")
                if unavailable:
                    (out / "log.json").write_text(json.dumps({"unavailable": True, "url": p.url,
                        "at": time.strftime("%Y-%m-%dT%H:%M:%S+07:00")}, ensure_ascii=False), encoding="utf-8")
                    continue
                log = capture(b, p, str(out), "p")
                times = comment_times(p)
                (out / "times.json").write_text(json.dumps(times, ensure_ascii=False, indent=1), encoding="utf-8")
                log["attachments"] = shoot_photos(b, p, d.get("media") or [], d.get("image_alts") or [], out)
                log["times_read"] = sum(1 for t in times if t["tooltip"])
                (out / "log.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
            except Exception as exc:
                (out / "error.txt").write_text(f"{time.strftime('%H:%M:%S')} {type(exc).__name__}: {exc}", encoding="utf-8")
                if (why := blocked(p)):
                    print(json.dumps({"status": "blocked", "reason": why, "done": done}, ensure_ascii=False))
                    return 3
                continue
            done += 1
            print(json.dumps({"done": done, "of": len(todo), "key": out.name, "comments": log.get("comment_count"),
                              "times": log.get("times_read"), "attach": len(log.get("attachments") or [])},
                             ensure_ascii=False), flush=True)
            if args.max and done >= args.max:
                break
            p.wait_for_timeout(random.randint(3000, 8000))
    print(json.dumps({"status": "ok", "done": done, "remaining": len(todo) - done}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
