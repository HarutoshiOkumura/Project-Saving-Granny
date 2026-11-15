# Save It

A phone number a person with dementia can call to ask "where are my glasses?". A phone worn on a lanyard sees where belongings are put down, a database remembers each place, and a voice agent answers by phone call or FaceTime. Built at Emory Hacks 2026. Submission is Sunday 15 Nov, 8:00 AM: Devpost entry plus a 2-minute video.

## Start of every session

1. Read `docs/STATUS.md`. It says what is done, what is stubbed and what is blocked.
2. Work on one step only: the `/step-NN-...` command you were given, or the step named in the request.
3. End by running that step's checks, updating `docs/STATUS.md`, and stopping. Do not start the next step unasked.

Read these when a step touches them, not before:

- `docs/PLAN.md`: build order, time boxes, checkpoints, cut order
- `docs/DECISIONS.md`: open choices and their defaults. If a step depends on an undecided item, use the default and record that in STATUS.
- `docs/SUPABASE.md` and `docs/ROBOFLOW.md`: exact setup steps for the humans

## Architecture

```
WRITE PATH (slow, may fail softly)
phone camera page --JPEG every 1-2 s--> POST /frames
   -> filters (blur, duplicate) -> perceive() -> log_sighting() / mark_absent() -> Supabase
                                   |-- Roboflow detector: boxes and crops
                                   |-- Gemini Flash: room, landmark, relation, in_hand as strict JSON

READ PATH (fast, must never fail)
caller -> Vapi phone number -> POST /vapi/tool -> ask_item() -> speak() -> one sentence
caller -> FaceTime -> Chert -> LiveKit agent -> ask_item() -> speak() + last-seen photo
family -> GET /dashboard -> GET /api/timeline
```

Two rules shape everything:

- **The database is the only memory.** Models never keep state. Before a model looks at a frame it is given `perception_context()`; after it looks, its answer goes through `log_sighting()` and `mark_absent()`. "Where is it now" is derived by `find_item()`, never stored.
- **The read path never calls a vision model.** `/find`, `/vapi/tool` and the agent tools do one database call and one pure function. Target under 1 second.

## Repo layout

```
app/main.py              FastAPI app and routes only
app/config.py            settings from environment (pydantic-settings)
app/memory/db.py         the ONLY module that talks to Supabase
app/memory/schema.py     Pydantic models for what the memory functions return (FindResult, Place)
app/speak.py             find_item JSON -> one spoken sentence (pure, unit-tested)
app/ask.py               one question: ask_item, speak(), 2 s timeout, fallback, log line (for /find and voice)
app/voice/vapi.py        Vapi tool webhook
app/perception/schema.py Pydantic models for the perception result
app/perception/detector.py  Roboflow calls
app/perception/vlm.py    Gemini call with a JSON schema
app/perception/filters.py   blur and duplicate checks
app/worker/ingest.py     frame -> perception -> database
app/web/                 capture.html, dashboard.html (static, no build step)
agent/                   LiveKit agent for the Chert FaceTime line (separate process)
scripts/                 bakeoff.py, replay_video.py, enroll.py, sync_typesense.py
tests/                   pytest; tests/fixtures/frames/ holds staged frames
supabase/migrations/     0001_save_it_memory.sql, 0002_lock_rls_auto_enable.sql (applied; frozen)
supabase/tests/          test_memory.sql (scratch database only)
supabase/seed.sql        the demo home as seeded on Supabase (template: seed.example.sql)
supabase/dummy_data.sql  sightings in each answer state, for building the read path before the camera works
```

## Commands

```bash
uv sync                                              # install (Python 3.12)
uv run uvicorn app.main:app --reload --port 8000     # run the API
uv run pytest -q                                     # unit tests
uv run ruff check . && uv run ruff format .          # lint and format
# database tests: scratch Postgres only, never the Supabase project
docker run --name saveit-pg -e POSTGRES_PASSWORD=pw -p 54329:5432 -d pgvector/pgvector:pg16
P=postgresql://postgres:pw@localhost:54329          # or: docker start saveit-pg
psql $P/postgres -qc "drop database if exists saveit_test" -c "create database saveit_test"
psql $P/saveit_test -v ON_ERROR_STOP=1 -q -f supabase/migrations/0001_save_it_memory.sql \
  -f supabase/migrations/0002_lock_rls_auto_enable.sql -f supabase/tests/test_memory.sql
```

## The memory contract

Call these through `app/memory/db.py` with `supabase.rpc(name, params)`. Parameter names must match exactly.

| Function | Use | Returns |
|---|---|---|
| `perception_context(p_home, p_room)` | Before the vision model looks: allowed rooms, landmarks, items, current beliefs | jsonb |
| `log_sighting(p_home, p_item, p_label, p_room, p_landmark, p_relation, p_in_hand, p_seen_at, ...)` | One detection. Merges frames into a stay, applies the two-frame rule (a repeated capture time is not a second frame), keeps one active row per item. The landmark decides the room; raises `22023` if `p_room` disagrees or either is not in this home | sighting id, or null when nothing may be stored (no-capture room, or a camera frame with no room) |
| `mark_absent(p_home, p_landmark, p_seen_at, p_visible, p_needed, p_min_gap)` | A landmark was clearly in view; `p_visible` lists item ids seen on it. An empty look counts only if `p_min_gap` (30 s) after the last counted one | count flipped to `contradicted` |
| `ask_item(p_home, p_query, p_channel)` | The voice tools. Answers like `find_item` and logs the question in the same call. `p_channel`: `phone`, `facetime`, `web` | `find_item` jsonb plus `query_id` |
| `find_item(p_home, p_query)` | Read-only answer that logs nothing (dashboard, scripts, debugging) | jsonb with `state` |
| `record_outcome(p_query, p_found)` | After "did you find it?", with the `query_id` from `ask_item`. `false` retires that answer | void |
| `match_room(p_home, p_embedding, p_k)`, `match_item(p_home, p_category, p_embedding)` | Optional embedding lookups | rows, best first |

`find_item` states and their keys:

- `seen`, `carried`, `not_there_anymore`: `item`, `plural`, `sighting_id`, `room`, `landmark`, `relation`, `address`, `minutes_ago`, `last_seen_at` (UTC, ISO 8601 ending in `Z`), `timezone` (the home's IANA zone), `confident`, `photo`, `previous`, `usual`, `wearer_went_to`, `possible_newer_glimpse`.
- `never_seen`: `item`, `plural`, `usual`, `timezone`, `possible_glimpse`.
- `unknown_item`: `heard`.
- `ask_item` adds `query_id` to every state.

Sighting statuses: `tentative` (one frame) -> `active` (two agreeing frames) -> `superseded` (item seen elsewhere) or `contradicted` (landmark seen empty 3 times at least 30 s apart, or the person said it was not there).

Details and edge cases load from `.claude/rules/memory-db.md` when you open database files.

## The perception contract

`perceive(frame, context) -> Perception`, where every name comes from `perception_context()`:

```json
{"room": "kitchen", "room_confidence": 0.9,
 "landmarks_in_view": ["counter"],
 "items": [{"item": "glasses", "landmark": "counter", "relation": "on",
            "in_hand": false, "confidence": 0.8, "note": "black glasses beside the kettle"}]}
```

The model may only answer with names from the lists (use JSON-schema enums built at call time). `"unknown"` is always an allowed room and `"none"` an allowed landmark. Details load from `.claude/rules/perception.md`.

## Hard rules

- **Never upload images of a real home or real person to Roboflow.** The workspace is on the Research plan, so everything in it is public. Staged photos of our own objects only.
- **Real camera frames go to Gemini only from a billing-enabled Google project with AI Studio logging turned off, and every call passes `store=False`.** On the free tier Google may use inputs, images included, to improve its products, with human review; on paid projects logging is on by default and keeps requests 55 days; the Interactions API also stores each request unless told not to (D24). Staged test photos are fine on the free tier.
- **Never store a full frame.** Store a tight crop of the item, in the private `crops` bucket, and sign URLs at read time.
- **Never write anything for a room with `capture_allowed = false`.** If perception says the room is one, drop the frame: no crop, no row.
- **Never commit secrets.** Keys live in `.env` (gitignored). The Supabase secret key (`SUPABASE_SECRET_KEY`, `sb_secret_...`, which replaces the legacy service-role key) is backend-only and must never appear in `app/web/`.
- **Never run `supabase/tests/test_memory.sql` against the Supabase project.** It needs an empty database and inserts fixed ids.
- **Never insert into `sightings` directly, even for dummy data.** Load `supabase/dummy_data.sql`, or call `log_sighting` twice per stay with different `p_seen_at`; one call stays tentative and never answers. Details: "Dummy data" in `.claude/rules/memory-db.md`.
- **Never edit an applied migration.** `0001` and `0002` are applied to Supabase. Add the next numbered file (`0003_*.sql`), and re-run the database tests on scratch Postgres first.
- **Never say "HIPAA compliant"** in code, copy or docs. We are not a covered entity; we say "built with HIPAA-style safeguards".
- **Do not guess third-party request or response shapes.** Check the linked doc first (see External services). If the doc and this file disagree, the doc wins; note it in STATUS.

## Conventions

- Python 3.12, type hints everywhere, Pydantic models at every boundary (HTTP, model output, database rows).
- No SQL strings and no Supabase calls outside `app/memory/db.py`.
- Route handlers stay thin: parse, call one function, return.
- Every model call has a timeout, at most 3 retries with backoff, and a safe fallback (for the worker: skip the frame; for voice: "I'm not sure, let me check with your family").
- Log one line per frame and per question with ids and timings. Never log image bytes or keys.
- Tests: `speak()` has a test per state; `ingest` has a test using fixture frames with the model calls faked. Do not call paid services in tests.
- Times are stored in UTC. Spoken times are relative ("about forty minutes ago", "this morning").
- Small commits, one step per branch or commit series, message says which step.

## External services

Verify against the doc before coding. Use these model ids exactly.

| Service | Use | Doc to check |
|---|---|---|
| Supabase | Postgres + pgvector, storage, RPC | `docs/SUPABASE.md` |
| Roboflow | Detector: YOLO-World, SAM 3 or our trained model; optional CLIP ViT-L/14 embeddings (768 numbers) | `docs/ROBOFLOW.md`, https://docs.roboflow.com/llms.txt |
| Gemini API | Frame understanding (D24). Model `gemini-3.6-flash`; the bake-off also tries `gemini-3.5-flash-lite` (faster) and `gemini-4-hydrogen` (step-up). Interactions API (`client.aio.interactions.create`, package `google-genai`) with a JSON schema in `response_format` and `store=False` | https://aistudio.google.com/docs/structured-output, `.../image-understanding`, `.../interactions`, `.../thinking`, `.../media-resolution` |
| Vapi | Inbound phone number, one function tool | https://docs.vapi.ai/tools/custom-tools.md |
| Chert + LiveKit | FaceTime line bridged to a LiveKit agent | https://docs.trychert.com/llms.txt, https://docs.livekit.io/agents/ |
| Typesense | Typo and synonym matching of item names (optional) | https://typesense.org/docs/ |
| Coder | Development workspaces; optional egress allowlist for the worker | https://coder.com/docs |

## Out of scope until the core demo passes

The core demo is: put glasses down on camera, walk away, call the number, hear the right place. Until `docs/STATUS.md` shows that passing, do not build 3D scans, AR arrows, live pointing on FaceTime, hand tracking, object tracking across frames, user accounts, or multi-home support. One home, one `HOME_ID` from the environment.
