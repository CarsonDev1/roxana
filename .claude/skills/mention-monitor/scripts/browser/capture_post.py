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


def main(out_dir, prefix):
    sys.stdout.reconfigure(encoding="utf-8")
    log = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%S+07:00"), "steps": []}
    with sync_playwright() as pw:
        b = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
        p = [q for q in b.contexts[0].pages if not q.url.startswith("devtools")][-1]
        p.bring_to_front()
        cdp = b.contexts[0].new_cdp_session(p)
        n = {"post": 0, "cscroll": 0}

        def shot(kind, shows):
            n[kind] += 1
            path = f"{out_dir}\\{prefix}_{kind}_{n[kind]:02d}.png"
            data = cdp.send("Page.captureScreenshot", {"format": "png"})["data"]
            open(path, "wb").write(base64.b64decode(data))
            log["steps"].append({"shot": path, "kind": kind, "shows": shows, "at": time.strftime("%H:%M:%S")})
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
        for _ in range(30):
            more = p.locator('[role="dialog"] [role="button"]').filter(
                has_text=__import__("re").compile(r"^(Xem thêm bình luận|Xem \d+ phản hồi|Xem tất cả \d+ phản hồi|Xem 1 phản hồi|Xem thêm)$"))
            visible = [more.nth(i) for i in range(more.count()) if more.nth(i).is_visible()]
            if not visible:
                break
            visible[0].scroll_into_view_if_needed(); visible[0].click(timeout=5000); pause(2, 5)
        log["expanded_rounds"] = _

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
            for _ in range(40):
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
        print(json.dumps(log, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
