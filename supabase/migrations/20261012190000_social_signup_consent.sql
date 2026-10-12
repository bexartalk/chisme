-- Chisme social: sign-up age check + Terms / Privacy consent (Plato, legal). Apply AFTER 20261004150000_social_p1.sql.
-- Not applied by this branch.
--
-- Birthdates: Chisme no longer stores them. The server checks the birthdate at sign-up (18+, Chicago time) and keeps
-- only "adult = true" plus when it was checked. Less data held = less to leak; it's all the law and the Terms need.
-- Existing rows (if any) are kept as adults checked at their sign-up time, then the birthday column is dropped.

alter table public.social_private add column if not exists adult boolean;
alter table public.social_private add column if not exists age_checked_at timestamptz;
alter table public.social_private add column if not exists tos_version text;
alter table public.social_private add column if not exists privacy_version text;

update public.social_private set adult = true where adult is null;
update public.social_private set age_checked_at = coalesce(tos_at, created_at) where age_checked_at is null;
update public.social_private set tos_version = 'pre-2026-10-12' where tos_version is null;
update public.social_private set privacy_version = 'pre-2026-10-12' where privacy_version is null;

alter table public.social_private alter column adult set not null;
alter table public.social_private alter column age_checked_at set not null;
alter table public.social_private alter column tos_version set not null;
alter table public.social_private alter column privacy_version set not null;
alter table public.social_private drop constraint if exists social_private_adult_check;
alter table public.social_private add constraint social_private_adult_check check (adult = true);   -- under-18s never get a row
alter table public.social_private drop column if exists birthday;

-- What each person agreed to, and when (append-only from the server; gone with the account)
create table if not exists public.social_consents (
  id          text primary key,
  user_id     uuid not null references auth.users (id) on delete cascade,
  kind        text not null check (kind in ('terms', 'privacy', 'community_rules', 'age_18')),
  version     text not null check (char_length(version) between 1 and 40),
  agreed_at   timestamptz not null default now()
);
create index if not exists social_consents_user on public.social_consents (user_id, kind);

alter table public.social_consents enable row level security;
alter table public.social_consents force row level security;
revoke all on table public.social_consents from anon;
revoke insert, update, delete, truncate, references, trigger on table public.social_consents from authenticated;
drop policy if exists "own consents" on public.social_consents;
create policy "own consents" on public.social_consents for select to authenticated using (user_id = (select auth.uid()));
