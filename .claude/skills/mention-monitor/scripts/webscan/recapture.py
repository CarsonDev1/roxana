"""Re-capture web bundles a classifier put on hold (cls.json {"hold": ...}) — closes consent/login pop-ups, waits for
the page to settle, then extracts and screenshots again with the same rules as capture_articles.py.

python recapture.py <bundles_dir> [<bundles_dir> ...]   (only bundles whose cls.json is a hold and not yet applied)

The earlier capture is kept in <bundle>/prev_<time>/; cls.json is moved there too, so the bundle goes back to the
classifiers. A page that still has no content (error page, "no results", maintenance) → meta.json relevant=false with
"recapture": {"result": "empty"} — kept as a record of what was checked.
"""
from __future__ import annotations

import base64
import json
import shutil
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from capture_articles import EXTRACT, MAX_PART  # noqa: E402
from common import Project, match_keywords, setup_stdout  # noqa: E402

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0 Safari/537.36"
# Bấm nút đồng ý/đóng của hộp thoại cookie, quyền riêng tư, mời đăng nhập; rồi gỡ lớp phủ cố định che nửa màn hình
DISMISS = r"""
() => {
  const re = /^(Đồng ý|Tôi đồng ý|Chấp nhận|Chấp nhận tất cả|Accept|Accept all|Agree|I agree|OK|Đóng|Close|Bỏ qua|Để sau|Không, cảm ơn|×|✕)$/i;
  let n = 0;
  for (const b of document.querySelectorAll('button, [role=button], a, span, div')) {
    const t = (b.innerText || b.getAttribute('aria-label') || '').trim();
    if (t.length <= 25 && re.test(t) && b.offsetParent !== null) { try { b.click(); n++; } catch (e) {} }
  }
  const vw = innerWidth * innerHeight;
  for (const e of document.querySelectorAll('body *')) {
    const s = getComputedStyle(e);
    if ((s.position === 'fixed' || s.position === 'sticky') && +s.zIndex > 10) {
      const r = e.getBoundingClientRect();
      if (r.width * r.height > vw * 0.3) { e.remove(); n++; }
    }
  }
  document.documentElement.style.overflow = 'auto'; document.body.style.overflow = 'auto';
  return n;
}
"""


def main(argv=None) -> int:
    setup_stdout()
    dirs = [Path(a) for a in (argv or sys.argv[1:])]
    config = Project().load_config()
    todo = []
    for root in dirs:
        for d in sorted(root.iterdir()):
            cf = d / "cls.json"
            if cf.exists() and not (d / "applied.json").exists() and json.loads(cf.read_text(encoding="utf-8")).get("hold"):
                todo.append(d)
    out = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 1000}, locale="vi-VN", user_agent=UA)
        for d in todo:
            meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
            url = meta.get("final") or meta.get("canonical")
            page = ctx.new_page()
            cdp = ctx.new_cdp_session(page)
            try:
                page.goto(url, wait_until="networkidle", timeout=90000)
            except Exception:
                pass  # trang còn tải ngầm (quảng cáo…) vẫn chụp được
            page.wait_for_timeout(4000)
            closed = page.evaluate(DISMISS)
            page.wait_for_timeout(2000)
            info = page.evaluate(EXTRACT)
            matched, lacking = match_keywords(f"{info['title']}\n{info['text']}", config)
            prev = d / f"prev_{time.strftime('%H%M%S')}"
            prev.mkdir()
            for f in list(d.iterdir()):
                if f.is_file() and (f.name.startswith("article") or f.name in ("cls.json", "meta.json")):
                    shutil.copy2(f, prev / f.name) if f.name == "meta.json" else shutil.move(str(f), str(prev / f.name))
            rec = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+07:00"), "closed_popups": closed, "prev": prev.name}
            if not matched or len(info["text"]) < 300:
                meta.update(relevant=False, recapture={**rec, "result": "empty", "text_len": len(info["text"])})
                (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
                out.append({"bundle": d.name, "result": "empty", "len": len(info["text"])})
                page.close()
                continue
            (d / "article.txt").write_text(info["text"], encoding="utf-8")
            (d / "article.html").write_text(page.content(), encoding="utf-8")
            reg, parts, y, n = info["region"], [], info["region"]["y"], 0
            while y < reg["y"] + reg["height"] and n < 20:
                h = min(MAX_PART, reg["y"] + reg["height"] - y)
                n += 1
                shot = d / f"article_{n:02d}.png"
                data = cdp.send("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True,
                                                          "clip": {"x": reg["x"], "y": y, "width": reg["width"], "height": h, "scale": 1}})["data"]
                shot.write_bytes(base64.b64decode(data))
                parts.append({"file": str(shot), "at": time.strftime("%H:%M:%S")})
                y += h
            info.pop("text")
            meta.update({k: v for k, v in info.items() if k not in ("region",)}, region=info["region"], shots=parts,
                        keywords=matched, lacking_context=lacking, relevant=True, captured_at=rec["at"],
                        recapture={**rec, "result": "ok"})
            (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
            out.append({"bundle": d.name, "result": "ok", "shots": len(parts)})
            page.close()
        browser.close()
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
