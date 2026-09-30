"""Read-only capture of the post open in the Chrome window (permalink dialog view).

python capture_post.py <out_dir> <prefix>
Writes <prefix>_post_NN.png, <prefix>_cscroll_NN.png, <prefix>_snapshot.txt, <prefix>_comments.json,
<prefix>_images.json, <prefix>_log.json. Clicks only: comment filter, "Xem thêm", "Xem N phản hồi"/"Xem thêm bình luận".
"""
import base64
import json
import random
import sys
import time

from playwright.sync_api import sync_playwright

READ_COMMENTS = r"""
(root) => {
  const dialogs = [...document.querySelectorAll('[role="dialog"]')];
  const scope = root || dialogs.filter(d => d.querySelector('div[role="article"]')).pop() || document;
  const out = [], seen = new Set();
  scope.querySelectorAll('div[role="article"][aria-label]').forEach((el, i) => {
    const label = el.getAttribute('aria-label') || '';
    if (!el.getClientRects().length) return;  // bản ẩn của trang phía sau dialog
    if (!/bình luận|phản hồi|comment|reply/i.test(label)) return;
    const links = [...el.querySelectorAll('a[href]')];
    const author = links.find(a => a.innerText.trim() && !/comment_id=/.test(a.href));
    const permalink = links.find(a => /comment_id=/.test(a.href) && /^\d|giờ|phút|ngày|tuần|tháng|năm|Vừa xong/.test(a.innerText.trim()));
    const body = [...el.querySelectorAll('div[dir="auto"]')]
      .filter(d => !d.closest('div[role="article"]') || d.closest('div[role="article"]') === el)
      .map(d => d.innerText.trim()).filter(Boolean);
    // Facebook (09/2026) không lồng role=article cho trả lời: cấp lấy từ nhãn + reply_comment_id.
    const href = permalink ? permalink.href : '';
    const cid = (href.match(/[?&]comment_id=(\d+)/) || [])[1] || null;
    const rid = (href.match(/reply_comment_id=(\d+)/) || [])[1] || null;
    const depth = /^Phản hồi|^Reply/i.test(label) || rid ? 2 : 1;
    const r = el.getBoundingClientRect();
    const key = (cid || '') + '/' + (rid || '') || label;
    if (seen.has(key)) return; seen.add(key);  // mỗi bình luận chỉ một lần
    const reacts = [...el.querySelectorAll('[aria-label]')].map(x => x.getAttribute('aria-label')).filter(t => /cảm xúc|reaction/i.test(t));
    const emoji = [...el.querySelectorAll('img[alt]')].map(i => i.alt).filter(a => a && a.length <= 8);
    const stickers = [...el.querySelectorAll('[aria-label]')].map(x => x.getAttribute('aria-label')).filter(t => /nhãn dán|sticker|gif/i.test(t));
    out.push({i, label, author: author && author.innerText.trim(), author_href: author && author.href,
              time_text: permalink && permalink.innerText.trim(), comment_url: href || null,
              fb_comment_id: rid || cid, parent_fb_comment_id: rid ? cid : null,
              text: [...new Set(body)].join('\n'), emoji, stickers, depth, reacts,
              top: Math.round(r.top + scrollY), height: Math.round(r.height)});
  });
  return out;
}
"""


POST_AREA = r"""
() => {
  const d = [...document.querySelectorAll('[role="dialog"]')]
    .filter(x => x.getClientRects().length && x.querySelector('div[role="article"], [role="textbox"], img')).pop();
  if (!d) return {error: 'không thấy khung bài (dialog) — mở bài bằng permalink trước'};
  const b = d.getBoundingClientRect();
  const top = Math.max(0, b.top), left = Math.max(0, b.left);
  let bottom = Math.min(b.bottom, innerHeight);
  const composer = d.querySelector('[contenteditable="true"], [role="textbox"]');
  // Chân khung bài = khối bao ô "Bình luận dưới tên <tài khoản>" + ảnh đại diện: leo lên tổ tiên còn thấp (< 160px).
  let row = composer && (composer.closest('form') || composer);
  while (row && row.parentElement && d.contains(row.parentElement)
         && row.parentElement.getBoundingClientRect().height < 160) row = row.parentElement;
  let account = null;
  if (row) {
    const r = row.getBoundingClientRect();
    if (r.top > top + 80 && r.top < bottom) bottom = r.top - 2;  // cắt ngay trên chân khung bài
    const m = (composer.getAttribute('aria-label') || '').match(/dưới tên (.+)$/);
    account = m && m[1].trim();
  }
  const area = {x: left, y: top, width: Math.min(b.right, innerWidth) - left, height: bottom - top};
  // Chốt chặn: mọi điểm mẫu trong vùng chụp phải thuộc khung bài và không thuộc ô bình luận của tài khoản.
  const bad = [];
  for (let i = 0; i <= 12; i++) for (let j = 0; j <= 12; j++) {
    const x = area.x + 3 + (area.width - 6) * i / 12, y = area.y + 3 + (area.height - 6) * j / 12;
    const e = document.elementFromPoint(x, y);
    if (!e || !d.contains(e) || (row && row.contains(e))) bad.push([Math.round(x), Math.round(y)]);
  }
  // Tên tài khoản không được hiện trong vùng chụp (nó chỉ nên có ở ô bình luận, đã loại).
  const leak = account && [...d.querySelectorAll('span, a, div[dir="auto"]')].some(e => {
    if (row && row.contains(e)) return false;
    const r = e.getBoundingClientRect();
    return r.height && r.bottom > area.y && r.top < area.y + area.height && e.childElementCount === 0
           && e.textContent.trim() === account;
  });
  return {...area, account, bad, leak};
}
"""


def post_area(page) -> dict:
    area = page.evaluate(POST_AREA)
    if area.get("error"):
        raise RuntimeError(area["error"])
    if area["bad"] or area["leak"] or area["height"] < 100:
        raise RuntimeError(f"Vùng chụp dính phần ngoài bài / thông tin tài khoản — không chụp: {area}")
    return {k: area[k] for k in ("x", "y", "width", "height")}


VISIBLE_COMMENTS = r"""
(area) => {
  const d = [...document.querySelectorAll('[role="dialog"]')].filter(x => x.querySelector('div[role="article"]')).pop();
  if (!d) return [];
  return [...d.querySelectorAll('div[role="article"][aria-label]')].filter(el => el.getClientRects().length)
    .map(el => ({el, r: el.getBoundingClientRect()}))
    .filter(({r}) => r.bottom > area.y + 8 && r.top < area.y + area.height - 8)
    .sort((a, b) => a.r.top - b.r.top)
    .map(({el}) => {
      const a = [...el.querySelectorAll('a[href*="comment_id="]')].map(x => x.href)[0] || '';
      const cid = (a.match(/[?&]comment_id=(\d+)/) || [])[1] || null;
      const rid = (a.match(/reply_comment_id=(\d+)/) || [])[1] || null;
      return rid || cid || el.getAttribute('aria-label');
    });
}
"""


POST_INFO = r"""
() => {
  const d = [...document.querySelectorAll('[role="dialog"]')].filter(x => x.querySelector('[data-ad-rendering-role]')).pop() || document;
  const names = [...d.querySelectorAll('[data-ad-rendering-role="profile_name"]')];
  const link = (el) => el && [...el.querySelectorAll('a[href]')].find(a => a.innerText.trim());
  const a0 = link(names[0]);
  const msgs = [...d.querySelectorAll('[data-ad-rendering-role="story_message"]')];
  const meta = d.querySelector('[data-ad-rendering-role="meta"]');
  const firstComment = d.querySelector('div[role="article"][aria-label]');
  // số liệu: các số đứng một mình sau thân bài và trước bình luận đầu tiên (thích · bình luận · chia sẻ)
  const nums = [...d.querySelectorAll('span')].filter(s => {
      if (!/^\d[\d.,]*\s*(K|N|nghìn|triệu)?$/i.test(s.innerText.trim())) return false;
      if (firstComment && (firstComment.compareDocumentPosition(s) & Node.DOCUMENT_POSITION_FOLLOWING)) return false;
      return !s.closest('div[role="article"][aria-label]');
    }).map(s => s.innerText.trim());
  const shared = names[1] ? {author: (link(names[1]) || {}).innerText, author_href: (link(names[1]) || {}).href,
                             text: msgs[1] ? msgs[1].innerText.trim() : null} : null;
  const badge = names[0] ? [...names[0].parentElement.querySelectorAll('span')].map(s => s.innerText.trim())
      .find(t => /^(Quản trị viên|Người kiểm duyệt|Fan cứng|Người đóng góp nổi bật|Thành viên mới|Admin|Moderator)$/.test(t)) : null;
  return {author: a0 ? a0.innerText.trim() : (names[0] ? names[0].innerText.trim() : null), author_href: a0 ? a0.href : null,
          badge: badge || null, text: msgs[0] ? msgs[0].innerText.trim() : null, shared,
          time_text: meta ? meta.innerText.split('·')[0].trim() : null, counts_raw: [...new Set(nums.slice(0, 3))].length ? nums.slice(0, 3) : [],
          link_preview: [...d.querySelectorAll('[data-ad-rendering-role="title"], [data-ad-rendering-role="description"]')].map(e => e.innerText.trim()).filter(Boolean)};
}
"""


def capture(b, p, out_dir, prefix) -> dict:
    """Capture the post currently open in page `p` (permalink dialog view). Returns the log dict."""
    log = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%S+07:00"), "steps": []}
    if True:
        cdp = b.contexts[0].new_cdp_session(p)
        n = {"post": 0, "cscroll": 0}

        def shot(kind, shows):
            n[kind] += 1
            path = f"{out_dir}\\{prefix}_{kind}_{n[kind]:02d}.png"
            area = post_area(p)  # chỉ khung bài — không thanh Facebook, menu trái (tên tài khoản), quảng cáo, ô bình luận
            data = cdp.send("Page.captureScreenshot", {"format": "png", "clip": {**area, "scale": 1}})["data"]
            open(path, "wb").write(base64.b64decode(data))
            step = {"shot": path, "kind": kind, "shows": shows, "at": time.strftime("%H:%M:%S")}
            if kind == "cscroll":  # bình luận nào nằm trong ảnh này, theo thứ tự từ trên xuống → scroll_refs
                step["comments"] = p.evaluate(f"({VISIBLE_COMMENTS})", area)
            log["steps"].append(step)
            return path

        def pause(a=2.0, z=4.0):
            p.wait_for_timeout(int(random.uniform(a, z) * 1000))

        dialog = p.locator('[role="dialog"]').filter(has=p.locator('[role="article"], [aria-label]')).last
        scroller = dialog if dialog.count() else p.locator("body")
        box = scroller.bounding_box() or {"x": 0, "y": 0, "width": 1384, "height": 905}
        cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        p.mouse.move(cx, cy)

        # 1. thân bài: ảnh đầu, cuộn tới khi thấy dòng số liệu (Thích/Bình luận/Chia sẻ)
        shot("post", "Thân bài: nhóm, người đăng, mốc thời gian, nội dung, đầu ảnh đính kèm")
        p.mouse.wheel(0, 420); pause(1.5, 2.5)
        shot("post", "Phần còn lại của ảnh đính kèm và số tương tác")

        # 2. ảnh trong bài
        imgs = p.evaluate("""(sel) => [...document.querySelectorAll(sel + ' img')].filter(i => i.naturalWidth > 300)
            .map(i => ({src: i.src, w: i.naturalWidth, h: i.naturalHeight, alt: i.alt}))""", '[role="dialog"]')
        json.dump(imgs, open(f"{out_dir}\\{prefix}_images.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

        # 3. bộ lọc bình luận -> Tất cả bình luận
        import re as _re
        filt = p.locator('[role="dialog"] [role="button"]').filter(
            has_text=_re.compile("^\\s*(Phù hợp nhất|Mới nhất|Tất cả bình luận)[\\s﻿]*$"))
        if filt.count() and filt.first.inner_text().strip(" ﻿\n") == "Tất cả bình luận":
            log["filter"] = "Tất cả bình luận (đã chọn sẵn)"
        elif filt.count():
            filt.first.click(timeout=5000); pause(1, 2)
            items = p.locator('[role="menuitem"]')
            pick = [items.nth(i) for i in range(items.count())
                    if items.nth(i).inner_text().splitlines()[0].strip(" ﻿") =="Tất cả bình luận"]
            if pick:
                pick[0].click(timeout=5000); pause(2.5, 4)
                log["filter"] = "Tất cả bình luận"
            else:
                log["filter"] = "không có tuỳ chọn Tất cả bình luận"
                p.keyboard.press("Escape")
        else:
            log["filter"] = "không thấy nút bộ lọc (có thể đã là Tất cả bình luận)"

        # 4. mở hết phản hồi / bình luận / Xem thêm
        for _ in range(400):
            more = p.locator('[role="dialog"] [role="button"]').filter(
                has_text=__import__("re").compile(r"^(Xem thêm bình luận|Xem \d+ phản hồi|Xem tất cả \d+ phản hồi|Xem 1 phản hồi|Xem thêm)$"))
            visible = [more.nth(i) for i in range(more.count()) if more.nth(i).is_visible()]
            if not visible:
                break
            visible[0].scroll_into_view_if_needed(); visible[0].click(timeout=5000); pause(2, 5)
        log["expanded_rounds"] = _

        # 4b. thông tin bài (sau khi đã mở "Xem thêm")
        try:
            log["post"] = p.evaluate(POST_INFO)
        except Exception as exc:
            log["post"] = {"error": str(exc)[:200]}

        # 5. bản chữ
        text = p.evaluate("""() => { const d = [...document.querySelectorAll('[role="dialog"]')].pop(); return (d || document.body).innerText; }""")
        open(f"{out_dir}\\{prefix}_snapshot.txt", "w", encoding="utf-8").write(text)

        # 6. ảnh cuộn bình luận: từ dòng số liệu xuống hết
        first = p.locator('[role="dialog"] div[role="article"][aria-label]').first
        if first.count():
            first.scroll_into_view_if_needed(); pause(1, 2)
            p.mouse.move(cx, cy)
            p.mouse.wheel(0, -150); pause(1, 1.5)
            last_marker = None
            for _ in range(600):
                shot("cscroll", f"Bình luận đoạn {n['cscroll'] + 1}")
                marker = p.evaluate("""() => { const d = [...document.querySelectorAll('[role="dialog"] *')].find(e => e.scrollHeight > e.clientHeight + 50 && getComputedStyle(e).overflowY.match(/auto|scroll/)); return d ? d.scrollTop : scrollY; }""")
                if marker == last_marker:
                    break
                last_marker = marker
                p.mouse.wheel(0, int(box["height"] * 0.7)); pause(1.5, 2.5)
            # ảnh cuối trùng ảnh trước khi đã hết cuộn — giữ lại, không xoá bằng chứng

        # 7. đọc DOM bình luận + vị trí trong từng ảnh cuộn
        comments = p.evaluate(f"({READ_COMMENTS})(null)")
        json.dump(comments, open(f"{out_dir}\\{prefix}_comments.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        log["comment_count"] = len(comments)
        log["url"] = p.url
        log["ended_at"] = time.strftime("%Y-%m-%dT%H:%M:%S+07:00")
        json.dump(log, open(f"{out_dir}\\{prefix}_log.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return log


def main(out_dir, prefix):
    sys.stdout.reconfigure(encoding="utf-8")
    with sync_playwright() as pw:
        b = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
        p = [q for q in b.contexts[0].pages if not q.url.startswith("devtools")][-1]
        p.bring_to_front()
        print(json.dumps(capture(b, p, out_dir, prefix), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
