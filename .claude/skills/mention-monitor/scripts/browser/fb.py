"""Tiny read-only driver for the Chrome window opened with --remote-debugging-port=9222 (Playwright over CDP).

Usage: python fb.py <cmd> [args]
  status                      url + title of the active tab
  goto <url>                  navigate the active tab, wait for load
  shot <out.png> [full]       screenshot of the viewport (or full page)
  clip <out.png> x y w h      screenshot of a region (CSS px)
  text <out.txt>              document.body.innerText
  js <file.js> [out]          evaluate a read-only JS expression file, print/save JSON result
  hover x y | click x y       mouse at CSS px (click only for UI toggles: "Xem thêm", comment filter)
  clicktext "<text>" [n]      click the n-th (default 1) visible element whose text is exactly <text>
  scroll <dy> | wait <sec>    wheel scroll / sleep
"""
import base64
import json
import sys
import time

from playwright.sync_api import sync_playwright


def page_of(browser):
    ctx = browser.contexts[0]
    pages = [p for p in ctx.pages if not p.url.startswith("devtools://")]
    return pages[-1]


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8")
    cmd, args = argv[0], argv[1:]
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = page_of(browser)
        page.bring_to_front()
        if cmd == "status":
            print(json.dumps({"url": page.url, "title": page.title(),
                              "viewport": page.evaluate("[innerWidth, innerHeight, scrollY]")}, ensure_ascii=False))
        elif cmd == "goto":
            page.goto(args[0], wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)
            print(page.url)
        elif cmd in ("shot", "clip"):
            # Page.screenshot của Playwright bị treo với Facebook qua CDP; gọi thẳng Page.captureScreenshot.
            params = {"format": "png"}
            if cmd == "clip":
                x, y, w, h = map(float, args[1:5])
                params["clip"] = {"x": x, "y": y, "width": w, "height": h, "scale": float(args[5]) if len(args) > 5 else 1}
            data = browser.contexts[0].new_cdp_session(page).send("Page.captureScreenshot", params)["data"]
            with open(args[0], "wb") as f:
                f.write(base64.b64decode(data))
            print(args[0])
        elif cmd == "text":
            with open(args[0], "w", encoding="utf-8") as f:
                f.write(page.evaluate("document.body.innerText"))
            print(args[0])
        elif cmd == "js":
            result = page.evaluate(open(args[0], encoding="utf-8").read())
            out = json.dumps(result, ensure_ascii=False, indent=1)
            if len(args) > 1:
                open(args[1], "w", encoding="utf-8").write(out)
                print(args[1])
            else:
                print(out)
        elif cmd == "hover":
            page.mouse.move(float(args[0]), float(args[1]))
            page.wait_for_timeout(1500)
        elif cmd == "click":
            page.mouse.click(float(args[0]), float(args[1]))
            page.wait_for_timeout(2000)
        elif cmd == "clicktext":
            n = int(args[1]) if len(args) > 1 else 1
            loc = page.get_by_text(args[0], exact=True).locator("visible=true").nth(n - 1)
            loc.click(timeout=5000)
            page.wait_for_timeout(2000)
        elif cmd == "scroll":
            page.mouse.wheel(0, float(args[0]))
            page.wait_for_timeout(1500)
        elif cmd == "wait":
            time.sleep(float(args[0]))


if __name__ == "__main__":
    main(sys.argv[1:])
