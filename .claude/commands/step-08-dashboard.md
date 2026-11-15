---
description: Step 08 - family dashboard with timeline, crops and the "tell Save It" form
---

# Step 08: Family dashboard

Read `docs/STATUS.md`, `.claude/rules/memory-db.md`, and `docs/DECISIONS.md` D16, D17, D21 and D26.
Depends on: 02.
Time box: 2.5 hours (1.5 for the dashboard, 1 for "add an item").

## Build

1. `GET /api/timeline` (requires `APP_TOKEN`): the `timeline` view for `HOME_ID`, newest first, last 50 rows, with crop paths turned into signed URLs valid for 1 hour (D17). Pydantic response model.
2. `GET /api/places` and `POST /api/told` (requires `APP_TOKEN`): `{item, landmark, note}` becomes `log_sighting` with `p_event = 'told'` and `p_source = 'manual'`; names are validated against the seed.
3. `app/web/dashboard.html`, static: polls every 2 s (D16); one card per item with its current place, relative time and crop; the history below; a "Tell Save It" form with item and place dropdowns; a debug toggle that also shows tentative sightings.
   Large, readable text; works at phone width and on a laptop; no Supabase key in the page.
   A sighting with no item (an unowned one, step 12) shows as "unregistered object" rather than breaking the card; the `timeline` view has no `label` column until step 12 adds it.
4. "Add an item" (D26 A): `POST /api/items` (requires `APP_TOKEN`) with name, colour, short description, optional aliases and optional usual place, inserted through `app/memory/db.py`.
   Refuse a name or alias that is already any item's name or alias (case-insensitive, after dropping "my", "the", "a"), so a new item cannot shadow another ("bottle").
   A form on the dashboard for it. The camera starts looking for the new item within 30 s with no restart (the worker's context cache); say so on the page.
   Optional if time allows: a photo of the item, from which Gemini writes the colour and description (staged objects only until the privacy rules are revised).

## Checks

- pytest for the routes with the database faked; ruff clean.
- Live: a "told" entry appears within 2 s, and `find_item` returns it.
- Live: add a staged item from the form, replay or film it put down, and `find_item` answers for it. A clashing name or alias is refused.
- Look at the page on a phone and on a laptop, and fix anything that looks off.
