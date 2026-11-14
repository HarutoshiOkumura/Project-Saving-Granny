# Decisions to settle

Each item has a default so nobody is blocked. Change a default by editing this file and telling Claude Code; it reads this file when a step depends on one.

Status key: OPEN (using default), DECIDED (write the choice and who chose).

## Settle in the first hour

**D1. Where is the "home" for the demo?** OPEN
A hackathon hall has no rooms, and every corner looks alike. Options: (a) film in a teammate's apartment or dorm and judge from the video plus a live call; (b) stage two or three tables as "rooms" with very different props (a lamp and a pillow; a kettle and a toaster; coat hooks). Default: both. Film the real walk for the video; stage two tables for live judging. The names in `supabase/seed.sql` (seeded on Supabase in step 01) must match whatever you stage.

**D2. Which items and landmarks, exactly?** DECIDED (the team, 14 Nov, step 01)
Rooms: bedroom, kitchen, hallway, bathroom (no capture). Landmarks: bedroom nightstand, dresser, desk; kitchen counter, table; hallway key hook, shoe shelf. Items: glasses, keys, and `bag` (the FRANZI Milano green bag; aliases "green bag", "handbag", "purse"). The bag has no usual place yet. Seeded from `supabase/seed.sql`. Fewer, more distinct items beat a long list. Every name here becomes an allowed answer for the vision model.

**D3. Which detector?** OPEN, decided by the step 04 bake-off
Candidates: YOLO-World zero-shot, SAM 3 text prompts, a Roboflow Instant or RF-DETR model trained on the demo items, or the language model alone. Pass rule is CP2 in `PLAN.md`. Default if nobody runs the bake-off: language model alone for placement, trained Roboflow model for boxes and crops.

**D4. Does the Chert line carry caller camera and agent video?** OPEN, ask Chert staff
This decides whether step 10 shows a photo or is audio only. Also confirm the per-call time cap and that one line means one call at a time.

**D5. Where does the backend run, and what is its public HTTPS address?** DECIDED (the team, 14 Nov: MacBook Pro and iPhone 17; the rest is Claude Code's plan, not yet tried)
Vapi needs a public HTTPS URL for the tool.
The phone needs HTTPS to open the camera.

- **Machine:** the team's MacBook Pro runs the backend during the demo, inside a Coder workspace (D6).
- **Phone:** the lanyard phone is an iPhone 17, using Safari.
- **Public address:** a Cloudflare Quick Tunnel started inside the workspace.
  `cloudflared tunnel --url http://localhost:8000` prints a `https://<random>.trycloudflare.com` address; put it in `PUBLIC_BASE_URL`.
- **Why this shape:** Coder is not in the path a call takes, so a Coder hiccup cannot drop a call once the workspace is running.
  Coder's docs do not say whether its own built-in tunnel can serve a public port reliably, so it is not used for that.
- **From the docs (checked 14 Nov):** a Quick Tunnel's hostname changes on every run and stops working when the process stops.
  It allows 200 in-flight requests, has no Server-Sent Events and no uptime guarantee.
  Web traffic to a workspace port does not count as Coder activity; an open editor, terminal or SSH session does.

Before every test run and the demo:

1. Plug in the Mac and run `caffeinate -dims` in a terminal for the whole session.
2. Turn autostop off for the workspace (template "Default autostop" off, or `coder schedule stop <workspace> manual`), then restart the workspace, because schedule changes apply on the next build.
3. Start `cloudflared` once and leave it running; restart only the API if needed.
   Every new tunnel address must go into three places: `.env`, the Vapi tool's server URL, and the capture page bookmark on the iPhone.
4. One person owns the Mac during judging: (name).

> **⚠ UNVERIFIED: none of the checks below has been tried yet.**
> Run all of them in the first end-to-end test (step 03's CP1 at the latest) and write each result in `docs/STATUS.md`.
> If a check fails, switch to its fallback, then run the check again.

| # | Assumption | How you notice it failed | Fallback |
|---|---|---|---|
| A1 | The venue network lets `cloudflared` connect out. | `cloudflared` prints connection errors and no `trycloudflare.com` address, or `curl <address>/health` from a phone on cellular does not return `{"ok":true}`. | Put the Mac on a teammate's phone hotspot (not the lanyard iPhone) and restart `cloudflared` (then step 3 above). |
| A2 | Coder runs a Docker workspace on the Mac, and the API starts in it. | The workspace shows Failed or Stopped in the Coder dashboard, or `curl localhost:8000/health` inside the workspace fails. | Run the API on the Mac itself (`uv run uvicorn app.main:app --port 8000`) with `cloudflared` on the Mac. Everything still works, but drop the Coder sentence from the pitch (D6). |
| A3 | Autostop is off, so the workspace keeps running with nobody's editor open. | The workspace page in the Coder dashboard shows a stop time. | Keep a `coder ssh <workspace>` session open in a Mac terminal during judging; an open session counts as activity. |
| A4 | The address in Vapi matches the running tunnel. | A call gets silence or the fallback sentence, and the Vapi call log shows a failed tool request. | Copy the current `trycloudflare.com` address into the Vapi tool's server URL and `.env`, and reopen the capture page on the iPhone. |
| A5 | Answers stay fast through the tunnel. | `curl -s -o /dev/null -w '%{time_total}\n' <address>/health` from a phone on cellular or another network takes more than 1 s. | Try the hotspot (A1). If it is still slow, note it in STATUS for step 11. |
| A6 | Safari on the iPhone 17 opens the camera on the tunnel address. | The capture page shows a camera error, or the permission prompt never appears. | Settings > Apps > Safari > Camera: Allow, and open the page in Safari itself, not inside another app. For the video, use the replay path (CP4 in `PLAN.md`). |

**D6. What counts as using Coder?** DECIDED (the team, 14 Nov)
Everything that touches camera frames runs inside a Coder workspace.
In practice that is the whole backend, because `POST /frames` lives in the same app as the voice tools (D5).
We run our own open-source Coder server on the demo MacBook with a Docker template, so we are the admins and no license limits apply.
Take a screenshot of the running workspace for Devpost.

How to say it (pitch, video, Devpost):

- Say "built with HIPAA-style safeguards": frames are handled only inside an isolated Coder workspace, full frames are never stored, only a tight crop of each item is kept in a private bucket with expiring links, and no-capture rooms store nothing.
- Frames are still sent to Anthropic (Claude) and Roboflow for analysis.
  Coder isolates our code, not theirs, so never claim the frames stay in the container.
- Never say "HIPAA compliant" or "protected under HIPAA".
  HIPAA covers healthcare providers, insurers and their contractors, and running in a container does not make us one.
- The egress allowlist is item 2 on the cut list in `PLAN.md`.
  If it gets built, add "the workspace can only reach our database and the two model providers", and remember it must also let `cloudflared` out (D5).
  If it is cut, leave that sentence out.

> **⚠ UNVERIFIED: whether the Coder table counts a self-hosted Coder server.**
> Ask them. If only their hosted deployment counts, update D5 and this entry before step 03.

## Settle before step 05

**D7. Room recognition.** OPEN
Default: the language model picks the room from the list. Add the embedding vote (`match_room`) only if it confuses rooms on the fixture frames.

**D8. Whose item is it?** OPEN
Default: one enrolled item per category, so a detected "glasses" is the glasses. Add `match_item` only if the demo needs two look-alike items.

**D9. Embedding model and width.** OPEN
The schema uses `vector(768)`, which fits Roboflow-hosted CLIP ViT-L/14. If you choose another encoder, change the width in the migration before loading it. One encoder for every embedding.

**D10. What triggers a frame?** OPEN
Default: every 2 seconds, then the blur and duplicate filters. A hand-in-view gate is a later refinement.

**D11. Thresholds.** OPEN
Defaults: blur below 25; duplicate at SSIM 0.95 or more; detector confidence per model as in `.claude/rules/perception.md`; stay-merge window 10 minutes; 3 empty looks to conclude absence; spoken confidence cut at 0.5. All are guesses. Tune on the fixture frames in step 05 and write the tuned values here.

**D12. No-capture rooms.** OPEN
The database refuses to store anything for them, but the frame has already been sent to a model API by the time the room is known. Options: (a) accept and disclose; (b) a Pause button on the capture page; (c) run a local room classifier first and drop the frame before any network call. Default: (a) plus (b).

## Settle before step 03

**D13. How does a caller map to a home?** OPEN
Default: one home, `HOME_ID` in the environment. Caller-number lookup is out of scope.

**D14. Voice and wording.** OPEN
Pick the Vapi voice and speaking rate. Have someone outside the team listen to three answers. The rules are in `.claude/rules/voice.md`; change them there, not in code.

**D15. What happens after the answer?** OPEN
Default: the agent asks "Would you like me to stay on the line while you look?", then "Did you find them?", and reports the outcome. A "no" retires that answer.

## Settle when you reach them

**D16. Dashboard data access.** Default: the page polls the backend every 2 seconds. No Supabase key in the browser.

**D17. Photo retention.** Default: crops only, private bucket, signed for 1 hour, cleared after 7 days by `purge_old`.

**D18. Typesense's job.** Default: resolve the spoken words to an item name (typos, synonyms), then call `find_item`. Postgres stays the source of truth.

**D19. FaceTime agent language.** Default: Python LiveKit agent, because drawing into a published video track is verified in Python. The Chert starter is Node; attaching a Python agent by dispatch name is expected to work but untested.

**D20. Roboflow hosted inference and privacy.** Unverified whether hosted inference retains images. Default: staged scenes only until someone confirms with Roboflow.

**D21. What the model may see of people.** Default: crops are padded boxes around items; the prompt forbids describing people; no face is stored.

**D22. Measuring it.** Default metric for the write-up: on the fixture set, the share of put-down events where `find_item` then returns the right landmark. Report the number, however small the set.

**D23. Speech stack for the FaceTime agent.** Default: whatever the Chert starter ships with. Adding another speech provider means another key and another failure point.
