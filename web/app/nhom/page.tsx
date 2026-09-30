import type { Metadata } from "next";
import Link from "next/link";
import { Badge, Card, Ext, KeyVal, NoData, PageTitle } from "@/components/ui";
import { getData, label } from "@/lib/data";
import { fmtNumber, fmtTime } from "@/lib/text";

export const metadata: Metadata = { title: "Nhóm & trang" };

export default async function ContainersPage() {
  const data = await getData();
  if (!data) return <NoData />;
  const list = [...data.containers].sort((a, b) => Number(b.needs_join) - Number(a.needs_join) || b.source_count - a.source_count);
  return (
    <>
      <PageTitle title="Nhóm & trang" subtitle="Nơi các bài được đăng. Nhóm kín chưa tham gia không quét được — anh/chị tự xin vào, lần cập nhật sau sẽ quét." />
      <div className="grid gap-4 md:grid-cols-2">
        {list.map((c) => (
          <Card key={c.id} className={c.needs_join ? "border-warning/70" : ""}>
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="font-semibold">{c.name}</p>
                <p className="font-mono text-xs text-muted">{c.id} · {label(data, "container_kind", c.kind)}</p>
              </div>
              <div className="flex flex-wrap gap-1">
                {c.needs_join && <Badge tone="warning" icon="!">Cần xin vào</Badge>}
                {c.topic_dedicated && <Badge tone="accent">Chuyên về vụ việc</Badge>}
              </div>
            </div>
            <div className="mt-3">
              <KeyVal items={[
                ["Link", <Ext key="u" href={c.url} />],
                ["Công khai/Kín", label(data, "privacy", c.privacy)],
                ["Đã tham gia", label(data, "joined", c.joined)],
                ["Cách quét", label(data, "scan_mode", c.scan_mode)],
                ["Thành viên", c.member_count ? `${fmtNumber(c.member_count)} (lúc ${fmtTime(c.member_count_at, "day")})` : null],
                ["Quét lần cuối", fmtTime(c.last_scanned_at) || "Chưa quét"],
                ["Bài thu được", <Link key="n" className="text-accent-ink hover:underline" href={`/bai-viet?container=${c.id}`}>{c.source_count} bài</Link>],
                ["Ghi chú", c.notes],
              ]} />
            </div>
          </Card>
        ))}
      </div>
    </>
  );
}
