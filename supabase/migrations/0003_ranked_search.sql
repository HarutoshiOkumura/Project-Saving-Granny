-- =====================================================================
-- 0003: ranked "where to look next", on top of 0001. Additive only: no 0001 table or function changes.
-- Tested on Postgres 16 with supabase/tests/test_ranking.sql (runs alone or after test_memory.sql).
--
-- Why: find_item() answers with the newest active sighting, so "I put them on the table", said by the
-- person on a call, outranks two camera frames of the glasses on the nightstand. rank_item() weighs
-- who said what, how long ago, and where someone already looked, and returns places in two orders:
-- most likely first (what to say) and best to check first (where to send the person).
--
--   trust     camera (seen, placed, confirmed_live, tour) 1.0 | family typed it ('told' + 'manual') 0.9
--             live hint 0.5 | the person said it on a call ('told' + 'facetime_caller') 0.4
--   retire    a newer active/superseded sighting retires an older one only if newer trust >= least(older, 0.8):
--             a spoken claim cannot erase camera evidence, but the family or the camera can
--   habit     0.02 everywhere + 0.3 at the item's home landmark + 0.7 x share of its past (retired) stays
--   evidence  sum over live stays at a place of trust x exp(-age / 6 h); a one-frame glimpse counts 0.3x
--   misses    each empty look at a place in the last 12 h, after its newest evidence (camera: absent_count;
--             a person: record_miss) multiplies that place by (1 - find_chance)
--   score     (0.6 x habit + evidence) x (1 - find_chance) ^ misses;   p = score / sum(score)
--   order     search_order sorts by p x find_chance / seconds; seconds = walk from the wearer's room + check
--   band      high: p1 >= 0.6 and p1 - p2 >= 0.25 | split: p1 + p2 >= 0.6 | low otherwise
-- =====================================================================

alter table landmarks add column if not exists find_chance real
  check (find_chance > 0 and find_chance <= 1);   -- chance one look finds it if it is there; null = by kind
alter table landmarks add column if not exists check_seconds real
  check (check_seconds > 0);                      -- seconds to check the place once there; null = by kind

create table if not exists misses (               -- someone looked at a place for an item and it was not there
  id          uuid primary key default gen_random_uuid(),
  home_id     uuid not null references homes(id) on delete cascade,
  item_id     uuid not null references items(id) on delete cascade,
  landmark_id uuid not null references landmarks(id) on delete cascade,
  missed_at   timestamptz not null,
  source      text not null default 'caller' check (source in ('caller','manual','worn_cam')),
  unique (item_id, landmark_id, missed_at)       -- retries cannot double-count a look
);
create index if not exists misses_item_idx on misses (item_id, landmark_id, missed_at desc);
alter table misses enable row level security;

create or replace function sighting_trust(p_event text, p_source text) returns real
language sql immutable as $$
  select (case
    when p_event = 'told' and p_source = 'facetime_caller' then 0.4   -- the person's own memory
    when p_event = 'told'                                  then 0.9   -- family typed it in
    when p_source = 'live_hint'                            then 0.5
    else 1.0                                                          -- the camera saw it
  end)::real
$$;

create or replace function walk_seconds(p_from uuid, p_to uuid) returns real
language sql stable as $$
  select (case
    when p_from is null or p_to is null then 15
    when p_from = p_to then 6
    when exists (select 1 from room_links
                  where (room_a = p_from and room_b = p_to) or (room_a = p_to and room_b = p_from)) then 15
    else 25
  end)::real
$$;

-- "It wasn't there." Call this (not record_outcome) when the person checked a place we suggested.
create or replace function record_miss(p_home uuid, p_item uuid, p_landmark uuid,
                                       p_at timestamptz default now(), p_source text default 'caller')
returns uuid language plpgsql as $$
declare
  mid uuid;
begin
  if not exists (select 1 from places where landmark_id = p_landmark and home_id = p_home) then
    raise exception 'landmark % is not in home %', p_landmark, p_home;
  end if;
  if not exists (select 1 from items where id = p_item and home_id = p_home) then
    raise exception 'item % is not in home %', p_item, p_home;
  end if;
  insert into misses (home_id, item_id, landmark_id, missed_at, source)
  values (p_home, p_item, p_landmark, p_at, p_source)
  on conflict (item_id, landmark_id, missed_at) do nothing
  returning id into mid;
  return mid;
end $$;

-- The read path: one call returns the ranked places plus find_item()'s answer under "find".
create or replace function rank_item(p_home uuid, p_query text, p_now timestamptz default now())
returns jsonb language plpgsql stable as $$
declare
  q    text := regexp_replace(lower(trim(p_query)), '^(my|the|a|some|her|his)\s+', '');
  it   items;
  here uuid;
  res  jsonb;
begin
  select * into it from items
   where home_id = p_home
     and (lower(name) = q or q = any (select lower(a) from unnest(aliases) a))
   limit 1;
  if not found then
    return jsonb_build_object('state', 'unknown_item', 'heard', p_query);
  end if;

  select o.room_id into here                       -- where the wearer is now (last room the camera saw)
    from observations o
   where o.home_id = p_home and o.room_id is not null and o.captured_at <= p_now
   order by o.captured_at desc limit 1;

  with
  cand as (                                        -- every place in the home, including no-capture rooms
    select pl.landmark_id, pl.room_id, pl.room_spoken, pl.landmark_spoken,
           coalesce(l.find_chance, case l.kind when 'container' then 0.6 when 'floor' then 0.7
                                               when 'fixture' then 0.95 else 0.9 end)::real as find_chance,
           coalesce(l.check_seconds, case l.kind when 'container' then 8 when 'floor' then 6
                                                 when 'fixture' then 2 else 3 end)::real as check_s
      from places pl join landmarks l on l.id = pl.landmark_id
     where pl.home_id = p_home
  ),
  rows_ as (
    select s.id, s.landmark_id, s.status, s.in_hand, s.event_type, s.source, s.last_seen_at,
           s.absent_count, s.contradicted_at, sighting_trust(s.event_type, s.source) as trust
      from sightings s
     where s.item_id = it.id and s.last_seen_at <= p_now
  ),
  live as (                                        -- stays that still count as evidence
    select a.* from rows_ a
     where a.status in ('tentative', 'active', 'superseded')
       and not exists (select 1 from rows_ b
                        where b.status in ('active', 'superseded')
                          and b.id <> a.id
                          and b.last_seen_at > a.last_seen_at
                          and b.trust >= least(a.trust, 0.8))
  ),
  ev as (
    select l.landmark_id,
           sum(l.trust * case when l.status = 'tentative' then 0.3 else 1.0 end
                       * exp(-extract(epoch from (p_now - l.last_seen_at)) / 21600.0)) as e,
           max(l.last_seen_at) as newest
      from live l
     where not l.in_hand and l.landmark_id is not null
     group by l.landmark_id
  ),
  why as (                                         -- who put it there, for the spoken answer
    select distinct on (l.landmark_id) l.landmark_id,
           case when l.event_type = 'told' and l.source = 'facetime_caller' then 'you_said'
                when l.event_type = 'told' then 'family_said'
                else 'camera' end as why,
           round(extract(epoch from (p_now - l.last_seen_at)) / 60)::int as minutes_ago
      from live l
     where not l.in_hand and l.landmark_id is not null and l.status <> 'tentative'
     order by l.landmark_id, l.last_seen_at desc
  ),
  past as (                                        -- retired or contradicted stays: what it usually does
    select r.landmark_id, count(*)::real as n
      from rows_ r
     where r.status <> 'tentative' and not r.in_hand and r.landmark_id is not null
       and r.id not in (select id from live)
     group by r.landmark_id
  ),
  habit as (
    select c.landmark_id,
           0.02 + case when c.landmark_id = it.home_landmark_id then 0.3 else 0 end
                + 0.7 * coalesce(p.n / nullif((select sum(n) from past), 0), 0) as h
      from cand c left join past p using (landmark_id)
  ),
  miss as (
    select c.landmark_id,
           coalesce((select sum(r.absent_count) from rows_ r
                      where r.landmark_id = c.landmark_id and r.absent_count > 0
                        and coalesce(r.contradicted_at, p_now) > p_now - interval '12 hours'
                        and r.last_seen_at >= coalesce(ev.newest, '-infinity'::timestamptz)), 0)
           + (select count(*) from misses m
               where m.item_id = it.id and m.landmark_id = c.landmark_id
                 and m.missed_at <= p_now and m.missed_at > p_now - interval '12 hours'
                 and m.missed_at > coalesce(ev.newest, '-infinity'::timestamptz)) as n
      from cand c left join ev using (landmark_id)
  ),
  scored as (
    select c.*, h.h / (select sum(h) from habit) as habit_p, coalesce(ev.e, 0) as evidence,
           power(1 - c.find_chance, m.n) as miss_factor, m.n::int as misses,
           walk_seconds(here, c.room_id) + c.check_s as seconds,
           w.why, w.minutes_ago
      from cand c
      join habit h using (landmark_id)
      join miss m using (landmark_id)
      left join ev using (landmark_id)
      left join why w using (landmark_id)
  ),
  prob as (
    select s.*, x.score / sum(x.score) over () as p
      from scored s
      cross join lateral (select (0.6 * s.habit_p + s.evidence) * s.miss_factor as score) x
  ),
  ranked as (
    select pr.*,
           row_number() over (order by pr.p desc, pr.landmark_spoken) as rk_p,
           row_number() over (order by pr.p * pr.find_chance / pr.seconds desc, pr.p desc,
                              pr.landmark_spoken) as rk_go
      from prob pr
  )
  select jsonb_build_object(
           'item', it.name,
           'plural', it.plural,
           'wearer_room', (select coalesce(spoken_name, name) from rooms where id = here),
           'band', case when max(p) filter (where rk_p = 1) >= 0.6
                         and max(p) filter (where rk_p = 1) - coalesce(max(p) filter (where rk_p = 2), 0) >= 0.25
                        then 'high'
                        when max(p) filter (where rk_p = 1) + coalesce(max(p) filter (where rk_p = 2), 0) >= 0.6
                        then 'split'
                        else 'low' end,
           'places', jsonb_agg(jsonb_build_object(
                       'landmark_id', landmark_id, 'room', room_spoken, 'landmark', landmark_spoken,
                       'p', round(p::numeric, 3), 'why', coalesce(why, 'usual'),
                       'minutes_ago', minutes_ago, 'misses', misses)
                     order by rk_p) filter (where rk_p <= 5),
           'search_order', jsonb_agg(jsonb_build_object(
                       'landmark_id', landmark_id, 'room', room_spoken, 'landmark', landmark_spoken,
                       'p', round(p::numeric, 3), 'seconds', round(seconds::numeric, 1))
                     order by rk_go) filter (where rk_go <= 5))
    into res
    from ranked;

  return res || jsonb_build_object('find', find_item(p_home, p_query));
end $$;
