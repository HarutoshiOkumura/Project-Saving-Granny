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

- Model from settings (`PERCEPTION_MODEL`), default `gemini-3.6-flash` (D24). The step 04 bake-off kept it (D3): `gemini-3.5-flash-lite` is the fallback if latency or rate limits bite; `gemini-4-hydrogen` and `gemini-3.8-flash` (no answer on our key) are not used.
- Use the Interactions API from `google-genai`: `client.aio.interactions.create(model=..., input=[...], response_format=..., generation_config=..., store=False, timeout=...)`, and read `output_text`. `generateContent` is legacy; do not use it. Verify the request shape against the docs linked in `CLAUDE.md` before coding.
- Checked with a live text-only call on 14 Nov: `response_format={"type": "text", "mime_type": "application/json", "schema": ...}` returned `status` `completed` and JSON inside the enum. Step 04 confirmed it with images: text first, then `{"type": "image", "data": <base64>, "mime_type": "image/jpeg", "resolution": "high"}`.
- Always pass `store=False`. By default the API stores every interaction (1 day on the free tier, 55 days on paid). Real frames only from a billing-enabled project with AI Studio logging off (hard rule in `CLAUDE.md`).
- Input: the text prompt first, then the image (the image doc's order for a single image), as inline base64 JPEG with `mime_type` `image/jpeg`. Apply the photo's EXIF rotation first; phone-camera fixture photos carry it.
- Set `generation_config.thinking_level` explicitly. Use `low`: in step 04 `minimal` missed a keys close-up that `low` found. Thinking tokens are billed and count against the output limit.
- Image resolution: Gemini 3 spends 1,120 tokens per image by default (`high`). Keep it: `medium` (560) held the close-ups in step 04 but was not tried at a distance, where keys and glasses need the pixels.
- Leave sampling settings (temperature and the like) at their defaults.
- Timeout 10 s, enforced with `asyncio.timeout` around the call (step 04: median about 3 s, worst 7.2 s over 51 calls). At most 3 retries with backoff, then skip the frame. Process frames concurrently, never one after another.
- At most `VLM_IN_FLIGHT` (2) Gemini calls at once. A frame that finds them busy waits in a line one frame long per device; a newer frame replaces it, and the replaced one is dropped (`busy`). Plain dropping lost the second looks of two CP3 put-downs (step 06).
- Turn the SDK's own retries off: `genai.Client(api_key=..., http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1)))`. By default it retries 408, 409, 429 and 5xx up to 4 times inside one call; in step 04 that stacked with our retries into a 429 storm, and its `timeout` let one call run 94 s. Treat any `status` other than `completed` (for example `incomplete` or `failed`) as a skipped frame.
- Known weakness: vision language models tend to report an object that is not there when the prompt names it. The bake-off's empty frames measure this; the item cut and the drop rules contain it; beliefs stay out of the prompt (next bullet).
- Prompt: report only listed items that are clearly visible; `in_hand` means in the wearer's own hand; never describe people; when unsure, lower the confidence rather than guess.
- Leave the context's `beliefs` out of the prompt (D3). Step 04 found no harm on 5 empty frames, but its one gain could not be told apart from suggestion, and a false confirmation would block "not there anymore".

## Drop rules (worker, in this order)

1. Room is a no-capture room: drop the frame. No crop, no observation, no rows, no `mark_absent`.
2. Room is `"unknown"` or `room_confidence` is below the room cut: write nothing for this frame (fail closed; it could be a no-capture room).
3. Item with landmark `"none"` and `in_hand` false: drop the item. A hackathon hall is full of other people's phones and glasses.
4. Item confidence below the item cut: drop the item.
5. The same item twice in one frame: keep the most confident entry.

## Frame filters

- Blur: variance of the Laplacian below the blur cut: drop the frame. Measured at 640 px; it mostly measures texture, so keep the cut low (a sharp frame of glasses on a plain table scores 60).
- Duplicate: SSIM at or above the duplicate cut against the last accepted frame: drop it, except when the last accepted frame left a tentative sighting open. Keep that frame, because it is the second look the two-frame rule needs. The worker approximates "left a tentative sighting open" as "logged a sighting".
- Also keep a duplicate once the last accepted frame is `DUPLICATE_REFRESH_S` (10 s) old, so a camera left looking at an empty landmark still feeds `mark_absent`.

## Absence

- Call `mark_absent` only for landmarks in `landmarks_in_view`, passing every item placed on that landmark in this frame as visible.
- Absence needs looks spread in time. After step 01 the database ignores looks closer together than its minimum gap; do not work around that in the worker.

## Crops

- A padded box (15 percent on each side) around the item, clipped to the frame. Never the full frame, never a face.
- Upload only after the drop rules pass, to the private `crops` bucket at `crops/<home>/<item>/<utc timestamp>.jpg`.
- Each logged look also gets a moment photo beside its crop (`...Z.moment.jpg`, 15 Nov): the widest 16:9 window around the item, at most half of the frame's area (all of an upright frame's width), 960 px, with the item's place inside it kept in a JPEG comment. The worker only calls `moments.record_soon()`; the photo is made in a thread and uploaded in the background, one at a time per stay with the newest look winning, so no frame waits on it. It is not a tight crop: it can show a person standing beside the item (D21). `MOMENT_PHOTOS=false` turns it off.

## Detectors and Roboflow

- D3: SAM 3 gates Gemini. Every filtered frame goes to `POST /sam3/concept_segment` with the prompts "green handbag", "eyeglasses", "bunch of keys", "wristwatch", "dark blue bottle" (plain names box single keys; "reading glasses" misses). An item without a measured wording is prompted with its own name (`detector.prompts_for`). Any demo item at 0.5 or more opens the gate; otherwise no Gemini call, except one empty look at most every 30 s for `mark_absent`.
- Ignore SAM 3's label (it called a distant watch "bunch of keys"). Crop with the SAM 3 box that overlaps Gemini's `box_2d` most (IoU at least 0.5), else Gemini's box.
- Send `disable_model_monitoring: true` on every Roboflow call (D20).

- Gemini can also return boxes: `box_2d` as `[ymin, xmin, ymax, xmax]` normalized to 0..1000. The bake-off scores them as a detector candidate; scale them back to pixels before cropping.
- `detect(image) -> list[Detection]` in `app/perception/detector.py` is the only place that calls Roboflow.
- Inference only, on staged frames of our own objects. Never upload a frame from a real home or of a real person to a Roboflow project: the workspace is on the Research plan, so it is public.

## Thresholds

Defaults are guesses (D11). Tune them on the fixture frames and record the tuned values in `docs/STATUS.md` and D11.
They are settings (`ROOM_CUT`, `ITEM_CUT`, `SAM3_GATE`, ...); step 05 measured them live and kept every default (D11 has the margins).

| Setting | Default |
|---|---|
| Blur cut (variance of Laplacian) | 25 |
| Duplicate cut (SSIM) | 0.95 |
| Room cut (`room_confidence`) | 0.6 |
| Item cut (item `confidence`) | 0.5 |
| Roboflow Instant confidence | 0.85 to 0.99 |
| SAM 3 gate confidence | 0.5 (step 04: opened 12/12 item frames, 1/5 empty; step 05: item frames 0.57 and up, empty up to 0.55, so do not raise it) |
| RF-DETR confidence | tune on fixtures, if one is trained |
| Frame interval | 0.5 s (D10, step 06: 2 s confirmed 0 of 4 CP3 put-downs) |
| Duplicate refresh | 10 s |
| Empty look | at most every 30 s |
| Gemini calls in flight | 2, plus a line one frame long per device |

## Disclosure

Frames reach the model APIs before the room is known, so the no-capture rule stops storage, not transmission (D12).
The capture page's Pause button is the control for that.
