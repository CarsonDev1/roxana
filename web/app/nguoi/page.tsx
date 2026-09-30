import type { Metadata } from "next";
import Link from "next/link";
import { Badge, Card, Ext, NoData, PageTitle, SectionTitle } from "@/components/ui";
import { getData, label } from "@/lib/data";
import { fmtTime } from "@/lib/text";

export const metadata: Metadata = { title: "Người & tổ chức" };

export default async function PeoplePage() {
  const data = await getData();
  if (!data) return <NoData />;
  const parties = [...data.parties].sort((a, b) => Number(b.primary) - Number(a.primary) || b.mentions - a.mentions);
  return (
    <>
      <PageTitle title="Người & tổ chức"
        subtitle="Các bên liên quan (vai trò theo báo chí) và những người đăng/bình luận — chỉ ghi đúng như hiển thị trên bài, không tra thêm thông tin cá nhân." />
      <SectionTitle>Các bên liên quan</SectionTitle>
      <div className="mb-8 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {parties.map((p) => (
          <Card key={p.id}>
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="font-semibold">{p.name}</p>
                <p className="text-xs text-muted">{p.kind}</p>
              </div>
              <Badge tone={p.primary ? "accent" : "neutral"}>{p.primary ? "Bên chính" : "Bên liên quan khác"}</Badge>
            </div>
            {p.role && <p className="mt-2 line-clamp-4 text-sm text-ink-2">{p.role}</p>}
            <p className="mt-2 text-sm">
              <Link href={`/bai-viet?party=${p.id}`} className="font-medium text-accent-ink hover:underline">{p.mentions} lần được nhắc</Link>
              {p.first && <span className="text-xs text-muted"> · từ {fmtTime(p.first, "day")} đến {fmtTime(p.last, "day")}</span>}
            </p>
            {p.press_sources && <p className="mt-1 text-xs text-muted">Nguồn báo chí: {p.press_sources}</p>}
          </Card>
        ))}
      </div>

      <SectionTitle>Người đăng & người bình luận ({data.people.length})</SectionTitle>
      <div className="overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full text-sm">
          <thead className="bg-surface-2 text-left text-ink-2">
            <tr><th className="px-3 py-2 font-medium">Tên (như hiển thị)</th><th className="px-3 py-2 font-medium">Loại</th>
              <th className="px-3 py-2 text-right font-medium">Bài</th><th className="px-3 py-2 text-right font-medium">Bình luận</th>
              <th className="px-3 py-2 font-medium">Lần đầu</th><th className="px-3 py-2 font-medium">Gần nhất</th><th className="px-3 py-2 font-medium">Link</th></tr>
          </thead>
          <tbody>
            {data.people.map((p) => (
              <tr key={p.key} className="border-t border-line">
                <td className="px-3 py-2 font-medium">
                  <Link href={p.posts ? `/bai-viet?q=${encodeURIComponent(p.name)}` : `/binh-luan?q=${encodeURIComponent(p.name)}`} className="hover:underline">{p.name}</Link>
                </td>
                <td className="px-3 py-2 text-ink-2">{label(data, "author_kind", p.kind)}</td>
                <td className="tabular px-3 py-2 text-right">{p.posts}</td>
                <td className="tabular px-3 py-2 text-right">{p.comments}</td>
                <td className="px-3 py-2 text-ink-2">{fmtTime(p.first, "day")}</td>
                <td className="px-3 py-2 text-ink-2">{fmtTime(p.last, "day")}</td>
                <td className="px-3 py-2">{p.url && <Ext href={p.url}>mở</Ext>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
