# Quét Facebook

Công cụ: claude-in-chrome (Chrome của người dùng, đã đăng nhập). Nạp một lần bằng ToolSearch:
`select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__find,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__javascript_tool`

- **Chụp ảnh:** `computer` với `action: "screenshot"` (hoặc `"zoom"` + `region`) và **`save_to_disk: true`** → kết quả trả đường dẫn file đã lưu → dùng làm `evidence[].file`. Ảnh phải thấy tên người đăng, mốc thời gian và nội dung.
- **Bản chữ:** `get_page_text` → `snapshot_text`.
- **Đọc DOM:** `javascript_tool` **chỉ để đọc** (không `click()`, không gửi form, không sửa trang).
- Không bấm nút có thể mở hộp thoại trình duyệt (alert/confirm).

## 0. Chuẩn bị

1. `tabs_context_mcp` → `tabs_create_mcp` (tab mới, không dùng tab cũ của người dùng).
2. Mở `https://www.facebook.com/`. Thấy form đăng nhập → **dừng**, nhờ người dùng tự đăng nhập.
3. Làm bước 1 của SKILL.md (RUN, stats, progress).

## 1. Ma trận tìm kiếm (lần quét đầu, `mode=full`)

Với **mỗi term** trong mỗi nhóm của `config.json → keyword_groups`, gõ cả bản **có dấu** và **không dấu** (vd "Tường Phong" và "Tuong Phong"; bỏ dấu cả `đ`/`Đ` → `d`/`D`; term đã không dấu thì chỉ một bản). Mục `hashtag` ghép từ **mọi** term của nhóm được áp dụng (viết liền, không dấu, chữ thường: "Tường Phong" → `tuongphong`, "#roxanaplaza" → `roxanaplaza`); term bắt đầu bằng `#` chỉ dùng cho mục `hashtag`:

| `section` | URL | Bộ lọc |
|---|---|---|
| `posts` | `https://www.facebook.com/search/posts/?q=<term>` | lần lượt bộ lọc "Ngày đăng" = từng năm 2017 → năm hiện tại (chọn trong khung bộ lọc bên trái), mỗi năm là 1 task; thêm 1 task "Bài viết mới nhất" |
| `groups` | `https://www.facebook.com/search/groups/?q=<term>` | — |
| `pages` | `https://www.facebook.com/search/pages/?q=<term>` | — |
| `videos` | `https://www.facebook.com/search/videos/?q=<term>` | — |
| `photos` | `https://www.facebook.com/search/photos/?q=<term>` | — |
| `hashtag` | `https://www.facebook.com/hashtag/<term viết liền, không dấu, không cách>` | chỉ với nhóm `roxana`, `tuongphong`, `naviland` |

Với mỗi container trong `config.json → containers` (và mỗi container mới phát hiện):
- Lấy mã `FB-G…` bằng `add_record.py check --url <link nhóm>` (lấy phần tử có `record_type: "container"` — bài chỉ có link nhóm cũng khớp). Chưa có trong kho → ghi bản ghi `container` trước (mục 2 bước 3) rồi mới tạo task — task container luôn cần `container_id`.
- `scan_mode=full` (nhóm/trang chuyên về vụ việc): `group_feed` — `https://www.facebook.com/groups/<id>/?sorting_setting=CHRONOLOGICAL`, hoặc `page_feed` với trang. Cuộn từ mới nhất tới bài cũ nhất, thu **mọi bài**.
- `scan_mode=keyword` (nhóm chung): `in_group_search` — `https://www.facebook.com/groups/<id>/search/?q=<term>` cho mọi term.
- `joined` khác `yes` và nhóm kín → không quét; đưa vào danh sách "cần xin vào".
- `privacy` hoặc `joined` là `unknown` (vd nhóm nhập từ file cũ) → task đầu tiên của nhóm là mở trang nhóm, xác định công khai/kín và đã tham gia chưa, ghi `recheck` với `updates` (`privacy`, `joined`, `member_count`…); sau đó áp các quy tắc trên.

File task cho `--add-tasks` (mảng):

```json
[
  {"kind": "search", "section": "posts", "query": "Roxana Plaza", "filters": {"year": 2021}},
  {"kind": "search", "section": "posts", "query": "Roxana Plaza", "filters": {"sort": "recent"}},
  {"kind": "search", "section": "groups", "query": "Tuong Phong"},
  {"kind": "container", "section": "group_feed", "container_id": "FB-G0001"},
  {"kind": "container", "section": "in_group_search", "container_id": "FB-G0005", "query": "Naviland"}
]
```

## 2. Một task tìm kiếm / cuộn feed

1. Mở URL, áp bộ lọc. Ghi `started_at`.
2. Cuộn danh sách. Với mỗi kết quả: lấy link ứng viên, chạy `add_record.py check --url <link>`. Đã có và không nằm trong `recheck-due` → bỏ qua (đếm là trùng). Chưa có → thu thập bài (mục 3) ngay hoặc thêm task `{"kind": "capture", "url": "<link>"}`.
3. Kết quả là **nhóm/trang** (hoặc gặp nhóm/trang chưa có trong kho qua một bài viết): ghi `container` (xem schema.md). Tên hoặc mô tả có `context_terms` → `topic_dedicated: true`, `scan_mode: "full"`; ngược lại `keyword`. Nhóm kín: ghi `privacy: "private"`, `joined` theo nút trên trang ("Tham gia nhóm" → `no`, "Đã gửi yêu cầu" → `pending`, vào được feed → `yes`). Thêm task container nếu `joined=yes` hoặc nhóm công khai.
4. Kết quả khớp nhóm `requires_context` mà không có từ ngữ cảnh → `exclusion` (classification.md).
5. Cuộn tới khi Facebook hiện "Hết kết quả", hoặc 3 lần cuộn liên tiếp không tải thêm → `reached_end: true`. Dừng sớm vì bất kỳ lý do gì → `reached_end: false` + ghi lý do vào `issues`.
6. Ghi `search_log` (đếm `results_seen`, `results_new`, `results_duplicate`, `results_excluded`). Cập nhật task `done:LOG-...`.
7. Với container: sau khi quét xong ghi `recheck` cho container với `updates.last_scanned_at` (và `member_count` nếu thấy).

## 3. Thu thập một bài

1. **Link riêng:** bấm vào mốc thời gian của bài (hoặc đọc `href` của nó) để lấy permalink. Dạng hợp lệ: `/groups/<gid>/posts/<pid>/`, `/groups/<gid>/permalink/<pid>/`, `/<user>/posts/<pfbid…>`, `/permalink.php?story_fbid=…&id=…`, `/photo/?fbid=…&set=…`, `/reel/<id>`, `/watch/?v=<id>`, `/videos/<id>`. Link `/share/…` → mở, lấy URL sau khi chuyển hướng. Không lấy được → `url_kind: "container_only"`, `url` = link nhóm.
2. `check --url <permalink>` lần nữa. Có bản `origin=legacy` cùng nội dung (thử `check --text "<vài từ đầu>"`) → đặt `supersedes`.
3. **Thời gian chính xác:** rê chuột (`computer` `hover`) lên mốc thời gian, đọc tooltip → `posted_at` + `posted_at_precision: "exact"`. `posted_at_raw` luôn là chữ hiện trên bài (vd "22 tháng 8 lúc 09:15", "3 ngày"), không phải chữ trong tooltip. Không có tooltip → quy đổi thời gian tương đối theo giờ thu thập (`captured_at`, tức lúc đang xem trang) → `relative_estimate`.
4. Bấm mọi "Xem thêm" trong thân bài.
5. **Chụp thân bài** (`save_to_disk: true`); bài dài hơn một màn hình → cuộn và chụp tiếp, mỗi ảnh một evidence `post`.
6. `get_page_text` → `snapshot_text`.
7. **Ảnh đính kèm:** mở từng ảnh (album → mở hết). Ảnh là văn bản/tài liệu → chụp evidence `attach` (dùng `zoom` nếu chữ nhỏ) và **chép lại chữ** vào `attachments[].transcribed_text`. Ảnh thường → mô tả ngắn trong `attachments[].description`.
8. **Bài chia sẻ:** ghi `shared_from`; bài gốc chưa có trong kho → thêm task `capture` cho bài gốc.
9. Ghi số liệu hiển thị (`metrics` + `counted_at`). Người đăng: tên, `href` của link tên, huy hiệu (Quản trị viên, Người kiểm duyệt, Fan cứng…; không có huy hiệu hoặc chỉ là "Thành viên" → `null`) — **không mở trang cá nhân**.
10. Phân loại (classification.md). **Chưa ghi vào kho** — thu thập bình luận trước (mục 4) để ảnh cuộn bình luận vào cùng `evidence` của bài.

## 4. Bình luận

1. Mở bộ lọc bình luận (chữ "Phù hợp nhất" phía trên bình luận) → chọn **"Tất cả bình luận"**. Không có tuỳ chọn này → ghi vào `notes` của bài.
2. Lặp bấm "Xem thêm bình luận", "Xem <N> phản hồi", "Xem thêm" trong bình luận dài — tới khi không còn nút nào. Nghỉ 2–5 giây giữa các lần bấm.
3. **Đọc bình luận** bằng `javascript_tool` (chỉ đọc). Phiên bản khởi đầu — nếu Facebook đổi giao diện, điều chỉnh và ghi lại bản mới vào đây:

   ```js
   (() => {
     const out = [];
     document.querySelectorAll('div[role="article"][aria-label]').forEach((el, i) => {
       const label = el.getAttribute('aria-label') || '';
       if (!/bình luận|phản hồi|comment|reply/i.test(label)) return;
       const links = [...el.querySelectorAll('a[href]')];
       const author = links.find(a => a.innerText.trim() && !a.href.includes('comment_id='));
       const permalink = links.find(a => a.href.includes('comment_id='));
       const parts = [...el.querySelectorAll('div[dir="auto"]')].map(d => d.innerText.trim()).filter(Boolean);
       let depth = 1;
       for (let p = el.parentElement; p; p = p.parentElement) if (p.getAttribute && p.getAttribute('role') === 'article') depth++;
       out.push({i, label, author: author && author.innerText.trim(), author_href: author && author.href,
                 time_text: permalink && permalink.innerText.trim(), comment_url: permalink && permalink.href,
                 text: [...new Set(parts)].join('\n'), depth: Math.min(depth, 3)});
     });
     return JSON.stringify(out);
   })()
   ```

   `fb_comment_id` = tham số `comment_id` (hoặc `reply_comment_id` với trả lời) trong `comment_url`. Đọc DOM thất bại → dùng `get_page_text` và tách thủ công.
4. **Ảnh cuộn:** cuộn lên đầu phần bình luận; lặp: chụp (`save_to_disk: true`) → cuộn khoảng 80% chiều cao màn hình (chừa phần chồng lấn để không hở bình luận). Mỗi ảnh là một evidence `cscroll` của **bài**. Ghi lại bình luận nào ở ảnh thứ mấy, vị trí thứ mấy.
5. **Bình luận mức cao** (classification.md) → cuộn tới, chụp riêng bằng `zoom` vùng bình luận → evidence `comment` của bình luận đó.
6. **Ghi vào kho theo thứ tự:**
   1. `add` bản ghi **source** với `evidence` = ảnh `post` + `attach` + toàn bộ `cscroll` → nhận `id` và `evidence_paths`.
   2. `add` **cả cây bình luận** trong một mảng: `source_id` = mã vừa nhận; `parent_comment_id` = `"@<chỉ số>"`; `scroll_refs[].file` = đường dẫn tương ứng trong `evidence_paths` (thứ tự ảnh `cscroll` giữ nguyên như khi gửi).
   3. Bài có tin mới về tiến trình pháp lý/hành chính (thanh tra, toà, công an, đối thoại) → `add` một `event` (schema.md) với `related_ids` = mã bài; văn bản chỉ thấy qua ảnh đăng trên mạng xã hội → `reliability: "mxh"`.
   - Bài không có bình luận: bỏ bước 1–5, ghi source luôn.
7. **Đối chiếu:** số bình luận thu được lệch > 5% so với số Facebook hiển thị → ghi vào `notes` của bài hoặc một `recheck`: "Facebook hiển thị 604, thu được 571 — có thể do bình luận bị ẩn/xoá/lọc spam".

## 5. Nhịp độ và điều kiện dừng

- Nghỉ ngẫu nhiên 3–8 giây giữa các lần mở trang (`computer` `wait`), 2–5 giây giữa các lần bấm mở bình luận.
- Làm theo lô: 1 container hoặc khoảng 10 task tìm kiếm; hết lô → `build_excel.py`.
- **Dừng ngay** khi thấy: "Bạn tạm thời bị chặn", checkpoint / xác minh danh tính, CAPTCHA, form đăng nhập, cảnh báo hành vi tự động. Khi đó: `--set <task>=blocked --note "<điều thấy trên màn hình>"`, chạy `build_excel.py` và `report`, báo người dùng. **Không thử lại cùng thao tác, không tìm cách vượt qua.**
- Trang "Nội dung này hiện không khả dụng": bài đã có trong kho → `recheck` `deleted` kèm ảnh thông báo; bài mới → bỏ qua và ghi vào `issues` của `search_log`.

## 6. Lần cập nhật (`mode=update`)

1. Ma trận tìm kiếm như mục 1 nhưng **chỉ** lọc "Bài viết mới nhất" (không lọc theo năm). Dừng cuộn khi gặp liên tiếp 10 kết quả đã có trong kho → `reached_end: true`, `notes: "Dừng khi gặp 10 kết quả cũ liên tiếp"`.
2. Container `full`: cuộn feed tới khi gặp liên tiếp 10 bài đã có.
3. `status.py recheck-due --run RUN` → mở lại từng bài:
   - Không còn → `recheck` `deleted` + ảnh thông báo.
   - Nội dung khác bản trong kho → `recheck` `edited` + `new_text` + ảnh mới + `snapshot_text`.
   - Còn nguyên → `recheck` `active` + `metrics` mới.
   - Mở lại bình luận (mục 4): ảnh cuộn mới đi kèm `recheck` của bài; bình luận mới → `add` với `scroll_refs` trỏ vào `evidence_paths` của recheck đó; bình luận cũ không còn → `recheck` `deleted` cho bình luận đó.
   - Bài từ file cũ (`reason` có "file cũ"): thu thập đầy đủ như bài mới (mục 3–4) với `supersedes` = mã bài cũ.
4. Container `joined` khác `yes`: mở lại xem đã được duyệt chưa; đã vào → `recheck` với `updates.joined = "yes"` và thêm task quét.
