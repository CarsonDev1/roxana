"use client";
/* eslint-disable @next/next/no-img-element -- ảnh bằng chứng hiển thị nguyên bản qua /api/file */

import { useEffect, useRef, useState, type ReactNode } from "react";
import { fileUrl } from "@/lib/files";
import { fmtTime } from "@/lib/text";

export type ViewerImage = {
  file: string;
  title?: string | null;
  sha256?: string | null;
  captured_at?: string | null;
};

/** Khung xem ảnh ngay trên trang (thẻ <dialog>): Esc / nút ✕ / bấm nền để đóng; bấm ảnh để phóng to 100%. */
export function ImageDialog({ image, onClose }: { image: ViewerImage | null; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  const [zoom, setZoom] = useState(false);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (image && !d.open) {
      setZoom(false);
      d.showModal();
    } else if (!image && d.open) {
      d.close();
    }
  }, [image]);

  const src = image ? fileUrl(image.file)! : "";
  return (
    <dialog ref={ref} onClose={onClose} aria-label={image?.title ?? "Xem ảnh"}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      className="m-auto h-[94vh] w-[96vw] max-w-none rounded-xl bg-surface p-0 shadow-2xl backdrop:bg-black/70">
      {image && (
        <div className="flex h-full flex-col">
          <div className="flex items-start justify-between gap-3 border-b border-line px-4 py-2.5">
            <div className="min-w-0 text-sm">
              {image.title && <p className="font-medium">{image.title}</p>}
              <p className="text-xs text-muted">
                {image.captured_at && <>Chụp {fmtTime(image.captured_at)} · </>}
                <span className="font-mono">{image.file}</span>
              </p>
              {image.sha256 && <p className="break-all font-mono text-[11px] text-muted">SHA-256 {image.sha256}</p>}
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <button type="button" onClick={() => setZoom((z) => !z)}
                className="rounded-md px-2.5 py-1 text-sm ring-1 ring-line hover:bg-surface-2">
                {zoom ? "Vừa màn hình" : "Kích thước thật"}
              </button>
              <button type="button" onClick={onClose} aria-label="Đóng"
                className="rounded-md px-2.5 py-1 text-sm ring-1 ring-line hover:bg-surface-2">✕</button>
            </div>
          </div>
          <div className={`flex-1 bg-surface-2 ${zoom ? "overflow-auto" : "flex items-center justify-center overflow-hidden p-3"}`}>
            <img src={src} alt={image.title ?? "Ảnh bằng chứng"} onClick={() => setZoom((z) => !z)}
              className={zoom ? "max-w-none cursor-zoom-out" : "max-h-full max-w-full cursor-zoom-in object-contain"} />
          </div>
        </div>
      )}
    </dialog>
  );
}

/** Nút/đường link chữ mở ảnh trong khung xem (thay cho mở tab mới). */
export function ImageLink({ image, children, className = "" }:
  { image: ViewerImage; children: ReactNode; className?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)} className={`text-left hover:underline ${className}`}>{children}</button>
      <ImageDialog image={open ? image : null} onClose={() => setOpen(false)} />
    </>
  );
}
