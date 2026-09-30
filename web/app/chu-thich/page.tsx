import type { Metadata } from "next";
import { Card, NoData, PageTitle, SectionTitle } from "@/components/ui";
import { getData } from "@/lib/data";

export const metadata: Metadata = { title: "Chú thích" };

export default async function LegendPage() {
  const data = await getData();
  if (!data) return <NoData />;
  const groups: [string, string][] = [["tone", "Thái độ"], ["claim_type", "Loại nội dung"], ["importance", "Mức quan trọng"]];
  return (
    <>
      <PageTitle title="Chú thích" subtitle="Cách đọc dữ liệu trên trang này." />
      <div className="grid gap-4 lg:grid-cols-2">
        {groups.map(([key, title]) => (
          <Card key={key}>
            <SectionTitle>{title}</SectionTitle>
            <dl className="space-y-2 text-sm">
              {Object.entries(data.labels[key] ?? {}).map(([v, text]) => (
                <div key={v}><dt className="font-medium">{text}</dt><dd className="text-ink-2">{data.descriptions[key]?.[v]}</dd></div>
              ))}
            </dl>
          </Card>
        ))}
        <Card>
          <SectionTitle>Chủ đề</SectionTitle>
          <p className="text-sm text-ink-2">{Object.values(data.labels.topics ?? {}).join(" · ")}</p>
          <SectionTitle>Độ tin cậy của mốc sự kiện</SectionTitle>
          <p className="text-sm text-ink-2">{Object.values(data.labels.reliability ?? {}).join(" · ")}</p>
        </Card>
        <Card className="lg:col-span-2">
          <SectionTitle>Mã và bằng chứng</SectionTitle>
          <ul className="list-disc space-y-1.5 pl-5 text-sm text-ink-2">
            <li>FB-P = bài Facebook · FB-C = bình luận Facebook · FB-G = nhóm/trang · WEB-P = bài báo/website · LOG = nhật ký quét · CHK = lần kiểm tra lại · EXC = kết quả đã loại · EVT = mốc sự kiện.</li>
            <li>Ảnh chụp chỉ gồm vùng của bài/bình luận, chụp ngay lúc thu thập — không có thanh Facebook, menu hay thông tin của tài khoản quét. Ảnh gốc không bao giờ bị sửa; ảnh thu nhỏ là bản phái sinh để xem nhanh.</li>
            <li>Kiểm tra ảnh không bị sửa: mở Command Prompt, chạy <code className="font-mono">certutil -hashfile &quot;&lt;đường dẫn ảnh&gt;&quot; SHA256</code> — kết quả phải trùng mã SHA-256 hiển thị.</li>
            <li>Một bài có thể có nhiều lần chụp (vd chụp lại khi kiểm tra); trang hiện lần mới nhất, các lần trước vẫn giữ trong kho và xem được ở trang bài.</li>
            <li>Độ chính xác thời gian: “Chính xác” = lấy từ ô hiện ra khi rê chuột lên mốc thời gian; “Ước lượng” = quy đổi từ “2 giờ”, “3 ngày”… theo lúc thu thập.</li>
            <li>Chuyển sang máy khác: chép cả thư mục dự án (data, screenshots, snapshots, output).</li>
          </ul>
        </Card>
        <Card className="lg:col-span-2">
          <SectionTitle>Lưu ý ngôn từ</SectionTitle>
          <p className="text-sm text-ink-2">Nội dung nguyên văn giữ nguyên lời người đăng, kể cả lời lẽ gay gắt. Các từ như “lừa đảo” là cách người đăng gọi, không phải kết luận pháp lý. Phân loại thái độ/cáo buộc chỉ mô tả nội dung.</p>
        </Card>
      </div>
    </>
  );
}
