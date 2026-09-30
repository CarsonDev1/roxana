# Quét YouTube (video, Shorts, bình luận)

Chạy **song song** với luồng Facebook và web: Chrome ẩn riêng (Playwright, không đăng nhập), chỉ đọc — không thích,
không bình luận, không đăng ký kênh, không vượt captcha. Gặp trang "lưu lượng bất thường"/captcha → dừng (exit 3).

## 1. Tìm — `scripts/ytscan/discover.py <run>/youtube`

Mỗi term (`terms` + `weak_terms`, có dấu và không dấu) tìm 2 lần: theo mức liên quan và mới nhất; cuộn tới hết kết quả
(tối đa 15 lần cuộn). Kết quả có tên vụ việc ở tiêu đề/đoạn trích/tên kênh (kể cả tên trần còn thiếu ngữ cảnh) →
`candidates.jsonl`. Mỗi lượt tìm → `discover_log.jsonl` (dùng làm `search_log`, `platform: "youtube"`, `section: "videos"`).

## 2. Chụp — `scripts/ytscan/capture_videos.py <run>/youtube`

Mỗi video → `<run>/youtube/bundles/<mã video>/`:
- `video_NN.png`: khung phát (đã dừng), tiêu đề, kênh, lượt xem, ngày, **mô tả mở rộng** — ẩn thanh đầu trang YouTube.
- `video.txt` (tiêu đề + mô tả đầy đủ) · `meta.json`: giờ đăng chính xác (`publishDate`), lượt xem, lượt thích, thời lượng, thẻ.
- `comments.json`: **mọi** bình luận và phản hồi đang hiển thị (bấm hết "N phản hồi"/"Hiện thêm phản hồi", mở "Đọc thêm");
  mã bình luận `lc` (phản hồi có dạng `<mã gốc>.<mã phản hồi>`), tác giả, chữ kèm emoji, thời gian tương đối, lượt thích.
- `cscroll_NN.png`: cột bình luận chụp theo từng màn hình; `log.json` ghi bình luận nào nằm trong ảnh nào (→ `scroll_refs`).
- Tiêu đề/mô tả/thẻ không nhắc vụ việc → `meta.json` `"relevant": false`, không chụp.
- Số "N bình luận" YouTube hiện thường lớn hơn số đọc được (bình luận bị giữ lại/đã xoá) — ghi đủ những gì hiển thị.

## 3. Ghi kho — `bundle_to_records.py` (`video_drafts` / `apply_video`) qua `apply_all.py --yt <run>/youtube/bundles`

`platform: "youtube"`, `content_type: "video"` (Shorts → `reel`, phát trực tiếp → `live`), mã `YT-P…`; bình luận `YT-C…`
(`yt_comment_id`, `posted_at_precision: "relative_estimate"`). Phân loại như Facebook: `cls.json` =
`{"source": {...}, "comments": {"<yt_comment_id>": {...}}}` (xem `classification.md`).
