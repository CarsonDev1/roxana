import path from "node:path";

// Chỉ các thư mục bằng chứng / ảnh thu nhỏ được phục vụ — không bao giờ config, kho gốc hay file khác trên máy.
const ALLOWED_PREFIXES = [["screenshots"], ["snapshots"], ["output", "thumbs"]];

/** Absolute path for a project-relative evidence path, or null when it is outside the allowed folders. */
export function allowedFile(root: string, rel: string): string | null {
  if (!rel || rel.includes("\0")) return null;
  const unified = rel.replace(/\\/g, "/");
  if (unified.startsWith("/") || /^[a-zA-Z]:/.test(unified)) return null;
  const segments = unified.split("/").filter((s) => s !== "" && s !== ".");
  if (segments.some((s) => s === "..")) return null;
  const ok = ALLOWED_PREFIXES.some((prefix) => segments.length > prefix.length
    && prefix.every((p, i) => segments[i] === p));
  if (!ok) return null;
  const abs = path.resolve(root, ...segments);
  const rootAbs = path.resolve(root);
  return abs.startsWith(rootAbs + path.sep) ? abs : null;
}

export function fileUrl(rel: string | null | undefined): string | null {
  return rel ? `/api/file?path=${encodeURIComponent(rel)}` : null;
}
