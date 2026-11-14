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
| `recall_life_fact(question)` | Typesense `facts` search (`docs/TYPESENSE.md`, D26) |
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
