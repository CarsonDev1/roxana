"""Smoke test for the local web viewer (not collected by pytest — needs `npm run start` in web/).

python tests/smoke_web.py [--base http://127.0.0.1:3000] [--shots <dir>]
Opens every page in headless Chrome, fails on HTTP errors, console errors, page errors or broken images.
"""
import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:3000")
    ap.add_argument("--shots")
    args = ap.parse_args(argv)
    data = json.loads((ROOT / "output" / "site" / "data.json").read_text(encoding="utf-8"))
    pages = ["/", "/bai-viet", "/binh-luan", "/dong-thoi-gian", "/bang-chung", "/nguoi", "/nhom", "/nhat-ky",
             "/chu-thich", "/bai-viet?importance=cao", "/bai-viet?q=ngoc%20lien"]
    pages += [f"/bai-viet/{s['id']}" for s in data["sources"][:3]]
    pages += [f"/bai-viet/{s['id']}" for s in data["sources"] if s.get("comments_collected")]
    superseded = [s["supersedes"] for s in data["sources"] if s.get("supersedes")]
    failures = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        for dark in (False,):  # web chỉ có chế độ sáng
            page = browser.new_page(viewport={"width": 1366, "height": 900}, color_scheme="dark" if dark else "light")
            errors = []
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            for path in (pages if not dark else pages[:4]):
                errors.clear()
                resp = page.goto(args.base + path, wait_until="networkidle")
                broken = page.evaluate("[...document.images].filter(i => i.complete && i.naturalWidth === 0).map(i => i.src)")
                status = resp.status if resp else 0
                if status >= 400 or errors or broken:
                    failures.append({"path": path, "dark": dark, "status": status, "errors": errors[:3], "broken": broken[:3]})
                if args.shots:
                    name = (path.strip("/").replace("/", "_").replace("?", "_") or "home") + ("_dark" if dark else "")
                    page.screenshot(path=str(Path(args.shots) / f"{name}.png"), full_page=True)
            page.close()
        page = browser.new_page()
        with_images = [s["id"] for s in data["sources"] if s.get("main_image")]
        if with_images:  # bấm ảnh → khung xem ngay trên trang, không mở tab mới; Esc đóng
            page.goto(f"{args.base}/bai-viet/{with_images[0]}", wait_until="networkidle")
            tabs = len(browser.contexts[0].pages) if browser.contexts else 1
            btn = page.get_by_role("button", name="Xem ảnh lớn").first
            btn.focus(); page.keyboard.press("Enter")
            dialog = page.locator("dialog[open]")
            ok = dialog.count() == 1
            if ok:  # ảnh gốc có thể dài hàng nghìn px — chờ tải xong
                page.wait_for_function("() => { const i = document.querySelector('dialog[open] img'); return i && i.complete && i.naturalWidth > 0; }", timeout=30000)
            page.keyboard.press("Escape")
            if not ok or page.locator("dialog[open]").count() or len(browser.contexts[0].pages) != tabs:
                failures.append({"path": "image viewer", "error": "khung xem ảnh không mở/đóng đúng"})
            font = page.evaluate("getComputedStyle(document.body).fontFamily")
            if "inter" not in font.lower():
                failures.append({"path": "font", "error": font})
        for sid in superseded:  # bản từ file cũ đã bị thay → chuyển sang bản quét
            page.goto(f"{args.base}/bai-viet/{sid}", wait_until="networkidle")
            if f"/bai-viet/{sid}" in page.url:
                failures.append({"path": f"/bai-viet/{sid}", "error": "không chuyển sang bản quét thay thế"})
        for bad in ("../config.json", "data/records.jsonl", "output/site/data.json", "screenshots/../config.json"):
            if page.request.get(f"{args.base}/api/file?path={bad}").status != 404:
                failures.append({"path": f"/api/file?path={bad}", "error": "phải trả 404"})
        browser.close()
    print(json.dumps({"pages": len(pages), "failures": failures}, ensure_ascii=False, indent=1))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
