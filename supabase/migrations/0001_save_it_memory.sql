-- =====================================================================
-- Save It: external memory for the vision models  (Postgres 15+ / Supabase)
-- Tested on Postgres 16.16 + pgvector 0.8.7 on 14 Nov 2026 with test_memory.sql (75 checks; 82 with
-- the Supabase roles present). Applied to the Supabase project on 14 Nov 2026 as migration
-- save_it_memory. FROZEN from then on: schema changes go in 0002_*.sql.
--
-- Layers
--   1. Spatial index   homes > rooms > landmarks        typed in once at setup; changes rarely
--   2. Things          items + item_refs                what to look for, and what "mine" looks like
--   3. Episodic log    observations + sightings         append-only: what the camera saw, and when
--   4. Belief          item_last_seen, find_item()      derived from the log, never stored
--   5. Habits          item_usual_places                derived from the log
--   6. Feedback        queries                          what was asked, and whether the answer was right
--
-- Rules the functions enforce
--   * One glimpse is 'tentative'. A second agreeing frame (a different capture time) makes it 'active'.
--   * Only the newest 'active' row per item is the current belief; older ones become 'superseded'.
--   * Seeing an item again where it is already believed to be extends that stay (first_seen_at..last_seen_at).
--   * A landmark seen empty 3 times, at least 30 s apart, flips the row to 'contradicted' ("not there any more").
--   * A landmark decides its room. Nothing is ever written for a room with capture_allowed = false,
--     and a camera frame whose room is unknown is not written either.
--
-- Embeddings: use ONE image encoder everywhere and set its width below (768 = CLIP ViT-L/14).
-- With a few hundred rows no vector index is needed; exact search is instant.
-- =====================================================================

create extension if not exists vector;

-- ---------------------------------------------------------------------
-- 1. Spatial index: the home as an address book
-- ---------------------------------------------------------------------
create table homes (
  id          uuid primary key default gen_random_uuid(),
  person_name text not null,
  timezone    text not null default 'America/New_York',
  created_at  timestamptz not null default now()
);

create table rooms (
  id              uuid primary key default gen_random_uuid(),
  home_id         uuid not null references homes(id) on delete cascade,
  name            text not null,                 -- 'bedroom': the word the vision model must return
  spoken_name     text,                          -- 'your bedroom': the words the voice agent says
  floor           smallint,
  capture_allowed boolean not null default true, -- false for bathrooms: no sighting is ever stored
  splat_url       text,                          -- optional 3D scan of this room
  unique (home_id, name)
);

create table room_links (                        -- which rooms connect (reject impossible room jumps)
  room_a uuid not null references rooms(id) on delete cascade,
  room_b uuid not null references rooms(id) on delete cascade,
  primary key (room_a, room_b)
);

create table room_refs (                         -- "where am I?" index: 10-15 tour photos per room
  id        uuid primary key default gen_random_uuid(),
  room_id   uuid not null references rooms(id) on delete cascade,
  photo_url text,
  model     text not null,                       -- encoder that produced the embedding
  embedding vector(768) not null
);

create table landmarks (                         -- fixed furniture the person already knows
  id           uuid primary key default gen_random_uuid(),
  room_id      uuid not null references rooms(id) on delete cascade,
  parent_id    uuid references landmarks(id) on delete cascade,  -- 'top drawer' inside 'nightstand'
  name         text not null,                    -- 'nightstand': the word the vision model must return
  spoken_name  text,                             -- 'the table beside your bed'
  kind         text not null default 'surface'
               check (kind in ('surface','container','fixture','floor')),
  color        text,
  photo_url    text,
  point_prompt text,                             -- what a pointing model should look for: 'red kettle'
  model        text,
  embedding    vector(768),
  x real, y real, z real,                        -- optional pin position in the room's 3D scan
  unique (room_id, name)
);

create view places with (security_invoker = true) as                           -- every landmark as one readable address
select l.id as landmark_id, r.home_id, r.id as room_id,
       r.name as room, l.name as landmark, l.kind, r.capture_allowed,
       r.name || ' > ' || coalesce(p.name || ' > ', '') || l.name as address,
       coalesce(r.spoken_name, r.name) as room_spoken,
       coalesce(l.spoken_name, l.name) as landmark_spoken
from landmarks l
join rooms r on r.id = l.room_id
left join landmarks p on p.id = l.parent_id;

-- ---------------------------------------------------------------------
-- 2. Things: the short list of belongings worth remembering
-- ---------------------------------------------------------------------
create table items (
  id               uuid primary key default gen_random_uuid(),
  home_id          uuid not null references homes(id) on delete cascade,
  name             text not null,                -- 'glasses'
  aliases          text[] not null default '{}', -- {'specs','readers'}
  category         text not null,                -- detector prompt or class
  color            text,
  description      text,                         -- 'black reading glasses, round frames'
  plural           boolean not null default false, -- true for 'glasses', 'keys': the voice says "were", not "was"
  home_landmark_id uuid references landmarks(id) on delete set null,  -- where it belongs
  unique (home_id, name)
);

create table item_refs (                         -- "whose keys are these?" index: 3-5 photos per item
  id        uuid primary key default gen_random_uuid(),
  item_id   uuid not null references items(id) on delete cascade,
  crop_url  text,
  in_situ   boolean not null default false,      -- photographed in its usual place
  model     text not null,
  embedding vector(768) not null
);

-- ---------------------------------------------------------------------
-- 3. Episodic log
-- ---------------------------------------------------------------------
create table observations (                      -- one row per processed keyframe: text only, no image
  id              uuid primary key default gen_random_uuid(),
  home_id         uuid not null references homes(id) on delete cascade,
  device_id       text not null,
  captured_at     timestamptz not null,
  room_id         uuid references rooms(id) on delete set null,
  room_conf       real,
  landmarks_seen  uuid[] not null default '{}',
  source          text not null default 'worn_cam'
                  check (source in ('worn_cam','facetime_caller','tour','manual')),
  perceived_by    text,                          -- exact model IDs used
  idempotency_key text not null,                 -- device_id + frame timestamp: retries cannot double-log
  unique (home_id, idempotency_key)
);
create index on observations (home_id, captured_at desc);

create table sightings (                         -- one row per stay of an item at a place
  id              uuid primary key default gen_random_uuid(),
  home_id         uuid not null references homes(id) on delete cascade,
  item_id         uuid references items(id) on delete cascade,  -- null = "some keys", owner unresolved
  label           text not null,                 -- raw detector label
  room_id         uuid references rooms(id) on delete set null,
  landmark_id     uuid references landmarks(id) on delete set null,
  relation        text not null default 'unknown'
                  check (relation in ('on','in','under','next_to','unknown')),
  in_hand         boolean not null default false,
  description     text,
  first_seen_at   timestamptz not null,
  last_seen_at    timestamptz not null,
  n_frames        int not null default 1,
  absent_count    int not null default 0,        -- times the landmark was seen without the item
  last_absent_at  timestamptz,                   -- when the last counted empty look happened
  status          text not null default 'tentative'
                  check (status in ('tentative','active','superseded','contradicted')),
  event_type      text not null default 'seen'
                  check (event_type in ('seen','placed','told','confirmed_live')),
  source          text not null default 'worn_cam'
                  check (source in ('worn_cam','facetime_caller','tour','manual','live_hint')),
  contradicted_at timestamptz,
  det_conf real, room_conf real, id_conf real,   -- kept separate so the agent can hedge honestly
  crop_url        text,                          -- tight crop only; never the full frame
  point           jsonb,                         -- {"x":0.42,"y":0.71}, 0-1, top-left origin
  last_observation_id uuid references observations(id) on delete set null,
  embedding       vector(768),
  fts tsvector generated always as
      (to_tsvector('english'::regconfig, coalesce(label,'') || ' ' || coalesce(description,''))) stored
);
create index on sightings (item_id, last_seen_at desc);
create index on sightings (home_id, last_seen_at desc);
create index on sightings (landmark_id) where status = 'active';
create index on sightings using gin (fts);

-- Privacy backstop: a row that would place anything in a room with capture_allowed = false is
-- silently dropped, whoever writes it. Checks the row's room and the rooms of its landmarks.
create or replace function drop_no_capture() returns trigger language plpgsql
  set search_path = public, pg_temp as $$
declare
  lms uuid[];
begin
  if tg_table_name = 'sightings' then
    lms := array[new.landmark_id];
  else
    lms := new.landmarks_seen;
  end if;
  if exists (select 1 from rooms r
              where not r.capture_allowed
                and (r.id = new.room_id
                     or r.id in (select l.room_id from landmarks l where l.id = any (lms)))) then
    return null;
  end if;
  return new;
end $$;

create trigger observations_drop_no_capture
  before insert or update of room_id, landmarks_seen on observations
  for each row execute function drop_no_capture();
create trigger sightings_drop_no_capture
  before insert or update of room_id, landmark_id on sightings
  for each row execute function drop_no_capture();

-- ---------------------------------------------------------------------
-- 6. Feedback: every question, and whether the answer was right
-- ---------------------------------------------------------------------
create table queries (
  id          uuid primary key default gen_random_uuid(),
  home_id     uuid not null references homes(id) on delete cascade,
  asked_at    timestamptz not null default now(),
  channel     text not null check (channel in ('phone','facetime','web')),
  heard       text not null,                     -- what speech-to-text produced
  item_id     uuid references items(id) on delete set null,
  sighting_id uuid references sightings(id) on delete set null,
  state       text,                              -- the state find_item returned
  outcome     text check (outcome in ('found','not_found')),
  outcome_at  timestamptz
);

-- ---------------------------------------------------------------------
-- 4 and 5. Belief and habits: views over the log
-- ---------------------------------------------------------------------
create view item_last_seen with (security_invoker = true) as                   -- current belief per item
select distinct on (s.item_id)
  s.home_id, s.item_id, i.name as item, s.id as sighting_id,
  s.status, s.in_hand, s.relation, s.event_type,
  s.room_id, s.landmark_id, pl.address,
  coalesce(r.spoken_name, r.name) as room_spoken, pl.landmark_spoken,
  s.first_seen_at, s.last_seen_at,
  round(extract(epoch from now() - s.last_seen_at) / 60)::int as minutes_ago,
  s.crop_url, l.x, l.y, l.z
from sightings s
join items i on i.id = s.item_id
left join rooms r on r.id = s.room_id
left join landmarks l on l.id = s.landmark_id
left join places pl on pl.landmark_id = s.landmark_id
where s.status in ('active','contradicted')      -- a tentative glimpse never answers on its own
order by s.item_id, s.last_seen_at desc;

create view item_usual_places with (security_invoker = true) as                -- "they're usually on your nightstand"
select s.item_id, s.landmark_id, count(*) as episodes,
       round(100.0 * count(*) / sum(count(*)) over (partition by s.item_id))::int as pct,
       max(s.last_seen_at) as last_seen_at
from sightings s
where s.item_id is not null and s.landmark_id is not null
  and s.status <> 'tentative' and not s.in_hand
group by s.item_id, s.landmark_id;

create view timeline with (security_invoker = true) as                         -- caregiver view and the 3D time slider
select s.home_id, s.item_id, i.name as item, s.id as sighting_id,
       s.event_type, s.status, s.in_hand, s.first_seen_at, s.last_seen_at,
       coalesce(pl.address, r.name) as address, s.crop_url, l.x, l.y, l.z
from sightings s
left join items i on i.id = s.item_id
left join rooms r on r.id = s.room_id
left join landmarks l on l.id = s.landmark_id
left join places pl on pl.landmark_id = s.landmark_id
where s.status <> 'tentative';

-- ---------------------------------------------------------------------
-- Write path 1: log one detection. Merges into an episode, applies the two-frame rule,
-- and keeps exactly one 'active' row per item.
-- The room is the landmark's room when a landmark is given. Raises 22023 when p_room disagrees
-- with the landmark, or when the room or landmark is not in this home.
-- Returns null and stores nothing for a no-capture room, or for a camera frame with no room.
-- ---------------------------------------------------------------------
create or replace function log_sighting(
  p_home uuid, p_item uuid, p_label text,
  p_room uuid, p_landmark uuid, p_relation text, p_in_hand boolean,
  p_seen_at timestamptz,
  p_det_conf real default null, p_room_conf real default null, p_id_conf real default null,
  p_crop_url text default null, p_description text default null,
  p_observation uuid default null,
  p_event text default 'seen', p_source text default 'worn_cam'
) returns uuid language plpgsql
  set search_path = public, pg_temp as $$
declare
  ep      sightings;
  v_room  uuid := p_room;
  allowed boolean;
begin
  if p_landmark is not null then                 -- the landmark decides the room
    select l.room_id into v_room
      from landmarks l join rooms r on r.id = l.room_id
     where l.id = p_landmark and r.home_id = p_home;
    if not found then
      raise exception 'landmark % is not in home %', p_landmark, p_home using errcode = '22023';
    end if;
    if p_room is not null and p_room <> v_room then
      raise exception 'landmark % is in room %, not in room %', p_landmark, v_room, p_room
        using errcode = '22023';
    end if;
  end if;

  if v_room is null then
    if p_source in ('worn_cam', 'facetime_caller') then
      return null;                               -- privacy fails closed: a camera frame from an unknown room
    end if;
  else
    select capture_allowed into allowed from rooms where id = v_room and home_id = p_home;
    if not found then
      raise exception 'room % is not in home %', v_room, p_home using errcode = '22023';
    end if;
    if not allowed then
      return null;                               -- privacy: nothing is stored for this room
    end if;
  end if;

  perform pg_advisory_xact_lock(hashtext(coalesce(p_item::text, p_label)));

  select * into ep from sightings
   where home_id = p_home
     and item_id is not distinct from p_item
     and (p_item is not null or label = p_label)
     and status in ('tentative','active')
     and room_id is not distinct from v_room
     and landmark_id is not distinct from p_landmark
     and in_hand = p_in_hand
     and (   (status = 'active' and not in_hand                 -- still where we believe it is:
              and p_seen_at >= first_seen_at - interval '10 minutes')   -- same stay, any gap
          or (last_seen_at  >= p_seen_at - interval '10 minutes'       -- otherwise frames must be
              and first_seen_at <= p_seen_at + interval '10 minutes')) -- within 10 minutes
   order by last_seen_at desc
   limit 1;

  if found then                                  -- same place again: extend the episode
    if p_seen_at = ep.first_seen_at or p_seen_at = ep.last_seen_at then
      return ep.id;                              -- the same frame sent twice is not a second agreeing frame
    end if;
    update sightings set
      first_seen_at = least(first_seen_at, p_seen_at),
      last_seen_at  = greatest(last_seen_at, p_seen_at),
      n_frames      = n_frames + 1,
      absent_count  = 0,
      last_absent_at = null,
      status        = 'active',                  -- second agreeing frame confirms it
      event_type    = case when p_event <> 'seen' then p_event else event_type end,
      relation      = case when p_relation <> 'unknown' then p_relation else relation end,
      crop_url      = case when p_crop_url is not null
                            and coalesce(p_det_conf, 0) >= coalesce(det_conf, 0)
                           then p_crop_url else crop_url end,
      description   = coalesce(p_description, description),
      det_conf      = greatest(det_conf, p_det_conf),
      room_conf     = greatest(room_conf, p_room_conf),
      id_conf       = greatest(id_conf, p_id_conf),
      last_observation_id = coalesce(p_observation, last_observation_id)
    where id = ep.id
    returning * into ep;
  else                                           -- new place: open an episode
    insert into sightings (home_id, item_id, label, room_id, landmark_id, relation, in_hand,
                           description, first_seen_at, last_seen_at, status, event_type, source,
                           det_conf, room_conf, id_conf, crop_url, last_observation_id)
    values (p_home, p_item, p_label, v_room, p_landmark, coalesce(p_relation, 'unknown'), p_in_hand,
            p_description, p_seen_at, p_seen_at,
            case when p_event in ('told','confirmed_live') then 'active' else 'tentative' end,
            p_event, p_source, p_det_conf, p_room_conf, p_id_conf, p_crop_url, p_observation)
    returning * into ep;
  end if;

  if ep.status = 'active' and ep.item_id is not null then
    update sightings s set status = 'superseded'
     where s.item_id = ep.item_id and s.status = 'active'
       and s.id <> (select id from sightings
                     where item_id = ep.item_id and status = 'active'
                     order by last_seen_at desc, first_seen_at desc limit 1);
  end if;

  return ep.id;
end $$;

-- ---------------------------------------------------------------------
-- Write path 2: the camera looked at a landmark and these items were (not) there.
-- An empty look counts only if it is at least p_min_gap after the last counted one, so a burst
-- of frames in one glance is one look. Returns how many sightings flipped to 'contradicted'.
-- ---------------------------------------------------------------------
create or replace function mark_absent(
  p_home uuid, p_landmark uuid, p_seen_at timestamptz,
  p_visible uuid[] default '{}', p_needed int default 3, p_min_gap interval default '30 seconds'
) returns int language plpgsql
  set search_path = public, pg_temp as $$
declare
  flipped int;
begin
  with hit as (
    update sightings set
      absent_count    = absent_count + 1,
      last_absent_at  = p_seen_at,
      status          = case when absent_count + 1 >= p_needed then 'contradicted' else status end,
      contradicted_at = case when absent_count + 1 >= p_needed then p_seen_at else contradicted_at end
    where home_id = p_home and landmark_id = p_landmark
      and status = 'active' and in_hand = false
      and last_seen_at < p_seen_at
      and (last_absent_at is null or p_seen_at >= last_absent_at + p_min_gap)
      and item_id is not null and item_id <> all (p_visible)
    returning status
  )
  select count(*) filter (where status = 'contradicted') into flipped from hit;
  return flipped;
end $$;

-- ---------------------------------------------------------------------
-- Read path 1: what the voice agent calls. One query, structured answer.
-- state: seen | carried | not_there_anymore | never_seen | unknown_item
-- ---------------------------------------------------------------------
create or replace function find_item(p_home uuid, p_query text) returns jsonb
language plpgsql stable
  set search_path = public, pg_temp as $$
declare
  q         text := regexp_replace(lower(trim(p_query)), '^(my|the|a|some|her|his)\s+', '');
  it        items;
  tz        text;
  cur       record;
  has_cur   boolean;
  ruled_out uuid;                                -- the landmark this answer has just ruled out
  j_prev    jsonb;
  j_usual   jsonb;
  last_room text;
  newer     boolean;
begin
  select * into it from items
   where home_id = p_home
     and (lower(name) = q or q = any (select lower(a) from unnest(aliases) a))
   limit 1;
  if not found then
    return jsonb_build_object('state', 'unknown_item', 'heard', p_query);
  end if;
  select timezone into tz from homes where id = p_home;

  select s.id, s.status, s.in_hand, s.relation, s.event_type, s.last_seen_at, s.crop_url,
         s.landmark_id, pl.address, pl.landmark_spoken,
         coalesce(r.spoken_name, r.name) as room_spoken,
         round(extract(epoch from now() - s.last_seen_at) / 60)::int as minutes_ago,
         coalesce(s.det_conf, 1) * coalesce(s.room_conf, 1) * coalesce(s.id_conf, 1) as conf
    into cur
    from sightings s
    left join rooms r on r.id = s.room_id
    left join places pl on pl.landmark_id = s.landmark_id
   where s.item_id = it.id and s.status in ('active','contradicted')
   order by s.last_seen_at desc limit 1;
  has_cur := found;
  if has_cur and cur.status = 'contradicted' then
    ruled_out := cur.landmark_id;
  end if;

  -- Usual place: a habit needs at least 2 settled stays at one place; otherwise use where the
  -- family says it belongs. Never offer the place this answer has just ruled out.
  select jsonb_build_object('room', pl.room_spoken, 'landmark', pl.landmark_spoken, 'pct', u.pct)
    into j_usual
    from item_usual_places u join places pl on pl.landmark_id = u.landmark_id
   where u.item_id = it.id and u.episodes >= 2
     and u.landmark_id is distinct from ruled_out
   order by u.episodes desc, u.last_seen_at desc limit 1;

  if j_usual is null then
    select jsonb_build_object('room', pl.room_spoken, 'landmark', pl.landmark_spoken, 'pct', null)
      into j_usual from places pl
     where pl.landmark_id = it.home_landmark_id
       and pl.landmark_id is distinct from ruled_out;
  end if;

  if not has_cur then
    return jsonb_build_object(
      'state', 'never_seen', 'item', it.name, 'plural', it.plural, 'usual', j_usual, 'timezone', tz,
      'possible_glimpse', exists (select 1 from sightings where item_id = it.id and status = 'tentative'));
  end if;

  select jsonb_build_object('room', coalesce(r.spoken_name, r.name), 'landmark', pl.landmark_spoken,
           'minutes_ago', round(extract(epoch from now() - s.last_seen_at) / 60)::int)
    into j_prev
    from sightings s
    left join rooms r on r.id = s.room_id
    left join places pl on pl.landmark_id = s.landmark_id
   where s.item_id = it.id and s.id <> cur.id and s.status <> 'tentative' and not s.in_hand
     and s.landmark_id is distinct from cur.landmark_id
     and s.last_seen_at <= cur.last_seen_at
   order by s.last_seen_at desc limit 1;

  select coalesce(r.spoken_name, r.name) into last_room   -- where the wearer went afterwards
    from observations o join rooms r on r.id = o.room_id
   where o.home_id = p_home and o.captured_at > cur.last_seen_at
   order by o.captured_at desc limit 1;

  newer := exists (select 1 from sightings
                    where item_id = it.id and status = 'tentative' and last_seen_at > cur.last_seen_at);

  return jsonb_build_object(
    'state', case when cur.status = 'contradicted' then 'not_there_anymore'
                  when cur.in_hand then 'carried' else 'seen' end,
    'item', it.name, 'plural', it.plural, 'sighting_id', cur.id,
    'room', cur.room_spoken, 'landmark', cur.landmark_spoken, 'relation', cur.relation,
    'address', cur.address, 'minutes_ago', cur.minutes_ago,
    'last_seen_at', to_char(cur.last_seen_at at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
    'timezone', tz,
    'confident', cur.conf >= 0.5, 'photo', cur.crop_url,
    'previous', j_prev, 'usual', j_usual,
    'wearer_went_to', last_room, 'possible_newer_glimpse', newer);
end $$;

-- ---------------------------------------------------------------------
-- Read path 1b: what the voice tools call. Answers exactly like find_item and logs the question
-- in the same call, so the read path stays one round trip and record_outcome has a row to update.
-- Returns the find_item answer plus query_id.
-- ---------------------------------------------------------------------
create or replace function ask_item(p_home uuid, p_query text, p_channel text) returns jsonb
language plpgsql
  set search_path = public, pg_temp as $$
declare
  ans jsonb := find_item(p_home, p_query);
  qid uuid;
begin
  insert into queries (home_id, channel, heard, item_id, sighting_id, state)
  values (p_home, p_channel, p_query,
          (select id from items where home_id = p_home and name = ans->>'item'),
          (ans->>'sighting_id')::uuid, ans->>'state')
  returning id into qid;
  return ans || jsonb_build_object('query_id', qid);
end $$;

-- ---------------------------------------------------------------------
-- Read path 2: what the vision model is shown before it looks at a frame.
-- It may only answer with these rooms, landmarks and items, and it sees the current beliefs.
-- ---------------------------------------------------------------------
create or replace function perception_context(p_home uuid, p_room uuid default null) returns jsonb
language sql stable
  set search_path = public, pg_temp as $$
  select jsonb_build_object(
    'rooms', (select jsonb_agg(name order by name) from rooms where home_id = p_home),
    'landmarks', (
      select jsonb_agg(jsonb_build_object('room', room, 'landmark', landmark, 'kind', kind)
                       order by room, landmark)
        from places
       where home_id = p_home and capture_allowed
         and (p_room is null or room_id = p_room
              or room_id in (select room_b from room_links where room_a = p_room
                             union select room_a from room_links where room_b = p_room))),
    'items', (
      select jsonb_agg(jsonb_build_object('item', name, 'looks_like', concat_ws(', ', color, description))
                       order by name)
        from items where home_id = p_home),
    'beliefs', (
      select jsonb_agg(jsonb_build_object('item', item, 'address', address, 'in_hand', in_hand,
                                          'status', status, 'minutes_ago', minutes_ago))
        from item_last_seen where home_id = p_home));
$$;

-- ---------------------------------------------------------------------
-- Feedback and retention
-- ---------------------------------------------------------------------
create or replace function record_outcome(p_query uuid, p_found boolean) returns void
language plpgsql
  set search_path = public, pg_temp as $$
declare
  sid uuid;
begin
  update queries
     set outcome = case when p_found then 'found' else 'not_found' end, outcome_at = now()
   where id = p_query
   returning sighting_id into sid;
  if not p_found and sid is not null then        -- "it wasn't there": stop repeating that answer
    update sightings set status = 'contradicted', contradicted_at = now()
     where id = sid and status = 'active';
  end if;
end $$;

create or replace function purge_old(p_home uuid, p_keep interval default '7 days') returns void
language sql
  set search_path = public, pg_temp as $$
  delete from observations where home_id = p_home and captured_at < now() - p_keep;
  delete from sightings where home_id = p_home and status = 'tentative'
                          and last_seen_at < now() - p_keep;
  update sightings set crop_url = null, description = null, embedding = null, point = null
   where home_id = p_home and last_seen_at < now() - p_keep;   -- photos expire; the habit fact stays
$$;

-- ---------------------------------------------------------------------
-- Security. Row level security on, with no policies: only the backend's secret key (sb_secret_...,
-- role service_role, which bypasses RLS) reads or writes. Grants are at the end of this file.
-- Never commit keys to the repo.
-- ---------------------------------------------------------------------
alter table homes        enable row level security;
alter table rooms        enable row level security;
alter table room_links   enable row level security;
alter table room_refs    enable row level security;
alter table landmarks    enable row level security;
alter table items        enable row level security;
alter table item_refs    enable row level security;
alter table observations enable row level security;
alter table sightings    enable row level security;
alter table queries      enable row level security;

do $$ begin                                      -- live pins and caregiver timeline (Supabase only)
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    alter publication supabase_realtime add table sightings;
  end if;
end $$;

-- ---------------------------------------------------------------------
-- The two embedding lookups, as functions so the worker can call them through Supabase RPC.
-- ---------------------------------------------------------------------
-- "Where am I?"  vote among the k nearest tour photos. First row is the winner.
create or replace function match_room(p_home uuid, p_embedding vector(768), p_k int default 11)
returns table (room_id uuid, room text, votes int, best_similarity real)
language sql stable
  set search_path = public, pg_temp as $$
  select t.room_id, t.name, count(*)::int, max(t.sim)::real
    from (select rr.room_id, r.name, 1 - (rr.embedding <=> p_embedding) as sim
            from room_refs rr join rooms r on r.id = rr.room_id
           where r.home_id = p_home
           order by rr.embedding <=> p_embedding
           limit p_k) t
   group by t.room_id, t.name
   order by 3 desc, 4 desc;
$$;

-- "Whose keys are these?"  best single reference photo per item, same category only.
-- The caller applies the threshold; below it, log the sighting with item_id = null.
create or replace function match_item(p_home uuid, p_category text, p_embedding vector(768))
returns table (item_id uuid, item text, similarity real)
language sql stable
  set search_path = public, pg_temp as $$
  select i.id, i.name, max(1 - (ir.embedding <=> p_embedding))::real
    from item_refs ir join items i on i.id = ir.item_id
   where i.home_id = p_home and i.category = p_category
   group by i.id, i.name
   order by 3 desc;
$$;

-- ---------------------------------------------------------------------
-- API grants (Supabase only; skipped where the Supabase roles do not exist, as on scratch Postgres).
-- Only the backend's secret key (role service_role) reaches these objects. The publishable key
-- (anon) and signed-in users (authenticated) get nothing. Supabase is moving to opt-in grants,
-- so service_role is granted explicitly. https://supabase.com/docs/guides/api/securing-your-api
-- The vector extension's own functions are left alone.
-- ---------------------------------------------------------------------
do $$ begin
  if exists (select 1 from pg_roles where rolname = 'service_role') then
    revoke all on table homes, rooms, room_links, room_refs, landmarks, items, item_refs,
                        observations, sightings, queries,
                        places, item_last_seen, item_usual_places, timeline
      from anon, authenticated, service_role;
    revoke execute on function log_sighting, mark_absent, find_item, ask_item, perception_context,
                               record_outcome, purge_old, match_room, match_item, drop_no_capture
      from public, anon, authenticated, service_role;

    grant usage on schema public to service_role;
    grant select, insert, update, delete on table homes, rooms, room_links, room_refs, landmarks,
                                                  items, item_refs, observations, sightings, queries
      to service_role;
    grant select on table places, item_last_seen, item_usual_places, timeline to service_role;
    grant execute on function log_sighting, mark_absent, find_item, ask_item, perception_context,
                              record_outcome, purge_old, match_room, match_item
      to service_role;                           -- drop_no_capture is a trigger: nobody calls it
  end if;
end $$;
