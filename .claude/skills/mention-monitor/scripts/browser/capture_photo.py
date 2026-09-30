"""Open a Facebook photo URL and screenshot only the photo itself (2x), nothing of the page around it. Read-only.

python capture_photo.py <photo_url> <out.png>
"""
import base64
import json
import sys

from playwright.sync_api import sync_playwright

LARGEST_IMAGE = r"""
() => {
  const im = [...document.querySelectorAll('img')].filter(i => i.naturalWidth > 300 && i.getClientRects().length)
    .sort((a, b) => b.getBoundingClientRect().height * b.getBoundingClientRect().width
                  - a.getBoundingClientRect().height * a.getBoundingClientRect().width)[0];
  if (!im) return null;
  const r = im.getBoundingClientRect();
  const x = Math.max(0, r.left), y = Math.max(0, r.top);
  return {x, y, width: Math.min(r.right, innerWidth) - x, height: Math.min(r.bottom, innerHeight) - y,
          natural: [im.naturalWidth, im.naturalHeight], alt: im.alt};
}
"""


def main(url, out):
    sys.stdout.reconfigure(encoding="utf-8")
    with sync_playwright() as pw:
        b = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
        p = [q for q in b.contexts[0].pages if not q.url.startswith("devtools")][-1]
        p.bring_to_front()
        p.goto(url, wait_until="domcontentloaded", timeout=60000)
        p.wait_for_timeout(4000)
        box = p.evaluate(LARGEST_IMAGE)
        if not box:
            raise RuntimeError("không thấy ảnh trên trang")
        clip = {k: box[k] for k in ("x", "y", "width", "height")}
        data = b.contexts[0].new_cdp_session(p).send("Page.captureScreenshot",
                                                     {"format": "png", "clip": {**clip, "scale": 2}})["data"]
        open(out, "wb").write(base64.b64decode(data))
        print(json.dumps({"file": out, **box}, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
