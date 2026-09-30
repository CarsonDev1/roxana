import type { Metadata } from "next";
import Link from "next/link";
import { Nav } from "@/components/Nav";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Theo dõi vụ việc Roxana Plaza", template: "%s · Roxana Plaza" },
  description: "Tổng hợp các lần nhắc tới vụ việc trên mạng xã hội — xem trên máy, chỉ đọc",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="vi" className="h-full antialiased">
      <body className="flex min-h-full flex-col">
        <a href="#noi-dung" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-surface focus:px-3 focus:py-2">
          Bỏ qua tới nội dung
        </a>
        <header className="no-print sticky top-0 z-40 border-b border-line bg-surface/95 backdrop-blur">
          <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 py-3 lg:flex-row lg:items-center lg:gap-6">
            <Link href="/" className="shrink-0 font-semibold tracking-tight text-ink">
              Roxana Plaza <span className="font-normal text-muted">· theo dõi dư luận</span>
            </Link>
            <Nav />
          </div>
        </header>
        <main id="noi-dung" className="mx-auto w-full max-w-7xl flex-1 px-4 py-6">{children}</main>
        <footer className="no-print border-t border-line py-4 text-center text-xs text-muted">
          Chạy trên máy này, chỉ đọc. Nội dung nguyên văn giữ nguyên lời người đăng; phân loại chỉ mô tả nội dung, không phải kết luận pháp lý.
        </footer>
      </body>
    </html>
  );
}
