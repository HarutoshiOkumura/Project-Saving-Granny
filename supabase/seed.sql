-- Demo home for Save It: the B School classroom at Emory Hacks, as seeded on Supabase on 14 Nov 2026
-- (D1, D2). One room to find things in, plus a no-capture bathroom corner for the privacy demo.
-- Run after the migrations. Safe to re-run: it keeps the home row and replaces this home's rooms,
-- landmarks and items, and it refuses while any sighting or observation exists (rehearsal reset first).
--
-- `name` is the word the vision model must return. `spoken_name` is what the voice says.
-- Keep names short, lower-case and unlike each other. Every name here becomes an allowed answer.
-- In fixture file names, write names with hyphens instead of spaces or underscores
-- (close_water-bottle_table_01.jpg, empty_b-school-classroom_01.jpg).
-- The home id is fixed so you can put it in .env as HOME_ID.

insert into homes (id, person_name, timezone)
values ('11111111-1111-1111-1111-111111111111', 'Grandma', 'America/New_York')
on conflict (id) do nothing;

-- Re-seeding replaces rooms, landmarks and items, so it must not run under logged data.
do $$
begin
  if exists (select 1 from sightings where home_id = '11111111-1111-1111-1111-111111111111')
     or exists (select 1 from observations where home_id = '11111111-1111-1111-1111-111111111111') then
    raise exception 'sightings or observations exist for the demo home; run the rehearsal reset first (docs/SUPABASE.md section 8)';
  end if;
end $$;
delete from items where home_id = '11111111-1111-1111-1111-111111111111';
delete from rooms where home_id = '11111111-1111-1111-1111-111111111111';   -- landmarks and room_links cascade

insert into rooms (home_id, name, spoken_name, floor, capture_allowed) values
  ('11111111-1111-1111-1111-111111111111', 'b_school_classroom', 'the classroom', 1, true),
  ('11111111-1111-1111-1111-111111111111', 'bathroom',           'the bathroom',  1, false);   -- nothing is ever stored here

-- which rooms connect
insert into room_links (room_a, room_b)
select a.id, b.id
  from rooms a join rooms b on b.home_id = a.home_id
 where a.home_id = '11111111-1111-1111-1111-111111111111'
   and (a.name, b.name) in (('b_school_classroom', 'bathroom'));

-- the staged furniture. kind: surface | container | fixture | floor
-- A classroom has many tables and chairs: stage one of each and keep the others out of frame.
insert into landmarks (room_id, name, spoken_name, kind, point_prompt)
select r.id, v.name, v.spoken_name, v.kind, v.point_prompt
  from (values
    ('b_school_classroom', 'table', 'the table', 'surface', 'classroom table'),
    ('b_school_classroom', 'chair', 'the chair', 'surface', 'classroom chair'),
    ('b_school_classroom', 'floor', 'the floor', 'floor',   'carpet floor')
  ) as v(room, name, spoken_name, kind, point_prompt)
  join rooms r on r.name = v.room and r.home_id = '11111111-1111-1111-1111-111111111111';

-- belongings worth remembering. category = the detector class name (must match the Roboflow class).
-- plural = true when the voice should say "they" (glasses, keys).
-- usual_landmark null = nobody has said where it belongs. The glasses live on the table, so the
-- demo puts them somewhere else and the "not there anymore" answer can offer the table.
insert into items (home_id, name, aliases, category, color, description, plural, home_landmark_id)
select '11111111-1111-1111-1111-111111111111', v.name, v.aliases::text[], v.category, v.color, v.description, v.plural,
       (select landmark_id from places
         where home_id = '11111111-1111-1111-1111-111111111111' and landmark = v.usual_landmark)
  from (values
    ('glasses',      '{specs,spectacles,readers,"reading glasses",eyeglasses}',                                    'glasses', 'black',     'black reading glasses',                          true,  'table'),
    ('keys',         '{key,"house keys","door keys"}',                                                              'keys',    'black',     'car key fob with a few keys on a ring',          true,  'table'),
    ('bag',          '{"green bag",handbag,"hand bag",purse,"franzi bag","milano bag","franzi milano bag"}',        'bag',     'green',     'green handbag with gold lettering (FRANZI Milano)', false, null),
    ('watch',        '{wristwatch,"wrist watch","silver watch"}',                                                   'watch',   'silver',    'silver wristwatch',                              false, null),
    ('water bottle', '{bottle,"blue bottle","blue water bottle","drink bottle",flask,water}',                       'bottle',  'dark blue', 'dark blue water bottle',                         false, null)
  ) as v(name, aliases, category, color, description, plural, usual_landmark);

-- check
select address, landmark_spoken from places order by address;
select name, aliases, category, home_landmark_id is not null as has_usual_place from items order by name;
