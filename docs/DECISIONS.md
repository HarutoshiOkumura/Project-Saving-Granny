# Decisions to settle

Each item has a default so nobody is blocked. Change a default by editing this file and telling Claude Code; it reads this file when a step depends on one.

Status key: OPEN (using default), DECIDED (write the choice and who chose).

## Settle in the first hour

**D1. Where is the "home" for the demo?** OPEN
A hackathon hall has no rooms, and every corner looks alike. Options: (a) film in a teammate's apartment or dorm and judge from the video plus a live call; (b) stage two or three tables as "rooms" with very different props (a lamp and a pillow; a kettle and a toaster; coat hooks). Default: both. Film the real walk for the video; stage two tables for live judging. The names in `supabase/seed.example.sql` must match whatever you stage.

**D2. Which items and landmarks, exactly?** OPEN
Default: 3 rooms, 6 landmarks, 6 items as in the seed file, but demo only glasses and keys. Fewer, more distinct items beat a long list. Every name here becomes an allowed answer for the vision model.

**D3. Which detector?** OPEN, decided by the step 04 bake-off
Candidates: YOLO-World zero-shot, SAM 3 text prompts, a Roboflow Instant or RF-DETR model trained on the demo items, or the language model alone. Pass rule is CP2 in `PLAN.md`. Default if nobody runs the bake-off: language model alone for placement, trained Roboflow model for boxes and crops.

**D4. Does the Chert line carry caller camera and agent video?** OPEN, ask Chert staff
This decides whether step 10 shows a photo or is audio only. Also confirm the per-call time cap and that one line means one call at a time.

**D5. Where does the backend run, and what is its public HTTPS address?** OPEN
Vapi needs a public HTTPS URL for the tool. The phone needs HTTPS to open the camera. Default: one machine (or one Coder workspace) running the API, exposed through a tunnel; put the URL in `PUBLIC_BASE_URL`. Decide who keeps that machine awake during judging.

**D6. What counts as using Coder?** OPEN, ask the Coder table
Default: develop in a Coder workspace from a shared template and use Coder Agents for one step; screenshot both.

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
