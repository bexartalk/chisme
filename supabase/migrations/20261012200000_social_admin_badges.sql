-- Chisme social: the admin account, gold / blue badges, and new-user review. Apply AFTER
-- 20261012190000_social_signup_consent.sql. Not applied by this branch.
--
-- Only the server (service role) writes these; signed-in users can't (no insert/update rights on any social table,
-- and the trigger below refuses badge / role / review changes from anyone but the service role, even if a grant
-- slips in later).

alter table public.social_profiles add column if not exists role text check (role is null or role = 'admin');
alter table public.social_profiles add column if not exists badge text check (badge is null or badge in ('gold', 'blue'));
alter table public.social_profiles add column if not exists badge_at timestamptz;
alter table public.social_profiles add column if not exists review text check (review is null or review in ('pending', 'approved'));
create unique index if not exists social_profiles_one_admin on public.social_profiles ((role)) where role = 'admin';
create index if not exists social_profiles_review on public.social_profiles (review, created_at) where review = 'pending';

-- a new metiche's first Chismes wait for the admin
alter table public.social_chismes drop constraint if exists social_chismes_status_check;
alter table public.social_chismes add constraint social_chismes_status_check check (status in ('visible', 'hidden', 'removed', 'held'));

-- the admin's alerts: new sign-ups, reports, held Chismes
alter table public.social_notifications drop constraint if exists social_notifications_kind_check;
alter table public.social_notifications add constraint social_notifications_kind_check
  check (kind in ('homie_request', 'homie_yes', 'reaction', 'comment', 'mention', 'tag', 'new_user', 'report', 'held'));

create or replace function public.social_badges_admin_only() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  if coalesce(current_setting('request.jwt.claim.role', true), '') <> 'service_role'
     and current_user not in ('postgres', 'service_role', 'supabase_admin')
     and (new.badge is distinct from old.badge or new.role is distinct from old.role or new.review is distinct from old.review
          or new.badge_at is distinct from old.badge_at) then
    raise exception 'only the Chisme admin (through the server) can change badges, roles or reviews';
  end if;
  return new;
end $$;
drop trigger if exists social_badges_admin_only on public.social_profiles;
create trigger social_badges_admin_only before update on public.social_profiles
  for each row execute function public.social_badges_admin_only();
revoke all on function public.social_badges_admin_only() from public, anon, authenticated;

-- RLS stays forced on both tables (from part 1); users still only read their own profile row directly.
alter table public.social_profiles force row level security;
alter table public.social_chismes force row level security;
