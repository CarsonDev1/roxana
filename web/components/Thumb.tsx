"use client";
/* eslint-disable @next/next/no-img-element -- ảnh bằng chứng phục vụ nguyên bản qua /api/file, không tối ưu hoá */

import { useState } from "react";
import { fileUrl } from "@/lib/files";
import type { Image } from "@/lib/types";
import { ImageDialog } from "./ImageViewer";

/** Ảnh thu nhỏ; bấm để xem lớn ngay trên trang. Ảnh thiếu/hỏng hiện khung báo thay vì vỡ trang. */
export function Thumb({ image, alt, className = "", big = false, link = true }:
  { image: Image | null; alt: string; className?: string; big?: boolean; link?: boolean }) {
  const [broken, setBroken] = useState(false);
  const [open, setOpen] = useState(false);
  if (!image) {
    return <div className={`flex items-center justify-center rounded-lg bg-surface-2 p-4 text-center text-xs text-muted ${className}`}>Chưa có ảnh chụp</div>;
  }
  // Ảnh lớn dùng file gốc (ảnh thu nhỏ 240px phóng to sẽ mờ); danh sách dùng ảnh thu nhỏ cho nhẹ.
  const src = big ? fileUrl(image.file) : fileUrl(image.thumb) ?? fileUrl(image.file);
  if (broken || !src) {
    return (
      <div className={`flex flex-col items-center justify-center gap-1 rounded-lg bg-surface-2 p-4 text-center text-xs text-muted ${className}`}>
        <span>Ảnh không đọc được</span>
        <span className="break-all font-mono">{image.file}</span>
      </div>
    );
  }
  const img = <img src={src} alt={alt} loading="lazy" onError={() => setBroken(true)}
    className={big ? "h-auto w-full object-contain" : "h-full max-h-72 w-full object-cover object-top"} />;
  const cls = `block overflow-hidden rounded-lg bg-surface-2 ring-1 ring-line ${className}`;
  if (!link) return <div className={cls}>{img}</div>; // nằm trong thẻ bấm được khác (vd thẻ bài) — không mở khung xem
  return (
    <>
      <button type="button" onClick={() => setOpen(true)} title="Xem ảnh lớn" aria-label={`Xem ảnh lớn: ${alt}`}
        className={`${cls} w-full cursor-zoom-in text-left transition hover:ring-2 hover:ring-accent/50`}>
        {img}
      </button>
      <ImageDialog image={open ? { file: image.file, title: image.shows || alt, sha256: image.sha256, captured_at: image.captured_at } : null}
        onClose={() => setOpen(false)} />
    </>
  );
}
