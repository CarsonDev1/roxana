import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import { Nav } from "@/components/Nav";
import "./globals.css";

// Inter có đủ dấu tiếng Việt; next/font tải lúc build và phục vụ cùng web (không gọi Google khi mở trang).
const inter = Inter({ subsets: ["latin", "vietnamese"], variable: "--font-inter", display: "swap" });

export const viewport: Viewport = { colorScheme: "light" };

export const metadata: Metadata = {
  title: { default: "Theo dõi vụ việc Roxana Plaza", template: "%s · Roxana Plaza" },
  description: "Tổng hợp các lần nhắc tới vụ việc trên mạng xã hội — xem trên máy, chỉ đọc",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="vi" className={`${inter.variable} h-full antialiased`} style={{ colorScheme: "light" }}>
      <body className="flex min-h-full flex-col">
        <a href="#noi-dung" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-surface focus:px-3 focus:py-2">
          Bỏ qua tới nội dung
        </a>
        <header className="no-print sticky top-0 z-40 border-b border-line bg-surface/95 backdrop-blur">
          <div className="mx-auto flex max-w-7xl items-center gap-6 px-4 py-3">
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
