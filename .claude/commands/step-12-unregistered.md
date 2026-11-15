---
description: Step 12 (optional) - remember unregistered objects and answer for them with a hedge (D26 C)
---

# Step 12 (optional): Remember unregistered objects

Read `docs/STATUS.md`, `.claude/rules/perception.md`, `.claude/rules/memory-db.md`, `.claude/rules/voice.md`, and `docs/DECISIONS.md` D3, D21 and D26.
Depends on: 03, 06, 08.
Time box: 3 to 4 hours.

Start only if `docs/STATUS.md` shows CP1 and CP4 passed, and not later than 01:00 on Sun 15 Nov (D26).
Otherwise stop and say so: this step is the first to cut after the 3D scan (`docs/PLAN.md`).

## Goal

"Where's my orange bottle?" gets "I saw an orange bottle on the table about ten minutes ago, but I'm not sure it's yours", with a photo on the dashboard, although nobody registered an orange bottle.
Registered items must behave exactly as before.

## Build

1. Perception (`app/perception/schema.py`, `vlm.py`): an `others` list beside `items`, each entry a category from a fixed list (start with bottle, bag, keys, glasses, wallet, phone; one constant), a short free-text label ("orange water bottle"), the landmark, relation, confidence and `box_2d`.
   The prompt says: report an object under `others` only when it matches no listed belonging; never describe people.
   Registered items keep their enum; a look-alike of a registered item still goes to `items`.
2. SAM 3 (`detector.prompts_for`): add the category words as prompts (16 at most in total), so the gate opens for them.
3. Worker (`app/worker/ingest.py`): the drop rules apply to `others` too (no-capture room, unsure room, no place, item cut, one entry per label).
   Each kept one is logged with `log_sighting(p_item null, p_label = label)`, with its crop.
   Unowned sightings never count as visible items for `mark_absent`.
4. Database: `supabase/migrations/0003_unowned_lookup.sql`.
   A question that matches no item name or alias searches recent unowned sightings by label (word overlap or `pg_trgm`, your call; test both kinds of question below) and returns the best one under a new key on `unknown_item` (or a new state), with label, address, minutes ago and photo.
   Add `label` to the `timeline` view.
   Write the checks in `supabase/tests/test_memory.sql` first and see them fail; run them on scratch Postgres only; then apply with the Supabase MCP. Same revoke and grant as the other functions, and `set search_path`.
5. Voice: the hedged sentence in `.claude/rules/voice.md` first, then `speak()` and its test. Always hedged, never "your".
6. Dashboard: show unowned sightings by label, marked as "maybe not yours".

## Tests

- Schema and prompt: `others` enum and required fields; registered items unchanged.
- Worker: an unowned object is logged with no item; it never changes a registered item's belief; it is not in `mark_absent`'s visible list; the drop rules apply.
- `speak()`: the hedged sentence.

## Checks

- pytest and ruff are clean; the database tests pass on scratch.
- `RUN_LIVE=1 LIVE_FRAMES=all uv run pytest -m live -s` still gives 17/17 for the registered items, with no registered item reported falsely. Record what lands in `others` on the fixtures.
- Replay the CP3 take at 0.5 s: the four answers are unchanged. Count the unowned sightings it stores (the noise level) and list them in STATUS.
- Put an unregistered staged object down on camera and ask for it by colour and kind: the hedged answer comes back. Ask for a registered item by an alias: unchanged.
