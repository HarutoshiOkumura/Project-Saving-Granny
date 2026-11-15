# Insights: three designs on top of the memory database

Status: DESIGN, not built (15 Nov 01:55 EST).
Evidence: `docs/research/save-it-data-and-safety-ideas.md` (cited; read its "Ranked recommendations" first).
Owner of each design: open (see "Decisions needed" at the end).

The research says one thing clearly.
Save It is not an early-detection tool, but it is an unusually fine clock for **change**: it can tell a family and a clinician when something started and how fast it moved.
A sudden change (questions doubling) shows in 2 to 3 days; a typical slow decline hides in the noise for 1 to 2 years.
The most dangerous and most missed acute state, hypoactive delirium, shows up as *less* activity and *less* wear, so missing data is itself a signal.

The three designs below build that, in dependency order:

1. **Wear time and honest measurement**: know when the camera was actually on, and keep perception errors and life events from looking like memory change.
2. **Change from usual**: three headline metrics against the person's own baseline, a two-track detector, a family digest and a one-page clinician summary.
3. **Confirm, then family decides**: a safety loop for falls, distress and scams during calls, plus a "quiet day" check-in that uses design 1.

Each one respects the hard rules in `CLAUDE.md`: no full frames, nothing for no-capture rooms, no edits to applied migrations, no audio stored, and wording that stays on the wellness side of the FDA line.

## Rules shared by all three

- **No disease words, ever, in anything a family or wearer sees.**
  Not "decline", "delirium", "infection", "abnormal", "risk", "score", "MCI", "sundowning", "diagnosis", "worsening".
  Say the observation and the person's own usual: "Asked about her glasses 9 times this week; she usually asks about 4."
  A unit test scans every output template for the banned words (the avoid/prefer table is in the report, "Disease words, not the data").
- **Every count is divided by worn hours** (design 1), and every chart shows coverage first.
- **Compare a person only with themselves.** No norms, no percentiles against other people.
- **Never analyse or show gaps in the room timeline.** A gap while the camera is worn can be the bathroom, which the no-capture rule exists to protect.
- **Numbers, not voices.** No audio, no voice embeddings, no transcripts kept past testing (Illinois and Texas voiceprint law, and plain respect).
- **Alerts are off by default.** The weekly digest is the default channel. The only thing that interrupts a family is design 3, and only after asking the person.
- **One new migration for all three**, after `0003` (ranked search, not applied) and `0004` (reserved for D26 C).
  Call it `0005_insights.sql`, write its checks in `supabase/tests/test_memory.sql` first and see them fail on scratch Postgres, pin `search_path` on every function, revoke from `anon`/`authenticated`, grant to `service_role`, enable RLS on every new table.
  If `0003` or `0004` is never applied, renumber before applying; the file must not depend on them.

## Design 1: Wear time and honest measurement

### Why

Without wear time every number lies: "fewer questions this week" may mean better memory, a charging phone, or a withdrawn person who never put the lanyard on.
`observations` cannot answer it, because the worker writes one only when SAM 3's gate opens on an enrolled item or for an empty look at most every 30 seconds.
The worker already sees every frame and already computes sharpness and similarity (`app/perception/filters.py`), so it knows whether the camera is on and whether it is moving.

### What

1. **`wear_minutes` table**: one row per device per minute the camera sent frames.

   ```sql
   create table wear_minutes (
     home_id   uuid not null references homes(id) on delete cascade,
     device_id text not null,
     minute    timestamptz not null,          -- date_trunc('minute', captured_at), UTC
     frames    smallint not null,             -- frames received in that minute
     moving    smallint not null,             -- frames not dropped as duplicates: the camera moved
     primary key (home_id, device_id, minute)
   );
   ```

   No room, no image, no item.
   "Worn" means `moving >= 2` in the minute: a phone lying on a table sends near-duplicates, so `moving` stays near 0.
   The worker keeps one counter per device in memory and flushes finished minutes with one upsert (adding to any existing row), so a restart loses at most one minute.
   Frames from a no-capture room still count toward wear, because wear says only "the camera was on", not where.

2. **`coverage_daily` view**: worn hours per local day (`homes.timezone`), and the share of the person's usual waking hours covered.
   Every metric in design 2 divides by it.

3. **`life_events` table**: family tags that explain a week, entered on the dashboard.

   ```sql
   create table life_events (
     id         uuid primary key default gen_random_uuid(),
     home_id    uuid not null references homes(id) on delete cascade,
     kind       text not null check (kind in ('visitor','unwell','hospital','new_medicine',
                                              'new_item','away','camera_off','new_hearing_aid','other')),
     starts_at  timestamptz not null,
     ends_at    timestamptz,                   -- null: one day
     note       text check (char_length(note) <= 200),
     created_at timestamptz not null default now()
   );
   ```

   `new_medicine` is the single most valuable tag (medication changes are a leading cause of sudden change).
   The detector in design 2 mutes or annotates tagged windows, and adding an item (`new_item`) restarts that item's baseline.

4. **`perception_quality_daily` view**: signals that the camera, not the person, changed.
   Stays that never confirmed (tentative per day), contradicted stays per landmark, confident `seen` answers followed by `not_found`, and the same item active in two places.
   Design 2 refuses to call a change on a day whose quality is outside its own usual range, and says why ("Find It had trouble seeing this week").

5. **`confident` for each question, at read time.**
   `queries.sighting_id` already points at the stay that answered, so a view computes `det_conf x room_conf x id_conf >= 0.5` from it, as `find_item` does.
   No change to `ask_item`.
   The stay's confidences can move a little after the question; that drift is accepted and noted.

### Where it lives

- `app/worker/wear.py`: the per-device minute counter (pure, unit-tested with fake clocks); `ingest.py` calls it for every frame before any filter drops it.
- `app/memory/db.py`: `upsert_wear_minutes()`, `add_life_event()`, `list_life_events()`.
- `app/main.py`: `POST /api/events`, `GET /api/events` (APP_TOKEN).
- Tests: counter edges (minute boundaries, restart, two devices, a still camera), views on scratch Postgres.

### Effort and tonight

About 3 to 4 hours in all.
**Tonight slice (about 1 hour):** the counter, the table and `coverage_daily`.
A replay through `scripts/replay_video.py` fills it, so the demo can show "camera worn 1 minute of the last hour" honestly.

## Design 2: Change from usual

### Why

This is the medical use the research supports: a passive, timestamped version of questions clinicians already ask families (ECog "where he/she has placed objects" and "repeating questions", AD8 item 3, ADCS-ADL item 11, RMBPC item 1), read as change against the person's own history.
Its job is to answer a clinician's first question about any change, "when did this start, and how fast?", which families often cannot.

### The three headline metrics

Only three, to keep false alarms from many comparisons down.
"Wearer questions" are `queries` with `channel = 'facetime'` (or `phone`); `web` is family and is reported apart.

| Metric | Definition | Echoes |
|---|---|---|
| Questions per 10 worn hours | wearer questions per local day / worn hours x 10 | RMBPC 1, ECog memory 5, AD8 3 |
| Asked again after a sure answer | share of wearer questions whose previous question about the same item, within 10 minutes, got a confident `seen` answer | ECog-II "unknowingly repeating"; the metric that moved with treatment in the VISTA trial |
| Found | `found / (found + not_found)` over questions with an outcome | ADCS-ADL 11 |

Context shown beside them, never alerted on: put-downs at the item's usual place, odd-place put-downs as dated examples ("keys on the fridge, Tuesday 3 pm"), and when in the day questions come up.

### Data

- `pattern_days(p_home uuid, p_from date, p_to date) returns jsonb`: one row per local day with worn hours, wearer questions, repeats after a sure answer, found, not found, put-downs, put-downs at the usual place, odd-place put-downs, rooms visited, and that day's perception-quality flags and life events.
  Stable, read-only, one round trip; the detector and every page read only this.
- Odd place: a confirmed put-down on a landmark that holds under 5% of that item's past confirmed stays (with at least 20 past stays), counted only for `active` stays with `id_conf` at least 0.5, so a recognition error rarely looks like an odd place.

### The detector (`app/patterns.py`, pure, no database)

Two tracks, both comparing the person only with themselves.
Every threshold is a starting guess until a study measures the real week-to-week variability (report, rank 11), and the code says so next to each constant.

- **Sudden track (daily).**
  Baseline: the previous 28 days' median per worn hour.
  Score each signal with a Poisson z-score on the day's count against baseline x worn hours, **in both directions**.
  Worn hours is itself a signal: a day worn far less than usual counts as a move.
  Flag when two signals move together for two days in a row, or one moves at least threefold in a day.
  Never flag inside a tagged `away`, `camera_off` or `hospital` window, or on a day with bad perception quality.
- **Slow track (weekly).**
  Nothing for the first 4 weeks ("Find It is learning her routine").
  Robust z on each weekly rate against the median and MAD of the previous 8 weeks, fed to a one-sided CUSUM per direction.
  Call a change only when it persists for 3 weeks.
  Show "not enough data" when a 4-week window has under 20 wearer questions or worn hours drop by more than 30% week on week.
- **Save It changes what it measures.** The first weeks after start, a new item, or a change to the agent's prompt or voice reset the baselines they touch (a `product_change` event written by the deploy).

The output is a list of `Change` objects: signal, direction, start date, size against usual, and the evidence days.
It never contains a disease, a score or a recommendation.

### Wording (`app/patterns_say.py`, pure, tested)

One template per change kind, in the observation-plus-usual form:

- "She asked about four times more than usual since Tuesday."
- "Fewer calls and less time with the camera than usual since Tuesday."
- "This is a bigger change over six weeks than we have seen before."
- "If this continues, you may want to mention it at her next appointment."

The banned-word test from the shared rules runs over every template and every rendered example.

### Surfaces

- **Family dashboard, "Patterns" tab** (step 08 builds the page shell): a "today" card ("asked about 3 things today; all were found"), the three headline metrics as small weekly charts with a shaded band for her own usual, coverage greyed where low, the life-event tags on the time axis, and the change sentences.
  No red, no gauges.
  `GET /api/patterns?weeks=12` (APP_TOKEN) returns the days, the bands and the changes.
- **Weekly digest**: the same content as a short text, in the dashboard and later by the design 3 channel when the family opts in.
- **One-page clinician summary** `GET /report/monthly` (APP_TOKEN, printable HTML): header "Prepared from Save It by [family member]. Everyday observations, not a medical test"; a coverage strip; the three charts over 6 to 12 months with her own band; tagged events with two or three dated examples; a "questions for this visit" box the family fills in; a footer saying what is never recorded and that the numbers have no norms.
  It fits the hour-long cognitive care-planning visit (CPT 99483) and GUIDE dementia programs such as Emory Integrated Memory Care.
- **The wearer** sees none of the charts.
  Their side is their items, what is kept about them, and a pause control.

### Consent

- `homes.share_summary_with_clinician boolean not null default false`, set only after asking the wearer while they can answer, with the date recorded (`share_decided_at`).
  The monthly page refuses to render for sharing while it is false.
- Research use, if a study happens, is a separate consent and gets only de-identified totals.

### Demo data

The demo home has a few hours of history, not weeks, so the trend views would be empty.
Use a **separate sample home** (`HOME_ID` `22222222-...`, labelled "Sample: not a real person" on every page) filled by `scripts/sample_history.py`.
Sightings go through `log_sighting` with past `p_seen_at` values (allowed).
`ask_item` always stamps `now()`, so sample questions need a direct insert into `queries`; that is acceptable only in the sample home, and the script refuses any other `HOME_ID`.
The script writes a believable 10-week story: a steady routine, a `new_medicine` tag in week 6, then four days of more questions and less wear, which the sudden track flags.

### Effort and tonight

About 1.5 to 2 days for the function, the detector, the wording, the API and the monthly page; the dashboard tab follows step 08.
**Tonight slice:** none in code.
Use the report's evidence slide and the wording table in the pitch ("Save It notices change from her own usual, and hands the dated timeline to her doctor").

## Design 3: Confirm, then the family decides

### Why

People with dementia who fall often cannot get up, and cognition was the only predictor of lying on the floor for an hour or more; call alarms mostly went unused.
But an automatic 911 call fails on accuracy (motion-sensor detectors averaged 57% sensitivity on real falls), on law (automated calls to 911 centres: $10,000 to $100,000 fines per call unless an emergency purpose, untested for software false alarms), and on harm (sirens and strangers terrify a confused person).
The industry pattern is detect, confirm with the person, hand to a human who decides.

### What

1. **`report_concern` tool in the FaceTime agent** (Tom's area: `agent/saveit.mjs`, `agent/prompt.mjs`).
   Kinds: `fall`, `hurt`, `help`, `smoke`, `scam`, `lost_outside`.
   Triggers named in the prompt: "I fell", "I can't get up", "help me" (not "help me find..."), "I smell smoke", "someone wants gift cards / a wire / my bank details", "my grandson is in jail", "don't tell anyone".
   Flow: one calm question ("Are you hurt?"), wait up to 45 seconds, then call the tool with the answer (`hurt`, `ok`, `no_answer`).
   "I'm fine" still reports at low urgency: people with dementia sometimes deny a real fall.
   Near-miss phrases ("my glasses fell", "help me find my keys") must not fire; they are the first voice tests.
2. **`concerns` table and endpoints.**

   ```sql
   create table concerns (
     id           uuid primary key default gen_random_uuid(),
     home_id      uuid not null references homes(id) on delete cascade,
     kind         text not null check (kind in ('fall','hurt','help','smoke','scam','lost_outside','quiet_day')),
     answer       text check (answer in ('hurt','ok','no_answer')),
     urgency      text not null check (urgency in ('urgent','check_in','note')),
     raised_at    timestamptz not null default now(),
     room_id      uuid references rooms(id) on delete set null,  -- last room the camera saw, if any
     status       text not null default 'open' check (status in ('open','on_my_way','calling_911','all_ok')),
     handled_at   timestamptz,
     handled_by   text
   );
   ```

   `POST /concerns` (APP_TOKEN, from the agent) and `POST /concerns/{id}/handle` (APP_TOKEN, from the family's buttons).
   Urgency: `hurt` or `no_answer` after a fall or help is `urgent`; `ok` is `check_in`; `scam` is `note`.
   The payload carries words, the time and the last room only: no frame, no crop of a person.
3. **Family side.**
   An urgent concern shows a full-width banner on the dashboard (it already polls every 2 seconds, D16) with three buttons: "I'm on my way", "I'm calling 911", "All OK".
   The family member decides; the software never dials.
   A notification channel that reaches a phone (SMS or push) is a separate decision below; until it exists the agent must not say it told anyone (`.claude/rules/voice.md`).
   Production path, pitched not built: an unanswered urgent concern escalates to a professional monitoring service (Noonlight-style), which calls the person and the family before involving 911.
4. **What the agent says.**
   Until the channel exists: "I'm here with you. If you are hurt, please call 911 or ask someone near you for help."
   After: "I'm letting June know now. Stay where you are; she'll be in touch."
   For a scam: "That sounds like a trick some people try. It's fine to hang up. Let's not send any money today."
   Wording goes into `.claude/rules/voice.md` with the other templates, reviewed by a person.
5. **Quiet-day check-in** (uses design 1).
   If by 2 pm local the camera has been worn under a quarter of its usual morning hours and no call came in, raise a `quiet_day` concern at `check_in` urgency: "Find It hasn't heard from Mom today, and the camera has been off since 9 am."
   It catches a charging phone as often as a withdrawn person, and says so in plain words; it never guesses why.

### Honest limits

- It only helps during a call, or through the quiet-day check; a fall with no call and the phone face down is invisible.
  Recommend Apple Watch Fall Detection (on by default at 55+) to families instead of rebuilding it.
- The scam guard only hears what the person tells Find It, not the scam call itself.
- A lanyard motion-sensor trigger waits for the capture page (step 07); it adds false alarms from the swinging phone and needs the same confirm step.

### Effort and tonight

About 4 to 6 hours plus the channel.
**Tonight slice (about 1 to 1.5 hours, Tom):** the prompt rules and the confirm question with today's safe sentence, the `report_concern` tool writing to the call log, and the near-miss voice tests.
On stage, show it as "confirm, then the family decides", never with a real 911 call.

## Decisions needed

- **Owners.** Design 1 and the backend of 3: Haru with Claude Code? The agent side of 3: Tom?
- **Notification channel** for design 3 and the digest: SMS (needs a provider account and a number), web push (needs the dashboard installed as a PWA), or email (slowest). Recommendation: SMS, because the people who answer a fall are not watching a dashboard.
- **Sample home** for design 2's demo and pitch: approve the separate `22222222-...` home and the direct `queries` insert in it only?
- **Migration number**: `0005_insights.sql`, or fold into whatever applies first.
- **What to say on stage**: the report's line is "Save It is a clock for change, not a diagnostic test", with "could support research" and never "detects decline".

## Not in these designs (and why)

- Bathroom-visit counts (the strongest infection signal in the Minder study): they would break the no-capture rule. Not recommended.
- Voice biomarkers from call audio: calls are seconds long, speech recognition errs more in dementia, and voiceprints carry legal risk. Interaction numbers per call (asked again within a call, "which one?" turns, reply delay from `voice-meter.mjs` events) are a later, separate table once design 2 has baselines.
- Learned place priors and confidence calibration from outcomes: high value for "where to look" and no clinical risk, but they improve the core product, not these three. Next after them.
