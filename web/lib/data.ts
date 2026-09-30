import fs from "node:fs/promises";
import path from "node:path";
import { cookies } from "next/headers";
import { connection } from "next/server";
import { createClient, supabaseConfigured } from "@/utils/supabase/server";
import type { SiteData } from "./types";

/** Thư mục dự án (chứa .claude, data/, screenshots/). Mặc định: thư mục cha của web/. */
export function projectRoot(): string {
  return path.resolve(process.env.MM_PROJECT_DIR ?? path.join(process.cwd(), ".."));
}

export function dataFile(): string {
  return path.join(projectRoot(), "output", "site", "data.json");
}

/**
 * Dữ liệu mỗi lần tải trang (không cache).
 * - Trên máy: output/site/data.json (quét xong chạy export_site.py rồi F5 là thấy).
 * - Không có file đó (vd. trên Vercel) hoặc MM_DATA_SOURCE=supabase: bản mới nhất trong bảng site_snapshots của Supabase
 *   (sync_supabase.py đẩy lên sau mỗi đợt quét).
 */
export async function getData(): Promise<SiteData | null> {
  await connection();
  if (process.env.MM_DATA_SOURCE !== "supabase") {
    try {
      return JSON.parse(await fs.readFile(dataFile(), "utf-8")) as SiteData;
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code !== "ENOENT") throw err;
    }
  }
  return supabaseConfigured ? latestSnapshot() : null;
}

async function latestSnapshot(): Promise<SiteData | null> {
  const supabase = createClient(await cookies());
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
