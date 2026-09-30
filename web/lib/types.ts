// Shape of output/site/data.json written by .claude/skills/mention-monitor/scripts/export_site.py
export const SCHEMA_VERSION = 1;

export type Image = {
  file: string;
  sha256: string | null;
  captured_at: string | null;
  kind: "post" | "attach" | "cscroll" | "comment" | string;
  shows: string | null;
  capture_tool: string | null;
  thumb: string | null;
};

export type Attachment = {
  kind?: string;
  description?: string | null;
  transcribed_text?: string | null;
  url?: string | null;
};

export type Metrics = { reactions?: number | null; comments?: number | null; shares?: number | null;
  views?: number | null; counted_at?: string | null; reply_count?: number | null };

export type Source = {
  id: string; platform: string; content_type: string; url: string; url_kind: string;
  container_id: string | null; container_name: string | null;
  author_name: string; author_url: string | null; author_kind: string; author_badge: string | null;
  posted_at_raw: string; posted_at: string | null; posted_at_precision: string;
  text: string; current_text: string | null; attachments: Attachment[] | null;
  shared_from: { url?: string; author_name?: string; author_url?: string; text_excerpt?: string } | null;
  keywords_matched: string[]; entities_mentioned: string[] | null; topics: string[] | null;
  tone: string | null; claim_type: string | null; importance: string; importance_reason: string | null;
  status: string; last_checked_at: string | null; captured_at: string; run_id: string; origin: string;
  supersedes: string | null; notes: string | null; snapshot_file: string | null; snapshot_sha256: string | null;
  comments_collected: number; metrics: Metrics; metrics_history: (Metrics & { record_id: string; at: string })[];
  month: string; main_image: Image | null;
  captures: { record_id: string; at: string | null; images: (Image | null)[] }[];
  search: string;
};

export type Comment = {
  id: string; source_id: string; parent_comment_id: string | null; depth: number; url: string | null;
  fb_comment_id: string | null; author_name: string; author_url: string | null; author_kind: string;
  author_badge: string | null; posted_at_raw: string; posted_at: string | null; posted_at_precision: string;
  text: string; attachments: Attachment[] | null; keywords_matched: string[] | null;
  entities_mentioned: string[] | null; topics: string[] | null; tone: string | null; claim_type: string | null;
  importance: string; importance_reason: string | null; status: string; last_checked_at: string | null;
  captured_at: string; run_id: string; notes: string | null;
  scroll_refs: { file: string; position: number }[] | null;
  order: number; reactions: number | null; reply_count: number | null; month: string;
  own_image: Image | null; search: string;
};

export type Container = {
  id: string; platform: string; kind: string; name: string; url: string; privacy: string; joined: string;
  scan_mode: string; topic_dedicated: boolean; member_count: number | null; member_count_at: string | null;
  last_scanned_at: string | null; notes: string | null; status: string; needs_join: boolean; source_count: number;
};

export type Event = { id: string; date_raw: string; date: string | null; sort_key: string | null;
  description: string; source_text: string | null; related_ids: string[] | null; reliability: string;
  origin: string };

export type SearchLog = { id: string; run_id: string; platform: string; scope: string; container_id: string | null;
  section: string; query: string; filters: Record<string, unknown> | null; started_at: string;
  ended_at: string | null; results_seen: number; results_new: number; results_duplicate: number | null;
  results_excluded: number | null; reached_end: boolean; issues: string | string[] | null; notes: string | null };

export type Change = { id: string; target_id: string; checked_at: string; status: string; new_text: string | null;
  metrics: Metrics | null; updates: Record<string, unknown> | null; notes: string | null; target_type: string;
  metrics_grew: boolean; images: (Image | null)[] };

export type Exclusion = { id: string; recorded_at: string; url: string; excerpt: string;
  keywords_matched: string[]; reason: string };

export type Person = { key: string; name: string; url: string | null; kind: string; posts: number;
  comments: number; ids: string[]; platforms: string[]; first: string | null; last: string | null };

export type Party = { id: string; name: string; label: string | null; kind: string | null; role: string | null;
  primary: boolean; press_sources: string | null; keyword_group: string | null; mentions: number;
  first: string | null; last: string | null };

export type EvidenceItem = { id: string; type: "source" | "comment"; source_id: string | null; image: Image | null;
  summary: string; author_name: string; url: string | null; posted_at_raw: string; posted_at: string | null;
  posted_at_precision: string; reason: string | null; captured_at: string; container_name: string | null };

export type Stats = {
  totals: { sources: number; comments: number; containers: number; need_join: number; exclusions: number;
    high: number; events: number };
  by_platform: Record<string, number>; by_tone: Record<string, number>; by_importance: Record<string, number>;
  by_month: { month: string; count: number }[]; by_party: Record<string, number>;
  latest_run: string | null; runs: string[]; new_in_latest_run: { sources: number; comments: number };
  gaps: { id: string; section: string | null; query: string | null; issue: string }[];
};

export type SiteData = {
  schema_version: number; generated_at: string; project_name: string; disclaimer: string | null;
  labels: Record<string, Record<string, string>>; descriptions: Record<string, Record<string, string>>;
  keyword_groups: { id: string; label: string }[]; parties: Party[];
  sources: Source[]; comments: Comment[]; containers: Container[]; events: Event[]; search_logs: SearchLog[];
  changes: Change[]; exclusions: Exclusion[]; people: Person[]; stats: Stats; evidence: EvidenceItem[];
  warnings: string[];
};
