import type { Metadata } from "next";
import Link from "next/link";
import { Badge, Empty, IdLink, NoData, PageTitle } from "@/components/ui";
import { getData, label } from "@/lib/data";
import { excerpt, fmtTime } from "@/lib/text";

export const metadata: Metadata = { title: "Dòng thời gian" };

type Row =
  | { kind: "event"; key: string; sort: string; dateText: string; id: string; title: string; source: string | null;
      reliability: string; related: string[] }
  | { kind: "post"; key: string; sort: string; dateText: string; id: string; title: string; author: string;
      container: string | null };

const RELIABILITY_TONE = { bao_chi: "good", van_ban: "accent", mxh: "warning" } as const;

export default async function TimelinePage({ searchParams }: PageProps<"/dong-thoi-gian">) {
  const data = await getData();
  if (!data) return <NoData />;
  const showPosts = (await searchParams).bai !== "0";
  const rows: Row[] = [
    ...data.events.map((e): Row => ({
      kind: "event", key: e.id, sort: e.date || e.sort_key || "9999", dateText: e.date_raw, id: e.id,
      title: e.description, source: e.source_text, reliability: e.reliability, related: e.related_ids ?? [] })),
    ...(showPosts ? data.sources.filter((s) => s.importance === "cao" && s.posted_at).map((s): Row => ({
      kind: "post", key: s.id, sort: s.posted_at!.slice(0, 10), dateText: fmtTime(s.posted_at, s.posted_at_precision),
      id: s.id, title: excerpt(s.text, 200), author: s.author_name, container: s.container_name })) : []),
  ].sort((a, b) => a.sort.localeCompare(b.sort) || (a.kind === "event" ? -1 : 1));

  return (
    <>
      <PageTitle title="Dòng thời gian"
        subtitle="Các mốc của vụ việc (kèm độ tin cậy của nguồn) và các bài mức quan trọng cao theo ngày đăng."
        actions={<Link href={showPosts ? "?bai=0" : "?"} className="no-print text-sm text-accent-ink hover:underline">
          {showPosts ? "Chỉ hiện mốc sự kiện" : "Hiện cả bài mức cao"}</Link>} />
      {rows.length === 0 ? <Empty>Chưa có mốc nào.</Empty> : (
        <ol className="relative ml-3 border-l-2 border-line">
          {rows.map((r) => (
            <li key={r.key} className="mb-5 ml-6">
              <span aria-hidden="true" className={`absolute -left-[7px] mt-1.5 h-3 w-3 rounded-full ring-4 ring-page ${r.kind === "event" ? "bg-accent" : "bg-critical"}`} />
              <p className="tabular text-sm font-semibold">{r.dateText || "Không rõ ngày"}</p>
              {r.kind === "event" ? (
                <div className="mt-1 rounded-xl border border-line bg-surface p-3">
                  <p className="text-[15px]">{r.title}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-ink-2">
                    <Badge tone={RELIABILITY_TONE[r.reliability as keyof typeof RELIABILITY_TONE] ?? "neutral"}>
                      {label(data, "reliability", r.reliability)}</Badge>
                    {r.source && <span>Nguồn: {r.source}</span>}
                    {r.related.map((id) => <IdLink key={id} id={id} />)}
                    <span className="font-mono text-muted">{r.id}</span>
                  </div>
                </div>
              ) : (
                <Link href={`/bai-viet/${r.id}`} className="mt-1 block rounded-xl border border-critical/30 bg-surface p-3 hover:bg-surface-2">
                  <p className="text-xs text-muted"><span aria-hidden="true">▲ </span>Bài mức cao · {r.author}{r.container ? ` · ${r.container}` : ""} · <span className="font-mono">{r.id}</span></p>
                  <p className="mt-1 text-sm text-ink-2">{r.title}</p>
                </Link>
              )}
            </li>
          ))}
        </ol>
      )}
    </>
  );
}
