---
description: Step 05 - perception module (schema, Claude call, detector, crops)
---

# Step 05: Perception module

Read `docs/STATUS.md`, `.claude/rules/perception.md`, and `docs/DECISIONS.md` D3, D7, D8, D9, D11 and D21.
Read the Claude structured outputs and vision docs linked in `CLAUDE.md` before writing the Claude call.
Depends on: 01, 04.
Time box: 2 hours.

## Build

1. `app/perception/schema.py`: Pydantic models `Perception`, `ItemSeen` and `Detection`, and `build_json_schema(context) -> dict` with enums as the perception rules describe (sorted, deterministic, landmark values as addresses).
2. `app/perception/vlm.py`: one function that sends one JPEG and the context to Claude and returns `Perception | None`, with the settings, timeout, retries and fallback from the rules.
3. `app/perception/detector.py`: `detect(image) -> list[Detection]` for the model D3 chose, behind that one function.
4. `perceive(frame, context) -> Perception` combining them: Claude places items; the detector supplies boxes for crops, and vetoes items only if the bake-off showed that helps.
5. `crop(frame, box) -> bytes`: the padded crop from the rules.
6. Thresholds come from settings, with the defaults in the perception rules.

## Tests

- Fixture frames with faked Claude and detector responses: schema building, enum contents, parsing, every drop rule that lives in perception, crop padding and bounds.
- One opt-in test marked `live` that calls the real APIs on 3 frames, skipped unless `RUN_LIVE=1`.

## Checks

- pytest and ruff are clean.
- Run the live test once on the whole fixture set: the share of frames where room, landmark and item are all correct. Record it and the tuned thresholds in STATUS and D11.
