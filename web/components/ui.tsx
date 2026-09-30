import Link from "next/link";
import type { ReactNode } from "react";

type Tone = "critical" | "serious" | "warning" | "good" | "accent" | "neutral" | "muted";

const TONE_CLASS: Record<Tone, string> = {
  critical: "bg-critical-wash text-ink ring-critical/40",
  serious: "bg-serious-wash text-ink ring-serious/40",
  warning: "bg-warning-wash text-ink ring-warning/50",
  good: "bg-good-wash text-ink ring-good/40",
  accent: "bg-accent-wash text-accent-ink ring-accent/30",
  neutral: "bg-surface-2 text-ink-2 ring-line",
  muted: "bg-transparent text-muted ring-line",
};

/** Nhãn: màu luôn đi kèm chữ (và biểu tượng với trạng thái) — không dùng màu làm tín hiệu duy nhất. */
export function Badge({ tone = "neutral", icon, children, title }:
  { tone?: Tone; icon?: string; children: ReactNode; title?: string }) {
  return (
    <span title={title} className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${TONE_CLASS[tone]}`}>
      {icon && <span aria-hidden="true">{icon}</span>}
      {children}
    </span>
  );
}

export function ImportanceBadge({ value, label }: { value: string | null; label: string }) {
  if (!value) return null;
  if (value === "cao") return <Badge tone="critical" icon="▲">Mức {label.toLowerCase()}</Badge>;
  if (value === "thap") return <Badge tone="muted">Mức {label.toLowerCase()}</Badge>;
  return <Badge tone="neutral">Mức {label.toLowerCase()}</Badge>;
}

export function ToneBadge({ value, label }: { value: string | null; label: string }) {
  if (!value) return null;
  const map: Record<string, [Tone, string]> = {
    gay_gat: ["critical", "‼"], tieu_cuc: ["serious", "−"], trung_lap: ["neutral", "○"], tich_cuc: ["good", "+"],
  };
  const [tone, icon] = map[value] ?? ["neutral", ""];
  return <Badge tone={tone} icon={icon}>{label}</Badge>;
}

export function StatusBadge({ value, label }: { value: string; label: string }) {
  if (!value || value === "active") return null;
  const icon = value === "deleted" ? "✕" : value === "edited" ? "✎" : "!";
  return <Badge tone="warning" icon={icon}>{label}</Badge>;
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-xl border border-line bg-surface p-4 shadow-sm ${className}`}>{children}</section>;
}

export function PageTitle({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-ink-2">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}

export function SectionTitle({ children, id }: { children: ReactNode; id?: string }) {
  return <h2 id={id} className="mb-3 text-base font-semibold">{children}</h2>;
}

export function KeyVal({ items }: { items: [string, ReactNode][] }) {
  const shown = items.filter(([, v]) => v !== null && v !== undefined && v !== "");
  return (
    <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1.5 text-sm">
      {shown.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="text-muted">{k}</dt>
          <dd className="min-w-0 break-words">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export function Ext({ href, children }: { href: string | null | undefined; children?: ReactNode }) {
  if (!href) return null;
  return (
    <a href={href} target="_blank" rel="noopener noreferrer nofollow" className="break-all text-accent-ink underline decoration-accent/40 underline-offset-2 hover:decoration-accent">
      {children ?? href}
    </a>
  );
}

export function IdLink({ id, sourceId }: { id: string; sourceId?: string | null }) {
  const href = id.startsWith("FB-C") || id.startsWith("WEB-C") ? `/bai-viet/${sourceId}#${id}` : `/bai-viet/${id}`;
  return <Link href={href} className="font-mono text-xs text-accent-ink hover:underline">{id}</Link>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="rounded-lg border border-dashed border-line p-6 text-center text-sm text-muted">{children}</p>;
}

export function NoData() {
  return (
    <Card className="mx-auto max-w-2xl">
      <h1 className="text-lg font-semibold">Chưa có dữ liệu để hiển thị</h1>
      <p className="mt-2 text-sm text-ink-2">Chạy lệnh sau trong thư mục dự án rồi tải lại trang:</p>
      <pre className="mt-3 overflow-x-auto rounded-lg bg-surface-2 p-3 text-sm">python .claude/skills/mention-monitor/scripts/export_site.py</pre>
    </Card>
  );
}

export function Warnings({ items, generatedAt, schemaOk }: { items: string[]; generatedAt: string; schemaOk: boolean }) {
  if (schemaOk && items.length === 0) return null;
  return (
    <div role="status" className="no-print mb-4 rounded-lg border border-warning/60 bg-warning-wash p-3 text-sm">
      <p className="font-medium"><span aria-hidden="true">! </span>Cần chú ý</p>
      {!schemaOk && <p>Dữ liệu được xuất bằng phiên bản khác của script ({generatedAt}) — chạy lại export_site.py.</p>}
      <ul className="mt-1 list-disc pl-5">{items.slice(0, 10).map((w) => <li key={w}>{w}</li>)}</ul>
    </div>
  );
}
