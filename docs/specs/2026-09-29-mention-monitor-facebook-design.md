# Mention Monitor — Khung chung + Facebook — Thiết kế

- **Ngày:** 2026-09-29
- **Trạng thái:** Chờ duyệt
- **Phạm vi đợt này:** khung chung (kho dữ liệu, bằng chứng, dựng Excel) + nền tảng Facebook + nhập file cũ + chạy thử
- **Đợt sau (spec riêng):** YouTube, TikTok, Web (báo chí, diễn đàn, website)

---

## 1. Bối cảnh và mục tiêu

Tổng hợp **mọi lần nhắc** tới vụ việc dự án Roxana Plaza trên mạng xã hội và website — bài viết, bài chia sẻ, bình luận, trả lời bình luận, video, bài báo — thành **một file Excel master** chi tiết, có ảnh chụp màn hình làm bằng chứng cho từng mục.

Mục đích sử dụng: **cả hai**
- **Pháp lý:** danh sách bằng chứng có URL, thời điểm chụp, ảnh gốc không chỉnh sửa, mã băm — đủ để làm danh mục khi lập vi bằng qua Thừa phát lại hoặc nộp kèm đơn.
- **Dư luận:** biết ai nói gì, ở đâu, lan truyền bao nhiêu, thái độ thế nào, chủ đề gì, theo thời gian.

Chế độ chạy: **quét toàn bộ lần đầu, sau đó cập nhật định kỳ** vào cùng file master (loại trùng, phát hiện bài bị sửa/xoá).

### Tiêu chí thành công
1. Mỗi bài/bình luận thu được có: link, người đăng (như hiển thị), nguyên văn đầy đủ, thời gian, ít nhất 1 ảnh chụp chứa nó, SHA-256 của ảnh.
2. Mọi lần tìm kiếm đều có trong Nhật ký quét, kèm giới hạn/sự cố gặp phải — chỗ chưa phủ được hiện rõ.
3. Chạy cập nhật không tạo bản trùng; bài bị sửa/xoá được ghi nhận, bản cũ vẫn giữ.
4. File Excel dựng lại được bất cứ lúc nào từ kho gốc, kết quả giống nhau.

---

## 2. Nguyên tắc bắt buộc

Các nguyên tắc này được ghi thành quy tắc cứng trong `SKILL.md`.

1. **Chỉ đọc.** Không thích, không bình luận, không chia sẻ, không nhắn tin, không tự xin vào nhóm, không theo dõi trang. Không bấm nút có tác động (gửi, báo cáo, chặn…).
2. **Không vượt rào.** Không vượt CAPTCHA, checkpoint, tường đăng nhập, giới hạn tốc độ. Gặp là dừng, lưu tiến độ, báo người dùng. Không tự đăng nhập — người dùng tự đăng nhập Chrome trước.
3. **Riêng tư người đăng.** Với người đăng/bình luận là cá nhân thường, chỉ ghi những gì **hiển thị ngay trên bài**: tên hiển thị, link gắn trên tên, loại tài khoản (cá nhân/trang), huy hiệu trong nhóm. **Không** mở trang cá nhân để tra thêm, **không** ghi số điện thoại, địa chỉ, nơi làm, người thân, **không** đối chiếu danh tính giữa các nền tảng.
   - Ngoại lệ: các bên trong `key_parties` (mục 5) — vai trò của họ đã được báo chí công bố; được ghi thông tin vai trò từ nguồn báo chí.
4. **Lọc trùng tên.** Kết quả khớp tên người (vd "Ngọc Liên") nhưng không có từ ngữ cảnh của vụ việc thì **loại**, chỉ ghi link + lý do + trích đoạn ≤100 ký tự, **không ghi tên người đăng**.
5. **Bằng chứng không sửa.** Ảnh gốc và bản chữ gốc không bao giờ bị ghi đè, cắt, nén hay chú thích lên. Ảnh thu nhỏ là bản phái sinh, tạo riêng.
6. **Kho gốc chỉ ghi thêm.** Không sửa, không xoá dòng đã ghi. Mọi thay đổi (sửa, xoá, số liệu mới) là một bản ghi mới.
7. **Minh bạch độ phủ.** Không tuyên bố "đã đủ". Báo cáo cuối mỗi lần quét nêu rõ phần chưa quét được và lý do.
8. **Ngôn từ.** Nội dung nguyên văn giữ nguyên, kể cả từ ngữ gay gắt. Phân loại (thái độ, "cáo buộc") là mô tả nội dung, không phải kết luận pháp lý. Sheet Chú thích ghi rõ điều này.
9. **Dữ liệu ở máy người dùng.** Không tải dữ liệu thu được lên dịch vụ ngoài.

---

## 3. Cấu trúc thư mục

Mọi thứ nằm trong `D:\Roxana`. Skill là skill cấp dự án — chỉ hiện khi mở Claude Code tại `D:\Roxana`.

```
D:\Roxana\
├── .claude\skills\mention-monitor\
│   ├── SKILL.md                 quy trình chung, nguyên tắc (mục 2), cách gọi script
│   ├── references\
│   │   ├── schema.md            đặc tả trường dữ liệu (mục 6)
│   │   ├── classification.md    định nghĩa phân loại (mục 8)
│   │   └── facebook.md          hướng dẫn quét Facebook (mục 9)
│   └── scripts\
│       ├── common.py            đường dẫn, đọc config, kiểm tra schema, cấp mã, chuẩn hoá URL, băm
│       ├── add_record.py        ghi bản ghi vào kho (lệnh: add, check)
│       ├── status.py            thống kê, danh sách cần kiểm tra lại, tiến độ lần quét
│       ├── build_excel.py       dựng Excel từ kho
│       └── import_legacy.py     nhập file Excel cũ (chạy 1 lần)
├── config.json                  từ khoá, biến thể, từ ngữ cảnh, bên chính, danh sách nhóm/trang
├── data\records.jsonl           KHO GỐC — chỉ ghi thêm
├── screenshots\facebook\YYYY-MM-DD\...   ảnh gốc
├── snapshots\facebook\YYYY-MM-DD\...     bản chữ gốc (.txt)
├── runs\<run_id>\progress.json  tiến độ lần quét (để chạy tiếp khi bị ngắt)
├── runs\<run_id>\report.md      báo cáo cuối lần quét
├── output\Roxana_Tong_hop.xlsx  file Excel dựng ra
├── output\thumbs\               ảnh thu nhỏ (phái sinh, xoá được)
├── legacy\                      bản sao file Excel cũ
├── tests\                       pytest cho các script
└── docs\specs\                  tài liệu thiết kế
```

Git theo dõi: skill, scripts, tests, docs, `config.json`. Không đưa vào git: `data/`, `screenshots/`, `snapshots/`, `runs/`, `output/`, `legacy/` (ghi trong `.gitignore`) — dữ liệu cá nhân và ảnh dung lượng lớn.

Tất cả thời gian lưu dạng ISO 8601 có múi giờ `+07:00`.

---

## 4. Luồng hoạt động

```
config.json ─► Claude đọc SKILL.md + facebook.md
                 │
                 ▼
        Chrome (đã đăng nhập) ── tìm kiếm ─► ghi search_log
                 │
                 ▼ với mỗi bài/bình luận
   chụp ảnh (save_to_disk) + lưu bản chữ
                 │
                 ▼
   add_record.py add  ── kiểm tra schema, loại trùng, cấp mã,
                          chép ảnh vào screenshots\, tính SHA-256,
                          ghi thêm 1 dòng vào records.jsonl
                 │
                 ▼ cuối lần quét
   build_excel.py ─► output\Roxana_Tong_hop.xlsx
   status.py      ─► runs\<run_id>\report.md
```

---

## 5. config.json

```json
{
  "project_name": "Roxana Plaza",
  "timezone": "+07:00",
  "keyword_groups": [
    {"id": "roxana",   "label": "Roxana Plaza",
     "terms": ["Roxana Plaza", "Roxana", "Roxanna", "Roxanna Plaza", "Roxana Plaza Bình Dương", "#roxanaplaza"]},
    {"id": "tuongphong", "label": "CĐT Tường Phong",
     "terms": ["Tường Phong", "Tuong Phong", "Công ty Tường Phong", "CĐT Tường Phong"]},
    {"id": "lien", "label": "Bà Phạm Thị Ngọc Liên",
     "terms": ["Phạm Thị Ngọc Liên", "Phạm Ngọc Liên", "Pham Thi Ngoc Lien", "Pham Ngoc Lien", "bà Ngọc Liên"],
     "requires_context": true},
    {"id": "naviland", "label": "Naviland",
     "terms": ["Naviland", "Navi Land", "Nvl Roxana"]},
    {"id": "launamtuong", "label": "Ông Lầu Nam Tường",
     "terms": ["Lầu Nam Tường", "Lau Nam Tuong"], "requires_context": true},
    {"id": "tuyen", "label": "Bà Dương Thị Phương Tuyền",
     "terms": ["Dương Thị Phương Tuyền", "Phương Tuyền", "Duong Thi Phuong Tuyen"], "requires_context": true},
    {"id": "viethome", "label": "Viethome",
     "terms": ["Viethome", "Viet Home Roxana"], "requires_context": true}
  ],
  "context_terms": ["Roxana", "Tường Phong", "Tuong Phong", "Naviland", "Viethome", "Bình Hoà", "Thuận An", "đòi nhà"],
  "key_parties": [
    {"id": "tuongphong", "name": "Công ty TNHH XD-DV-TM-Đầu tư BĐS Tường Phong", "kind": "Doanh nghiệp",
     "role": "Chủ đầu tư chính thức, hợp pháp của dự án Roxana Plaza…", "keyword_group": "tuongphong", "primary": true}
  ],
  "containers": [
    {"platform": "facebook", "name": "ROXANA PLAZA - HÀNH TRÌNH ĐÒI NHÀ",
     "url": "https://www.facebook.com/groups/427692059062534/",
     "privacy": "unknown", "joined": "unknown", "scan_mode": "full"}
  ],
  "recheck_policy_days": {"cao": 0, "trung_binh": 30, "thap": 90}
}
```

- `requires_context: true` → kết quả chỉ được giữ khi nội dung bài (hoặc bài chứa bình luận, hoặc tên nhóm/trang) có ít nhất một `context_terms`. Không có → bản ghi `exclusion`.
- Tìm kiếm luôn chạy cả bản có dấu và không dấu của mỗi term.
- `key_parties` được `import_legacy.py` điền đủ 12 bên từ sheet "Các bên liên quan" của file cũ (ví dụ trên chỉ có 1 bên).
- **Bên chính** (`primary: true`) = 6 bên có nhóm từ khoá: Tường Phong, Naviland, Viethome, ông Lầu Nam Tường, bà Phạm Thị Ngọc Liên, bà Dương Thị Phương Tuyền. 6 bên còn lại (ông Hoàng Tùng, ông Nguyễn Anh Đào, 4 cơ quan nhà nước) là bên liên quan khác — vẫn được gắn vào `entities_mentioned` khi được nhắc, nhưng không dùng làm từ khoá tìm kiếm.
- `containers[].scan_mode`: `full` (nhóm/trang chuyên đề — quét toàn bộ bài) hoặc `keyword` (nhóm chung — chỉ tìm trong nhóm theo từ khoá). Skill được phép thêm container mới phát hiện vào config.

---

## 6. Mô hình dữ liệu — `data/records.jsonl`

Mỗi dòng là một JSON. Trường chung của mọi bản ghi:

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `record_type` | enum | `source` · `comment` · `container` · `search_log` · `recheck` · `exclusion` · `event` |
| `id` | string | do `add_record.py` cấp, không do Claude tự đặt |
| `run_id` | string | `RUN-2026-09-29-01` |
| `recorded_at` | ISO | thời điểm ghi vào kho |
| `origin` | enum | `scan` (thu thập) · `legacy` (từ file cũ) |

### Định dạng mã

| Loại | Mẫu | Ví dụ |
|---|---|---|
| source Facebook | `FB-P` + 5 số | `FB-P00012` |
| source báo chí (từ file cũ, đợt Web sau sẽ dùng tiếp) | `WEB-P` + 5 số | `WEB-P00003` |
| comment Facebook | `FB-C` + 6 số | `FB-C000145` |
| container | `FB-G` + 4 số | `FB-G0003` |
| search_log | `LOG-` + 6 số | |
| recheck | `CHK-` + 6 số | |
| exclusion | `EXC-` + 6 số | |
| event | `EVT-` + 4 số | |

### 6.1 `source` — bài viết / chia sẻ / ảnh / video / reel / bài báo

| Trường | Bắt buộc | Mô tả |
|---|---|---|
| `platform` | ✓ | `facebook` · `web` (· `youtube`, `tiktok` đợt sau) |
| `content_type` | ✓ | `post` · `shared_post` · `photo` · `video` · `reel` · `live` · `article` |
| `url` | ✓ | link tốt nhất có được |
| `url_kind` | ✓ | `permalink` · `container_only` (chỉ có link nhóm) · `none` |
| `container_id` | | mã container (FB-G…) nếu đăng trong nhóm/trang |
| `container_name` | | tên nhóm/trang như hiển thị |
| `author_name` | ✓ | tên hiển thị |
| `author_url` | | link gắn trên tên; không có thì `null` |
| `author_kind` | ✓ | `person` · `page` · `anonymous` (thành viên ẩn danh) · `unknown` |
| `author_badge` | | vd `Quản trị viên`, `Người kiểm duyệt`, `Fan cứng` |
| `posted_at_raw` | ✓ | chuỗi hiển thị nguyên gốc, vd `2 giờ`, `9 tháng 3, 2025` |
| `posted_at` | | ISO đã quy đổi |
| `posted_at_precision` | ✓ | `exact` (lấy từ tooltip khi rê chuột) · `day` · `month` · `year` · `relative_estimate` · `unknown` |
| `text` | ✓ | nguyên văn đầy đủ (đã mở "Xem thêm"); bài chỉ có ảnh thì `""` và mô tả ở `attachments` |
| `attachments` | | danh sách `{kind: image|video|link|document, description, transcribed_text, url}` |
| `shared_from` | | `{url, author_name, author_url, text_excerpt}` nếu là bài chia sẻ |
| `metrics` | | `{reactions, comments, shares, views, counted_at}` — số hiển thị tại thời điểm đếm |
| `comments_collected` | | số bình luận đã thu (script tự tính khi dựng Excel) |
| `keywords_matched` | ✓ | danh sách `keyword_groups.id` khớp |
| `entities_mentioned` | | danh sách `key_parties.id` được nhắc |
| `topics` | | xem mục 8 |
| `tone` | ✓ | xem mục 8 |
| `claim_type` | ✓ | xem mục 8 |
| `importance` | ✓ | `cao` · `trung_binh` · `thap` |
| `importance_reason` | ✓ | lý do ngắn |
| `evidence` | ✓ (scan) | danh sách ảnh, xem 6.8 |
| `snapshot_file` | ✓ (scan) | đường dẫn bản chữ gốc |
| `captured_at` | ✓ | thời điểm thu thập |
| `notes` | | |
| `legacy_ref` | | với `origin=legacy`: tên sheet + dòng trong file cũ |

`origin=legacy` được miễn `evidence`, `snapshot_file`, `tone`, `claim_type`, `importance_reason`; Excel đánh dấu "Từ file cũ — chưa có ảnh".

### 6.2 `comment`

| Trường | Bắt buộc | Mô tả |
|---|---|---|
| `source_id` | ✓ | bài chứa bình luận |
| `parent_comment_id` | | nếu là trả lời |
| `depth` | ✓ | 1 = bình luận, 2 = trả lời, 3 = trả lời của trả lời |
| `url` | | link bình luận (`?comment_id=…`) nếu lấy được |
| `fb_comment_id` | | id bình luận của Facebook nếu lấy được |
| `author_name`, `author_url`, `author_kind`, `author_badge` | như source | |
| `posted_at_raw`, `posted_at`, `posted_at_precision` | như source | |
| `text` | ✓ | nguyên văn |
| `attachments` | | ảnh/sticker/GIF/link trong bình luận |
| `reactions` | | |
| `reply_count` | | |
| `keywords_matched`, `entities_mentioned`, `topics`, `tone`, `claim_type`, `importance`, `importance_reason` | như source (`importance_reason` chỉ bắt buộc khi `cao`) | |
| `scroll_refs` | ✓ | danh sách `{file, position}` — ảnh cuộn chứa bình luận này và thứ tự trong ảnh |
| `evidence` | ✓ khi `importance=cao` | ảnh chụp riêng |
| `captured_at` | ✓ | |

### 6.3 `container` — nhóm / trang / kênh

`platform`, `kind` (`group` · `page` · `channel`), `name`, `url`, `privacy` (`public` · `private` · `unknown`), `member_count` + `member_count_at`, `topic_dedicated` (bool — chuyên về Roxana), `joined` (`yes` · `no` · `pending` · `unknown`), `scan_mode` (`full` · `keyword`), `last_scanned_at`, `notes`.

Một container `private` + `joined != yes` = **Cần xin vào nhóm**.

### 6.4 `search_log`

`platform`, `scope` (`global` · `container`), `container_id`, `section` (`posts` · `groups` · `pages` · `videos` · `photos` · `hashtag` · `group_feed` · `in_group_search`), `query`, `filters` (vd `{"year": 2021}` hoặc `{"sort": "recent"}`), `started_at`, `ended_at`, `results_seen`, `results_new`, `results_duplicate`, `results_excluded`, `reached_end` (bool — cuộn tới hết kết quả), `issues` (vd "Facebook chỉ trả 40 kết quả", "yêu cầu đăng nhập lại"), `notes`.

### 6.5 `recheck`

`target_id`, `checked_at`, `status` (`active` · `edited` · `deleted` · `unavailable` — không truy cập được, vd bị chặn/nhóm rời), `new_text` (khi `edited`), `metrics` (số liệu mới), `evidence` (ảnh lần kiểm tra), `notes`.

Khi dựng Excel, trạng thái và số liệu **mới nhất** của mỗi mục lấy từ recheck gần nhất; lịch sử đầy đủ ở sheet Lịch sử thay đổi.

### 6.6 `exclusion`

`url`, `excerpt` (≤100 ký tự), `keywords_matched`, `reason` (vd "Trùng tên — không có từ ngữ cảnh"), `search_log_id`. Không có trường tên người đăng.

### 6.7 `event` — mốc dòng thời gian

`date_raw`, `date` (ISO, có thể chỉ năm/tháng), `description`, `source_text`, `related_ids` (mã source/comment), `reliability` (`bao_chi` — báo chí chính thống · `van_ban` — có văn bản chính thức kèm · `mxh` — mạng xã hội, chưa kiểm chứng).

### 6.8 Bằng chứng (`evidence[]`)

Mỗi phần tử: `file` (đường dẫn tương đối từ `D:\Roxana`), `sha256`, `captured_at`, `kind`, `shows` (mô tả ngắn ảnh chụp phần nào), `capture_tool` (`claude-in-chrome` · `playwright`).

`kind`:
- `post` — thân bài (nhiều ảnh nếu bài dài, đánh số `_01`, `_02`…)
- `attach` — ảnh đính kèm mở lớn (văn bản, giấy mời…)
- `cscroll` — ảnh cuộn phần bình luận (thuộc source)
- `comment` — ảnh riêng một bình luận

Tên file do `add_record.py` đặt: `screenshots/facebook/<YYYY-MM-DD>/<ID>_<kind>_<NN>.png`, vd `FB-P00012_cscroll_07.png`, `FB-C000145_comment_01.png`.

Ảnh cuộn bình luận được ghi vào `evidence` của **source** (kind `cscroll`); mỗi comment trỏ tới chúng qua `scroll_refs`.

### 6.9 Loại trùng

| Loại | Khoá trùng |
|---|---|
| source có permalink | URL đã chuẩn hoá (bỏ tham số theo dõi như `__cft__`, `__tn__`, `ref`, `mibextid`; `m.`/`mbasic.`/`web.` → `www.`; giữ `fbid`, `set`, `v`, `story_fbid`, `id`, `comment_id`) |
| source `container_only` / `none` | băm(`container_id` + `author_name` + 200 ký tự đầu của `text` đã chuẩn hoá khoảng trắng) |
| comment | `fb_comment_id` nếu có; không thì băm(`source_id` + `author_name` + `text` chuẩn hoá + `posted_at_raw`) |
| container | URL chuẩn hoá |

Gặp trùng: `add_record.py` trả `{"status": "duplicate", "existing_id": ...}` và không ghi. Nếu nội dung khác bản cũ (bài bị sửa) → Claude ghi `recheck` với `status=edited`.

Trùng giữa bản `legacy` và bản `scan` của cùng một bài: bản scan được ghi thành bản ghi mới có trường `supersedes` = mã bản legacy; Excel chỉ hiện bản scan, ghi chú "thay cho <mã legacy>".

---

## 7. Scripts

Python 3 (máy có 3.14), thư viện có sẵn: `openpyxl`, `Pillow`, `pytest`. Mọi script nhận `--project D:\Roxana` (mặc định: thư mục cha của `.claude`). Đầu ra dạng JSON để Claude đọc. Mã hoá UTF-8 (đặt `PYTHONIOENCODING=utf-8` hoặc tự cấu hình stdout — console Windows mặc định cp1252 làm vỡ tiếng Việt).

### `add_record.py`
- `add --json <file|->` — nhận 1 bản ghi hoặc mảng bản ghi (để ghi hàng loạt bình luận).
  - Kiểm tra trường bắt buộc theo `record_type` và `origin`.
  - Với mỗi `evidence[].file` là đường dẫn tạm (vd ảnh từ `save_to_disk`): chép vào vị trí chuẩn với tên chuẩn, tính SHA-256 trên **bản đã chép**, ghi đường dẫn mới. Không xoá file tạm.
  - Bản ghi source `origin=scan` phải có `snapshot_text` (chuỗi — script ghi ra `snapshots/facebook/<YYYY-MM-DD>/<ID>.txt` và đặt `snapshot_file`) hoặc `snapshot_file` là đường dẫn file có sẵn (script chép vào vị trí chuẩn). Thiếu cả hai → `invalid`.
  - Kết quả trả về kèm `evidence_paths` — đường dẫn chuẩn của từng ảnh đã chép, để dùng cho `scroll_refs` của bình luận.
  - `scroll_refs[].file` của comment phải là đường dẫn chuẩn đã tồn tại trong `screenshots/` và thuộc evidence `cscroll` của `source_id` (hoặc của một recheck của source đó) → không thì `invalid`.
  - Loại trùng (6.9), cấp mã, ghi thêm vào `records.jsonl` (mở file ở chế độ append, ghi xong `flush` + `fsync`).
  - Trả `[{status: added|duplicate|invalid, id, existing_id?, errors?}]`.
  - Bản ghi comment cấp mã theo thứ tự trong mảng; `parent_comment_id` có thể trỏ tới chỉ số trong cùng mảng dạng `"@3"` để ghi cây bình luận một lần.
- `check --url <url>` / `check --key-of <json>` — cho biết đã có trong kho chưa (dùng trước khi mất công chụp).

### `status.py`
- `stats` — số bản ghi theo loại/nền tảng/mức quan trọng.
- `recheck-due --run <run_id>` — danh sách source cần kiểm tra lại theo `recheck_policy_days`.
- `progress --run <run_id>` — đọc/in `progress.json`.
- `report --run <run_id>` — viết `runs/<run_id>/report.md`: số mới, số trùng, số loại trừ, bài bị sửa/xoá, container cần xin vào, các `issues` trong search_log, phần chưa quét.

### `build_excel.py`
- Đọc toàn bộ `records.jsonl`, gộp recheck, bỏ bản legacy đã bị thay, dựng `output/Roxana_Tong_hop.xlsx` (mục 10). Ghi file tạm rồi đổi tên — không làm hỏng file cũ nếu lỗi giữa chừng.
- Tạo ảnh thu nhỏ vào `output/thumbs/` (rộng 240px, giữ tỉ lệ, JPEG chất lượng 80); chỉ tạo lại khi thiếu.
- Nếu file Excel đang mở trong Excel (bị khoá) → báo lỗi rõ ràng, không ghi đè.

### `import_legacy.py`
- Chép file cũ vào `legacy/`, đọc 4 sheet:
  - "Tóm tắt vụ việc" → 11 `event` (điền `reliability` theo cột Nguồn: bài đăng/ảnh Facebook → `mxh`, còn lại → `bao_chi`) + đoạn lưu ý cuối → dùng cho sheet Chú thích.
  - "Các bên liên quan" → `key_parties` trong `config.json` (12 bên; 6 bên chính được gắn `keyword_group` và `primary: true`).
  - "Bài viết MXH nổi bật" → 11 `source` (`platform=facebook`, `origin=legacy`) + container tương ứng (loại trùng theo URL nhóm).
  - "Nguồn báo chí" → 14 `source` (`platform=web`, `content_type=article`, `origin=legacy`).
- Chạy lại lần 2 không tạo bản trùng.

---

## 8. Phân loại (`references/classification.md`)

**`tone`** — thái độ của nội dung đối với các bên được nhắc:
- `tich_cuc` — khen, bênh vực, ghi nhận
- `trung_lap` — đưa tin, hỏi, thông báo, không bày tỏ thái độ
- `tieu_cuc` — phê phán, phản đối, bất bình, dùng lời lẽ bình thường
- `gay_gat` — chửi bới, xúc phạm, đe doạ, dùng từ thô tục

**`claim_type`** (chọn 1, ưu tiên theo thứ tự):
- `van_ban` — kèm văn bản/tài liệu (giấy mời, văn bản toà, kết luận thanh tra, hợp đồng)
- `cao_buoc` — quy kết hành vi sai trái cho người/tổ chức cụ thể
- `keu_goi` — kêu gọi hành động (tố cáo, tập trung, ký đơn…)
- `thong_tin` — tường thuật sự kiện, cập nhật tiến trình
- `tin_don` — thông tin không nguồn, "nghe nói"
- `y_kien` — bày tỏ quan điểm, cảm xúc
- `hoi_dap` — hỏi hoặc trả lời câu hỏi

**`topics`** (chọn nhiều): `ban_chui` · `tang_gia_ky_lai` · `cham_ban_giao` · `thanh_tra` · `toa_an` · `cong_an_to_giac` · `tuan_hanh` · `doi_thoai` · `tranh_chap_noi_bo` · `xay_sai_phep` · `hoan_tien` · `khac`

**`importance`**:
- `cao` — ít nhất một: kèm văn bản chính thức · nêu đích danh một bên chính kèm cáo buộc · thông tin mới về tiến trình pháp lý/hành chính · do admin nhóm hoặc một bên chính đăng · tương tác ≥ 100 (thích + bình luận + chia sẻ) · bình luận có ≥ 20 lượt thích
- `trung_binh` — nhắc tới vụ việc hoặc các bên với nội dung có thông tin/ý kiến cụ thể
- `thap` — ngắn, không thêm thông tin (vd "theo dõi", "hóng", "+1", sticker)

Bình luận `thap` vẫn được ghi nguyên văn và có `scroll_refs` — không bỏ.

---

## 9. Hướng dẫn quét Facebook (`references/facebook.md`)

### 9.0 Chuẩn bị
1. `tabs_context_mcp` — xác nhận Chrome kết nối; mở tab mới.
2. Mở `https://www.facebook.com/` — xác nhận đã đăng nhập (không có form đăng nhập). Chưa đăng nhập → dừng, nhờ người dùng tự đăng nhập.
3. Đọc `config.json`; chạy `status.py stats`.
4. Tạo `run_id` và `runs/<run_id>/progress.json`:
   ```json
   {"run_id": "RUN-2026-09-29-01", "mode": "full|update", "started_at": "...",
    "tasks": [{"id": "T001", "kind": "search", "section": "posts", "query": "Roxana Plaza",
               "filters": {"year": 2021}, "status": "pending|done|blocked", "log_id": null}]}
   ```
   Có `progress.json` dở dang → chạy tiếp các task `pending`, không làm lại task `done`.

### 9.1 Ma trận tìm kiếm (lần quét đầu)
Với mỗi term trong mỗi `keyword_groups` (cả có dấu và không dấu):

| Mục | URL | Bộ lọc |
|---|---|---|
| Bài viết | `https://www.facebook.com/search/posts/?q=<term>` | lần lượt "Ngày đăng" = từng năm 2017 → 2026; thêm 1 lượt "Bài viết mới nhất" |
| Nhóm | `/search/groups/?q=<term>` | — |
| Trang | `/search/pages/?q=<term>` | — |
| Video | `/search/videos/?q=<term>` | — |
| Ảnh | `/search/photos/?q=<term>` | — |
| Hashtag | `/hashtag/<term-viết-liền-không-dấu>` | chỉ với term của nhóm `roxana`, `tuongphong`, `naviland` |

Với mỗi container trong config:
- `scan_mode=full`: mở `/groups/<id>/?sorting_setting=CHRONOLOGICAL` (nhóm) hoặc trang, cuộn từ mới nhất tới bài cũ nhất, thu **mọi bài**.
- `scan_mode=keyword`: `/groups/<id>/search/?q=<term>` cho mọi term.

Nhóm/trang mới phát hiện: ghi `container`; tên hoặc mô tả có `context_terms` → `topic_dedicated=true`, `scan_mode=full`, thêm task. Nhóm kín chưa tham gia → ghi `joined=no`, không quét, đưa vào danh sách "Cần xin vào".

Cuộn danh sách kết quả tới khi Facebook hiện "Hết kết quả" / không tải thêm sau 3 lần cuộn → `reached_end=true`. Dừng sớm vì bất cứ lý do gì → `reached_end=false` + ghi `issues`.

### 9.2 Thu thập một bài
1. Lấy URL ứng viên, chạy `add_record.py check --url` — đã có và không cần kiểm tra lại thì bỏ qua.
2. Mở permalink: bấm vào mốc thời gian của bài. Dạng hợp lệ: `/groups/<gid>/posts/<pid>/`, `/groups/<gid>/permalink/<pid>/`, `/<user>/posts/<pfbid…>`, `/permalink.php?story_fbid=…&id=…`, `/photo/?fbid=…&set=…`, `/reel/<id>`, `/watch/?v=<id>`, `/videos/<id>`. Link `/share/…` → mở rồi lấy URL sau khi chuyển hướng. Không lấy được → `url_kind=container_only`, `url` = link nhóm.
3. Rê chuột lên mốc thời gian để lấy thời gian chính xác từ tooltip → `posted_at_precision=exact`.
4. Bấm mọi "Xem thêm" trong thân bài.
5. Chụp ảnh thân bài (`save_to_disk: true`), cuộn và chụp tiếp nếu bài dài hơn một màn hình. Ảnh phải thấy tên người đăng, mốc thời gian, nội dung.
6. Lưu bản chữ: `get_page_text` → đưa vào `snapshot_text`.
7. Ảnh đính kèm: mở từng ảnh; ảnh là văn bản/tài liệu → chụp `attach` (dùng `zoom` nếu chữ nhỏ) và chép lại chữ vào `attachments[].transcribed_text`. Album nhiều ảnh → mở hết.
8. Bài chia sẻ: ghi `shared_from`; bài gốc chưa có trong kho → thêm task thu thập bài gốc.
9. Ghi số liệu tương tác hiển thị + `counted_at`.
10. Phân loại (mục 8). **Chưa ghi vào kho** — thu thập bình luận trước (9.3) để ảnh cuộn bình luận vào cùng `evidence` của bài.

### 9.3 Thu thập bình luận
1. Mở bộ lọc bình luận, chọn **"Tất cả bình luận"** (không để "Phù hợp nhất"). Không có tuỳ chọn này → ghi `issues`.
2. Lặp: bấm "Xem thêm bình luận", "Xem N phản hồi", "Xem thêm" trong bình luận dài — tới khi không còn nút nào. Nghỉ 2–5 giây giữa các lần bấm.
3. Đọc bình luận bằng `javascript_tool` **chỉ đọc DOM** (không bấm, không gửi): lấy các phần tử `role="article"` trong khu vực bình luận — tên, link tên, huy hiệu, nguyên văn, mốc thời gian, link `comment_id`, số cảm xúc, cấp lồng. Cách dò DOM cụ thể được hoàn thiện ở bước chạy thử (mục 12) vì Facebook đổi cấu trúc thường xuyên; không đọc được bằng DOM → dùng `get_page_text` và tách thủ công.
4. Chụp ảnh cuộn: cuộn lên đầu khu vực bình luận; lặp chụp (`save_to_disk`) → cuộn khoảng 80% chiều cao màn hình (giữ phần chồng lấn để không hở bình luận). Mỗi ảnh là một evidence `cscroll` của source. Ghi bình luận nào ở ảnh nào, thứ tự mấy → `scroll_refs`. Bình luận nằm vắt qua hai ảnh → ghi cả hai.
5. Bình luận `cao` → cuộn tới, chụp riêng (`zoom` vùng bình luận), đưa vào `evidence`.
6. Ghi vào kho theo thứ tự:
   1. `add_record.py add` bản ghi **source** với `evidence` gồm ảnh `post`, `attach` và toàn bộ `cscroll` → nhận `id` và `evidence_paths`.
   2. `add_record.py add` **cả cây bình luận** một lần (mảng; `source_id` = mã vừa nhận; `"@chỉ_số"` cho `parent_comment_id`; `scroll_refs[].file` = đường dẫn chuẩn từ `evidence_paths`).
   - Bài không có bình luận: bỏ bước 3–5, ghi source luôn.
   - Lần cập nhật (9.5): ảnh cuộn mới đi kèm bản ghi `recheck` của source; bình luận mới trỏ `scroll_refs` tới ảnh của recheck đó.
7. So `comments_collected` với `metrics.comments`; lệch > 5% → ghi `issues` vào `notes` của recheck ("Facebook hiển thị 604, thu được 571 — có thể do bình luận bị ẩn/xoá/lọc spam").

### 9.4 Nhịp độ và điều kiện dừng
- Nghỉ ngẫu nhiên 3–8 giây giữa các lần mở trang, 2–5 giây giữa các lần bấm mở bình luận.
- Làm theo lô: mỗi lô là một container hoặc một cụm task tìm kiếm; hết lô → cập nhật `progress.json`.
- **Dừng ngay** khi thấy: "Bạn tạm thời bị chặn", checkpoint/xác minh danh tính, CAPTCHA, form đăng nhập, cảnh báo hành vi tự động. Đánh task hiện tại `blocked`, ghi `issues`, lưu tiến độ, dựng Excel với dữ liệu đã có, báo người dùng. Không thử lại cùng thao tác.
- Không mở hộp thoại/nút có thể gây alert trình duyệt.

### 9.5 Lần cập nhật (`mode=update`)
1. Ma trận tìm kiếm với bộ lọc "Mới nhất" thay cho lọc theo năm; dừng cuộn khi gặp liên tiếp 10 kết quả đã có trong kho.
2. Container `full`: cuộn feed tới khi gặp liên tiếp 10 bài đã có.
3. `status.py recheck-due` → mở lại từng bài:
   - Không còn ("Nội dung này hiện không khả dụng") → `recheck` `deleted`, chụp ảnh thông báo.
   - Nội dung khác → `recheck` `edited` + `new_text` + ảnh mới.
   - Còn → `recheck` `active` + số liệu mới.
   - Mở lại bình luận: bình luận mới → `add` như 9.3; bình luận cũ không còn → `recheck` `deleted` cho comment đó.
4. Container `joined=no` → mở lại xem người dùng đã được duyệt chưa; đã vào → `scan_mode` như cũ, thêm task quét.

### 9.6 Kết thúc lần quét
`build_excel.py` → `status.py report` → trình bày cho người dùng: số mới, bài quan trọng mới, bài bị sửa/xoá, nhóm cần xin vào, phần chưa quét được.

---

## 10. File Excel — `output/Roxana_Tong_hop.xlsx`

Định dạng chung: font Arial 10; hàng tiêu đề đậm, nền xám nhạt, cố định (freeze) hàng tiêu đề và cột Mã; bật AutoFilter; ô nội dung dài xuống dòng; độ rộng cột cố định hợp lý; link là hyperlink bấm được. Ảnh thu nhỏ nhúng trong ô, chiều cao hàng vừa ảnh. Link ảnh gốc là **đường dẫn tương đối** (`../screenshots/...`) — phải chép cả thư mục `D:\Roxana` khi chuyển máy. Đặt `fullCalcOnLoad` để Excel tự tính công thức khi mở.

| # | Sheet | Mỗi dòng | Cột chính |
|---|---|---|---|
| 1 | **Tổng quan** | — | Tên dự án, cập nhật lúc, lần quét gần nhất · tổng nguồn / bình luận / container / số cần xin vào · theo nền tảng · theo bên được nhắc (6 bên chính + bên khác) · theo thái độ · theo mức quan trọng · theo tháng đăng (chỉ đếm mục có `posted_at` tới ngày hoặc tháng; số mục không rõ ngày ghi riêng) · bảng "Chưa quét được" (các `issues` gần nhất). Số liệu là công thức `COUNTIF/COUNTIFS` trỏ tới các sheet dữ liệu |
| 2 | **Dòng thời gian** | 1 event | Ngày · Sự kiện · Nguồn · Mã liên quan (link nội bộ) · Độ tin cậy |
| 3 | **Bài viết & Nguồn** | 1 source | Mã · Nền tảng · Loại · Ảnh (thumb) · Mở ảnh gốc · Số ảnh · Nhóm/Trang · Người đăng · Link người đăng · Loại TK · Huy hiệu · Thời gian (gốc) · Ngày đăng · Độ chính xác · Nội dung nguyên văn · Đính kèm / chữ trong ảnh · Chia sẻ từ · Thích · Bình luận (FB) · Bình luận (đã thu) · Chia sẻ · Lượt xem · Đếm lúc · Từ khoá · Bên được nhắc · Chủ đề · Thái độ · Loại nội dung · Mức quan trọng · Lý do · Link bài · Loại link · Trạng thái · Kiểm tra lần cuối · SHA-256 ảnh chính · Bản chữ gốc · Thu thập lúc · Lần quét · Nguồn dữ liệu (Quét / Từ file cũ) · Ghi chú |
| 4 | **Bình luận** | 1 comment | Mã · Thuộc bài (link nội bộ tới sheet 3) · Trả lời cho · Cấp · Ảnh riêng (thumb) · Ảnh cuộn (file + vị trí, link) · Người viết · Link người viết · Huy hiệu · Thời gian (gốc) · Ngày · Nội dung nguyên văn · Đính kèm · Thích · Số phản hồi · Từ khoá · Bên được nhắc · Chủ đề · Thái độ · Loại · Mức quan trọng · Lý do · Link bình luận · Trạng thái · SHA-256 · Thu thập lúc · Ghi chú |
| 5 | **Người & Tổ chức** | 1 bên chính hoặc 1 người đăng/bình luận | Tên · Nhóm (Bên chính / Người đăng / Người bình luận) · Loại · Link (như hiển thị) · Vai trò (chỉ bên chính) · Số bài đăng · Số bình luận · Số lần được nhắc (chỉ các bên trong `key_parties`) · Xuất hiện lần đầu · Lần gần nhất. Gộp người theo `author_url`, không có thì theo tên. Số đếm là công thức |
| 6 | **Nhóm & Trang** | 1 container | Mã · Tên · Loại · Link · Công khai/Kín · Thành viên · Chuyên đề Roxana · Đã tham gia · Cách quét · Số bài thu được (công thức) · Quét lần cuối · Ghi chú. Dòng "Cần xin vào" tô nền vàng |
| 7 | **Bằng chứng quan trọng** | 1 source hoặc comment `cao` | Mã · Loại · Ảnh (thumb lớn 480px) · Tóm tắt nội dung (≤300 ký tự) · Người đăng · Link · Thời gian · Lý do quan trọng · File ảnh gốc · SHA-256 · Thu thập lúc |
| 8 | **Nhật ký quét** | 1 search_log | Mã · Lần quét · Bắt đầu · Kết thúc · Nền tảng · Phạm vi · Mục · Từ khoá · Bộ lọc · Đã xem · Mới · Trùng · Loại trừ · Hết kết quả · Sự cố/giới hạn · Ghi chú |
| 9 | **Lịch sử thay đổi** | 1 recheck có thay đổi (`edited`, `deleted`, `unavailable`, hoặc số liệu tăng) | Mã · Đối tượng (link nội bộ) · Kiểm tra lúc · Trạng thái · Nội dung mới · Số liệu mới · Ảnh · Ghi chú |
| 10 | **Đã loại trừ** | 1 exclusion | Mã · Thời điểm · Link · Trích đoạn · Từ khoá khớp · Lý do |
| 11 | **Chú thích** | — | Ý nghĩa từng cột · định nghĩa phân loại (mục 8) · cách đọc mã · cách kiểm tra SHA-256 (`certutil -hashfile <file> SHA256`) · lưu ý ngôn từ (mục 2.8) + đoạn lưu ý từ file cũ · lưu ý chép cả thư mục |

(So với bản trình bày trong trao đổi: thêm sheet **Đã loại trừ** để việc lọc trùng tên có thể kiểm tra lại được.)

Giá trị enum hiển thị bằng tiếng Việt có dấu (vd `trung_binh` → "Trung bình", `container_only` → "Chỉ có link nhóm").

---

## 11. Xử lý lỗi

| Tình huống | Xử lý |
|---|---|
| Chrome không kết nối / chưa đăng nhập Facebook | Dừng trước khi quét, hướng dẫn người dùng |
| Bị chặn / checkpoint / CAPTCHA | Mục 9.4 |
| Nội dung không khả dụng | `recheck deleted` (bài đã có) hoặc bỏ qua + ghi `issues` (bài mới) |
| `save_to_disk` không trả đường dẫn / lỗi chụp | Thử lại 1 lần; vẫn lỗi → chuyển sang Playwright `browser_take_screenshot` (cần người dùng đăng nhập Facebook trong trình duyệt Playwright); vẫn lỗi → đánh task `blocked` và báo người dùng. **Không** ghi bản ghi `origin=scan` thiếu ảnh |
| `add_record.py` trả `invalid` | Sửa bản ghi theo `errors`, gửi lại; không bỏ qua trường bắt buộc |
| Phiên bị ngắt / hết ngữ cảnh | Chạy lại skill → đọc `progress.json`, tiếp tục task `pending` |
| Excel đang mở khi dựng | `build_excel.py` báo, người dùng đóng Excel rồi chạy lại |
| `records.jsonl` có dòng hỏng (vd mất điện giữa lúc ghi) | Script đọc bỏ qua dòng cuối không phải JSON hợp lệ, báo cảnh báo; không tự xoá |

---

## 12. Kiểm thử và nghiệm thu

### 12.1 Test tự động (pytest, `tests/`, viết test trước)
- **common:** chuẩn hoá URL Facebook (các dạng ở 9.2, bỏ tham số theo dõi); khoá trùng; bỏ dấu tiếng Việt; cấp mã tăng dần theo loại.
- **add_record:** từ chối thiếu trường bắt buộc (theo loại và origin); chép ảnh đúng tên chuẩn; SHA-256 khớp `hashlib` tính độc lập; trùng → `duplicate` và kho không đổi; mảng comment với `"@n"` tạo đúng cây; không bao giờ sửa dòng đã có (so sánh byte các dòng cũ trước/sau); `check --url` đúng.
- **build_excel:** với bộ dữ liệu mẫu (vài source, comment lồng, container kín, recheck edited/deleted, exclusion, legacy bị thay): đủ 11 sheet đúng tên; số dòng mỗi sheet đúng; ảnh thu nhỏ neo đúng ô; hyperlink ảnh và link nội bộ đúng đích; trạng thái mới nhất lấy từ recheck; bản legacy bị thay không hiện; công thức Tổng quan trỏ đúng vùng và kết quả tự tính trong Python khớp giá trị mong đợi; chạy hai lần ra nội dung ô giống nhau.
- **import_legacy:** từ file cũ thật → 11 event, 12 key_parties, 11 source Facebook, 14 source web, container đúng; chạy lần 2 không thêm gì.

Máy chưa có LibreOffice nên không chạy được `recalc.py`; công thức được kiểm bằng test ở trên và bằng cách mở file trong Excel lúc nghiệm thu.

### 12.2 Chạy thử thật (trước khi quét lớn)
Trên 2 bài có trong file cũ:
- **Bài #6** (Quyết Chiến Roxana, ảnh Giấy mời) — kiểm tra đính kèm văn bản + chép chữ trong ảnh.
- **Bài #4** (Huynh Bich Diem, 4 bình luận) — kiểm tra trọn quy trình bình luận.

Đạt khi: lấy được permalink · nội dung đầy đủ · ảnh lưu đúng chỗ, SHA-256 khớp · số bình luận thu được = số Facebook hiển thị · bản scan thay bản legacy · Excel mở được trong Excel, ảnh và link hoạt động. Ở bước này cũng chốt: cách `save_to_disk` trả đường dẫn, cách dò DOM bình luận (cập nhật vào `facebook.md`).

**Người dùng duyệt file Excel chạy thử trước khi quét toàn bộ.**

### 12.3 Kiểm thử skill
Một agent phụ không có ngữ cảnh trước đọc `SKILL.md` + `facebook.md` và làm một tình huống (vd "thu thập bài X gồm bình luận"). Ghi lại chỗ agent làm sai hoặc bỏ bước → sửa hướng dẫn → chạy lại tới khi đúng.

---

## 13. Rủi ro và điểm cần xác minh khi triển khai

| Rủi ro | Cách giảm |
|---|---|
| Facebook đổi giao diện/DOM | Dò DOM dựa vào `role`/`aria-label` thay vì class; có đường lùi `get_page_text`; hướng dẫn nêu dấu hiệu nhận biết thay vì toạ độ cố định |
| Tìm kiếm Facebook trả thiếu, không tìm được chữ trong bình luận | Lọc theo năm, tìm trong từng nhóm, quét toàn bộ nhóm chuyên đề; ghi `reached_end` và `issues` để chỗ thiếu hiện rõ |
| Tài khoản bị giới hạn vì thao tác nhiều | Nhịp độ 9.4, chạy theo lô, dừng ngay khi có cảnh báo |
| `save_to_disk` lưu ở thư mục tạm không cố định | `add_record.py` luôn chép vào vị trí chuẩn; xác minh ở chạy thử |
| Bài nhiều bình luận (600+) tốn nhiều thời gian | Ghi tiến độ theo lô; ảnh cuộn thay vì ảnh từng bình luận; có thể tách bài lớn thành task riêng |
| Ảnh chụp tự làm có giá trị chứng cứ hạn chế | SHA-256 + thời điểm + URL + bản chữ gốc; sheet Bằng chứng quan trọng làm danh mục để Thừa phát lại lập vi bằng |

---

## 14. Ngoài phạm vi đợt này
- YouTube, TikTok, Web — mỗi nền tảng một spec riêng, thêm `references/<platform>.md` và mã `YT-`, `TT-`, `WEB-`, dùng chung kho, script và Excel.
- Chạy tự động theo lịch khi không có người trông.
- Tự đăng nhập, tự xin vào nhóm, bất kỳ thao tác ghi nào trên nền tảng.
- Tra cứu thêm thông tin cá nhân của người đăng ngoài những gì hiển thị trên bài.

---

## 15. Điều chỉnh khi lập kế hoạch (thắng các mục trên khi khác nhau)

1. **Khoá trùng bình luận không có `fb_comment_id`** = băm(`source_id` + `author_name` + `text`) + hậu tố `#n` (thứ tự xuất hiện của bình luận giống hệt trong cùng một lần `add`). Bỏ `posted_at_raw` khỏi khoá vì thời gian tương đối ("2 giờ" → "3 ngày") đổi giữa các lần quét. Khoá được lưu vào bản ghi ở trường `dedupe_key`.
2. **Cập nhật container** (đã được duyệt vào nhóm, số thành viên, lần quét cuối…) qua bản ghi `recheck` có trường `updates` (chỉ các khoá: `privacy`, `joined`, `scan_mode`, `member_count`, `member_count_at`, `last_scanned_at`, `topic_dedicated`, `notes`, `name`).
3. `search_log.section` có thêm `page_feed`.
4. `key_parties[]` có thêm `label` (tên ngắn hiển thị), `press_sources`, `legacy: true` (bên nhập từ file cũ).
5. Excel: sheet Bài viết thêm cột `Mã nhóm`, `Tháng đăng`; sheet Bình luận thêm cột `Tháng`, cột "Loại" đổi tên `Loại nội dung`; sheet Nhóm & Trang dùng cột `Chuyên đề vụ việc` và thêm cột `Cần xin vào`.
6. `event` có thêm `sort_key` (với bản legacy: không giảm theo thứ tự dòng trong file cũ) để sắp xếp Dòng thời gian.
7. `snapshot_text` được ghi ra file rồi **bỏ khỏi bản ghi**; bản ghi có thêm `snapshot_sha256`.
8. Chỉ `parent_comment_id` được dùng tham chiếu trong mảng dạng `"@n"`.
9. Kiểm tra schema nằm ở `schema.py` (spec ghi trong `common.py`); mô hình đọc ở `view.py`; hàm openpyxl ở `xlsx_helpers.py`.
10. `supersedes` do Claude tự đặt phải trỏ tới một `source` `origin=legacy` có trong kho.
11. Chụp ảnh lỗi 2 lần liên tiếp → dừng và hỏi người dùng (spec §11 định tự chuyển sang Playwright; nay chỉ **đề xuất** Playwright, vì trình duyệt Playwright cần người dùng tự đăng nhập Facebook).
