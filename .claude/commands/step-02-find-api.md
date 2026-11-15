---
description: Step 02 - find API, Pydantic result model and speak()
---

# Step 02: Find API and speak()

Read `docs/STATUS.md`, `.claude/rules/voice.md`, `.claude/rules/memory-db.md`, and `docs/DECISIONS.md` D13 and D14.
Depends on: 00, 01.
Time box: 1 hour.

## Build

1. `app/memory/db.py`: one Supabase client built from `SUPABASE_URL` and `SUPABASE_SECRET_KEY`, and `ask_item(query, channel) -> FindResult` calling the `ask_item` RPC (or `find_item` if step 01 did not add it).
   Check the supabase-py `rpc` call in the Supabase docs (`search_docs`) before writing it.
2. Pydantic models: `FindResult` with every key listed in `CLAUDE.md`, and `Place` for `previous` and `usual`. Missing optional keys are `None`; unknown extra keys are ignored.
3. `app/speak.py`: `speak(result: FindResult, now: datetime) -> str`, a pure function that follows `.claude/rules/voice.md` exactly.
4. `GET /find?item=...` returns `{"sentence": ..., "result": ...}`. On any database error or a 2-second timeout, return the fallback sentence from the voice rules and log the error.
5. One log line per question: query, state, sighting id, milliseconds.

## Tests

- `tests/test_speak.py`: at least one test per state, plus plural and singular, landmark missing (room only), `usual` missing, `usual` equal to the ruled-out place, `confident` false, `carried` with and without `wearer_went_to`, and every time band in the voice rules.
- `tests/test_find.py`: the route with `db.ask_item` faked, and the fallback when it raises.
- No network in tests.

## Checks

- `uv run pytest -q` and ruff are clean.
- With the smoke-test rows from `docs/SUPABASE.md` section 5 loaded, `curl -s "localhost:3000/find?item=my%20specs"` returns one sentence naming the kitchen counter and about forty minutes ago.
- Time 20 calls: median under 300 ms, worst under 1 s. Record the numbers in STATUS.
- Delete the smoke-test rows.
