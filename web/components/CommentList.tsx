"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { filterComments, type CommentFilters } from "@/lib/filter";
import type { Option } from "@/lib/options";
import { displayText, fmtTime } from "@/lib/text";
import type { Comment } from "@/lib/types";
import { Badge, ImportanceBadge, StatusBadge, ToneBadge } from "./ui";

const PAGE = 200;

export function CommentList({ comments, labels, options, sourceTitles, initial }: {
  comments: Comment[]; labels: Record<string, Record<string, string>>; options: Record<string, Option[]>;
  sourceTitles: Record<string, string>; initial: CommentFilters;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [f, setF] = useState<CommentFilters>(initial);
  const [limit, setLimit] = useState(PAGE);
  const shown = useMemo(() => filterComments(comments, f), [comments, f]);
  const L = (e: string, v: string | null | undefined) => (v ? labels[e]?.[v] ?? v : "");

  function update(next: CommentFilters) {
    setF(next);
    setLimit(PAGE);
    const qs = new URLSearchParams(Object.entries(next).filter(([, v]) => v) as [string, string][]);
    router.replace(qs.size ? `${pathname}?${qs}` : pathname, { scroll: false });
  }

  return (
    <>
      <div className="mb-4 flex flex-wrap items-end gap-3" role="search">
        <label className="min-w-64 flex-1">
          <span className="text-xs font-medium text-ink-2">Tìm trong bình luận, người viết</span>
          <input type="search" value={f.q ?? ""} onChange={(e) => update({ ...f, q: e.target.value })}
            className="mt-1 w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm" />
        </label>
        {([["tone", "Thái độ"], ["importance", "Mức quan trọng"], ["party", "Bên được nhắc"]] as const).map(([k, lab]) => (
          <label key={k}>
            <span className="text-xs font-medium text-ink-2">{lab}</span>
            <select value={f[k] ?? ""} onChange={(e) => update({ ...f, [k]: e.target.value || undefined })}
              className="mt-1 block rounded-lg border border-line bg-surface px-2 py-2 text-sm">
              <option value="">Tất cả</option>
              {(options[k] ?? []).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </label>
        ))}
        {f.source && <Badge tone="accent">Chỉ bài {f.source} <button type="button" aria-label="Bỏ lọc bài" className="ml-1" onClick={() => update({ ...f, source: undefined })}>×</button></Badge>}
      </div>
      <p className="mb-3 text-sm text-ink-2" aria-live="polite"><strong className="text-ink">{shown.length}</strong> / {comments.length} bình luận</p>
      <ul className="space-y-2">
        {shown.slice(0, limit).map((c) => (
          <li key={c.id} className="rounded-xl border border-line bg-surface p-3" style={{ marginLeft: `${(c.depth - 1) * 1.5}rem` }}>
            <div className="flex flex-wrap items-center gap-x-2 text-sm">
              <span className="font-semibold">{c.author_name}</span>
              {c.depth > 1 && <span className="text-xs text-muted">↳ trả lời</span>}
              <span className="text-xs text-muted">{fmtTime(c.posted_at, c.posted_at_precision) || c.posted_at_raw}</span>
              <Link href={`/bai-viet/${c.source_id}#${c.id}`} className="font-mono text-xs text-accent-ink hover:underline">{c.id}</Link>
              <span className="truncate text-xs text-muted">trong bài {sourceTitles[c.source_id] ?? c.source_id}</span>
            </div>
            <p className="prose-raw mt-1 text-sm">{c.text ? displayText(c.text) : <em className="text-muted">(không có chữ)</em>}</p>
            <div className="mt-1.5 flex flex-wrap gap-1">
              <ImportanceBadge value={c.importance} label={L("importance", c.importance)} />
              <ToneBadge value={c.tone} label={L("tone", c.tone)} />
              <StatusBadge value={c.status} label={L("recheck_status", c.status)} />
            </div>
          </li>
        ))}
      </ul>
      {shown.length > limit && (
        <button type="button" onClick={() => setLimit((n) => n + PAGE)}
          className="mt-4 w-full rounded-lg border border-line bg-surface py-2 text-sm hover:bg-surface-2">
          Xem thêm {Math.min(PAGE, shown.length - limit)} bình luận
        </button>
      )}
    </>
  );
}
