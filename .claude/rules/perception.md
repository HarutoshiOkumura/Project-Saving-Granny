---
paths:
  - "app/perception/**"
  - "app/worker/**"
  - "scripts/bakeoff.py"
  - "scripts/replay_video.py"
  - "tests/fixtures/**"
---

# Perception rules

These load when you work on perception, the ingest worker, the bake-off or the replay script.

## Output contract

`perceive(frame, context) -> Perception`, with the shape shown in `CLAUDE.md`.

- Build the JSON schema from `perception_context()` at call time.
- Rooms: every room name plus `"unknown"`.
- Landmarks: addresses such as `"kitchen > counter"` plus `"none"`, so a landmark also fixes its room and names never collide across rooms.
- Items: item names.
- Sort every enum and build the schema deterministically. Claude compiles each new schema once and caches it for 24 hours, so a schema that changes every frame pays that cost every frame. One schema per room context is fine; never put beliefs or timestamps in the schema.
- The API does not enforce numeric minimum and maximum, so clamp confidences to 0..1 in Pydantic.

## Claude call

- Model from settings, default `claude-haiku-5-5`. Step up to `claude-sonnet-5-5` only if the bake-off says so.
- JSON via `output_config.format` with `type: "json_schema"`. Verify the request shape against the structured outputs and vision docs linked in `CLAUDE.md` before coding.
- Set `output_config.effort` explicitly. Start at `low`; Haiku 5.5 defaults to `medium`. Try thinking disabled for latency if quality holds (allowed at effort `high` or below).
- Do not send `temperature`, `top_p` or `top_k`. Do not prefill.
- Timeout 8 s, at most 3 retries with backoff, then skip the frame. Treat `stop_reason` `refusal` or `max_tokens` as a skipped frame.
- Prompt: report only listed items that are clearly visible; `in_hand` means in the wearer's own hand; never describe people; when unsure, lower the confidence rather than guess.
- Whether the context's `beliefs` go into the prompt is decided by the step 04 bake-off, because showing them can make the model "confirm" them. Until then, leave them out.

## Drop rules (worker, in this order)

1. Room is a no-capture room: drop the frame. No crop, no observation, no rows, no `mark_absent`.
2. Room is `"unknown"` or `room_confidence` is below the room cut: write nothing for this frame (fail closed; it could be a no-capture room).
3. Item with landmark `"none"` and `in_hand` false: drop the item. A hackathon hall is full of other people's phones and glasses.
4. Item confidence below the item cut: drop the item.
5. The same item twice in one frame: keep the most confident entry.

## Frame filters

- Blur: variance of the Laplacian below the blur cut: drop the frame.
- Duplicate: SSIM at or above the duplicate cut against the last accepted frame: drop it, except when the last accepted frame left a tentative sighting open. Keep that frame, because it is the second look the two-frame rule needs.

## Absence

- Call `mark_absent` only for landmarks in `landmarks_in_view`, passing every item placed on that landmark in this frame as visible.
- Absence needs looks spread in time. After step 01 the database ignores looks closer together than its minimum gap; do not work around that in the worker.

## Crops

- A padded box (15 percent on each side) around the item, clipped to the frame. Never the full frame, never a face.
- Upload only after the drop rules pass, to the private `crops` bucket at `crops/<home>/<item>/<utc timestamp>.jpg`.

## Detectors and Roboflow

- `detect(image) -> list[Detection]` in `app/perception/detector.py` is the only place that calls Roboflow.
- Inference only, on staged frames of our own objects. Never upload a frame from a real home or of a real person to a Roboflow project: the workspace is on the Research plan, so it is public.

## Thresholds

Defaults are guesses (D11). Tune them on the fixture frames and record the tuned values in `docs/STATUS.md` and D11.

| Setting | Default |
|---|---|
| Blur cut (variance of Laplacian) | 25 |
| Duplicate cut (SSIM) | 0.95 |
| Room cut (`room_confidence`) | 0.6 |
| Item cut (item `confidence`) | 0.5 |
| YOLO-World confidence | start at 0.05 |
| Roboflow Instant confidence | 0.85 to 0.99 |
| RF-DETR, SAM 3 confidence | tune on fixtures |
| Frame interval | 2 s (D10) |

## Disclosure

Frames reach the model APIs before the room is known, so the no-capture rule stops storage, not transmission (D12).
The capture page's Pause button is the control for that.
