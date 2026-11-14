# Read path: rank_item, record_miss, speak

## rank_item (migration 0002; additive, changes nothing in 0001)

`rank_item(p_home uuid, p_query text, p_now timestamptz default now()) returns jsonb`

Call it from every voice tool and from `/find`. It is one DB call, about 0.5 ms on scratch Postgres. `p_now` exists for tests; production uses the default.

```json
{"item": "glasses", "plural": true, "wearer_room": "the kitchen", "band": "split",
 "places": [{"landmark_id": "…", "room": "your bedroom", "landmark": "the table beside your bed",
             "p": 0.728, "why": "camera", "minutes_ago": 60, "misses": 0}],
 "search_order": [{"landmark_id": "…", "room": "the kitchen", "landmark": "the kitchen table",
                   "p": 0.208, "seconds": 9.0}],
 "find": {"state": "seen", "…": "find_item(p_home, p_query), unchanged"}}
```

**Fields:**
- `places`: up to 5, most likely first. `why` is one of:
  - `camera`
  - `family_said`
  - `you_said`
  - `usual`: no live sighting there, only habit. `minutes_ago` is then null.
- `search_order`: up to 5, best place to check first. Sorted by p × find_chance / seconds.
- Unknown item: the result is `{"state": "unknown_item", "heard": "<query>"}` with no `find` key.

**Model:**
- **trust:**
  - camera (`seen`, `placed`, `confirmed_live`, `tour`): 1.0
  - family (`told` + `manual`): 0.9
  - `live_hint`: 0.5
  - the person on a call (`told` + `facetime_caller`): 0.4
- **retire:** a newer active or superseded sighting retires an older one only if newer trust ≥ min(older trust, 0.8). A spoken claim cannot erase camera evidence; the family or the camera can.
- **habit:** 0.02 at every place, + 0.3 at `items.home_landmark_id`, + 0.7 × the place's share of past (retired or contradicted) stays.
- **evidence:** Σ trust × exp(−age / 6 h) over live stays at a place. A one-frame (tentative) glimpse counts 0.3×.
- **misses** count only if in the last 12 h and newer than the newest evidence there. Two kinds: camera `absent_count` and `record_miss` rows. Each multiplies the place by (1 − find_chance).
- **score** = (0.6 · habit + evidence) · (1 − find_chance)^misses. **p** = score / Σ score.
- **Landmark defaults** (`find_chance` and `check_seconds` columns, new and nullable; null means the kind default):

  | kind | find_chance | check_seconds |
  |---|---|---|
  | surface | 0.9 | 3 |
  | fixture | 0.95 | 2 |
  | container | 0.6 | 8 |
  | floor | 0.7 | 6 |
- **walk seconds** are measured from the wearer's room (the latest `observations.room_id`):

  | wearer is | walk seconds |
  |---|---|
  | in the same room | 6 |
  | in a linked room | 15 |
  | anywhere else | 25 |
  | unknown | 15 |

  Check seconds are added on top.
- **band:**
  - high if p1 ≥ 0.6 and p1 − p2 ≥ 0.25
  - split if p1 + p2 ≥ 0.6
  - low otherwise
- Every place in the home is a candidate, including no-capture rooms (habit only).

## record_miss

`record_miss(p_home, p_item, p_landmark, p_at default now(), p_source default 'caller')`

- Use it when the person checked a suggested place and it wasn't there. **Use it instead of `record_outcome`.**
- The same (item, place, time) counts once.
- Raises if the place or item isn't in the home.
- Sources: `caller`, `manual`, `worn_cam`.

## Tests (scratch Postgres only)

```bash
psql postgresql://postgres:pw@localhost:54329/postgres -v ON_ERROR_STOP=1 \
  -f supabase/migrations/0001_save_it_memory.sql -f supabase/migrations/0002_ranked_search.sql \
  -f supabase/tests/test_memory.sql -f supabase/tests/test_ranking.sql
```

- 46 + 13 = 59 checks pass on Postgres 16.15. That run used a stand-in for pgvector; 0002 uses no vectors.
- It prints a sample `rank_item` result at the end.

**Behaviour the tests prove:**
- Camera twice at the nightstand 60 min ago, then the person says "kitchen table":
  - `find_item` answers kitchen table, `confident: true`;
  - `rank_item` keeps the nightstand first (`camera`) and the kitchen table second (`you_said`).
- `record_miss` at the nightstand → the kitchen table leads.
- The family types "drawer" after the camera saw the keys on the hook → drawer first, hook second, band split.
- One empty camera look at the counter → the usual table leads.
- Nothing known and the wearer in the kitchen → kitchen places first in `search_order`, band low.

## speak(): rank_item JSON → spoken text (`app/speak.py`, pure, one pytest per case)

Cases:
- `unknown_item`
- band high, split and low
- `why` = `you_said` vs `camera`
- `find.state` = `carried`
- plural vs singular (`plural` picks is/are)
- a place with misses
- never seen (`why` = `usual`)

| Case | Say |
|---|---|
| high | "Your glasses are on the table beside your bed." If the camera saw it, add "I saw them there about an hour ago." |
| split | "Probably on the table beside your bed. If not, the kitchen table." |
| low | "I'm not sure. Let's check the kitchen table first." Then offer: "Shall I ask June to help?" Use the family member's name from config. |
| carried | "You had your glasses in the kitchen." Then the top place. |
| `you_said` ranked below the camera | "You told me the kitchen table, but I saw them by your bed." |
| unknown | "I don't know that one yet. I'll ask your family to add it." |

**Voice rules** (until `.claude/rules/voice.md` exists):
- ≤ 12 words per sentence, ≤ 2 sentences per turn.
- Repeat the item name; never "it" or "them" alone.
- Relative times only ("about an hour ago", "this morning").
- Never quiz ("do you remember…?"). One instruction per turn.
- Use landmark words exactly as stored.
- Never tell the person to climb, kneel or reach high; suggest waiting for family instead.

## Read-side build order (Tom)

1. `app/speak.py` + tests.
2. `GET /find?item=` (step 02) → `rank_item` → `speak()`, returning `{say, rank}`. Needs steps 00 and 01.
3. Chert FaceTime agent (`docs/CHERT.md`).
4. Typesense resolver and sync (`docs/TYPESENSE.md`). It sits in front of `rank_item`.
5. Dashboard (`docs/DASHBOARD.md`).
6. Demo assets: the comparison chart and video (`docs/SPONSORS.md`).
