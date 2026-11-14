---
description: Step 07 - phone capture page on the lanyard, CP4
---

# Step 07: Capture page

Read `docs/STATUS.md`, `.claude/rules/perception.md`, and `docs/DECISIONS.md` D5, D10 and D12.
Depends on: 06, and HTTPS at `PUBLIC_BASE_URL`.
Time box: 1.5 to 2 hours.

## Build

1. Generate `APP_TOKEN` (`python -c "import secrets; print(secrets.token_urlsafe(24))"`) into `.env` if it is empty, and tell the humans.
2. `app/web/capture.html`, static with no build step, served by FastAPI:
   - Asks for the token once and keeps it in `localStorage`.
   - Opens the rear camera with `getUserMedia` and sends a JPEG (longest side about 1024 px, quality about 0.7) every 2 s (D10) to `/frames`, with `device_id` and `captured_at` in UTC.
   - Keeps the screen awake with the Screen Wake Lock API, re-acquires it when the page becomes visible again, and shows a clear warning if the lock is lost or the camera stops.
   - A large Pause button (D12) that stops capture and sending, with an obvious paused state.
   - Shows the last send status and round-trip time. Never shows or stores a Supabase key.
   - Works on iPhone Safari and Android Chrome.

## Checks

- On the lanyard phone, walk the staged home: frames arrive (server log), and a put-down shows up in `find_item` within 10 seconds.
- Record the CP4 result in STATUS. If it fails, film the demo from the replay path and say so (`docs/PLAN.md` CP4).

## Humans

On the lanyard phone: auto-lock off, low-power mode off, brightness low, charger nearby.
