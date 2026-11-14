---
description: Step 11 - harden, rehearse, record the video, draft the Devpost entry
---

# Step 11: Harden, rehearse, record

Read `docs/STATUS.md`, `docs/PLAN.md` (checkpoints, cut order, definition of demo-ready, what to say you did not build), and `docs/DECISIONS.md` D22.
Freeze is 05:00 Sunday 15 Nov, 3 hours before submission. After the freeze, only fixes and recording.

## Do

1. Walk the demo-ready list in `docs/PLAN.md` three times in a row, fixing whatever breaks. Reset between runs (`docs/SUPABASE.md` section 8).
2. Failure drills: stop the worker mid-demo, drop the tunnel, fake a Claude API timeout, slow Supabase down. The phone answer must still be one calm sentence every time.
3. Compute the D22 metric on the fixture set, and put the number in STATUS and in the write-up.
4. Record the fallback take (demo-ready item 6) and the 2-minute video: the problem, the call, how it works (one diagram), privacy (the no-capture room, crops only, "built with HIPAA-style safeguards"), and what we did not build.
5. Draft the Devpost entry in `docs/DEVPOST.md`: what it does, how we built it (each sponsor tool and what it does for us), challenges, what we did not build, and the D22 number.

## Checks

- Three clean runs in a row.
- The video is exported, and a human has reviewed the Devpost draft.
- No secrets in git history: `git log -p | grep -E 'sb_secret_|sk-ant-'` finds nothing.
- Nothing anywhere says "HIPAA compliant".
