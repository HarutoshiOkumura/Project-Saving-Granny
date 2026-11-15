# Status

Claude Code updates this at the end of every step. Humans edit it freely. Keep it under one screen.

Last updated: Sat 14 Nov, 19:27 EST

## Steps

| # | Step | State | Notes |
|---|---|---|---|
| 00 | Scaffold | done | uv project (Python 3.12.15, `uv.lock` committed), ruff, package layout, `app/config.py` (`get_settings()`), `GET /health`, 10 tests. Left for humans: D5 and D6 (below) |
| 01 | Supabase | done | `0001` (8 fixes) and `0002` applied; 75/75 checks on scratch (82/82 with Supabase roles); home seeded; private `crops` bucket; smoke test and API key checks pass; `ask_item` median 98 ms over HTTPS. Left: MCP read-only (below) |
| 02 | Find API and speak() | done | `GET /find?item=...&channel=web` -> `app.ask.ask()` -> `db.ask_item` + `speak()`; 80 new tests (90 total). Live on Supabase: "my specs" -> "I last saw your glasses on the kitchen counter about forty minutes ago." 20 calls: median 50 ms, worst 114 ms; first call after a restart 115 to 160 ms (one 865 ms outlier, likely cold DNS). Dead database: fallback at 2.0 s; bad hostname: 46 ms. Smoke rows deleted |
| 03 | Phone voice | todo | Call `app.ask.ask(item, "phone")`, not `db.ask_item` + `speak()`: the 2 s timeout, fallback and log line are already there. `/find` has no auth yet; once the tunnel is up anyone can query it, so add a token check then |
| 04 | Detector bake-off | todo | Keys are in `.env` (`ROBOFLOW_API_KEY`, `GOOGLE_API_KEY`). Names decided (D1, D2) and seeded on Supabase. Waiting on staged photos in `tests/fixtures/frames/`. Candidates now include Gemini (D24) |
| 05 | Perception module | todo | Gemini, not Claude (D24): Interactions API, `store=False`, `thinking_level` `low`, 15 s timeout, frames processed concurrently (Flash took about 7 s per image in Roboflow's evals) |
| 06 | Ingest worker | todo | Catch `22023` from `log_sighting` (room and landmark disagree) and skip the frame |
| 07 | Capture page | todo | |
| 08 | Dashboard | todo | |
| 09 | Typesense | todo | optional |
| 10 | FaceTime | todo | optional; blocked on D4. The agent calls the backend's `GET /find` (step 02), never Supabase. Build against `supabase/dummy_data.sql` (rewritten 14 Nov for the classroom names) |
| 11 | Harden and record | todo | |

State is one of: todo, doing, done, stubbed (works with fake data), blocked (say on what).

## Checkpoints

- CP1 phone call answers from seeded data: not yet (the backend half works: `GET /find` answers from Supabase)
- CP2 detector chosen: not yet
- CP3 replayed walk gives three correct answers: not yet
- CP4 live from the lanyard phone: not yet

## Stubs and fakes in the code right now

(none)

## Defaults taken from DECISIONS.md

- D1, D2: the B School classroom (one room plus a no-capture bathroom corner), landmarks table, chair, floor; items glasses, keys, bag, watch, water bottle. Re-seeded on Supabase on 14 Nov; `seed.sql` can now be re-run and refuses while anything is logged.
- D11: stay-merge 10 min, 3 empty looks to contradict, now at least 30 s apart (`mark_absent` `p_min_gap`); confidence cut 0.5.
- D13: one home, `HOME_ID=11111111-1111-1111-1111-111111111111`.
- D15: `ask_item` logs every question so `record_outcome` can retire a wrong answer; whether the voice asks "did you find it?" is still open.
- D17: `crops` bucket is private, JPEG only, 1 MiB cap.

## Tuned values

(blur threshold, duplicate threshold, detector confidence, similarity cut)

## Open questions for the humans

- 3D scan (D25): judges liked the point cloud idea on 14 Nov. Plan: finish the original steps first; after CP3 and CP4, maybe A (3D view on the dashboard, 2 to 3 h, no pipeline change) and C (local room check against the scan before frames go to Gemini, 2 to 4 h more). Optional now: record the scan video while the staging is up.
- **Before any real camera frame (step 06 replay of a real walk, step 07):** link a billing account to the Google AI Studio project behind `GOOGLE_API_KEY`, then turn logging off (AI Studio, Logs and Datasets; it turns on by default with billing), and check its per-model rate limit in AI Studio (the capture page sends up to 30 frames a minute). On the free tier Google may use and human-review the images (D24).
- **⚠ D5 and D6 are decided but UNVERIFIED** (MacBook Pro, Coder workspace, Cloudflare Quick Tunnel, iPhone 17). Run checks A1 to A6 in `docs/DECISIONS.md` D5 in the first end-to-end test (step 03 at the latest) and write the results here. Each check has a fallback.
- Humans, before step 03: Coder server and a Docker workspace on the Mac (screenshot it), the tunnel address in `PUBLIC_BASE_URL` (empty now), a name for who owns the Mac during judging, and ask the Coder table whether a self-hosted server counts (D6).
- After step 01: make the Supabase MCP read-only by adding `&read_only=true` to the URL in `.mcp.json`.
- Stage one table and one chair and keep the classroom's other tables and chairs out of frame, or "on the table" does not say which one. Want more precise spoken names ("the table by the window")? One SQL update on `landmarks.spoken_name`.
- The bag, watch and water bottle have no usual place. One SQL update on `items.home_landmark_id` adds one.
- Tom: the dummy data now uses the classroom names. Pull, then reload `supabase/dummy_data.sql` if you want test sightings.
- D4: pick a cut-off time for Chert's answer; FaceTime is 4 to 6 hours.
- D15: keep "did you find it?"? It needs a second Vapi tool; the database side (`ask_item`, `record_outcome`) is ready.
- Photo idea (14 Nov): keep the item's last good view instead of its best-confidence one, and a wider "context" crop that shows the landmark. Decide in step 05/06 on real fixture crops. Full frames stay out (hard rule).
- `package.json`, `package-lock.json` and `node_modules/` (`@supabase/server`) appeared in the repo root at 15:36. The app is Python; delete them unless someone needs them.

## Things that differ from the docs or from CLAUDE.md

- Perception switched from Claude to Gemini on 14 Nov (D24). `anthropic` is gone from the dependencies; `google-genai` 3.3.0 replaces it. `ANTHROPIC_API_KEY` became `GOOGLE_API_KEY`, and the local `.env` had its stale `PERCEPTION_MODEL=claude-haiku-5-5` replaced. `CLAUDE.md`, the perception rules, steps 00, 04, 05 and 11, `docs/ROBOFLOW.md` and D6 now say Gemini.
- Google's docs now lead with the Interactions API; `generateContent` is legacy but supported. Interactions stores requests by default, hence `store=False` everywhere.
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
