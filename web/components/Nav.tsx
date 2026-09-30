"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Sheet } from "./Sheet";

const LINKS = [
  { href: "/", label: "Tổng quan" },
  { href: "/bai-viet", label: "Bài viết" },
  { href: "/binh-luan", label: "Bình luận" },
  { href: "/dong-thoi-gian", label: "Dòng thời gian" },
  { href: "/bang-chung", label: "Bằng chứng" },
  { href: "/nguoi", label: "Người & tổ chức" },
  { href: "/nhom", label: "Nhóm & trang" },
  { href: "/nhat-ky", label: "Nhật ký" },
  { href: "/chu-thich", label: "Chú thích" },
];

/** Từ màn hình xl: thanh menu ngang. Nhỏ hơn: nút ☰ mở menu dạng Sheet trượt từ bên phải. */
export function Nav() {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const [lastPath, setLastPath] = useState(path);
  if (lastPath !== path) {
    setLastPath(path);
    setOpen(false);
  }
  const isActive = (href: string) => (href === "/" ? path === "/" : path.startsWith(href));

  return (
    <>
      <nav aria-label="Mục chính" className="hidden gap-1 xl:flex">
        {LINKS.map((l) => (
          <Link key={l.href} href={l.href} aria-current={isActive(l.href) ? "page" : undefined}
            className={`whitespace-nowrap rounded-md px-3 py-2 text-sm transition-colors ${
              isActive(l.href) ? "bg-accent-wash font-semibold text-accent-ink" : "text-ink-2 hover:bg-surface-2 hover:text-ink"}`}>
            {l.label}
          </Link>
        ))}
      </nav>

      <button type="button" onClick={() => setOpen(true)} aria-label="Mở menu" aria-haspopup="dialog" aria-expanded={open}
        className="-mr-2 ml-auto rounded-md p-2 text-ink-2 hover:bg-surface-2 hover:text-ink xl:hidden">
        <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
          <path d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>
      <Sheet open={open} onClose={() => setOpen(false)} title="Menu">
        <nav aria-label="Mục chính (điện thoại)" className="flex flex-col gap-1">
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href} onClick={() => setOpen(false)} aria-current={isActive(l.href) ? "page" : undefined}
              className={`rounded-lg px-3 py-3 text-[15px] transition-colors ${
                isActive(l.href) ? "bg-accent-wash font-semibold text-accent-ink" : "text-ink-2 hover:bg-surface-2 hover:text-ink"}`}>
              {l.label}
            </Link>
          ))}
        </nav>
      </Sheet>
    </>
  );
}
