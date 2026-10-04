-- Chisme owner posts ("post your own chisme"): one table + one public Storage bucket for the photos and map images.
-- Only the server writes, with the service-role / secret key (which bypasses RLS). The public (anon / publishable key)
-- can read published posts only, and can't write anything. The browser never talks to Supabase: the server proxies.

create table if not exists public.owner_posts (
  id           uuid primary key default gen_random_uuid(),
  slug         text not null unique check (slug ~ '^[a-z0-9][a-z0-9-]{2,95}$'),
  status       text not null default 'published' check (status in ('published', 'draft')),
  category     text not null check (category in ('news', 'weather', 'events', 'sports', 'food', 'other')),
  headline     text not null check (char_length(headline) between 1 and 140),
  body         text not null default '' check (char_length(body) <= 6000),
  photos       jsonb not null default '[]'::jsonb check (jsonb_typeof(photos) = 'array' and jsonb_array_length(photos) <= 3),
  location     text check (location is null or char_length(location) <= 200),
  map_query    text check (map_query is null or char_length(map_query) <= 200),
  lat          double precision check (lat is null or lat between -90 and 90),
  lon          double precision check (lon is null or lon between -180 and 180),
  map_image    jsonb,
  source_url   text check (source_url is null or (source_url ~* '^https?://[^\s<>"'']+$' and char_length(source_url) <= 1800)),
  source_name  text check (source_name is null or char_length(source_name) <= 160),
  pinned_until timestamptz,
  push_sent_at timestamptz,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

create index if not exists owner_posts_feed on public.owner_posts (status, created_at desc);

create or replace function public.owner_posts_touch() returns trigger
language plpgsql set search_path = '' as $$
begin
  new.updated_at := now();
  return new;
end $$;

drop trigger if exists owner_posts_touch on public.owner_posts;
create trigger owner_posts_touch before update on public.owner_posts
  for each row execute function public.owner_posts_touch();

alter table public.owner_posts enable row level security;
alter table public.owner_posts force row level security;

drop policy if exists "public reads published posts" on public.owner_posts;
create policy "public reads published posts" on public.owner_posts
  for select to anon, authenticated using (status = 'published');
-- no insert / update / delete policies on purpose: with RLS on, anon and authenticated can't write at all
revoke insert, update, delete, truncate, references, trigger on public.owner_posts from anon, authenticated;

-- Photos (webp, metadata stripped, resized by the server) and the OpenStreetMap static map images.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('owner-posts', 'owner-posts', true, 2097152, array['image/webp'])
on conflict (id) do update set public = excluded.public, file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;
-- (no storage.objects policies for anon / authenticated: nobody but the server's secret key can upload, replace or
--  delete; a public bucket's files are readable by URL, and the file names carry a random part)
