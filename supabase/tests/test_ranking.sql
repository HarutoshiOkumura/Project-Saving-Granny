-- Tests for 0003_ranked_search.sql. Scratch Postgres only, never the Supabase project.
-- Runs on its own home, so it can share a database with test_memory.sql:
--   psql "$SCRATCH" -v ON_ERROR_STOP=1 -f supabase/migrations/0001_save_it_memory.sql \
--        -f supabase/migrations/0002_lock_rls_auto_enable.sql \
--        -f supabase/migrations/0003_ranked_search.sql -f supabase/tests/test_ranking.sql
-- Every check raises on failure, so reaching "ALL RANKING CHECKS PASSED" means all passed.
\set ON_ERROR_STOP 1
\pset pager off

create or replace function expect(ok boolean, what text) returns void language plpgsql as $$
begin
  if ok is not true then raise exception 'FAILED: %', what; end if;
  raise notice 'ok  %', what;
end $$;

-- ---------- setup: one home, four rooms (bathroom is no-capture), six landmarks, four items ----------
insert into homes (id, person_name) values ('a0000000-0000-0000-0000-000000000001', 'Grandma');

insert into rooms (id, home_id, name, spoken_name, floor, capture_allowed) values
 ('a1000000-0000-0000-0000-000000000001','a0000000-0000-0000-0000-000000000001','bedroom','your bedroom',1,true),
 ('a1000000-0000-0000-0000-000000000002','a0000000-0000-0000-0000-000000000001','kitchen','the kitchen',1,true),
 ('a1000000-0000-0000-0000-000000000003','a0000000-0000-0000-0000-000000000001','hallway','the hallway',1,true),
 ('a1000000-0000-0000-0000-000000000004','a0000000-0000-0000-0000-000000000001','bathroom','the bathroom',1,false);

insert into room_links values
 ('a1000000-0000-0000-0000-000000000003','a1000000-0000-0000-0000-000000000001'),
 ('a1000000-0000-0000-0000-000000000003','a1000000-0000-0000-0000-000000000002'),
 ('a1000000-0000-0000-0000-000000000003','a1000000-0000-0000-0000-000000000004');

insert into landmarks (id, room_id, name, spoken_name, kind) values
 ('a2000000-0000-0000-0000-000000000001','a1000000-0000-0000-0000-000000000001','nightstand','the table beside your bed','surface'),
 ('a2000000-0000-0000-0000-000000000002','a1000000-0000-0000-0000-000000000002','counter','the kitchen counter','surface'),
 ('a2000000-0000-0000-0000-000000000003','a1000000-0000-0000-0000-000000000002','table','the kitchen table','surface'),
 ('a2000000-0000-0000-0000-000000000004','a1000000-0000-0000-0000-000000000003','key hook','the hook by the front door','fixture'),
 ('a2000000-0000-0000-0000-000000000005','a1000000-0000-0000-0000-000000000002','drawer','the kitchen drawer','container'),
 ('a2000000-0000-0000-0000-000000000006','a1000000-0000-0000-0000-000000000004','sink','the bathroom sink','surface');

insert into items (id, home_id, name, aliases, category, home_landmark_id, plural) values
 ('a3000000-0000-0000-0000-000000000001','a0000000-0000-0000-0000-000000000001','glasses','{specs,readers}','glasses','a2000000-0000-0000-0000-000000000001', true),
 ('a3000000-0000-0000-0000-000000000002','a0000000-0000-0000-0000-000000000001','keys','{"house keys"}','keys','a2000000-0000-0000-0000-000000000004', true),
 ('a3000000-0000-0000-0000-000000000003','a0000000-0000-0000-0000-000000000001','remote','{clicker}','remote','a2000000-0000-0000-0000-000000000003', false),
 ('a3000000-0000-0000-0000-000000000004','a0000000-0000-0000-0000-000000000001','wallet','{billfold}','wallet',null, false);

-- ---------- 1. never seen: the place it belongs leads ----------
select expect(rank_item('a0000000-0000-0000-0000-000000000001', 'my specs')->'places'->0->>'landmark' = 'the table beside your bed'
          and rank_item('a0000000-0000-0000-0000-000000000001', 'my specs')->'places'->0->>'why' = 'usual'
          and rank_item('a0000000-0000-0000-0000-000000000001', 'my specs')->>'band' = 'high',
              'never seen: the home landmark leads, band high');
select expect(rank_item('a0000000-0000-0000-0000-000000000001', 'dentures')->>'state' = 'unknown_item',
              'unknown item is reported, not guessed');
select expect(rank_item('a0000000-0000-0000-0000-000000000001', 'specs')->'find'->>'state' = 'never_seen',
              'the result carries find_item under "find"');

-- ---------- 2. the camera sees the glasses on the nightstand twice, an hour ago ----------
select log_sighting('a0000000-0000-0000-0000-000000000001','a3000000-0000-0000-0000-000000000001','glasses',
  'a1000000-0000-0000-0000-000000000001','a2000000-0000-0000-0000-000000000001','on',false,
  now() - interval '60 minutes', 0.9, 0.9, 1.0);
select log_sighting('a0000000-0000-0000-0000-000000000001','a3000000-0000-0000-0000-000000000001','glasses',
  'a1000000-0000-0000-0000-000000000001','a2000000-0000-0000-0000-000000000001','on',false,
  now() - interval '60 minutes' + interval '2 seconds', 0.9, 0.9, 1.0);
select expect(rank_item('a0000000-0000-0000-0000-000000000001', 'glasses')->'places'->0->>'why' = 'camera'
          and (rank_item('a0000000-0000-0000-0000-000000000001', 'glasses')->'places'->0->>'minutes_ago')::int = 60,
              'camera evidence leads, with its age');

-- ---------- 3. the person says on a call they put them on the kitchen table (wrong) ----------
select log_sighting('a0000000-0000-0000-0000-000000000001','a3000000-0000-0000-0000-000000000001','glasses',
  'a1000000-0000-0000-0000-000000000002','a2000000-0000-0000-0000-000000000003','on',false,
  now() - interval '55 minutes', null, null, null, null, null, null, 'told', 'facetime_caller');
select expect(find_item('a0000000-0000-0000-0000-000000000001', 'glasses')->>'landmark' = 'the kitchen table',
              'find_item (0001) answers with the spoken claim');
select expect(rank_item('a0000000-0000-0000-0000-000000000001', 'glasses')->'places'->0->>'landmark' = 'the table beside your bed'
          and rank_item('a0000000-0000-0000-0000-000000000001', 'glasses')->'places'->1->>'landmark' = 'the kitchen table'
          and rank_item('a0000000-0000-0000-0000-000000000001', 'glasses')->'places'->1->>'why' = 'you_said',
              'rank_item keeps the camera first and the spoken claim second');

-- ---------- 4. the person checks the nightstand: not there ----------
select record_miss('a0000000-0000-0000-0000-000000000001','a3000000-0000-0000-0000-000000000001',
                   'a2000000-0000-0000-0000-000000000001', now() - interval '1 minute');
select expect(rank_item('a0000000-0000-0000-0000-000000000001', 'glasses')->'places'->0->>'landmark' = 'the kitchen table'
          and (rank_item('a0000000-0000-0000-0000-000000000001', 'glasses')->'places'->1->>'misses')::int = 1,
              'after one miss at the nightstand, the kitchen table leads');
select expect(record_miss('a0000000-0000-0000-0000-000000000001','a3000000-0000-0000-0000-000000000001',
                          'a2000000-0000-0000-0000-000000000001', (select max(missed_at) from misses)) is null,
              'the same miss sent twice counts once');

-- ---------- 5. the family types where the keys are: that does outrank the camera ----------
select log_sighting('a0000000-0000-0000-0000-000000000001','a3000000-0000-0000-0000-000000000002','keys',
  'a1000000-0000-0000-0000-000000000003','a2000000-0000-0000-0000-000000000004','on',false,
  now() - interval '60 minutes', 0.9, 0.9, 1.0);
select log_sighting('a0000000-0000-0000-0000-000000000001','a3000000-0000-0000-0000-000000000002','keys',
  'a1000000-0000-0000-0000-000000000003','a2000000-0000-0000-0000-000000000004','on',false,
  now() - interval '60 minutes' + interval '2 seconds', 0.9, 0.9, 1.0);
select log_sighting('a0000000-0000-0000-0000-000000000001','a3000000-0000-0000-0000-000000000002','keys',
  'a1000000-0000-0000-0000-000000000002','a2000000-0000-0000-0000-000000000005','in',false,
  now() - interval '55 minutes', null, null, null, null, null, null, 'told', 'manual');
select expect(rank_item('a0000000-0000-0000-0000-000000000001', 'keys')->'places'->0->>'landmark' = 'the kitchen drawer'
          and rank_item('a0000000-0000-0000-0000-000000000001', 'keys')->'places'->0->>'why' = 'family_said'
          and rank_item('a0000000-0000-0000-0000-000000000001', 'keys')->'places'->1->>'landmark' = 'the hook by the front door'
          and rank_item('a0000000-0000-0000-0000-000000000001', 'keys')->>'band' = 'split',
              'family input outranks the older camera sighting; the usual hook stays second (split)');

-- ---------- 6. the camera looks at the counter once and the remote is gone ----------
select log_sighting('a0000000-0000-0000-0000-000000000001','a3000000-0000-0000-0000-000000000003','remote',
  'a1000000-0000-0000-0000-000000000002','a2000000-0000-0000-0000-000000000002','on',false,
  now() - interval '30 minutes', 0.9, 0.9, 1.0);
select log_sighting('a0000000-0000-0000-0000-000000000001','a3000000-0000-0000-0000-000000000003','remote',
  'a1000000-0000-0000-0000-000000000002','a2000000-0000-0000-0000-000000000002','on',false,
  now() - interval '30 minutes' + interval '2 seconds', 0.9, 0.9, 1.0);
select expect(rank_item('a0000000-0000-0000-0000-000000000001', 'clicker')->'places'->0->>'landmark' = 'the kitchen counter',
              'remote seen on the counter leads');
select mark_absent('a0000000-0000-0000-0000-000000000001','a2000000-0000-0000-0000-000000000002',
                   now() - interval '10 minutes', '{}');
select expect(rank_item('a0000000-0000-0000-0000-000000000001', 'clicker')->'places'->0->>'landmark' = 'the kitchen table',
              'one empty look at the counter: the usual table leads');

-- ---------- 7. search order: what is close to the wearer comes first ----------
insert into observations (home_id, device_id, captured_at, room_id, idempotency_key)
values ('a0000000-0000-0000-0000-000000000001', 'lanyard', now() - interval '1 minute',
        'a1000000-0000-0000-0000-000000000002', 'test-ranking-7');
select expect(rank_item('a0000000-0000-0000-0000-000000000001', 'wallet')->>'wearer_room' = 'the kitchen'
          and rank_item('a0000000-0000-0000-0000-000000000001', 'wallet')->'search_order'->0->>'room' = 'the kitchen'
          and rank_item('a0000000-0000-0000-0000-000000000001', 'wallet')->'search_order'->2->>'landmark' = 'the hook by the front door'
          and rank_item('a0000000-0000-0000-0000-000000000001', 'wallet')->>'band' = 'low',
              'nothing known: nearby places come first and the band is low');

-- ---------- 8. record_miss refuses a place outside the home ----------
do $$ begin
  perform record_miss('a0000000-0000-0000-0000-000000000001', 'a3000000-0000-0000-0000-000000000001',
                      gen_random_uuid());
  raise exception 'FAILED: record_miss accepted a landmark outside the home';
exception when others then
  if sqlerrm like 'FAILED%' then raise; end if;
  raise notice 'ok  record_miss refuses a landmark outside the home';
end $$;

\echo ''
\echo 'ALL RANKING CHECKS PASSED'
\echo ''
\echo '--- sample rank_item output for "my specs" (what the voice tool receives) ---'
select jsonb_pretty(rank_item('a0000000-0000-0000-0000-000000000001', 'my specs') - 'find');
\timing on
select count(*) as calls, sum(length(rank_item('a0000000-0000-0000-0000-000000000001', 'glasses')::text)) > 0 as answered
  from generate_series(1, 20);
\timing off
