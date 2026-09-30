-- Bản sao Supabase của kho theo dõi (kho gốc vẫn là data/records.jsonl trên máy).
-- Chạy một lần trong Supabase → SQL Editor. Chạy lại cũng không sao (idempotent).
-- Quyền: ai có link/khoá công khai (publishable) chỉ ĐỌC được; chỉ script đồng bộ (khoá secret, bỏ qua RLS) ghi được.

create table if not exists public.records (
  id           text primary key,          -- FB-P00001, WEB-P00012, CHK-000001…
  record_type  text not null,
  recorded_at  timestamptz,
  data         jsonb not null              -- nguyên bản ghi như trong records.jsonl
);
create index if not exists records_type_idx on public.records (record_type);

create table if not exists public.site_snapshots (
  id              bigint generated always as identity primary key,
  generated_at    timestamptz not null,
  schema_version  int not null,
  data            jsonb not null,          -- output/site/data.json (web đọc bản mới nhất)
  created_at      timestamptz not null default now()
);

alter table public.records enable row level security;
alter table public.site_snapshots enable row level security;

drop policy if exists "public read" on public.records;
create policy "public read" on public.records for select to anon, authenticated using (true);
drop policy if exists "public read" on public.site_snapshots;
create policy "public read" on public.site_snapshots for select to anon, authenticated using (true);
-- Không có policy insert/update/delete → trình duyệt không ghi/sửa/xoá được.

-- Ảnh bằng chứng + ảnh thu nhỏ: bucket công khai (đọc bằng link), cùng đường dẫn tương đối như trên máy.
insert into storage.buckets (id, name, public)
values ('evidence', 'evidence', true)
on conflict (id) do update set public = excluded.public;
