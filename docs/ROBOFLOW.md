# Roboflow: exact steps

Facts here were read from Roboflow's docs on 14 Nov 2026. Nothing here has been run by us yet. Where it says "verify", open the linked page before coding; the docs index is https://docs.roboflow.com/llms.txt.

## 0. One rule first

The workspace is on the Research plan, and every image in a Research workspace becomes public on Roboflow Universe. Upload staged photos of our own objects only. Nothing from a real home, nobody's face.

## 1. Key

Workspace settings, API keys. Put the private key in `.env` as `ROBOFLOW_API_KEY`. Credits will not run out: 50 a month buys roughly 267,000 YOLO-World calls or 100,000 SAM 3 calls.

## 2. Bake-off before any training (about 1 hour)

1. Stage the demo home (`DECISIONS.md` D1, D2). Hold the phone where the lanyard will hang.
2. Shoot 25 to 30 frames into `tests/fixtures/frames/`:
   - 10 close-ups: the item 0.5 to 1 metre away as it is set down.
   - 10 medium: 1.5 to 3 metres.
   - 5 to 10 with clutter and no demo item.
3. Run `scripts/bakeoff.py` (built in step 04) over them with each candidate:
   - **YOLO-World**, zero-shot: `POST https://serverless.roboflow.com/yolo_world/infer` with `text` set to the class names and `yolo_world_version_id` such as `v2-l`. Start at confidence 0.05. Verify: https://docs.roboflow.com/models/supported-models/yolo-world.md
   - **SAM 3**, text prompts: `POST https://serverless.roboflow.com/sam3/concept_segment`, up to 16 prompts per request, about 250 ms. Verify: https://docs.roboflow.com/models/supported-models/sam3.md
   - **Gemini** (`gemini-3.6-flash`, `gemini-3.5-flash-lite` and `gemini-4-hydrogen`, D24) with the perception schema, no detector. Also score Gemini's own `box_2d` boxes as a detector.
4. Try two or three wordings per item ("keys", "bunch of keys", "reading glasses", "eyeglasses", "silver watch", "wristwatch", "water bottle", "dark blue bottle", "green handbag").
5. Fill the table the script prints: per model and item, hits out of 10 close-ups, hits out of 10 medium, false alarms on the empty frames.
6. Decide with CP2 in `PLAN.md`. Write the result into `DECISIONS.md` D3.

Expect zero-shot to do well on phone and remote and poorly on keys and glasses at a distance. If so, go to section 3 at once; training runs in the background.

## 3. Train on the demo items (about 2 hours of a person's time, mostly waiting)

Guide: https://docs.roboflow.com/guides/model-training.md

1. Film each item for 30 to 60 seconds in the staged home: on each landmark, in a hand, from 0.5 to 3 metres, several angles, lights on and off, with other clutter nearby.
2. In Roboflow, create a project of type Object Detection. One class per item category, named exactly as `items.category` in the seed file.
3. Upload the videos. Sample 1 to 2 frames per second, aiming for 250 to 400 images in total.
4. Auto-label by typing each class name; raise the confidence threshold until the boxes look right. Review every image; fix or delete bad boxes.
5. **Roboflow Instant** trains by itself once labelled images are added (under 1,000 images, a few minutes, free). Use a confidence threshold between 0.85 and 0.99. Verify: https://docs.roboflow.com/models/train/roboflow-instant.md
6. In parallel, generate a dataset version with a train, validation and test split, and train **RF-DETR** Small or Medium. Medium takes about 45 minutes.
7. Note the model id (`<project>/<version>`) and put it in `.env` as `ROBOFLOW_MODEL_ID`.
8. Re-run the bake-off with the trained model added. Keep whichever passes CP2.

Say in the write-up that the model is trained on our own demo objects.

## 4. Call it from Python

```python
from inference_sdk import InferenceHTTPClient

rf = InferenceHTTPClient(api_url="https://serverless.roboflow.com", api_key=ROBOFLOW_API_KEY)
# predictions: class, confidence, x, y, width, height
result = rf.infer("frame.jpg", model_id=ROBOFLOW_MODEL_ID)
```

Verify the client and response shape in the docs before relying on this; `x` and `y` are normally the box centre in pixels of the image you sent. All Roboflow calls live in `app/perception/detector.py` behind one function, `detect(image) -> list[Detection]`, so the detector can be swapped without touching anything else.

## 5. Embeddings, only if D7 or D8 call for them

- Roboflow hosts CLIP. ViT-L/14 returns 768 numbers, which is the width of every `vector(768)` column in the schema.
- Room index: 10 to 15 tour photos per room into `room_refs`; query with `match_room`.
- Item index: 3 to 5 crops per item (plain background and in place) into `item_refs`; query with `match_item`; accept above a similarity you tune on the fixtures, else log the sighting with no owner.
- Verify the endpoint and client method names in the docs index before coding. `scripts/enroll.py` does the uploads to Supabase, not to Roboflow.

## 6. Workflows

A Roboflow Workflow can chain detector, crop, a language-model block and a webhook. It is a good picture for the video, but it duplicates the Python chain. Build the Python chain. Recreate it as a Workflow only if time is left and you want the screenshot.

## 7. If the hosted API is slow or down

```bash
pip install inference-cli && inference server start     # local server on port 9001, CPU only in Docker on a Mac
```

Point `api_url` at `http://localhost:9001`. Use Python 3.12 for this.
