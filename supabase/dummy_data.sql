-- =====================================================================
-- Dummy data for building the read path (find API, speak(), Vapi, the Chert agent) before the
-- camera pipeline exists. Run it on the Supabase project (SQL editor, psql "$DATABASE_URL", or the
-- MCP execute_sql), or on scratch Postgres after the migrations and seed.sql.
--
-- It REPLACES the episodic log: it deletes every row in queries, sightings and observations for the
-- demo home, then writes the scenarios below. The home, rooms, landmarks and items are kept.
-- It refuses to run once the real camera pipeline has written anything (an observation from any
-- device other than 'dummy'). Safe to run again; each run starts from a clean log.
--
-- Afterwards find_item gives:
--   glasses   seen               on the kitchen counter, about 40 minutes ago; previous: the nightstand
--   keys      carried            in hand in the hallway 12 minutes ago; wearer_went_to: your bedroom
--   bag       not_there_anymore  last on the bedroom desk 2 hours ago, seen empty 3 times since;
--                                usual is null (the bag has no home landmark, and the desk is ruled out)
--   umbrella  unknown_item       (any word that is not an item name or alias)
--   never_seen is what every item says after the rehearsal reset, before any sighting.
-- photo is null everywhere (see the last rule below).
--
-- Clean up with the rehearsal reset when done, before real camera data:
--   delete from queries; delete from sightings; delete from observations;
--
-- Rules for writing more (also in .claude/rules/memory-db.md, "Dummy data"):
--   * Only through log_sighting and mark_absent. Never insert into sightings directly: that skips the
--     two-frame rule and can leave two active rows for one item.
--   * A stay answers only after two log_sighting calls at the same place with DIFFERENT p_seen_at,
--     within 10 minutes of each other. One call, or the same time twice, stays tentative, and
--     find_item says never_seen.
--   * mark_absent looks must be at least 30 seconds apart; 3 counted looks give not_there_anymore.
--   * Pass the landmark and leave p_room null: the room comes from the landmark. Room only, with
--     p_landmark null, is for an item in hand.
--   * Use times relative to now(), and pass real booleans for p_in_hand.
--   * Leave p_crop_url null unless a JPEG of our own staged objects is first uploaded to the private
--     crops bucket at that path (crops/<home>/<item>/<utc timestamp>.jpg). A path with no file
--     breaks photo signing. Never a photo of a real home or person.
-- =====================================================================

do $$
declare
  h          constant uuid := '11111111-1111-1111-1111-111111111111';
  t          constant timestamptz := now();
  glasses    uuid := (select id from items where home_id = h and name = 'glasses');
  keys       uuid := (select id from items where home_id = h and name = 'keys');
  bag        uuid := (select id from items where home_id = h and name = 'bag');
  nightstand uuid := (select landmark_id from places where home_id = h and landmark = 'nightstand');
  counter    uuid := (select landmark_id from places where home_id = h and landmark = 'counter');
  key_hook   uuid := (select landmark_id from places where home_id = h and landmark = 'key hook');
  desk       uuid := (select landmark_id from places where home_id = h and landmark = 'desk');
  hallway    uuid := (select id from rooms where home_id = h and name = 'hallway');
  bedroom    uuid := (select id from rooms where home_id = h and name = 'bedroom');
begin
  if exists (select 1 from observations where home_id = h and device_id <> 'dummy') then
    raise exception 'real camera data exists (observations from a device other than ''dummy''); not overwriting it. Run the rehearsal reset by hand if you really mean to.';
  end if;
  if num_nonnulls(glasses, keys, bag, nightstand, counter, key_hook, desk, hallway, bedroom) < 9 then
    raise exception 'the demo home is not seeded as supabase/seed.sql expects; run seed.sql first';
  end if;

  delete from queries      where home_id = h;
  delete from sightings    where home_id = h;
  delete from observations where home_id = h;

  -- glasses: on the nightstand 3 hours ago, then on the kitchen counter 40 minutes ago.
  -- Two frames 2 seconds apart make each stay active; the newer stay supersedes the older one.
  perform log_sighting(h, glasses, 'glasses', null, nightstand, 'on', false, t - interval '3 hours', 0.9, 0.9, 1.0);
  perform log_sighting(h, glasses, 'glasses', null, nightstand, 'on', false, t - interval '3 hours' + interval '2 seconds', 0.9, 0.9, 1.0);
  perform log_sighting(h, glasses, 'glasses', null, counter, 'on', false, t - interval '40 minutes', 0.9, 0.9, 1.0);
  perform log_sighting(h, glasses, 'glasses', null, counter, 'on', false, t - interval '40 minutes' + interval '2 seconds', 0.9, 0.9, 1.0);

  -- keys: on the key hook 5 hours ago, then in hand in the hallway 12 minutes ago
  -- (room only, no landmark), then the wearer walked into the bedroom.
  perform log_sighting(h, keys, 'keys', null, key_hook, 'on', false, t - interval '5 hours', 0.9, 0.9, 1.0);
  perform log_sighting(h, keys, 'keys', null, key_hook, 'on', false, t - interval '5 hours' + interval '2 seconds', 0.9, 0.9, 1.0);
  perform log_sighting(h, keys, 'keys', hallway, null, 'unknown', true, t - interval '12 minutes', 0.9, 0.9, 1.0);
  perform log_sighting(h, keys, 'keys', hallway, null, 'unknown', true, t - interval '12 minutes' + interval '2 seconds', 0.9, 0.9, 1.0);
  insert into observations (home_id, device_id, captured_at, room_id, room_conf, idempotency_key)
  values (h, 'dummy', t - interval '8 minutes', bedroom, 0.9, 'dummy:bedroom');

  -- bag: on the bedroom desk 2 hours ago, then the desk was seen empty three times, a minute apart.
  perform log_sighting(h, bag, 'bag', null, desk, 'on', false, t - interval '2 hours', 0.9, 0.9, 1.0);
  perform log_sighting(h, bag, 'bag', null, desk, 'on', false, t - interval '2 hours' + interval '2 seconds', 0.9, 0.9, 1.0);
  perform mark_absent(h, desk, t - interval '30 minutes', '{}');
  perform mark_absent(h, desk, t - interval '29 minutes', '{}');
  perform mark_absent(h, desk, t - interval '28 minutes', '{}');
end $$;

-- what the read path now answers
select i.name as item, f->>'state' as state, f->>'room' as room, f->>'landmark' as landmark,
       f->>'minutes_ago' as minutes_ago
  from items i cross join lateral find_item(i.home_id, i.name) f
 where i.home_id = '11111111-1111-1111-1111-111111111111'
 order by i.name;
