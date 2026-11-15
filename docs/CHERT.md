# Chert FaceTime (prize: "Chert: Best Use of FaceTime")

Sources, read 14 Nov 2026:
- the npm package `@trychert/facetime@0.1.0-beta.21` (`README`, `QUICKSTART`, `COMMANDS`, `CLI_GUIDE`);
- the `cherthq/sdk` repo docs.

EmoryHacks gives a free 48-hour line. The EmoryHacks Chert page says the agent sees the caller's video live.

## Setup
- **Node 22.12+, 24 or 26.** Node 20 is rejected. macOS or Linux; Windows 11 is in beta.
- `npm install -g @trychert/facetime@beta`
- `chert login` opens a browser. On a remote shell such as Coder, use `chert login --device`. The session is stored in `~/.chert` (owner-only).
  - Tom's Mac already has `~/.chert` and `~/Active-Projects/Chert-Demo`. Ask Tom before reusing either.
- `chert whoami --json` gives the `project_id`.
- The project needs the owner or admin role and **exactly one line set to "customer decides"**.

## Our agent: `agent/` (built 14 Nov, Tom; step 10 "stubbed")
Built from `chert new agent --video --agent save-it` (CLI 0.1.0-beta.20). Line: +1 (628) 278-8831, trial, project owner Tom.

| File | Does |
|---|---|
| `agent.mjs` | Gemini Live voice (D23), Save It persona and voice rules, the five tools, greets on `bridge_ready` |
| `saveit.mjs` | Tools' read side. `BACKEND_URL` set → HTTP (contract below); empty → `fake-home.mjs`. Keeps per-call `item`, `suggested` place, last `result` and `query_id` |
| `fake-home.mjs` | Stand-in home from `supabase/seed.example.sql`, returns `rank_item`-shaped JSON (same band and search-order rules) |
| `card.mjs` | Agent video: 1280×720 card, place name ≤ 2 × 22 chars, 56 px white on dark panel, marker pulses 1 Hz while speaking |
| `test/` | `npm test`: offline, no paid calls |

Run (two terminals, from `agent/`; a third for the backend when `BACKEND_URL=http://localhost:8000`):
0. Backend, from the repo root: `uv run uvicorn app.main:app --port 8000`. If it is down, every answer is "I'm not sure. Let me check with June."
1. `npm install && npm start` (waits for jobs; free until a call)
2. `npx @trychert/facetime@0.1.0-beta.20 dev --agent save-it` → wait for "is in a waiting room", then FaceTime the line.
3. Stop: Ctrl+C on `chert dev` first (frees the line), then the agent. After code changes restart both.

`npm start` must log `"agentName":"save-it"`; otherwise `chert dev` declines every call. VS Code's `python.terminal.useEnvFile` loads the repo's `.env` into every terminal and `node --env-file` never overrides a variable that is already set, so `agent/env.mjs` (imported first) applies `agent/.env.local` over the terminal's values and drops `SUPABASE_*` and `DATABASE_URL`. Change agent settings in `agent/.env.local`, not in the shell.

Every call writes one JSON line per event to `agent/logs/calls.jsonl` (gitignored) and the console: caller and agent state changes, each tool call with milliseconds, and the model's `ttft_ms`. `LOG_TRANSCRIPTS=1` in `agent/.env.local` adds what was heard and said (testing only). `GEMINI_THINKING_BUDGET=0` is an optional latency experiment; Google's docs do not confirm it for this model (checked 14 Nov).

### How the agent answers (14 Nov)
When a call starts, the agent loads `GET /snapshot`: every item's current sentence, without logging questions. It puts them in Gemini's instructions, so a question about a known item is answered in one model turn, in the model's own words. Places and times must stay as given. The question is still logged and the card still moves: each final transcript that names an item or alias runs `/find` in the background. With a snapshot loaded the agent has no `find_object` tool: anything not on the list gets "I don't know it yet" straight away, and the question is still logged in the background when it sounds like a where-is question. Tom's 14 Nov test call showed why: the model answered the bag from the list and also called `find_object`, then said the same sentence twice, and each unknown item cost an extra model round of about 1.5 s. If `/snapshot` fails, the agent offers `find_object` and looks up each question.

The assistant is called **Find It** on calls and on the card (`agent/prompt.mjs`, Tom 14 Nov). Internal ids stay `save-it` (`AGENT_NAME`, `chert dev --agent save-it`). The snapshot carries each item's looks (`color`, `description`) and where it was before or usually lives. So the agent can ask "The blue one or the green one?" when two items fit, and answer "where was it before that?", all without a lookup. Tested by voice against Gemini with two water bottles: it asked which one, then answered; every turn took about 1.5 s, so asking costs one exchange and nothing else. With one bottle it answered straight away. The card and the question log follow the reply when the question named no single item.

Look-alikes are worked out fresh at every call start (`lookalikeGroups` in `prompt.mjs`): items of the same kind (the item's `category`, e.g. two bags or two cups), or items a shared name or alias fits. Nothing in the database is renamed; a second bag enrolled later joins the first bag's group on the next call. Each look-alike is listed once, in its group, with its description and its own answer side by side. The model asks which one using whatever the descriptions differ in (colour, size, shape, brand), then answers only from the chosen line. Tested by voice: two bags (green handbag, brown bag) and a big white mug against a small white espresso cup (same colour, no aliases) both get "which one?" and the right answer. Without kinds, on Tom's 14 Nov test call, it asked about the water bottle but not the bag (named plain "bag"). A colour-only relabel in between was replaced, because it could not tell a big cup from a small one. The card and the question log follow a single item only: a word naming exactly one item in what the caller said, or a statement in the reply. They never follow a "which one?" question.

No tool or sentence may promise to contact family (family calling is paused). On the same call, "let me check with your family" made the model call `alert_caregiver`. Nothing answers `/alert`, so the failure came back as "I'm not sure. Let me check with June." and was said as a second answer. `alert_caregiver` and `recall_life_fact` are removed until their backends exist.

The card's marker shows who is talking: orange and pulsing while Save It speaks, steady green the moment the caller's voice comes in. The green comes from a level meter on the caller's audio in the agent (`voice-meter.mjs`), not from Gemini, which reports speech only after transcribing the first words. Measured: green about 0.3 s after the voice starts. The meter also logs `voice` on/off events, so the time from the caller stopping to Save It answering can be read from the call log.

Measured with spoken questions through LiveKit (first sound after the question ended):
| | glasses | keys | watch |
|---|---|---|---|
| Lookup per question, sentence read word for word | 4.9 s | 3.3 s | 3.2 s |
| Snapshot in the instructions | 2.6 s | 3.1 s | 3.1 s |
| Snapshot + Gemini thinking off (default now) | 1.8 s | 1.9 s / 2.4 s | 2.1 s / 2.3 s |
Without the lookup tool (later the same evening): glasses 2.6 s, bag 2.5 s (said once), pencils (unknown) 1.9 s, watch 3.8 s. Gemini's own time varies run to run, so the median across thinking-off runs is about 2.2 s. Gemini alone, sent the audio directly with no tools, took 1.5 to 3 s. Answers also got shorter: 3.5 to 4.4 s of speech, down from 6.8 to 7.6 s.

### Where to look and the last-seen photo (D33, 15 Nov)

Each `/snapshot` entry has two new fields.
Every older field is unchanged, so an agent that ignores them keeps working.

- `where_to_look`: places ranked with chances, or `null` for an unknown item or when the read failed.

  ```json
  {"band": "high",
   "places": [{"landmark_id": "2bfe…", "room": "the classroom", "landmark": "the table",
               "address": "b_school_classroom > table", "pct": 67,
               "why": ["last_seen", "home"], "minutes_ago": 30},
              {"landmark_id": "3882…", "room": "the classroom", "landmark": "the chair",
               "address": "b_school_classroom > chair", "pct": 25,
               "why": ["glimpse"], "minutes_ago": 1}],
   "elsewhere_pct": 8,
   "ruled_out": null}
  ```

  - `places` is most likely first, with at most 4 places; the `pct` values plus `elsewhere_pct` add up to 100.
    `room` and `landmark` are the spoken words, as in `result`.
  - `why` says what put a place on the list: `last_seen` (the current answer), `glimpse` (one camera frame newer than the answer: a hint, never an answer), `usual` (two or more settled stays there) and `home` (where the family says it belongs).
  - `band`: `high` when the top place has at least 60% and leads the second by 25 points, `split` when the top two have 60% together, `low` otherwise.
    Offer the list when the band is not `high`, or when the caller says it is not there.
    Say the places in order, most likely first, and never the percentages (`.claude/rules/voice.md`); the percentages are for the card.
  - `ruled_out` is the place just seen empty (`not_there_anymore`); it is never in `places` unless a newer glimpse put it back.
  - The weights are in `app/look.py`.
    The chances are a ranking aid, not measured probabilities.
- `photo_url`: a signed link to the last-seen crop, valid for 1 hour, or `null`.
  It is sent only when the request carries `Authorization: Bearer <APP_TOKEN>`, because it opens a private crop.
  `saveit.mjs` already sends that header when `APP_TOKEN` is set, so set `APP_TOKEN` in `agent/.env.local` to the backend's value.
  `result.photo` stays the storage path.

Measured against Supabase on 15 Nov: `/snapshot` takes about 190 ms warm without the token and 270 to 340 ms with it (signing is one Storage request); the first call after a restart took 1.2 s.
If the habit read or the signing fails, the sentences still come back and only these fields are `null`.

### Test without FaceTime (uses no Chert minutes)
Chert counts FaceTime minutes per call (trial: 50, at most 5 a call; `npx @trychert/facetime@0.1.0-beta.20 doctor` shows what is left). Holding the line costs nothing, and the agent opens no Gemini session until someone joins. For everyday testing, skip FaceTime:
1. Backend (repo root): `uv run uvicorn app.main:app --port 8000`
2. Agent (`agent/`): `npm start`
3. Browser call (`agent/`): `npm run web-call`, open http://127.0.0.1:8090, press **Call Save It**, allow the microphone.

`web-call.mjs` mints a token for a fresh room that dispatches `save-it` with `{"test_call": true}` (LiveKit "Dispatch via access token"; dispatch happens only when the room is created). The agent greets at once, since no FaceTime bridge will send `bridge_ready`. Same voice, tools and card; the page crops the card the way the iPhone did (a checkbox shows the full frame). The server listens on 127.0.0.1 and refuses other Host headers, so the token endpoint never leaves the laptop. `chert dev` can run at the same time: each call is its own room. Save FaceTime for final checks and the recording.

`agent/.env.local` (gitignored, mode 600): `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `GOOGLE_API_KEY`, `AGENT_NAME=save-it`, `BACKEND_URL`, `APP_TOKEN`, `FAMILY_NAME`. No `OPENAI_API_KEY`: `chert doctor`'s OpenAI warning is expected.

### Agent ↔ backend contract
All JSON; `Authorization: Bearer $APP_TOKEN` when set; the agent times out after 3 s and says "I'm not sure. Let me check with June."

| Request | Response | Backend does | Built? |
|---|---|---|---|
| `GET /find?item=<words>&channel=facetime` | `{sentence, result}` | `ask_item` → `speak()` (`app/ask.py`); `result` is `FindResult` | yes (step 02) |
| same, once `/find` ranks | `{say, rank, suggested?}` | `rank_item` → `speak()` | no (needs 0003) |
| `POST /miss {item, landmark_id}` | `{say, rank, suggested?}` | `record_miss`, re-rank, next place | no |
| `POST /told {object_phrase, place_phrase, kind}` | `{say}` | `log_sighting` with `told` + `facetime_caller` (`kind`: `placed` or `found`) | no |
| `GET /facts?q=<question>` | `{say}` | Typesense `facts`, patient-visible only | no |
| `POST /alert {reason}` | `{say?}` | dashboard alert | no |

The agent reads `sentence` (or `say`) verbatim. The card shows `suggested`: from `/find`'s `result`, the place it names (`seen`), the room (`carried`: where they went, else where they had it), or the usual place (`never_seen`, `not_there_anymore`); with `rank`, `suggested` or `rank.search_order[0]` (`{landmark_id, room, landmark}`; `/miss` sends its id). An answer with no place clears the card.

While an endpoint is missing (404) the tool answers without it and promises nothing: "not there" offers the usual place once (unless they just checked it), then "Shall I ask June to help?"; `record_placement` says "Okay, thank you for telling me." (nothing is saved); facts and alerts give the fallback.

## Fastest path: the JavaScript video starter
1. `chert new pal --video` creates `agent.mjs`, `face.mjs`, `greet.mjs`, `chert-rooms.mjs`, `package.json`, its own `CLAUDE.md`/`AGENTS.md`, and `.env.local` with the agent name filled in. Read its `CLAUDE.md` when working there. The video starter publishes a drawn face as its camera.
2. Fill `.env.local`: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, and `OPENAI_API_KEY`. That key needs OpenAI Realtime access and credits.
3. Terminal A: `npm install && npm start`. Terminal B: `chert dev`.
4. Wait for "Connected to Chert" and "agent is in a waiting room", then FaceTime the line.

`chert doctor [--agent NAME]` checks login, role, line, LiveKit and agent registration. With `--agent` it dispatches a real test job.

Put the agent in `agent/` (the `CLAUDE.md` layout). Keep the starter files and add tools that call our backend over HTTP.

## Alternative: a Python LiveKit agent
1. Register the agent with an `agent_name` and start it as usual (`python agent.py dev`).
2. `export LIVEKIT_URL=… LIVEKIT_API_KEY=… LIVEKIT_API_SECRET=…`
3. `chert dev --agent NAME`

This is documented in `CLI_GUIDE`.

## Call rules (break these and calls fail)
- **Warm room.** `chert dev` keeps one warm room with the agent already inside, so calls answer in about 0.1 s. One agent job therefore runs before any caller exists. **Don't speak on job start or on participant join.**
- **Greeting.** Greet **once**, when room metadata becomes `{"chert_call":"<id>","chert_bridge_ready":true,"at":"<ISO>"}`. `chert dev` prints "FaceTime is ready." at that moment.
  - Greet within **10 s** of `bridge_ready`, or the call ends with `remote_audio_timeout`.
  - Without the signal, don't greet; the caller speaks first.
  - The starter does this in `greet.mjs`.
- **Job metadata** is `{"chert_warm":true}` for a warm room, or `{"chert_call":ID,"media":{…}}` for a room created during a call. Don't rely on the call ID being present.
- `--no-prewarm` makes calls wait for the agent to join (3.7–4.9 s measured). That leaves less time inside Chert's deadline.
- **Restarting the agent:** stop `chert dev` (Ctrl+C, wait for release), restart the agent, then run `chert dev` again. Otherwise an old warm job answers.
- After a hangup, wait for "Call ended." `chert dev` then prepares a new waiting room. Test a second call only after it's ready.
- `--takeover` replaces a session already holding the line. `--project UUID` picks the project.
- The LiveKit key and secret stay on this machine. Chert gets a token for one room, valid for at most 2 h.

## Video

**Caller video is blocked in four places as of 15 Nov (D33 in `docs/DECISIONS.md`):** `AutoSubscribe.AUDIO_ONLY` (`agent.mjs:70`), `videoEnabled: false` (`agent.mjs:208`), the Gemini plugin's empty `pushVideo` (1.8.0 to 1.10.0), and the prompt; Chert's caller capture on our line is unverified. D33 has the 15-minute check and the arrow design (`POST /locate`, echo the caller's view with an overlay).

- Calls carry `media: {audio, video}`. Lines report `supports_audio` and `supports_video`. Call events include `remote_video_ready`, `remote_video_unavailable` and `caller_video_published`.
- Requesting video doesn't guarantee it: check the line's `supports_video` and the call's `media_status`.
- **Our agent shows video only by publishing a camera track from the agent.** The video starter already does this. Replace the drawn face with our card: the place name in big text plus the last-seen crop (sizes and colours in `docs/DASHBOARD.md`).
- **Do not build on** these; the hosted backend returns `404 endpoint_unavailable`:
  - custom video over WHIP/WHEP (`@trychert/sdk/media`)
  - web pages rendered as call video
  - screen sharing
  - call-video composition
- Caller video (the person points their phone) can verify "found it": send one frame to a vision model. Blur faces first and never store the frame.

## Agent tools

Keep per-call state, such as the last suggested landmark, in agent code. Never make the LLM echo IDs.

| Tool | Does |
|---|---|
| `find_object(phrase)` | backend `/find` → `rank_item` → `speak()`; remembers `search_order[0].landmark_id` as `last_suggested` |
| `report_not_there()` | `record_miss(item, last_suggested)`, then the next place |
| `record_placement(object_phrase, place_phrase, kind)` | `kind` is `placed` or `found`. `placed` → `log_sighting` with `told` + `facetime_caller` (trust 0.4). Verbal `found` → the same. Seen on caller video and verified → `confirmed_live` + `facetime_caller` (trust 1.0). |
| `recall_life_fact(question)` | Typesense `facts` search (`docs/TYPESENSE.md`, D29) |
| `alert_caregiver(reason)` | dashboard alert |

The agent reads `speak()`'s sentence **verbatim**. The LLM must never name a place that isn't in the tool result.

## Outbound calls (optional, permission-gated)
- JS SDK: `sdk.facetime.createCall({direction:'outbound', mode:'managed', assistant_id, destination, media:{audio:true, video:false}}, '<idempotency-key>')`.
- Route availability and permissions depend on the backend, so probe first.
- Only call team members' own devices.
- Ideas: a 6 PM pill reminder; "keys before leaving".

## Fallbacks and extras
- `chert agent on "<one sentence>" [--voice VOICE]`: Chert runs a hosted agent on the trial or shared line, with no LiveKit project and no model key. Owner/admin only, and not every account has it. It answers whenever `chert dev` isn't holding the line, which makes it a good emergency demo.
- `chert byor`: hands each call to a TypeScript callback, for apps that run their own LiveKit rooms (`examples/byor` in the package).
- Python control plane: `pip install chert-sdk==0.2.3` (import `trychert`). Environment variables:
  - `CHERT_API_KEY`
  - `CHERT_PROJECT_ID`
  - `CHERT_FACETIME_TOKEN`: an `ftk_…` project API key from facetime.trychert.com → Developer → Project API keys. Owners and admins only; shown once.
  - `CHERT_FACETIME_URL` (optional)
  - `CHERT_WEBHOOK_SECRET` (BYOR webhooks)
- Plans can't be switched: `changePlan` returns `billing_plan_change_unavailable`.
