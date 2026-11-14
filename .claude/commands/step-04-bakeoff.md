---
description: Step 04 - detector bake-off on staged frames, decide D3
---

# Step 04: Detector bake-off

Read `docs/STATUS.md`, all of `docs/ROBOFLOW.md`, `.claude/rules/perception.md`, and `docs/DECISIONS.md` D3 and D20.
Depends on: `ROBOFLOW_API_KEY` and `ANTHROPIC_API_KEY` in `.env`, and staged frames in `tests/fixtures/frames/`.
Time box: 1 hour, plus training in the background.

## Frames

Staged scenes of our own objects only. If the folder is empty, ask the humans for frames (`docs/ROBOFLOW.md` section 2).
File names carry the ground truth; ask the humans to use this pattern:

- `close_<item>_<landmark>_<nn>.jpg` and `medium_<item>_<landmark>_<nn>.jpg`
- `empty_<room>_<nn>.jpg` for frames with no demo item

## Build

`scripts/bakeoff.py`:

- Candidates: YOLO-World (`v2-l`, confidence from 0.05), SAM 3 text prompts, and Claude Haiku with the perception schema and no detector.
- Read each Roboflow page linked in `docs/ROBOFLOW.md` section 2 and the Claude structured outputs and vision pages before writing the calls.
- Two or three wordings per item (`docs/ROBOFLOW.md` section 2, item 4).
- For Claude, run each frame with and without `beliefs` in the prompt, to see whether beliefs cause false sightings.
- Print a Markdown table per model and wording: hits out of the close-ups, hits out of the medium frames, false alarms on empty frames, median latency.
- Cache responses under `.cache/bakeoff/` (gitignored) so re-runs cost nothing.
- Inference only. Never upload frames to a Roboflow project from this script.

## Checks

- The table is pasted into STATUS.
- The CP2 decision (pass rule in `docs/PLAN.md`) is written into `docs/DECISIONS.md` D3, including the beliefs result.
- If zero-shot fails CP2 on keys or glasses, tell the humans to start training now (`docs/ROBOFLOW.md` section 3), and re-run with the trained model when it is ready.
