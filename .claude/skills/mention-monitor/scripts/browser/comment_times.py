"""Hover each visible comment's timestamp link (inside the post dialog) and read the tooltip. Read-only."""
import json
import re
import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
out = sys.argv[1]
with sync_playwright() as pw:
    b = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
    p = [q for q in b.contexts[0].pages if not q.url.startswith("devtools")][-1]
    p.bring_to_front()
    dialog = p.locator('[role="dialog"]').filter(has=p.locator('div[role="article"]')).last
    links = dialog.locator('div[role="article"] a[href*="comment_id="]')
    result = []
    for i in range(links.count()):
        a = links.nth(i)
        label = a.inner_text().strip()
        if not a.is_visible() or not re.match(r"^\d+\s*(giây|phút|giờ|ngày|tuần|tháng|năm)|^Vừa xong", label):
            continue
        a.scroll_into_view_if_needed()
        a.hover()
        p.wait_for_timeout(3000)
        tips = p.evaluate("[...document.querySelectorAll('[role=tooltip]')].map(e => e.innerText.trim()).filter(Boolean)")
        m = re.search(r"(?:reply_)?comment_id=(\d+)", a.get_attribute("href") or "")
        result.append({"label": label, "comment_id": m and m.group(1), "tooltip": tips[-1] if tips else None})
        p.mouse.move(5, 5)
        p.wait_for_timeout(600)
    json.dump(result, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(result, ensure_ascii=False, indent=1))
