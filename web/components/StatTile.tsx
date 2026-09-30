import Link from "next/link";

export function StatTile({ label, value, hint, href, tone }:
  { label: string; value: number; hint?: string; href?: string; tone?: "critical" | "warning" }) {
  const body = (
    <>
      <p className="text-sm text-ink-2">{label}</p>
      <p className="mt-1 text-3xl font-semibold tracking-tight">{value.toLocaleString("vi-VN")}</p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </>
  );
  const cls = `block rounded-xl border bg-surface p-4 shadow-sm ${
    tone === "critical" && value ? "border-critical/40" : tone === "warning" && value ? "border-warning/60" : "border-line"}`;
  return href ? <Link href={href} className={`${cls} hover:bg-surface-2`}>{body}</Link> : <div className={cls}>{body}</div>;
}
