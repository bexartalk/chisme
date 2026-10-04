-- Paid / sponsor posts (paid event spotlights, sponsor posts): a flag the app turns into a "Sponsored" label on the feed
-- card, the post page, the link-preview description and the notification (FTC disclosure). Independent of pinning.
-- News stays independent: a paid post can't be in the News category.
alter table public.owner_posts add column if not exists sponsored boolean not null default false;
alter table public.owner_posts drop constraint if exists owner_posts_sponsored_not_news;
alter table public.owner_posts add constraint owner_posts_sponsored_not_news check (not (sponsored and category = 'news'));
