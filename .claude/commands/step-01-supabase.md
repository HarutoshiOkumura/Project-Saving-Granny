---
description: Step 01 - fix and finalize the memory schema, apply it to Supabase, seed the demo home, smoke test
---

# Step 01: Supabase

Read `docs/STATUS.md`, `docs/SUPABASE.md`, `.claude/rules/memory-db.md`, and `docs/DECISIONS.md` D1, D2, D13 and D15.
Time box: 1.5 hours.
If you pass it, stop, write what is left in STATUS, and ask the humans whether to continue.

## Where things stand

On 14 Nov 2026 the Supabase project (ref `rsxigywtkxqqcotevcrz`) was empty: no tables, no migrations, `vector` not installed.
Because `0001_save_it_memory.sql` has not been applied, fix it in place.
Once it is applied it is frozen, and later changes go in `0002_*.sql`.
Before editing, confirm with the Supabase MCP `list_migrations`; if `0001` already shows as applied, put the fixes in `0002_*.sql` instead.

## 1. Scratch database first

Start the scratch Postgres from `CLAUDE.md` (or `docker start saveit-pg` if the container exists).
Run the tests on a fresh database each time and confirm the 46-check baseline:

```bash
P=postgresql://postgres:pw@localhost:54329
psql $P/postgres -qc "drop database if exists saveit_test" -c "create database saveit_test"
psql $P/saveit_test -v ON_ERROR_STOP=1 -q \
  -f supabase/migrations/0001_save_it_memory.sql -f supabase/tests/test_memory.sql
```

If the sandbox refuses to start Docker, stop and ask the human to run the command or allow it.
Never run `supabase/tests/test_memory.sql` against Supabase.

## 2. Fix the schema, test first

For each fix, add a check to `supabase/tests/test_memory.sql`, watch it fail, then change the SQL.
Keep every existing check passing.

1. **Usual place** (`find_item`). Never offer as `usual` the landmark the current answer has just ruled out. Use history only for a place with at least 2 non-tentative, not-in-hand stays; otherwise fall back to `items.home_landmark_id`. Test: one counter stay, then contradicted, must give the nightstand as usual, not the counter.
2. **Same frame twice** (`log_sighting`). A call whose `p_seen_at` equals the stay's `first_seen_at` or `last_seen_at` must not add a frame or promote `tentative` to `active`. Test: two identical calls leave it tentative with 1 frame.
3. **Spaced absence** (`mark_absent`). Count an empty look only if it is at least `p_min_gap` (new parameter, default 30 seconds) after the last counted look for that sighting. Add a `last_absent_at` column; re-sighting resets it. Tests: three looks 2 seconds apart leave it active; three looks 40 seconds apart contradict it.
4. **Room from landmark** (`log_sighting`). When `p_landmark` is given, the room is that landmark's room. If `p_room` is also given and differs, raise an exception. Test both.
5. **Privacy fails closed.** (a) For camera sources (`worn_cam`, `facetime_caller`), `log_sighting` returns null when the room cannot be determined (no room and no landmark). (b) A `before insert` trigger on `observations` and on `sightings` that silently drops rows for rooms with `capture_allowed = false` (the trigger returns null). Test: a direct insert of a bathroom observation stores nothing.
6. **Grants.** At the end of the migration, inside a `do` block that runs only if the role `service_role` exists (scratch Postgres has no Supabase roles): revoke all on our tables and views from `anon` and `authenticated`; revoke execute on our functions from `public`, `anon` and `authenticated`; grant `service_role` usage on schema `public`, select/insert/update/delete on our tables, select on our views, and execute on our functions. Name our objects explicitly; do not touch the `vector` extension's functions. Source: https://supabase.com/docs/guides/api/securing-your-api.
7. **One call that answers and logs** (D15). Add `ask_item(p_home uuid, p_query text, p_channel text) returns jsonb`: it calls `find_item`, inserts a `queries` row (heard, item, sighting, state), and returns the `find_item` result plus `query_id`. The voice tools call this, so the read path stays one database call and `record_outcome` has a row to update.
8. **Fields `speak()` needs.** `find_item` also returns `last_seen_at` (UTC) and the home's `timezone`.

Then update the contract in `CLAUDE.md` (function table, and the full key list including `possible_glimpse`, `sighting_id`, `address`, `heard`, `query_id`, `last_seen_at`, `timezone`) and `.claude/rules/memory-db.md`, and delete the "Known gaps" section of the rules file.

## 3. Seed

If `docs/DECISIONS.md` still shows D1 or D2 as OPEN, ask the humans for the final room, landmark and item names.
If nobody answers within the step, copy `supabase/seed.example.sql` to `supabase/seed.sql`, keep only the items the demo uses (glasses and keys), and record that default in STATUS.
Names must be short, lower case and unlike each other.

## 4. Apply to Supabase

Use the Supabase MCP.

1. `apply_migration` with the contents of `0001_save_it_memory.sql`, name `save_it_memory`.
2. Run the checks in `docs/SUPABASE.md` section 3 with `execute_sql`.
3. `get_advisors` (security). Fix anything other than the known "extension in public schema" warning, or write in STATUS why not.
4. Run `supabase/seed.sql` with `execute_sql`.
5. Create the private `crops` bucket. Check the Storage docs with `search_docs` for the SQL or API to use first.
6. Run the smoke test in `docs/SUPABASE.md` section 5, then delete the test rows.

## Checks

- Every check in `supabase/tests/test_memory.sql` passes on scratch Postgres, old and new.
- `list_migrations` shows the migration and `list_tables` shows 10 tables.
- `get_advisors` shows no unexplained security findings.
- The API answers with the secret key, which proves the grants and the key work:
  ```bash
  set -a; . ./.env; set +a
  curl -s "$SUPABASE_URL/rest/v1/rpc/find_item" -H "apikey: $SUPABASE_SECRET_KEY" \
    -H "Content-Type: application/json" -d "{\"p_home\":\"$HOME_ID\",\"p_query\":\"glasses\"}"
  ```
  Expect JSON with `"state"`. A `42501` error means a grant is missing.
- The same call with `SUPABASE_PUBLISHABLE_KEY` is refused.

## Finish

Update `docs/STATUS.md` and, if anything changed, `docs/SUPABASE.md`.
Ask the humans to make the Supabase MCP read-only by adding `&read_only=true` to the URL in `.mcp.json`, now that the schema is applied.
Commit as `step 01: ...`, then stop.
