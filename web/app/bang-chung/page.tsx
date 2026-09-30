import type { Metadata } from "next";
import Link from "next/link";
import { PrintButton } from "@/components/PrintButton";
import { Thumb } from "@/components/Thumb";
import { Empty, Ext, KeyVal, NoData, PageTitle } from "@/components/ui";
import { getData } from "@/lib/data";
import { displayText, fmtTime } from "@/lib/text";

export const metadata: Metadata = { title: "Danh mục bằng chứng" };

export default async function EvidencePage() {
  const data = await getData();
  if (!data) return <NoData />;
  const items = data.evidence;
  return (
    <>
      <PageTitle title="Danh mục bằng chứng quan trọng"
        subtitle={<>Bài và bình luận mức quan trọng cao · {items.length} mục · xuất lúc {fmtTime(data.generated_at)}.
          Dùng làm danh mục khi lập vi bằng qua Thừa phát lại hoặc nộp kèm đơn.</>}
        actions={<PrintButton />} />
      <p className="mb-4 rounded-lg bg-surface-2 p-3 text-xs text-ink-2">
        Ảnh được chụp theo vùng của bài ngay lúc thu thập (không cắt sửa sau). Kiểm tra ảnh không bị sửa: mở Command Prompt,
        chạy <code className="font-mono">certutil -hashfile &quot;&lt;đường dẫn ảnh&gt;&quot; SHA256</code> — kết quả phải trùng mã SHA-256 bên dưới.
        Nội dung là lời người đăng; phân loại không phải kết luận pháp lý.
      </p>
      {items.length === 0 ? <Empty>Chưa có mục mức cao.</Empty> : (
        <ol className="space-y-5">
          {items.map((x, i) => (
            <li key={x.id} className="print-block grid gap-4 rounded-xl border border-line bg-surface p-4 md:grid-cols-[minmax(0,420px)_1fr]">
              <Thumb image={x.image} alt={`Ảnh bằng chứng ${x.id}`} big className="self-start" />
              <div className="min-w-0">
                <p className="text-sm text-muted">#{i + 1} · {x.type === "comment" ? "Bình luận" : "Bài viết"} ·{" "}
                  <Link className="font-mono text-accent-ink hover:underline"
                    href={x.type === "comment" ? `/bai-viet/${x.source_id}#${x.id}` : `/bai-viet/${x.id}`}>{x.id}</Link></p>
                <p className="prose-raw mt-2 text-[15px]">{displayText(x.summary)}</p>
                <div className="mt-3">
                  <KeyVal items={[
                    ["Người đăng", x.author_name],
                    ["Nhóm/trang", x.container_name],
                    ["Thời gian", [x.posted_at_raw, fmtTime(x.posted_at, x.posted_at_precision)].filter(Boolean).join(" · ")],
                    ["Link", <Ext key="l" href={x.url} />],
                    ["Lý do quan trọng", x.reason],
                    ["File ảnh gốc", x.image ? <span key="f" className="break-all font-mono text-xs">{x.image.file}</span> : "Chưa có ảnh"],
                    ["SHA-256", x.image ? <span key="h" className="break-all font-mono text-xs">{x.image.sha256}</span> : null],
                    ["Ảnh chụp lúc", fmtTime(x.image?.captured_at)],
                    ["Thu thập lúc", fmtTime(x.captured_at)],
                  ]} />
                </div>
              </div>
            </li>
          ))}
        </ol>
      )}
    </>
  );
}
