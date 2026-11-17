-- GFB CMMS: email notifications. Already applied to the live database (17/11/2026); kept here so a fresh install matches.
-- Needs: pg_net, pg_cron, a vault secret named notify_key, and the notify-send Edge Function with
-- MS_TENANT_ID, MS_CLIENT_ID, MS_CLIENT_SECRET, MAIL_FROM secrets.
create extension if not exists pg_net;
create extension if not exists pg_cron;
alter table public.profiles add column if not exists can_verify boolean not null default false;
create table if not exists public.notify_settings (key text primary key, value text);
insert into public.notify_settings values ('enabled','true'), ('app_url','https://gfbtammy-droid.github.io/gfb-cmms/') on conflict (key) do nothing;
create table if not exists public.notify_outbox (id bigserial primary key, to_email text not null, to_name text, subject text not null, body text not null,
  kind text, coll text, doc_id text, created_at timestamptz not null default now(), sent_at timestamptz, attempts int not null default 0, last_error text);
create table if not exists public.notify_state (coll text not null, doc_id text not null, kind text not null, since timestamptz not null default now(),
  reminders int not null default 0, last_at timestamptz, primary key (coll, doc_id, kind));
alter table public.notify_settings enable row level security;
alter table public.notify_outbox enable row level security;
alter table public.notify_state enable row level security;
create policy "notify_outbox: admin read" on public.notify_outbox for select using (public.me_is_admin());
create policy "notify_settings: admin read" on public.notify_settings for select using (public.me_is_admin());
grant select on public.notify_outbox, public.notify_settings to authenticated;
-- (admin_update_user gains p_verify; list_people() returns active users' names for "Person in charge")
-- GFB CMMS: email notifications (purchase approvals, work order handover, daily reminders)
alter table public.notify_outbox add column if not exists claimed_at timestamptz;

create or replace function public.notify_esc(t text) returns text language sql immutable as $$
  select replace(replace(replace(replace(coalesce(t,''),'&','&amp;'),'<','&lt;'),'>','&gt;'),'"','&quot;') $$;

create or replace function public.notify_link(p_kind text, p_id text) returns text language sql stable security definer set search_path = public as $$
  select coalesce((select value from notify_settings where key='app_url'),'') || case when coalesce(p_kind,'') = '' then '' else '#' || p_kind || '-' || p_id end $$;

-- one simple, clean HTML email
create or replace function public.notify_html(p_title text, p_intro text, p_rows jsonb, p_link text, p_btn text)
returns text language plpgsql immutable as $$
declare r jsonb; tbl text := '';
begin
  for r in select * from jsonb_array_elements(coalesce(p_rows,'[]'::jsonb)) loop
    if coalesce(r->>1,'') <> '' then
      tbl := tbl || '<tr><td style="padding:6px 12px 6px 0;color:#6b7280;vertical-align:top;white-space:nowrap">' || notify_esc(r->>0)
                 || '</td><td style="padding:6px 0;color:#111827">' || replace(notify_esc(r->>1), E'\n', '<br>') || '</td></tr>';
    end if;
  end loop;
  return '<div style="font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#111827;max-width:600px">'
    || '<div style="background:#1f5f4a;color:#fff;padding:14px 18px;border-radius:8px 8px 0 0;font-weight:600">GFB Asset &amp; Maintenance</div>'
    || '<div style="border:1px solid #e5e7eb;border-top:0;padding:18px;border-radius:0 0 8px 8px">'
    || '<h2 style="margin:0 0 8px;font-size:18px">' || notify_esc(p_title) || '</h2>'
    || '<p style="margin:0 0 14px;color:#374151">' || p_intro || '</p>'
    || case when tbl <> '' then '<table style="border-collapse:collapse;margin-bottom:16px">' || tbl || '</table>' else '' end
    || case when coalesce(p_link,'') <> '' then '<a href="' || notify_esc(p_link) || '" style="display:inline-block;background:#1f5f4a;color:#fff;text-decoration:none;padding:10px 18px;border-radius:6px;font-weight:600">' || notify_esc(p_btn) || '</a>' else '' end
    || '<p style="margin:18px 0 0;font-size:12px;color:#9ca3af">Automatic message from the GFB CMMS. Please do not reply to this email.</p>'
    || '</div></div>';
end $$;

-- start the sender straight away (also runs every 10 minutes as a retry)
create or replace function public.notify_kick() returns void language plpgsql security definer set search_path = public as $$
declare k text;
begin
  select decrypted_secret into k from vault.decrypted_secrets where name = 'notify_key';
  if k is null then return; end if;
  perform net.http_post(url := 'https://teolxizoketsqbkpukgh.supabase.co/functions/v1/notify-send',
                        headers := jsonb_build_object('Content-Type','application/json','x-notify-key',k),
                        body := '{}'::jsonb);
exception when others then null;
end $$;

create or replace function public.notify_enqueue(p_to uuid, p_subject text, p_body text, p_kind text, p_coll text, p_id text)
returns void language plpgsql security definer set search_path = public as $$
declare pr profiles;
begin
  if coalesce((select value from notify_settings where key='enabled'),'true') <> 'true' then return; end if;
  select * into pr from profiles where id = p_to and active;
  if pr.id is null or coalesce(pr.email,'') = '' then return; end if;
  insert into notify_outbox(to_email, to_name, subject, body, kind, coll, doc_id)
  values (pr.email, coalesce(nullif(pr.name,''), pr.email), p_subject, p_body, p_kind, p_coll, p_id);
end $$;

create or replace function public.notify_creator(d jsonb) returns uuid language sql stable security definer set search_path = public as $$
  select coalesce(
    (select (d->'history'->0->>'by')::uuid where (d->'history'->0->>'by') ~ '^[0-9a-f-]{36}$'),
    (select id from profiles where active and (name = d->>'createdBy' or split_part(email,'@',1) = d->>'createdBy') limit 1)) $$;

create or replace function public.notify_doc_change() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  d jsonb := new.data; o jsonb := case when tg_op = 'UPDATE' then old.data else '{}'::jsonb end;
  s text := coalesce(d->>'status',''); so text := coalesce(o->>'status','');
  actor uuid := auth.uid(); creator uuid := public.notify_creator(new.data);
  pic uuid; ref text; link text; u record; rows jsonb; sent boolean := false; tot numeric;
begin
  if new.coll = 'purchases' then
    ref := coalesce(nullif(d->>'no',''), 'Purchase request');
    link := public.notify_link('pur', new.id);
    tot := public._pur_total(d);
    rows := jsonb_build_array(
      jsonb_build_array('Requested by', coalesce(d->>'requestedBy', d->>'createdBy')),
      jsonb_build_array('Department', d->>'dept'), jsonb_build_array('Purpose', d->>'purpose'),
      jsonb_build_array('Amount', 'RM ' || to_char(coalesce(tot,0), 'FM999,999,990.00')),
      jsonb_build_array('Needed by', to_char(nullif(d->>'neededBy','')::date, 'DD/MM/YYYY')),
      jsonb_build_array('PO no.', d->>'poNo'),
      jsonb_build_array('Approver note', d->'approval'->>'note'));

    if s = 'Pending approval' and (s <> so or (d->>'submittedAt') is distinct from (o->>'submittedAt')) then
      for u in select id from profiles where active and can_approve and id is distinct from actor loop
        perform notify_enqueue(u.id, ref || ' waiting for your approval',
          notify_html(ref || ' needs your approval', 'A purchase request has been submitted for approval.', rows, link, 'Open and approve'),
          'pur_submitted', new.coll, new.id); sent := true;
      end loop;
      insert into notify_state(coll, doc_id, kind, since, reminders, last_at)
      values (new.coll, new.id, 'pur_approve', coalesce(nullif(d->>'submittedAt','')::timestamptz, now()), 0, null)
      on conflict (coll, doc_id, kind) do update set since = excluded.since, reminders = 0, last_at = null;
    elsif s <> 'Pending approval' then
      delete from notify_state where coll = new.coll and doc_id = new.id;
    end if;

    if s in ('Approved','Rejected','PO issued') and s <> so and creator is not null and creator is distinct from actor then
      perform notify_enqueue(creator,
        ref || case s when 'Approved' then ' approved' when 'Rejected' then ' rejected' else ' · ' || coalesce(d->>'poNo','PO') || ' issued' end,
        notify_html(ref || case s when 'Approved' then ' has been approved' when 'Rejected' then ' was rejected' else ': purchase order issued' end,
          case s when 'Approved' then 'Your purchase request was approved by ' || notify_esc(d->'approval'->>'name') || '.'
                 when 'Rejected' then 'Your purchase request was rejected by ' || notify_esc(d->'approval'->>'name') || '. Check the note, revise and resubmit if needed.'
                 else 'Purchase order ' || notify_esc(d->>'poNo') || ' has been issued for your request.' end,
          rows, link, 'Open the request'),
        'pur_' || lower(replace(s,' ','_')), new.coll, new.id); sent := true;
    end if;

  elsif new.coll = 'workorders' then
    if coalesce(d->>'draft','') = 'true' then return new; end if;
    ref := coalesce(nullif(d->>'no',''), 'Work order');
    link := public.notify_link('wo', new.id);
    pic := case when (d->>'picId') ~ '^[0-9a-f-]{36}$' then (d->>'picId')::uuid end;
    rows := jsonb_build_array(
      jsonb_build_array('Problem / reason', d->>'title'), jsonb_build_array('Job type', d->>'type'),
      jsonb_build_array('Priority', d->>'priority'), jsonb_build_array('Status', s),
      jsonb_build_array('Department', d->>'dept'), jsonb_build_array('Location', d->>'location'),
      jsonb_build_array('Reported by', d->>'reportedBy'), jsonb_build_array('Person in charge', d->>'picName'),
      jsonb_build_array('Technician', d->>'technician'), jsonb_build_array('Tasks completed', d->>'tasksDone'));

    if pic is not null and pic is distinct from actor and (d->>'picId') is distinct from (o->>'picId') and s not in ('Completed','Verified') then
      perform notify_enqueue(pic, ref || ' assigned to you: ' || coalesce(d->>'title',''),
        notify_html(ref || ' assigned to you', 'You are now the person in charge of this work order.', rows, link, 'Open the work order'),
        'wo_assigned', new.coll, new.id); sent := true;
    end if;

    if s = 'Completed' and s <> so then
      for u in select id from profiles where active and can_verify and id is distinct from actor loop
        perform notify_enqueue(u.id, ref || ' completed, please verify: ' || coalesce(d->>'title',''),
          notify_html(ref || ' is ready for verification', 'The work has been marked completed. Please check the job and do the QA / HOD verification.', rows, link, 'Open and verify'),
          'wo_completed', new.coll, new.id); sent := true;
      end loop;
    end if;

    if s = 'Verified' and s <> so then
      for u in select distinct x from unnest(array[creator, pic]) x where x is not null and x is distinct from actor loop
        perform notify_enqueue(u.x, ref || ' verified: ' || coalesce(d->>'title',''),
          notify_html(ref || ' has been verified', 'Verified by ' || notify_esc(d->>'verifiedBy') || '. This job is now closed.', rows, link, 'Open the work order'),
          'wo_verified', new.coll, new.id); sent := true;
      end loop;
    end if;

    if s in ('Open','In progress','Waiting parts') then
      insert into notify_state(coll, doc_id, kind, since) values (new.coll, new.id, 'wo_open',
        coalesce(nullif(d->>'reportDate','')::date::timestamptz, now()))
      on conflict (coll, doc_id, kind) do nothing;
    else
      delete from notify_state where coll = new.coll and doc_id = new.id and kind = 'wo_open';
    end if;
    if s = 'Completed' then
      insert into notify_state(coll, doc_id, kind, since) values (new.coll, new.id, 'wo_verify', now())
      on conflict (coll, doc_id, kind) do nothing;
    else
      delete from notify_state where coll = new.coll and doc_id = new.id and kind = 'wo_verify';
    end if;
  end if;

  if sent then perform public.notify_kick(); end if;
  return new;
end $$;

drop trigger if exists docs_notify_trg on public.docs;
create trigger docs_notify_trg after insert or update on public.docs
  for each row when (new.coll in ('purchases','workorders')) execute function public.notify_doc_change();

-- clean up state when a record is deleted
create or replace function public.notify_doc_delete() returns trigger language plpgsql security definer set search_path = public as $$
begin delete from notify_state where coll = old.coll and doc_id = old.id; return old; end $$;
drop trigger if exists docs_notify_del_trg on public.docs;
create trigger docs_notify_del_trg after delete on public.docs for each row execute function public.notify_doc_delete();

-- working days (Mon-Fri, Malaysia time) after the start date, up to today
create or replace function public.notify_wdays(p_from timestamptz) returns int language sql stable as $$
  select count(*)::int from generate_series((p_from at time zone 'Asia/Kuala_Lumpur')::date + 1,
                                            (now() at time zone 'Asia/Kuala_Lumpur')::date, interval '1 day') g
  where extract(isodow from g) < 6 $$;

-- daily summary at 8:00 am (Mon-Fri): one email per person
create or replace function public.notify_daily() returns int
language plpgsql security definer set search_path = public as $$
declare st record; d jsonb; thr int; who uuid[]; ref text; link text; what text; esc boolean; n int := 0;
        r record; html text; cnt int;
begin
  if coalesce((select value from notify_settings where key='enabled'),'true') <> 'true' then return 0; end if;
  create temp table if not exists _dig(uid uuid, ref text, link text, what text, since timestamptz, times int, escal boolean) on commit drop;
  truncate _dig;
  for st in select s.*, x.data from notify_state s join docs x on x.coll = s.coll and x.id = s.doc_id loop
    d := st.data; who := null; esc := false;
    if st.kind = 'pur_approve' then
      if coalesce(d->>'status','') <> 'Pending approval' then continue; end if;
      thr := 2; ref := coalesce(d->>'no','Purchase request'); link := notify_link('pur', st.doc_id);
      what := 'Approve purchase request · ' || coalesce(d->>'purpose','') || ' · RM ' || to_char(coalesce(_pur_total(d),0),'FM999,999,990.00');
      select array_agg(id) into who from profiles where active and can_approve;
    elsif st.kind = 'wo_open' then
      if coalesce(d->>'status','') not in ('Open','In progress','Waiting parts') or coalesce(d->>'draft','') = 'true' then continue; end if;
      thr := case d->>'priority' when 'Critical' then 1 when 'High' then 3 else 7 end;
      ref := coalesce(d->>'no','Work order'); link := notify_link('wo', st.doc_id);
      what := coalesce(d->>'status','') || ' · ' || coalesce(d->>'priority','') || ' · ' || coalesce(d->>'title','');
      who := array[coalesce(case when (d->>'picId') ~ '^[0-9a-f-]{36}$' then (d->>'picId')::uuid end, notify_creator(d))];
    elsif st.kind = 'wo_verify' then
      if coalesce(d->>'status','') <> 'Completed' then continue; end if;
      thr := 2; ref := coalesce(d->>'no','Work order'); link := notify_link('wo', st.doc_id);
      what := 'Verify completed job · ' || coalesce(d->>'title','');
      select array_agg(id) into who from profiles where active and can_verify;
    else continue; end if;

    if notify_wdays(st.since) < thr or notify_wdays(coalesce(st.last_at, st.since)) < thr then continue; end if;
    update notify_state set reminders = reminders + 1, last_at = now() where coll = st.coll and doc_id = st.doc_id and kind = st.kind;
    esc := st.kind <> 'pur_approve' and st.reminders + 1 >= 3;
    insert into _dig select u, ref, link, what, st.since, st.reminders + 1, false from unnest(coalesce(who,'{}')) u where u is not null;
    if esc then insert into _dig select id, ref, link, what, st.since, st.reminders + 1, true from profiles where active and role = 'admin'; end if;
  end loop;

  for r in select uid, bool_or(escal) anyesc, count(*) c from _dig group by uid loop
    select string_agg('<tr><td style="padding:8px 10px;border-bottom:1px solid #e5e7eb;white-space:nowrap"><a href="' || notify_esc(link) || '" style="color:#1f5f4a;font-weight:600">' || notify_esc(ref) || '</a></td>'
        || '<td style="padding:8px 10px;border-bottom:1px solid #e5e7eb">' || notify_esc(what) || case when escal then ' <b style="color:#b91c1c">(escalated)</b>' else '' end || '</td>'
        || '<td style="padding:8px 10px;border-bottom:1px solid #e5e7eb;white-space:nowrap">' || to_char(since at time zone 'Asia/Kuala_Lumpur','DD/MM/YYYY') || '</td>'
        || '<td style="padding:8px 10px;border-bottom:1px solid #e5e7eb;text-align:center">' || times || '</td></tr>', '' order by escal desc, since)
      into html from (select distinct on (ref, escal) * from _dig where uid = r.uid) z;
    perform notify_enqueue(r.uid, 'Reminder: ' || r.c || ' item(s) waiting for you in the CMMS',
      notify_html('Items waiting for you', 'These items have been waiting longer than expected. Please follow up today.'
        || case when r.anyesc then ' Items marked <b>escalated</b> have already had two reminders.' else '' end
        || '<br><br><table style="border-collapse:collapse;font-size:13px;width:100%"><tr style="background:#f3f4f6;text-align:left"><th style="padding:8px 10px">Ref</th><th style="padding:8px 10px">Waiting for</th><th style="padding:8px 10px">Since</th><th style="padding:8px 10px">Reminder</th></tr>'
        || html || '</table>', null, notify_link('', '') , 'Open the CMMS'),
      'daily', null, null);
    n := n + 1;
  end loop;
  if n > 0 then perform notify_kick(); end if;
  return n;
end $$;

-- admin: send a test email to myself
create or replace function public.notify_test() returns jsonb language plpgsql security definer set search_path = public as $$
begin
  if not public.me_is_admin() then raise exception 'Only an admin can send a test email.' using errcode = '42501'; end if;
  perform notify_enqueue(auth.uid(), 'Test email from the GFB CMMS',
    notify_html('Email notifications are working', 'If you can read this, the CMMS can send emails from Microsoft 365.', null, notify_link('',''), 'Open the CMMS'),
    'test', null, null);
  perform notify_kick();
  return jsonb_build_object('ok', true);
end $$;

-- admin: switch on/off
create or replace function public.notify_set_enabled(p_on boolean) returns jsonb language plpgsql security definer set search_path = public as $$
begin
  if not public.me_is_admin() then raise exception 'Only an admin can change this.' using errcode = '42501'; end if;
  insert into notify_settings values ('enabled', case when p_on then 'true' else 'false' end)
  on conflict (key) do update set value = excluded.value;
  return jsonb_build_object('ok', true);
end $$;

-- used only by the sender (service role)
create or replace function public.notify_claim(p_n int) returns setof public.notify_outbox language sql security definer set search_path = public as $$
  update notify_outbox set claimed_at = now(), attempts = attempts + 1
   where id in (select id from notify_outbox where sent_at is null and attempts < 5
                  and (claimed_at is null or claimed_at < now() - interval '10 minutes')
                order by id limit p_n for update skip locked)
  returning * $$;
create or replace function public.notify_done(p_id bigint, p_ok boolean, p_err text) returns void language sql security definer set search_path = public as $$
  update notify_outbox set sent_at = case when p_ok then now() end, last_error = case when p_ok then null else left(p_err, 500) end,
    claimed_at = case when p_ok then claimed_at end where id = p_id $$;
create or replace function public.notify_status(p_text text) returns void language sql security definer set search_path = public as $$
  insert into notify_settings values ('last_status', left(p_text, 300)) on conflict (key) do update set value = excluded.value $$;

revoke execute on function public.notify_claim(int), public.notify_done(bigint,boolean,text), public.notify_status(text),
  public.notify_kick(), public.notify_enqueue(uuid,text,text,text,text,text), public.notify_daily(),
  public.notify_doc_change(), public.notify_doc_delete(), public.notify_creator(jsonb) from public, anon, authenticated;
grant execute on function public.notify_claim(int), public.notify_done(bigint,boolean,text), public.notify_status(text) to service_role;
revoke execute on function public.notify_test(), public.notify_set_enabled(boolean) from public, anon;
grant execute on function public.notify_test(), public.notify_set_enabled(boolean) to authenticated;
select vault.create_secret(encode(gen_random_bytes(24),'hex'), 'notify_key', 'CMMS email sender key') where not exists (select 1 from vault.secrets where name='notify_key');
select cron.schedule('cmms-notify-daily', '0 0 * * 1-5', 'select public.notify_daily()');   -- 8:00 am Malaysia time, Mon-Fri
select cron.schedule('cmms-notify-retry', '*/10 * * * *', 'select public.notify_kick()');
