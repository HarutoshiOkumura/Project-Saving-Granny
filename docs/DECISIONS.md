# Decisions to settle

Each item has a default so nobody is blocked. Change a default by editing this file and telling Claude Code; it reads this file when a step depends on one.

Status key: OPEN (using default), DECIDED (write the choice and who chose).

## Settle in the first hour

**D1. Where is the "home" for the demo?** DECIDED (the team, 14 Nov)
The B School classroom at the hackathon, as one room named `b_school_classroom` (spoken "the classroom"), plus a `bathroom` corner where nothing is stored, for the privacy demo.
A classroom has many tables and chairs, so stage one table and one chair and keep the others out of frame; otherwise "on the table" does not say which one.
The names live in `supabase/seed.sql` (seeded on Supabase on 14 Nov) and must match what is staged.

**D2. Which items and landmarks, exactly?** DECIDED (the team, 14 Nov; replaces the step 01 home)
Landmarks in the classroom: `table`, `chair`, `floor` (the carpet).
Items: `glasses` and `keys` (both usually on the table), `bag` (the green FRANZI Milano handbag with gold lettering), `watch` (silver) and `water bottle` (dark blue); the last three have no usual place.
The glasses' usual place is the table so the demo can put them elsewhere and the "not there anymore" answer can offer the table.
Seeded from `supabase/seed.sql`. Every name here becomes an allowed answer for the vision model.

**D3. Which detector?** DECIDED (step 04 bake-off, 14 Nov, by Claude Code; the gate below answers the team's question "why does Gemini see every frame?". Change it here if you disagree)
Pass rule, CP2 in `PLAN.md`: each item found in at least 8 of 10 close-ups, at most 1 false alarm on the empty frames.
The set was smaller: 8 close-ups (1 or 2 per item), 4 medium, 5 empty, so "8 of 10" was applied per item as 80 percent rounded up, which means every close-up.
A detector hit needs IoU at least 0.5 against a hand-drawn box (`tests/fixtures/frames/boxes.json`).
Full tables: `docs/STATUS.md` and `uv run python -m scripts.bakeoff` (cached, free to re-run).

- **CP2 passes zero-shot. No training needed.**
  - SAM 3, wording "green handbag, eyeglasses, bunch of keys, wristwatch, dark blue bottle", threshold 0.7: 8/8 close-ups, 2/4 medium, 0 false alarms, 0 stray boxes, about 0.4 s.
  - `gemini-3.6-flash` alone (thinking `low`, resolution `high`): 8/8 close-ups placed on the right landmark, 3/4 medium, 0 false alarms, room right 17/17, its own `box_2d` boxes 8/8 close-ups. Median 2.8 s, worst 7.0 s.
    After the keys fix below: all 12 item frames placed and boxed, 0 false alarms, median 3.3 s, worst 7.2 s.
  - YOLO-World `v2-l` fails on keys and glasses at every wording and threshold. Plain names ("keys") make SAM 3 box single keys instead of the bunch, and "reading glasses" loses the glasses.
- **Design for step 05: SAM 3 gates Gemini.**
  1. Every frame that passes the blur and duplicate filters goes to SAM 3 with the wording above.
  2. Any demo item at or above 0.5 opens the gate. On the fixtures that opened all 12 item frames, each with its box on the item, and 1 of 5 empty frames (a "wristwatch" at 0.55 on bare carpet), where Gemini then reported nothing.
  3. Gate open: Gemini places the item (room, landmark, relation, in hand). SAM 3's own label is ignored, because it called the medium-distance watch "bunch of keys". The crop uses the SAM 3 box that overlaps Gemini's `box_2d` most (IoU at least 0.5), else Gemini's box.
  4. Gate closed: no Gemini call, except one "empty look" at most every 30 s for `mark_absent`, which ignores looks closer together than that anyway.
  - Why: during a walk most frames hold no demo item, so Gemini calls drop from up to 30 a minute to a few, fewer frames go to Google, and the free-tier rate limit stops mattering. Cost: SAM 3 adds about 0.4 s before Gemini, well inside the 10 s budget.
- **Gemini settings (D24): keep `gemini-3.6-flash`, thinking `low`, resolution `high`.**
  - `gemini-3.5-flash-lite` scored as well here (12/12 placed) in 1.5 s, but its notes repeat the seeded description ("keys on an orange lanyard") for keys that have no lanyard, so it echoes the prompt instead of describing the photo. Keep it as the fallback if latency or rate limits bite.
  - `gemini-4-hydrogen` missed the plain close-up of the keys on the table, and is slower (median 3.6 s). Not used.
  - Thinking `minimal` missed one keys close-up. Resolution `medium` held 8/8 close-ups in 2.0 s but was not tried at medium distance, where small items need the pixels.
  - Every Gemini miss in the bake-off was a keys frame, and every one was a total omission, not a low confidence. The seeded description said "keys on an orange lanyard"; the staged keys are a black car key fob with a few keys.
    Fixed on 14 Nov (the team chose to change the description): `black`, `car key fob with a few keys on a ring`, on Supabase and in `seed.sql`. 3.6 Flash then found all 3 keys frames, including the medium one it had missed.
- **Beliefs stay out of the prompt for now.**
  - Measured: with beliefs that put an item on every landmark in the empty frames, 3.6 Flash made 0 false sightings on 5 empty frames, 0 stray items, and placed all 6 items that sat away from their believed place correctly.
  - The one gain (the medium keys) was on a frame where the belief was true, so it cannot be told apart from suggestion.
  - A missed frame costs one frame; a false confirmation would keep an empty landmark "occupied" and block "not there anymore", step 4 of the demo. Revisit with more empty frames.
- **Training (`docs/ROBOFLOW.md` section 3) is optional.** It would help medium distance, SAM 3's weak spot (2/4 at 0.7). Not on the critical path.

**D4. Does the Chert line carry caller camera and agent video?** OPEN, ask Chert staff
This decides whether step 10 shows a photo or is audio only. Also confirm the per-call time cap and that one line means one call at a time.

**D5. Where does the backend run, and what is its public HTTPS address?** DECIDED (the team, 14 Nov: MacBook Pro and iPhone 17; the rest is Claude Code's plan, not yet tried)
Vapi needs a public HTTPS URL for the tool.
The phone needs HTTPS to open the camera.

- **Machine:** the team's MacBook Pro runs the backend during the demo, inside a Coder workspace (D6).
- **Phone:** the lanyard phone is an iPhone 17, using Safari.
- **Public address:** a Cloudflare Quick Tunnel started inside the workspace.
  `cloudflared tunnel --url http://localhost:8000` prints a `https://<random>.trycloudflare.com` address; put it in `PUBLIC_BASE_URL`.
- **Why this shape:** Coder is not in the path a call takes, so a Coder hiccup cannot drop a call once the workspace is running.
  Coder's docs do not say whether its own built-in tunnel can serve a public port reliably, so it is not used for that.
- **From the docs (checked 14 Nov):** a Quick Tunnel's hostname changes on every run and stops working when the process stops.
  It allows 200 in-flight requests, has no Server-Sent Events and no uptime guarantee.
  Web traffic to a workspace port does not count as Coder activity; an open editor, terminal or SSH session does.

Before every test run and the demo:

1. Plug in the Mac and run `caffeinate -dims` in a terminal for the whole session.
2. Turn autostop off for the workspace (template "Default autostop" off, or `coder schedule stop <workspace> manual`), then restart the workspace, because schedule changes apply on the next build.
3. Start `cloudflared` once and leave it running; restart only the API if needed.
   Every new tunnel address must go into three places: `.env`, the Vapi tool's server URL, and the capture page bookmark on the iPhone.
4. One person owns the Mac during judging: (name).

> **⚠ UNVERIFIED: none of the checks below has been tried yet.**
> Run all of them in the first end-to-end test (step 03's CP1 at the latest) and write each result in `docs/STATUS.md`.
> If a check fails, switch to its fallback, then run the check again.

| # | Assumption | How you notice it failed | Fallback |
|---|---|---|---|
| A1 | The venue network lets `cloudflared` connect out. | `cloudflared` prints connection errors and no `trycloudflare.com` address, or `curl <address>/health` from a phone on cellular does not return `{"ok":true}`. | Put the Mac on a teammate's phone hotspot (not the lanyard iPhone) and restart `cloudflared` (then step 3 above). |
| A2 | Coder runs a Docker workspace on the Mac, and the API starts in it. | The workspace shows Failed or Stopped in the Coder dashboard, or `curl localhost:8000/health` inside the workspace fails. | Run the API on the Mac itself (`uv run uvicorn app.main:app --port 8000`) with `cloudflared` on the Mac. Everything still works, but drop the Coder sentence from the pitch (D6). |
| A3 | Autostop is off, so the workspace keeps running with nobody's editor open. | The workspace page in the Coder dashboard shows a stop time. | Keep a `coder ssh <workspace>` session open in a Mac terminal during judging; an open session counts as activity. |
| A4 | The address in Vapi matches the running tunnel. | A call gets silence or the fallback sentence, and the Vapi call log shows a failed tool request. | Copy the current `trycloudflare.com` address into the Vapi tool's server URL and `.env`, and reopen the capture page on the iPhone. |
| A5 | Answers stay fast through the tunnel. | `curl -s -o /dev/null -w '%{time_total}\n' <address>/health` from a phone on cellular or another network takes more than 1 s. | Try the hotspot (A1). If it is still slow, note it in STATUS for step 11. |
| A6 | Safari on the iPhone 17 opens the camera on the tunnel address. | The capture page shows a camera error, or the permission prompt never appears. | Settings > Apps > Safari > Camera: Allow, and open the page in Safari itself, not inside another app. For the video, use the replay path (CP4 in `PLAN.md`). |

**D6. What counts as using Coder?** DECIDED (the team, 14 Nov)
Everything that touches camera frames runs inside a Coder workspace.
In practice that is the whole backend, because `POST /frames` lives in the same app as the voice tools (D5).
We run our own open-source Coder server on the demo MacBook with a Docker template, so we are the admins and no license limits apply.
Take a screenshot of the running workspace for Devpost.

How to say it (pitch, video, Devpost):

- Say "built with HIPAA-style safeguards": frames are handled only inside an isolated Coder workspace, full frames are never stored, only a tight crop of each item is kept in a private bucket with expiring links, and no-capture rooms store nothing.
- Frames are still sent to Google (Gemini) and Roboflow for analysis.
  Coder isolates our code, not theirs, so never claim the frames stay in the container.
- Never say "HIPAA compliant" or "protected under HIPAA".
  HIPAA covers healthcare providers, insurers and their contractors, and running in a container does not make us one.
- The egress allowlist is item 2 on the cut list in `PLAN.md`.
  If it gets built, add "the workspace can only reach our database and the two model providers", and remember it must also let `cloudflared` out (D5).
  If it is cut, leave that sentence out.

> **⚠ UNVERIFIED: whether the Coder table counts a self-hosted Coder server.**
> Ask them. If only their hosted deployment counts, update D5 and this entry before step 03.

## Settle before step 05

**D7. Room recognition.** OPEN (default kept in step 05)
Default: the language model picks the room from the list. Add the embedding vote (`match_room`) only if it confuses rooms on the fixture frames.
Step 05 (15 Nov): Gemini named the room right on 17/17 fixture frames, lowest `room_confidence` 0.80, so no embedding vote. The fixtures have no bathroom frame yet, so confusion between rooms is untested.

**D8. Whose item is it?** OPEN
Default: one enrolled item per category, so a detected "glasses" is the glasses. Add `match_item` only if the demo needs two look-alike items.

**D9. Embedding model and width.** OPEN
The schema uses `vector(768)`, which fits Roboflow-hosted CLIP ViT-L/14. If you choose another encoder, change the width in the migration before loading it. One encoder for every embedding.

**D10. What triggers a frame?** DECIDED (step 06 CP3 replays, 15 Nov, by Claude Code with the user)
A JPEG every **0.5 seconds**, then the blur and duplicate filters. A hand-in-view gate is a later refinement.
The CP3 take (66 s, four put-downs, each item in view for about 1 s) replayed at both rates: every 2 s confirmed 0 of 4 put-downs (one frame each, so every stay stayed tentative); every 0.5 s confirmed 4 of 4, once frames waiting for Gemini queue one deep per device instead of being dropped.
Cost for that minute: 132 SAM 3 calls and 16 Gemini calls (the gate kept 107 frames from Gemini). For 24/7 that is 7,200 SAM 3 calls an hour before the duplicate filter.

**D11. Thresholds.** OPEN (perception cuts tuned in step 05; blur and duplicate cuts wait for step 06)
Defaults: blur below 25; duplicate at SSIM 0.95 or more; detector confidence per model as in `.claude/rules/perception.md`; stay-merge window 10 minutes; 3 empty looks to conclude absence; spoken confidence cut at 0.5. All are guesses. Tune on the fixture frames in step 05 and write the tuned values here.

Step 06, 15 Nov, measured on the CP3 take: blur cut 25 kept (a sharp frame of the glasses on the plain table scores 60, so variance of the Laplacian mostly measures texture; smears scored 14 to 46); duplicate cut 0.95 kept (SSIM 0.1 to 0.6 while walking, 0.72 to 0.98 holding still, so it drops only the stillest frames). Added: `DUPLICATE_REFRESH_S` 10, `EMPTY_LOOK_EVERY_S` 30, `VLM_IN_FLIGHT` 2.

Step 05, 15 Nov: `perceive()` live on all 17 fixture frames (`RUN_LIVE=1 LIVE_FRAMES=all uv run pytest -m live -s`), 17/17 fully correct (room, landmark and item).
The cuts are settings (`ROOM_CUT`, `ITEM_CUT`, `SAM3_GATE`, `PERCEPTION_TIMEOUT_S`, `DETECTOR_TIMEOUT_S`); every value below is unchanged from its default, because the measurements leave room on the safe side of each.

| Cut | Value | Evidence |
|---|---|---|
| Room cut | 0.6 | Lowest `room_confidence` on a right room: 0.80. |
| Item cut | 0.5 | Lowest confidence on a right item: 0.95. Gemini reported no stray or wrong item at all, so nothing tests the cut from above. |
| SAM 3 gate | 0.5 | Lowest best score on an item frame: 0.57 (the medium watch on the table). Highest on an empty frame: 0.55 (a "wristwatch" on bare carpet). The two overlap, so the gate errs open: a wrong opening costs one Gemini call that then sees nothing, and a wrong closing loses a put-down. Do not raise it. |
| Gemini timeout | 10 s | Median 2.7 s, worst 5.3 s over 17 calls (step 04: worst 7.2 s over 51). |
| SAM 3 timeout | 5 s | Median 0.56 s, worst 0.86 s over 20 calls (step 04: worst 0.95 s). |
| Box match | IoU 0.5 | Every one of the 12 crop boxes came from SAM 3, IoU 0.68 to 0.99 against the hand-drawn boxes. |

**D12. No-capture rooms.** OPEN
The database refuses to store anything for them, but the frame has already been sent to a model API by the time the room is known. Options: (a) accept and disclose; (b) a Pause button on the capture page; (c) run a local room classifier first and drop the frame before any network call. Default: (a) plus (b).

**D24. Which vision language model reads the frames?** DECIDED (the team, 14 Nov: Google Gemini instead of Claude; model choice and settings by Claude Code)

- **Model:** `gemini-3.6-flash` (stable), set by `PERCEPTION_MODEL`.
  The step 04 bake-off also tries `gemini-3.5-flash-lite` (stable, faster, weaker) and `gemini-4-hydrogen` (the step-up); keep whichever passes CP2 with acceptable latency.
  `gemini-3.8-flash` did not answer on our key on 14 Nov (timeouts at 20, 45 and 60 s, even for plain text), nor on the step 04 retry (60 s, one image). Not used.
  Step 04 kept `gemini-3.6-flash` (D3 has the numbers).
- **Is it good enough? Probably for the reasoning half; not proven for tight boxes on small items.** Research on 14 Nov:
  - Roboflow's Vision Evals (12 Nov 2026, 32 samples, no breakdown by object size), object identification: 3.6 Flash 99.0%, 3.8 Flash 97.9%, 3.5 Flash-Lite 84.4%, Claude Haiku 5.5 83.3%. https://playground.roboflow.com/evals/identification
  - Same evals, detection mAP@50: Hydrogen 81.0, 3.8 Flash 68.1, 3.6 Flash 57.1. SAM 3 and YOLO-World were not scored. https://playground.roboflow.com/evals/object-detection
  - Same evals, latency per image at low effort: Flash-Lite about 1.2 s; 3.6 Flash, 3.8 Flash and Hydrogen about 7.4 s.
  - Known weakness, from older Gemini models: reporting a named object that is not there (RF100-VL https://arxiv.org/abs/2505.20612; SAM 3 paper https://arxiv.org/abs/2511.16719). Spatial relations benefit from some thinking (https://arxiv.org/abs/2509.02175, 2025).
  - No public benchmark tests these models on small household items at 0.5 to 3 m or on on/in/under. The step 04 bake-off on our own photos is the real test.
  - So: keep a detector for crops unless Gemini's own boxes pass CP2 in the bake-off, start at thinking `low`, and process frames concurrently.
- **API:** the Interactions API from the `google-genai` package (`client.aio.interactions.create`), with a JSON schema in `response_format`.
  Google calls `generateContent` legacy.
- **Checked live on 14 Nov (text only, no images):** `gemini-3.6-flash` and `gemini-3.5-flash-lite` both returned `status` `completed` and JSON inside the enum, in 0.7 to 1.5 s.
- **Settings (step 04 measured them):** `thinking_level` `low`, image resolution `high` (1,120 tokens), frames processed concurrently. Details in `.claude/rules/perception.md`.
  - Timeout 10 s: the worst of 51 calls to 3.6 Flash with images took 7.2 s, the median about 3 s.
  - The SDK retries 408, 409, 429 and 5xx up to 4 times inside one call by default, and the call's `timeout` did not stop one such call before 94 s.
    Build the client with `HttpOptions(retry_options=HttpRetryOptions(attempts=1))`, wrap each call in `asyncio.timeout`, and do the 3 retries ourselves.
- **Privacy:**
  - On the free tier Google uses API inputs, images included, "for product development and machine learning", and "human reviewers may read, annotate, and process your API input and output". On the paid tier Google does not use prompts or responses to improve its products. Source: https://aistudio.google.com/docs/terms
  - The Interactions API stores every request by default (1 day free, 55 days paid). Every call passes `store=False`. Source: https://aistudio.google.com/docs/interactions
  - On billing-enabled projects, AI Studio logs Interactions requests by default and keeps them up to 55 days, private to the project. Turn it off under Logs and Datasets in AI Studio. Source: https://aistudio.google.com/docs/logs-policy
  - So: staged test photos may use the free-tier key; real camera frames need a billing-enabled project with logging off (hard rule in `CLAUDE.md`).
- **Rate limits:** Google shows the free-tier limits per model only in AI Studio.
  On 14 Nov the free tier refused most calls with 429 at 4 in flight, and none at 1 in flight (92 calls, about 2 to 3 s each).
  With the SAM 3 gate (D3) the demo sends only a few frames a minute to Gemini; billing is still required for real frames (privacy, above).

## Settle before step 03

**D13. How does a caller map to a home?** OPEN
Default: one home, `HOME_ID` in the environment. Caller-number lookup is out of scope.

**D14. Voice and wording.** OPEN
Pick the Vapi voice and speaking rate. Have someone outside the team listen to three answers. The rules are in `.claude/rules/voice.md`; change them there, not in code.

**D15. What happens after the answer?** OPEN
Default: the agent asks "Would you like me to stay on the line while you look?", then "Did you find them?", and reports the outcome. A "no" retires that answer.

## Settle when you reach them

**D16. Dashboard data access.** Default: the page polls the backend every 2 seconds. No Supabase key in the browser.

**D17. Photo retention.** Default: crops only, private bucket, signed for 1 hour, cleared after 7 days by `purge_old`.

**D18. Typesense's job.** Default: resolve the spoken words to an item name (typos, synonyms), then call `find_item`. Postgres stays the source of truth.

**D19. FaceTime agent language.** Default: Python LiveKit agent, because drawing into a published video track is verified in Python. The Chert starter is Node; attaching a Python agent by dispatch name is expected to work but untested.

**D20. Roboflow hosted inference and privacy.** Unverified whether hosted inference retains images. Default: staged scenes only until someone confirms with Roboflow.
Read on 14 Nov: "Model Monitoring does not save inference images by default" (https://docs.roboflow.com/deployment/monitoring-and-analytics/model-monitoring.md); it saves them only through a Dataset Upload block or Active Learning, neither of which we use.
Every call also sends `disable_model_monitoring: true`. That covers monitoring, not the serving infrastructure itself, so the question to Roboflow stays open.

**D21. What the model may see of people.** Default: crops are padded boxes around items; the prompt forbids describing people; no face is stored.

**D22. Measuring it.** Default metric for the write-up: on the fixture set, the share of put-down events where `find_item` then returns the right landmark. Report the number, however small the set.

**D23. Speech stack for the FaceTime agent.** Default: whatever the Chert starter ships with. Adding another speech provider means another key and another failure point.

## After the core demo passes

**D25. A room scan: 3D view (A) and room recognition from the scan (C).** OPEN (the team, 14 Nov: maybe, as an afterthought)
The judges liked the point cloud idea on 14 Nov.
Start only after CP3 and CP4 pass (cut item 1 in `PLAN.md`, and the out-of-scope list in `CLAUDE.md`); until then, finish the original plan.
Optional now: record the scan video while the staged table and chair are set up; it takes ten minutes and touches no code.

- **Making the scan:** Scaniverse (free, processes on the phone, exports PLY), or ffmpeg plus COLMAP or GLOMAP on the Mac from a video (nerfstudio's `ns-process-data video` wraps both).
  The base iPhone 17 has no LiDAR; a Pro model gives a cleaner scan at real scale.
- **A, 3D view (about 2 to 3 hours):** click the table, chair and floor in the cloud and store their positions in `landmarks.x/y/z` (the columns exist; no migration).
  The dashboard draws the room (three.js `PLYLoader` from a CDN, no build step) with a pin on the landmark `find_item` returns, and the timeline moves the pin.
  No change to perception, the database functions or voice.
- **C, room from the nearest scan frame (about 2 to 4 hours on top of A):** embed the scan's frames with CLIP ViT-L/14 running locally (768 numbers, fits `vector(768)`, D9) into `room_refs`, and look up each live frame with `match_room` before any network call.
  Fail closed: send a frame to Gemini only if it closely matches a frame of a capture-allowed room, otherwise drop it. This needs no bathroom imagery, and it is D12 option (c): the no-capture rule then stops transmission, not only storage.
  The embedding must run locally; Roboflow-hosted CLIP would send the frame out.
  This changes the write path: tune the match cut on fixture frames, and add an `ingest` test for a dropped frame.
- **Not planned: full camera localization (B).** Matching each frame to the scan to get the camera's position (for example hloc) would tell identical tables apart and check `landmarks_in_view` geometrically, but iOS Safari gives no camera position, so it costs seconds per frame on the server and fails on blurry frames.
  Pitch it as the next step; a native ARKit app would provide the position for free.
- **Privacy:** a scan of a real home is as sensitive as the frames.
  Leave the bathroom out, keep the file in a private bucket and sign it at read time like the crops.
  Scaniverse keeps the scan on the phone; Polycam's photo mode uploads it.

**D26. Items nobody registered.** A DECIDED (the user, 15 Nov: build it in step 08).
C OPEN: decide after CP1 and CP4; start by 01:00 Sun 15 Nov or keep it for the pitch.

Today Save It remembers only the items in the `items` table.

- The model's answer is limited to registered names (JSON-schema enums), so an unregistered object is never stored.
- `find_item` matches a question only on an exact item name or alias.
  "Where's my orange bottle?" with no orange bottle registered gets `unknown_item` ("I'm sorry, which thing are you looking for?").
- Two worse cases today: "where's my bottle?" matches the blue water bottle's alias "bottle" and answers with that one, and a look-alike can be filed as a registered item.
  In CP3 (step 06) a keyring on another person's desk became "your keys are on the table".
- Adding an item needs no code: the camera starts looking for a new row within 30 s (the worker's context cache), and SAM 3 is prompted with the item's name until someone measures a better wording.
  What is missing is a way to add one without SQL.

We never keep full frames (hard rule), so anything the camera was not told to look for when it saw it is gone.
That decides the difference between the two options below.

| | A. Add an item | C. Remember unregistered objects |
|---|---|---|
| What it does | The family adds an item on the dashboard; from then on it is tracked like the others | The camera also notes everyday objects outside the list, with no owner; a question that matches no item searches those notes |
| Answers about something nobody registered? | No. Only from the moment it is added, never about earlier | Yes, if the camera happened to see it |
| Who has to act | The family, once per item | Nobody |
| What is stored | Only chosen items | Every everyday object in view, other people's too |
| Answer | Confident: "Your glasses are on the table." | Hedged: "I saw an orange bottle on the table about ten minutes ago, but I'm not sure it's yours." |
| Effort | About 1 hour, inside step 08 | 3 to 4 hours plus re-testing: step 12 |

**A, add an item (step 08).**

- A dashboard form: name, colour, a short description, optional aliases and usual place.
  `POST /api/items` (APP_TOKEN) inserts the row through `app/memory/db.py`.
- Refuse a name or alias that is already another item's name or alias, so new items cannot create the "bottle" clash above.
- The camera picks it up within 30 s, with no restart.
- Optional, if time allows: take a photo of the item and let Gemini write the colour and description (staged objects only until the privacy rules are revised).

**C, remember unregistered objects (step 12, optional, after the core demo).**

- Gemini also reports objects from a short list of everyday categories that match no registered item, each with a free-text label ("orange water bottle").
  Start with bottle, bag, keys, glasses, wallet and phone; the team can change the list.
- The worker stores them as unowned sightings: `log_sighting` with `p_item` null and the label.
  The database already supports this: unowned stays merge by label and never change a registered item's belief or absence count.
- SAM 3 needs category prompts ("bottle", "bag", ...) so the gate opens for them.
- A migration (`0003`) lets a question that matches no item search unowned sightings by label (word overlap or `pg_trgm`), adds `label` to the `timeline` view, and returns the match with `unknown_item` (or a new state).
  `speak()` and `.claude/rules/voice.md` gain the hedged sentence.
- Risks: other people's belongings.
  CP3 already showed one (the keyring on another desk), and a hall or a care home is full of bottles, bags and keys.
  More is stored about the surroundings, which weakens the privacy story; every such answer must be hedged and come with a photo the family can check on the dashboard.
- A middle path: only for categories the family turns on ("any bottle"), still hedged.

**Deciding on C.** Build A regardless.
Start C only after CP1 (a real call answers) and CP4 (live camera) pass, and not later than 01:00 on Sun 15 Nov, so it can be re-tested and rehearsed before the 05:00 freeze.
If it has not started by then, keep it as the next step in the pitch: "we only remember what the family chose, so we never point you at someone else's bottle; recognising anything is next."
