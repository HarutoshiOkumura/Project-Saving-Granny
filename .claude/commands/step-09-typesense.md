---
description: Step 09 (optional) - Typesense typo and synonym matching for item names
---

# Step 09: Typesense name matching (optional)

Read `docs/STATUS.md` and `docs/DECISIONS.md` D18, then the current Typesense API docs at https://typesense.org/docs/ before writing calls.
Depends on: 02.
Time box: 1.5 to 2 hours.
This is third in the cut order (`docs/PLAN.md`); skip it if the core demo is not passing.

## Build

1. `scripts/sync_typesense.py`: one collection of items (name, aliases) read through `app/memory/db.py`; safe to run repeatedly.
2. `app/names.py`: `resolve(spoken: str) -> str` with typo tolerance and a 300 ms timeout. On any failure it returns the input unchanged, so `find_item` still runs. Postgres stays the source of truth.
3. The voice paths call `resolve` before `ask_item`.

## Checks

- "specs", "spectecles" and "my reading glases" all resolve to glasses.
- An item that is not enrolled stays unknown.
- With Typesense stopped, phone answers still work.
