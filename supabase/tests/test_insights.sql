-- Tests for 0005_insights.sql. Scratch Postgres only, never the Supabase project.
-- Runs on its own home, so it can share a database with test_memory.sql:
--   psql "$SCRATCH" -v ON_ERROR_STOP=1 -f supabase/migrations/0001_save_it_memory.sql \
--        -f supabase/migrations/0002_lock_rls_auto_enable.sql \
--        -f supabase/migrations/0005_insights.sql -f supabase/tests/test_insights.sql
-- 0005 does not depend on 0003 or 0004, so they are not loaded.
-- Every check raises on failure, so reaching "ALL INSIGHTS CHECKS PASSED" means all passed.
-- The grant checks run only if the Supabase roles exist (see test_memory.sql's header).
\set ON_ERROR_STOP 1
\pset pager off

create or replace function expect(ok boolean, what text) returns void language plpgsql as $$
begin
  if ok is not true then raise exception 'FAILED: %', what; end if;
  raise notice 'ok  %', what;
end $$;

create or replace function expect_error(stmt text, errcode text, what text) returns void language plpgsql as $$
begin
  begin
    execute stmt;
  exception when others then
    if sqlstate <> errcode then
      raise exception 'FAILED: % (got % %, wanted %)', what, sqlstate, sqlerrm, errcode;
    end if;
    raise notice 'ok  %', what;
    return;
  end;
  raise exception 'FAILED: % (no error raised)', what;
end $$;

-- ---------- setup: one home in New York, one room ----------
insert into homes (id, person_name, timezone) values
 ('c0000000-0000-0000-0000-000000000001', 'Grandma', 'America/New_York');
insert into rooms (id, home_id, name, spoken_name) values
 ('c1000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000001', 'kitchen', 'the kitchen');

-- ---------- 1. every new table has row level security ----------
select expect((select bool_and(relrowsecurity) from pg_class
                where relname in ('wear_minutes','life_events','concerns') and relkind = 'r')
              and (select count(*) from pg_class
                    where relname in ('wear_minutes','life_events','concerns') and relkind = 'r') = 3,
              '1 wear_minutes, life_events and concerns exist with RLS on');

-- ---------- 2. wear_minutes: counts only, one row per device per minute ----------
insert into wear_minutes (home_id, device_id, minute, frames, moving) values
 ('c0000000-0000-0000-0000-000000000001', 'lanyard', '2026-11-14 14:00:00+00', 120, 100),  -- 09:00 local
 ('c0000000-0000-0000-0000-000000000001', 'lanyard', '2026-11-14 14:01:00+00', 120, 1),    -- lying still
 ('c0000000-0000-0000-0000-000000000001', 'lanyard', '2026-11-14 15:30:00+00', 60, 30);    -- 10:30 local
select expect_error($$insert into wear_minutes (home_id, device_id, minute, frames, moving)
                      values ('c0000000-0000-0000-0000-000000000001', 'lanyard', '2026-11-14 14:00:00+00', 5, 5)$$,
                    '23505', '2a one row per device per minute');
select expect_error($$insert into wear_minutes (home_id, device_id, minute, frames, moving)
                      values ('c0000000-0000-0000-0000-000000000001', 'lanyard', '2026-11-14 16:00:00+00', 3, 4)$$,
                    '23514', '2b moving cannot exceed frames');
select expect_error($$insert into wear_minutes (home_id, device_id, minute, frames, moving)
                      values ('c0000000-0000-0000-0000-000000000001', 'lanyard', '2026-11-14 16:01:30+00', 3, 1)$$,
                    '23514', '2c minute is a whole minute');
select expect((select count(*) from information_schema.columns
                where table_name = 'wear_minutes'
                  and column_name not in ('home_id','device_id','minute','frames','moving')) = 0,
              '2d wear_minutes holds counts only: no room, no item, no image');

-- ---------- 3. wear views add up worn minutes by the home's local day and hour ----------
select expect((select worn_minutes from wear_daily
                where home_id = 'c0000000-0000-0000-0000-000000000001' and day = '2026-11-14') = 2,
              '3a wear_daily: a minute with fewer than 2 moving frames is not worn');
select expect((select frames from wear_daily
                where home_id = 'c0000000-0000-0000-0000-000000000001' and day = '2026-11-14') = 300,
              '3b wear_daily keeps the frame total');
select expect((select worn_minutes from wear_hourly
                where home_id = 'c0000000-0000-0000-0000-000000000001'
                  and day = '2026-11-14' and hour = 9) = 1,
              '3c wear_hourly uses the home''s local hour (14:00 UTC is 09:00 in New York)');
select expect((select worn_minutes from wear_hourly
                where home_id = 'c0000000-0000-0000-0000-000000000001'
                  and day = '2026-11-14' and hour = 10) = 1,
              '3d wear_hourly: 15:30 UTC is 10:00 to 11:00 local');

-- ---------- 4. life_events: family tags ----------
insert into life_events (home_id, kind, starts_at, note) values
 ('c0000000-0000-0000-0000-000000000001', 'new_medicine', '2026-11-10 12:00+00', 'started a new tablet');
select expect_error($$insert into life_events (home_id, kind, starts_at)
                      values ('c0000000-0000-0000-0000-000000000001', 'diagnosis', now())$$,
                    '23514', '4a an unknown tag kind is refused');
select expect_error($$insert into life_events (home_id, kind, starts_at, ends_at)
                      values ('c0000000-0000-0000-0000-000000000001', 'away', now(), now() - interval '1 day')$$,
                    '23514', '4b a tag cannot end before it starts');
select expect_error($$insert into life_events (home_id, kind, starts_at, note)
                      values ('c0000000-0000-0000-0000-000000000001', 'other', now(), repeat('x', 201))$$,
                    '23514', '4c a note is at most 200 characters');

-- ---------- 5. concerns: the safety loop ----------
insert into concerns (id, home_id, kind, answer, urgency, room_id) values
 ('c2000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000001', 'fall', 'no_answer',
  'urgent', 'c1000000-0000-0000-0000-000000000001');
select expect((select status = 'open' and channel = 'facetime' and handled_at is null from concerns
                where id = 'c2000000-0000-0000-0000-000000000001'),
              '5a a new concern is open, from FaceTime, not handled');
select expect_error($$insert into concerns (home_id, kind, urgency)
                      values ('c0000000-0000-0000-0000-000000000001', 'call_911', 'urgent')$$,
                    '23514', '5b an unknown concern kind is refused');
select expect_error($$insert into concerns (home_id, kind, urgency)
                      values ('c0000000-0000-0000-0000-000000000001', 'fall', 'emergency')$$,
                    '23514', '5c an unknown urgency is refused');
select expect_error($$update concerns set status = 'dispatched'
                       where id = 'c2000000-0000-0000-0000-000000000001'$$,
                    '23514', '5d only the family''s three answers close a concern');
update concerns set status = 'on_my_way', handled_at = now(), handled_by = 'June'
 where id = 'c2000000-0000-0000-0000-000000000001';
select expect((select status = 'on_my_way' from concerns where id = 'c2000000-0000-0000-0000-000000000001'),
              '5e the family can answer "on my way"');
select expect_error($$insert into concerns (home_id, kind, urgency, answer)
                      values ('c0000000-0000-0000-0000-000000000001', 'fall', 'urgent', 'maybe')$$,
                    '23514', '5f an unknown answer is refused');

-- ---------- 6. homes: sharing with a clinician is off until the wearer agrees ----------
select expect((select not share_summary_with_clinician and share_decided_at is null from homes
                where id = 'c0000000-0000-0000-0000-000000000001'),
              '6 sharing the summary is off by default, with no decision recorded');

-- ---------- 7. API grants (Supabase roles only) ----------
do $$ begin
  if exists (select 1 from pg_roles where rolname = 'service_role') then
    perform expect(not has_table_privilege('anon', 'concerns', 'select')
                   and not has_table_privilege('authenticated', 'wear_minutes', 'insert')
                   and not has_table_privilege('anon', 'wear_daily', 'select'),
                   '7a the publishable key reaches none of the new tables or views');
    perform expect(has_table_privilege('service_role', 'concerns', 'update')
                   and has_table_privilege('service_role', 'wear_minutes', 'insert')
                   and has_table_privilege('service_role', 'life_events', 'delete')
                   and has_table_privilege('service_role', 'wear_hourly', 'select'),
                   '7b the backend can use the new tables and views');
  else
    raise notice 'skip 7 (no Supabase roles on this cluster)';
  end if;
end $$;

select 'ALL INSIGHTS CHECKS PASSED' as result;
