# Mention Monitor — Web xem kết quả (thay file Excel) — Thiết kế

- **Ngày:** 2026-09-30
- **Trạng thái:** Người dùng duyệt phần kiến trúc, yêu cầu "cứ tiến hành làm" — phần trang/bố cục dưới đây do Claude quyết theo các mục đích người dùng chọn.
- **Liên quan:** `2026-09-29-mention-monitor-facebook-design.md` (spec gốc). Thay mục 10 (File Excel) về vai trò "đầu ra chính".

## 1. Mục tiêu

Web xem toàn bộ kết quả thu thập thay cho `output/Roxana_Tong_hop.xlsx` ("vừa xấu vừa không trực quan"). Người dùng chọn đủ 4 mục đích: **nắm tình hình nhanh · đọc và tìm nội dung · chuẩn bị hồ sơ pháp lý · theo dõi dòng thời gian** — "đầy đủ mọi thứ thay vì file Excel".

Ràng buộc:
- **Chạy trên máy** (`http://127.0.0.1:3000`), dữ liệu không rời máy (nguyên tắc 9 của spec gốc vẫn giữ). Deploy (Vercel) tính sau, chỉ khi người dùng quyết cách bảo vệ và sửa nguyên tắc 9.
- **Chỉ đọc**: web không ghi vào kho, không sửa ảnh/bản chữ gốc.
- Giao diện tiếng Việt, một người dùng, không đăng nhập (vì chỉ nghe trên 127.0.0.1).

Thành công khi: mọi thông tin đang có trong 11 sheet Excel đều xem được trên web; tìm/lọc bài và bình luận tức thì; mỗi bài mở ra thấy ảnh bằng chứng, nguyên văn, cây bình luận, lịch sử; danh mục bằng chứng in được; quét xong chạy một lệnh là web cập nhật.

## 2. Kiến trúc

```
data/records.jsonl ─► scripts/export_site.py ─► output/site/data.json
                       (dùng view.py)            (schema_version, generated_at, …)
screenshots/ snapshots/ output/thumbs/ ─┐
                                        ▼
web/ (Next.js App Router + TypeScript + Tailwind)
 ├─ lib/data.ts     đọc data.json (MM_PROJECT_DIR, mặc định thư mục cha của web/), không cache cứng
 ├─ app/api/file    trả file CHỈ trong screenshots/, snapshots/, output/thumbs/ (kiểm realpath)
 └─ các trang (mục 3)
```

- `export_site.py` tính sẵn mọi thứ (nhãn tiếng Việt, cây bình luận, thống kê, người/nhóm, bằng chứng, thay đổi, nhật ký, phần chưa quét) — web chỉ hiển thị, không viết lại logic gộp dữ liệu.
- Ảnh hiển thị của mỗi mục = lần chụp **mới nhất** (bài chụp lại qua recheck); danh sách mọi lần chụp vẫn có.
- Ảnh thu nhỏ tạo bằng `xlsx_helpers.make_thumbnail` vào `output/thumbs/` (240px danh sách, 480px bằng chứng).
- Ghi file JSON tạm rồi đổi tên (không làm hỏng bản cũ nếu lỗi giữa chừng).
- Skill: bước "sau mỗi lô" và "kết thúc" chạy `export_site.py`; `build_excel.py` giữ lại, chạy tay khi cần nộp file.

## 3. Trang

| Đường dẫn | Nội dung |
|---|---|
| `/` Tổng quan | Ô số liệu (nguồn, bình luận, nhóm, mức cao, cần xin vào); biểu đồ theo tháng đăng; theo thái độ; theo mức quan trọng; số lần nhắc từng bên; lần quét gần nhất; mục mới của lần quét gần nhất; **chưa quét được / giới hạn** |
| `/bai-viet` | Danh sách bài/nguồn: ô tìm chữ (không phân biệt dấu), lọc nền tảng · nhóm · thái độ · mức quan trọng · bên được nhắc · chủ đề · nguồn dữ liệu (quét/file cũ) · trạng thái; sắp theo ngày đăng/ngày thu thập; thẻ có ảnh thu nhỏ, người đăng, thời gian, trích đoạn, nhãn |
| `/bai-viet/[id]` | Thông tin bài, nguyên văn, đính kèm + chữ trong ảnh, chia sẻ từ, số liệu (mới nhất + lịch sử), phân loại + lý do, **ảnh bằng chứng** (xem lớn, SHA-256, giờ chụp, mở file gốc), bản chữ gốc, **cây bình luận** (mỗi bình luận: nguyên văn, ảnh cuộn + vị trí, ảnh riêng, link), lịch sử kiểm tra lại, "thay cho" bản cũ |
| `/binh-luan` | Mọi bình luận: tìm, lọc (thái độ, mức, bên được nhắc, bài), link về bài |
| `/dong-thoi-gian` | Trục thời gian: mốc sự kiện (độ tin cậy, nguồn, mã liên quan) + bài mức cao theo ngày |
| `/nguoi` | Bên liên quan (vai trò, số lần nhắc) · người đăng/bình luận (như hiển thị: tên, link, số bài, số bình luận, lần đầu/gần nhất) |
| `/nhom` | Nhóm & trang: công khai/kín, đã tham gia, cách quét, số bài, "cần xin vào" nổi bật |
| `/bang-chung` | Danh mục bằng chứng mức cao: ảnh lớn, tóm tắt, người đăng, link, giờ đăng, lý do, file gốc, SHA-256, giờ thu thập; **In** (CSS in A4, mỗi mục một khối) |
| `/nhat-ky` | Tab: Nhật ký quét · Lịch sử thay đổi · Đã loại trừ (không tên người đăng) |
| `/chu-thich` | Định nghĩa phân loại, cách đọc mã, kiểm tra SHA-256 (`certutil`), lưu ý ngôn từ, lưu ý từ file cũ, ảnh chụp chỉ vùng bài |

Mọi nhãn trạng thái đi kèm chữ (màu không là tín hiệu duy nhất); tương phản đủ; bàn phím dùng được; bố cục co giãn tới màn hình hẹp.

## 4. Xử lý lỗi

- Chưa có `data.json` → trang hướng dẫn chạy `export_site.py`.
- File ảnh thiếu/hỏng → khung "Ảnh không đọc được" + đường dẫn, không vỡ trang.
- `/api/file` với đường dẫn ngoài 3 thư mục, `..`, đường dẫn tuyệt đối → 404.
- `schema_version` khác phiên bản web mong đợi → cảnh báo trên đầu trang.

## 5. Kiểm thử

- pytest `tests/test_export_site.py`: đủ khoá dữ liệu; số liệu khớp view; bài bị thay không hiện; cây bình luận đúng thứ tự/cấp; ảnh mới nhất được chọn; exclusion không có tên; ghi nguyên tử; ký tự lạ vẫn ra JSON hợp lệ.
- Web: `npm run build` (kiểm kiểu TypeScript) + kiểm thử đơn vị cho hàm lọc/tìm và kiểm tra đường dẫn file; smoke test Playwright (Python) mở mọi trang trên dữ liệu thật, không lỗi console, `/api/file?path=../config.json` → 404.

## 6. Ngoài phạm vi

Deploy, đăng nhập, sửa/gắn cờ dữ liệu trên web, xuất PDF phía server (dùng In của trình duyệt).
