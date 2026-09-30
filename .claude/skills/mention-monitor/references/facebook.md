# Quét Facebook

## Công cụ trình duyệt — đã chạy thử thật ngày 30/09/2026 (bài #6, #4 của file cũ)

**Cách A — Playwright điều khiển một Chrome riêng trên máy này (đã kiểm chứng, dùng mặc định):**
1. `powershell -File .claude/skills/mention-monitor/scripts/browser/start_chrome.ps1` — mở Chrome với profile riêng `%LOCALAPPDATA%\RoxanaMonitor\chrome-profile` (ngoài repo, không vào git) và cổng điều khiển `127.0.0.1:9222`. Kiểm tra: `curl -s http://127.0.0.1:9222/json/version`.
2. Lần đầu: nhờ người dùng **tự đăng nhập** Facebook trong cửa sổ đó (phiên được giữ cho các lần sau). Claude không gõ mật khẩu.
3. Các script (Python có Playwright: `python -m pip install playwright`, không cần tải trình duyệt):
   - `scripts/browser/fb.py status | goto <url> | shot <png> | clip <png> x y w h [scale] | text <txt> | js <file.js> [out] | scroll <dy>` — một thao tác mỗi lần gọi.
   - `scripts/browser/capture_post.py <thư_mục_ảnh> <tiền_tố>` — với bài đang mở ở permalink: chụp 2 ảnh thân bài, chọn **"Tất cả bình luận"**, mở hết "Xem thêm"/phản hồi, ghi bản chữ, chụp ảnh cuộn bình luận, đọc DOM bình luận → `<tiền_tố>_comments.json`, nhật ký giờ từng ảnh → `<tiền_tố>_log.json`.
   - `scripts/browser/comment_times.py <out.json>` — rê chuột lên mốc thời gian từng bình luận, đọc tooltip (giờ chính xác). Tooltip đôi khi không kịp hiện → chạy lại, gộp kết quả.
   - `scripts/browser/capture_photo.py <photo_url> <out.png>` — chỉ chụp tấm ảnh (2x) → evidence `attach`.
   - `scripts/browser/capture_comment.py <link ?comment_id=…> "<tên người viết>" <out.png>` — chỉ chụp khung bình luận đó (2x) → evidence `comment`.
   - Ảnh lưu thẳng vào thư mục chỉ định; dùng đường dẫn đó làm `evidence[].file` (add_record chép vào `screenshots/` và băm). `capture_tool: "playwright"`.
   - **Chỉ chụp nội dung bài** (yêu cầu người dùng 30/09/2026): ảnh thân bài/ảnh cuộn là vùng khung "Bài viết của …", cắt ngay trên chân khung (ô "Bình luận dưới tên <tài khoản>" + ảnh đại diện). Không được dính thanh Facebook, menu trái (tên tài khoản quét), quảng cáo, ô bình luận. `capture_post.py` kiểm tra điểm mẫu và tên tài khoản trước mỗi lần chụp; vi phạm → dừng, không chụp. Không dùng `fb.py shot` (toàn màn hình) cho bằng chứng.
   - **Chụp lại một bài đã có** (vd ảnh cũ dính thông tin tài khoản): ghi `recheck` cho bài với `evidence` mới (+ `metrics`, `snapshot_file`), rồi mỗi bình luận một `recheck` có `scroll_refs` trỏ vào ảnh cuộn mới (đường dẫn `evidence_paths` của recheck bài); bình luận mức cao thêm `evidence` `comment` mới. Excel hiện ảnh của lần chụp mới nhất; ảnh cũ vẫn giữ trong kho.
4. Nếu lệnh chụp bị treo: thường do có **2 tab** cùng mở (tab khôi phục phiên) hoặc cửa sổ bị che — đóng tab thừa, script luôn `bring_to_front()` trước khi chụp; `start_chrome.ps1` đã tắt chế độ ngừng vẽ khi cửa sổ bị che.

**Cách B — extension claude-in-chrome:** chỉ dùng khi `list_connected_browsers` cho thấy trình duyệt **trên chính máy này** (`onThisComputer`/`isLocal`). Ngày 30/09/2026 extension đang nối với một máy **macOS khác** → không dùng được: người dùng không thấy cửa sổ, và ảnh `save_to_disk` nằm ở máy kia. Không bao giờ thao tác trên trình duyệt ở máy khác mà không hỏi người dùng.

Quy tắc chung:
- Ảnh phải thấy tên người đăng, mốc thời gian và nội dung. Bản chữ trang → `snapshot_file`/`snapshot_text`.
- JS **chỉ để đọc** (không `click()` bằng JS, không gửi form, không sửa trang). Chỉ bấm: bộ lọc bình luận, "Xem thêm", "Xem N phản hồi", "Xem thêm bình luận". Không bấm "Tham gia", "Có" ở hộp gợi ý cài đặt, hay bất cứ nút có tác động nào.
- **Mọi giờ (`captured_at`, `counted_at`, `checked_at`) lấy từ nhật ký của script / giờ ghi file, không gõ ước lượng.** Không ghi `captured_at` của từng ảnh thì add_record lấy giờ ghi file ảnh; giờ ở tương lai bị từ chối.

## 0. Chuẩn bị

1. Mở trình duyệt theo Cách A (hoặc B nếu hợp lệ).
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

1. **Link riêng:** bấm vào mốc thời gian của bài (hoặc đọc `href` của nó) để lấy permalink. Dạng hợp lệ: `/groups/<gid>/posts/<pid>/`, `/groups/<gid>/permalink/<pid>/`, `/<user>/posts/<pfbid…>`, `/permalink.php?story_fbid=…&id=…`, `/photo/?fbid=…&set=…`, `/reel/<id>`, `/watch/?v=<id>`, `/videos/<id>`. Link `/share/…` → mở, lấy URL sau khi chuyển hướng. Không lấy được → `url_kind: "container_only"`, `url` = link nhóm. `href` của mốc thời gian là `#` cho tới khi **rê chuột** lên nó — rê chuột trước rồi mới đọc `href` (tooltip hiện cùng lúc). Link ảnh `/photo/?fbid=…&set=pcb.<pid>` hoặc `set=gm.<pid>` chỉ là **một ảnh trong bài**: bình luận nằm ở bài — mở link "Xem bài viết" ở khung bên phải (`/groups/<gid>/permalink/<pid>/`) và thu thập ở đó; link ảnh ghi vào `attachments[].url`.
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

1. Mở bộ lọc bình luận (chữ "Phù hợp nhất" phía trên bình luận) → chọn **"Tất cả bình luận"**. Menu có 3 mục: "Phù hợp nhất", "Mới nhất", "Tất cả bình luận"; dòng mô tả của "Mới nhất" cũng chứa cụm "tất cả bình luận" → chọn mục có **dòng đầu** đúng bằng "Tất cả bình luận". Nhãn nút có ký tự ẩn `﻿` ở cuối. Chụp xong kiểm tra ảnh cuộn: phía trên bình luận phải hiện chữ "Tất cả bình luận". Không có tuỳ chọn này → ghi vào `notes` của bài.
2. Lặp bấm "Xem thêm bình luận", "Xem <N> phản hồi", "Xem thêm" trong bình luận dài — tới khi không còn nút nào. Nghỉ 2–5 giây giữa các lần bấm.
3. **Đọc bình luận** (chỉ đọc DOM): dùng `READ_COMMENTS` trong `scripts/browser/capture_post.py` — bản đã chạy đúng trên 2 bài thật (7 bình luận, 2 trả lời, 1 sticker, 1 emoji). Điều đã kiểm chứng:
   - Mỗi bình luận là `div[role="article"]` có `aria-label` "Bình luận dưới tên <tên> vào <thời gian> trước" hoặc "Phản hồi bình luận của <A> dưới tên <B> …".
   - Trang phía sau dialog chứa **bản ẩn** của cùng các bình luận → chỉ lấy phần tử trong dialog cuối và đang hiển thị (`getClientRects().length`), loại trùng theo `comment_id`/`reply_comment_id`.
   - Trả lời **không** còn lồng `role="article"` → cấp 2 xác định bằng nhãn "Phản hồi…" hoặc `reply_comment_id`; `comment_id` trong link của trả lời là mã bình luận cha.
   - `fb_comment_id` = `reply_comment_id` (trả lời) hoặc `comment_id` (bình luận). Link tên người viết có `__cft__`/`__tn__` — add_record tự làm sạch.
   - Emoji là ảnh: lấy từ `img[alt]` (vd "❤️", "👍") ghép thành `text`. Sticker: `aria-label` chứa "sticker"/"nhãn dán" → `text: ""` + `attachments[{kind: "image", description: "Nhãn dán …"}]`.
   - Số cảm xúc của bình luận: `aria-label` dạng "3 cảm xúc; xem ai đã bày tỏ cảm xúc…"; không có → 0.
   Đọc DOM thất bại → dùng bản chữ trang và tách thủ công.
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
   - Mở lại bình luận (mục 4): ảnh cuộn mới đi kèm `recheck` của bài; rồi `add` lại **cả cây bình luận** đang hiển thị trong một mảng (như lần đầu, `scroll_refs` trỏ vào `evidence_paths` của recheck đó) — bình luận đã có trả `duplicate` (không sao), bình luận mới được ghi. **Không** gửi riêng các bình luận mới: nhiều bình luận giống hệt nhau (vd "+1" cùng người) chỉ phân biệt được khi gửi cả cây; bình luận cũ không còn → `recheck` `deleted` cho bình luận đó.
   - Bài từ file cũ (`reason` có "file cũ"): thu thập đầy đủ như bài mới (mục 3–4) với `supersedes` = mã bài cũ.
4. Container `joined` khác `yes`: mở lại xem đã được duyệt chưa; đã vào → `recheck` với `updates.joined = "yes"` và thêm task quét.
