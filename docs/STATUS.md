# Status

Claude Code updates this at the end of every step. Humans edit it freely. Keep it under one screen.

Last updated: Sat 14 Nov, 22:10 EST

## Steps

| # | Step | State | Notes |
|---|---|---|---|
| 00 | Scaffold | done | uv project (Python 3.12.15, `uv.lock` committed), ruff, package layout, `app/config.py` (`get_settings()`), `GET /health`, 10 tests. Left for humans: D5 and D6 (below) |
| 01 | Supabase | done | `0001` (8 fixes) and `0002` applied; 75/75 checks on scratch (82/82 with Supabase roles); home seeded; private `crops` bucket; smoke test and API key checks pass; `ask_item` median 98 ms over HTTPS. Left: MCP read-only (below) |
| 02 | Find API and speak() | done | `GET /find?item=...&channel=web` -> `app.ask.ask()` -> `db.ask_item` + `speak()`; 80 new tests (90 total). Live on Supabase: "my specs" -> "I last saw your glasses on the kitchen counter about forty minutes ago." 20 calls: median 50 ms, worst 114 ms; first call after a restart 115 to 160 ms (one 865 ms outlier, likely cold DNS). Dead database: fallback at 2.0 s; bad hostname: 46 ms. Smoke rows deleted |
| 03 | Phone voice | todo | Call `app.ask.ask(item, "phone")`, not `db.ask_item` + `speak()`: the 2 s timeout, fallback and log line are already there. `/find` has no auth yet; once the tunnel is up anyone can query it, so add a token check then |
| 04 | Detector bake-off | done | CP2 passes zero-shot (table below, D3). `scripts/bakeoff.py` (cached in `.cache/bakeoff/`), 17 frames renamed to the pattern, hand-drawn boxes in `tests/fixtures/frames/boxes.json`, `db.perception_context()` + `PerceptionContext`, Pillow added; 23 new tests (113 total). Keys description fixed on Supabase and in `seed.sql`. Fixtures are 1920 px copies. Deferred by the team to save time: the extra frames (below) |
| 05 | Perception module | done | `perceive(frame, context, empty_look=)` in `app/perception/`: SAM 3 gate, then Gemini (thinking `low`, resolution `high`, no beliefs, `store=False`), SAM 3 box swapped in at IoU 0.5. SAM 3 failure fails open; Gemini failure gives `perception=None`. `apply_drop_rules()`, `load_frame()` (EXIF rotation, no metadata), `crop()`, shared retries. Live on all 17 fixtures: **17/17 fully correct** (room, landmark, item), all 12 crop boxes from SAM 3. 101 new tests (214 total) incl. an offline replay of the recorded live answers. The bake-off now imports the moved schema, prompt and drop rules (its cache still hits) |
| 06 | Ingest worker | done | `POST /frames` (Bearer `APP_TOKEN`, replies 202, works in the background) -> `app/worker/ingest.py`: blur and duplicate filters, context and name-to-id map (cached 30 s), `perceive()`, drop rules (no-capture rooms from the `rooms` table), observation upsert on the idempotency key, crop upload, `log_sighting`, `mark_absent`; one log line per frame with status and ms per stage. At most 2 Gemini calls in flight plus a line one frame long per device (a newer frame replaces the waiting one). `scripts/replay_video.py --interval`. 66 new tests (280 total). CP3 below |
| 07 | Capture page | todo | Send a JPEG every **0.5 s** (D10) to `POST /frames` as multipart `frame`, `device_id`, `captured_at` (ISO 8601 with zone), header `Authorization: Bearer <APP_TOKEN>`. Long side at most 1920 px |
| 08 | Dashboard | todo | Now includes "add an item" (D26 A, about 1 h more): a form and `POST /api/items` that refuses names or aliases that clash. Show a sighting with no item as "unregistered object" |
| 09 | Typesense | todo | optional |
| 10 | FaceTime | todo | optional; blocked on D4. The agent calls the backend's `GET /find` (step 02), never Supabase. Build against `supabase/dummy_data.sql` (rewritten 14 Nov for the classroom names) |
| 11 | Harden and record | todo | |
| 12 | Unregistered objects | todo | optional (D26 C, `/step-12-unregistered`). Start only after CP1 and CP4 pass and by 01:00 Sun; otherwise it is a "next step" in the pitch |

State is one of: todo, doing, done, stubbed (works with fake data), blocked (say on what).

## Checkpoints

- CP1 phone call answers from seeded data: not yet (the backend half works: `GET /find` answers from Supabase)
- CP2 detector chosen: passed 14 Nov. SAM 3 (gate and crops) + `gemini-3.6-flash` (placement), D3
- CP3 replayed walk gives three correct answers: **passed 15 Nov at 0.5 s** on `recordings/IMG_2092.MOV` (66 s, four put-downs), with caveats below. `find_item` after the replay, each answer's last frame from the replay device:
  - glasses: "I last saw your glasses on the table just now."
  - watch: "I last saw your watch on the table just now."
  - bag: "I last saw your bag on the floor just now."
  - water bottle: "I last saw your water bottle on the chair just now."

  | Replay | Put-downs confirmed by the run's own frames | Notes |
  |---|---|---|
  | Every 2 s (the old D10 default) | 0 of 4 | Each item was in one frame only, so every stay stayed tentative |
  | Every 0.5 s, drop when Gemini is busy | 2 of 4 (glasses, bag) | The busy drops took the watch's and the bottle's second looks |
  | **Every 0.5 s, one-frame line per device** | **4 of 4** | Watch 2 frames, bottle 2, bag 5, glasses 2. 16 Gemini calls and 132 SAM 3 calls for the 66 s |

  Caveats: (1) the database still holds a teammate's dummy rows, and the replay extended two of them (glasses and bottle stays start at 23:42 and 22:12, dummy times); a clean record needs the rehearsal reset, then one replay (open question below). (2) A false "keys on the table" became active (6 frames): a keyring on a teammate's desk at 32 to 35 s, which Gemini can only call "the table"; the same desk gave one glasses frame. D1's "keep other tables out of frame" is real.
- CP4 live from the lanyard phone: not yet

## Stubs and fakes in the code right now

(none)

## Defaults taken from DECISIONS.md

- D1, D2: the B School classroom (one room plus a no-capture bathroom corner), landmarks table, chair, floor; items glasses, keys, bag, watch, water bottle. Re-seeded on Supabase on 14 Nov; `seed.sql` can now be re-run and refuses while anything is logged.
- D7: Gemini picks the room (17/17 right in step 05); no embedding vote. D8: one item per category, no `match_item`. D9: no embeddings used yet. D21: the prompt forbids describing people; crops are padded item boxes.
- D11: stay-merge 10 min, 3 empty looks to contradict, now at least 30 s apart (`mark_absent` `p_min_gap`); confidence cut 0.5.
- D13: one home, `HOME_ID=11111111-1111-1111-1111-111111111111`.
- D15: `ask_item` logs every question so `record_outcome` can retire a wrong answer; whether the voice asks "did you find it?" is still open.
- D17: `crops` bucket is private, JPEG only, 1 MiB cap.

## Tuned values

Step 05 live run, 15 Nov (`RUN_LIVE=1 LIVE_FRAMES=all uv run pytest -m live -s`, report in `.cache/live/perception.md`): all defaults kept, margins in D11.

- Room cut 0.6: lowest right `room_confidence` 0.80. Item cut 0.5: lowest right item 0.95, no stray item at all.
- SAM 3 gate 0.5: item frames score 0.57 and up, empty frames up to 0.55 (bare carpet). Overlapping, so it errs open; do not raise it.
- Timeouts: Gemini 10 s (median 2.7 s, worst 5.3 s), SAM 3 5 s (median 0.56 s, worst 0.86 s).
- Blur cut 25 and duplicate cut 0.95 kept after measuring the take (D11): a sharp frame of the glasses on the plain table scores only 60, smears 14 to 46; walking gives SSIM 0.1 to 0.6 between frames 0.5 s apart, holding still 0.72 to 0.98. New: duplicate refresh 10 s, empty look every 30 s, `VLM_IN_FLIGHT` 2.
- Frame interval 0.5 s (D10, decided by the CP3 replays above).

Bake-off, 14 Nov (8 close-ups, 4 medium, 5 empty; frames at 1920 px; box hit = IoU 0.5 with the hand-drawn box; Gemini counts after the worker's drop rules):

| Candidate | Close | Medium | False alarms | Median | Worst | CP2 |
|---|---|---|---|---|---|---|
| YOLO-World v2-l, best wording and threshold | 6/8 | 0/4 | 0/5 | 0.16 s | | fail: glasses, keys |
| SAM 3, descriptive wording, 0.7 | 8/8 | 2/4 | 0/5 | 0.36 s | | pass |
| SAM 3, descriptive wording, 0.5 (the gate) | 8/8 | 3/4 | 1/5 | 0.36 s | | pass |
| 3.6 Flash, low, high, no beliefs (placed / boxes) | 8/8 / 8/8 | 3/4 / 3/4 | 0/5 | 2.8 s | 5.6 s | pass |
| 3.6 Flash, low, high, with beliefs | 8/8 / 8/8 | 4/4 / 4/4 | 0/5 | 2.9 s | 7.0 s | pass |
| 3.5 Flash-Lite, low, high | 8/8 / 8/8 | 4/4 / 4/4 | 0/5 | 1.5 s | 2.3 s | pass |
| 4 Hydrogen, low, high | 7/8 / 7/8 | 4/4 / 4/4 | 0/5 | 3.6 s | 5.0 s | fail: keys |
| 3.6 Flash, minimal, high (close-ups only) | 7/8 | | | 2.0 s | 3.3 s | |
| 3.6 Flash, low, medium res (close-ups only) | 8/8 | | | 2.0 s | 2.7 s | |
| 3.5 Flash-Lite, minimal, high (close-ups only) | 7/8 | | | 1.5 s | 2.0 s | |
| **3.6 Flash, low, high, no beliefs, after the keys fix** | 8/8 / 8/8 | 4/4 / 4/4 | 0/5 | 3.3 s | 7.2 s | pass |

Every Gemini run had the room right on every frame, no stray items, and every empty landmark listed in view. All Gemini misses were keys frames: the seeded description named an orange lanyard the keys do not have. With the description fixed (last row), nothing was missed.

## Open questions for the humans

- **D26 C (remember unregistered objects): decide by 01:00 Sun**, once CP1 and CP4 pass. D26 has both options, the risks (other people's things, as CP3's keyring showed) and the pitch line if it is not built. "Add an item" (A) is in step 08 either way.

- **Frames to add later (deferred 14 Nov to save time):** about 6 medium shots (SAM 3's weak spot), 2 with an item in a hand (`in_hand` is untested), 1 of the bathroom corner (no-capture rule), 1 with an item on a different table. Name them like the others; only new frames cost calls.
- **One chair:** the frames use two chairs (the gray stool and a blue-cushioned one). D1 says stage one.
- 3D scan (D25): judges liked the point cloud idea on 14 Nov. Plan: finish the original steps first; after CP3 and CP4, maybe A (3D view on the dashboard, 2 to 3 h, no pipeline change) and C (local room check against the scan before frames go to Gemini, 2 to 4 h more). Optional now: record the scan video while the staging is up.
- **Rehearsal reset (needs a yes from whoever owns the dummy data):** the shared Supabase log mixes a teammate's dummy rows (64 questions, 9 sightings incl. the new "brown bag" and "orange water bottle") with three CP3 replays. Since the replays wrote observations from non-`dummy` devices, `supabase/dummy_data.sql` now refuses to reload until the reset runs. Reset, then replay once more for a clean CP3 record: `uv run python -m scripts.replay_video recordings/IMG_2092.MOV --interval 0.5 --ask "glasses,watch,bag,water bottle"`.
- **New items on Supabase, not in `seed.sql`:** "brown bag" (alias "bag") and "orange water bottle" (alias "water bottle"). Their aliases are other items' names, so "where is my bag?" may resolve to either. SAM 3 looks for them by name, unmeasured. Add them to `seed.sql` or delete them.
- **False sightings from other people's tables:** see the CP3 caveat. For the demo video keep other desks out of frame; a sturdier fix is a short description of the staged table in the prompt (landmark description), which needs a re-measure.
- `APP_TOKEN` was empty in `.env`; step 06 filled it with a random value. The capture page (step 07) and anyone replaying need the same value.
- **The person in IMG_2092.MOV (32 to 35 s) went to Gemini (free-tier key) and Roboflow** with the user's go-ahead on 15 Nov: the team is revising that rule. Update the hard rules in `CLAUDE.md`, D20 and D24 to the new wording so later sessions follow it.
- **Before any real camera frame (step 06 replay of a real walk, step 07):** link a billing account to the Google AI Studio project behind `GOOGLE_API_KEY`, then turn logging off (AI Studio, Logs and Datasets; it turns on by default with billing), and check its per-model rate limit in AI Studio (the capture page sends up to 30 frames a minute). On the free tier Google may use and human-review the images (D24).
- **⚠ D5 and D6 are decided but UNVERIFIED** (MacBook Pro, Coder workspace, Cloudflare Quick Tunnel, iPhone 17). Run checks A1 to A6 in `docs/DECISIONS.md` D5 in the first end-to-end test (step 03 at the latest) and write the results here. Each check has a fallback.
- Humans, before step 03: Coder server and a Docker workspace on the Mac (screenshot it), the tunnel address in `PUBLIC_BASE_URL` (empty now), a name for who owns the Mac during judging, and ask the Coder table whether a self-hosted server counts (D6).
- After step 01: make the Supabase MCP read-only by adding `&read_only=true` to the URL in `.mcp.json`.
- Stage one table and one chair and keep the classroom's other tables and chairs out of frame, or "on the table" does not say which one. Want more precise spoken names ("the table by the window")? One SQL update on `landmarks.spoken_name`.
- The bag, watch and water bottle have no usual place. One SQL update on `items.home_landmark_id` adds one.
- Tom: the dummy data now uses the classroom names. Pull, then reload `supabase/dummy_data.sql` if you want test sightings.
- D4: pick a cut-off time for Chert's answer; FaceTime is 4 to 6 hours.
- D15: keep "did you find it?"? It needs a second Vapi tool; the database side (`ask_item`, `record_outcome`) is ready.
- Photo idea (14 Nov): keep the item's last good view instead of its best-confidence one, and a wider "context" crop that shows the landmark. Decide in step 06. Step 05 evidence (crops in `.cache/live/crops/`): close-up crops are sharp and clear (129 to 1024 px wide; the smallest is the keys on the carpet); medium-distance crops are 69 to 268 px wide and blurry, the medium watch on the chair only 69 x 108. Suggestion: keep the tight crop, and add a context crop at least about 320 px on its short side when the item box is small. Full frames stay out (hard rule).
- `package.json`, `package-lock.json` and `node_modules/` (`@supabase/server`) appeared in the repo root at 15:36. The app is Python; delete them unless someone needs them.

## Things that differ from the docs or from CLAUDE.md

- The `google-genai` SDK retries 408, 409, 429 and 5xx up to 4 times inside each call by default, and its `timeout` let one call run 94 s. The bake-off turns that off (`HttpRetryOptions(attempts=1)`) and wraps calls in `asyncio.timeout`; the rules file now says the same for step 05. On the free tier, 4 calls in flight drew a 429 storm; 1 in flight drew none.
- `gemini-3.8-flash` timed out again on its step 04 retry (60 s). Not used.
- Frame names: `empty_<landmark>_<nn>.jpg` added beside `empty_<room>_<nn>.jpg`, so the bake-off can check that the model lists an empty landmark in view (absence needs it). Step 04 command and `docs/ROBOFLOW.md` updated. The 17 frames were renamed to the pattern (`close_blue_waterbottle_chair.JPG` became `close_water-bottle_chair_01.jpg`; `medium_empty_*` became `empty_*`).
- Committed fixture frames are 1920 px copies with no metadata (12.6 MB), byte for byte what the bake-off sent. The 24 MP originals, which carry GPS coordinates in their EXIF, are kept in the gitignored `tests/fixtures/frames/originals/`.
- Roboflow's docs say Model Monitoring does not save inference images by default; every call also sends `disable_model_monitoring: true` (D20).
- Perception switched from Claude to Gemini on 14 Nov (D24). `anthropic` is gone from the dependencies; `google-genai` 3.3.0 replaces it. `ANTHROPIC_API_KEY` became `GOOGLE_API_KEY`, and the local `.env` had its stale `PERCEPTION_MODEL=claude-haiku-5-5` replaced. `CLAUDE.md`, the perception rules, steps 00, 04, 05 and 11, `docs/ROBOFLOW.md` and D6 now say Gemini.
- Google's docs now lead with the Interactions API; `generateContent` is legacy but supported. Interactions stores requests by default, hence `store=False` everywhere.
- Step 06: the replay script takes `--interval` (seconds between frames) instead of the step's `--fps`, to match D10's wording. It sends frames in real time by default (`--speed` to go faster) so Gemini's busy slots behave as live.
- Step 06: the "drop frames while Gemini is busy" rule became a line one frame long per device (newer replaces older), because plain dropping lost two of four second looks in CP3 (table above).
- Step 06: an item with no measured SAM 3 wording is looked for by its own name instead of opening the gate for every frame (`detector.prompts_for`); only a home with more than 16 items still fails open.
- Step 06: the duplicate filter keeps a duplicate when the last accepted frame logged a sighting (the tentative exception, approximated: the worker cannot see the stay's status) and when the last accepted frame is 10 s old, so a still camera keeps sending looks for `mark_absent`.
- Step 06: the supabase-py `DeprecationWarning` is fixed: `db.py` passes its own `httpx.AsyncClient` (10 s, shared by PostgREST and Storage). Read path re-measured: `find_item` median 57 ms over 10 calls.
- Step 06: the write path reads `rooms`, `places` and `items` directly (name-to-id map) and upserts `observations`; neither has a function in 0001. `numpy` added for the filters.
- Step 05: the perception contract in `CLAUDE.md` now shows what the code returns: `perceive()` returns `PerceiveResult` (gate, timings, `perception` or None), landmarks are addresses, items carry `box` and `box_source`. New modules `perceive.py`, `frame.py` and `retry.py` added to the layout.
- SAM 3's response fields (`prompt_index`, `masks`, `confidence`) are not in Roboflow's SAM 3 page; `detector.py` reads them as recorded in step 04 and 05 (`tests/fixtures/responses/`).
- Live runs print a `DeprecationWarning` from supabase-py 2.34.1 itself: with no `httpx_client` in the options it passes `timeout` and `verify` to postgrest-py, which deprecated them. Unit tests never hit it. Fix in step 06, which adds Storage to `db.py`: pass one `httpx.AsyncClient` as `httpx_client` (it is shared by PostgREST and Storage, so give uploads a longer timeout than the 2 s read path) and re-check the read-path latency.
- New modules not in the original layout: `app/ask.py` (one question: database, `speak()`, fallback, log line; shared by `/find` and the voice tools) and `app/memory/schema.py` (`FindResult`, `Place`). Added to the layout in `CLAUDE.md`.
- `speak()` choices where the voice rules are silent: `usual` has no relation, so it is always "on" its landmark (as in the template); a missing `confident` counts as not confident; 58 and 59 minutes say "fifty-five" to stay in the 10 to 59 band. Change the rules file to change these.
- Ruff treats the repo's `supabase/` SQL folder as a first-party package, so `pyproject.toml` marks `supabase` as third-party for import sorting.
- Settings: read them with `app.config.get_settings()`, never at import time. Empty values in `.env` count as unset. URL fields drop a trailing slash. Tests use only the fakes in `tests/conftest.py`, never `.env`.
- Ruff 0.17 also formats Python code blocks in Markdown. I fixed two snippets in `docs/ROBOFLOW.md` and `docs/SUPABASE.md` so `ruff format --check .` is clean.
- uv on this machine is set to manual Python downloads; run `uv python install 3.12` once before `uv sync`.
- Supabase keys are the new `sb_publishable_...` and `sb_secret_...` keys; env names are `SUPABASE_PUBLISHABLE_KEY` and `SUPABASE_SECRET_KEY`. https://supabase.com/docs/guides/getting-started/migrating-to-new-api-keys
- Supabase runs Postgres 17.11 with pgvector 0.8.2; scratch runs 16.16 with 0.8.7. Schema definitions compared identical after applying.
- New Supabase projects ship `public.rls_auto_enable()` (event trigger `ensure_rls`), executable by `anon`. The advisor flagged it; `0002` revokes it. An event trigger fires without EXECUTE (checked on scratch).
- Security advisor now shows only `rls_enabled_no_policy` (INFO, 10 tables: deliberate, no role but `service_role` has a grant, so RLS is never reached) and `extension_in_public` (accepted).
- I pinned `search_path` on every function (not in the step list) so the advisor's `function_search_path_mutable` never fires; test section 25 enforces it.
