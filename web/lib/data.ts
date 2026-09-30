import fs from "node:fs/promises";
import path from "node:path";
import { cookies } from "next/headers";
import { connection } from "next/server";
import { createClient, supabaseConfigured } from "@/utils/supabase/server";
import { keyedCache } from "./cache";
import type { SiteData } from "./types";

/** Thư mục dự án (chứa .claude, data/, screenshots/). Mặc định: thư mục cha của web/. */
export function projectRoot(): string {
  return path.resolve(process.env.MM_PROJECT_DIR ?? path.join(process.cwd(), ".."));
}

export function dataFile(): string {
  return path.join(projectRoot(), "output", "site", "data.json");
}

// Snapshot nặng vài MB: đọc + parse lại ở mỗi lần chuyển trang làm web chậm, nên giữ bản đã parse trong bộ nhớ.
const fileCache = keyedCache<SiteData>(60 * 60_000);
const SUPABASE_TTL_MS = 60_000;
const supabaseCache = keyedCache<SiteData | null>(SUPABASE_TTL_MS);

/**
 * Dữ liệu của trang.
 * - Trên máy: output/site/data.json, đọc lại ngay khi file đổi (quét xong chạy export_site.py rồi F5 là thấy).
 * - Không có file đó (vd. trên Vercel) hoặc MM_DATA_SOURCE=supabase: bản mới nhất trong bảng site_snapshots của Supabase
 *   (sync_supabase.py đẩy lên sau mỗi đợt quét); bản mới hiện ra chậm nhất sau SUPABASE_TTL_MS.
 */
export async function getData(): Promise<SiteData | null> {
  await connection();
  if (process.env.MM_DATA_SOURCE !== "supabase") {
    const file = dataFile();
    try {
      const st = await fs.stat(file);
      return await fileCache(`${st.mtimeMs}:${st.size}`,
        async () => JSON.parse(await fs.readFile(file, "utf-8")) as SiteData);
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code !== "ENOENT") throw err;
    }
  }
  if (!supabaseConfigured) return null;
  const cookieStore = await cookies();
  return supabaseCache("latest", () => latestSnapshot(cookieStore));
}

async function latestSnapshot(cookieStore: Awaited<ReturnType<typeof cookies>>): Promise<SiteData | null> {
  const supabase = createClient(cookieStore);
  const { data, error } = await supabase.from("site_snapshots").select("data")
    .order("id", { ascending: false }).limit(1).maybeSingle();
  if (error) throw new Error(`Supabase: ${error.message}`);
  return (data?.data as SiteData | undefined) ?? null;
}

export function label(data: SiteData, enumName: string, value: string | null | undefined): string {
  if (!value) return "";
  return data.labels[enumName]?.[value] ?? value;
}

export function partyLabel(data: SiteData, id: string): string {
  const p = data.parties.find((x) => x.id === id);
  return p ? p.label || p.name : id;
}

export function keywordLabel(data: SiteData, id: string): string {
  return data.keyword_groups.find((g) => g.id === id)?.label ?? id;
}
