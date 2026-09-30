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
import shutil
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
  // Khung thân bài quen thuộc của báo Việt được ưu tiên hơn điểm (cột "Tin mới" nhiều đoạn mô tả có thể điểm cao hơn)
  // Chỉ nhận khung khi: lớp đó không lặp nhiều lần trên trang (nhiều trang dùng .article-content cho từng ô tin ở danh sách)
  // và khung không ngắn hơn hẳn khối chấm điểm (nếu không, đó là một ô tin chứ không phải thân bài)
  const KNOWN = ['[itemprop="articleBody"]', '.edittor-content', '.fck_detail', '.the-article-body', '.detail-content', '.detail__content',
                 '.article-content', '.article__body', '.content-detail', '.singular-content', '.detail-cmain', '#main-detail-body',
                 '.entry-content', '.post-content', '.cms-body', '.article-body', '.news-content', '.content-news', '.detail-content-body'];
  const pText = (el) => [...el.querySelectorAll('p')].reduce((s, p) => s + p.innerText.trim().length, 0) || el.innerText.trim().length;
  const bestN = body === document.body ? 0 : pText(body);
  const known = KNOWN.flatMap(sel => { const els = [...document.querySelectorAll(sel)]; return els.length <= 2 ? els : []; })
    .filter(el => !outside(el)).map(el => ({el, n: pText(el)}))
    .map(x => ({...x, imgs: [...x.el.querySelectorAll('img')].filter(i => i.getBoundingClientRect().width >= 300).length}))
    // khung thân bài chỉ gồm ẢNH văn bản (thông báo, công văn chụp) cũng nhận, dù ít chữ
    .filter(x => (x.n > 400 || x.imgs > 0) && (x.n >= bestN * 0.5 || x.imgs > 0 || x.el.contains(body) || body.contains(x.el)))
    .sort((a, b) => (b.n + b.imgs * 2000) - (a.n + a.imgs * 2000));
  if (known.length) body = known[0].el;
  const h1s = [...document.querySelectorAll('h1')].filter(h => h.getClientRects().length);
  const br = body.getBoundingClientRect();
  const h1 = h1s.find(h => { const r = h.getBoundingClientRect(); return r.top <= br.top + 5 && br.top - r.bottom < 900 && r.right > br.left && r.left < br.right; })
          || h1s[0] || null;
  const top = h1 && h1.getBoundingClientRect().top < br.top ? h1 : body;
  const r1 = top.getBoundingClientRect(), r2 = body.getBoundingClientRect();
  // bề ngang theo khối nội dung (tiêu đề có thể trải hết trang); tiêu đề chỉ quyết định mép trên
  const left = Math.max(0, Math.min(r2.left, r1.width < r2.width * 1.4 ? r1.left : r2.left) - 8);
  const right = Math.min(document.documentElement.clientWidth, Math.max(r2.right, r1.width < r2.width * 1.4 ? r1.right : r2.right) + 8);
  // Khung chèn giữa bài (tin mới / tin liên quan / đọc thêm): tạm ẩn khi đọc chữ; ảnh chụp giữ nguyên như trang hiển thị
  const INLINE = '.tindnd, .box-tinlienquan, .tinlienquan, .relate-news, .related-news, .box-related, .news-relation, ' +
                 '[class^="related"], [class*=" related"], .read-more-box, .box-docthem, .VCSortableInPreviewMode[type="RelatedNews"]';
  const hidden = [...body.querySelectorAll(INLINE)].map(e => [e, e.style.display]);
  hidden.forEach(([e]) => { e.style.display = 'none'; });
  const bodyText = body.innerText.trim();
  hidden.forEach(([e, d]) => { e.style.display = d; });
  // Danh sách tin khác ở cuối thân bài ("Có thể bạn quan tâm"…): cắt vùng chụp và nguyên văn tại tiêu đề đó
  // chỉ các tiêu đề chắc chắn là danh sách cuối bài; "Tin liên quan"/"Đọc thêm" hay nằm GIỮA bài (Dân trí…) → không cắt
  const TAIL = /^(Có thể bạn quan tâm|Tin cùng chuyên mục|Bài viết liên quan|Xem thêm các tin|Tin khác|Tin mới nhất)\s*:?$/i;
  // "Đọc thêm"/"Xem thêm"/"Tin liên quan"… có thể nằm giữa bài: chỉ cắt khi sau đó chỉ còn các dòng ngắn kiểu tiêu đề tin
  const SOFT = /^(Đọc thêm|Xem thêm|Xem nhiều|Đọc nhiều|Tin liên quan|Tin nổi bật|Tin tài trợ|Tin cùng chủ đề|Cùng chuyên mục)\s*:?$/i;
  const onlyHeadlinesAfter = (label) => {
    const i = bodyText.indexOf(label, Math.floor(bodyText.length * 0.3));
    return i > 0 && bodyText.slice(i + label.length).split('\n').every(l => l.trim().length <= 200);
  };
  const tail = [...body.querySelectorAll('h2, h3, h4, div, span, strong, p, a')].find(e => {
    const t = (e.innerText || '').trim();
    return e.childElementCount <= 1 && e.getBoundingClientRect().top > r2.top + r2.height * 0.3
      && (TAIL.test(t) || (SOFT.test(t) && onlyHeadlinesAfter(t)));
  });
  const cutAt = tail ? tail.getBoundingClientRect().top : null;
  let cleanText = bodyText;
  if (tail) { const i = bodyText.indexOf(tail.innerText.trim(), Math.floor(bodyText.length * 0.3)); if (i > 0) cleanText = bodyText.slice(0, i).trim(); }
  const author = (ld && (Array.isArray(ld.author) ? ld.author.map(a => a.name).join(', ') : ld.author && ld.author.name))
    || meta('meta[name="author"]') || meta('meta[property="article:author"]') || null;
  return {
    canonical: (document.querySelector('link[rel="canonical"]') || {}).href || location.href, final: location.href,
    title: meta('meta[property="og:title"]') || (h1 && h1.innerText.trim()) || document.title,
    site: meta('meta[property="og:site_name"]') || location.hostname,
    author, published: (ld && ld.datePublished) || meta('meta[property="article:published_time"]') || meta('meta[itemprop="datePublished"]') || meta('time[datetime]') && document.querySelector('time[datetime]').getAttribute('datetime'),
    modified: (ld && ld.dateModified) || meta('meta[property="article:modified_time"]'),
    text: (h1 ? h1.innerText.trim() + '\n\n' : '') + cleanText, cut_tail: !!tail,
    region: {x: left, y: r1.top + scrollY - 8, width: right - left, height: (cutAt || r2.bottom) - r1.top + 16},
    body_is_page: body === document.body,
    doc_images: [...body.querySelectorAll('img')].map(i => ({i, r: i.getBoundingClientRect()}))
      .filter(({i, r}) => r.width >= 300 && (i.naturalWidth || 0) >= 800 && (!cutAt || r.top < cutAt))
      .slice(0, 30).map(({i, r}) => ({x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height,
                                       src: i.currentSrc || i.src, alt: i.alt || null, natural: [i.naturalWidth, i.naturalHeight]})),
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
            prev = index.get(c["url"])
            # lỗi tạm (trang sập, chuyển hướng bị ngắt, mạng) được thử lại, tối đa 3 lần
            if prev is not None and not ("error" in prev and prev.get("attempts", 1) < 3):
                continue
            if "facebook.com" in c["url"]:
                index[c["url"]] = {"skipped": "facebook — thuộc luồng Facebook"}
                continue
            try:
                try:
                    page.goto(c["url"], wait_until="domcontentloaded", timeout=60000)
                except Exception as exc:  # link Google News tự chuyển sang bài báo giữa chừng → không phải lỗi
                    if "interrupted by another navigation" not in str(exc):
                        raise
                    page.wait_for_timeout(3000)
                if "news.google.com" in page.url:  # trang chuyển hướng của Google News
                    page.wait_for_url(lambda u: "news.google.com" not in u, timeout=30000)
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_timeout(random.randint(2500, 4000))
                title = page.title()
                if any(b.lower() in (title + page.evaluate("document.body.innerText.slice(0,2000)")).lower() for b in BLOCK):
                    index[c["url"]] = {"blocked": page.url}
                    continue
                # cuộn tới đáy (trang dài nhiều ảnh văn bản) rồi chờ mọi ảnh lớn tải xong (tối đa ~60 giây)
                page.evaluate("""async () => {
                  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
                  for (let i = 0; i < 150 && innerHeight + scrollY < document.body.scrollHeight - 5; i++) { scrollBy(0, 1200); await sleep(250); }
                  for (let t = 0; t < 60; t++) {
                    const pending = [...document.images].filter(im => !im.complete && im.getBoundingClientRect().width >= 300);
                    if (!pending.length) break;
                    pending.forEach(im => im.scrollIntoView({block: 'center'}));
                    await sleep(1000);
                  }
                  scrollTo(0, 0);
                }""")
                page.wait_for_timeout(800)
                # thanh menu dính, nút liên hệ nổi, hộp chat… không che nội dung trong ảnh chụp
                page.evaluate("() => document.querySelectorAll('body *').forEach(e => { const p = getComputedStyle(e).position; "
                              "if (p === 'fixed' || p === 'sticky') e.style.setProperty('visibility', 'hidden', 'important'); })")
                info = page.evaluate(EXTRACT)
            except Exception as exc:
                index[c["url"]] = {"error": f"{type(exc).__name__}: {str(exc)[:200]}",
                                   "attempts": (prev or {}).get("attempts", 0) + 1}
                index_f.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
                if page.is_closed() or "crash" in str(exc).lower() or "closed" in str(exc).lower():
                    try:  # trang đã sập thì mọi lần mở sau đều lỗi theo → mở trang mới
                        page.close()
                    except Exception:
                        pass
                    page = ctx.new_page()
                    cdp = ctx.new_cdp_session(page)
                continue
            final = info["canonical"] or info["final"]
            key = key_of(final)
            out = root / key
            # tên trang ("Roxana Plaza") cũng tính — trang thông báo của CĐT thường chỉ có ảnh văn bản, ít chữ
            matched, lacking = match_keywords(f"{info['title']}\n{info['site']}\n{info['text']}", config)
            meta = {**info, "candidate": c, "key": key, "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S+07:00"),
                    "keywords": matched, "lacking_context": lacking, "relevant": bool(matched)}
            meta.pop("text")
            if (out / "meta.json").exists():  # một link khác dẫn tới cùng bài đã chụp → giữ bản đã có, không ghi đè
                index[c["url"]] = {"key": key, "relevant": json.loads((out / "meta.json").read_text(encoding="utf-8")).get("relevant"),
                                   "same_as_existing": True}
                index_f.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
                continue
            out.mkdir(parents=True, exist_ok=True)
            if matched and not (out / "meta.json").exists():
                (out / "article.txt").write_text(info["text"], encoding="utf-8")
                (out / "article.html").write_text(page.content(), encoding="utf-8")
                reg = info["region"]
                parts, y, n = [], reg["y"], 0
                try:
                    while y < reg["y"] + reg["height"] and n < 20:
                        h = min(MAX_PART, reg["y"] + reg["height"] - y)
                        n += 1
                        shot = out / f"article_{n:02d}.png"
                        data = cdp.send("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True,
                                                                  "clip": {"x": reg["x"], "y": y, "width": reg["width"], "height": h, "scale": 1}})["data"]
                        shot.write_bytes(base64.b64decode(data))
                        parts.append({"file": str(shot), "at": time.strftime("%H:%M:%S")})
                        y += h
                except Exception as exc:  # chụp lỗi (trang quá dài, trang sập…) → bỏ thư mục dở, ghi lỗi để lần sau thử lại
                    shutil.rmtree(out, ignore_errors=True)
                    index[c["url"]] = {"error": f"screenshot: {type(exc).__name__}: {str(exc)[:160]}",
                                       "attempts": (prev or {}).get("attempts", 0) + 1}
                    index_f.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
                    page = ctx.new_page()
                    cdp = ctx.new_cdp_session(page)
                    continue
                meta["shots"] = parts
                att = []  # từng ảnh văn bản chụp riêng ở độ phân giải 2x để đọc được chữ
                for k, im in enumerate(info.get("doc_images") or [], 1):
                    try:
                        data = cdp.send("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True,
                                        "clip": {"x": im["x"], "y": im["y"], "width": im["w"], "height": min(im["h"], 8000), "scale": 2}})["data"]
                        f = out / f"attach_{k:02d}.png"
                        f.write_bytes(base64.b64decode(data))
                        att.append({"file": str(f), "at": time.strftime("%H:%M:%S"), "src": im["src"], "alt": im["alt"]})
                    except Exception:
                        continue
                meta["attach_shots"] = att
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
