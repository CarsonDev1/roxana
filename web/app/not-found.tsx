import Link from "next/link";
import { Card } from "@/components/ui";

export default function NotFound() {
  return (
    <Card className="mx-auto max-w-lg text-center">
      <h1 className="text-lg font-semibold">Không tìm thấy</h1>
      <p className="mt-2 text-sm text-ink-2">Mã này không có trong dữ liệu đã xuất.</p>
      <Link href="/bai-viet" className="mt-4 inline-block text-sm text-accent-ink hover:underline">Về danh sách bài</Link>
    </Card>
  );
}
