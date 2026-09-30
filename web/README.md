# Web xem kết quả — Mention Monitor

Thay cho file Excel. Chạy **trên máy**, **chỉ đọc**: không ghi vào kho, không sửa ảnh gốc, chỉ nghe ở `127.0.0.1`.

## Chạy

```bash
# 1. Xuất dữ liệu từ kho (sau mỗi lần quét — skill tự làm)
python .claude/skills/mention-monitor/scripts/export_site.py

# 2. Lần đầu hoặc sau khi sửa code web
cd web
npm install
npm run build

# 3. Mở web
npm run start        # → http://127.0.0.1:3000
```

Quét xong chỉ cần chạy lại bước 1 rồi tải lại trang (không cần build lại).

## Cấu trúc

- `lib/data.ts` — đọc `../output/site/data.json` (đổi thư mục dự án bằng biến `MM_PROJECT_DIR`).
- `app/api/file` — trả ảnh/bản chữ, **chỉ** trong `screenshots/`, `snapshots/`, `output/thumbs/`; đường dẫn khác → 404.
- Trang: `/` tổng quan · `/bai-viet` · `/bai-viet/[id]` · `/binh-luan` · `/dong-thoi-gian` · `/bang-chung` (in được) · `/nguoi` · `/nhom` · `/nhat-ky` · `/chu-thich`.
- Mọi quy tắc gộp dữ liệu (kiểm tra lại, bản thay thế, ảnh mới nhất) nằm ở `scripts/view.py` + `export_site.py`; web chỉ hiển thị.

## Kiểm thử

```bash
npm test                                  # hàm lõi (chặn đường dẫn, tìm không dấu, lọc)
npm run build && npm run lint             # kiểu TypeScript + lint
npm run start &  python ../tests/smoke_web.py   # mở mọi trang bằng Chrome ngầm
```

## Deploy

Chưa làm. Deploy (vd Vercel) nghĩa là đưa tên, ảnh bình luận của người dân thường lên máy chủ ngoài — trái nguyên tắc
"dữ liệu ở máy người dùng" của skill. Chỉ làm khi đã quyết cách bảo vệ (bắt buộc đăng nhập) và sửa nguyên tắc đó; khi ấy
thay `lib/data.ts` + `app/api/file` bằng nguồn có kiểm soát truy cập.
