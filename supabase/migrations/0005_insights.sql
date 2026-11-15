-- =====================================================================
-- 0005: insights (docs/INSIGHTS.md): wear time, family tags, the safety loop, and the
-- clinician-sharing consent. Additive only: three new tables, two views over them, and two
-- defaulted columns on homes. No 0001 or 0002 object changes.
-- Does not depend on 0003 (ranked search) or 0004 (D26 C), so it can be applied without them.
-- Tested on Postgres 16 with supabase/tests/test_insights.sql.
--
--   wear_minutes  one row per device per minute the camera sent frames: counts only, no room,
--                 no item, no image. "Worn" is at least 2 frames that moved (not duplicates).
--   wear_daily    worn minutes per home and local day (homes.timezone)
--   wear_hourly   the same per local hour, for the "quiet day" check
--   life_events   family tags that explain a day: visitor, unwell, new medicine...
--   concerns      the safety loop: the person said "I fell", "help", "I smell smoke"...; the
--                 family answers "on my way", "calling 911" or "all OK". Nothing here dials 911.
-- =====================================================================

create table if not exists wear_minutes (
  home_id   uuid not null references homes(id) on delete cascade,
  device_id text not null,
  minute    timestamptz not null check (minute = date_trunc('minute', minute)),
  frames    int not null check (frames > 0),
  moving    int not null check (moving >= 0 and moving <= frames),
  primary key (home_id, device_id, minute)
);
create index if not exists wear_minutes_home_minute_idx on wear_minutes (home_id, minute desc);

create view wear_daily with (security_invoker = true) as
select w.home_id, (w.minute at time zone h.timezone)::date as day,
       count(*) filter (where w.moving >= 2)::int as worn_minutes,
       sum(w.frames)::int as frames
from wear_minutes w
join homes h on h.id = w.home_id
group by 1, 2;

create view wear_hourly with (security_invoker = true) as
select w.home_id, (w.minute at time zone h.timezone)::date as day,
       extract(hour from w.minute at time zone h.timezone)::int as hour,
       count(*) filter (where w.moving >= 2)::int as worn_minutes
from wear_minutes w
join homes h on h.id = w.home_id
group by 1, 2, 3;

create table if not exists life_events (           -- family tags that explain a day
  id         uuid primary key default gen_random_uuid(),
  home_id    uuid not null references homes(id) on delete cascade,
  kind       text not null check (kind in ('visitor','unwell','hospital','new_medicine','new_item',
                                           'away','camera_off','new_hearing_aid','other')),
  starts_at  timestamptz not null,
  ends_at    timestamptz check (ends_at is null or ends_at >= starts_at),  -- null: that one day
  note       text check (char_length(note) <= 200),
  created_at timestamptz not null default now()
);
create index if not exists life_events_home_idx on life_events (home_id, starts_at desc);

create table if not exists concerns (              -- the safety loop: confirm, then the family decides
  id         uuid primary key default gen_random_uuid(),
  home_id    uuid not null references homes(id) on delete cascade,
  kind       text not null check (kind in ('fall','hurt','help','smoke','scam','lost_outside','quiet_day')),
  answer     text check (answer in ('hurt','ok','no_answer')),   -- to "Are you hurt?"
  urgency    text not null check (urgency in ('urgent','check_in','note')),
  channel    text not null default 'facetime' check (channel in ('phone','facetime','web')),
  raised_at  timestamptz not null default now(),
  room_id    uuid references rooms(id) on delete set null,       -- the last room the camera saw
  status     text not null default 'open'
             check (status in ('open','on_my_way','calling_911','all_ok')),
  handled_at timestamptz,
  handled_by text check (char_length(handled_by) <= 60)
);
create index if not exists concerns_home_idx on concerns (home_id, raised_at desc);

alter table homes add column if not exists share_summary_with_clinician boolean not null default false;
alter table homes add column if not exists share_decided_at timestamptz;  -- when the wearer was asked

alter table wear_minutes enable row level security;
alter table life_events  enable row level security;
alter table concerns     enable row level security;

-- API grants, as at the end of 0001: only the backend's secret key (service_role) reaches these.
do $$ begin
  if exists (select 1 from pg_roles where rolname = 'service_role') then
    revoke all on table wear_minutes, life_events, concerns, wear_daily, wear_hourly
      from anon, authenticated, service_role;
    grant select, insert, update, delete on table wear_minutes, life_events, concerns to service_role;
    grant select on table wear_daily, wear_hourly to service_role;
  end if;
end $$;
