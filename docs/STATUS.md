# Status

Claude Code updates this at the end of every step. Humans edit it freely. Keep it under one screen.

Last updated: Sun 15 Nov 03:05 EST. **Start here: D33 in `docs/DECISIONS.md`** (the judge's asks, the plan to the 05:00 freeze, and why the FaceTime agent cannot see the camera yet).
**Rank 3 backend done** (below). Next: `POST /locate`.
**Tom (and Tom's agent): read `docs/HANDOFF_TOM.md` first**: merging the photo card with `photo_url`, `where_to_look` and `report_concern`.
Research report on medical, safety and analytics uses of the data: `docs/research/save-it-data-and-safety-ideas.md` (notes in `docs/research/notes/`).
**Insights MVP done (02:45):** three designs from `docs/INSIGHTS.md` built as MVPs, no sample data (Haru's call): wear time (`wear_minutes`, counted in the worker), change from usual (`GET /api/patterns`), and confirm-then-family (`report_concern` in the agent, `POST /concerns`, `GET /api/concerns`, `.../handle`). Migration `0005_insights` applied to Supabase at 02:38 (21 checks on scratch first; advisor unchanged). 49 new Python tests (385 total), 7 new agent tests (36). End to end on Supabase, test rows deleted. Not built: dashboard views (step 08), a family notification channel, the clinician page. **Tom:** `agent/agent.mjs` and `agent/prompt.mjs` changed (safety tool and rules; expect a small merge); please voice-test the near misses in docs/CHERT.md "Safety".

**D33 Rank 3 backend (done 15 Nov 01:30):** `/snapshot` entries gain `where_to_look` (places ranked with whole percentages, `why`, `band`, `ruled_out`) and `photo_url` (signed crop link, 1 h). Additive: every older field is unchanged. Contract in `docs/CHERT.md` "Where to look and the last-seen photo", weights in `app/look.py` (pure; last seen, newer one-frame glimpses, `item_usual_places` habits, the family's home place, a constant "somewhere else"). One extra read per snapshot (`db.look_evidence`: `places`, `item_usual_places`, tentative sightings in 24 h, run alongside the `find_item` calls) and one Storage request (`db.sign_photos`). 29 new tests (336 total). Live on Supabase: all 5 items ranked (each `high`, last seen on its landmark 89 to 91%); with the token all 5 links open as JPEGs; without it, no links. Warm `/snapshot` 190 ms without the token, 270 to 340 ms with it; first call 1.2 s. **Tom:** set `APP_TOKEN` in `agent/.env.local` to the backend's value for photos (`saveit.mjs` already sends it); the prompt and card do not read `where_to_look` yet.

## Steps

| # | Step | State | Notes |
|---|---|---|---|
| 00 | Scaffold | done | uv project (Python 3.12.15, `uv.lock` committed), ruff, package layout, `app/config.py` (`get_settings()`), `GET /health`, 10 tests. Left for humans: D5 and D6 (below) |
| 01 | Supabase | done | `0001` (8 fixes) and `0002` applied; 75/75 checks on scratch (82/82 with Supabase roles); home seeded; private `crops` bucket; smoke test and API key checks pass; `ask_item` median 98 ms over HTTPS. Left: MCP read-only (below) |
| 01b | Ranked search | todo | `rank_item`, `record_miss` (planning chat): 59/59 checks against the original 0001, not the applied one. Renumbered to `0003` (Haru's `0002` is applied). Re-test on scratch against the applied 0001 (pinned `search_path`, explicit grants, test section 25), then apply |
| 02 | Find API and speak() | done | `GET /find?item=...&channel=web` -> `app.ask.ask()` -> `db.ask_item` + `speak()`; 80 new tests (90 total). Live on Supabase: "my specs" -> "I last saw your glasses on the kitchen counter about forty minutes ago." 20 calls: median 50 ms, worst 114 ms; first call after a restart 115 to 160 ms (one 865 ms outlier, likely cold DNS). Dead database: fallback at 2.0 s; bad hostname: 46 ms. Smoke rows deleted |
| 03 | Phone voice | cut | Vapi is cut (D33): people ask through FaceTime (step 10) |
| 04 | Detector bake-off | done | CP2 passes zero-shot (table below, D3). `scripts/bakeoff.py` (cached in `.cache/bakeoff/`), 17 frames renamed to the pattern, hand-drawn boxes in `tests/fixtures/frames/boxes.json`, `db.perception_context()` + `PerceptionContext`, Pillow added; 23 new tests (113 total). Keys description fixed on Supabase and in `seed.sql`. Fixtures are 1920 px copies. Deferred by the team to save time: the extra frames (below) |
| 05 | Perception module | done | `perceive(frame, context, empty_look=)` in `app/perception/`: SAM 3 gate, then Gemini (thinking `low`, resolution `high`, no beliefs, `store=False`), SAM 3 box swapped in at IoU 0.5. SAM 3 failure fails open; Gemini failure gives `perception=None`. `apply_drop_rules()`, `load_frame()` (EXIF rotation, no metadata), `crop()`, shared retries. Live on all 17 fixtures: **17/17 fully correct** (room, landmark, item), all 12 crop boxes from SAM 3. 101 new tests (214 total) incl. an offline replay of the recorded live answers. The bake-off now imports the moved schema, prompt and drop rules (its cache still hits) |
| 06 | Ingest worker | done | `POST /frames` (Bearer `APP_TOKEN`, replies 202, works in the background) -> `app/worker/ingest.py`: blur and duplicate filters, context and name-to-id map (cached 30 s), `perceive()`, drop rules (no-capture rooms from the `rooms` table), observation upsert on the idempotency key, crop upload, `log_sighting`, `mark_absent`; one log line per frame with status and ms per stage. At most 2 Gemini calls in flight plus a line one frame long per device (a newer frame replaces the waiting one). `scripts/replay_video.py --interval`. 66 new tests (280 total). CP3 below |
| 07 | Capture page | deferred | D33: the demo is pre-recorded and uses `scripts/replay_video.py --interval 0.5`, so no tunnel is needed. If built later: Send a JPEG every **0.5 s** (D10) to `POST /frames` as multipart `frame`, `device_id`, `captured_at` (ISO 8601 with zone), header `Authorization: Bearer <APP_TOKEN>`. Long side at most 1920 px |
| 08 | Dashboard | todo | Now includes "add an item" (D26 A, about 1 h more): a form and `POST /api/items` that refuses names or aliases that clash. Show a sighting with no item as "unregistered object" |
| 09 | Typesense | done | Keyword only (no embeddings, ~180 MB RAM). `app.ask.ask()` calls `names.resolve()` before `ask_item`, so /find and the FaceTime agent both get it; any failure, or 300 ms, falls back to the raw words. A hit counts only if every word of the name or of one alias matched ("house phone" stays unknown). Typo lengths count the word stem, tuned to 5 and 8 letters so "nurse" does not become "purse". Live: "spectecles", "my reading glases", "black reading glasses", "car keys", "bags", "water botle" resolve in ~2 ms; "dentures", "wallet", "nurse" stay unknown; /find answered with Typesense stopped (2 web rows left in `queries`). Known: "glasses case" resolves to glasses. Not built: synonym sets (aliases do that job), hybrid/NL/RAG, analytics. Run: `docker start saveit-typesense` (local 30.2, key in `.env`), then `uv run python -m scripts.sync_typesense` after items or aliases change |
| 10 | FaceTime | doing | **Caller video is blocked in four places (D33): audio-only subscribe, `videoEnabled: false`, the Gemini plugin's empty `pushVideo`, and the prompt; Chert caller capture unverified. Tom: the 15-minute track check in D33 first.** The agent loads `GET /snapshot` (every item's sentence, no question logged) when a call starts and answers known items in one model turn, in its own words, with places and times kept as given; transcripts drive the card and the question log through `/find`. Gemini thinking off by default. Spoken-question benchmark through LiveKit, first sound after the question: 1.8 to 3.8 s, median about 2.2 s (was 3.2 to 4.9 s); answers 3 to 4.4 s long (was 6.8 to 7.6 s). No `find_object` tool while a snapshot is loaded (Tom's test call: it answered the bag and looked it up, then repeated itself). Card marker: green about 0.3 s after the caller's voice starts (level meter on their audio, no word). No promises to contact family anywhere (tools without backends removed; `speak()` no longer says "let me check with your family"). "Bag" now asks which one, like the water bottle. Spoken name now Find It; asks "the blue one or the green one?" when two items fit (looks in the snapshot), tested by voice against Gemini at about 1.5 s a turn. Browser test calls: `npm run web-call`. "Not there" and "I put it..." still save nothing (no `/miss`, `/told`). Caller video still blocked on D4 |
| 11 | Harden and record | todo | |
| 12 | Unregistered objects | todo | optional (D26 C, `/step-12-unregistered`). Start only after CP1 and CP4 pass and by 01:00 Sun; otherwise it is a "next step" in the pitch |

State is one of: todo, doing, done, stubbed (works with fake data), blocked (say on what).

## Checkpoints

- CP1 (since D33: a FaceTime call to the Chert line answers from camera data): not yet. The database was reset on 14 Nov 23:20 for a clean end-to-end run.
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

- `agent/fake-home.mjs` + `speakStub()` in `agent/saveit.mjs`: the fake home, used only while `BACKEND_URL` in `agent/.env.local` is empty.
- `agent/saveit.mjs` backend mode: `report_not_there` and `record_placement` save nothing yet (no `/miss`, `/told`): "not there" offers the usual place once, then family. Contract in docs/CHERT.md.

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

- **Plan to the freeze is D33** (15 Nov 01:00): Rank 3 backend ("where to look" + photo link in `/snapshot`, done 01:30), then `POST /locate`, then the dashboard view (Haru with Claude Code); the caller-video check, the photo card, then the arrow (Tom); from 02:30 stage, rehearse, film, Devpost. D26 C (Rank 2) passed its 01:00 deadline: only if everything else is done.

- **Frames to add later (deferred 14 Nov to save time):** about 6 medium shots (SAM 3's weak spot), 2 with an item in a hand (`in_hand` is untested), 1 of the bathroom corner (no-capture rule), 1 with an item on a different table. Name them like the others; only new frames cost calls.
- **One chair:** the frames use two chairs (the gray stool and a blue-cushioned one). D1 says stage one.
- 3D scan (D25): judges liked the point cloud idea on 14 Nov. Plan: finish the original steps first; after CP3 and CP4, maybe A (3D view on the dashboard, 2 to 3 h, no pipeline change) and C (local room check against the scan before frames go to Gemini, 2 to 4 h more). Optional now: record the scan video while the staging is up.
- Rehearsal reset done (Sat 14 Nov 23:20 EST, D33): 80 questions, 13 sightings, 32 observations deleted; rooms, landmarks and all 7 items kept (the look-alikes too). Run the next replay on this clean log: `uv run python -m scripts.replay_video recordings/IMG_2092.MOV --interval 0.5 --ask "glasses,watch,bag,water bottle"`.
- **New items on Supabase, not in `seed.sql`:** "brown bag" (alias "bag") and "orange water bottle" (alias "water bottle"). Their aliases are other items' names, so "where is my bag?" may resolve to either. SAM 3 looks for them by name, unmeasured. Add them to `seed.sql` or delete them.
- **False sightings from other people's tables:** see the CP3 caveat. For the demo video keep other desks out of frame; a sturdier fix is a short description of the staged table in the prompt (landmark description), which needs a re-measure.
- `APP_TOKEN` was empty in `.env`; step 06 filled it with a random value. The capture page (step 07) and anyone replaying need the same value.
- **The person in IMG_2092.MOV (32 to 35 s) went to Gemini (free-tier key) and Roboflow** with the user's go-ahead on 15 Nov: the team is revising that rule. Update the hard rules in `CLAUDE.md`, D20 and D24 to the new wording so later sessions follow it.
- **Before any real camera frame (step 06 replay of a real walk, step 07):** link a billing account to the Google AI Studio project behind `GOOGLE_API_KEY`, then turn logging off (AI Studio, Logs and Datasets; it turns on by default with billing), and check its per-model rate limit in AI Studio (the capture page sends up to 30 frames a minute). On the free tier Google may use and human-review the images (D24).
- **Coder (Tom, 14 Nov 20:50):** we use the event's hosted deployment, not a server on the Mac (D5, D6 changed). Tom's workspace `save-it` is set up by `scripts/coder_setup.sh` (96 Python and 14 agent tests pass on the pushed `df241d5`). No public ports there, so the public address is still a Quick Tunnel, now started in the workspace. No Docker in workspaces: the database tests and the local `saveit-typesense` container stay on a laptop, so in a workspace `names.resolve()` falls back until Typesense runs another way. All in `docs/CODER.md`.
- **⚠ D5 checks UNVERIFIED:** run A1 to A6 in `docs/DECISIONS.md` D5 in the first end-to-end test and write the results here. Humans: screenshot the workspace for Devpost, name who owns it during judging, put the tunnel address in `PUBLIC_BASE_URL`, and ask the Coder table the three questions in `docs/CODER.md`.
- After step 01: make the Supabase MCP read-only by adding `&read_only=true` to the URL in `.mcp.json`.
- Stage one table and one chair and keep the classroom's other tables and chairs out of frame, or "on the table" does not say which one. Want more precise spoken names ("the table by the window")? One SQL update on `landmarks.spoken_name`.
- The bag, watch and water bottle have no usual place. One SQL update on `items.home_landmark_id` adds one.
- Tom: the dummy data now uses the classroom names. Pull, then reload `supabase/dummy_data.sql` if you want test sightings.
- D4: pick a cut-off time for Chert's answer; FaceTime is 4 to 6 hours.
- D15: keep "did you find it?"? It needs a second Vapi tool; the database side (`ask_item`, `record_outcome`) is ready.
- Photo idea (14 Nov): keep the item's last good view instead of its best-confidence one, and a wider "context" crop that shows the landmark. Decide in step 06. Step 05 evidence (crops in `.cache/live/crops/`): close-up crops are sharp and clear (129 to 1024 px wide; the smallest is the keys on the carpet); medium-distance crops are 69 to 268 px wide and blurry, the medium watch on the chair only 69 x 108. Suggestion: keep the tight crop, and add a context crop at least about 320 px on its short side when the item box is small. Full frames stay out (hard rule).
- `package.json`, `package-lock.json` and `node_modules/` (`@supabase/server`) appeared in the repo root at 15:36. The app is Python; delete them unless someone needs them.
- Merged 14 Nov 21:48 EST: `tom/read-side` is in `main`; work on `main` from now on. `0003` is still not applied to Supabase. Tom's read-side decisions were renumbered D24-D29 -> D27-D32 (Haru's D24-D26 were on main first), and D26 C's planned migration is now `0004`.
- For Haru: Supabase now holds a classroom home (table, chair, floor; bathroom no-capture; plus watch and water bottle) that is not in `seed.sql`, so `dummy_data.sql` refuses to run. Please commit the classroom seed.
- Dummy sightings for the classroom were loaded at 19:20 (Tom asked), only through `log_sighting` and `mark_absent`: glasses on the table (chair before), keys in hand, water bottle next to the chair, watch gone from the table, bag never seen. Clear them with the rehearsal reset before real camera data.
- For Haru: your replay (`replay-05s-line`, from 21:11) writes into the same home the FaceTime agent is tested on, so answers change mid-test and the test look-alikes (brown bag, orange water bottle, not in your scene) get marked "not there anymore". That is correct behaviour, but it makes ground truth move. A second test home (another `HOME_ID`, same schema) would keep agent tests and your pipeline apart. Worth it?
- For Haru: look-alikes need (1) a `description` that tells them apart at enrollment ("big white mug" against "small white espresso cup"), since the agent asks with it, and (2) perception that tells them apart when logging (D8, `match_item`), or sightings land on the wrong one.
- For Haru: Tom renamed the assistant to **Find It** (what callers hear and see on the card). Repo, docs and internal ids still say Save It. Rename the project and the Devpost entry too?
- For Haru: Tom had two look-alikes enrolled in Supabase at 20:50 for testing "which one?": `brown bag` (alias `bag`; dummy stay on the floor) and `orange water bottle` (alias `water bottle`; dummy stays on the chair, then the table). They are not in `seed.sql` or the Typesense copy (re-run `scripts/sync_typesense.py`). Keep them for the demo, or delete them after the rehearsal reset?
- Enroll a wallet and a phone in the demo home? On the first test call they were the first things asked for; D2 kept the demo to glasses, keys and the bag.
- Confirm the read-side direction (D27, D28, D30 in docs/DECISIONS.md): voice uses `rank_item`, Typesense beyond name matching, Chert FaceTime as the main channel.
- For Haru: Roboflow: applying for the academic/research plan makes all data in that workspace public on Roboflow Universe (Roboflow docs). That confirms the hard rule.
- For Haru: Ranking trust depends on writing the right `p_event`/`p_source`: camera `seen`/`worn_cam`; family form `told`/`manual`; the person on a call `told`/`facetime_caller`.
- For Haru: `observations.room_id` (the wearer's room) drives `rank_item`'s walking order. Keep writing it for every frame.
- For Haru: Landmarks can set the new nullable `find_chance` (0–1) and `check_seconds`. Null means the default by kind.

## Things that differ from the docs or from CLAUDE.md

- D33 did not say who may see photo links. `/snapshot` itself stays open (the agent may run without a token), but `photo_url` comes only with `Authorization: Bearer <APP_TOKEN>`, since a signed link opens a private crop to anyone who has it. The ranking does not use 0003's `rank_item` (not applied); it reads `item_usual_places` as D33 says and borrows `rank_item`'s band cut-offs, so the two can be compared once 01b lands.
- Crops seen through the new photo links (15 Nov): the glasses crop cuts off the right lens (box from step 06), and the keys crop is about 90 x 60 px (the false keyring sighting), which will look blurry on the card. The context-crop idea under open questions would fix both.
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
- Chert starter is JavaScript, needs Node 22.12+ and `OPENAI_API_KEY`; a Python agent works via `chert dev --agent NAME` (npm `@trychert/facetime@0.1.0-beta.21`). Details in docs/CHERT.md.
- Our agent uses Gemini Live instead of OpenAI (D23). `@livekit/agents-plugin-google@1.8.0` drops caller video for Gemini Live and breaks `generateReply` on "3.1" models.
- VS Code's `python.terminal.useEnvFile` (on in Tom's settings) injects the repo `.env` into every terminal, and `node --env-file` keeps injected values: the agent registered as `my-agent` (the root `.env` value) and Chert declined calls. `agent/env.mjs` now applies `agent/.env.local` first and drops `SUPABASE_*`/`DATABASE_URL`. Since 14 Nov it is off for this workspace on Tom's Mac (`.vscode/settings.json`, gitignored) and the stray `AGENT_NAME` is out of the root `.env`; terminals opened before that still carry the old values.
- FaceTime on an iPhone held upright crops about 100 px off each side of the agent's 1280×720 video. The card keeps text 160 px in: at most 16 characters per line at 70 px (DASHBOARD.md had said 22 at 56 px).
- `ask_item` matches names and aliases exactly, so "where are my glasses" came back `unknown_item`. The agent now drops filler words before `/find`; Typesense would do this properly (D28).
- voice.md `unknown_item` changed (Tom, 14 Nov): name the thing back ("I don't know your wallet yet, but your family can teach me."); ask "which thing" only when we did not catch one or two words.
