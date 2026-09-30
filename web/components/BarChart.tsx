"use client";

import { useId, useState } from "react";

export type Bar = { key: string; label: string; value: number; href?: string };

/**
 * Một chuỗi số liệu, một màu (sequential/emphasis) — nhãn và giá trị dùng màu chữ, không dùng màu thanh.
 * Thanh ≤ 24px, đầu bo 4px, mốc 0 vuông; tooltip khi rê chuột/focus; luôn có chế độ xem bảng.
 */
export function BarChart({ title, bars, orientation = "row", unit = "mục", note }:
  { title: string; bars: Bar[]; orientation?: "row" | "column"; unit?: string; note?: string }) {
  const [table, setTable] = useState(false);
  const [hover, setHover] = useState<string | null>(null);
  const id = useId();
  const max = Math.max(1, ...bars.map((b) => b.value));
  const total = bars.reduce((s, b) => s + b.value, 0);

  return (
    <figure aria-labelledby={`${id}-t`}>
      <div className="mb-3 flex items-baseline justify-between gap-2">
        <figcaption id={`${id}-t`} className="text-sm font-semibold">{title}</figcaption>
        <button type="button" onClick={() => setTable((v) => !v)}
          className="no-print rounded px-2 py-0.5 text-xs text-ink-2 ring-1 ring-line hover:bg-surface-2">
          {table ? "Xem biểu đồ" : "Xem bảng"}
        </button>
      </div>

      {table ? (
        <table className="w-full text-sm">
          <thead><tr className="text-left text-muted"><th className="py-1 font-normal">Nhóm</th><th className="py-1 text-right font-normal">Số {unit}</th></tr></thead>
          <tbody>
            {bars.map((b) => (
              <tr key={b.key} className="border-t border-line">
                <td className="py-1">{b.href ? <a className="hover:underline" href={b.href}>{b.label}</a> : b.label}</td>
                <td className="tabular py-1 text-right">{b.value.toLocaleString("vi-VN")}</td>
              </tr>
            ))}
            <tr className="border-t border-line font-medium"><td className="py-1">Tổng</td><td className="tabular py-1 text-right">{total.toLocaleString("vi-VN")}</td></tr>
          </tbody>
        </table>
      ) : orientation === "row" ? (
        <ul className="space-y-2">
          {bars.map((b) => {
            const w = (b.value / max) * 100;
            const Inner = (
              <>
                <span className="w-40 shrink-0 truncate text-sm text-ink-2" title={b.label}>{b.label}</span>
                <span className="relative h-5 flex-1">
                  <span className="absolute inset-y-0 left-0 rounded-r-[4px] bg-accent transition-opacity"
                    style={{ width: `${b.value ? Math.max(w, 1.5) : 0}%`, maxHeight: 24, opacity: hover && hover !== b.key ? 0.45 : 1 }} />
                </span>
                <span className="tabular w-12 shrink-0 text-right text-sm font-medium">{b.value.toLocaleString("vi-VN")}</span>
              </>
            );
            const props = { onPointerEnter: () => setHover(b.key), onPointerLeave: () => setHover(null),
              onFocus: () => setHover(b.key), onBlur: () => setHover(null),
              className: "flex items-center gap-3 rounded px-1 py-0.5 hover:bg-surface-2",
              "aria-label": `${b.label}: ${b.value} ${unit}` };
            return <li key={b.key}>{b.href ? <a href={b.href} {...props}>{Inner}</a> : <div tabIndex={0} {...props}>{Inner}</div>}</li>;
          })}
        </ul>
      ) : (
        <div className="relative">
          <div className="flex h-52 items-end gap-2 border-b border-axis px-1 pt-5" role="list">
            {bars.map((b) => {
              const h = (b.value / max) * 100;
              const active = hover === b.key;
              return (
                <div key={b.key} role="listitem" tabIndex={0} aria-label={`${b.label}: ${b.value} ${unit}`}
                  onPointerEnter={() => setHover(b.key)} onPointerLeave={() => setHover(null)}
                  onFocus={() => setHover(b.key)} onBlur={() => setHover(null)}
                  className="relative flex h-full flex-1 items-end justify-center">
                  {active && (
                    <div className="pointer-events-none absolute bottom-full z-10 mb-1 -translate-y-1 whitespace-nowrap rounded-md bg-ink px-2 py-1 text-xs text-surface shadow"
                      style={{ bottom: `${h}%` }}>
                      <strong className="tabular">{b.value.toLocaleString("vi-VN")}</strong> {unit} · {b.label}
                    </div>
                  )}
                  <div className="relative w-full max-w-6 rounded-t-[4px] bg-accent transition-opacity"
                    style={{ height: `${b.value ? Math.max(h, 2) : 0}%`, opacity: hover && !active ? 0.45 : 1 }}>
                    {b.value > 0 && (
                      <span aria-hidden="true" className="tabular absolute bottom-full left-1/2 mb-0.5 -translate-x-1/2 text-[11px] font-medium text-ink-2">
                        {b.value.toLocaleString("vi-VN")}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-1 flex gap-2 px-1">
            {bars.map((b, i) => (
              <span key={b.key} className="tabular flex-1 text-center text-[11px] text-muted">
                {bars.length > 12 && i % Math.ceil(bars.length / 12) ? "" : b.label}
              </span>
            ))}
          </div>
        </div>
      )}
      {note && <p className="mt-2 text-xs text-muted">{note}</p>}
    </figure>
  );
}
