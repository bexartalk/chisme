-- Chisme social, part 1: accounts (Supabase Auth keeps the passwords), Homies (mutual only), Chismes, reactions,
-- comments, saves, reports, blocks, notifications, uploads.
--
-- How access works: phones never talk to Supabase. Chisme's server (social.py) reads and writes with the project's
-- secret / service-role key, which bypasses RLS, and applies every audience, block and privacy rule itself.
-- RLS is still ON (and forced) on every table as a second wall: the public (anon / publishable key) can read nothing,
-- nobody but the server can write anything, and a signed-in Supabase user (auth.uid()) can only ever read their own
-- rows (plus Chismes they're allowed to see). Email addresses are never stored here (Supabase Auth has them); only a
-- salted hash of the normalized address for duplicate-account checks, and a masked hint ("g•••@gmail.com").

create table if not exists public.social_profiles (
  id            uuid primary key references auth.users (id) on delete cascade,
  username      text not null unique check (username ~ '^[a-z0-9_]{3,20}$'),
  display_name  text not null check (char_length(display_name) between 1 and 40),
  bio           text not null default '' check (char_length(bio) <= 160),
  area          text check (area is null or char_length(area) <= 40),
  photo         text check (photo is null or photo ~ '^a/[0-9]{6}/[A-Za-z0-9_-]{12}\.webp$'),
  privacy       jsonb not null default '{}'::jsonb check (jsonb_typeof(privacy) = 'object'),
  status        text not null default 'active' check (status in ('active', 'banned')),
  verified      boolean not null default false,
  flagged       boolean not null default false,
  report_count  integer not null default 0,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create table if not exists public.social_private (   -- never shown to anyone, never in an API answer
  user_id       uuid primary key references auth.users (id) on delete cascade,
  email_hash    text not null unique,                 -- HMAC of the normalized email (dots / +tags removed for Gmail)
  email_hint    text not null default '',             -- "g•••@gmail.com", for the owner's own Settings
  phone         text check (phone is null or phone ~ '^\+?[0-9]{7,15}$'),   -- optional, private, no SMS
  birthday      date not null,
  tos_at        timestamptz not null,
  privacy_at    timestamptz not null,
  signup_ip     text,                                  -- HMAC, not the address
  device        text,                                  -- HMAC of a random per-device id
  created_at    timestamptz not null default now()
);

create table if not exists public.social_sessions (   -- Chisme's own session ids (stored hashed); passwords stay in Supabase Auth
  id_hash       text primary key,
  user_id       uuid not null references auth.users (id) on delete cascade,
  created_at    timestamptz not null default now(),
  expires_at    timestamptz not null,
  ua            text check (ua is null or char_length(ua) <= 80)
);

create table if not exists public.social_homies (     -- one row per mutual pair, a < b
  a             uuid not null references auth.users (id) on delete cascade,
  b             uuid not null references auth.users (id) on delete cascade,
  created_at    timestamptz not null default now(),
  primary key (a, b),
  check (a < b)
);

create table if not exists public.social_homie_requests (   -- never changes state on NAH (NAH lives in social_nahs, private)
  id            uuid primary key,
  from_id       uuid not null references auth.users (id) on delete cascade,
  to_id         uuid not null references auth.users (id) on delete cascade,
  status        text not null default 'pending' check (status = 'pending'),
  created_at    timestamptz not null default now(),
  unique (from_id, to_id),
  check (from_id <> to_id)
);

create table if not exists public.social_nahs (       -- "✋ NAH": private to the person who said it
  user_id       uuid not null references auth.users (id) on delete cascade,
  target_id     uuid not null references auth.users (id) on delete cascade,
  created_at    timestamptz not null default now(),
  primary key (user_id, target_id)
);

create table if not exists public.social_blocks (
  blocker_id    uuid not null references auth.users (id) on delete cascade,
  blocked_id    uuid not null references auth.users (id) on delete cascade,
  created_at    timestamptz not null default now(),
  primary key (blocker_id, blocked_id),
  check (blocker_id <> blocked_id)
);

create table if not exists public.social_media (      -- every upload (resized WebP, metadata stripped)
  name          text primary key check (name ~ '^[ac]/[0-9]{6}/[A-Za-z0-9_-]{12}\.webp$'),
  owner_id      uuid not null references auth.users (id) on delete cascade,
  kind          text not null check (kind in ('chisme', 'avatar')),
  status        text not null check (status in ('pending', 'attached', 'quarantine', 'blocked')),
  w             integer, h integer, bytes integer,
  created_at    timestamptz not null default now()
);

create table if not exists public.social_chismes (
  id            uuid primary key,
  author_id     uuid not null references auth.users (id) on delete cascade,
  text          text not null default '' check (char_length(text) <= 2000),
  photos        jsonb not null default '[]'::jsonb check (jsonb_typeof(photos) = 'array' and jsonb_array_length(photos) <= 4),
  audience      text not null check (audience in ('everyone', 'homies', 'me')),
  hashtags      jsonb not null default '[]'::jsonb check (jsonb_typeof(hashtags) = 'array'),
  mentions      jsonb not null default '[]'::jsonb check (jsonb_typeof(mentions) = 'array'),
  tags          jsonb not null default '[]'::jsonb check (jsonb_typeof(tags) = 'array'),
  status        text not null default 'visible' check (status in ('visible', 'hidden', 'removed')),
  report_count  integer not null default 0,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  check (char_length(text) > 0 or jsonb_array_length(photos) > 0)
);

create table if not exists public.social_reactions (
  chisme_id     uuid not null references public.social_chismes (id) on delete cascade,
  user_id       uuid not null references auth.users (id) on delete cascade,
  kind          text not null check (kind in ('like', 'laugh', 'wow', 'chile')),
  created_at    timestamptz not null default now(),
  primary key (chisme_id, user_id, kind)
);

create table if not exists public.social_saves (
  user_id       uuid not null references auth.users (id) on delete cascade,
  chisme_id     uuid not null references public.social_chismes (id) on delete cascade,
  created_at    timestamptz not null default now(),
  primary key (user_id, chisme_id)
);

create table if not exists public.social_comments (
  id            uuid primary key,
  chisme_id     uuid not null references public.social_chismes (id) on delete cascade,
  author_id     uuid not null references auth.users (id) on delete cascade,
  text          text not null check (char_length(text) between 1 and 500),
  status        text not null default 'visible' check (status in ('visible', 'hidden', 'removed')),
  report_count  integer not null default 0,
  created_at    timestamptz not null default now()
);

create table if not exists public.social_reports (    -- kept (reporter set to null) if the reporter deletes their account
  id            uuid primary key,
  reporter_id   uuid references auth.users (id) on delete set null,
  target_kind   text not null check (target_kind in ('chisme', 'comment', 'user')),
  target_id     uuid not null,
  target_user   uuid,
  reason        text not null check (reason in ('spam', 'harassment', 'hate', 'nudity', 'violence', 'minor', 'scam', 'other')),
  details       text not null default '' check (char_length(details) <= 500),
  status        text not null default 'open' check (status in ('open', 'dismissed', 'actioned')),
  created_at    timestamptz not null default now(),
  unique (reporter_id, target_kind, target_id)
);

create table if not exists public.social_notifications (
  id            uuid primary key,
  user_id       uuid not null references auth.users (id) on delete cascade,
  actor_id      uuid not null references auth.users (id) on delete cascade,
  kind          text not null check (kind in ('homie_request', 'homie_yes', 'reaction', 'comment', 'mention', 'tag')),
  chisme_id     uuid references public.social_chismes (id) on delete cascade,
  read          boolean not null default false,
  created_at    timestamptz not null default now()
);

create table if not exists public.social_bans (       -- banned sign-ups: the email hash only
  email_hash    text primary key,
  reason        text not null default '',
  created_at    timestamptz not null default now()
);

create table if not exists public.social_csam_holds ( -- a scanner match: evidence kept (private bucket) for the legal report; no FK on purpose
  id            uuid primary key,
  media_name    text not null,
  owner_id      uuid,
  sha256        text not null,
  created_at    timestamptz not null default now(),
  reported_at   timestamptz
);

-- indexes (feeds, lookups, and every foreign key)
create index if not exists social_profiles_created on public.social_profiles (created_at desc);
create index if not exists social_sessions_user on public.social_sessions (user_id);
create index if not exists social_homies_b on public.social_homies (b);
create index if not exists social_homie_requests_to on public.social_homie_requests (to_id);
create index if not exists social_nahs_target on public.social_nahs (target_id);
create index if not exists social_blocks_blocked on public.social_blocks (blocked_id);
create index if not exists social_media_owner on public.social_media (owner_id);
create index if not exists social_chismes_author on public.social_chismes (author_id, created_at desc);
create index if not exists social_chismes_feed on public.social_chismes (status, audience, created_at desc);
create index if not exists social_reactions_user on public.social_reactions (user_id);
create index if not exists social_saves_chisme on public.social_saves (chisme_id);
create index if not exists social_comments_chisme on public.social_comments (chisme_id, created_at);
create index if not exists social_comments_author on public.social_comments (author_id);
create index if not exists social_reports_reporter on public.social_reports (reporter_id);
create index if not exists social_reports_open on public.social_reports (status, created_at desc);
create index if not exists social_notifications_user on public.social_notifications (user_id, created_at desc);
create index if not exists social_notifications_actor on public.social_notifications (actor_id);
create index if not exists social_notifications_chisme on public.social_notifications (chisme_id);

create or replace function public.social_touch() returns trigger
language plpgsql set search_path = '' as $$
begin
  new.updated_at := now();
  return new;
end $$;
revoke execute on function public.social_touch() from public, anon, authenticated;

drop trigger if exists social_profiles_touch on public.social_profiles;
create trigger social_profiles_touch before update on public.social_profiles for each row execute function public.social_touch();
drop trigger if exists social_chismes_touch on public.social_chismes;
create trigger social_chismes_touch before update on public.social_chismes for each row execute function public.social_touch();

-- RLS: on and forced everywhere; the clients can't write; the public can't read
do $$
declare t text;
begin
  foreach t in array array['social_profiles', 'social_private', 'social_sessions', 'social_homies', 'social_homie_requests',
                           'social_nahs', 'social_blocks', 'social_media', 'social_chismes', 'social_reactions', 'social_saves',
                           'social_comments', 'social_reports', 'social_notifications', 'social_bans', 'social_csam_holds'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('alter table public.%I force row level security', t);
    execute format('revoke all on table public.%I from anon', t);
    execute format('revoke insert, update, delete, truncate, references, trigger on table public.%I from authenticated', t);
  end loop;
end $$;

-- a signed-in Supabase user reads only their own rows
drop policy if exists "own profile" on public.social_profiles;
create policy "own profile" on public.social_profiles for select to authenticated using (id = (select auth.uid()));
drop policy if exists "own private row" on public.social_private;
create policy "own private row" on public.social_private for select to authenticated using (user_id = (select auth.uid()));
drop policy if exists "own sessions" on public.social_sessions;
create policy "own sessions" on public.social_sessions for select to authenticated using (user_id = (select auth.uid()));
drop policy if exists "own homie pairs" on public.social_homies;
create policy "own homie pairs" on public.social_homies for select to authenticated using ((select auth.uid()) in (a, b));
drop policy if exists "own homie requests" on public.social_homie_requests;
create policy "own homie requests" on public.social_homie_requests for select to authenticated
  using ((select auth.uid()) in (from_id, to_id));
drop policy if exists "own nahs" on public.social_nahs;
create policy "own nahs" on public.social_nahs for select to authenticated using (user_id = (select auth.uid()));
drop policy if exists "own blocks" on public.social_blocks;
create policy "own blocks" on public.social_blocks for select to authenticated using (blocker_id = (select auth.uid()));
drop policy if exists "own uploads" on public.social_media;
create policy "own uploads" on public.social_media for select to authenticated using (owner_id = (select auth.uid()));
drop policy if exists "chismes they may see" on public.social_chismes;
create policy "chismes they may see" on public.social_chismes for select to authenticated using (
  author_id = (select auth.uid())
  or (status = 'visible' and audience = 'everyone')
  or (status = 'visible' and audience = 'homies' and exists (
        select 1 from public.social_homies h
        where (h.a = (select auth.uid()) and h.b = social_chismes.author_id)
           or (h.b = (select auth.uid()) and h.a = social_chismes.author_id))));
drop policy if exists "own reactions" on public.social_reactions;
create policy "own reactions" on public.social_reactions for select to authenticated using (user_id = (select auth.uid()));
drop policy if exists "own saves" on public.social_saves;
create policy "own saves" on public.social_saves for select to authenticated using (user_id = (select auth.uid()));
drop policy if exists "own comments" on public.social_comments;
create policy "own comments" on public.social_comments for select to authenticated using (author_id = (select auth.uid()));
drop policy if exists "own reports" on public.social_reports;
create policy "own reports" on public.social_reports for select to authenticated using (reporter_id = (select auth.uid()));
drop policy if exists "own notifications" on public.social_notifications;
create policy "own notifications" on public.social_notifications for select to authenticated using (user_id = (select auth.uid()));
drop policy if exists "server only" on public.social_bans;
create policy "server only" on public.social_bans for select to authenticated using (false);
drop policy if exists "server only" on public.social_csam_holds;
create policy "server only" on public.social_csam_holds for select to authenticated using (false);

-- Storage: public photos (WebP, metadata stripped, resized by the server; random names) and a PRIVATE quarantine
-- bucket for uploads held for a CSAM scan / kept as evidence. Only the server's secret key can write either one.
-- (Cloudflare R2 replaces "chisme-media" once Goonie sets it up: SOCIAL_MEDIA_STORE=r2; see SOCIAL.md.)
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('chisme-media', 'chisme-media', true, 2097152, array['image/webp'])
on conflict (id) do update set public = excluded.public, file_size_limit = excluded.file_size_limit, allowed_mime_types = excluded.allowed_mime_types;
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('chisme-quarantine', 'chisme-quarantine', false, 2097152, array['image/webp'])
on conflict (id) do update set public = excluded.public, file_size_limit = excluded.file_size_limit, allowed_mime_types = excluded.allowed_mime_types;
