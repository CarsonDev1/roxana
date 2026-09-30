import type { SiteData } from "./types";

export type Option = { value: string; label: string };

function fromLabels(data: SiteData, enumName: string, present: Set<string>): Option[] {
  return Object.entries(data.labels[enumName] ?? {})
    .filter(([v]) => present.has(v)).map(([value, label]) => ({ value, label }));
}

/** Chỉ các lựa chọn thực sự có trong dữ liệu — không liệt kê bộ lọc rỗng. */
export function sourceOptions(data: SiteData): Record<string, Option[]> {
  const s = data.sources;
  const set = (xs: (string | null | undefined)[]) => new Set(xs.filter(Boolean) as string[]);
  return {
    platform: fromLabels(data, "platform", set(s.map((x) => x.platform))),
    container: data.containers.map((c) => ({ value: c.id, label: c.name })),
    tone: fromLabels(data, "tone", set(s.map((x) => x.tone))),
    importance: fromLabels(data, "importance", set(s.map((x) => x.importance))),
    party: data.parties.filter((p) => s.some((x) => (x.entities_mentioned ?? []).includes(p.id)))
      .map((p) => ({ value: p.id, label: p.label || p.name })),
    topic: fromLabels(data, "topics", set(s.flatMap((x) => x.topics ?? []))),
    status: fromLabels(data, "recheck_status", set(s.map((x) => x.status))),
  };
}

export function commentOptions(data: SiteData): Record<string, Option[]> {
  const c = data.comments;
  const set = (xs: (string | null | undefined)[]) => new Set(xs.filter(Boolean) as string[]);
  return {
    tone: fromLabels(data, "tone", set(c.map((x) => x.tone))),
    importance: fromLabels(data, "importance", set(c.map((x) => x.importance))),
    party: data.parties.filter((p) => c.some((x) => (x.entities_mentioned ?? []).includes(p.id)))
      .map((p) => ({ value: p.id, label: p.label || p.name })),
  };
}

export function first(v: string | string[] | undefined): string | undefined {
  return Array.isArray(v) ? v[0] : v || undefined;
}
