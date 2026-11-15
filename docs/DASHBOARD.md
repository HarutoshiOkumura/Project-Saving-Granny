# Family dashboard, and what the person sees and hears

There are two audiences:
- **the person with dementia:** voice and FaceTime video only;
- **the family:** the dashboard.

Coder for Good judges "User Experience & Design". The Typesense sheet also scores "Design & User Experience: accessibility and ease of use".

## Visual constants (use everywhere; WCAG AAA)
- **Font:** Atkinson Hyperlegible (Braille Institute; on Google Fonts). Body 28 px, headings 44 px, line height 1.5.
- **Colours:**

  | Role | Colour | Contrast on white |
  |---|---|---|
  | text on white `#FFFFFF` | `#111111` | ≈18.9:1 |
  | accent | `#0842A0` | ≈9.1:1 |
  | alert | `#8C1D18` | ≈9.1:1 |

  Text needs at least 7:1.
- **Family dashboard palette (15 Nov, a medical-portal look after Kaiser Permanente's public site, without its name, logo or layouts):** ink `#0d1c3d` (text, top bar), brand `#003b71` (actions, links, active tab), signal `#0078b3` (bars, focus ring, tab underline; never text: 4.84:1), muted text `#464f63` (KP's `#677083` fails 7:1 as text), pale band `#f2f8fb`, line `#d3d6dc`, alert `#8C1D18`. Atkinson Hyperlegible stays (KP's Gotham is licensed). Every text pair is at least 7:1 (measured by `.cache/redesign/contrast.py`). The person-facing colours above are unchanged.
- **Touch targets ≥ 72 px.** The Mira team found 44 px buttons unusable for 80-year-olds.
- ≤ 3 choices per screen.
- Never use colour alone; pair it with a shape and words.
- Animations ≥ 600 ms. Any pulse ≤ 1 Hz, well under 3 flashes/s.
- **FaceTime video card** (the agent's camera track, 1280×720):
  - FaceTime on an iPhone held upright shows only about the middle 84% of the width (test call, 14 Nov): keep everything readable at least 160 px from each side;
  - ≤ 2 lines × ≤ 16 characters (22 ran into the cropped edges);
  - 70 px white text on a dark band (was 56 px);
  - shows the place name and the last-seen crop;
  - a marker below the text: orange ring and red dot pulsing at 1 Hz while Save It talks; steady green the moment the caller's voice comes in, from a level meter on their audio (`agent/voice-meter.mjs`; about 0.3 s from voice to green on the video, measured 14 Nov); dim otherwise. No word under the light: Tom's choice on 14 Nov, after a version that said LISTENING.
- **Marker on a photo** (values from Mira's `object_finder.py`):
  - a red (255,50,50) dot with a warm orange (255,180,60) ring;
  - a 3 s slow zoom to it, then a 3 s pulse.

## Voice rules (patient-facing)
- Speech rate about 0.9.
- ≤ 12 words per sentence, ≤ 2 sentences per turn, about 800 ms pause between steps.
- After 8 s of silence, reprompt, at most twice; then offer to call family.
- Repeat the item name. One instruction per turn. No memory quizzing. Use landmark words.
- Never send the person to climb, kneel, reach high, go outdoors or use stairs.

## Pages (static HTML in `app/web/`, no build step, per `CLAUDE.md`)
- **Timeline.** Per D16, poll the backend every 2 s; no Supabase key in the browser. Show the latest sightings with crops (signed URLs, 1 h) and status badges that use shape plus text.
- **Item page.** `rank_item` bars (p per place, why, minutes ago) and the search order. This shows judges the answer is ranked, not just "last seen".
- **"Tell Save It" form.** Item + place → `told` + `manual` (trust 0.9).
- **Facts form** (D29) → Typesense `facts`.
- **Search box.** Typesense union search with a scoped key (or via the backend), plus the NL line "Save It understood: …".
- **Insights.** Popular questions and "couldn't answer" (Typesense analytics), each with an "Enroll" button.
- **Compare toggle.** The same question answered by last-seen (`find_item`, MemPal-style) and by ranking (`rank_item`).

## Privacy
- Say "built with HIPAA-style safeguards". Never say "HIPAA compliant".
- Crops only, in a private bucket, served by signed URLs (`CLAUDE.md`).
- **Before any external LLM call** (Typesense NL/RAG → Gemini; the call agent's model), send the minimum:
  - replace full names, addresses, phone numbers and dates of birth with tokens like `[[PERSON_1]]`;
  - put the real values back locally after the reply.

  This follows the idea behind Mira's `minimizeForLLM`: send the age range, conditions and medications, not identity.
- Demo phone numbers use the fictional 555-01xx range.
- The patient-facing scoped key cannot read caregiver-only notes (embedded filter).
- Blur faces before sending caller frames to a vision model, and never store those frames.

## Dashboard API (step 08, 15 Nov)

The page is `app/web/dashboard.html`, served at `GET /dashboard` with no secrets in it.
It asks the family member once for the `APP_TOKEN` and keeps it in this browser (`localStorage`, with a "Sign out" button).
Every call below sends `Authorization: Bearer <APP_TOKEN>`; a 401 means "ask for the token again".
All text from the server goes into the page with `textContent`, never `innerHTML`.

| Call | Use | Reply |
|---|---|---|
| `GET /api/board` | Polled every 2 s (D16) | `{person, timezone, now, items: [snapshot entry], concerns: {concerns: [...], quiet_day}, camera: {worn_minutes_today, last_frame_at}}` |
| `GET /api/timeline?debug=false` | History, polled every 10 s | `[{sighting_id, item, event_type, status, in_hand, first_seen_at, last_seen_at, room, landmark, photo_url}]`, newest first, at most 50. `item` null means an unregistered object. `debug=true` adds one-frame (`tentative`) stays |
| `GET /api/setup` | Dropdowns and the setup tab | `{rooms: [{id, name, spoken_name, capture_allowed}], places: [{landmark_id, room_id, room, landmark, kind}], items: [{id, name, aliases, category, color, description, plural, home_landmark_id}]}` (`room` and `landmark` are spoken names) |
| `GET /api/places` | The same `places` list alone | |
| `POST /api/told` | "Tell Save It where it is" | body `{item, landmark_id, note?}`; reply `{sighting_id, sentence}`: what Find It will now say |
| `POST /api/items` | Add an item (D26 A) | body `{name, color?, description?, aliases?, kind?, plural, home_landmark_id?}`; 201 with the item; 409 `{detail}` when the name or an alias is already used; the camera looks for it within 30 s |
| `POST /api/rooms` | Add a room | body `{name, spoken_name?, capture_allowed}` (`capture_allowed` has no default: the family must choose); 201; 409 on a duplicate |
| `POST /api/landmarks` | Add a place things get put down on | body `{room_id, name, spoken_name?, kind}` (`kind`: surface, container, fixture, floor); 201; 409 duplicate; 422 for a no-capture room |
| `GET /api/concerns`, `POST /api/concerns/{id}/handle` | Safety loop (docs/INSIGHTS.md) | handle body `{status: on_my_way, calling_911 or all_ok, by}` |
| `GET /api/patterns?days=28` | Patterns tab, on open and every 60 s | see `app/patterns.py` `Patterns` |
| `GET /api/events`, `POST /api/events` | Family tags | body `{kind, starts_at, ends_at?, note?}` |

A snapshot entry (`items[]`) is the `/snapshot` shape in `docs/CHERT.md`: `item`, `sentence`, `result` (with `state`, `room`, `landmark`, `last_seen_at`, `photo`), `where_to_look`, `photo_url`.
Photo links are cached on the server for 50 minutes, so the same storage path keeps the same link: replace an `<img>` only when `result.photo` changes, so photos do not flicker on every poll.
Percentages from `where_to_look` may be shown on the page; they are never spoken.
