-- Test script for save_it_memory.sql. Run on an empty database after loading the schema:
--   psql -v ON_ERROR_STOP=1 -d saveit_test -f supabase/migrations/0001_save_it_memory.sql -f supabase/tests/test_memory.sql
-- Every check raises an exception on failure, so reaching "ALL CHECKS PASSED" means all passed.
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
