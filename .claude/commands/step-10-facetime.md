---
description: Step 10 (optional) - FaceTime line via Chert and a LiveKit agent
---

# Step 10: FaceTime line (Chert + LiveKit, optional)

Read `docs/STATUS.md`, `.claude/rules/voice.md`, and `docs/DECISIONS.md` D4, D19 and D23.
Depends on: 02, and D4 answered by Chert staff.
Time box: 4 to 6 hours. This is fifth in the cut order (`docs/PLAN.md`).
If D4 is still OPEN, stop and ask the humans.

Before writing code, read https://docs.trychert.com/llms.txt and the LiveKit Agents docs (https://docs.livekit.io/agents/), and record in STATUS what the line supports.

## Build

1. `agent/`: a Python LiveKit agent (D19) with its own `pyproject.toml`, using the speech stack Chert's starter ships (D23).
2. One tool, `where_is(item)`, that calls the backend's `GET /find?item=...&photo=1` over HTTPS. The agent never holds the Supabase key; `app/memory/db.py` stays the only Supabase module. Add the `photo=1` option to `/find`: it returns a signed `photo_url` for the crop.
3. If D4 says agent video works, show the last-seen crop as a still image while answering. No live pointing (out of scope).
4. Voice behaviour from the voice rules.

## Checks

- A FaceTime call to the line answers "where are my glasses?" correctly; with video, the crop shows.
- Record a take for the video.
