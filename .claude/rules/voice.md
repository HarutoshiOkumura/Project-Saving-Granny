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
- `never_seen` without `usual`: "I haven't seen your glasses yet."
- `unknown_item`: "I don't know your wallet yet, but your family can teach me." Name the thing from `heard` after dropping question and filler words ("where is my wallet" -> "wallet"). If that leaves anything but one or two words, we did not catch it: "I'm sorry, which thing are you looking for?" (Changed 14 Nov after a test call: the question alone sounded as if Save It had not listened.)
- Any error, timeout or missing data: "I'm not sure right now."
- Never promise to contact family or anyone else: nothing can call or message them yet (the family call is paused; Tom, 14 Nov). A test call showed the promise making the agent try a tool that does not exist and then say a second, contradictory sentence.

Never offer a `usual` place that is the same as the place just ruled out.

## Guided directions (`GET /guide`, `app/guide.py`)

While the caller walks, the newest camera frame says where they are, and `guide()` gives one step.
The sentence rules above apply. A step that says where the item is starts with "I think" when the memory is not sure; a step that only gives a direction is never hedged.
Examples use glasses on the kitchen counter, with the caller starting in the bedroom.

- `no_view` (no frame in the last 30 seconds): "Look for your glasses on the kitchen counter in the kitchen." Not sure: "I think your glasses are on the kitchen counter in the kitchen."
- `go_to_room`, more than one room away: "From your bedroom, walk to the hallway first." Only the next room, never the whole route.
- `go_to_room`, the next room (or no known way): "From the hallway, walk to the kitchen, and I'll help you from there."
- `other_floor`: "I last saw your glasses in the kitchen, and that is on another floor." Never a direction: we never send anyone to the stairs.
- `look_for` (right room, landmark not in view): "You're in the right room, so look for the kitchen counter." With no landmark: "You're in the right room, and I last saw your glasses in here."
- `in_view` (the landmark is in the newest frame): "You're close, so look on the kitchen counter in front of you for your glasses." Not sure: "I think your glasses are on the kitchen counter in front of you."
- `item_in_view` (the item itself is in the newest frame): "I can see your glasses on the kitchen counter in front of you."
- `in_hand` (seen in their hand in the last minute): "You have your glasses in your hand now." This ends the guiding.
- `none` (anything but `seen`): the plain `speak()` sentence, and the guiding ends.
- `unsure` (any error): "I'm not sure right now." The agent says it only as a first reply, never mid-walk.

The FaceTime agent (`agent/guide.mjs`) says a step at once when it is closer than the last one, and a step that is no closer only after it has held for three polls (6 seconds). Directions are at least 5 seconds apart, at most 8 per walk, never over the caller's voice, and stop after 3 minutes.

## Agent behaviour (Vapi and the FaceTime agent)

- FaceTime agent (changed 14 Nov after a test call felt scripted and slow): when a call starts it loads every item's sentence (`GET /snapshot`) and answers in its own words from those, in one turn instead of a tool round trip. It keeps every place and time exactly as given and never adds a place, time or item; anything not in the snapshot goes through the tool. The card and the question log follow what the caller said.
- Phone (Vapi): call the tool for every "where is" question, then say the tool's sentence word for word. Do not add places, times or guesses.
- The assistant's spoken name is **Find It** (Tom, 14 Nov; was "Save It"). Internal ids (`save-it`) are unchanged.
- When a question could mean more than one item (two water bottles), the FaceTime agent asks one short question by how they look ("The blue one or the green one?"), using `looks_like` from the snapshot, then answers. Only when it really could be either.
- When the caller describes a thing instead of naming it ("the silver one I wear on my wrist"), the FaceTime agent calls `find_by_description` (15 Nov). One clear fit: it says which thing it understood, then that thing's sentence. Several equal fits: "Do you mean your green bag or your brown bag?" (`moments.which_one`). No fit: the `unknown_item` sentence. It never guesses between a fit and a near miss.
- On FaceTime a photo of the thing where it was last seen may appear with the answer. The agent may say "have a look at the picture", but never describes the photo: it cannot see it.
- One question at a time. Speak slowly and warmly. Repeat the answer gladly when asked.
- After answering (D15), offer to stay on the line while they look, but not after every answer (asking every time sounded robotic on the test call). If yes, wait, then ask whether they found it and report the answer with the outcome tool if it exists.
- If the caller sounds distressed or asks for a person, be calm and reassuring. Do not promise to let anyone know until the family call exists.
- Never say "HIPAA compliant".

## Safety (report_concern, 15 Nov)

The FaceTime agent asks once, reports, and the family decides (docs/INSIGHTS.md design 3).
It never calls 911 and never says it told anyone: nothing can reach family yet.
The code (`agent/concern.mjs`) must use these sentences exactly; a test checks they are here.

- Fall, hurt, help or lost outside: ask "Are you hurt?" once, then report with their answer.
  - Hurt, no answer, or not asked: "I'm here with you. If you're hurt, call 911 or ask someone nearby."
  - Fine after a fall: "I'm glad you're okay. Take your time getting up."
  - Fine otherwise: "I'm glad you're okay. I'm right here with you."
- Smoke or something burning (report at once, no question): "Please move away from the smoke. Call 911 if you see fire."
- Someone wants money (gift cards, a wire, bank details, a grandchild in jail, "don't tell anyone"), reported at once: "That sounds like a trick some people try. Please don't send any money, and it's fine to hang up."
- Not safety, never reported: "my glasses fell", "the bag fell off the chair", "help me find my keys", "I lost my keys".
- "I'm fine" is still reported (as `ok`): people with dementia sometimes deny a real fall.
