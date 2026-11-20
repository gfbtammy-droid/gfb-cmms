-- GFB CMMS: allow the new "sendouts" record type (Send-out D/O and collection notes).
-- Adds 'sendouts' to the allowed record types in save_doc (saving) and import_docs (restore from backup).
-- Nothing else in either function changes. Safe to run more than once.
do $$
declare d text; n text;
begin
  foreach n in array array['public.save_doc(text,text,jsonb,text,text)','public.import_docs(jsonb)'] loop
    select pg_get_functiondef(n::regprocedure) into d;
    if position('''purchases'',''sendouts'',''config''' in d) > 0 then continue; end if;
    if position('''purchases'',''config'')' in d) = 0 then raise exception 'Record type list not found in %', n; end if;
    execute replace(d, '''purchases'',''config'')', '''purchases'',''sendouts'',''config'')');
  end loop;
end $$;
