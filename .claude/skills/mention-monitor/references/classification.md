# Phân loại nội dung

Phân loại mô tả **nội dung**, không đánh giá đúng/sai, không phải kết luận pháp lý. Phân vân giữa hai mức → chọn mức nhẹ hơn và ghi lý do vào `notes` (`tone`: `tich_cuc`/`trung_lap` → `tieu_cuc` → `gay_gat`; `importance`: `thap` → `trung_binh` → `cao`).

## `tone` — thái độ của nội dung đối với các bên được nhắc

| Giá trị | Khi nào | Ví dụ |
|---|---|---|
| `tich_cuc` | khen, bênh vực, ghi nhận | "Cảm ơn thanh tra đã vào cuộc" |
| `trung_lap` | đưa tin, hỏi, thông báo, không bày tỏ thái độ | "Mai 8h họp ở 15 Nguyễn Gia Thiều nhé" |
| `tieu_cuc` | phê phán, phản đối, bất bình, lời lẽ bình thường | "CĐT trễ hẹn 7 năm vẫn chưa giao nhà" |
| `gay_gat` | chửi bới, xúc phạm, đe doạ, từ thô tục | "bọn ác ôn…", chửi tục |

## `claim_type` — chọn **một**, xét theo thứ tự từ trên xuống, lấy cái đầu tiên khớp

| Giá trị | Khi nào |
|---|---|
| `van_ban` | kèm văn bản/tài liệu: giấy mời, văn bản toà án, kết luận thanh tra, hợp đồng, biên bản |
| `cao_buoc` | quy kết hành vi sai trái cho người/tổ chức **cụ thể** ("Tường Phong lừa đảo", "bà X chiếm tiền") |
| `keu_goi` | kêu gọi hành động: làm đơn tố cáo, tập trung, ký đơn, vào nhóm |
| `thong_tin` | tường thuật sự kiện, cập nhật tiến trình, có nguồn hoặc là người trực tiếp chứng kiến |
| `tin_don` | thông tin không nguồn, "nghe nói", "hình như" |
| `y_kien` | bày tỏ quan điểm, cảm xúc |
| `hoi_dap` | hỏi hoặc trả lời câu hỏi |

## `topics` — chọn **nhiều** (có thể rỗng)

`ban_chui` (bán khi chưa đủ điều kiện) · `tang_gia_ky_lai` (tăng giá, ký lại hợp đồng) · `cham_ban_giao` · `thanh_tra` · `toa_an` · `cong_an_to_giac` · `tuan_hanh` · `doi_thoai` · `tranh_chap_noi_bo` (tranh chấp cổ phần Naviland…) · `xay_sai_phep` · `hoan_tien` · `khac`

## `importance`

| Giá trị | Điều kiện (chỉ cần một) |
|---|---|
| `cao` | kèm văn bản chính thức · nêu đích danh một **bên chính** (6 bên có `primary: true` trong `key_parties`) kèm cáo buộc · tin mới về tiến trình pháp lý/hành chính · do admin nhóm hoặc một bên chính đăng · bài có tổng thích + bình luận + chia sẻ ≥ 100 · bình luận có ≥ 20 lượt thích |
| `trung_binh` | nhắc tới vụ việc hoặc các bên, có thông tin hoặc ý kiến cụ thể |
| `thap` | ngắn, không thêm thông tin: "hóng", "theo dõi", "+1", chỉ sticker/emoji, hoặc câu ngắn chỉ bày tỏ thái độ không nêu tên/sự việc cụ thể ("trả nhà cho dân đi") |

`importance_reason` ghi điều kiện nào khớp, vd "Nêu đích danh bà Phạm Thị Ngọc Liên kèm cáo buộc". Mức `thap` **vẫn ghi đủ** nguyên văn và `scroll_refs` — không bỏ bình luận nào.

## `keywords_matched`, `entities_mentioned`

- `keywords_matched`: nhóm từ khoá xuất hiện trong nội dung (không phân biệt dấu, hoa/thường). Bình luận trong bài về Roxana nhưng tự nó không nhắc từ khoá nào → `[]` (vẫn ghi).
- `entities_mentioned`: bên trong `key_parties` được nhắc — kể cả nhắc gián tiếp rõ ràng ("CĐT" trong nhóm Roxana → `tuongphong`; "bà Liên" trong ngữ cảnh Roxana → `lien`). Không chắc → không gắn.

## Trùng tên — bắt buộc kiểm tra với nhóm `requires_context`

Kết quả khớp tên (vd "Phạm Ngọc Liên", "Phương Tuyền", "Viethome") mà bài, bài chứa bình luận, và tên nhóm/trang **không có** từ nào trong `context_terms` → **không** ghi `source`/`comment`; ghi `exclusion`:

```json
{"record_type": "exclusion", "url": "<link kết quả>", "excerpt": "<≤ 100 ký tự quanh chỗ khớp>",
 "keywords_matched": ["lien"], "reason": "Trùng tên — không có từ ngữ cảnh của vụ việc", "search_log_id": "LOG-000031"}
```
