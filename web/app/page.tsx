import Link from "next/link";
import { BarChart } from "@/components/BarChart";
import { StatTile } from "@/components/StatTile";
import { Thumb } from "@/components/Thumb";
import { Card, Empty, ImportanceBadge, NoData, PageTitle, SectionTitle, ToneBadge, Warnings } from "@/components/ui";
import { getData, label, partyLabel } from "@/lib/data";
import { excerpt, fmtMonth, fmtTime } from "@/lib/text";
import { SCHEMA_VERSION } from "@/lib/types";

const TONE_ORDER = ["tich_cuc", "trung_lap", "tieu_cuc", "gay_gat"];
const RECORD_TYPE_LABEL: Record<string, string> = { source: "bài/nguồn", search_log: "log tìm kiếm", event: "sự kiện",
  exclusion: "loại trừ", recheck: "kiểm tra lại", comment: "bình luận", container: "nhóm/trang" };
const IMPORTANCE_ORDER = ["cao", "trung_binh", "thap"];

export default async function Overview() {
  const data = await getData();
  if (!data) return <NoData />;
  const st = data.stats;
  const known = st.by_month.filter((m) => m.month !== "unknown");
  const unknown = st.by_month.find((m) => m.month === "unknown")?.count ?? 0;
  const newest = [...data.sources].filter((s) => s.importance === "cao")
    .sort((a, b) => (b.posted_at ?? "").localeCompare(a.posted_at ?? "")).slice(0, 4);
  const trends = data.trends;
  const trendMain = trends?.groups.find((g) => g.points.length > 0);
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

      {st.totals.records != null && (
        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border border-line bg-surface px-4 py-3 text-sm shadow-sm">
          <p className="text-ink-2">
            Tổng bản ghi trong kho <span className="ml-1 text-lg font-semibold text-ink">{st.totals.records.toLocaleString("vi-VN")}</span>
          </p>
          <ul className="flex flex-wrap gap-1.5 text-xs text-muted">
            {Object.entries(st.records_by_type ?? {}).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
              <li key={k} className="rounded-full bg-surface-2 px-2.5 py-1">
                {RECORD_TYPE_LABEL[k] ?? k} <b className="font-semibold text-ink-2">{v.toLocaleString("vi-VN")}</b>
              </li>
            ))}
          </ul>
        </div>
      )}

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

      {trends && trendMain && (
        <Card className="mt-4">
          <BarChart title={`Mức quan tâm tìm kiếm trên Google — “${trendMain.keyword}” (36 tháng gần nhất)`} orientation="column" unit="điểm"
            bars={trendMain.points.slice(-36).map((p) => ({ key: p.date, label: fmtMonth(p.date), value: p.value }))}
            note={trends.note} />
          <table className="mt-4 w-full text-sm">
            <thead><tr className="text-left text-muted">
              <th className="py-1 font-normal">Nhóm từ khoá (Google Trends)</th>
              <th className="py-1 text-right font-normal">Tháng cao nhất</th>
              <th className="py-1 text-right font-normal">TB 12 tháng gần nhất</th>
            </tr></thead>
            <tbody>
              {trends.groups.map((g) => (
                <tr key={g.group} className="border-t border-line">
                  <td className="py-1">{g.label} <span className="text-xs text-muted">“{g.keyword}”</span></td>
                  {g.error ? <td colSpan={2} className="py-1 text-right text-xs text-muted">Không lấy được ({g.error})</td>
                    : g.peak_month ? (<>
                      <td className="tabular py-1 text-right">{fmtMonth(g.peak_month)}</td>
                      <td className="tabular py-1 text-right">{g.avg_last_12_months ?? "—"}</td>
                    </>) : <td colSpan={2} className="py-1 text-right text-xs text-muted">Lượt tìm quá ít, Google không có số liệu</td>}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-muted">Nguồn: {trends.source} ({trends.geo}), lấy lúc {fmtTime(trends.fetched_at)}.</p>
        </Card>
      )}

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
