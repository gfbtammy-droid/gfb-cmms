-- GFB CMMS: allow the "disposals" record type (asset damage & disposal reports).
-- 1. Adds 'disposals' to the allowed record types in save_doc and import_docs.
-- 2. Report numbers (DSP-YYMM-NNN) are unique, like WO / PR / D/O numbers.
-- Safe to run more than once.
do $$
declare d text; n text;
begin
  foreach n in array array['public.save_doc(text,text,jsonb,text,text)','public.import_docs(jsonb)'] loop
    select pg_get_functiondef(n::regprocedure) into d;
    if position('''sendouts'',''disposals'',''config''' in d) > 0 then continue; end if;
    if position('''sendouts'',''config'')' in d) = 0 then raise exception 'Record type list not found in %', n; end if;
    execute replace(d, '''sendouts'',''config'')', '''sendouts'',''disposals'',''config'')');
  end loop;
end $$;
drop index if exists public.docs_no_uq;
create unique index docs_no_uq on public.docs (coll,(data->>'no')) where coll in ('workorders','purchases','incidents','sendouts','disposals') and coalesce(data->>'no','')<>'';
