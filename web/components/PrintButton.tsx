"use client";

export function PrintButton({ label = "In danh mục" }: { label?: string }) {
  return (
    <button type="button" onClick={() => window.print()}
      className="no-print rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90">
      {label}
    </button>
  );
}
