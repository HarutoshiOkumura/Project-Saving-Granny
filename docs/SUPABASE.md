# Supabase: exact steps

The SQL was tested on Postgres 16 with pgvector 0.6 (46 checks). It has not been run on Supabase yet, so step 3 is the first real test. Dashboard labels move around; if a menu is not where this says, search the dashboard for the word.

## 1. Create the project

1. New project. Pick the region nearest the venue. Save the database password.
2. Collect four values for `.env`:
   - `SUPABASE_URL`: the project URL.
   - `SUPABASE_SERVICE_ROLE_KEY`: the service-role (secret) key. Backend only.
   - `DATABASE_URL`: a Postgres connection string from the Connect panel. If `psql` cannot reach the direct host from the venue network, use the session pooler string.
   - `HOME_ID`: comes from step 4.

## 2. Load the schema

Either paste `supabase/migrations/0001_save_it_memory.sql` into the SQL editor and run it, or:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f supabase/migrations/0001_save_it_memory.sql
```

It creates the `vector` extension, 10 tables, 4 views and 8 functions, turns on row level security, and adds `sightings` to the Realtime publication if that publication exists.

## 3. Check it loaded

```sql
select extname from pg_extension where extname = 'vector';
select count(*) from information_schema.tables where table_schema = 'public';   -- 10 tables + 4 views = 14
select proname from pg_proc where proname in
  ('log_sighting','mark_absent','find_item','perception_context','record_outcome','purge_old','match_room','match_item');
```

If the extension line fails, enable `vector` under Database, Extensions, then re-run the migration.

## 4. Seed the demo home

1. Copy `supabase/seed.example.sql` to `supabase/seed.sql` and edit the rooms, landmarks and items to match what you staged (`DECISIONS.md` D1, D2).
2. Run it. The home id is fixed in the file: `11111111-1111-1111-1111-111111111111`. Put it in `.env` as `HOME_ID`.
3. Check: `select address, landmark_spoken from places;`

## 5. Smoke test by hand

```sql
-- two frames two seconds apart: tentative, then active
select log_sighting('11111111-1111-1111-1111-111111111111',
  (select id from items where name = 'glasses'), 'glasses',
  (select room_id from places where landmark = 'counter'),
  (select landmark_id from places where landmark = 'counter'),
  'on', false, now() - interval '40 minutes', 0.9, 0.9, 1.0);
select log_sighting('11111111-1111-1111-1111-111111111111',
  (select id from items where name = 'glasses'), 'glasses',
  (select room_id from places where landmark = 'counter'),
  (select landmark_id from places where landmark = 'counter'),
  'on', false, now() - interval '40 minutes' + interval '2 seconds', 0.9, 0.9, 1.0);

select jsonb_pretty(find_item('11111111-1111-1111-1111-111111111111', 'my specs'));
```

Expect `"state": "seen"`, `"landmark": "the kitchen counter"`, `"minutes_ago": 40`. Clear the test rows afterwards with `delete from sightings;`.

## 6. Storage

1. Create a bucket named `crops`. Keep it private.
2. The backend uploads with the service-role key to `crops/<home>/<item>/<timestamp>.jpg` and stores that path in `sightings.crop_url`.
3. When a page or agent needs the picture, the backend creates a signed URL that lasts 1 hour.

## 7. Call it from Python

```python
from supabase import create_client
sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
res = sb.rpc("find_item", {"p_home": HOME_ID, "p_query": "glasses"}).execute()
answer = res.data          # a dict with "state", "room", "landmark", ...
```

- Parameter names are the SQL argument names. Leave out arguments that have defaults.
- If the API says the function is not in the schema cache, run `notify pgrst, 'reload schema';` once.
- All of this lives in `app/memory/db.py` and nowhere else.

## 8. Things that will bite

- **Row level security is on with no policies.** The anon key reads nothing; that is deliberate. The dashboard goes through the backend. If you later want Realtime in the browser, add a read-only policy first and never ship the service-role key to a page.
- **Do not run `supabase/tests/test_memory.sql` here.** It expects an empty database. Use the scratch Postgres command in `CLAUDE.md`.
- **Schema changes** go in `0002_*.sql`, tested on scratch Postgres first.
- **Vector width** is 768 and cannot change once rows exist.
- **Clock.** Always pass the frame's capture time to `log_sighting`. `minutes_ago` is computed from it.
- **Reset between rehearsals:** `delete from queries; delete from sightings; delete from observations;` leaves the home, rooms, landmarks and items in place.
