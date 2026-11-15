---
description: Step 04 - detector bake-off on staged frames, decide D3
---

# Step 04: Detector bake-off

Read `docs/STATUS.md`, all of `docs/ROBOFLOW.md`, `.claude/rules/perception.md`, and `docs/DECISIONS.md` D3 and D20.
Depends on: `ROBOFLOW_API_KEY` and `GOOGLE_API_KEY` in `.env`, and staged frames in `tests/fixtures/frames/`.
Time box: 1 hour, plus training in the background.

## Frames

Staged scenes of our own objects only. If the folder is empty, ask the humans for frames (`docs/ROBOFLOW.md` section 2).
File names carry the ground truth; ask the humans to use this pattern:

- `close_<item>_<landmark>_<nn>.jpg` and `medium_<item>_<landmark>_<nn>.jpg`
- `empty_<landmark>_<nn>.jpg` for a landmark with no demo item on it (scores whether the model lists it in view, which absence needs), `empty_<room>_<nn>.jpg` for a wide shot with no demo item
- `tests/fixtures/frames/boxes.json` holds a hand-drawn box per item frame, `[ymin, xmin, ymax, xmax]` on 0..1000 of the upright image; add one for every new item frame
- Inside a name, hyphens stand for spaces and underscores: `close_water-bottle_table_01.jpg`, `empty_b-school-classroom_01.jpg`. Map them back to the seeded names when scoring.

## Build

`scripts/bakeoff.py`:

- Candidates: YOLO-World (`v2-l`, confidence from 0.05), SAM 3 text prompts, and Gemini (`gemini-3.6-flash`, `gemini-3.5-flash-lite` and `gemini-4-hydrogen`, D24) with the perception schema and no detector. Also score Gemini's own `box_2d` boxes as a detector.
- Read each Roboflow page linked in `docs/ROBOFLOW.md` section 2, and the Gemini pages linked in `CLAUDE.md` (structured output, image understanding, interactions, thinking, media resolution), before writing the calls. Pass `store=False` on every Gemini call.
- For Gemini, also compare `thinking_level` `minimal` against `low`, and image resolution `high` against `medium`, on the close-ups; report the median and worst latency for each. A put-down must reach `find_item` within 10 s (two frames 2 s apart), so a model slower than about 7 s per frame needs a reason to be chosen.
- Two or three wordings per item (`docs/ROBOFLOW.md` section 2, item 4).
- For Gemini, run each frame with and without `beliefs` in the prompt, to see whether beliefs cause false sightings.
- Print a Markdown table per model and wording: hits out of the close-ups, hits out of the medium frames, false alarms on empty frames, median latency.
- Cache responses under `.cache/bakeoff/` (gitignored) so re-runs cost nothing.
- Inference only. Never upload frames to a Roboflow project from this script.

## Checks

- The table is pasted into STATUS.
- The CP2 decision (pass rule in `docs/PLAN.md`) is written into `docs/DECISIONS.md` D3, including the beliefs result.
- If zero-shot fails CP2 on keys or glasses, tell the humans to start training now (`docs/ROBOFLOW.md` section 3), and re-run with the trained model when it is ready.
