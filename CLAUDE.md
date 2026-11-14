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
- `docs/RETRIEVAL.md`: rank_item, record_miss, speak() rules (read side)
- `docs/CHERT.md`: FaceTime agent setup and call rules
- `docs/TYPESENSE.md`: search layer, exact API syntax, prize criteria
- `docs/DASHBOARD.md`: GUI and voice accessibility constants, pages, privacy
- `docs/SPONSORS.md`: prizes, judging, Coder, Gemini, pitch facts

## Architecture

```
WRITE PATH (slow, may fail softly)
phone camera page --JPEG every 1-2 s--> POST /frames
   -> filters (blur, duplicate) -> perceive() -> log_sighting() / mark_absent() -> Supabase
                                   |-- Roboflow detector: boxes and crops
                                   |-- Claude Haiku: room, landmark, relation, in_hand as strict JSON

READ PATH (fast, must never fail)
caller -> Vapi phone number -> POST /vapi/tool -> find_item() -> speak() -> one sentence
caller -> FaceTime -> Chert -> LiveKit agent -> find_item() -> speak() + last-seen photo
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
app/speak.py             find_item JSON -> one spoken sentence (pure, unit-tested)
app/voice/vapi.py        Vapi tool webhook
app/perception/schema.py Pydantic models for the perception result
app/perception/detector.py  Roboflow calls
app/perception/vlm.py    Claude call with a JSON schema
app/perception/filters.py   blur and duplicate checks
app/worker/ingest.py     frame -> perception -> database
app/web/                 capture.html, dashboard.html (static, no build step)
agent/                   LiveKit agent for the Chert FaceTime line (separate process)
scripts/                 bakeoff.py, replay_video.py, enroll.py, sync_typesense.py
tests/                   pytest; tests/fixtures/frames/ holds staged frames
supabase/migrations/     0001_save_it_memory.sql (tested; do not edit once applied)
supabase/tests/          test_memory.sql (scratch database only)
supabase/seed.example.sql   demo home: rooms, landmarks, items
```

## Commands

```bash
uv sync                                              # install (Python 3.12)
uv run uvicorn app.main:app --reload --port 8000     # run the API
uv run pytest -q                                     # unit tests
uv run ruff check . && uv run ruff format .          # lint and format
# database tests: scratch Postgres only, never the Supabase project
docker run --name saveit-pg -e POSTGRES_PASSWORD=pw -p 54329:5432 -d pgvector/pgvector:pg16
psql postgresql://postgres:pw@localhost:54329/postgres -v ON_ERROR_STOP=1 \
  -f supabase/migrations/0001_save_it_memory.sql -f supabase/tests/test_memory.sql
```

## The memory contract

Call these through `app/memory/db.py` with `supabase.rpc(name, params)`. Parameter names must match exactly.

| Function | Use | Returns |
|---|---|---|
| `perception_context(p_home, p_room)` | Before the vision model looks: allowed rooms, landmarks, items, current beliefs | jsonb |
| `log_sighting(p_home, p_item, p_label, p_room, p_landmark, p_relation, p_in_hand, p_seen_at, ...)` | One detection. Merges frames into a stay, applies the two-frame rule, keeps one active row per item | sighting id, or null for a no-capture room |
| `mark_absent(p_home, p_landmark, p_seen_at, p_visible)` | A landmark was clearly in view; `p_visible` lists item ids seen on it | count flipped to `contradicted` |
| `find_item(p_home, p_query)` | The voice tools | jsonb with `state` |
| `record_outcome(p_query, p_found)` | After "did you find it?" | void |
| `match_room(p_home, p_embedding, p_k)`, `match_item(p_home, p_category, p_embedding)` | Optional embedding lookups | rows, best first |

`find_item` states: `seen`, `carried`, `not_there_anymore`, `never_seen`, `unknown_item`. Other keys: `item`, `plural`, `room`, `landmark`, `relation`, `minutes_ago`, `confident`, `photo`, `previous`, `usual`, `wearer_went_to`, `possible_newer_glimpse`.

Sighting statuses: `tentative` (one frame) -> `active` (two agreeing frames) -> `superseded` (item seen elsewhere) or `contradicted` (landmark seen empty 3 times, or the person said it was not there).

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
- **Never store a full frame.** Store a tight crop of the item, in the private `crops` bucket, and sign URLs at read time.
- **Never write anything for a room with `capture_allowed = false`.** If perception says the room is one, drop the frame: no crop, no row.
- **Never commit secrets.** Keys live in `.env` (gitignored). The Supabase service-role key is backend-only and must never appear in `app/web/`.
- **Never run `supabase/tests/test_memory.sql` against the Supabase project.** It needs an empty database and inserts fixed ids.
- **Never edit `0001_save_it_memory.sql` after it is applied.** Add `0002_*.sql`, and re-run the database tests on scratch Postgres first.
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
| Claude API | Frame understanding. Model `claude-haiku-5-5`; step up to `claude-sonnet-5-5` only if the bake-off says so. JSON via `output_config.format` with `type: "json_schema"` | https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md and `.../vision.md` |
| Vapi | Inbound phone number, one function tool | https://docs.vapi.ai/tools/custom-tools.md |
| Chert + LiveKit | FaceTime line bridged to a LiveKit agent | https://docs.trychert.com/llms.txt, https://docs.livekit.io/agents/ |
| Typesense | Typo and synonym matching of item names (optional) | https://typesense.org/docs/ |
| Coder | Development workspaces; optional egress allowlist for the worker | https://coder.com/docs |

## Out of scope until the core demo passes

The core demo is: put glasses down on camera, walk away, call the number, hear the right place. Until `docs/STATUS.md` shows that passing, do not build 3D scans, AR arrows, live pointing on FaceTime, hand tracking, object tracking across frames, user accounts, or multi-home support. One home, one `HOME_ID` from the environment.
