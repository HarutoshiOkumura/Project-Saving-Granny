# Find It - Emory Hacks 2026 

A person living with dementia FaceTimes Find It and asks "Where are my glasses?".
A phone worn on a lanyard sees where things are put down, a database remembers each place, and the agent answers out loud with the place and a photo.
The family gets a dashboard: where everything is, alerts, and how the days are going.

[![Watch the demo](https://img.youtube.com/vi/dDo-NCyA80o/maxresdefault.jpg)](https://www.youtube.com/watch?v=dDo-NCyA80o)

Built at Emory Hacks 2026.

## What you need

- Python 3.12 with [uv](https://docs.astral.sh/uv/), and Node 22.12 or newer.
- A Supabase project with `supabase/migrations/0001`, `0002` and `0005` applied and the home seeded (`docs/SUPABASE.md`).
- Keys for Google Gemini and Roboflow, and a Chert FaceTime line with LiveKit for the call agent (`docs/CHERT.md`).

## Run the demo

1. Install and configure the backend:

   ```bash
   uv python install 3.12 && uv sync
   cp .env.example .env    # fill in the Supabase, Google and Roboflow keys, HOME_ID and APP_TOKEN
   ```

2. Start the backend:

   ```bash
   uv run uvicorn app.main:app --port 3000
   ```

3. Open the family dashboard at http://localhost:3000/dashboard and type the `APP_TOKEN` from `.env` once.

4. Feed it a camera walk. Replay a recorded video (needs ffmpeg), and the dashboard fills in as things are put down:

   ```bash
   uv run python -m scripts.replay_video path/to/walk.mov --interval 0.5
   ```

5. Start the FaceTime agent in a second terminal, then FaceTime the Chert line:

   ```bash
   cd agent
   cp .env.example .env.local    # LiveKit and Google keys, BACKEND_URL, and the same APP_TOKEN
   npm install && npm start
   npx @trychert/facetime@0.1.0-beta.20 dev --agent save-it    # third terminal
   ```

   To test without FaceTime, run `npm run web-call` in `agent/` instead.

Optional: Typesense adds typo-tolerant names and search by description (`docker start saveit-typesense`, then `uv run python -m scripts.sync_typesense`).

## Use it

On a FaceTime call, the person can:

- ask "Where are my glasses?" or "Where did I put my keys?",
- describe the thing instead of naming it ("the green one with the gold letters"; needs Typesense),
- say "It's not there" to hear where it usually lives,
- ask to be guided there step by step,
- say "I fell" or "Someone wants gift cards": Find It asks "Are you hurt?" once, raises an alert for the family and never calls 911 itself.

On the dashboard, the family can:

- **Now**: see where each thing is, with its last photo and the places to look; answer alerts with "I'm on my way", "I'm calling 911" or "All OK".
- **History**: see what the camera saw and when.
- **Patterns**: see how the days compare with the person's own usual (everyday observations, not a medical test), and note visits or new medicines.
- **Setup**: add things, rooms and places to put them down, and tell Find It where something is. The camera picks up new things within 30 seconds.

## Privacy

Built with HIPAA-style safeguards.
Only small crops of things are kept, in a private bucket with links that expire after an hour.
Nothing is ever saved from rooms marked private, such as the bathroom.

## Develop

```bash
uv run pytest -q && uv run ruff check .    # backend tests and lint
cd agent && npm test                       # agent tests
```

Start with `docs/STATUS.md` (what is done and what is next) and `CLAUDE.md` (architecture and rules).
The research behind the medical and safety features is in `docs/research/`.
