import fs from "node:fs/promises";
import path from "node:path";
import { projectRoot } from "@/lib/data";
import { allowedFile, storageUrl } from "@/lib/files";

async function exists(p: string): Promise<boolean> {
  return fs.access(p).then(() => true, () => false);
}

const TYPES: Record<string, string> = {
  ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
  ".txt": "text/plain; charset=utf-8",
};

// Chỉ đọc. Trả file bằng chứng / ảnh thu nhỏ; mọi đường dẫn khác → 404 (không lộ config, kho gốc, file hệ thống).
export async function GET(request: Request) {
  const rel = new URL(request.url).searchParams.get("path") ?? "";
  const root = projectRoot();
  const abs = allowedFile(root, rel);
  const type = abs ? TYPES[path.extname(abs).toLowerCase()] : undefined;
  if (!abs || !type) return new Response("Not found", { status: 404 });
  const remote = storageUrl(rel);
  if (remote && (process.env.MM_DATA_SOURCE === "supabase" || !(await exists(abs)))) {
    return Response.redirect(remote, 302); // không có file trên máy (vd. trên Vercel) → ảnh trong Supabase Storage
  }
  try {
    // realpath chặn trường hợp symlink trỏ ra ngoài thư mục được phép
    const real = await fs.realpath(abs);
    const realRoot = await fs.realpath(root);
    if (!real.startsWith(realRoot + path.sep) || !allowedFile(realRoot, path.relative(realRoot, real))) {
      return new Response("Not found", { status: 404 });
    }
    const body = await fs.readFile(real);
    return new Response(body, {
      headers: { "Content-Type": type, "Cache-Control": "private, max-age=60", "X-Content-Type-Options": "nosniff" },
    });
  } catch {
    return new Response("Not found", { status: 404 });
  }
}
