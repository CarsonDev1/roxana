"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { filterSources, type SourceFilters, type SourceSort } from "@/lib/filter";
import { excerpt, fmtTime } from "@/lib/text";
import type { Source } from "@/lib/types";
import { Thumb } from "./Thumb";
import { Badge, ImportanceBadge, StatusBadge, ToneBadge } from "./ui";

export type Option = { value: string; label: string };
type Labels = Record<string, Record<string, string>>;

const FACETS: { key: keyof SourceFilters; label: string }[] = [
  { key: "platform", label: "Nền tảng" }, { key: "container", label: "Nhóm/trang" }, { key: "tone", label: "Thái độ" },
  { key: "importance", label: "Mức quan trọng" }, { key: "party", label: "Bên được nhắc" },
  { key: "topic", label: "Chủ đề" }, { key: "status", label: "Trạng thái" },
];

export function SourceList({ sources, labels, options, initial }: {
  sources: Source[]; labels: Labels; options: Record<string, Option[]>; initial: SourceFilters & { sort?: SourceSort };
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [f, setF] = useState<SourceFilters>(initial);
  const [sort, setSort] = useState<SourceSort>(initial.sort ?? "posted_desc");
  const shown = useMemo(() => filterSources(sources, f, sort), [sources, f, sort]);
  const L = (e: string, v: string | null | undefined) => (v ? labels[e]?.[v] ?? v : "");

  function update(next: SourceFilters, nextSort = sort) {
    setF(next);
    setSort(nextSort);
    const qs = new URLSearchParams(Object.entries({ ...next, sort: nextSort === "posted_desc" ? "" : nextSort })
      .filter(([, v]) => v) as [string, string][]);
    router.replace(qs.size ? `${pathname}?${qs}` : pathname, { scroll: false });
  }

  const active = Object.values(f).filter(Boolean).length;

  return (
    <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
      <aside className="space-y-3 lg:sticky lg:top-24 lg:self-start" aria-label="Bộ lọc">
        <label className="block">
          <span className="text-xs font-medium text-ink-2">Tìm trong nội dung, người đăng, chữ trong ảnh</span>
          <input type="search" value={f.q ?? ""} onChange={(e) => update({ ...f, q: e.target.value })}
            placeholder="vd: Ngọc Liên, giấy mời, tăng giá…"
            className="mt-1 w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm placeholder:text-muted" />
        </label>
        {FACETS.map(({ key, label }) => (
          <label key={key} className="block">
            <span className="text-xs font-medium text-ink-2">{label}</span>
            <select value={f[key] ?? ""} onChange={(e) => update({ ...f, [key]: e.target.value || undefined })}
              className="mt-1 w-full rounded-lg border border-line bg-surface px-2 py-1.5 text-sm">
              <option value="">Tất cả</option>
              {(options[key] ?? []).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </label>
        ))}
        {active > 0 && (
          <button type="button" onClick={() => update({})} className="text-sm text-accent-ink hover:underline">Xoá bộ lọc</button>
        )}
      </aside>

      <div>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-ink-2" aria-live="polite"><strong className="text-ink">{shown.length}</strong> / {sources.length} bài</p>
          <label className="flex items-center gap-2 text-sm">
            <span className="text-ink-2">Sắp xếp</span>
            <select value={sort} onChange={(e) => update(f, e.target.value as SourceSort)}
              className="rounded-lg border border-line bg-surface px-2 py-1">
              <option value="posted_desc">Ngày đăng mới nhất</option>
              <option value="posted_asc">Ngày đăng cũ nhất</option>
              <option value="captured_desc">Thu thập gần nhất</option>
              <option value="importance">Quan trọng trước</option>
            </select>
          </label>
        </div>

        <ul className="space-y-3">
          {shown.map((s) => (
            <li key={s.id}>
              <Link href={`/bai-viet/${s.id}`}
                className="grid gap-4 rounded-xl border border-line bg-surface p-3 shadow-sm hover:bg-surface-2 sm:grid-cols-[160px_1fr]">
                <Thumb image={s.main_image} alt={`Ảnh bài ${s.id}`} link={false} className="aspect-[4/3] sm:h-28" />
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
                    <span className="font-semibold">{s.author_name}</span>
                    {s.container_name && <span className="text-muted">trong {s.container_name}</span>}
                  </div>
                  <p className="text-xs text-muted">
                    {fmtTime(s.posted_at, s.posted_at_precision) || s.posted_at_raw || "Không rõ ngày"} · {L("platform", s.platform)} · <span className="font-mono">{s.id}</span>
                  </p>
                  <p className="mt-1.5 line-clamp-2 text-sm text-ink-2">{excerpt(s.current_text ?? s.text, 260) || "(chỉ có ảnh)"}</p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    <ImportanceBadge value={s.importance} label={L("importance", s.importance)} />
                    <ToneBadge value={s.tone} label={L("tone", s.tone)} />
                    <StatusBadge value={s.status} label={L("recheck_status", s.status)} />
                    {s.comments_collected > 0 && <Badge tone="neutral">{s.comments_collected} bình luận</Badge>}
                  </div>
                </div>
              </Link>
            </li>
          ))}
        </ul>
        {shown.length === 0 && <p className="rounded-lg border border-dashed border-line p-6 text-center text-sm text-muted">Không có bài khớp bộ lọc.</p>}
      </div>
    </div>
  );
}
