import { fold } from "./text";
import type { Comment, Source } from "./types";

export type SourceFilters = {
  q?: string; platform?: string; container?: string; tone?: string; importance?: string; party?: string;
  topic?: string; status?: string;
};
export type SourceSort = "posted_desc" | "posted_asc" | "captured_desc" | "importance";

const IMPORTANCE_RANK: Record<string, number> = { cao: 0, trung_binh: 1, thap: 2 };

function matchQuery(search: string, q?: string) {
  const needle = fold(q);
  return !needle || needle.split(" ").every((w) => search.includes(w));
}

function byDate(a: string | null, b: string | null, dir: 1 | -1) {
  if (!a && !b) return 0;
  if (!a) return 1; // ngày không rõ luôn xuống cuối
  if (!b) return -1;
  return a < b ? -dir : a > b ? dir : 0;
}

export function filterSources(list: Source[], f: SourceFilters, sort: SourceSort = "posted_desc"): Source[] {
  const out = list.filter((s) =>
    matchQuery(s.search, f.q)
    && (!f.platform || s.platform === f.platform)
    && (!f.container || s.container_id === f.container)
    && (!f.tone || s.tone === f.tone)
    && (!f.importance || s.importance === f.importance)
    && (!f.party || (s.entities_mentioned ?? []).includes(f.party))
    && (!f.topic || (s.topics ?? []).includes(f.topic))
    && (!f.status || s.status === f.status));
  const cmp: Record<SourceSort, (a: Source, b: Source) => number> = {
    posted_desc: (a, b) => byDate(a.posted_at, b.posted_at, -1) || a.id.localeCompare(b.id),
    posted_asc: (a, b) => byDate(a.posted_at, b.posted_at, 1) || a.id.localeCompare(b.id),
    captured_desc: (a, b) => byDate(a.captured_at, b.captured_at, -1) || a.id.localeCompare(b.id),
    importance: (a, b) => (IMPORTANCE_RANK[a.importance] ?? 9) - (IMPORTANCE_RANK[b.importance] ?? 9)
      || byDate(a.posted_at, b.posted_at, -1),
  };
  return [...out].sort(cmp[sort]);
}

export type CommentFilters = { q?: string; tone?: string; importance?: string; party?: string; source?: string };

export function filterComments(list: Comment[], f: CommentFilters): Comment[] {
  return list.filter((c) =>
    matchQuery(c.search, f.q)
    && (!f.tone || c.tone === f.tone)
    && (!f.importance || c.importance === f.importance)
    && (!f.party || (c.entities_mentioned ?? []).includes(f.party))
    && (!f.source || c.source_id === f.source))
    .sort((a, b) => a.order - b.order);
}
