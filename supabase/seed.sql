-- Demo home for Save It, as seeded on the Supabase project in step 01 (14 Nov 2026).
-- Started from seed.example.sql (D1, D2 defaults), plus a desk in the bedroom and the green bag.
-- Run after 0001_save_it_memory.sql. Safe to run once on an empty set of tables.
--
-- `name` is the word the vision model must return. `spoken_name` is what the voice says.
-- Keep names short, lower-case and unlike each other. Every name here becomes an allowed answer.
-- The home id is fixed so you can put it in .env as HOME_ID.

insert into homes (id, person_name, timezone)
values ('11111111-1111-1111-1111-111111111111', 'Grandma', 'America/New_York');

insert into rooms (home_id, name, spoken_name, floor, capture_allowed) values
  ('11111111-1111-1111-1111-111111111111', 'bedroom',  'your bedroom',  1, true),
  ('11111111-1111-1111-1111-111111111111', 'kitchen',  'the kitchen',   1, true),
  ('11111111-1111-1111-1111-111111111111', 'hallway',  'the hallway',   1, true),
  ('11111111-1111-1111-1111-111111111111', 'bathroom', 'the bathroom',  1, false);   -- nothing is ever stored here

-- which rooms connect
insert into room_links (room_a, room_b)
select a.id, b.id
  from rooms a join rooms b on b.home_id = a.home_id
 where a.home_id = '11111111-1111-1111-1111-111111111111'
   and (a.name, b.name) in (('hallway','bedroom'), ('hallway','kitchen'), ('hallway','bathroom'));

-- fixed furniture the person already knows. kind: surface | container | fixture | floor
insert into landmarks (room_id, name, spoken_name, kind, point_prompt)
select r.id, v.name, v.spoken_name, v.kind, v.point_prompt
  from (values
    ('bedroom', 'nightstand', 'the table beside your bed',   'surface', 'small table next to the bed'),
    ('bedroom', 'dresser',    'the dresser',                 'surface', 'chest of drawers'),
    ('bedroom', 'desk',       'the desk in your bedroom',    'surface', 'writing desk'),
    ('kitchen', 'counter',    'the kitchen counter',         'surface', 'kitchen counter'),
    ('kitchen', 'table',      'the kitchen table',           'surface', 'dining table'),
    ('hallway', 'key hook',   'the hook by the front door',  'fixture', 'wall hook by the door'),
    ('hallway', 'shoe shelf', 'the shelf by the front door', 'surface', 'low shelf by the door')
  ) as v(room, name, spoken_name, kind, point_prompt)
  join rooms r on r.name = v.room and r.home_id = '11111111-1111-1111-1111-111111111111';

-- belongings worth remembering. category = the detector class name (must match the Roboflow class).
-- plural = true when the voice should say "were" (glasses, keys).
-- usual_landmark null = nobody has said where it belongs yet.
insert into items (home_id, name, aliases, category, color, description, plural, home_landmark_id)
select '11111111-1111-1111-1111-111111111111', v.name, v.aliases::text[], v.category, v.color, v.description, v.plural,
       (select landmark_id from places
         where home_id = '11111111-1111-1111-1111-111111111111' and landmark = v.usual_landmark)
  from (values
    ('glasses', '{specs,spectacles,readers,"reading glasses",eyeglasses}',               'glasses', 'black',  'black reading glasses',     true,  'nightstand'),
    ('keys',    '{key,"house keys","door keys"}',                                        'keys',    'orange', 'keys on an orange lanyard', true,  'key hook'),
    ('bag',     '{"green bag",handbag,purse,"franzi bag","milano bag","franzi milano bag"}', 'bag', 'green',  'FRANZI Milano green bag',   false, null)
  ) as v(name, aliases, category, color, description, plural, usual_landmark);

-- check
select address, landmark_spoken from places order by address;
select name, aliases, category, home_landmark_id is not null as has_usual_place from items order by name;
