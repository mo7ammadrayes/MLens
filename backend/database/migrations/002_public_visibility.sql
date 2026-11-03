-- 002_public_visibility.sql
-- Run once in Supabase: SQL Editor -> New query -> paste -> Run. Safe to re-run.
-- Requires 001_supabase_auth.sql.

begin;

-- 1. Public/private flags. Everything is public unless the owner makes it
--    private. Models inherit their experiment's flag; predictions are
--    always private.
alter table public.datasets
    add column if not exists is_public boolean not null default true;

alter table public.experiments
    add column if not exists is_public boolean not null default true;

create index if not exists ix_datasets_public
    on public.datasets (dataset_id) where is_public;
create index if not exists ix_experiments_public
    on public.experiments (experiment_id) where is_public;

-- 2. Other users can run predictions with someone's public model. If the
--    owner later deletes that model, keep their saved prediction CSVs and
--    just clear the link (instead of blocking the delete).
alter table public.prediction_results
    alter column model_id drop not null;

do $$
declare
    fk_name text;
begin
    for fk_name in
        select conname
        from pg_constraint
        where conrelid = 'public.prediction_results'::regclass
          and contype = 'f'
          and pg_get_constraintdef(oid) like 'FOREIGN KEY (model_id)%'
    loop
        execute format(
            'alter table public.prediction_results drop constraint %I',
            fk_name
        );
    end loop;

    alter table public.prediction_results
        add constraint fk_prediction_results_model
        foreign key (model_id) references public.models (model_id)
        on delete set null;
end $$;

commit;

-- Existing rows become PUBLIC because of the default above. To make all
-- current data private instead, run:
--   update public.datasets set is_public = false;
--   update public.experiments set is_public = false;
