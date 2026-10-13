-- Chisme v49.21: the reserved @goonie handle and the 🌮 Golden Taco badge, plus an admin audit log.
-- Apply AFTER 20261012200000_social_admin_badges.sql. Not applied by this branch (write-only; never applied to prod from here).
--
-- 1) @goonie is reserved for the owner (the admin account tied to SOCIAL_OWNER_EMAIL). Its lookalikes (g00nie, goonie_,
--    go_onie, gooonie, goon1e, goonle ...) are refused for everyone. Same skeleton rule as social.py username_skeleton().
-- 2) golden_taco: a badge alongside gold / blue. Only the server (service role, after its admin check) can change it;
--    the trigger below refuses it from anyone else, even if a grant slips in later.
-- 3) social_admin_audit: who changed what, for whom, when. Server-only, append-only.

create or replace function public.social_username_skeleton(u text) returns text
language sql immutable set search_path = '' as $$
  select regexp_replace(translate(lower(coalesce(u, '')), '01l!34578_', 'oiiieastb'), '(.)\1+', '\1', 'g')
$$;

alter table public.social_profiles add column if not exists golden_taco boolean not null default false;
alter table public.social_profiles add column if not exists golden_taco_at timestamptz;

-- the owner's handle: only the admin row may be exactly 'goonie'; nobody (the admin included) may hold a lookalike
alter table public.social_profiles drop constraint if exists social_profiles_goonie_reserved;
alter table public.social_profiles add constraint social_profiles_goonie_reserved check (
  public.social_username_skeleton(username) <> 'gonie' or (username = 'goonie' and role = 'admin'));

create table if not exists public.social_admin_audit (
  id text primary key,
  actor_id uuid references public.social_profiles (id) on delete set null,
  actor text not null,
  target_id uuid references public.social_profiles (id) on delete set null,
  target_username text,
  action text not null check (action in ('golden_taco_grant', 'golden_taco_revoke')),
  created_at timestamptz not null default now()
);
create index if not exists social_admin_audit_at on public.social_admin_audit (created_at desc);
alter table public.social_admin_audit enable row level security;
alter table public.social_admin_audit force row level security;
revoke all on table public.social_admin_audit from anon, authenticated, public;   -- no policies: only the service role reads or writes

create or replace function public.social_audit_append_only() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  raise exception 'the admin audit log is append-only';
end $$;
drop trigger if exists social_audit_append_only on public.social_admin_audit;
create trigger social_audit_append_only before update or delete on public.social_admin_audit
  for each row execute function public.social_audit_append_only();
revoke all on function public.social_audit_append_only() from public, anon, authenticated;

-- extend the server-only trigger from 20261012200000 to cover the Golden Taco
create or replace function public.social_badges_admin_only() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  if coalesce(current_setting('request.jwt.claim.role', true), '') <> 'service_role'
     and current_user not in ('postgres', 'service_role', 'supabase_admin')
     and (new.badge is distinct from old.badge or new.role is distinct from old.role or new.review is distinct from old.review
          or new.badge_at is distinct from old.badge_at
          or new.golden_taco is distinct from old.golden_taco or new.golden_taco_at is distinct from old.golden_taco_at) then
    raise exception 'only the Chisme admin (through the server) can change badges, roles or reviews';
  end if;
  return new;
end $$;

alter table public.social_profiles force row level security;
