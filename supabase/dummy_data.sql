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
-- Afterwards find_item gives (the B School classroom home in seed.sql):
--   glasses       seen               on the chair, about 40 minutes ago; previous: the table
--   keys          carried            in hand in the classroom 12 minutes ago; wearer_went_to is null
--                                    (the only other room is the no-capture bathroom)
--   bag           not_there_anymore  last on the floor 2 hours ago, seen empty 3 times since;
--                                    usual is null (the bag has no home landmark)
--   water bottle  seen, not confident  next to the table 5 minutes ago ("I think I saw ...")
--   watch         never_seen         no sighting at all
--   umbrella      unknown_item       (any word that is not an item name or alias)
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
  bottle     uuid := (select id from items where home_id = h and name = 'water bottle');
  tbl        uuid := (select landmark_id from places where home_id = h and landmark = 'table');
  chair      uuid := (select landmark_id from places where home_id = h and landmark = 'chair');
  floor_     uuid := (select landmark_id from places where home_id = h and landmark = 'floor');
  classroom  uuid := (select id from rooms where home_id = h and name = 'b_school_classroom');
begin
  if exists (select 1 from observations where home_id = h and device_id <> 'dummy') then
    raise exception 'real camera data exists (observations from a device other than ''dummy''); not overwriting it. Run the rehearsal reset by hand if you really mean to.';
  end if;
  if num_nonnulls(glasses, keys, bag, bottle, tbl, chair, floor_, classroom) < 8 then
    raise exception 'the demo home is not seeded as supabase/seed.sql expects; run seed.sql first';
  end if;

  delete from queries      where home_id = h;
  delete from sightings    where home_id = h;
  delete from observations where home_id = h;

  -- glasses: on the table (their usual place) 3 hours ago, then on the chair 40 minutes ago.
  -- Two frames 2 seconds apart make each stay active; the newer stay supersedes the older one.
  perform log_sighting(h, glasses, 'glasses', null, tbl, 'on', false, t - interval '3 hours', 0.9, 0.9, 1.0);
  perform log_sighting(h, glasses, 'glasses', null, tbl, 'on', false, t - interval '3 hours' + interval '2 seconds', 0.9, 0.9, 1.0);
  perform log_sighting(h, glasses, 'glasses', null, chair, 'on', false, t - interval '40 minutes', 0.9, 0.9, 1.0);
  perform log_sighting(h, glasses, 'glasses', null, chair, 'on', false, t - interval '40 minutes' + interval '2 seconds', 0.9, 0.9, 1.0);

  -- keys: on the table 5 hours ago, then in hand in the classroom 12 minutes ago (room only).
  perform log_sighting(h, keys, 'keys', null, tbl, 'on', false, t - interval '5 hours', 0.9, 0.9, 1.0);
  perform log_sighting(h, keys, 'keys', null, tbl, 'on', false, t - interval '5 hours' + interval '2 seconds', 0.9, 0.9, 1.0);
  perform log_sighting(h, keys, 'keys', classroom, null, 'unknown', true, t - interval '12 minutes', 0.9, 0.9, 1.0);
  perform log_sighting(h, keys, 'keys', classroom, null, 'unknown', true, t - interval '12 minutes' + interval '2 seconds', 0.9, 0.9, 1.0);

  -- bag: on the floor 2 hours ago, then the floor was seen empty three times, a minute apart.
  perform log_sighting(h, bag, 'bag', null, floor_, 'on', false, t - interval '2 hours', 0.9, 0.9, 1.0);
  perform log_sighting(h, bag, 'bag', null, floor_, 'on', false, t - interval '2 hours' + interval '2 seconds', 0.9, 0.9, 1.0);
  perform mark_absent(h, floor_, t - interval '30 minutes', '{}');
  perform mark_absent(h, floor_, t - interval '29 minutes', '{}');
  perform mark_absent(h, floor_, t - interval '28 minutes', '{}');

  -- water bottle: next to the table 5 minutes ago, with a weak detection (0.5 x 0.9 x 1.0 is under
  -- the 0.5 cut), so find_item says confident = false and the voice starts with "I think".
  perform log_sighting(h, bottle, 'water bottle', null, tbl, 'next_to', false, t - interval '5 minutes', 0.5, 0.9, 1.0);
  perform log_sighting(h, bottle, 'water bottle', null, tbl, 'next_to', false, t - interval '5 minutes' + interval '2 seconds', 0.5, 0.9, 1.0);

  -- watch: nothing, so it stays never_seen.
end $$;

-- what the read path now answers
select i.name as item, f->>'state' as state, f->>'room' as room, f->>'landmark' as landmark,
       f->>'minutes_ago' as minutes_ago
  from items i cross join lateral find_item(i.home_id, i.name) f
 where i.home_id = '11111111-1111-1111-1111-111111111111'
 order by i.name;
