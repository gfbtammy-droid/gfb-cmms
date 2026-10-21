-- GFB CMMS: switch on Purchasing (purchase request -> approval -> purchase order -> goods received)
-- Safe to run more than once. Run in Supabase -> SQL Editor.

-- 1. Who may approve purchase requests
alter table public.profiles add column if not exists can_approve boolean not null default false;

create or replace function public.me_can_approve() returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce((select active and can_approve from profiles where id = auth.uid()), false) $$;

-- admin_update_user gains an optional "can approve purchases" flag
drop function if exists public.admin_update_user(uuid, text, text, boolean, boolean);
create or replace function public.admin_update_user(p_id uuid, p_name text, p_role text, p_active boolean, p_incidents boolean, p_approve boolean default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare t profiles; admins int;
begin
  if not public.me_is_admin() then raise exception 'Only an admin can manage users.' using errcode = '42501'; end if;
  select * into t from profiles where id = p_id;
  if t.id is null then raise exception 'User not found.'; end if;
  if p_role not in ('admin','editor','viewer') then raise exception 'Choose a role.'; end if;
  if t.role = 'admin' and t.active and (p_role <> 'admin' or not p_active) then
    select count(*) into admins from profiles where role = 'admin' and active;
    if admins <= 1 then raise exception 'Keep at least one active admin.'; end if;
  end if;
  update profiles set name = coalesce(nullif(trim(p_name), ''), name), role = p_role, active = p_active,
    incident_access = coalesce(p_incidents, false),
    can_approve = coalesce(p_approve, can_approve) where id = p_id;
  return jsonb_build_object('ok', true);
end $$;
grant execute on function public.admin_update_user(uuid, text, text, boolean, boolean, boolean) to authenticated;
grant execute on function public.me_can_approve() to authenticated;

-- 2. Total of a purchase (sum of qty x unit price)
create or replace function public._pur_total(d jsonb) returns numeric
language sql immutable as $$
  select coalesce(round(sum(coalesce(nullif(l->>'qty','')::numeric,0) * coalesce(nullif(l->>'price','')::numeric,0)), 2), 0)
  from jsonb_array_elements(coalesce(d->'lines','[]'::jsonb)) l $$;

-- 3. save_doc: allow 'purchases' and enforce the approval rules on the server
create or replace function public.save_doc(p_coll text, p_id text, p_data jsonb, p_act text, p_base text)
returns jsonb language plpgsql security definer set search_path = public as $$
declare prev jsonb; body jsonb; h jsonb; nowt text := public._iso(now()); who text;
        st text; ap jsonb; pap jsonb;
begin
  if not public.me_active() then raise exception 'Your account is not active yet.' using errcode = '42501'; end if;
  if p_coll not in ('assets','workorders','parts','suppliers','incidents','contracts','purchases','config') then
    raise exception 'Unknown record type.' using errcode = '22023'; end if;
  if not public.me_can_write() then raise exception 'Your account is view-only.' using errcode = '42501'; end if;
  if p_coll = 'incidents' and not public.me_incidents() then
    raise exception 'You do not have access to incident records.' using errcode = '42501'; end if;
  if p_id !~ '^[A-Za-z0-9_\-]{1,80}$' then raise exception 'Invalid record id.' using errcode = '22023'; end if;
  if length(p_data::text) > 900000 then raise exception 'This record is too large.' using errcode = '22023'; end if;

  select data into prev from docs where coll = p_coll and id = p_id for update;
  if prev is not null and p_base is distinct from (prev->>'updatedAt') then
    return jsonb_build_object('conflict', true, 'current', prev);
  end if;
  if prev is null and p_base is not null then
    return jsonb_build_object('conflict', true, 'current', null);
  end if;

  who := public.me_name();

  if p_coll = 'purchases' then
    st  := coalesce(p_data->>'status', '');
    ap  := p_data->'approval';
    pap := prev->'approval';
    if ap = 'null'::jsonb then ap := null; end if;
    if pap = 'null'::jsonb then pap := null; end if;
    -- only an approver can record (or change) an approval decision
    if ap is not null and ap is distinct from pap then
      if not public.me_can_approve() then
        raise exception 'Only a named approver can approve or reject a purchase request.' using errcode = '42501'; end if;
      -- stamp the decision with the real approver and time
      ap := ap || jsonb_build_object('by', auth.uid(), 'name', who, 'at', nowt,
                                     'total', public._pur_total(p_data));
      p_data := jsonb_set(p_data, '{approval}', ap);
    end if;
    -- statuses after approval need an approved decision covering the current amount
    if st in ('Approved','PO issued','Partly received','Received') then
      if ap is null or ap->>'decision' <> 'Approved' then
        raise exception 'This purchase request has not been approved yet.' using errcode = '42501'; end if;
      if public._pur_total(p_data) > coalesce(nullif(ap->>'total','')::numeric, 0) + 0.005
         and not public.me_can_approve() then
        raise exception 'The amount is higher than what was approved (RM %). Send it back for approval.', ap->>'total' using errcode = '42501'; end if;
    end if;
    if st = 'Rejected' and (ap is null or ap->>'decision' <> 'Rejected') then
      raise exception 'Only a named approver can reject a purchase request.' using errcode = '42501'; end if;
  end if;

  h := coalesce(prev->'history', '[]'::jsonb) || jsonb_build_array(jsonb_build_object(
         'at', nowt, 'by', auth.uid(), 'name', who, 'act', left(coalesce(p_act, 'Saved'), 600)));
  if jsonb_array_length(h) > 60 then
    select jsonb_agg(e order by i) into h from jsonb_array_elements(h) with ordinality t(e, i)
     where i > jsonb_array_length(h) - 60;
  end if;
  body := (p_data - 'history') || jsonb_build_object(
            'history', h, 'updatedAt', nowt, 'updatedBy', who,
            'createdAt', coalesce(prev->>'createdAt', nowt), 'createdBy', coalesce(prev->>'createdBy', who));

  insert into docs (coll, id, data, updated_at, updated_by, seq)
  values (p_coll, p_id, body, now(), auth.uid(), nextval('docs_seq'))
  on conflict (coll, id) do update set data = excluded.data, updated_at = excluded.updated_at,
    updated_by = excluded.updated_by, seq = excluded.seq;
  delete from tombstones where coll = p_coll and id = p_id;
  return jsonb_build_object('doc', body);
end $$;

-- 4. Goods received against a PO: updates stock and the PO in one step
create or replace function public.po_receive(p_id text, p_date text, p_do text, p_note text, p_lines jsonb, p_base text)
returns jsonb language plpgsql security definer set search_path = public as $$
declare po jsonb; l jsonb; rl jsonb; q numeric; r jsonb; rec jsonb; recs jsonb; recv jsonb := '[]'::jsonb;
        ord numeric; got numeric; allin boolean := true; anyin boolean := false; st text; ref text; d text;
begin
  if not public.me_can_write() then raise exception 'Your account is view-only.' using errcode = '42501'; end if;
  select data into po from docs where coll = 'purchases' and id = p_id for update;
  if po is null then return jsonb_build_object('error', 'Purchase order not found.'); end if;
  if p_base is distinct from (po->>'updatedAt') then return jsonb_build_object('conflict', true); end if;
  if coalesce(po->>'status','') not in ('PO issued','Partly received') then
    return jsonb_build_object('error', 'Goods can only be received against an issued purchase order.'); end if;
  d := coalesce(nullif(p_date, ''), to_char(now() at time zone 'Asia/Kuala_Lumpur', 'YYYY-MM-DD'));
  ref := coalesce(po->>'poNo', '') || case when coalesce(p_do, '') <> '' then ' / DO ' || p_do else '' end;
  for rl in select * from jsonb_array_elements(coalesce(p_lines, '[]'::jsonb)) loop
    q := coalesce(nullif(rl->>'qty', '')::numeric, 0);
    continue when q <= 0;
    select e into l from jsonb_array_elements(po->'lines') e where e->>'lid' = rl->>'lid';
    if l is null then raise exception 'Unknown PO line.'; end if;
    if coalesce(l->>'partId', '') <> '' then
      r := public.stock_move(l->>'partId', 'Receive', q, null, d, ref, 'Goods received for ' || coalesce(po->>'poNo',''),
                             nullif(l->>'price', '')::numeric);
      if r ? 'error' then raise exception '%', r->>'error'; end if;
      if r ? 'conflict' then raise exception 'Stock changed at the same moment. Try again.'; end if;
    end if;
    recv := recv || jsonb_build_array(jsonb_build_object('lid', l->>'lid', 'qty', q));
    anyin := true;
  end loop;
  if not anyin then return jsonb_build_object('error', 'Enter the quantity received for at least one item.'); end if;
  rec := jsonb_build_object('date', d, 'doNo', coalesce(p_do, ''), 'note', coalesce(p_note, ''), 'lines', recv,
                            'by', auth.uid(), 'name', public.me_name(), 'at', public._iso(now()));
  recs := coalesce(po->'receipts', '[]'::jsonb) || jsonb_build_array(rec);
  -- fully received?
  for l in select * from jsonb_array_elements(po->'lines') loop
    ord := coalesce(nullif(l->>'qty', '')::numeric, 0);
    select coalesce(sum(coalesce(nullif(x->>'qty','')::numeric,0)), 0) into got
      from jsonb_array_elements(recs) rr, jsonb_array_elements(rr->'lines') x where x->>'lid' = l->>'lid';
    if got < ord then allin := false; end if;
  end loop;
  st := case when allin then 'Received' else 'Partly received' end;
  select data into po from docs where coll = 'purchases' and id = p_id;  -- unchanged by stock_move
  return public.save_doc('purchases', p_id, po || jsonb_build_object('receipts', recs, 'status', st),
           'Goods received' || case when coalesce(p_do,'') <> '' then ' (DO ' || p_do || ')' else '' end || ' → ' || st,
           po->>'updatedAt');
end $$;
grant execute on function public.po_receive(text, text, text, text, jsonb, text) to authenticated;

-- 5. Backups / import accept purchases too
create or replace function public.import_docs(p_docs jsonb)
returns jsonb language plpgsql security definer set search_path = public as $$
declare d jsonb; n int := 0; nowt text := public._iso(now()); who text;
begin
  if not public.me_is_admin() then raise exception 'Only an admin can import data.' using errcode = '42501'; end if;
  who := public.me_name();
  for d in select * from jsonb_array_elements(p_docs) loop
    continue when (d->>'coll') not in ('assets','workorders','parts','suppliers','incidents','contracts','purchases','config');
    insert into docs (coll, id, data, updated_at, updated_by, seq)
    values (d->>'coll', d->>'id',
            (d->'data') || jsonb_build_object('updatedAt', nowt,
              'history', coalesce(d->'data'->'history', '[]'::jsonb) || jsonb_build_array(jsonb_build_object('at', nowt, 'by', auth.uid(), 'name', who, 'act', 'Imported into GFB Asset & Maintenance (Supabase)'))),
            now(), auth.uid(), nextval('docs_seq'))
    on conflict (coll, id) do update set data = excluded.data, updated_at = excluded.updated_at, updated_by = excluded.updated_by, seq = excluded.seq;
    n := n + 1;
  end loop;
  return jsonb_build_object('imported', n);
end $$;
