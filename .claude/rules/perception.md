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
- Sort every enum and build the schema deterministically, so one room context always gives the same schema. Never put beliefs or timestamps in the schema.
- Gemini's schema subset supports `enum`, `required`, `additionalProperties`, `minimum` and `maximum`, and ignores `minLength`, `maxLength` and `uniqueItems`. Clamp confidences to 0..1 in Pydantic anyway.

## Gemini call

- Model from settings (`PERCEPTION_MODEL`), default `gemini-3.6-flash` (D24). The step 04 bake-off also tries `gemini-3.5-flash-lite` (faster, weaker) and `gemini-4-hydrogen` (the step-up: best boxes in Roboflow's evals); keep whichever it says. `gemini-3.8-flash` did not answer on our key on 14 Nov; retry it once in step 04 and use it only if it answers.
- Use the Interactions API from `google-genai`: `client.aio.interactions.create(model=..., input=[...], response_format=..., generation_config=..., store=False, timeout=...)`, and read `output_text`. `generateContent` is legacy; do not use it. Verify the request shape against the docs linked in `CLAUDE.md` before coding.
- Checked with a live text-only call on 14 Nov: `response_format={"type": "text", "mime_type": "application/json", "schema": ...}` returned `status` `completed` and JSON inside the enum. Confirm the image part with one live call in step 04.
- Always pass `store=False`. By default the API stores every interaction (1 day on the free tier, 55 days on paid). Real frames only from a billing-enabled project with AI Studio logging off (hard rule in `CLAUDE.md`).
- Input: the text prompt first, then the image (the image doc's order for a single image), as inline base64 JPEG with `mime_type` `image/jpeg`. Apply the photo's EXIF rotation first; phone-camera fixture photos carry it.
- Set `generation_config.thinking_level` explicitly. Start at `low`: on/in/under judgments need some reasoning. The bake-off compares `minimal` (faster) against `low`; drop to `minimal` only if relations hold. Thinking tokens are billed and count against the output limit.
- Image resolution: Gemini 3 spends 1,120 tokens per image by default (`high`). Keep that for small items like keys and glasses; try `medium` (560) in the bake-off for latency.
- Leave sampling settings (temperature and the like) at their defaults.
- Timeout 15 s (a numeric `timeout` bounds the whole call), at most 3 retries with backoff, then skip the frame. Roboflow's evals timed Flash at about 7 s per image at low effort, so the worker must process frames concurrently, never one after another. Tighten the timeout to what step 04 measures. Treat any `status` other than `completed` (for example `incomplete` or `failed`) as a skipped frame.
- Known weakness: vision language models tend to report an object that is not there when the prompt names it. The bake-off's empty frames measure this; the item cut and the drop rules contain it; beliefs stay out of the prompt until the bake-off shows they are safe.
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

- Gemini can also return boxes: `box_2d` as `[ymin, xmin, ymax, xmax]` normalized to 0..1000. The bake-off scores them as a detector candidate; scale them back to pixels before cropping.
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
