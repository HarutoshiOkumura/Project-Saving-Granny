# Handoff for Tom's agent (15 Nov, about 03:00 EST)

Haru's session added backend fields and one agent tool while Tom was finishing the photo on the FaceTime card.
This note says how to fit them together with no surprises.
Contracts: `docs/CHERT.md` ("Where to look and the last-seen photo", "Safety: report_concern"); background: `docs/INSIGHTS.md`.
There is no dashboard yet (step 08): the FaceTime card is the only screen that shows any of this.

## 1. Merge first

Haru's push touches these agent files (all small and additive):

| File | Change |
|---|---|
| `agent/concern.mjs` (new) | `createConcernReporter()`: `POST /concerns`, swallows every failure, returns the sentence to say |
| `agent/test/concern.test.mjs` (new) | 7 tests |
| `agent/agent.mjs` | one import, one `createConcernReporter(...)` line next to `createSaveIt(...)`, and a `report_concern` tool at the top of the `tools` list (always offered, snapshot or not) |
| `agent/prompt.mjs` | `SAFETY_RULES` block, inserted into the instructions after "How you talk" |
| `agent/package.json` | `test` is now `node --test 'test/**/*.test.mjs'` (the old `node --test test/` failed on Node 24); `check` also checks `concern.mjs` |
| `agent/.env.example` | the `APP_TOKEN` comment |

If `agent.mjs` or `prompt.mjs` conflict with the photo work, keep both sides: the photo code and the `report_concern` tool and rules are independent.
Then run `npm test` (36 tests on Haru's side, plus yours) and `npm run check`.

## 2. Set `APP_TOKEN` in `agent/.env.local`

Copy the backend's `APP_TOKEN` from the root `.env` into `agent/.env.local`.
`saveit.mjs` and `concern.mjs` already send it as `Authorization: Bearer ...` when it is set.
Without it, `/snapshot` still answers but every `photo_url` is `null`, and `POST /concerns` is refused (401, swallowed; the agent still says its sentence).

## 3. The photo: use `photo_url` from the snapshot

Each `/snapshot` entry now looks like this (trimmed; every older field is unchanged):

```json
{
  "item": "glasses",
  "sentence": "I last saw your glasses on the table just now.",
  "result": {"state": "seen", "landmark": "the table", "room": "the classroom",
             "photo": "crops/1111.../glasses/20261115T070934304879Z.jpg", "...": "..."},
  "photo_url": "https://<project>.supabase.co/storage/v1/object/sign/crops/...jpg?token=...",
  "where_to_look": {
    "band": "high",
    "places": [{"landmark_id": "2bfe...", "room": "the classroom", "landmark": "the table",
                "address": "b_school_classroom > table", "pct": 89,
                "why": ["last_seen", "home"], "minutes_ago": 3}],
    "elsewhere_pct": 11,
    "ruled_out": null
  }
}
```

- **Show `photo_url`, not `result.photo`.** `result.photo` is a storage path; turning it into a link needs a Supabase key, and the agent must never hold `SUPABASE_*` keys (`CLAUDE.md`, one env file per process).
  If the photo work signs paths itself or reads Storage directly, switch it to `photo_url`.
- The link works for **1 hour** from when `/snapshot` answered.
  For a call that runs longer, reload `/snapshot` (or treat a failed image fetch as "no photo") rather than retrying the old link.
- `photo_url` is `null` for an item never seen, without the token, or when signing failed: show the card without a photo, never a placeholder that looks like a real picture.
- Fetch the image into memory for the card; do not write it to disk.
- **Never log `photo_url`**: the query string is a credential for that crop. Log `photo: true/false` instead.
- Crops can be small or cut off (the false keys crop is about 90 x 60 px; the glasses crop clips a lens). Scale with smoothing and keep the photo modest on the card rather than full-screen.

## 4. "Where to look" on the card (the judge's first ask)

- `where_to_look.places` is most likely first, at most 4, with whole `pct` values that add up to 100 with `elsewhere_pct`.
  `room` and `landmark` are the spoken words, the same as in `result`.
- **The card may show the percentages** (bars, "the table 67%", "the chair 25%"); **the voice must never say them** (`.claude/rules/voice.md`: no percentages). The voice says the places in order: "Try the table first, then the chair."
- `why` says what put a place there: `last_seen`, `glimpse` (one newer camera frame; a hint), `usual` (two or more settled stays), `home` (where the family says it belongs). Good for a small label under each bar.
- `band`: `high`, `split` or `low`. Offer the list when it is not `high`, or when the caller says it is not there.
- `ruled_out` is the place just seen empty: never show it as a place to look.
- `landmark_id` is there for `POST /locate` later (the arrow); nothing uses it yet.
- One easy win: `nextAfterMiss()` in `saveit.mjs` offers only `result.usual` after "it's not there". Walking `where_to_look.places` in order (skipping the place just checked) gives a second and third suggestion with no new backend call.

## 5. Safety: already wired, needs a voice test

- `report_concern` is in the tool list and the prompt has `SAFETY_RULES`; nothing else to wire.
- Please try on a test call: "I fell" (expect "Are you hurt?" once, then the safety sentence), "help me find my keys", "my glasses fell", "the bag fell off the chair", "I lost my keys" (all four must just be normal find questions), and "someone wants gift cards" (the scam sentence at once).
- The sentences are fixed in `voice.md` "Safety" and checked by a test. The agent never says it told anyone: there is no family notification channel yet.
- Optional for the card: a calm state while a concern is raised (for example the steady marker and "I'm here with you"), with no red and no alarm look.
- Each report writes one `report_concern` line to the call log with the backend's `id` and `urgency`. To see raised concerns: `curl -H "Authorization: Bearer $APP_TOKEN" localhost:8000/api/concerns`.

## 6. Do not

- Put `SUPABASE_*` keys in the agent, or sign photo paths there.
- Log `photo_url`, transcripts (outside `LOG_TRANSCRIPTS=1` testing) or image bytes.
- Speak a percentage, or promise to contact family.
- Show or speak a disease word ("decline", "confused", "dementia") anywhere a caller can see or hear it.
