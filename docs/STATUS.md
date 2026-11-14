# Status

Claude Code updates this at the end of every step. Humans edit it freely. Keep it under one screen.

Last updated: Sat 14 Nov 17:47 ET (Tom's Claude Code: merged Haru's steps 00 to 02 into branch `tom/read-side`; the FaceTime agent reads `/find`)

## Steps

| # | Step | State | Notes |
|---|---|---|---|
| 00 | Scaffold | done | uv project (Python 3.12.15, `uv.lock` committed), ruff, package layout, `app/config.py` (`get_settings()`), `GET /health`, 10 tests. Left for humans: D5 and D6 (below) |
| 01 | Supabase | done | `0001` (8 fixes) and `0002` applied; 75/75 checks on scratch (82/82 with Supabase roles); home seeded; private `crops` bucket; smoke test and API key checks pass; `ask_item` median 98 ms over HTTPS. Left: MCP read-only (below) |
| 01b | Ranked search | todo | `rank_item`, `record_miss` (planning chat): 59/59 checks against the original 0001, not the applied one. Renumbered to `0003` (Haru's `0002` is applied). Re-test on scratch against the applied 0001 (pinned `search_path`, explicit grants, test section 25), then apply |
| 02 | Find API and speak() | done | `GET /find?item=...&channel=web` -> `app.ask.ask()` -> `db.ask_item` + `speak()`; 80 new tests (90 total). Live on Supabase: "my specs" -> "I last saw your glasses on the kitchen counter about forty minutes ago." 20 calls: median 50 ms, worst 114 ms; first call after a restart 115 to 160 ms (one 865 ms outlier, likely cold DNS). Dead database: fallback at 2.0 s; bad hostname: 46 ms. Smoke rows deleted |
| 03 | Phone voice | todo | Call `app.ask.ask(item, "phone")`, not `db.ask_item` + `speak()`: the 2 s timeout, fallback and log line are already there. `/find` has no auth yet; once the tunnel is up anyone can query it, so add a token check then |
| 04 | Detector bake-off | todo | |
| 05 | Perception module | todo | |
| 06 | Ingest worker | todo | Catch `22023` from `log_sighting` (room and landmark disagree) and skip the frame |
| 07 | Capture page | todo | |
| 08 | Dashboard | todo | |
| 09 | Typesense | todo | optional |
| 10 | FaceTime | doing | With `BACKEND_URL` set, `agent/` reads step 02's `GET /find?channel=facetime` (`{sentence, result}`, verbatim) and points the card from `result`; checked live through the local backend against Supabase. "Not there" and "I put it..." save nothing until `/miss` (0003) and `/told` exist. `chert doctor --agent save-it` all pass; 10/10 `npm test`. Live FaceTime call: pending. Caller video still blocked on D4 |
| 11 | Harden and record | todo | |

State is one of: todo, doing, done, stubbed (works with fake data), blocked (say on what).

## Checkpoints

- CP1 phone call answers from seeded data: not yet (the backend half works: `GET /find` answers from Supabase)
- CP2 detector chosen: not yet
- CP3 replayed walk gives three correct answers: not yet
- CP4 live from the lanyard phone: not yet

## Stubs and fakes in the code right now

- `agent/fake-home.mjs` + `speakStub()` in `agent/saveit.mjs`: the fake home, used only while `BACKEND_URL` in `agent/.env.local` is empty.
- `agent/saveit.mjs` backend mode: `report_not_there` and `record_placement` save nothing yet (no `/miss`, `/told`): "not there" offers the usual place once, then family. Contract in docs/CHERT.md.

## Defaults taken from DECISIONS.md

- D2: decided in step 01 (default names plus a bedroom `desk` and the item `bag`, the FRANZI Milano green bag). The bag has no usual place (`home_landmark_id` null), so `never_seen` gives no `usual` for it.
- D11: stay-merge 10 min, 3 empty looks to contradict, now at least 30 s apart (`mark_absent` `p_min_gap`); confidence cut 0.5.
- D13: one home, `HOME_ID=11111111-1111-1111-1111-111111111111`.
- D15: `ask_item` logs every question so `record_outcome` can retire a wrong answer; whether the voice asks "did you find it?" is still open.
- D17: `crops` bucket is private, JPEG only, 1 MiB cap.

## Tuned values

(blur threshold, duplicate threshold, detector confidence, similarity cut)

## Open questions for the humans

- **⚠ D5 and D6 are decided but UNVERIFIED** (MacBook Pro, Coder workspace, Cloudflare Quick Tunnel, iPhone 17). Run checks A1 to A6 in `docs/DECISIONS.md` D5 in the first end-to-end test (step 03 at the latest) and write the results here. Each check has a fallback.
- Humans, before step 03: Coder server and a Docker workspace on the Mac (screenshot it), the tunnel address in `PUBLIC_BASE_URL` (empty now), a name for who owns the Mac during judging, and ask the Coder table whether a self-hosted server counts (D6).
- After step 01: make the Supabase MCP read-only by adding `&read_only=true` to the URL in `.mcp.json`.
- D1: where the demo home is staged. Names now live in `supabase/seed.sql`; change them there if the staging changes.
- Where does the bag usually live? One SQL update sets `items.home_landmark_id`.
- `desk` (bedroom) and `table` (kitchen) are similar furniture; the room separates them, but watch for mix-ups in the step 04 bake-off.
- D4: pick a cut-off time for Chert's answer; FaceTime is 4 to 6 hours.
- D15: keep "did you find it?"? It needs a second Vapi tool; the database side (`ask_item`, `record_outcome`) is ready.
- Photo idea (14 Nov): keep the item's last good view instead of its best-confidence one, and a wider "context" crop that shows the landmark. Decide in step 05/06 on real fixture crops. Full frames stay out (hard rule).
- `package.json`, `package-lock.json` and `node_modules/` (`@supabase/server`) appeared in the repo root at 15:36. The app is Python; delete them unless someone needs them.
- Confirm the read-side direction (D24, D25, D27 in docs/DECISIONS.md): voice uses `rank_item`, Typesense beyond name matching, Chert FaceTime as the main channel.
- For Haru: Roboflow: applying for the academic/research plan makes all data in that workspace public on Roboflow Universe (Roboflow docs). That confirms the hard rule.
- For Haru: Ranking trust depends on writing the right `p_event`/`p_source`: camera `seen`/`worn_cam`; family form `told`/`manual`; the person on a call `told`/`facetime_caller`.
- For Haru: `observations.room_id` (the wearer's room) drives `rank_item`'s walking order. Keep writing it for every frame.
- For Haru: Landmarks can set the new nullable `find_chance` (0–1) and `check_seconds`. Null means the default by kind.

## Things that differ from the docs or from CLAUDE.md

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
- VS Code's `python.terminal.useEnvFile` (on in Tom's settings) injects the repo `.env` into every terminal, and `node --env-file` keeps injected values: the agent registered as `my-agent` (the root `.env` value) and Chert declined calls. `agent/env.mjs` now applies `agent/.env.local` first and drops `SUPABASE_*`/`DATABASE_URL`. `chert dev`, run from such a terminal, still inherits the whole repo `.env`, Supabase secret included.
