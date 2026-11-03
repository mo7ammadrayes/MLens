-- 001_supabase_auth.sql
-- Run once in the Supabase dashboard: SQL Editor -> New query -> paste -> Run.
-- Safe to re-run.

begin;

-- 1. Link application users to Supabase Auth accounts.
alter table public.users
    add column if not exists auth_id uuid;

do $$
begin
    if not exists (
        select 1 from pg_constraint where conname = 'uq_users_auth_id'
    ) then
        alter table public.users
            add constraint uq_users_auth_id unique (auth_id);
    end if;

    if not exists (
        select 1 from pg_constraint where conname = 'fk_users_auth_id'
    ) then
        -- Deleting an auth account unlinks the row but keeps its data.
        alter table public.users
            add constraint fk_users_auth_id
            foreign key (auth_id) references auth.users (id)
            on delete set null;
    end if;
end $$;

-- 2. Lock the tables away from Supabase's public Data API.
-- The frontend now ships the publishable (anon) key. Without RLS, anyone
-- holding that key could read/write these tables through PostgREST.
-- Enabling RLS with no policies denies all Data API access; FastAPI
-- connects directly as the table owner (DATABASE_URL), which bypasses RLS.
alter table public.users                  enable row level security;
alter table public.datasets               enable row level security;
alter table public.experiments            enable row level security;
alter table public.models                 enable row level security;
alter table public.prediction_results     enable row level security;
alter table public.pending_file_deletions enable row level security;

commit;

-- Check the result:
-- select user_id, email, auth_id from public.users order by user_id;
-- select relname, relrowsecurity from pg_class
--   where relname in ('users','datasets','experiments','models',
--                     'prediction_results','pending_file_deletions');
