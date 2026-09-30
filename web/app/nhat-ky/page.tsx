import type { Metadata } from "next";
import { Badge, Empty, Ext, IdLink, NoData, PageTitle, SectionTitle } from "@/components/ui";
import { getData, label } from "@/lib/data";
import { displayText, fmtTime } from "@/lib/text";

export const metadata: Metadata = { title: "Nhật ký" };

const th = "px-3 py-2 text-left font-medium";
const td = "px-3 py-2 align-top";

export default async function LogPage() {
  const data = await getData();
  if (!data) return <NoData />;
  const containers = Object.fromEntries(data.containers.map((c) => [c.id, c.name]));
  const comments = Object.fromEntries(data.comments.map((c) => [c.id, c.source_id]));
  return (
    <>
      <PageTitle title="Nhật ký" subtitle="Mọi lần tìm kiếm/cuộn feed, các thay đổi phát hiện khi kiểm tra lại, và kết quả đã loại vì trùng tên." />
      <nav className="no-print mb-6 flex gap-2 text-sm">
        {[["#quet", `Nhật ký quét (${data.search_logs.length})`], ["#thay-doi", `Lịch sử thay đổi (${data.changes.length})`],
          ["#loai-tru", `Đã loại trừ (${data.exclusions.length})`]].map(([href, text]) => (
          <a key={href} href={href} className="rounded-lg px-3 py-1.5 ring-1 ring-line hover:bg-surface-2">{text}</a>
        ))}
      </nav>

      <SectionTitle id="quet">Nhật ký quét</SectionTitle>
      {data.search_logs.length === 0 ? <Empty>Chưa có lần tìm kiếm nào được ghi.</Empty> : (
        <div className="mb-8 overflow-x-auto rounded-xl border border-line bg-surface">
          <table className="w-full text-sm">
            <thead className="bg-surface-2 text-ink-2"><tr>
              <th className={th}>Mã</th><th className={th}>Bắt đầu</th><th className={th}>Phạm vi</th><th className={th}>Mục</th>
              <th className={th}>Từ khoá · bộ lọc</th><th className={`${th} text-right`}>Xem/Mới/Trùng/Loại</th>
              <th className={th}>Hết kết quả</th><th className={th}>Sự cố / giới hạn</th></tr></thead>
            <tbody>
              {data.search_logs.map((r) => (
                <tr key={r.id} className="border-t border-line">
                  <td className={`${td} font-mono text-xs`}>{r.id}</td>
                  <td className={td}>{fmtTime(r.started_at)}</td>
                  <td className={td}>{label(data, "scope", r.scope)}{r.container_id ? `: ${containers[r.container_id] ?? r.container_id}` : ""}</td>
                  <td className={td}>{label(data, "section", r.section)}</td>
                  <td className={td}>“{r.query}”{r.filters && <span className="text-muted"> {JSON.stringify(r.filters)}</span>}</td>
                  <td className={`${td} tabular text-right`}>{r.results_seen}/{r.results_new}/{r.results_duplicate ?? "—"}/{r.results_excluded ?? "—"}</td>
                  <td className={td}>{r.reached_end ? "Có" : <Badge tone="warning" icon="!">Chưa</Badge>}</td>
                  <td className={td}>{Array.isArray(r.issues) ? r.issues.join("; ") : r.issues}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <SectionTitle id="thay-doi">Lịch sử thay đổi</SectionTitle>
      {data.changes.length === 0 ? <Empty>Chưa có thay đổi.</Empty> : (
        <ul className="mb-8 space-y-2">
          {data.changes.map((c) => (
            <li key={c.id} className="rounded-xl border border-line bg-surface p-3 text-sm">
              <p className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs text-muted">{c.id}</span>
                <IdLink id={c.target_id} sourceId={comments[c.target_id]} />
                <span>{fmtTime(c.checked_at)}</span>
                <Badge tone={c.status === "active" ? "neutral" : "warning"}>{label(data, "recheck_status", c.status)}</Badge>
                {c.metrics_grew && <Badge tone="accent">Tương tác tăng</Badge>}
              </p>
              {c.new_text && <p className="prose-raw mt-1">{displayText(c.new_text)}</p>}
              {c.updates && <p className="mt-1 text-xs text-ink-2">Cập nhật: {Object.entries(c.updates).map(([k, v]) => `${k} = ${String(v).slice(0, 120)}`).join(" · ")}</p>}
              {c.notes && <p className="mt-1 text-xs text-muted">{c.notes}</p>}
            </li>
          ))}
        </ul>
      )}

      <SectionTitle id="loai-tru">Đã loại trừ (trùng tên, không thuộc vụ việc)</SectionTitle>
      <p className="mb-2 text-xs text-muted">Không ghi tên người đăng — chỉ link, trích đoạn và lý do, để kiểm tra lại việc lọc.</p>
      {data.exclusions.length === 0 ? <Empty>Chưa có kết quả bị loại.</Empty> : (
        <ul className="space-y-2">
          {data.exclusions.map((x) => (
            <li key={x.id} className="rounded-xl border border-line bg-surface p-3 text-sm">
              <p className="font-mono text-xs text-muted">{x.id} · {fmtTime(x.recorded_at)}</p>
              <p className="mt-1">“{x.excerpt}”</p>
              <p className="mt-1 text-xs text-ink-2">{x.reason} · <Ext href={x.url} /></p>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
