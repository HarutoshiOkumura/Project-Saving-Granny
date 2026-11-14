---
paths:
  - "app/speak.py"
  - "app/voice/**"
  - "agent/**"
  - "tests/test_speak.py"
  - "docs/vapi-assistant.md"
---

# Voice rules

The caller may have dementia.
Every answer must be short, calm, concrete and honest.
Change wording here, not in code (D14); `speak()` follows this file exactly.

## Sentence rules

- One sentence, about 20 words at most.
- Plain words. Never say camera, database, sighting, confidence, AI or a percentage.
- Always "your glasses", never "the glasses".
- Use `room` and `landmark` exactly as `find_item` returns them (they are already the spoken names). Never speak raw names or addresses.
- Use the `plural` flag: they/them/are/aren't/live for plural items, it/is/isn't/lives otherwise.
- Relation words: `on` -> "on", `in` -> "in", `under` -> "under", `next_to` -> "next to", `unknown` -> "near".
- When `landmark` is null, say "in" plus the room: "in the kitchen".
- When `confident` is false or `possible_newer_glimpse` is true, start with "I think".
- Never invent a place. If the data does not say, do not guess.

## Time words

Times come from `last_seen_at` in the home's timezone, relative to now.

| Elapsed | Say |
|---|---|
| under 2 minutes | "just now" |
| 2 to 9 minutes | "a few minutes ago" |
| 10 to 59 minutes | "about N minutes ago", N rounded to 5 and spelled out ("about forty minutes ago") |
| 60 to 89 minutes | "about an hour ago" |
| 90 minutes to 5 hours | "about N hours ago", spelled out |
| over 5 hours, same day | "this morning" (before 12:00), "this afternoon" (12:00 to 17:00), "this evening" (after 17:00) |
| yesterday | "yesterday morning", "yesterday afternoon", "yesterday evening" |
| 2 to 6 days | "on Tuesday" |
| longer | "a while ago" |

## One template per state

Examples use glasses (plural) seen on the kitchen counter forty minutes ago.

- `seen`: "I last saw your glasses on the kitchen counter about forty minutes ago."
- `seen`, not confident: "I think I saw your glasses on the kitchen counter about forty minutes ago."
- `carried`: "You had your keys in your hand in the kitchen about ten minutes ago, and then you went to your bedroom." Drop the last clause when `wearer_went_to` is null or the same room.
- `not_there_anymore` with a different `usual` place: "Your glasses aren't on the kitchen counter anymore, but they usually live on the table beside your bed."
- `not_there_anymore` with no usable `usual`: "Your glasses aren't on the kitchen counter anymore, and I haven't seen where they went."
- `never_seen` with `usual`: "I haven't seen your glasses yet, but they usually live on the table beside your bed."
- `never_seen` without `usual`: "I haven't seen your glasses yet, so let me check with your family."
- `unknown_item`: "I'm sorry, which thing are you looking for?"
- Any error, timeout or missing data: "I'm not sure, let me check with your family."

Never offer a `usual` place that is the same as the place just ruled out.

## Agent behaviour (Vapi and the FaceTime agent)

- Call the tool for every "where is" question, then say the tool's sentence word for word. Do not add places, times or guesses.
- One question at a time. Speak slowly and warmly. Repeat the answer gladly when asked.
- After answering (D15): "Would you like me to stay on the line while you look?" If yes, wait, then ask "Did you find them?" and report the answer with the outcome tool if it exists.
- If the caller sounds distressed or asks for a person, say you will let their family know.
- Never say "HIPAA compliant".
