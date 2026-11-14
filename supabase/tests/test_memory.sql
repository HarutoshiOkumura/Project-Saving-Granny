-- Test script for save_it_memory.sql. SCRATCH POSTGRES ONLY, never the Supabase project.
-- Run on an empty database after loading the schema:
--   psql -v ON_ERROR_STOP=1 -d saveit_test -f supabase/migrations/0001_save_it_memory.sql -f supabase/tests/test_memory.sql
-- Every check raises an exception on failure, so reaching "ALL CHECKS PASSED" means all passed.
-- 75 checks. Section 26 (API grants) runs only if the Supabase roles exist; to run it too (82 checks),
-- create them in the scratch cluster before loading the schema, and drop them afterwards:
--   create role anon nologin; create role authenticated nologin; create role service_role nologin bypassrls;
\set ON_ERROR_STOP 1
\pset pager off

create or replace function fake_vec(seed int) returns vector language sql immutable as $$
  select (array_agg(sin(seed * 12.9898 + g * 0.37)::real order by g))::vector(768)
  from generate_series(1, 768) g;
$$;

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

-- ---------- setup: one home, four rooms, five landmarks, two items ----------
insert into homes (id, person_name) values ('00000000-0000-0000-0000-000000000001', 'Grandma');

insert into rooms (id, home_id, name, spoken_name, floor, capture_allowed) values
 ('10000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000001','bedroom','your bedroom',2,true),
 ('10000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000001','kitchen','the kitchen',1,true),
 ('10000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000001','bathroom','the bathroom',2,false),
 ('10000000-0000-0000-0000-000000000004','00000000-0000-0000-0000-000000000001','hallway','the hallway',1,true);

insert into room_links values
 ('10000000-0000-0000-0000-000000000004','10000000-0000-0000-0000-000000000002'),
 ('10000000-0000-0000-0000-000000000004','10000000-0000-0000-0000-000000000001');

insert into landmarks (id, room_id, parent_id, name, spoken_name, kind) values
 ('20000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001',null,'nightstand','the table beside your bed','surface'),
 ('20000000-0000-0000-0000-000000000002','10000000-0000-0000-0000-000000000002',null,'counter','the kitchen counter','surface'),
 ('20000000-0000-0000-0000-000000000003','10000000-0000-0000-0000-000000000004',null,'key hook','the hook by the front door','fixture'),
 ('20000000-0000-0000-0000-000000000004','10000000-0000-0000-0000-000000000003',null,'sink','the bathroom sink','surface'),
 ('20000000-0000-0000-0000-000000000005','10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','top drawer','the top drawer','container');

insert into items (id, home_id, name, aliases, category, color, description, home_landmark_id, plural) values
 ('30000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000001','glasses','{specs,readers,"reading glasses"}','glasses','black','round reading glasses','20000000-0000-0000-0000-000000000001', true),
 ('30000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000001','keys','{"house keys","key"}','keys','orange','keys on an orange lanyard','20000000-0000-0000-0000-000000000003', true);

-- ---------- 1. spatial index ----------
select expect((select address from places where landmark = 'top drawer') = 'bedroom > nightstand > top drawer',
              'places view builds a nested address');

-- ---------- 2. embedding lookups ----------
insert into room_refs (room_id, model, embedding)
select '10000000-0000-0000-0000-000000000001', 'test', fake_vec(100 + g) from generate_series(1, 6) g;
insert into room_refs (room_id, model, embedding)
select '10000000-0000-0000-0000-000000000002', 'test', fake_vec(200 + g) from generate_series(1, 6) g;
insert into item_refs (item_id, model, embedding) values
 ('30000000-0000-0000-0000-000000000001', 'test', fake_vec(301)),
 ('30000000-0000-0000-0000-000000000002', 'test', fake_vec(401)),
 ('30000000-0000-0000-0000-000000000002', 'test', fake_vec(402));

select expect((select room from match_room('00000000-0000-0000-0000-000000000001', fake_vec(203), 5) limit 1) = 'kitchen',
              'match_room: nearest tour photos vote for the kitchen');
select expect((select votes from match_room('00000000-0000-0000-0000-000000000001', fake_vec(203), 5) limit 1) between 3 and 5,
              'match_room returns a vote count');
select expect((select item from match_item('00000000-0000-0000-0000-000000000001', 'keys', fake_vec(402)) limit 1) = 'keys'
          and (select similarity from match_item('00000000-0000-0000-0000-000000000001', 'keys', fake_vec(402)) limit 1) > 0.99,
              'match_item: best reference photo wins with similarity near 1');
select expect((select count(*) from match_item('00000000-0000-0000-0000-000000000001', 'wallet', fake_vec(402))) = 0,
              'match_item returns nothing for a category with no enrolled item');

-- ---------- 3. one glimpse is not an answer ----------
select expect((find_item('00000000-0000-0000-0000-000000000001', 'glasses')->>'state') = 'never_seen',
              'never seen before any sighting');
select expect((find_item('00000000-0000-0000-0000-000000000001', 'glasses')->'usual'->>'landmark') = 'the table beside your bed',
              'with no history, the usual place falls back to where the family says it belongs');
select expect((find_item('00000000-0000-0000-0000-000000000001', 'glasses')->>'plural')::boolean,
              'the plural flag is passed to the voice');

select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000001','glasses',
  '10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','on',false,
  now() - interval '3 hours', 0.9, 0.9, 0.9, 'crops/g1.jpg');

select expect((select status from sightings) = 'tentative', 'first frame is tentative');
select expect((find_item('00000000-0000-0000-0000-000000000001', 'glasses')->>'state') = 'never_seen'
          and (find_item('00000000-0000-0000-0000-000000000001', 'glasses')->>'possible_glimpse')::boolean,
              'a tentative glimpse does not become the answer, but is flagged');

-- ---------- 4. second frame confirms and merges ----------
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000001','glasses',
  '10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','on',false,
  now() - interval '3 hours' + interval '4 seconds', 0.95, 0.9, 0.9, 'crops/g2.jpg');

select expect((select count(*) from sightings) = 1, 'second frame merges into the same episode');
select expect((select status = 'active' and n_frames = 2 and crop_url = 'crops/g2.jpg' from sightings),
              'episode is active, counts 2 frames, keeps the better crop');
select expect((find_item('00000000-0000-0000-0000-000000000001', 'specs')->>'state') = 'seen'
          and (find_item('00000000-0000-0000-0000-000000000001', 'specs')->>'landmark') = 'the table beside your bed',
              'alias "specs" finds the glasses on the nightstand');
select expect((find_item('00000000-0000-0000-0000-000000000001', 'Glasses')->>'minutes_ago')::int between 178 and 181,
              'minutes_ago is about 180');
select expect((find_item('00000000-0000-0000-0000-000000000001', ' My reading glasses ')->>'item') = 'glasses',
              '"my reading glasses" resolves to the glasses');

-- ---------- 5. the item moves: old belief is superseded, history is kept ----------
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000001','glasses',
  '10000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000002','on',false,
  now() - interval '40 minutes', 0.9, 0.9, 0.9, 'crops/g3.jpg');
select expect((find_item('00000000-0000-0000-0000-000000000001', 'glasses')->>'landmark') = 'the table beside your bed'
          and (find_item('00000000-0000-0000-0000-000000000001', 'glasses')->>'possible_newer_glimpse')::boolean,
              'one frame in the kitchen does not overturn the belief yet');

select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000001','glasses',
  '10000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000002','on',false,
  now() - interval '40 minutes' + interval '3 seconds', 0.9, 0.9, 0.9, 'crops/g4.jpg');

select expect((select count(*) from sightings where item_id = '30000000-0000-0000-0000-000000000001' and status = 'active') = 1,
              'exactly one active row per item');
select expect((select count(*) from sightings where status = 'superseded') = 1, 'old place kept as superseded history');
select expect((find_item('00000000-0000-0000-0000-000000000001', 'glasses')->>'landmark') = 'the kitchen counter'
          and (find_item('00000000-0000-0000-0000-000000000001', 'glasses')->'previous'->>'landmark') = 'the table beside your bed',
              'answer is the kitchen counter, with the nightstand as the previous place');

-- ---------- 6. out-of-order frame from the past does not steal the belief ----------
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000001','glasses',
  '10000000-0000-0000-0000-000000000004','20000000-0000-0000-0000-000000000003','on',false,
  now() - interval '2 hours', 0.9, 0.9, 0.9);
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000001','glasses',
  '10000000-0000-0000-0000-000000000004','20000000-0000-0000-0000-000000000003','on',false,
  now() - interval '2 hours' + interval '2 seconds', 0.9, 0.9, 0.9);
select expect((find_item('00000000-0000-0000-0000-000000000001', 'glasses')->>'landmark') = 'the kitchen counter',
              'a late-arriving older episode is filed as history, not as the current belief');
select expect((select count(*) from sightings where item_id = '30000000-0000-0000-0000-000000000001' and status = 'active') = 1,
              'still exactly one active row');

-- ---------- 7. negative evidence ----------
select expect(mark_absent('00000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000002', now() - interval '20 minutes') = 0,
              'seen empty once: nothing flips');
select expect(mark_absent('00000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000002', now() - interval '19 minutes') = 0,
              'seen empty twice: nothing flips');
select expect((find_item('00000000-0000-0000-0000-000000000001', 'glasses')->>'state') = 'seen', 'still "seen" after two empty looks');
select expect(mark_absent('00000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000002', now() - interval '18 minutes') = 1,
              'seen empty three times: sighting flips to contradicted');
select expect((find_item('00000000-0000-0000-0000-000000000001', 'glasses')->>'state') = 'not_there_anymore',
              'agent is told "not there any more"');

-- an item that is visible is not counted absent
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000002','keys',
  '10000000-0000-0000-0000-000000000004','20000000-0000-0000-0000-000000000003','on',false, now() - interval '5 hours', 0.9,0.9,0.9);
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000002','keys',
  '10000000-0000-0000-0000-000000000004','20000000-0000-0000-0000-000000000003','on',false, now() - interval '5 hours' + interval '2 seconds', 0.9,0.9,0.9);
select mark_absent('00000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000003', now() - interval '4 hours',
                   array['30000000-0000-0000-0000-000000000002']::uuid[]);
select expect((select absent_count from sightings where item_id = '30000000-0000-0000-0000-000000000002' and status = 'active') = 0,
              'an item listed as visible is not marked absent');

-- ---------- 8. re-sighting after contradiction, and absent_count reset ----------
select mark_absent('00000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000003', now() - interval '3 hours');
select expect((select absent_count from sightings where item_id = '30000000-0000-0000-0000-000000000002' and status = 'active') = 1,
              'one empty look is counted');
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000002','keys',
  '10000000-0000-0000-0000-000000000004','20000000-0000-0000-0000-000000000003','on',false, now() - interval '2 hours', 0.9,0.9,0.9);
select expect((select absent_count = 0 and n_frames = 3 and last_seen_at - first_seen_at > interval '2 hours'
                 from sightings where item_id = '30000000-0000-0000-0000-000000000002' and status = 'active'),
              'seeing it there again hours later extends the same stay and resets the absent counter');
select expect((select count(*) from sightings where item_id = '30000000-0000-0000-0000-000000000002') = 1,
              'no duplicate episode was opened for the same stay');

-- ---------- 9. carried in hand ----------
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000002','keys',
  '10000000-0000-0000-0000-000000000002',null,'unknown',true, now() - interval '10 minutes', 0.9,0.9,0.9);
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000002','keys',
  '10000000-0000-0000-0000-000000000002',null,'unknown',true, now() - interval '10 minutes' + interval '2 seconds', 0.9,0.9,0.9);
insert into observations (home_id, device_id, captured_at, room_id, room_conf, idempotency_key) values
 ('00000000-0000-0000-0000-000000000001','phone-1', now() - interval '6 minutes','10000000-0000-0000-0000-000000000001',0.9,'phone-1:t1');
select expect((find_item('00000000-0000-0000-0000-000000000001', 'house keys')->>'state') = 'carried'
          and (find_item('00000000-0000-0000-0000-000000000001', 'house keys')->>'wearer_went_to') = 'your bedroom'
          and (find_item('00000000-0000-0000-0000-000000000001', 'house keys')->'previous'->>'landmark') = 'the hook by the front door',
              'keys: carried in the kitchen, wearer then went to the bedroom, previous place is the hook');

-- ---------- 10. idempotent observations ----------
insert into observations (home_id, device_id, captured_at, room_id, idempotency_key) values
 ('00000000-0000-0000-0000-000000000001','phone-1', now() - interval '6 minutes','10000000-0000-0000-0000-000000000001','phone-1:t1')
on conflict (home_id, idempotency_key) do nothing;
select expect((select count(*) from observations) = 1, 'a retried frame is not logged twice');

-- ---------- 11. privacy: bathroom is never stored ----------
select expect(log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000001','glasses',
  '10000000-0000-0000-0000-000000000003','20000000-0000-0000-0000-000000000004','on',false, now(), 0.99,0.99,0.99) is null,
              'log_sighting returns null for a no-capture room');
select expect((select count(*) from sightings where room_id = '10000000-0000-0000-0000-000000000003') = 0,
              'no bathroom sighting exists');

-- ---------- 12. "told" by a person counts immediately ----------
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000001','glasses',
  '10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000005','in',false, now() - interval '2 minutes',
  null, null, null, null, 'daughter said she put them in the drawer', null, 'told', 'manual');
select expect((find_item('00000000-0000-0000-0000-000000000001', 'glasses')->>'address') = 'bedroom > nightstand > top drawer'
          and (find_item('00000000-0000-0000-0000-000000000001', 'glasses')->>'state') = 'seen',
              'a caregiver telling the system is active at once');

-- ---------- 13. unresolved identity: "some keys" ----------
select log_sighting('00000000-0000-0000-0000-000000000001', null, 'keys',
  '10000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000002','on',false, now() - interval '1 minute', 0.8,0.9,null);
select log_sighting('00000000-0000-0000-0000-000000000001', null, 'keys',
  '10000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000002','on',false, now() - interval '55 seconds', 0.8,0.9,null);
select expect((select count(*) from sightings where item_id is null and status = 'active' and n_frames = 2) = 1,
              'unowned detections merge by label without touching item beliefs');
select mark_absent('00000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000002', now(), array['30000000-0000-0000-0000-000000000001']::uuid[]);
select mark_absent('00000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000002', now());
select expect((select absent_count from sightings where item_id is null) = 0,
              'absence is only tracked for enrolled items');
select expect((find_item('00000000-0000-0000-0000-000000000001', 'keys')->>'state') = 'carried',
              'unowned keys do not change the answer for the enrolled keys');

-- ---------- 14. habits, unknown item, perception context ----------
select expect((select count(*) from item_usual_places where item_id = '30000000-0000-0000-0000-000000000001') >= 3,
              'usual places has rows for the glasses');
select expect((select sum(pct) from item_usual_places where item_id = '30000000-0000-0000-0000-000000000001') between 99 and 101,
              'usual-place percentages add up to 100');
select expect((find_item('00000000-0000-0000-0000-000000000001', 'wallet')->>'state') = 'unknown_item', 'unknown item is reported as such');

select expect(jsonb_array_length(perception_context('00000000-0000-0000-0000-000000000001')->'rooms') = 4
          and not exists (select 1 from jsonb_array_elements(perception_context('00000000-0000-0000-0000-000000000001')->'landmarks') e
                           where e->>'room' = 'bathroom')
          and jsonb_array_length(perception_context('00000000-0000-0000-0000-000000000001')->'beliefs') = 2,
              'perception context lists rooms and beliefs and leaves out bathroom landmarks');
select expect(jsonb_array_length(perception_context('00000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000002')->'landmarks') = 2,
              'context for the kitchen holds only kitchen and adjoining hallway landmarks');

-- ---------- 15. feedback closes the loop ----------
insert into queries (id, home_id, channel, heard, item_id, sighting_id, state)
select '40000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000001','phone','where are my glasses',
       '30000000-0000-0000-0000-000000000001', (find_item('00000000-0000-0000-0000-000000000001','glasses')->>'sighting_id')::uuid, 'seen';
select record_outcome('40000000-0000-0000-0000-000000000001', false);
select expect((find_item('00000000-0000-0000-0000-000000000001', 'glasses')->>'state') = 'not_there_anymore',
              '"it was not there" retires the answer');

-- ---------- 16. retention ----------
update sightings set last_seen_at = now() - interval '9 days', first_seen_at = now() - interval '9 days'
 where status = 'superseded' and landmark_id = '20000000-0000-0000-0000-000000000001';
select purge_old('00000000-0000-0000-0000-000000000001');
select expect((select crop_url is null from sightings where status = 'superseded' and landmark_id = '20000000-0000-0000-0000-000000000001'),
              'old crops are cleared; the place fact stays');

-- ---------- 17. timeline ----------
select expect((select count(*) from timeline where item = 'glasses') >= 4, 'timeline lists the glasses history');

-- ---------- 18. the usual place never repeats the place just ruled out ----------
insert into items (id, home_id, name, category, home_landmark_id) values
 ('30000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000001','remote','remote','20000000-0000-0000-0000-000000000001');

-- one stay on the counter, then the counter is seen empty three times
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000003','remote',
  '10000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000002','on',false, now() - interval '6 hours', 0.9,0.9,0.9);
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000003','remote',
  '10000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000002','on',false, now() - interval '6 hours' + interval '2 seconds', 0.9,0.9,0.9);
select mark_absent('00000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000002', now() - interval '5 hours 50 minutes');
select mark_absent('00000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000002', now() - interval '5 hours 49 minutes');
select mark_absent('00000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000002', now() - interval '5 hours 48 minutes');
select expect((find_item('00000000-0000-0000-0000-000000000001', 'remote')->>'state') = 'not_there_anymore'
          and (find_item('00000000-0000-0000-0000-000000000001', 'remote')->'usual'->>'landmark') = 'the table beside your bed',
              'one counter stay, then ruled out: usual is where it belongs, not the counter');

-- two stays at the key hook make it a habit
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000003','remote',
  '10000000-0000-0000-0000-000000000004','20000000-0000-0000-0000-000000000003','on',false, now() - interval '5 hours', 0.9,0.9,0.9);
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000003','remote',
  '10000000-0000-0000-0000-000000000004','20000000-0000-0000-0000-000000000003','on',false, now() - interval '5 hours' + interval '2 seconds', 0.9,0.9,0.9);
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000003','remote',
  '10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','on',false, now() - interval '4 hours', 0.9,0.9,0.9);
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000003','remote',
  '10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','on',false, now() - interval '4 hours' + interval '2 seconds', 0.9,0.9,0.9);
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000003','remote',
  '10000000-0000-0000-0000-000000000004','20000000-0000-0000-0000-000000000003','on',false, now() - interval '3 hours', 0.9,0.9,0.9);
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000003','remote',
  '10000000-0000-0000-0000-000000000004','20000000-0000-0000-0000-000000000003','on',false, now() - interval '3 hours' + interval '2 seconds', 0.9,0.9,0.9);
select expect((find_item('00000000-0000-0000-0000-000000000001', 'remote')->>'landmark') = 'the hook by the front door'
          and (find_item('00000000-0000-0000-0000-000000000001', 'remote')->'usual'->>'landmark') = 'the hook by the front door',
              'two stays at one place make it the usual place');

-- the key hook is ruled out: it is not offered as usual, even with two stays
select mark_absent('00000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000003', now() - interval '2 hours 50 minutes');
select mark_absent('00000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000003', now() - interval '2 hours 49 minutes');
select mark_absent('00000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000003', now() - interval '2 hours 48 minutes');
select expect((find_item('00000000-0000-0000-0000-000000000001', 'remote')->>'state') = 'not_there_anymore'
          and (find_item('00000000-0000-0000-0000-000000000001', 'remote')->'usual'->>'landmark') = 'the table beside your bed',
              'a ruled-out place with two stays is not the usual place; fall back to where it belongs');

-- the place where it belongs is ruled out: usual is the next habit
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000003','remote',
  '10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','on',false, now() - interval '2 hours', 0.9,0.9,0.9);
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000003','remote',
  '10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','on',false, now() - interval '2 hours' + interval '2 seconds', 0.9,0.9,0.9);
select mark_absent('00000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001', now() - interval '1 hour 50 minutes');
select mark_absent('00000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001', now() - interval '1 hour 49 minutes');
select mark_absent('00000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001', now() - interval '1 hour 48 minutes');
select expect((find_item('00000000-0000-0000-0000-000000000001', 'remote')->>'landmark') = 'the table beside your bed'
          and (find_item('00000000-0000-0000-0000-000000000001', 'remote')->'usual'->>'landmark') = 'the hook by the front door',
              'when the place it belongs is ruled out, usual is the next habit');

-- ---------- 19. the same frame sent twice is one frame ----------
insert into items (id, home_id, name, category, home_landmark_id) values
 ('30000000-0000-0000-0000-000000000004','00000000-0000-0000-0000-000000000001','phone','phone','20000000-0000-0000-0000-000000000001');
select now() - interval '30 minutes' as phone_t \gset
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000004','phone',
  '10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','on',false, :'phone_t', 0.9,0.9,0.9) as phone_s1 \gset
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000004','phone',
  '10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','on',false, :'phone_t', 0.9,0.9,0.9) as phone_s2 \gset
select expect(:'phone_s1' = :'phone_s2'
          and (select status = 'tentative' and n_frames = 1 from sightings where id = :'phone_s1'),
              'the same frame sent twice leaves the stay tentative with 1 frame');

select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000004','phone',
  '10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','on',false, (:'phone_t')::timestamptz + interval '2 seconds', 0.9,0.9,0.9);
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000004','phone',
  '10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','on',false, :'phone_t', 0.9,0.9,0.9);
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000004','phone',
  '10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','on',false, (:'phone_t')::timestamptz + interval '2 seconds', 0.9,0.9,0.9);
select expect((select status = 'active' and n_frames = 2 from sightings where id = :'phone_s1'),
              'a new frame confirms the stay; repeats of its first or last frame are not counted');

-- ---------- 20. empty looks count only when spaced out ----------
select now() - interval '20 minutes' as gap_t \gset
select mark_absent('00000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001', :'gap_t');
select mark_absent('00000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001', (:'gap_t')::timestamptz + interval '2 seconds');
select mark_absent('00000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001', (:'gap_t')::timestamptz + interval '4 seconds');
select expect((select status = 'active' and absent_count = 1 from sightings where id = :'phone_s1'),
              'three empty looks 2 seconds apart count once and leave the stay active');

select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000004','phone',
  '10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','on',false, (:'gap_t')::timestamptz + interval '1 minute', 0.9,0.9,0.9);
select expect((select absent_count = 0 and last_absent_at is null and n_frames = 3 from sightings where id = :'phone_s1'),
              'seeing it again resets the absence count and its clock');

select mark_absent('00000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001', (:'gap_t')::timestamptz + interval '2 minutes');
select mark_absent('00000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001', (:'gap_t')::timestamptz + interval '2 minutes 40 seconds');
select expect(mark_absent('00000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001',
                          (:'gap_t')::timestamptz + interval '3 minutes 20 seconds') = 1,
              'three empty looks 40 seconds apart contradict the stay');
select expect((find_item('00000000-0000-0000-0000-000000000001', 'phone')->>'state') = 'not_there_anymore',
              'after spaced empty looks the phone is "not there any more"');

-- ---------- 21. the landmark decides the room ----------
insert into items (id, home_id, name, category) values
 ('30000000-0000-0000-0000-000000000005','00000000-0000-0000-0000-000000000001','cane','cane');
select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000005','cane',
  null,'20000000-0000-0000-0000-000000000002','next_to',false, now() - interval '15 minutes', 0.9,0.9,0.9) as cane_s \gset
select expect((select room_id = '10000000-0000-0000-0000-000000000002' from sightings where id = :'cane_s'),
              'with only a landmark given, the room is the landmark''s room');
select expect_error($$select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000005','cane',
  '10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000002','next_to',false, now(), 0.9,0.9,0.9)$$,
              '22023', 'a room that disagrees with the landmark is refused');
select expect_error($$select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000005','cane',
  null,'29999999-0000-0000-0000-000000000000','next_to',false, now(), 0.9,0.9,0.9)$$,
              '22023', 'a landmark that is not in this home is refused');
select expect_error($$select log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000005','cane',
  '19999999-0000-0000-0000-000000000000',null,'unknown',false, now(), 0.9,0.9,0.9)$$,
              '22023', 'a room that is not in this home is refused');

-- ---------- 22. privacy fails closed ----------
select expect(log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000005','cane',
  null,null,'unknown',false, now() - interval '10 minutes', 0.9,0.9,0.9) is null,
              'a worn-camera frame from an unknown room is not stored');
select expect(log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000005','cane',
  null,null,'unknown',false, now() - interval '10 minutes', 0.9,0.9,0.9, null, null, null, 'seen', 'facetime_caller') is null,
              'a FaceTime frame from an unknown room is not stored');
select expect((select count(*) from sightings where room_id is null and source in ('worn_cam','facetime_caller')) = 0,
              'no camera sighting without a room exists');
select expect(log_sighting('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000005','cane',
  null,null,'unknown',true, now() - interval '9 minutes', null,null,null, null, 'she has it with her', null, 'told', 'manual') is not null,
              'a person telling us, with no room, is still stored');

insert into observations (home_id, device_id, captured_at, room_id, idempotency_key) values
 ('00000000-0000-0000-0000-000000000001','phone-1', now(),'10000000-0000-0000-0000-000000000003','phone-1:bath');
select expect((select count(*) from observations where idempotency_key = 'phone-1:bath') = 0,
              'a direct insert of a bathroom observation stores nothing');
insert into observations (home_id, device_id, captured_at, landmarks_seen, idempotency_key) values
 ('00000000-0000-0000-0000-000000000001','phone-1', now(), array['20000000-0000-0000-0000-000000000004']::uuid[],'phone-1:sink');
select expect((select count(*) from observations where idempotency_key = 'phone-1:sink') = 0,
              'an observation that saw a bathroom landmark stores nothing');
insert into sightings (home_id, item_id, label, landmark_id, first_seen_at, last_seen_at) values
 ('00000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000005','cane','20000000-0000-0000-0000-000000000004', now(), now());
select expect((select count(*) from sightings where landmark_id = '20000000-0000-0000-0000-000000000004') = 0,
              'a direct insert of a bathroom sighting stores nothing');
update sightings set room_id = '10000000-0000-0000-0000-000000000003', landmark_id = '20000000-0000-0000-0000-000000000004'
 where id = :'cane_s';
select expect((select room_id = '10000000-0000-0000-0000-000000000002' from sightings where id = :'cane_s'),
              'a sighting cannot be moved into a no-capture room');

-- ---------- 23. one call answers and logs the question ----------
select ask_item('00000000-0000-0000-0000-000000000001', 'house keys', 'phone') as ask \gset
select expect(((:'ask')::jsonb->>'state') = 'carried'
          and ((:'ask')::jsonb->>'sighting_id') = (find_item('00000000-0000-0000-0000-000000000001', 'house keys')->>'sighting_id')
          and ((:'ask')::jsonb->>'item') = 'keys',
              'ask_item answers like find_item');
select expect((select heard = 'house keys' and channel = 'phone' and state = 'carried'
                  and item_id = '30000000-0000-0000-0000-000000000002'
                  and sighting_id = ((:'ask')::jsonb->>'sighting_id')::uuid
                 from queries where id = ((:'ask')::jsonb->>'query_id')::uuid),
              'ask_item logs what was heard, the item, the sighting and the state, and returns query_id');
select record_outcome(((:'ask')::jsonb->>'query_id')::uuid, true);
select expect((select outcome = 'found' and outcome_at is not null from queries where id = ((:'ask')::jsonb->>'query_id')::uuid),
              'record_outcome updates the logged question');
select ask_item('00000000-0000-0000-0000-000000000001', 'umbrella', 'web') as ask2 \gset
select expect(((:'ask2')::jsonb->>'state') = 'unknown_item'
          and (select state = 'unknown_item' and item_id is null and sighting_id is null and heard = 'umbrella'
                 from queries where id = ((:'ask2')::jsonb->>'query_id')::uuid),
              'an unknown item is logged with what was heard');

-- ---------- 24. fields speak() needs ----------
select expect((find_item('00000000-0000-0000-0000-000000000001', 'house keys')->>'last_seen_at') like '%Z'
          and (find_item('00000000-0000-0000-0000-000000000001', 'house keys')->>'last_seen_at')::timestamptz
              = (select last_seen_at from sightings
                  where id = (find_item('00000000-0000-0000-0000-000000000001', 'house keys')->>'sighting_id')::uuid)
          and (find_item('00000000-0000-0000-0000-000000000001', 'house keys')->>'timezone') = 'America/New_York',
              'find_item gives last_seen_at in UTC to the microsecond, and the home''s timezone');
insert into items (id, home_id, name, category) values
 ('30000000-0000-0000-0000-000000000006','00000000-0000-0000-0000-000000000001','hat','hat');
select expect((find_item('00000000-0000-0000-0000-000000000001', 'hat')->>'state') = 'never_seen'
          and (find_item('00000000-0000-0000-0000-000000000001', 'hat')->>'timezone') = 'America/New_York'
          and not (find_item('00000000-0000-0000-0000-000000000001', 'hat') ? 'last_seen_at'),
              'never_seen carries the timezone and no last_seen_at');

-- ---------- 25. functions pin their search_path (Supabase security advisor) ----------
select expect(not exists (
  select 1 from pg_proc p
   where p.pronamespace = 'public'::regnamespace
     and p.proname not in ('expect', 'expect_error', 'fake_vec')                          -- test helpers
     and not exists (select 1 from pg_depend d where d.objid = p.oid and d.deptype = 'e')  -- vector's own
     and not exists (select 1 from unnest(p.proconfig) c where c like 'search_path=%')),
              'every schema function pins its search_path');

-- ---------- 26. API grants (only where the Supabase roles exist) ----------
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'service_role') then
    raise notice 'skip  API grants: this database has no Supabase roles';
    return;
  end if;

  perform expect(not exists (
      select 1 from pg_class c, unnest(array['anon', 'authenticated']) r
       where c.relnamespace = 'public'::regnamespace and c.relkind in ('r', 'v')
         and has_table_privilege(r, c.oid, 'select, insert, update, delete, truncate, references, trigger')),
    'anon and authenticated have no privilege on any table or view');
  perform expect(not exists (
      select 1 from pg_proc p, unnest(array['anon', 'authenticated']) r
       where p.pronamespace = 'public'::regnamespace
         and p.proname not in ('expect', 'expect_error', 'fake_vec')
         and not exists (select 1 from pg_depend d where d.objid = p.oid and d.deptype = 'e')
         and has_function_privilege(r, p.oid, 'execute')),
    'anon and authenticated cannot run any function in public (vector''s own aside)');
  perform expect(not exists (
      select 1 from pg_class c
       where c.relnamespace = 'public'::regnamespace
         and ((c.relkind = 'r' and not (has_table_privilege('service_role', c.oid, 'select')
                                    and has_table_privilege('service_role', c.oid, 'insert')
                                    and has_table_privilege('service_role', c.oid, 'update')
                                    and has_table_privilege('service_role', c.oid, 'delete')))
           or (c.relkind = 'v' and not has_table_privilege('service_role', c.oid, 'select')))),
    'service_role can read and write every table and read every view');
  perform expect(not exists (
      select 1 from pg_proc p
       where p.pronamespace = 'public'::regnamespace
         and p.proname not in ('expect', 'expect_error', 'fake_vec')
         and p.prorettype <> 'trigger'::regtype
         and not exists (select 1 from pg_depend d where d.objid = p.oid and d.deptype = 'e')
         and not has_function_privilege('service_role', p.oid, 'execute')),
    'service_role can run every function');

  set role service_role;
  perform expect((ask_item('00000000-0000-0000-0000-000000000001', 'keys', 'web')->>'state') = 'carried',
    'service_role can ask where the keys are');
  insert into observations (home_id, device_id, captured_at, room_id, idempotency_key) values
   ('00000000-0000-0000-0000-000000000001','phone-1', now(),'10000000-0000-0000-0000-000000000003','phone-1:bath2');
  reset role;
  perform expect((select count(*) from observations where idempotency_key = 'phone-1:bath2') = 0,
    'the privacy trigger still drops a bathroom row written by service_role');

  set role anon;
  perform expect_error($q$select find_item('00000000-0000-0000-0000-000000000001', 'keys')$q$, '42501',
    'anon cannot call find_item');
  reset role;
end $$;

\echo
\echo ALL CHECKS PASSED
\echo
\echo --- sample find_item output (what the voice agent receives) ---
select jsonb_pretty(find_item('00000000-0000-0000-0000-000000000001', 'house keys'));
\echo --- find_item timing (20 calls) ---
\timing on
select count(*) as calls, sum(length(find_item('00000000-0000-0000-0000-000000000001', 'keys')::text)) > 0 as answered from generate_series(1, 20);
\timing off
\echo --- timeline ---
select item, status, in_hand, event_type, address, to_char(last_seen_at, 'HH24:MI') as last_seen from timeline order by item, last_seen_at;
