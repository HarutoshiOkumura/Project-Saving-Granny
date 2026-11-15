# Status

Claude Code updates this at the end of every step. Humans edit it freely. Keep it under one screen.

Last updated: Sat 14 Nov 19:48 ET (Tom's Claude Code: faster, natural FaceTime answers via /snapshot; step 09 Typesense came from a parallel session)

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
| 09 | Typesense | done | Keyword only (no embeddings, ~180 MB RAM). `app.ask.ask()` calls `names.resolve()` before `ask_item`, so /find and the FaceTime agent both get it; any failure, or 300 ms, falls back to the raw words. A hit counts only if every word of the name or of one alias matched ("house phone" stays unknown). Typo lengths count the word stem, tuned to 5 and 8 letters so "nurse" does not become "purse". Live: "spectecles", "my reading glases", "black reading glasses", "car keys", "bags", "water botle" resolve in ~2 ms; "dentures", "wallet", "nurse" stay unknown; /find answered with Typesense stopped (2 web rows left in `queries`). Known: "glasses case" resolves to glasses. Not built: synonym sets (aliases do that job), hybrid/NL/RAG, analytics. Run: `docker start saveit-typesense` (local 30.2, key in `.env`), then `uv run python -m scripts.sync_typesense` after items or aliases change |
| 10 | FaceTime | doing | The agent loads `GET /snapshot` (every item's sentence, no question logged) when a call starts and answers known items in one model turn, in its own words, with places and times kept as given; transcripts drive the card and the question log through `/find`. Gemini thinking off by default. Spoken-question benchmark through LiveKit, first sound after the question: 1.8 to 3.8 s, median about 2.2 s (was 3.2 to 4.9 s); answers 3 to 4.4 s long (was 6.8 to 7.6 s). No `find_object` tool while a snapshot is loaded (Tom's test call: it answered the bag and looked it up, then repeated itself). Card marker: green about 0.3 s after the caller's voice starts (level meter on their audio, no word). No promises to contact family anywhere (tools without backends removed; `speak()` no longer says "let me check with your family"). "Bag" now asks which one, like the water bottle. Spoken name now Find It; asks "the blue one or the green one?" when two items fit (looks in the snapshot), tested by voice against Gemini at about 1.5 s a turn. Browser test calls: `npm run web-call`. "Not there" and "I put it..." still save nothing (no `/miss`, `/told`). Caller video still blocked on D4 |
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

- **Coder (Tom, 14 Nov 20:50):** we use the event's hosted deployment, not a server on the Mac (D5, D6 changed). Tom's workspace `save-it` is set up by `scripts/coder_setup.sh` (96 Python and 14 agent tests pass on the pushed `df241d5`). No public ports there, so the public address is still a Quick Tunnel, now started in the workspace. No Docker in workspaces: the database tests and the local `saveit-typesense` container stay on a laptop, so in a workspace `names.resolve()` falls back until Typesense runs another way. All in `docs/CODER.md`.
- **⚠ D5 checks UNVERIFIED:** run A1 to A6 in `docs/DECISIONS.md` D5 in the first end-to-end test and write the results here. Humans: screenshot the workspace for Devpost, name who owns it during judging, put the tunnel address in `PUBLIC_BASE_URL`, and ask the Coder table the three questions in `docs/CODER.md`.
- After step 01: make the Supabase MCP read-only by adding `&read_only=true` to the URL in `.mcp.json`.
- D1: where the demo home is staged. Names now live in `supabase/seed.sql`; change them there if the staging changes.
- Where does the bag usually live? One SQL update sets `items.home_landmark_id`.
- `desk` (bedroom) and `table` (kitchen) are similar furniture; the room separates them, but watch for mix-ups in the step 04 bake-off.
- D4: pick a cut-off time for Chert's answer; FaceTime is 4 to 6 hours.
- D15: keep "did you find it?"? It needs a second Vapi tool; the database side (`ask_item`, `record_outcome`) is ready.
- Photo idea (14 Nov): keep the item's last good view instead of its best-confidence one, and a wider "context" crop that shows the landmark. Decide in step 05/06 on real fixture crops. Full frames stay out (hard rule).
- `package.json`, `package-lock.json` and `node_modules/` (`@supabase/server`) appeared in the repo root at 15:36. The app is Python; delete them unless someone needs them.
- For Haru: Tom's work is on branch `tom/read-side` (FaceTime agent reading `/find`, read-side docs, env-file rule in `CLAUDE.md`, `0003` not yet ready to apply). It already contains your main up to step 02; review and merge it, or tell Tom to.
- For Haru: Supabase now holds a classroom home (table, chair, floor; bathroom no-capture; plus watch and water bottle) that is not in `seed.sql`, so `dummy_data.sql` refuses to run. Please commit the classroom seed.
- Dummy sightings for the classroom were loaded at 19:20 (Tom asked), only through `log_sighting` and `mark_absent`: glasses on the table (chair before), keys in hand, water bottle next to the chair, watch gone from the table, bag never seen. Clear them with the rehearsal reset before real camera data.
- For Haru: your replay (`replay-05s-line`, from 21:11) writes into the same home the FaceTime agent is tested on, so answers change mid-test and the test look-alikes (brown bag, orange water bottle, not in your scene) get marked "not there anymore". That is correct behaviour, but it makes ground truth move. A second test home (another `HOME_ID`, same schema) would keep agent tests and your pipeline apart. Worth it?
- For Haru: look-alikes need (1) a `description` that tells them apart at enrollment ("big white mug" against "small white espresso cup"), since the agent asks with it, and (2) perception that tells them apart when logging (D8, `match_item`), or sightings land on the wrong one.
- For Haru: Tom renamed the assistant to **Find It** (what callers hear and see on the card). Repo, docs and internal ids still say Save It. Rename the project and the Devpost entry too?
- For Haru: Tom had two look-alikes enrolled in Supabase at 20:50 for testing "which one?": `brown bag` (alias `bag`; dummy stay on the floor) and `orange water bottle` (alias `water bottle`; dummy stays on the chair, then the table). They are not in `seed.sql` or the Typesense copy (re-run `scripts/sync_typesense.py`). Keep them for the demo, or delete them after the rehearsal reset?
- Enroll a wallet and a phone in the demo home? On the first test call they were the first things asked for; D2 kept the demo to glasses, keys and the bag.
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
- VS Code's `python.terminal.useEnvFile` (on in Tom's settings) injects the repo `.env` into every terminal, and `node --env-file` keeps injected values: the agent registered as `my-agent` (the root `.env` value) and Chert declined calls. `agent/env.mjs` now applies `agent/.env.local` first and drops `SUPABASE_*`/`DATABASE_URL`. Since 14 Nov it is off for this workspace on Tom's Mac (`.vscode/settings.json`, gitignored) and the stray `AGENT_NAME` is out of the root `.env`; terminals opened before that still carry the old values.
- FaceTime on an iPhone held upright crops about 100 px off each side of the agent's 1280×720 video. The card keeps text 160 px in: at most 16 characters per line at 70 px (DASHBOARD.md had said 22 at 56 px).
- `ask_item` matches names and aliases exactly, so "where are my glasses" came back `unknown_item`. The agent now drops filler words before `/find`; Typesense would do this properly (D25).
- voice.md `unknown_item` changed (Tom, 14 Nov): name the thing back ("I don't know your wallet yet, but your family can teach me."); ask "which thing" only when we did not catch one or two words.
