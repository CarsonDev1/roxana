"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

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

export function Nav() {
  const path = usePathname();
  return (
    <nav aria-label="Mục chính" className="flex gap-1 overflow-x-auto">
      {LINKS.map((l) => {
        const active = l.href === "/" ? path === "/" : path.startsWith(l.href);
        return (
          <Link key={l.href} href={l.href} aria-current={active ? "page" : undefined}
            className={`whitespace-nowrap rounded-md px-3 py-2 text-sm transition-colors ${
              active ? "bg-accent-wash font-semibold text-accent-ink" : "text-ink-2 hover:bg-surface-2 hover:text-ink"}`}>
            {l.label}
          </Link>
        );
      })}
    </nav>
  );
}
