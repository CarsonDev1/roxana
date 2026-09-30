"""Open a comment link (?comment_id=…) and screenshot only that comment's box (2x). Read-only.

python capture_comment.py <comment_url> <author_name> <out.png>
"""
import base64
import json
import sys

from playwright.sync_api import sync_playwright


def main(url, author, out):
    sys.stdout.reconfigure(encoding="utf-8")
    with sync_playwright() as pw:
        b = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
        p = [q for q in b.contexts[0].pages if not q.url.startswith("devtools")][-1]
        p.bring_to_front()
        p.goto(url, wait_until="domcontentloaded", timeout=60000)
        p.wait_for_timeout(4000)
        arts = [a for a in p.locator(f'[role="dialog"] div[role="article"][aria-label*="{author}"]').all() if a.is_visible()]
        if not arts:
            raise RuntimeError(f"không thấy bình luận của {author} trong khung bài")
        arts[0].scroll_into_view_if_needed()
        p.wait_for_timeout(1200)
        r = arts[0].bounding_box()
        # chỉ khung bình luận: ảnh đại diện + tên + nội dung + dòng Thích/Trả lời; không lấy phần ngoài khung bài
        d = p.locator('[role="dialog"]').last.bounding_box()
        x, y = max(r["x"], d["x"]), max(r["y"] - 4, d["y"])
        clip = {"x": x, "y": y, "width": min(r["x"] + r["width"], d["x"] + d["width"]) - x,
                "height": min(r["y"] + r["height"] + 4, d["y"] + d["height"]) - y}
        data = b.contexts[0].new_cdp_session(p).send("Page.captureScreenshot",
                                                     {"format": "png", "clip": {**clip, "scale": 2}})["data"]
        open(out, "wb").write(base64.b64decode(data))
        print(json.dumps({"file": out, "clip": clip}, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
