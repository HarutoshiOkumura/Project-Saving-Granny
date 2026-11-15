---
paths:
  - "supabase/**"
  - "app/memory/**"
---

# Memory database rules

These load when you work on the schema or on `app/memory/db.py`.
The contract table is in `CLAUDE.md`.

## State of the schema

- On 14 Nov 2026 step 01 applied `0001_save_it_memory.sql` (migration `save_it_memory`) and `0002_lock_rls_auto_enable.sql` (migration `lock_rls_auto_enable`) to the Supabase project, and seeded it from `supabase/seed.sql`.
- Both files are frozen. Changes go in the next numbered file (`0003_*.sql`), applied with the Supabase MCP `apply_migration` after the scratch tests pass.
- Supabase runs Postgres 17 with pgvector 0.8.2; the scratch container runs Postgres 16 with pgvector 0.8.7. Function, column, constraint, index and trigger definitions were compared after applying and are identical.
- Every schema change gets a check in `supabase/tests/test_memory.sql`, written first and seen failing.
- Run the tests on scratch Postgres only (command in `CLAUDE.md`), on a fresh database each time, loading every migration in order before the test file. 75 checks.
- Section 26 (API grants) runs only if the roles `anon`, `authenticated` and `service_role` exist. To run it (82 checks), create them in the scratch cluster first, as the test file header says, and drop them afterwards.

## How the log becomes a belief

- One frame opens a `tentative` stay. A second frame at the same place within 10 minutes makes it `active`. A tentative stay never answers a question.
- A call whose `p_seen_at` equals the stay's `first_seen_at` or `last_seen_at` is the same frame sent twice: it changes nothing and returns the same id.
- Seeing an item again where it is believed to be extends that stay, whatever the gap.
- When a stay becomes active, every other active stay for that item becomes `superseded`. Only the newest active stay by `last_seen_at` is the belief, so a late-arriving older episode is filed as history.
- `mark_absent` counts empty looks at a landmark, but only one per `p_min_gap` (default 30 seconds) per stay, tracked in `sightings.last_absent_at`. At 3 counted looks the stay becomes `contradicted` and `find_item` says `not_there_anymore`.
- Seeing the item there again resets `absent_count` and `last_absent_at`. A contradicted stay is never reopened; a new stay starts.
- `told` and `confirmed_live` events are active at once.
- `record_outcome(query, false)` contradicts the sighting that answer used.
- Unowned detections (`item_id` null, "some keys") merge by label and never change an item's belief or absence count.

## Rooms and privacy

- When `p_landmark` is given, the room is that landmark's room; `p_room` may be null. If `p_room` is also given and differs, `log_sighting` raises `22023` (invalid_parameter_value). It also raises `22023` for a room or landmark that is not in `p_home`. The worker must catch it and skip the frame.
- `log_sighting` returns null and stores nothing for a room with `capture_allowed = false`, and for a camera source (`worn_cam`, `facetime_caller`) when there is neither room nor landmark. A person telling us (`manual`, `told`) may have no room.
- A `before insert or update` trigger (`drop_no_capture`) on `observations` and `sightings` silently drops any row whose room, or any of whose landmarks, is in a no-capture room. It is a backstop; decide the room before uploading a crop.

## Calling the functions

- Always pass the frame's capture time as `p_seen_at`, in UTC. Replays rebase their timestamps so the last frame is now.
- Pass real booleans for `p_in_hand`, never null.
- Pass `p_visible` as a list, `[]` when nothing was seen, never null. Null makes `mark_absent` match nothing.
- Call `mark_absent` only for landmarks the model listed in `landmarks_in_view`, with every item it placed on that landmark in `p_visible`.
- Insert the observation first. If its `idempotency_key` already exists, the frame was already processed, so skip it.
- `crop_url` holds a storage path (`crops/<home>/<item>/<utc timestamp>.jpg`), not a URL. Sign it at read time for 1 hour. The first segment is the bucket; the object key is the rest (`db.crop_key`: item name as a slug, time as `20261115T010203456789Z`).
- The worker inserts observations with an upsert on `(home_id, idempotency_key)` that ignores duplicates; an empty answer means the frame was processed before. The key is `<device_id>/<captured_at in UTC, ISO 8601>`.
- The voice tools call `ask_item`, not `find_item`, so every question is logged and `record_outcome` has a `query_id` to update. `find_item` is for reads that should not be logged.
- `find_item` is `stable`: in one SQL statement it sees the snapshot from before any write in that statement. Check a write's effect in a separate statement.

## Dummy data

Until the camera pipeline runs (steps 05 to 07), the read path is built against dummy data.

- Load it with `supabase/dummy_data.sql`. It replaces the log (queries, sightings, observations) for the demo home with one item in each found state: glasses `seen` (on the chair), keys `carried`, bag `not_there_anymore`, water bottle `seen` but not confident; the watch stays `never_seen`. It refuses to run once an observation from a real device exists, so it cannot wipe camera data.
- To write more, go through `log_sighting` and `mark_absent` only. Never insert into `sightings` directly: that skips the two-frame rule and can leave two active rows for one item.
- A stay answers only after two `log_sighting` calls at the same place with different `p_seen_at`, within 10 minutes. One call, or the same time twice, stays `tentative`, and `find_item` says `never_seen`.
- `mark_absent` looks must be at least 30 seconds apart; 3 counted looks give `not_there_anymore`.
- Pass the landmark and leave `p_room` null; the room comes from the landmark. Room only (`p_landmark` null) is for an item in hand.
- Use times relative to `now()`. Leave `p_crop_url` null unless a JPEG of our own staged objects is first uploaded to the `crops` bucket at that path; a path with no file breaks photo signing.
- Clear dummy rows with the rehearsal reset before recording real camera data.

## find_item output

- States: `seen`, `carried`, `not_there_anymore`, `never_seen`, `unknown_item`. The keys per state are listed in `CLAUDE.md`.
- `landmark` and `address` are null when the item was seen in a room but not on a known landmark. `room` is null for a `told` event with no room.
- `usual`, `previous` and `wearer_went_to` can be null.
- `usual` is a place with at least 2 non-tentative, not-in-hand stays (most stays first, then most recent); otherwise the item's `home_landmark_id`. It is never the landmark the answer has just ruled out (`not_there_anymore`), so it can be null.
- `last_seen_at` is the stay's last frame in UTC (`2026-11-14T21:03:06.285073Z`); `timezone` is the home's IANA zone. `speak()` uses them for "this morning" and "about forty minutes ago".
- `never_seen` carries `possible_glimpse`; the other found states carry `possible_newer_glimpse`. `unknown_item` carries `heard`.
- `photo` is a storage path, not a URL.
- `confident` is detector x room x identity confidence, cut at 0.5.

## Access

- Row level security is on with no policies. Only the backend, using the secret key (`sb_secret_...`, role `service_role`), may read or write. The publishable key must get nothing.
- The end of `0001` revokes everything on our tables, views and functions from `anon` and `authenticated` (and `public` for functions), then grants `service_role` exactly: usage on `public`, select/insert/update/delete on the 10 tables, select on the 4 views, execute on the 9 callable functions. The trigger function is not granted to anyone. https://supabase.com/docs/guides/api/securing-your-api
- `0002` revokes execute on Supabase's own `public.rls_auto_enable()` (the event trigger that turns on RLS for new tables) from `public`, `anon` and `authenticated`. The event trigger still fires.
- A new function in a later migration needs the same revoke and grant, or the API answers `42501`. Every function also needs `set search_path`, or the security advisor flags it (test section 25 checks this).
- When calling the REST API directly (curl), send the new keys in the `apikey` header only, not `Authorization: Bearer`. Secret keys are refused from browser user agents.
- Security advisor after step 01: `rls_enabled_no_policy` (INFO, deliberate: no role but `service_role` has any grant) and `extension_in_public` for `vector` (accepted).
- `purge_old` is not scheduled, and nothing deletes files from the `crops` bucket.

## Rehearsal reset

`delete from queries; delete from sightings; delete from observations;` keeps the home, rooms, landmarks and items.
Never run `supabase/tests/test_memory.sql` against Supabase.
