---
description: Step 08 - family dashboard with timeline, crops and the "tell Save It" form
---

# Step 08: Family dashboard

Read `docs/STATUS.md`, `.claude/rules/memory-db.md`, and `docs/DECISIONS.md` D16, D17 and D21.
Depends on: 02.
Time box: 1.5 hours.

## Build

1. `GET /api/timeline` (requires `APP_TOKEN`): the `timeline` view for `HOME_ID`, newest first, last 50 rows, with crop paths turned into signed URLs valid for 1 hour (D17). Pydantic response model.
2. `GET /api/places` and `POST /api/told` (requires `APP_TOKEN`): `{item, landmark, note}` becomes `log_sighting` with `p_event = 'told'` and `p_source = 'manual'`; names are validated against the seed.
3. `app/web/dashboard.html`, static: polls every 2 s (D16); one card per item with its current place, relative time and crop; the history below; a "Tell Save It" form with item and place dropdowns; a debug toggle that also shows tentative sightings.
   Large, readable text; works at phone width and on a laptop; no Supabase key in the page.

## Checks

- pytest for the routes with the database faked; ruff clean.
- Live: a "told" entry appears within 2 s, and `find_item` returns it.
- Look at the page on a phone and on a laptop, and fix anything that looks off.
