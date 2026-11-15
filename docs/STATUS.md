# Status

Claude Code updates this at the end of every step. Humans edit it freely. Keep it under one screen.

Last updated: Sun 15 Nov 03:10 EST (Tom's Claude Code, room session: the splat builder and `GET /room` work end to end, row 14; the room page no longer speaks unless switched on). Before that: Sun 15 Nov 03:05 EST (Tom's Claude Code: FaceTime photo shown whole and wider; the robotic voice traced to the room page). Another Claude Code session on Tom's Mac is building the 3D room view at the same time and also edits this file. Before that: Sat 14 Nov 21:48 EST, `tom/read-side` merged into `main`. Both work on `main`.

## Steps

| # | Step | State | Notes |
|---|---|---|---|
| 00 | Scaffold | done | uv project (Python 3.12.15, `uv.lock` committed), ruff, package layout, `app/config.py` (`get_settings()`), `GET /health`, 10 tests. Left for humans: D5 and D6 (below) |
| 01 | Supabase | done | `0001` (8 fixes) and `0002` applied; 75/75 checks on scratch (82/82 with Supabase roles); home seeded; private `crops` bucket; smoke test and API key checks pass; `ask_item` median 98 ms over HTTPS. Left: MCP read-only (below) |
| 01b | Ranked search | todo | `rank_item`, `record_miss` (planning chat): 59/59 checks against the original 0001, not the applied one. Renumbered to `0003` (Haru's `0002` is applied). Re-test on scratch against the applied 0001 (pinned `search_path`, explicit grants, test section 25), then apply |
| 02 | Find API and speak() | done | `GET /find?item=...&channel=web` -> `app.ask.ask()` -> `db.ask_item` + `speak()`; 80 new tests (90 total). Live on Supabase: "my specs" -> "I last saw your glasses on the kitchen counter about forty minutes ago." 20 calls: median 50 ms, worst 114 ms; first call after a restart 115 to 160 ms (one 865 ms outlier, likely cold DNS). Dead database: fallback at 2.0 s; bad hostname: 46 ms. Smoke rows deleted |
| 03 | Phone voice | todo | Call `app.ask.ask(item, "phone")`, not `db.ask_item` + `speak()`: the 2 s timeout, fallback and log line are already there. `/find` has no auth yet; once the tunnel is up anyone can query it, so add a token check then |
| 04 | Detector bake-off | done | CP2 passes zero-shot (table below, D3). `scripts/bakeoff.py` (cached in `.cache/bakeoff/`), 17 frames renamed to the pattern, hand-drawn boxes in `tests/fixtures/frames/boxes.json`, `db.perception_context()` + `PerceptionContext`, Pillow added; 23 new tests (113 total). Keys description fixed on Supabase and in `seed.sql`. Fixtures are 1920 px copies. Deferred by the team to save time: the extra frames (below) |
| 05 | Perception module | done | `perceive(frame, context, empty_look=)` in `app/perception/`: SAM 3 gate, then Gemini (thinking `low`, resolution `high`, no beliefs, `store=False`), SAM 3 box swapped in at IoU 0.5. SAM 3 failure fails open; Gemini failure gives `perception=None`. `apply_drop_rules()`, `load_frame()` (EXIF rotation, no metadata), `crop()`, shared retries. Live on all 17 fixtures: **17/17 fully correct** (room, landmark, item), all 12 crop boxes from SAM 3. 101 new tests (214 total) incl. an offline replay of the recorded live answers. The bake-off now imports the moved schema, prompt and drop rules (its cache still hits) |
| 06 | Ingest worker | done | `POST /frames` (Bearer `APP_TOKEN`, replies 202, works in the background) -> `app/worker/ingest.py`: blur and duplicate filters, context and name-to-id map (cached 30 s), `perceive()`, drop rules (no-capture rooms from the `rooms` table), observation upsert on the idempotency key, crop upload, `log_sighting`, `mark_absent`; one log line per frame with status and ms per stage. At most 2 Gemini calls in flight plus a line one frame long per device (a newer frame replaces the waiting one). `scripts/replay_video.py --interval`. 66 new tests (280 total). CP3 below |
| 07 | Capture page | todo | Send a JPEG every **0.5 s** (D10) to `POST /frames` as multipart `frame`, `device_id`, `captured_at` (ISO 8601 with zone), header `Authorization: Bearer <APP_TOKEN>`. Long side at most 1920 px |
| 08 | Dashboard | todo | Now includes "add an item" (D26 A, about 1 h more): a form and `POST /api/items` that refuses names or aliases that clash. Show a sighting with no item as "unregistered object" |
| 09 | Typesense | done | Keyword only (no embeddings, ~180 MB RAM). `app.ask.ask()` calls `names.resolve()` before `ask_item`, so /find and the FaceTime agent both get it; any failure, or 300 ms, falls back to the raw words. A hit counts only if every word of the name or of one alias matched ("house phone" stays unknown). Typo lengths count the word stem, tuned to 5 and 8 letters so "nurse" does not become "purse". Live: "spectecles", "my reading glases", "black reading glasses", "car keys", "bags", "water botle" resolve in ~2 ms; "dentures", "wallet", "nurse" stay unknown; /find answered with Typesense stopped (2 web rows left in `queries`). Known: "glasses case" resolves to glasses. Not built: synonym sets (aliases do that job), hybrid/NL/RAG, analytics. Run: `docker start saveit-typesense` (local 30.2, key in `.env`), then `uv run python -m scripts.sync_typesense` after items or aliases change |
| 10 | FaceTime | doing | The agent loads `GET /snapshot` (every item's sentence, no question logged) when a call starts and answers known items in one model turn, in its own words, with places and times kept as given; transcripts drive the card and the question log through `/find`. Gemini thinking off by default. Spoken-question benchmark through LiveKit, first sound after the question: 1.8 to 3.8 s, median about 2.2 s (was 3.2 to 4.9 s); answers 3 to 4.4 s long (was 6.8 to 7.6 s). No `find_object` tool while a snapshot is loaded (Tom's test call: it answered the bag and looked it up, then repeated itself). Card marker: green about 0.3 s after the caller's voice starts (level meter on their audio, no word). No promises to contact family anywhere (tools without backends removed; `speak()` no longer says "let me check with your family"). "Bag" now asks which one, like the water bottle. Spoken name now Find It; asks "the blue one or the green one?" when two items fit (looks in the snapshot), tested by voice against Gemini at about 1.5 s a turn. Browser test calls: `npm run web-call`. "Not there" and "I put it..." still save nothing (no `/miss`, `/told`). Caller video still blocked on D4 |
| 11 | Harden and record | todo | |
| 12 | Unregistered objects | todo | optional (D26 C, `/step-12-unregistered`). Start only after CP1 and CP4 pass and by 01:00 Sun; otherwise it is a "next step" in the pitch |
| 13 | Moments: FaceTime photo, search by description | done, not yet tried on a call | Asked by Tom, 15 Nov. **Photo:** after an answer that says where a thing is, the FaceTime card shows the photo of that sighting with the place name on a band below; the place card goes up first and the photo replaces it when loaded, so the answer never waits. `GET /moments/{sighting_id}/photo` (needs `APP_TOKEN`) returns it sized for the card. New sightings get the wider moment photo with a ring on the thing: the ingest worker asks for it in the background for every logged look (`moments.record_soon`, added 15 Nov with Tom's go-ahead; cost measured below). The log was reset and `IMG_2092.MOV` processed again on 15 Nov 02:10 to 02:29 (below), so every stay now has its moment photo. **Search:** `GET /describe?q=` and the agent tool `find_by_description` turn "the silver one I wear on my wrist" into the item, then answer like `/find`. Typesense `moments` collection, hybrid: keywords plus a `gemini-embedding-2` vector made from each stay's crop and words; the backend keeps it in step with Postgres every 10 s. Live on the 5 demo items: described things answered in 0.4 to 0.8 s, "my wallet" gets "I don't know your wallet yet", photo on the card 0.6 to 2.1 s after the answer. 88 new Python tests (394), 13 new agent tests (42). **Not yet tried by voice on a call** (the browser call was started for Tom at 02:35) |
| 14 | Room scan: splat builder and 3D room view (D25 A) | done on sample scenes; **not yet run on our own room** | Asked by Tom, 15 Nov (he lifted the out-of-scope rule for this). `uv run python -m scripts.build_room video.mov` cuts frames on the laptop, sends the sharpest 32 (448 px) to the splat builder on a rented RTX 4090 (`splat/`, AnySplat, one forward pass, reached by SSH tunnel) and saves `preview.spz` + `full.spz` in `.cache/room/`. `GET /room` shows the room (three.js + Spark, served from `app/web/vendor/`), one large button per item; a tap shows the memory's sentence and the last-seen photo and flies to that landmark's pin. Pins are `landmarks.x/y/z`, placed by tapping in the 3D view (`PUT /room/pins`); things are never shown where the scan saw them. Measured on AnySplat's sample scenes: GPU 1.5 s (17 photos) and 2.6 s (32 photos) to a preview; from a video on Tom's Mac, preview saved after 4.4 s, both files after 5.8 s (44 s and 4 min when the hall network was at 30 to 60 KB/s). 39 new tests (the suite: 436 pass, 4 skipped), and 5 more that need torch: they pass on the GPU machine and check the GPU arithmetic against the numpy reference. All in `docs/SPLAT.md`. Not built: the refinement pass, a private-bucket copy of the scan |

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

Moments search, 15 Nov (`app/moments.py`; 5 items, 6 stays; 13 descriptions of enrolled things, 11 things that are not enrolled; cosine distance, lower is closer):

| | Result |
|---|---|
| Right item ranked first | 13 of 13 |
| Distance of the right item | 0.31 to 0.42 |
| Best wrong guess for an unknown thing (wallet, phone, dentures, TV remote...) | 0.41 to 0.45 |
| Cuts chosen | `MAX_DISTANCE` 0.425, `MARGIN` 0.035 (the best fit must beat the next item by this much) |
| Enrolled things answered with those cuts | 10 of 13. "What I drink from" declines; "the one I left on the chair" and "the thing on the floor" ask which one (place words alone do not separate items) |
| Unknown things answered wrongly | 0 of 11 |

A small sample with thin margins ("the tv remote" missed the cut by 0.006). Re-measure when items are added; the cuts lean towards "I don't know" on purpose.

What the moment photo hook costs the ingest worker, 15 Nov (worker run on fixture frames with the database and models faked as in `tests/test_ingest.py`, real image work, 40 frames per run, 3 runs each way):

| | Hook off | Hook on |
|---|---|---|
| Frame start to finish, median (50 ms stand-in for the models) | 80.1 to 80.5 ms | 79.6 to 80.8 ms |
| Same, worst frame | 91 to 94 ms | 90 to 98 ms |
| The `sightings` stage, median | 8.0 ms | 8.0 ms |

- The call the worker makes (`record_soon`) takes about 4 microseconds. The photo itself takes 12 ms (worst 15) in a worker thread, off the event loop.
- One moment photo is 21 to 78 KB (median 43 KB) on the 12 fixture frames with an item; the frame it comes from is 372 KB to 1.2 MB (median 661 KB) and already goes to SAM 3, and to Gemini when the gate opens.
- One upload at a time per stay, newest look wins: 40 looks at one stay with a 300 ms upload stored 11 photos, not 40.
- Real uploads, 15 Nov run on Tom's Mac (20 photos): 12 to 68 KB each, made in 7 to 18 ms, uploaded in 147 to 1,278 ms (median 238 ms), all in the background. The frames that kept an item took 19 s each on that link (SAM 3 and Gemini), so the photo was about 1 to 2% on top.

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

- **Room scan (row 14), to use it:** (1) film a slow 20 to 40 s walk around the staged table and chair, no people in shot; (2) `uv run python -m scripts.build_room <video>`; (3) open `/room`, type `APP_TOKEN`, press Place pins and tap the table, the chair and the floor once each. The room in `.cache/room/` right now is AnySplat's sample kitchen, and no landmark has a pin yet.
- **`/room` needs a backend started after 03:00.** The one on port 8000 (started 02:29) does not have the routes; restart it. Until then the room session's own backend on port 8010 serves it, and that one stops when that session ends.
- **A GPU is rented and billing: Vast.ai instance 60754139 (RTX 4090, about $0.47 an hour, $10.20 credit at 02:15).** Tom said yes to renting at 02:15. `scripts/splat_gpu.sh destroy` ends it; nothing else will. The tunnel (`scripts/splat_gpu.sh tunnel`) must be running for `build_room.py`.
- **Only staged scenes go to that GPU.** So far it has seen AnySplat's own sample images, nothing of ours. A scan of a real home, or frames with a person, needs the team's yes first (D25, `docs/SPLAT.md`).
- `app/web/vendor/` holds three.js 0.180.0 and Spark 2.4.0 (3.7 MB, MIT), so the room page loads without the venue network. Commit it with the page, or the page is blank on another machine.

- **For Haru: Tom's Claude Code changed two of your files on 15 Nov, with Tom's go-ahead.** `app/worker/ingest.py` gained one import and one call in the sightings loop, `moments.record_soon(frame, item.box, crop_url, sighting)`: for every logged look it has the wide moment photo made and uploaded in the background (`...Z.moment.jpg` beside the crop). It is not awaited and never raises; measured cost in "Tuned values". `tests/conftest.py` sets `MOMENT_PHOTOS=false` so your ingest tests stay offline, and `tests/test_ingest.py` has two new tests for the call. To turn it off anywhere: `MOMENT_PHOTOS=false` in `.env`.
- **The moment photo is not checked for faces.** It is a wide crop (all of an upright frame's width, at most half its area), so a person standing beside the thing can be in it. The hard rule in `CLAUDE.md`, the perception rules and D21 now say so. Fine for staged scenes; decide before a real home (blur faces, or keep it off).
- **The "robotic voice" on the 02:51 test call was not the agent.** It was the 3D room page (`app/web/room.html`, being built in another Claude Code session on Tom's Mac, served by that session's backend on port 8010). `choose(item, byHand)` there speaks the picked item's sentence with the browser's built-in speech (`speechSynthesis`, lines 366 to 373). The speakers played "I last saw your glasses on the table about forty minutes ago", the call's microphone picked it up, and the agent logged it as *heard* twice and tried `record_placement` for it (`POST /told`, 404, nothing saved). The room backend's log shows that page loading the glasses photo at those times. Fix on the room page's side: no speech, or a mute switch, or speech only when no call is running; or use headphones. Not changed here: that file belongs to the other session. **Fixed 03:08 by the room session:** the page is silent unless someone presses its "Read aloud" switch, and the headless browser that was tapping it for tests is stopped. Sorry for the false trail.
- **The photo was too zoomed in on that call; changed 15 Nov about 03:00** (Tom). Before, the caller saw about a tenth of the frame (a 3:2 window of 75% of the frame's width, then cut again to fill the card behind a two-line band). Now the moment photo is the widest 16:9 view the rule allows (all of an upright frame's width, at most half its area; 960 px, 32 to 74 KB on the six stored ones), the card shows it whole, the band is one line (the landmark), and the light sits in a corner: about a third of the frame, three times as much. The six stored photos were re-cut from the same video frames (one fresh `perceive()` each for the box); no database row changed. Close put-downs still show little around the thing, because the camera was close: the frame is all there is. Next step if that matters: keep the widest look of a stay instead of the most confident one.
- **Supabase was reset and the video processed again on Tom's Mac, 15 Nov 02:10 to 02:29** (Tom asked). Backup of the old log (21 questions, 6 sightings, 15 frame records): `.cache/supabase-backup-20261115-0215.json` on Tom's Mac. Result: 132 frames (one per 0.5 s), 20 stored, no errors; active stays: watch on the table (3 looks), keys on the table (4), water bottle on the chair (3), bag on the floor (5), glasses on the table (5); one tentative watch in a hand. `find_item` answers all five as `seen`.
  - **The keys stay is the false one from CP3's caveat:** its photo shows a keyring on a teammate's desk beside a laptop, with part of someone's arm. Delete it or re-film before the demo video.
  - **It was not a real-time replay.** Tom's link gave 2 to 17 s per SAM 3 call and 7 to 9 s per Gemini call, so `scripts/replay_video.py` would have lost nearly every frame. The frames (cut with the script's ffmpeg filter) went through `worker.ingest()` one after another with `DETECTOR_TIMEOUT_S=30` and `PERCEPTION_TIMEOUT_S=60`, capture times 0.5 s apart ending at 02:10. No frame was dropped as busy, so more frames were looked at than in the 14 Nov replay (20 stored against 15). The driver was a throwaway script, not in the repo.
  - Close put-downs fill the moment photo (watch, bottle, glasses), so those cards show no ring; the bag and the keys are ringed.
- **Tom's Mac was not set up for intake until 15 Nov 02:05:** `.env` had `PERCEPTION_MODEL=claude-haiku-5-5` (now `gemini-3.6-flash`) and no `ROBOFLOW_API_KEY` (Tom added it); `ffmpeg` is not installed (the run used the binary inside a conda environment's `imageio_ffmpeg`); the `coder port-forward ... 8090` process was stopped so the browser call could use port 8090. `ANTHROPIC_API_KEY` is still in that `.env`, unused.
- **`APP_TOKEN` was empty on Tom's Mac** in `.env` and `agent/.env.local`; 15 Nov 01:47 one random value was written to both (not printed anywhere). `/moments/.../photo` and `/frames` need it. A backend on another machine needs the same value in its `.env`.
- **Try it on a call** (`npm run web-call`, no Chert minutes): ask for the watch, then "the green one with the gold letters". Check that the photo appears after the place name, that the text band is readable, and how long the description tool takes by voice (each tool call cost about 1.5 s on the 14 Nov call).
- The live checks of `/describe` and `/find` on 15 Nov logged about a dozen test questions in `queries` (web and facetime). The rehearsal reset clears them.
- Embeddings send each stay's tight crop to the Gemini API once (`gemini-embedding-2`, same key as perception). The hard rule about real camera frames (billing-enabled project, logging off) applies to these calls too; the embeddings call has no `store` option.
- The local `saveit-typesense` container was restarted once (15 Nov, about 01:25) to stop a 605 MB model download that was using the hall's whole connection. `items` is intact; `moments` holds 6 stays. Rebuild it any time: `uv run python -m scripts.sync_moments`.

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

- Room scan: built although `CLAUDE.md` lists 3D scans as out of scope until the core demo passes (Tom asked, 15 Nov). D25 A planned a Scaniverse point cloud with `PLYLoader`; it is a Gaussian splat from AnySplat shown with Spark instead. What differs from the plan Tom supplied is listed at the end of `docs/SPLAT.md`.
- `splat/` is Python 3.10 code (the GPU machine's AnySplat environment) inside a 3.12 repo: ruff has a per-folder target, and `app/room.py` and `scripts/build_room.py` import only its numpy parts (`frames`, `spz`, `geometry`). New modules: `app/room.py`, `app/web/room.html`, `scripts/build_room.py`, `scripts/video_frames.swift`, `scripts/splat_gpu.sh`. New settings: `SPLAT_URL`, `SPLAT_TOKEN`, `ROOM_DIR`. `app/memory/db.py` gained `list_pins` and `set_pin` (a write to `landmarks.x/y/z` only).
- This Mac has no ffmpeg: `build_room.py` cuts video frames with AVFoundation through a small Swift program compiled on first use. `scripts/replay_video.py` still needs ffmpeg.

- Moments: Typesense's built-in image search (`docs/TYPESENSE.md` item 10, `ts/clip-vit-b-p32`) is not used. The model is a 605 MB download and the hall network gave 5 to 60 KB/s on 15 Nov. Vectors come from `gemini-embedding-2` instead (768 numbers; the crop and the words go in as one input and come back as one vector) and sit in a plain `float[]` field; the search sends the description's vector in `vector_query` through `POST /multi_search` with keywords in `q` (hybrid, `alpha` 0.7).
- `gemini-embedding-2` takes no `task_type`. Google's embeddings page (read 15 Nov; it now redirects to aistudio.google.com/docs/embeddings) says to prefix a text query with `task: search result | query: ` and to put no prefix on mixed picture-and-text input. A list of parts gives one vector, not one per part.
- Network, 15 Nov about 01:30: a 44 KB crop took 11 s from Supabase Storage at the worst moment (0.2 to 0.7 s later). Hence small photos, a photo cache in the backend, and the card showing the place name before the photo.
- The agent now lists `sharp` 0.35.3 as its own dependency (`@livekit/agents` already installed that version; only `package.json` and the lockfile changed). It is loaded on first use, so an agent without it still answers calls.
- New modules: `app/photo.py`, `app/moments.py`, `scripts/sync_moments.py`, `agent/photo.mjs`. The backend starts a background task (`moments.keep_current`) with the app; it does nothing without Typesense and a Google key.

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
