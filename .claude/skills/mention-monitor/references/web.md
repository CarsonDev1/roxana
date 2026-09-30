# Quét Web (báo chí, website, diễn đàn)

Chạy **song song** với luồng Facebook được: dùng Chrome ẩn riêng (Playwright, không đăng nhập), không đụng tài khoản Facebook.
Chỉ đọc; không đăng ký, không bình luận, không vượt captcha/paywall. Link Facebook tìm được ở đây chuyển sang luồng Facebook.

## 1. Tìm bài — `scripts/webscan/discover.py <run>/web [--sources news,web]`

- `news`: Google News RSS cho **mọi term** (có dấu + không dấu) × (không lọc năm + từng năm 2017 → năm hiện tại) —
  mỗi lượt tối đa ~100 bài nên phải chia theo năm.
- `web`: DuckDuckGo HTML (tối đa 5 trang). Trả 403/captcha → nguồn đó tự dừng, **không** thử vượt.
- Bổ sung bằng công cụ **WebSearch** (tìm theo các bên, tên pháp lý "Contentment Plaza", mốc tiến trình: toà án, công an,
  thanh tra, đối thoại, bàn giao…): thêm link vào `<run>/web/candidates.jsonl` với `"engine": "websearch"`.
- Mỗi lượt ghi `discover_log.jsonl` (engine, query, year, results, new, error) → dùng làm `search_log` (`platform: "web"`).

## 2. Chụp — `scripts/webscan/capture_articles.py <run>/web`

Mỗi bài → `<run>/web/bundles/<key>/`:
- `article_NN.png`: **chỉ khối bài** (tiêu đề + dòng tác giả/ngày + thân bài), nhận khối theo mật độ đoạn văn; bỏ quảng cáo,
  cột bên, tin liên quan, bình luận. Bài dài > 5000px chụp thành nhiều phần liên tiếp (mỗi phần là một ảnh gốc).
- `article.txt` nguyên văn · `article.html` bản HTML gốc · `meta.json` (link canonical, tiêu đề, tên báo, tác giả, giờ đăng
  từ meta/JSON-LD; không có thì ngày theo Google News → `posted_at_precision: "day"`).
- Không nhắc tới vụ việc → `meta.json` có `"relevant": false`, không chụp. Chỉ trùng tên → danh sách loại trừ.
- Khớp từ khoá theo chữ **có dấu** (viết không dấu vẫn khớp; "tường phòng" không khớp "Tường Phong") và theo **nguyên từ**.
  Tên trần "Roxana", "Tường Phong" (`weak_terms`) cũng là tên người/địa danh → chỉ tính khi bài có từ ngữ cảnh khác.
- Đổi quy tắc khớp hoặc `config.json` → chạy `scripts/webscan/rematch.py <run>/web --do` trước khi phân loại: bài không còn
  khớp chuyển `relevant: false` (ghi `rematch`), trùng tên → `<run>/web/exclusions.json` (bản nháp `exclusion`).

## 3. Ghi kho — `bundle_to_records.py` (`article_draft` / `apply_article`)

`platform: "web"`, `content_type: "article"`, `author_kind: "page"`, `container_name` = tên báo, mã `WEB-P…`.
Phân loại như Facebook (`classification.md`): đọc `article.txt`, ghi `{"source": {tone, claim_type, importance,
importance_reason, topics, entities_mentioned}}`. Báo chính thống đưa tin tiến trình (thanh tra, toà, công an, đối thoại)
→ thêm `event` với `reliability: "bao_chi"`.

## Chưa làm (ghi vào báo cáo "chưa quét được")

Bình luận dưới bài báo (VnExpress, Tuổi Trẻ… tải động), TikTok. YouTube: xem `youtube.md`.
