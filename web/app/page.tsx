import Link from "next/link";
import { BarChart } from "@/components/BarChart";
import { StatTile } from "@/components/StatTile";
import { Thumb } from "@/components/Thumb";
import { Card, Empty, ImportanceBadge, NoData, PageTitle, SectionTitle, ToneBadge, Warnings } from "@/components/ui";
import { getData, label, partyLabel } from "@/lib/data";
import { excerpt, fmtMonth, fmtTime } from "@/lib/text";
import { SCHEMA_VERSION } from "@/lib/types";

const TONE_ORDER = ["tich_cuc", "trung_lap", "tieu_cuc", "gay_gat"];
const IMPORTANCE_ORDER = ["cao", "trung_binh", "thap"];

export default async function Overview() {
  const data = await getData();
  if (!data) return <NoData />;
  const st = data.stats;
  const known = st.by_month.filter((m) => m.month !== "unknown");
  const unknown = st.by_month.find((m) => m.month === "unknown")?.count ?? 0;
  const newest = [...data.sources].filter((s) => s.importance === "cao")
    .sort((a, b) => (b.posted_at ?? "").localeCompare(a.posted_at ?? "")).slice(0, 4);
  const parties = data.parties.filter((p) => p.primary || (st.by_party[p.id] ?? 0) > 0);

  return (
    <>
      <Warnings items={data.warnings} generatedAt={data.generated_at} schemaOk={data.schema_version === SCHEMA_VERSION} />
      <PageTitle title={`Tổng hợp nhắc đến vụ việc ${data.project_name}`}
        subtitle={<>Cập nhật {fmtTime(data.generated_at)} · Lần quét gần nhất: {st.latest_run ?? "chưa quét"}
          {st.latest_run && <> · mới trong lần này: {st.new_in_latest_run.sources} bài, {st.new_in_latest_run.comments} bình luận</>}</>} />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <StatTile label="Bài viết & nguồn" value={st.totals.sources} href="/bai-viet"
          hint={Object.entries(st.by_platform).map(([k, v]) => `${label(data, "platform", k)} ${v}`).join(" · ")} />
        <StatTile label="Bình luận" value={st.totals.comments} href="/binh-luan" />
        <StatTile label="Mức quan trọng cao" value={st.totals.high} href="/bang-chung" tone="critical" hint="bài + bình luận" />
        <StatTile label="Mốc sự kiện" value={st.totals.events} href="/dong-thoi-gian" />
        <StatTile label="Nhóm & trang" value={st.totals.containers} href="/nhom" />
        <StatTile label="Nhóm kín cần xin vào" value={st.totals.need_join} href="/nhom" tone="warning" />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <BarChart title="Theo tháng đăng (bài + bình luận)" orientation="column" unit="mục"
            bars={known.map((m) => ({ key: m.month, label: fmtMonth(m.month), value: m.count }))}
            note={unknown ? `${unknown} mục không rõ ngày đăng — không tính vào biểu đồ.` : undefined} />
        </Card>
        <Card>
          <BarChart title="Theo thái độ (bài + bình luận)"
            bars={TONE_ORDER.map((t) => ({ key: t, label: label(data, "tone", t), value: st.by_tone[t] ?? 0,
              href: `/bai-viet?tone=${t}` }))} />
          <div className="mt-6">
            <BarChart title="Theo mức quan trọng"
              bars={IMPORTANCE_ORDER.map((t) => ({ key: t, label: label(data, "importance", t),
                value: st.by_importance[t] ?? 0, href: `/bai-viet?importance=${t}` }))} />
          </div>
        </Card>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <BarChart title="Số lần được nhắc (bài + bình luận)" unit="lần"
            bars={parties.map((p) => ({ key: p.id, label: partyLabel(data, p.id), value: st.by_party[p.id] ?? 0,
              href: `/bai-viet?party=${p.id}` }))} />
        </Card>
        <Card>
          <SectionTitle>Chưa quét được / giới hạn</SectionTitle>
          {data.search_logs.length === 0 && (
            <p className="mb-2 rounded-lg bg-warning-wash p-2 text-sm">
              <span aria-hidden="true">! </span><strong>Chưa chạy lần tìm kiếm nào</strong> — phần lớn Facebook chưa được quét.
            </p>
          )}
          {st.gaps.length === 0 ? (data.search_logs.length ? <Empty>Không có giới hạn nào được ghi nhận.</Empty> : null) : (
            <ul className="space-y-2 text-sm">
              {st.gaps.slice(0, 12).map((g) => (
                <li key={g.id} className="rounded-lg bg-warning-wash p-2">
                  <span className="font-mono text-xs text-muted">{g.id}</span>{" "}
                  <span className="font-medium">{g.query}</span>
                  <p className="text-ink-2">{g.issue}</p>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-3 text-xs text-muted">Không có nghĩa là đã tìm đủ — chỉ những giới hạn đã ghi nhận.</p>
        </Card>
      </div>

      <div className="mt-6">
        <div className="mb-3 flex items-baseline justify-between">
          <SectionTitle>Bài mức quan trọng cao mới nhất</SectionTitle>
          <Link href="/bai-viet?importance=cao" className="text-sm text-accent-ink hover:underline">Xem tất cả →</Link>
        </div>
        {newest.length === 0 ? <Empty>Chưa có bài mức cao.</Empty> : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            {newest.map((s) => (
              <Link key={s.id} href={`/bai-viet/${s.id}`} className="group rounded-xl border border-line bg-surface p-3 shadow-sm hover:bg-surface-2">
                <Thumb image={s.main_image} alt={`Ảnh bài ${s.id}`} link={false} className="mb-3 aspect-[4/3]" />
                <p className="text-sm font-medium">{s.author_name}</p>
                <p className="text-xs text-muted">{fmtTime(s.posted_at, s.posted_at_precision) || s.posted_at_raw} · {s.container_name}</p>
                <p className="mt-2 line-clamp-3 text-sm text-ink-2">{excerpt(s.text, 180)}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  <ImportanceBadge value={s.importance} label={label(data, "importance", s.importance)} />
                  <ToneBadge value={s.tone} label={label(data, "tone", s.tone)} />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
