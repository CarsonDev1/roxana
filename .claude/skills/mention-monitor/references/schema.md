# Trường dữ liệu

`add_record.py` tự thêm: `id`, `run_id`, `origin` (mặc định `scan`), `recorded_at`, `dedupe_key`; đổi `evidence[].file` thành đường dẫn chuẩn và thêm `sha256`, `captured_at`, `capture_tool`; ghi `snapshot_text` ra file → `snapshot_file` + `snapshot_sha256`. **Không tự đặt các trường này.**

Thời gian: ISO 8601 có `+07:00`, vd `2026-09-29T21:05:00+07:00`. Trường không có giá trị: `null` (không bỏ trường bắt buộc).

## Giá trị enum

| Trường | Giá trị |
|---|---|
| `platform` | `facebook` · `web` · `youtube` · `tiktok` |
| `content_type` | `post` · `shared_post` · `photo` · `video` · `reel` · `live` · `article` |
| `url_kind` | `permalink` (link riêng của bài) · `container_only` (chỉ có link nhóm) · `none` |
| `author_kind` | `person` · `page` · `anonymous` (thành viên ẩn danh) · `unknown` |
| `posted_at_precision` | `exact` (tooltip khi rê chuột) · `day` · `month` · `year` · `relative_estimate` ("2 giờ", "3 ngày" quy đổi theo giờ thu thập) · `unknown` |
| `evidence[].kind` | `post` (thân bài) · `attach` (ảnh đính kèm mở lớn) · `cscroll` (ảnh cuộn phần bình luận) · `comment` (ảnh riêng 1 bình luận) |
| container `kind` | `group` · `page` · `channel` |
| `privacy` | `public` · `private` · `unknown` |
| `joined` | `yes` · `no` · `pending` · `unknown` |
| `scan_mode` | `full` (quét mọi bài) · `keyword` (chỉ tìm trong nhóm theo từ khoá) |
| `scope` | `global` · `container` |
| `section` | `posts` · `groups` · `pages` · `videos` · `photos` · `hashtag` · `group_feed` · `page_feed` · `in_group_search` · `news` · `web_search` |
| recheck `status` | `active` · `edited` · `deleted` · `unavailable` |
| `reliability` | `bao_chi` · `van_ban` · `mxh` |
| `tone`, `claim_type`, `topics`, `importance` | xem `classification.md` |

## `source` — bài viết / chia sẻ / ảnh / video / reel / bài báo

Bắt buộc: `record_type`, `platform`, `content_type`, `url`, `url_kind`, `author_name`, `author_kind`, `posted_at_raw`, `posted_at_precision`, `text`, `keywords_matched`, `importance`, `captured_at`, và (khi thu thập) `tone`, `claim_type`, `importance_reason`, `evidence` (≥ 1 ảnh), `snapshot_text` hoặc `snapshot_file`.

```json
{
  "record_type": "source", "platform": "facebook", "content_type": "post",
  "url": "https://www.facebook.com/groups/427692059062534/posts/1597546225410439/", "url_kind": "permalink",
  "container_id": "FB-G0001", "container_name": "ROXANA PLAZA - HÀNH TRÌNH ĐÒI NHÀ",
  "author_name": "Quyết Chiến Roxana", "author_url": "https://www.facebook.com/100093187612816",
  "author_kind": "person", "author_badge": null,
  "posted_at_raw": "22 tháng 8 lúc 09:15", "posted_at": "2026-08-22T09:15:00+07:00", "posted_at_precision": "exact",
  "text": "<nguyên văn đầy đủ sau khi bấm Xem thêm>",
  "attachments": [{"kind": "image", "description": "Giấy mời của Thanh tra TP.HCM",
                   "transcribed_text": "<chép lại chữ trong ảnh>", "url": null}],
  "shared_from": null,
  "metrics": {"reactions": 7, "comments": 4, "shares": 0, "views": null, "counted_at": "2026-09-29T21:00:00+07:00"},
  "keywords_matched": ["roxana"], "entities_mentioned": ["lien"], "topics": ["doi_thoai"],
  "tone": "tieu_cuc", "claim_type": "van_ban", "importance": "cao",
  "importance_reason": "Kèm Giấy mời của Thanh tra TP.HCM",
  "evidence": [
    {"file": "<đường dẫn save_to_disk trả về>", "kind": "post", "shows": "Thân bài, tên người đăng, thời gian"},
    {"file": "<...>", "kind": "attach", "shows": "Ảnh Giấy mời phóng lớn"},
    {"file": "<...>", "kind": "cscroll", "shows": "Bình luận đoạn 1"}
  ],
  "snapshot_text": "<kết quả get_page_text>",
  "captured_at": "2026-09-29T21:00:00+07:00", "notes": null
}
```

- `shared_from`: `{"url", "author_name", "author_url", "text_excerpt"}` khi là bài chia sẻ.
- `keywords_matched`: id trong `config.json → keyword_groups`. `entities_mentioned`: id trong `key_parties`.

## `comment`

Bắt buộc: `source_id`, `depth` (1 = bình luận, 2 = trả lời, 3 = trả lời của trả lời), `author_name`, `author_kind`, `posted_at_raw`, `posted_at_precision`, `text`, `tone`, `claim_type`, `importance`, `scroll_refs`, `captured_at`. Thêm `parent_comment_id` khi `depth > 1`. Mức `cao` → thêm `evidence` (ảnh riêng, `kind: "comment"`) và `importance_reason`.

Ghi **cả cây bình luận trong một mảng**; `parent_comment_id` có thể là `"@<chỉ số trong mảng>"`:

```json
[
  {"record_type": "comment", "source_id": "FB-P00012", "depth": 1, "fb_comment_id": "1234567890",
   "url": "https://www.facebook.com/groups/427692059062534/posts/1597546225410439/?comment_id=1234567890",
   "author_name": "Huynh Bich Diem", "author_url": "https://www.facebook.com/100009329476350",
   "author_kind": "person", "author_badge": null,
   "posted_at_raw": "3 ngày", "posted_at": "2026-09-26T21:00:00+07:00", "posted_at_precision": "relative_estimate",
   "text": "Trả nhà cho dân đi", "attachments": [], "reactions": 3, "reply_count": 1,
   "keywords_matched": [], "entities_mentioned": [], "topics": [],
   "tone": "tieu_cuc", "claim_type": "y_kien", "importance": "thap",
   "scroll_refs": [{"file": "screenshots/facebook/2026-09-29/FB-P00012_cscroll_01.png", "position": 1}],
   "captured_at": "2026-09-29T21:05:00+07:00"},
  {"record_type": "comment", "source_id": "FB-P00012", "depth": 2, "parent_comment_id": "@0",
   "author_name": "Nguyen Toan Roxana", "author_url": "https://www.facebook.com/61590964520879",
   "author_kind": "person", "posted_at_raw": "2 ngày", "posted_at": "2026-09-27T21:00:00+07:00",
   "posted_at_precision": "relative_estimate", "text": "Đồng ý", "attachments": [], "reactions": 0,
   "reply_count": 0, "keywords_matched": [], "entities_mentioned": [], "topics": [],
   "tone": "tieu_cuc", "claim_type": "y_kien", "importance": "thap",
   "scroll_refs": [{"file": "screenshots/facebook/2026-09-29/FB-P00012_cscroll_01.png", "position": 2}],
   "captured_at": "2026-09-29T21:05:00+07:00"}
]
```

`scroll_refs[].file` **phải** là đường dẫn trong `evidence_paths` trả về khi ghi bài (hoặc khi ghi `recheck` có ảnh cuộn mới). `position` = thứ tự của bình luận trong ảnh đó (1, 2, …). Bình luận vắt qua 2 ảnh → 2 phần tử.

## `container` — nhóm / trang / kênh

Bắt buộc: `platform`, `kind`, `name`, `url`, `privacy`, `joined`, `scan_mode`, `topic_dedicated` (true nếu tên/mô tả có `context_terms`). Nên có: `member_count`, `member_count_at`, `notes`. Nhóm `private` + `joined` khác `yes` = **cần xin vào**.

Thay đổi về sau (đã được duyệt, số thành viên, lần quét cuối) → bản ghi `recheck` với `updates`:

```json
{"record_type": "recheck", "target_id": "FB-G0003", "checked_at": "2026-10-10T20:00:00+07:00", "status": "active",
 "updates": {"joined": "yes", "last_scanned_at": "2026-10-10T20:00:00+07:00", "member_count": 2500,
             "member_count_at": "2026-10-10T20:00:00+07:00"}}
```

Khoá được phép trong `updates`: `privacy`, `joined`, `scan_mode`, `member_count`, `member_count_at`, `last_scanned_at`, `topic_dedicated`, `notes`, `name`.

## `search_log` — mỗi lần tìm kiếm / cuộn một feed

Bắt buộc: `platform`, `scope`, `section`, `query`, `started_at`, `results_seen`, `results_new`, `reached_end`. Nên có: `ended_at`, `container_id` (khi `scope=container`), `filters`, `results_duplicate`, `results_excluded`, `issues`, `notes`.

```json
{"record_type": "search_log", "platform": "facebook", "scope": "global", "section": "posts",
 "query": "Roxana Plaza", "filters": {"year": 2021}, "started_at": "2026-09-29T20:00:00+07:00",
 "ended_at": "2026-09-29T20:12:00+07:00", "results_seen": 38, "results_new": 9, "results_duplicate": 27,
 "results_excluded": 2, "reached_end": true, "issues": null}
```

## `recheck` — xem lại bài/bình luận/nhóm đã có

Bắt buộc: `target_id`, `checked_at`, `status`. Sửa phân loại bài/bình luận: `updates` chỉ gồm `tone`, `claim_type`, `importance`, `importance_reason`, `topics`, `entities_mentioned` + `notes` nêu lý do (nhóm: các trường của nhóm). `edited` → thêm `new_text` (nội dung mới nguyên văn). Có thể kèm `metrics`, `evidence` (ảnh lần kiểm tra — gồm `cscroll` nếu chụp lại bình luận), `snapshot_text`, `notes`.

## `exclusion` — kết quả khớp tên nhưng không thuộc vụ việc

Bắt buộc: `url`, `excerpt` (≤ 100 ký tự), `keywords_matched`, `reason`. Nên có `search_log_id`. **Không được** có `author_name`, `author_url`.

## `event` — mốc cho sheet Dòng thời gian

Bắt buộc: `date_raw`, `description`, `reliability`. Nên có: `date` (ISO, có thể chỉ năm hoặc năm-tháng), `source_text`, `related_ids`. Thêm event khi gặp tin mới về tiến trình pháp lý/hành chính (thanh tra, toà, công an, đối thoại).
