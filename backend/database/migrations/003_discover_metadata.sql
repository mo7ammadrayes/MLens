-- 003_discover_metadata.sql
-- Run once in Supabase: SQL Editor -> New query -> paste -> Run. Safe to re-run.
-- Requires 002_public_visibility.sql.

begin;

-- Dataset details shown in Discover.
alter table public.datasets add column if not exists description text;
alter table public.datasets add column if not exists source text;
alter table public.datasets add column if not exists tags json;

-- Curated by MLens. Set by backend/scripts/seed_discover.py (or by hand);
-- the API never lets users change it.
alter table public.datasets
    add column if not exists is_featured boolean not null default false;

commit;

-- To feature or un-feature a dataset by hand:
--   update public.datasets set is_featured = true where dataset_id = <id>;
