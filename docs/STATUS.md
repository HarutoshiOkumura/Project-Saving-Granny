# Status

Claude Code updates this at the end of every step. Humans edit it freely. Keep it under one screen.

Last updated: Sat 14 Nov ~17:25 ET (Tom's Claude Code: step 10 FaceTime agent in `agent/`, stubbed on the fake home; D23/D28 decided; `.gitignore` added)

## Steps

| # | Step | State | Notes |
|---|---|---|---|
| 00 | Scaffold | todo | |
| 01 | Supabase | todo | Schema is written and tested locally; not yet applied to Supabase |
| 01b | Ranked search (0002) | done | `rank_item`, `record_miss`; 59/59 SQL checks pass on scratch Postgres 16; not yet applied to Supabase |
| 02 | Find API and speak() | todo | |
| 03 | Phone voice | todo | |
| 04 | Detector bake-off | todo | |
| 05 | Perception module | todo | |
| 06 | Ingest worker | todo | |
| 07 | Capture page | todo | |
| 08 | Dashboard | todo | |
| 09 | Typesense | todo | optional |
| 10 | FaceTime | stubbed | `agent/` answers on the line from the fake home (`BACKEND_URL` empty); `chert doctor --agent save-it` all pass; 8/8 `npm test`. Live call test: pending. Caller video still blocked on D4 |
| 11 | Harden and record | todo | |

State is one of: todo, doing, done, stubbed (works with fake data), blocked (say on what).

## Checkpoints

- CP1 phone call answers from seeded data: not yet
- CP2 detector chosen: not yet
- CP3 replayed walk gives three correct answers: not yet
- CP4 live from the lanyard phone: not yet

## Stubs and fakes in the code right now

- `agent/fake-home.mjs` + `speakStub()` in `agent/saveit.mjs`: fake `rank_item`/`speak()` until step 02's `/find`. Set `BACKEND_URL` in `agent/.env.local` to switch; contract in docs/CHERT.md.

## Defaults taken from DECISIONS.md

(list each decision id used and the default applied)

## Tuned values

(blur threshold, duplicate threshold, detector confidence, similarity cut)

## Open questions for the humans

(one line each; remove when answered)

- Confirm the read-side direction (D24, D25, D27 in docs/DECISIONS.md): voice uses `rank_item`, Typesense beyond name matching, Chert FaceTime as the main channel.
- For Haru: Roboflow: applying for the academic/research plan makes all data in that workspace public on Roboflow Universe (Roboflow docs). That confirms the hard rule.
- For Haru: Ranking trust depends on writing the right `p_event`/`p_source`: camera `seen`/`worn_cam`; family form `told`/`manual`; the person on a call `told`/`facetime_caller`.
- For Haru: `observations.room_id` (the wearer's room) drives `rank_item`'s walking order. Keep writing it for every frame.
- For Haru: Landmarks can set the new nullable `find_chance` (0–1) and `check_seconds`. Null means the default by kind.
- For Haru: Please push `.claude/commands/`, `.claude/rules/` and `.env.example`.

## Things that differ from the docs or from CLAUDE.md

(third-party API shapes that turned out different, with the link)

- Chert starter is JavaScript, needs Node 22.12+ and `OPENAI_API_KEY`; a Python agent works via `chert dev --agent NAME` (npm `@trychert/facetime@0.1.0-beta.21`). Details in docs/CHERT.md.
- Our agent uses Gemini Live instead of OpenAI (D23). `@livekit/agents-plugin-google@1.8.0` drops caller video for Gemini Live and breaks `generateReply` on "3.1" models.
- `CLAUDE.md` said `.env` was gitignored but the repo had no `.gitignore`; added one (14 Nov, Tom) ignoring `.env`, `.env.*` (keeps `.env.example`), `**/.env.local`, `node_modules/`, Python caches.
