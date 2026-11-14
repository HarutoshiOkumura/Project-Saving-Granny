# Build plan

Hour figures are estimates for one person and have not been timed. Each step has a prompt in `.claude/commands/`; run it in Claude Code as `/step-NN-name`.

## How to use these files

1. Unzip the kit into the root of an empty git repo. `CLAUDE.md` and `.claude/` must sit at the root.
2. Copy `.env.example` to `.env` and fill in what you have.
3. Start Claude Code in that folder and run `/step-00-scaffold`. Each step is one command; run one per session and clear the conversation between steps, so each starts from `docs/STATUS.md` and not from stale context.
4. Read the diff before you commit. The steps tell Claude Code to stop and ask in several places; answer those rather than letting it guess.

## First hour, for the humans (in parallel with step 00)

- Create the Supabase project and collect the keys (`docs/SUPABASE.md` section 1).
- Get the Roboflow API key and confirm the workspace plan (`docs/ROBOFLOW.md` sections 0 and 1).
- Decide and stage the demo home, and name the rooms, landmarks and items (`docs/DECISIONS.md` D1, D2).
- Shoot the 25 to 30 bake-off frames (`docs/ROBOFLOW.md` section 2).
- Ask Chert staff what the line supports (D4) and the Coder table what counts (D6).
- Create the Vapi account and claim the free inbound number.
- Decide where the backend runs and get its public HTTPS address (D5).

## The ordering rule

Build the read path first, on seeded data, then the write path.

- The call is the product. With six hand-typed rows you can already phone the number and hear a correct answer, which is a demo.
- The write path (camera, detector, language model) is where the risk is. It can fail softly: replay a recorded video, or let a family member type "I put them in the drawer". The read path cannot fail on stage.
- The schema is already written and tested, so both paths can be built in parallel against it from the first hour.

## Steps in order

| # | Step | Depends on | Est. hours | Output you can show |
|---|---|---|---|---|
| 00 | Scaffold repo, environment, Coder workspace | nothing | 0.5 | `uv run pytest` passes on an empty app |
| 01 | Supabase: schema, seed home, smoke test | 00 | 0.75 | `find_item` answers in the SQL editor |
| 02 | Find API and `speak()` | 01 | 1 | `curl /find?item=glasses` returns one sentence |
| 03 | Phone voice (Vapi) | 02 | 1.5 | Call the number, hear the answer |
| 04 | Detector bake-off, start training if needed | Roboflow key, staged frames | 1 + training in background | A table of hits and misses per model |
| 05 | Perception module | 01, 04 | 2 | Fixture frames produce correct JSON |
| 06 | Ingest worker, run on a replayed video | 05 | 2 | A recorded walk fills the timeline |
| 07 | Capture page on the phone | 06 | 1.5 to 2 | Live frames from the lanyard phone |
| 08 | Family dashboard | 02 | 1.5 | Timeline with crops; "tell Save It" form |
| 09 | Typesense name matching | 02 | 1.5 to 2 | "specs" and "spectecles" both resolve |
| 10 | FaceTime line (Chert + LiveKit) | 02, line confirmed | 4 to 6 | FaceTime call answers and shows the photo |
| 11 | Harden, rehearse, record | all of the above that exist | 2 to 3 | Video and Devpost entry |

## Who does what

Three tracks can start in the first hour, because they only share the schema.

- **Track A, memory and voice:** 00, 01, 02, 03, then 10.
- **Track B, perception:** 04 (start at once; it needs only a Roboflow key and staged frames), 05, 06.
- **Track C, capture and show:** stage the demo home and take enrolment photos, then 07 and 08, then own 11.
- **Fourth person, if there is one:** Coder deployment and template, confirm the Chert line, then 09.

## Checkpoints

| Checkpoint | Passes when | If it fails |
|---|---|---|
| CP1 after step 03 | A real phone call returns the seeded place | Use a Vapi web call in the browser; keep going |
| CP2 after step 04 | One detector finds each demo item in at least 8 of 10 close-up frames, with at most 1 false alarm on the empty frames | Train the Roboflow model on the demo items; meanwhile build step 05 on the language model alone |
| CP3 after step 06 | A replayed walk with three put-downs gives three correct `find_item` answers | Narrow the demo to two items and deliberate close-up put-downs; keep the "told" form as a backstop |
| CP4 after step 07 | The same result live from the lanyard phone | Film the demo from the replay path; say so in the video |
| Freeze | 3 hours before submission | Stop adding features; step 11 only |

## Cut order when time runs short

Cut from the top. Never cut below the line.

1. 3D scan view and AR arrow
2. Coder egress allowlist for the worker (keep building in Coder; that alone earns the credit)
3. Step 09, Typesense
4. Live pointing on FaceTime (keep the last-seen photo)
5. Step 10, FaceTime entirely
6. Embedding lookups (`match_room`, `match_item`); the language model names the room and each category has one enrolled item

---- do not cut ----

7. Steps 00 to 03 and 05 to 06, the dashboard's timeline, and the recorded video

## Definition of demo-ready

1. Someone puts glasses on the kitchen counter in view of the lanyard phone and walks to another room.
2. Within 10 seconds the dashboard shows the sighting with a crop.
3. They call the number and ask "where are my glasses?". The answer names the kitchen counter and a relative time.
4. Someone moves the glasses off camera; the camera sees the empty counter three times; the next call says they are no longer there and offers the usual place.
5. The camera enters the no-capture room and nothing is stored.
6. All of this is also recorded as a fallback take.
7. It all runs on the D5 setup, and every ⚠ UNVERIFIED check in `docs/DECISIONS.md` D5 has passed or has its fallback in place.

## What to say you did not build

State these in the Devpost entry and the Q&A; judges reward it.

- The detector is trained on, or tuned for, our own demo objects. It will not recognise another person's keys without enrolment.
- Tested with staged scenes and team members, not with people who have dementia.
- Frames are sent to model APIs before the room is known, so the no-capture rule stops storage, not transmission.
