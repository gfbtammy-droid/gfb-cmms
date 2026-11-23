-- GFB CMMS: database hardening from the code review of 23/11/2026 (APPLIED to the live database 23/11/2026).
-- 1. Keep up to 1,000 change-history lines per record (was 60) and 1,500 stock movements per part (was 300).
-- 2. Email notifications can never block a save: any error inside the notification trigger is logged as a warning.
-- 3. Running numbers (WO, PR, PO, incident, D/O) are unique at database level, so two people saving at the
--    same moment cannot get the same number; the second save is refused and simply retried.
-- 4. Security housekeeping: signed-out visitors cannot call any CMMS function; fixed search_path on 4 helpers.
-- Safe to run more than once. Nothing else in the functions changes.

do $$
declare d text;
begin
  -- 1a. history cap in save_doc
  select pg_get_functiondef('public.save_doc(text,text,jsonb,text,text)'::regprocedure) into d;
  if position('jsonb_array_length(h) > 1000' in d) = 0 then
    if position('jsonb_array_length(h) > 60' in d) = 0 or position('jsonb_array_length(h) - 60' in d) = 0 then
      raise exception 'save_doc history limit text not found'; end if;
    d := replace(replace(d, 'jsonb_array_length(h) > 60', 'jsonb_array_length(h) > 1000'), 'jsonb_array_length(h) - 60', 'jsonb_array_length(h) - 1000');
    execute d;
  end if;
  -- 1b. stock movement cap in stock_move
  select pg_get_functiondef('public.stock_move(text,text,numeric,numeric,text,text,text,numeric)'::regprocedure) into d;
  if position('jsonb_array_length(moves) > 1500' in d) = 0 then
    if position('jsonb_array_length(moves) > 300' in d) = 0 or position('jsonb_array_length(moves) - 300' in d) = 0 then
      raise exception 'stock_move limit text not found'; end if;
    d := replace(replace(d, 'jsonb_array_length(moves) > 300', 'jsonb_array_length(moves) > 1500'), 'jsonb_array_length(moves) - 300', 'jsonb_array_length(moves) - 1500');
    execute d;
  end if;
  -- 2. notification trigger: wrap the body so it can never abort the save
  select pg_get_functiondef('public.notify_doc_change()'::regprocedure) into d;
  if position('notification skipped' in d) = 0 then
    if position(E'begin\n  if new.coll = ''purchases'' then' in d) = 0
       or position(E'  if sent then perform public.notify_kick(); end if;\n  return new;\nend' in d) = 0 then
      raise exception 'notify_doc_change body text not found'; end if;
    d := replace(d, E'begin\n  if new.coll = ''purchases'' then', E'begin\n begin\n  if new.coll = ''purchases'' then');
    d := replace(d, E'  if sent then perform public.notify_kick(); end if;\n  return new;\nend',
                    E'  if sent then perform public.notify_kick(); end if;\n exception when others then\n  raise warning ''CMMS notification skipped for %/%: %'', new.coll, new.id, sqlerrm;\n end;\n  return new;\nend');
    execute d;
  end if;
end $$;

-- 3. unique running numbers (drafts without a number are not affected)
create unique index if not exists docs_no_uq on public.docs (coll, (data->>'no'))
  where coll in ('workorders','purchases','incidents','sendouts') and coalesce(data->>'no','') <> '';
create unique index if not exists docs_pono_uq on public.docs ((data->>'poNo'))
  where coll = 'purchases' and coalesce(data->>'poNo','') <> '';

-- 4. security housekeeping
do $$
declare f record;
begin
  for f in select p.oid::regprocedure as sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.prokind = 'f' and p.proowner = (select oid from pg_roles where rolname = current_user) loop
    execute format('revoke execute on function %s from anon, public', f.sig);
    execute format('grant execute on function %s to authenticated, service_role', f.sig);
  end loop;
end $$;
-- 4b. keep the internal email functions closed to signed-in users (database and email sender only), as in enable-email-notifications.sql
revoke execute on function public.notify_claim(int), public.notify_done(bigint,boolean,text), public.notify_status(text),
  public.notify_kick(), public.notify_enqueue(uuid,text,text,text,text,text), public.notify_daily(),
  public.notify_doc_change(), public.notify_doc_delete(), public.notify_creator(jsonb), public.notify_get_key(),
  public.sync_display_name() from public, anon, authenticated;
grant execute on function public.notify_claim(int), public.notify_done(bigint,boolean,text), public.notify_status(text), public.notify_get_key() to service_role;
alter function public._iso(timestamptz) set search_path = public;
alter function public._pur_total(jsonb) set search_path = public;
alter function public.notify_esc(text) set search_path = public;
alter function public.notify_wdays(timestamptz) set search_path = public;

-- 5. (applied 23/11/2026, separate migration) PO other charges / tax count towards the approved amount.
create or replace function public._pur_total(d jsonb) returns numeric language sql immutable set search_path to 'public' as $function$
  select round(
    coalesce((select sum(coalesce(nullif(l->>'qty','')::numeric,0) * coalesce(nullif(l->>'price','')::numeric,0))
              from jsonb_array_elements(coalesce(d->'lines','[]'::jsonb)) l), 0)
    + case when (d->'po'->>'other') ~ '^-?[0-9]+(\.[0-9]+)?$' then (d->'po'->>'other')::numeric else 0 end, 2)
$function$;
revoke execute on function public._pur_total(jsonb) from anon, public;
grant execute on function public._pur_total(jsonb) to authenticated, service_role;
