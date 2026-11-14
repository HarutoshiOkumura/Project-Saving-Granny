---
description: Step 06 - ingest worker, POST /frames, replay script, CP3
---

# Step 06: Ingest worker

Read `docs/STATUS.md`, `.claude/rules/perception.md`, `.claude/rules/memory-db.md`, and `docs/DECISIONS.md` D10, D11 and D12.
Depends on: 05.
Time box: 2 hours.

## Build

1. `app/perception/filters.py`: blur (variance of the Laplacian) and duplicate (SSIM against the last accepted frame), with the tentative-pending exception from the perception rules.
2. `app/worker/ingest.py`: `ingest(frame, device_id, captured_at) -> IngestResult`, in this order:
   filters, then `perception_context` (cached per room for 30 s), then `perceive`, then the drop rules, then insert the observation (skip the frame if its idempotency key exists), then for each kept item upload the crop and call `log_sighting`, then for each landmark in view call `mark_absent` with the items seen on it.
   A no-capture room returns at once: no crop, no observation, no rows.
3. `app/memory/db.py` gains the RPC wrappers and the crop upload (private `crops` bucket, path `crops/<home>/<item>/<utc timestamp>.jpg`).
4. `POST /frames` (multipart JPEG, `device_id`, `captured_at`), thin and protected by `APP_TOKEN`. It replies at once and processes in a background task, so the phone never waits on the models.
5. `scripts/replay_video.py <video> [--fps 1]`: samples frames, rebases timestamps so the last frame is now, and POSTs them to `/frames`.
6. One log line per frame: id, filter result, room, items kept and dropped with reasons, milliseconds per stage.

## Tests

`tests/test_ingest.py` with fixture frames and faked perception and database: every drop rule, a no-capture room writes nothing, a retried frame writes once, and `mark_absent` gets the right visible ids.

## Checks

- pytest and ruff are clean.
- CP3: record a staged walk with three put-downs, replay it, and `find_item` answers all three correctly. Paste the three answers into STATUS.
- If CP3 fails, follow `docs/PLAN.md` (two items, deliberate close-up put-downs, the "told" form as a backstop).
