# Supabase: exact steps

Done for project `rsxigywtkxqqcotevcrz` on 14 Nov 2026 (step 01): schema applied, demo home seeded, `crops` bucket created, smoke test passed.
Follow these steps again only for a new project.
The SQL is tested on scratch Postgres 16 with pgvector 0.8.7 (75 checks) and runs on Supabase's Postgres 17 with pgvector 0.8.2.
Dashboard labels move around; if a menu is not where this says, search the dashboard for the word.

## 1. Create the project

1. New project. Pick the region nearest the venue. Save the database password.
2. Collect these values for `.env` (template: `.env.example`):
   - `SUPABASE_URL`: the project URL.
   - `SUPABASE_SECRET_KEY`: the secret key (`sb_secret_...`), which replaces the legacy service-role key. Backend only.
   - `SUPABASE_PUBLISHABLE_KEY`: the publishable key (`sb_publishable_...`). Low privilege; the backend does not need it.
   - `DATABASE_URL`: a Postgres connection string from the Connect panel. If `psql` cannot reach the direct host from the venue network, use the session pooler string.
   - `HOME_ID`: comes from step 4.

## 2. Load the schema

Apply every file in `supabase/migrations/` in order, either with the Supabase MCP `apply_migration` (names `save_it_memory` and `lock_rls_auto_enable`), or:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f supabase/migrations/0001_save_it_memory.sql \
  -f supabase/migrations/0002_lock_rls_auto_enable.sql
```

`0001` creates the `vector` extension, 10 tables, 4 views, 10 functions and 2 privacy triggers.
It turns on row level security, adds `sightings` to the Realtime publication, and grants the API roles (only `service_role` gets anything).
`0002` takes Supabase's own `rls_auto_enable()` event-trigger function off the Data API.

## 3. Check it loaded

```sql
select extname from pg_extension where extname = 'vector';
select table_type, count(*) from information_schema.tables where table_schema = 'public' group by 1;  -- 10 tables, 4 views
select proname from pg_proc where proname in
  ('log_sighting','mark_absent','find_item','ask_item','perception_context','record_outcome',
   'purge_old','match_room','match_item','drop_no_capture');                                     -- 10 rows
```

If the extension line fails, enable `vector` under Database, Extensions, then re-run the migration.
Then run the security advisor (MCP `get_advisors`, type `security`).
Expected: `rls_enabled_no_policy` (INFO, deliberate) and `extension_in_public` for `vector` (accepted). Anything else needs a look.

## 4. Seed the demo home

1. `supabase/seed.sql` holds the names in use (D1, D2 defaults plus a bedroom desk and the green bag). To change them, edit it to match what you staged; `supabase/seed.example.sql` is the original template.
2. Run it on an empty home. The home id is fixed in the file: `11111111-1111-1111-1111-111111111111`. Put it in `.env` as `HOME_ID`.
3. Check: `select address, landmark_spoken from places;`

## 5. Smoke test by hand

```sql
-- two frames two seconds apart: tentative, then active. The landmark decides the room.
select log_sighting('11111111-1111-1111-1111-111111111111',
  (select id from items where name = 'glasses'), 'glasses',
  null, (select landmark_id from places where landmark = 'counter'),
  'on', false, now() - interval '40 minutes', 0.9, 0.9, 1.0);
select log_sighting('11111111-1111-1111-1111-111111111111',
  (select id from items where name = 'glasses'), 'glasses',
  null, (select landmark_id from places where landmark = 'counter'),
  'on', false, now() - interval '40 minutes' + interval '2 seconds', 0.9, 0.9, 1.0);

select jsonb_pretty(find_item('11111111-1111-1111-1111-111111111111', 'my specs'));
select jsonb_pretty(ask_item('11111111-1111-1111-1111-111111111111', 'my specs', 'web'));   -- logs a queries row
```

Expect `"state": "seen"`, `"landmark": "the kitchen counter"`, `"minutes_ago": 40`, and from `ask_item` a `query_id`.
Clear the test rows afterwards with the rehearsal reset in section 8.

Then check the API and the grants from a shell:

```bash
set -a; . ./.env; set +a
curl -s "$SUPABASE_URL/rest/v1/rpc/find_item" -H "apikey: $SUPABASE_SECRET_KEY" \
  -H "Content-Type: application/json" -d "{\"p_home\":\"$HOME_ID\",\"p_query\":\"glasses\"}"
```

The secret key must answer with JSON containing `"state"`.
The same call with `$SUPABASE_PUBLISHABLE_KEY` must be refused (HTTP 401, code `42501`).

## 6. Storage

1. The private `crops` bucket takes JPEGs up to 1 MiB. It was created with SQL (https://supabase.com/docs/guides/storage/buckets/creating-buckets):
   ```sql
   insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
   values ('crops', 'crops', false, 1048576, array['image/jpeg']);
   ```
2. There are no policies on `storage.objects`, so only the secret key can upload or sign. The publishable key is told the bucket does not exist.
3. The backend uploads with the secret key to `crops/<home>/<item>/<timestamp>.jpg` and stores that path in `sightings.crop_url`.
4. When a page or agent needs the picture, the backend creates a signed URL that lasts 1 hour.

## 7. Call it from Python

```python
from supabase import create_client
sb = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)
res = sb.rpc("ask_item", {"p_home": HOME_ID, "p_query": "glasses", "p_channel": "phone"}).execute()
answer = res.data          # a dict with "state", "room", "landmark", ..., "query_id"
sb.rpc("record_outcome", {"p_query": answer["query_id"], "p_found": True}).execute()
```

- Parameter names are the SQL argument names. Leave out arguments that have defaults.
- The voice tools call `ask_item`, which logs the question. `find_item` takes the same arguments minus `p_channel` and logs nothing.
- If the API says the function is not in the schema cache, run `notify pgrst, 'reload schema';` once.
- All of this lives in `app/memory/db.py` and nowhere else.

## 8. Things that will bite

- **Row level security is on with no policies.** The publishable key reads nothing; that is deliberate. The dashboard goes through the backend. If you later want Realtime in the browser, add a read-only policy and a grant first, and never ship the secret key to a page.
- **Grants.** Supabase is moving to opt-in API grants. `0001` revokes everything from `anon` and `authenticated` and grants `service_role` exactly what it needs. A function or table added later needs its own revoke and grant, or the API answers `42501`. Source: https://supabase.com/docs/guides/api/securing-your-api
- **search_path.** Every function sets `search_path`; the security advisor flags any that does not.
- **New keys.** When calling the REST API directly, send the `sb_` keys in the `apikey` header only, not `Authorization: Bearer`. Secret keys are refused from browser user agents.
- **Room and landmark must agree.** `log_sighting` takes the room from the landmark and raises `22023` if `p_room` says otherwise. A camera frame with no room and no landmark is not stored.
- **Bathroom rows vanish.** A trigger silently drops any `observations` or `sightings` row for a room with `capture_allowed = false`, even a direct insert. An insert that "worked" but stored nothing is this.
- **Do not run `supabase/tests/test_memory.sql` here.** It expects an empty database. Use the scratch Postgres command in `CLAUDE.md`.
- **Schema changes** go in the next numbered migration (`0003_*.sql`), tested on scratch Postgres first. `0001` and `0002` are applied and frozen.
- **Vector width** is 768 and cannot change once rows exist.
- **Clock.** Always pass the frame's capture time to `log_sighting`. `minutes_ago` is computed from it. Sending the same capture time twice does not confirm a sighting.
- **Reset between rehearsals:** `delete from queries; delete from sightings; delete from observations;` leaves the home, rooms, landmarks and items in place.
