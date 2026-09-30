"use client";

import { useEffect, useRef, type ReactNode } from "react";

/**
 * Ngăn trượt từ cạnh màn hình (Sheet), dựng trên thẻ <dialog> như ImageDialog:
 * Esc / nút ✕ / bấm nền để đóng, focus bị giữ trong ngăn khi mở và trả lại nút mở khi đóng.
 */
export function Sheet({ open, onClose, title, side = "right", children }:
  { open: boolean; onClose: () => void; title: string; side?: "left" | "right"; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    else if (!open && d.open) d.close();
  }, [open]);

  return (
    <dialog ref={ref} onClose={onClose} aria-label={title}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      className={`sheet m-0 h-dvh max-h-none w-[min(20rem,85vw)] max-w-none overflow-hidden border-line bg-surface p-0 text-ink shadow-2xl backdrop:bg-black/50 ${
        side === "right" ? "sheet-right ml-auto border-l" : "sheet-left mr-auto border-r"}`}>
      <div className="flex h-full flex-col">
        <div className="flex items-center justify-between border-b border-line px-4 py-3">
          <p className="font-semibold tracking-tight">{title}</p>
          <button type="button" onClick={onClose} aria-label="Đóng menu"
            className="-mr-2 rounded-md p-2 text-ink-2 hover:bg-surface-2 hover:text-ink">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto overscroll-contain p-3">{children}</div>
      </div>
    </dialog>
  );
}
