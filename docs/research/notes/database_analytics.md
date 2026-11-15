# Database analytics and caregiver insights from object sightings and "where is my X?" questions

Scope: what Save It could compute from `observations`, `sightings`, `queries`, `misses`, `items`, `landmarks` and `item_usual_places`, what the evidence says each metric means, what can go wrong, what caregivers actually want to see, and where the regulatory line sits.
Research date: 15 Nov 2026.
Column names below match `supabase/migrations/0001_save_it_memory.sql` and `0003_ranked_search.sql` (for example `sightings.first_seen_at`, `queries.asked_at`, `queries.state`, `queries.outcome`, `misses.missed_at`, `items.home_landmark_id`, `observations.captured_at`).
Note: the schema allows `queries.channel` values `phone`, `facetime` and `web`.

## 1. Do misplacing objects, searching for them and repeated questions track MCI and dementia, and has passive home sensing used them as digital markers?

### Takeaway
Misplacing objects and repeating questions are standard informant-rated items on validated early-change instruments (ECog, AD8, ADCS-ADL), and object-location memory is impaired in MCI and Alzheimer's disease on lab tests.
I found no study that used passively sensed object put-downs, misplacement events or "time to find keys" in real homes as a validated digital biomarker; the validated passive-sensing markers (ORCATECH, CART) are mobility, walking speed, routine variability, sleep and time out of home.
Save It's data would be a passive, objective analogue of specific questionnaire items, which is novel and promising but unvalidated.

### Cited Findings
Questionnaire items that map directly onto Save It data:
- The original Everyday Cognition (ECog) memory domain includes item 4 "Remembering where he/she has placed objects" and item 5 "Repeating stories and/or questions" - [Farias et al. 2021, Alzheimer Dis Assoc Disord, ECog revisions](https://pmc.ncbi.nlm.nih.gov/articles/PMC8387334)
- The 2021 ECog-II revised those items to "Remembering where he/she has placed personal items or objects" and "Unknowingly repeating stories and/or questions multiple times" - [Farias et al. 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC8387334)
- The ECog (39 items, six domains) is informant-rated and was reported in 2008 to differentiate normal cognition, MCI and dementia and to be sensitive to early functional change in MCI - [APA press release, 2008](https://www.apa.org/news/press/releases/2008/07/cognition)
- AD8 item 3 asks whether the person shows a change in repeating "the same things over and over (questions, stories, or statements)"; each "yes, a change" scores 1 and a total of 2 or more suggests cognitive impairment is likely - [Alzheimer's Association AD8 form](https://alz.org/getmedia/6e7291bf-4ac8-40ed-a148-824d4591ed7e/ad8-dementia-screening.pdf)
- The AD8 is a screen, not a diagnosis, and is preferably given to an informant - [Alzheimer's Association AD8 form](https://alz.org/getmedia/6e7291bf-4ac8-40ed-a148-824d4591ed7e/ad8-dementia-screening.pdf)
- The AD8 is copyrighted by Washington University and its terms permit reproduction only as published, without modification or derivative works - [Knight ADRC AD8 worksheet, 2005](https://knightadrc.wustl.edu/app/uploads/2021/06/AD8-Worksheet-English-2005.pdf)
- The ADCS-ADL inventory item 11 asks "In the past 4 weeks, did {S} usually manage to find his/her personal belongings at home?" rated without supervision or help (3), with supervision (2) or with physical help (1) - [ADCS-ADL form](https://dementiaresearch.org.au/wp-content/uploads/2016/01/ADCS-ADL_Form.pdf)
- Pfeffer's Functional Activities Questionnaire (FAQ) has 10 items (bills, tax records, shopping, game of skill, making coffee, meals, current events, attention to TV or books, remembering appointments and medications, travel) and no item about misplacing things - [Hartford Institute / Alzheimer's Association FAQ sheet, rev. 2016](https://alz.org/getmedia/73ea01f0-690b-4ff3-b909-4f0fa9a022ef/functional-activities-questionnaire.pdf)
- The FAQ uses a total of 0 to 30 with a recommended cut point of 9 (dependent in 3 or more activities) - [Hartford Institute FAQ "Try This"](https://hign.org/consultgeri/try-this-series/use-functional-activities-questionnaire-older-adults-dementia)

Evidence that everyday memory complaints predict decline:
- A 2010 NYU study (213 adults, about 7 years follow-up) found healthy older adults with subjective cognitive impairment, which includes lapses such as misplacing things, were 4.5 times more likely to progress to MCI or dementia stages - [ScienceDaily, Jan 2010](https://sciencedaily.com/releases/2010/01/100108101423.htm)
- In the Sydney Memory and Ageing Study (873 adults aged 70-90, 6 years), each point on an informant memory-complaint index carried a fully adjusted hazard ratio for incident dementia of 1.20 (1.12-1.28), and only informant indices stayed significant after adjusting for mood and personality - [Numbers et al. 2020, PLoS One](https://pmc.ncbi.nlm.nih.gov/articles/PMC7217434/)
- That study reported composite indices only, with individual items in a supplement, so it does not isolate a "misplacing objects" item effect - [Numbers et al. 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7217434/)

Object-location memory in the lab:
- Kessels et al. (2009) tested 30 MCI, 30 AD and 40 healthy controls on the Location Learning Test and found AD worse than MCI on both positional recall and object-location binding, noting that evidence on object-location memory in MCI had been "lacking altogether" before - [Kessels et al. 2009, J Int Neuropsychol Soc](https://www.cambridge.org/core/product/identifier/S1355617709990944/type/journal_article)
- The computerized Misplaced Objects Test has participants place 20 common objects in a simulated house and later find them, scoring finds on first and second attempts - [Misplaced Objects Test record](https://scilit.com/publications/883558b722dd38dbae1e7aa2f0a47857)

Repetitive questioning:
- Repetitive questioning is attributed to impaired episodic memory (difficulty learning, retaining and recalling new information), often worsened by poor attention and distractibility - [Hamdy et al. 2018, Gerontol Geriatr Med, "Repetitive Questioning Exasperates Caregivers"](https://etsu.elsevierpure.com/en/publications/repetitive-questioning-exasperates-caregivers/)
- In a US survey of 250 unpaid caregivers using the Cohen-Mansfield Agitation Inventory, repetitive questioning was the most common behaviour (94.8% of care recipients), and each 5-point CMAI increase was associated with 19% higher odds of high caregiver burden - [Grossberg et al., Dementia (survey run 2021; publication year listed as 2024 or 2025, check before citing)](https://www.hmpgloballearningnetwork.com/site/altc/news/agitated-behaviors-alzheimer-disease-strongly-linked-caregiver-burden-us-survey)

Theft delusions (a reason misplacement data matters to families):
- Delusions of theft are reported as the most common delusion subtype in Alzheimer's samples (for example 75.5% of deluded patients in a Japanese sample and 50.4% in a European study) and as a major driver of care burden - [Frontiers in Psychiatry 2021 review](https://www.frontiersin.org/articles/10.3389/fpsyt.2021.808724/full); figures came from a search summary and were not checked against the full text.

Passive home sensing studies (none tracked object misplacement):
- ORCATECH homes use passive infrared motion sensors in every room, door contacts on exterior doors and wearables, with optional pillboxes and scales - [Wu et al. 2021, Front Digit Health](https://www.frontiersin.org/journals/digital-health/articles/10.3389/fdgth.2021.764510/full)
- Akl et al. clustered home activity distributions from 85 single-occupant homes and detected MCI with an F0.5 score of 0.856 - [Akl et al. 2016 record](https://repository.adu.ac.ae/items/b28b297e-11ba-4473-a0f7-0e9e7ee59a6e)
- The CART platform (no video or audio) was deployed in 232 homes with 301 older adults across four US cohorts, collecting room transitions, sleep, computer use, medication boxes and more over months to years - [Beattie et al. 2020, Digital Biomarkers](https://doaj.org/article/303f4d042ced437491356dcb5bf5f1e5)
- ORCATECH reported that two weeks of monitoring did not predict MCI, that people with MCI wore their watches less often, and that medication-taking behaviour might be an early digital biomarker - [Alzforum, "Smart Homes Open Doors to Insights into Aging, Dementia"](https://alzforum.org/node/1226746)
- The public CASAS dataset (179 participants with cognitive diagnoses) includes item-use sensors recording whether an item is on its sensor during scripted complex tasks, building on Dawadi, Cook and Schmitter-Edgecombe (IEEE TSMC 2013) - [CASAS dataset on Zenodo](https://zenodo.org/records/15713579/latest)
- A 2022 review found smart-home activity recognition and anomaly detection "lack the capability of detecting transitions between stages of dementia" - [Sensors 2022, "Are Smart Homes Adequate for Older Adults with Dementia?"](https://doi.org/10.3390/s22114254)
- In an 18-month study of 35 older adults (15 giving daily commands to a home voice assistant), an LLM method detected MCI from command logs with 72.67% F1 - [Cog-TiPRO, arXiv 2025](https://arxiv.org/abs/2505.17137)
- In the European ENABLE trials (MMSE 12-25), an item locator was the most-trialled device (about 80% of Irish cases), but devices other than a passive night lamp often needed a carer to prompt use - [ENABLE Irish data, Trinity College Dublin](https://www.tara.tcd.ie/bitstreams/140b573c-069a-4344-95ba-d142d5a22b7b/download)
- Ego4D defines an episodic-memory "natural language queries" task (find the moment in first-person video that answers a question such as where an object was left), showing the engineering problem is studied but as computer vision, not as a clinical marker - [Grauman et al., Ego4D, arXiv 2110.07058](https://arxiv.org/abs/2110.07058)

### Inferences
- Save It's `sightings` and `queries` are a passive, objective version of ECog memory items 4 and 5, ADCS-ADL item 11 and AD8 item 3, which no published study has done in real homes as far as I could find.
- That makes "misplacement and repeat-question metrics" a plausible research direction, but the product must describe them as everyday facts ("asked about glasses 9 times this week"), not as a marker of cognition.
- The Sydney finding that informant reports carry the prognostic weight suggests pairing Save It's numbers with a short periodic caregiver check-in rather than replacing it.
- Do not embed the AD8 wording in the app or derive a score from it without Washington University permission.
- Save It's data has two advantages over ORCATECH-style motion sensors: object identity and the person's own questions; and two disadvantages: it depends on the phone being worn and on vision accuracy.

### Gaps
- No study found that measured search time, misplacement frequency or put-down location consistency passively in homes and related it to cognitive status or progression.
- No item-level hazard ratio for a "misplaces things" complaint was found; Sydney reports composites only.
- I could not verify whether misplacing objects precedes or triggers theft delusions; I found prevalence data only.
- The 2008 ECog paper's exact discriminative statistics for item 4 alone were not retrieved.

## 2. Routine and circadian metrics from room-level location over time: what has been validated?

### Takeaway
Validated room-level passive-sensing findings are modest and mostly from small ORCATECH cohorts: lower day-to-day stability of room-to-room transitions, more variable walking, slower walking trajectories and less time out of home associate with MCI or worse cognition.
Raw transition counts were not different, sleep findings were counterintuitive, and "sundowning" has no agreed definition, so evening-question metrics would be untested.
Save It's room data comes from a worn camera, not fixed sensors, so coverage (wear time, bathrooms excluded, nights while charging) is the dominant confounder.

### Cited Findings
- Wu et al. (139 adults living alone, 19 with MCI, 4,964 weeks) defined "mobility stability" as an interdaily stability measure of hourly room-to-room transitions adapted from circadian sleep-wake research, and lower stability was associated with MCI (adjusted beta -0.04, p = 0.03; baseline Cohen's d about 1) - [Wu et al. 2021, Front Digit Health](https://www.frontiersin.org/journals/digital-health/articles/10.3389/fdgth.2021.764510/full)
- In the same study, mobility frequency (room transitions per day) did not differ between MCI and non-MCI (d = 0.13, p = 0.62), and the MCI group was small - [Wu et al. 2021](https://www.frontiersin.org/journals/digital-health/articles/10.3389/fdgth.2021.764510/full)
- CART cohorts averaged 96-155 room transitions per day and 6.3-7.4 hours of nightly sleep, with overnight visitors reported by 15-45% of participants - [Beattie et al. 2020, Digital Biomarkers](https://doaj.org/article/303f4d042ced437491356dcb5bf5f1e5)
- Hayes et al. (7 MCI, 7 controls, up to 60 weeks, more than 108,000 hours) found more variable walking times and activity in MCI, with the gap larger in the afternoon than the morning - [Hayes et al. 2008, Alzheimer's & Dementia, record](https://katalog.lib.cas.cz/KNAV/EdsRecord/edselp,S1552526008028653)
- Dodge et al. followed 93 adults living alone for about 2.6 years and found non-amnestic MCI over-represented in the slowest, steepest-declining in-home walking-speed trajectory - [Dodge et al. 2012, Neurology](https://pmc.ncbi.nlm.nih.gov/articles/PMC3369505)
- Petersen et al. measured daily time out of home with in-home sensors for up to a year in 85 adults and found more time out associated with better cognitive status, with weather, season and weekday also affecting it - [Petersen et al. 2015, PLoS ONE](https://econpapers.repec.org/RePEc:plo:pone00:0139643)
- ORCATECH coverage notes that socialization, measured as time out of the house, waned at moderate amyloid plaque burden - [Alzforum](https://alzforum.org/node/1226746)
- MCI detection still worked in two-person homes, but analysis worked better hour-by-hour or longitudinally - [Muurling et al. 2023, JMIR Aging](https://preprints.jmir.org/preprint/45876/accepted)
- In ORCATECH sleep monitoring (about 26 weeks), amnestic MCI showed less sensor-measured sleep disruption than cognitively intact participants, contradicting self-reports of no group difference - [Lyons et al. 2015, Front Aging Neurosci](https://pmc.ncbi.nlm.nih.gov/articles/PMC4462097)
- In the first 8 participants of an ORCATECH bed-mat study, more disrupted sleep went with higher weekly agitation, and the authors call for larger samples - [Front Digit Health 2022](https://www.frontiersin.org/articles/10.3389/fdgth.2022.809370/full)
- GPS spatial entropy plus trip distance and speeding separated MCI from normal cognition in 298 older drivers with AUC 0.82 (0.87 with demographics, APOE and cognitive scores) - [Practical Neurology summary of a 2025 Neurology study](https://practicalneurology.com/news/driving-patterns-may-reveal-early-cognitive-decline/2484961/)
- In a small two-week GPS study (7 people with dementia, 8 controls), patients differed on entropy, segment similarity and distance from home - [Ghosh et al. 2022, Scientific Reports](https://discovery.ucl.ac.uk/id/eprint/10160708/1/Ghosh%20Sci%20Reports.pdf)
- "A clear and univocal definition of the sundown syndrome has not been yet achieved", including the time window, and epidemiological data are scarce - [Frontiers in Medicine 2016 mini review](https://www.frontiersin.org/articles/10.3389/fmed.2016.00073/full)
- A 2012 systematic review found the sundowning label used frequently in care settings without consistent meaning - [Sundown syndrome: a systematic review](https://pure.psu.edu/en/publications/sundown-syndrome-a-systematic-review-of-the-literature/)
- One clinical reference gives sundowning prevalence of 2.4% to 25% of people with dementia - [GPnotebook, secondary source](https://gpnotebook.com/pages/neurology/sundown-syndrome)
- The UK TIHM study combined home sensors and machine learning to flag agitation and urinary tract infections, routing dashboard alerts to a clinical monitoring team - [NHS Long Term Plan case study](https://longtermplan.nhs.uk/case-studies/technology-integrated-health-management)
- TIHM-related work reported recognising agitation and unusual patterns with accuracy up to 80% - [PLoS ONE 2018](https://doaj.org/article/06f9906eef1142eda4c1e277283b23c7)
- TIHM continued as the UK DRI "Minder" platform led by David Sharp - [Barnaghi lab, UK DRI](https://www.ukdri.ac.uk/labs/barnaghi-lab)
- Caregivers in a qualitative study wanted monitoring especially for falls risk, day and night rhythm, personal hygiene, nocturnal restlessness, and eating and drinking - [JMIR Aging 2021, requirements for unobtrusive monitoring](https://aging.jmir.org/2021/2/e26875/)

### Inferences
Metrics Save It can compute from `observations` (all untested for a worn camera):

| Metric | Computation | What it may show | Evidence status | Main pitfalls |
|---|---|---|---|---|
| Observed coverage | Distinct 5-minute bins with at least one `observations` row per day and per hour | Denominator for every other metric; wear habits | Needed for validity; ORCATECH saw less wear in MCI (Alzforum) | Wear time is itself confounded with cognition and mood |
| Room dwell profile | Minutes per `room_id` per hour of day, over covered bins only | Daily routine (kitchen at breakfast, living room evenings) | Analogous to sensor dwell work; not validated for cameras | `capture_allowed = false` rooms (bathroom) never logged; low `room_conf` frames |
| Room transitions and stability | Hourly transition counts; interdaily stability over a week (Wu 2021 style) | Day-to-day regularity of routine | Stability, not frequency, linked to MCI (Wu 2021) | Missing hours break stability formulas; visitors change routine |
| Activity onset and offset | First and last covered observation per day | Getting up and settling times | Plausible; not validated | Mostly measures when the phone is put on and taken off |
| Out-of-home proxy | Long gaps during daytime while phone not at charger (needs a "docked" signal) | Outings | Time out of home validated with door sensors (Petersen 2015) | Cannot tell outing from phone left on a table |
| Night activity | Observations between 23:00 and 06:00 local (`homes.timezone`) | Night wandering, if the lanyard is worn at night | Night restlessness is a caregiver priority (JMIR Aging 2021) | Near-zero coverage at night; dark frames fail perception |
| Evening question share | Share of wearer questions asked 16:00-22:00 vs personal baseline | A starting point for a "late-day difficulty" conversation | Sundowning undefined; no validation | Do not label it "sundowning"; evening may simply be when the person is home and idle |

- Treat routine metrics as context for the item and question metrics, not as headline numbers, because fixed-sensor findings do not transfer to a worn camera without re-validation.
- Never present the night or bathroom absence as "slept well"; missing data must look missing on charts.

### Gaps
- No study found validating room-level routine metrics derived from a body-worn camera.
- One ORCATECH study (128 adults, up to 527 days) reportedly found MCI associated with attenuated seasonal variation in night-time bedroom time; I could not confirm its citation URL.
- No validated objective measure of sundowning from home data was found.
- TIHM clinical outcome results (admissions avoided) were not found beyond case-study quotes.

## 3. Misplacement- and question-specific metrics: a catalog

### Takeaway
Save It can compute a rich set of item and question metrics directly from its tables, each mapping onto a recognised everyday-memory construct (placing objects, repeating questions, finding belongings), but every one of them is untested as a clinical measure.
The most useful caregiver-facing ones are concrete and actionable (where things end up, which items cause the most questions, whether answers led to finding the item); the most fragile are those that look clinical (unknown_item rate as "naming difficulty").

### Cited Findings
- ECog memory items cover placing objects and repeating questions, and ECog-II specifies "unknowingly" repeating multiple times - [Farias et al. 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC8387334)
- ADCS-ADL rates whether the person finds personal belongings without help, with supervision or with physical help - [ADCS-ADL form](https://dementiaresearch.org.au/wp-content/uploads/2016/01/ADCS-ADL_Form.pdf)
- Word-finding difficulty and reduced lexical diversity are characteristic of MCI in spontaneous-speech studies - [JMIR Aging 2023](https://aging.jmir.org/2023/1/e46483/)
- Automatically computed lexical features had only moderate within-task reliability (r about 0.49-0.65) in 39 older adults - [JMIR Aging 2023](https://aging.jmir.org/2023/1/e46483/)
- Early-AD participants differed from controls in lexical diversity, syntactic complexity and disfluency, and linguistic features added accuracy on top of biomarkers - [Frontiers in Aging Neuroscience 2024](https://www.frontiersin.org/journals/aging-neuroscience/articles/10.3389/fnagi.2024.1451326/full)
- In a voice-assistant study, intent and audio features were more sensitive to MCI than text features, and everyday command speech is noisy and unstandardized - [Cog-TiPRO, arXiv 2025](https://arxiv.org/abs/2505.17137)
- Voice-assistant speech features (slower speech rate, longer response time) were associated with cognitive impairment in older drivers - [JMIR 2021](https://jmir.org/2021/4/e27667/PDF)
- MCI detection in two-person homes is harder than in single-person homes - [Muurling et al. 2023](https://preprints.jmir.org/preprint/45876/accepted)

### Inferences
Definitions use Save It tables.
"Wearer questions" means `queries.channel in ('phone','facetime')`; `web` is usually family and must be reported separately.
"Put-downs" means `sightings` with `event_type = 'seen'`, `in_hand = false`, `status in ('active','superseded','contradicted')` (two-frame confirmed; exclude `tentative`).

| # | Metric | Computation | What it may tell a caregiver | Evidence status | Pitfalls |
|---|---|---|---|---|---|
| 1 | Home-place adherence | Share of put-downs per item per week at `items.home_landmark_id` | Whether "a place for everything" habits are holding; where to add a tray or hook | Construct: ECog item 4; untested | Home place set by family may not be the person's real habit; rooms not in camera view |
| 2 | Placement entropy | Shannon entropy of put-down landmarks per item over a rolling 28 days, normalised by log(number of landmarks used) | Habit strength: low = consistent, rising = items wandering | Analogue of mobility entropy and stability (Wu 2021, GPS entropy); untested for objects | Entropy rises with more landmarks registered and more camera coverage; needs smoothing with few stays |
| 3 | Unusual-place events | Put-down at a landmark whose smoothed historical share for that item is under about 5%, or a category-implausible place (glasses in the fridge) | "Check the bread bin" tips; early sign that the environment needs simplifying | Untested | Perception errors masquerade as unusual places; require `status = 'active'` and decent `id_conf` |
| 4 | Put-downs per day | Count of new put-down stays per item per day per covered hour | How much an item is handled | Untested | Exposure: more wear time = more sightings |
| 5 | Carry time | Total minutes of `in_hand = true` stays per item | Items that are carried around (risk of leaving them in odd places) | Untested | In-hand detection is the hardest perception case |
| 6 | Wearer questions per day | Count of wearer questions per day, total and per `item_id` | Burden and need: which items cause the most trouble | Construct: ECog item 5, AD8 item 3; untested | Novelty effect in the first weeks; family calling on the person's behalf |
| 7 | Repeat-question rate | Share of wearer questions where the same `item_id` was asked within 10 minutes (and within 60 minutes) after a `seen` answer | Whether answers "stick"; repetition is the top caregiver stressor (Grossberg) | Construct: ECog-II "unknowingly repeating"; untested | Poor call audio or a wrong answer also causes re-asking; check `outcome` |
| 8 | Forgetting latency | `asked_at` minus `first_seen_at` of the stay that answered (`queries.sighting_id`) | How soon after putting something down the person loses track of it | Novel; untested | Only defined when the put-down was seen; censored when nobody asks |
| 9 | Time to find | `outcome_at` minus `asked_at` for `outcome = 'found'` | Whether answers are usable in practice; ADCS-ADL "finds belongings" analogue | Construct: ADCS-ADL item 11; untested | Depends on when the follow-up question was asked, not when the item was actually found |
| 10 | Answer usefulness | found / (found + not_found) overall, by `state`, by confidence band | Is Save It helping; which states mislead | Product metric; no clinical meaning | Outcome missing for many calls (selection bias toward easy cases) |
| 11 | Not-there-anymore rate | Share of answers with `state = 'not_there_anymore'` | Items moved while unseen: by another person, off camera, or misperceived | Product metric | In two-person homes, others move things (Muurling 2023) |
| 12 | Never-seen and dark items | Days since last confirmed sighting per item; share of `never_seen` answers | Items possibly lost outside the home or never in camera view | Product metric | Perception misses look like loss |
| 13 | Unknown-item rate | Share of wearer questions with `state = 'unknown_item'`; inspect `heard` | Mostly a vocabulary and speech-recognition problem; possibly word-finding trouble | Word-finding is an MCI feature, but this proxy is untested and weak | Speech-to-text errors on older voices, hearing loss, items never registered, phone line noise |
| 14 | Misses per place | `misses` count per item and landmark | Places the person keeps checking in vain (old habits); where to put a reminder label | Untested | `misses.source` mixes caller, manual and worn camera |
| 15 | Family-told share | Share of `sightings` with `event_type` told by family or caller | Camera coverage gaps and family workload | Product metric | None clinical |
| 16 | Question time-of-day profile | Wearer questions by hour and weekday vs personal baseline | Times of day that are hardest; plan help around them | Sundowning undefined; untested | Activity and wear time also vary by hour |

Example SQL for metric 7 (repeat-question rate), assuming a local-time view:

```sql
with q as (
  select id, item_id, asked_at, state,
         lag(asked_at) over (partition by item_id order by asked_at) as prev_at
  from queries
  where channel in ('phone','facetime') and item_id is not null
)
select date_trunc('week', asked_at) as week,
       count(*) filter (where asked_at - prev_at < interval '10 minutes')::float
         / nullif(count(*), 0) as repeat_10min_share
from q
group by 1
order by 1;
```

Example SQL for metric 2 (placement entropy per item, last 28 days):

```sql
with p as (
  select item_id, landmark_id, count(*) as n
  from sightings
  where event_type = 'seen' and not in_hand and status <> 'tentative'
    and first_seen_at > now() - interval '28 days'
  group by 1, 2
), t as (
  select item_id, landmark_id, n, n::float / sum(n) over (partition by item_id) as p
  from p
)
select item_id, -sum(p * ln(p)) as entropy_nats, count(*) as places_used, sum(n) as stays
from t
group by item_id;
```

- Report metrics 1, 3, 6, 9 and 10 to caregivers by default; keep 2, 7, 8 and 16 as trend lines behind a "patterns" tab; keep 13 internal (speech-recognition quality) and never label it as language or naming ability.
- Every rate needs an exposure denominator (covered hours, put-downs, or questions) and a minimum count before display (for example at least 10 events in the window).
- Metric 8 (forgetting latency) is the most original idea here, because no questionnaire can measure the time between putting something down and losing track of it.

### Gaps
- No published norms exist for any of these metrics in healthy older adults, so "how many questions a week is a lot" is unknown.
- No study tested whether failed-lookup questions to a voice agent track ECog or ADCS-ADL scores.
- No evidence was found on how speech-recognition error rates differ between older adults with and without MCI on short item names.

## 4. Trend detection: detecting meaningful change over weeks without alarming caregivers over noise

### Takeaway
The passive-sensing literature favours personal baselines over population thresholds and longitudinal analysis over snapshots, and shows that two weeks of data is not enough.
Deployed alert systems (TigerPlace, TIHM) send baseline-deviation alerts to clinicians who decide what to do, and family-facing alert systems suffer from false alarms and alert fatigue.
For Save It, a run-in of about 4 weeks, weekly aggregation, exposure normalisation, robust personal z-scores or CUSUM, and a "sustained for 2-3 weeks" rule are reasonable defaults, but none has been validated for this data.

### Cited Findings
- High-frequency in-home monitoring with individual-specific thresholds could substantially reduce trial sample sizes; the authors estimated about 2,000 subjects with four years of follow-up would be needed to detect a 30% effect on an annually assessed memory test - [Dodge et al. 2015, PLoS ONE](https://pmc.ncbi.nlm.nih.gov/articles/PMC4574479)
- Two weeks of monitoring did not predict MCI in ORCATECH work - [Alzforum](https://alzforum.org/node/1226746)
- Hayes et al. found variability, not just averages, distinguished MCI over long monitoring, arguing that a clinic visit gives only a snapshot - [Hayes et al. 2008 record](https://katalog.lib.cas.cz/KNAV/EdsRecord/edselp,S1552526008028653)
- TigerPlace alerts were triggered by changes from each resident's prior baseline (day to day or over two weeks) and emailed to clinicians, who decided on follow-up; bed-sensor data accounted for at least half of relevant clinical alerts - [Today's Geriatric Medicine, 2013](https://www.todaysgeriatricmedicine.com/archive/050613p8.shtml)
- TigerPlace residents with sensors stayed about 1.7 years longer than those without, in a non-randomised comparison - [News-Medical, 2012](https://www.news-medical.net/news/20120615/MU-in-home-sensors-monitor-changes-in-aging-adults-health.aspx)
- Lancaster University and Howz described learning an individual's daily or weekly pattern and flagging unexpected deviations, distinguishing short-term anomalies from long-term changes - [EurekAlert](https://www.eurekalert.org/news-releases/484780)
- Unsupervised concept-drift detection was applied to home sensor data from 20 (pre-)frail older adults to flag abnormal behaviour - [Applied Intelligence 2022](https://link.springer.com/doi/10.1007/s10489-022-03611-3)
- A permutation-based routine-change method was evaluated on 18 smart homes of older adults - [Health and Technology 2018](https://link.springer.com/doi/10.1007/s12553-018-0260-4)
- Weather, season and weekday changed daily time out of home, so these must be modelled - [Petersen et al. 2015](https://econpapers.repec.org/RePEc:plo:pone00:0139643)
- Earlier remote-monitoring analyses highlighted false alarms as a barrier, and caregivers valued alert context (utility, accuracy, delivery type) - [Zmora et al. 2021, J Gerontol Nurs](https://experts.umn.edu/en/publications/dementia-caregivers-experiences-and-reactions-to-remote-activity-/)
- In 62 caregivers, alert counts declined over the first 6 months and were not associated with usability or primary outcomes; 38% of caregiver comments were negative - [Gaugler group, GSA 2019 abstract](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6840027/)
- CUSUM charts accumulate deviations from a target to detect small persistent shifts faster than per-point thresholds - [NIST/SEMATECH e-Handbook, CUSUM](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc323.htm)
- Bayesian online change-point detection computes a posterior over "run length since the last change" for streaming data - [Adams and MacKay 2007, arXiv](https://arxiv.org/abs/0710.3742)

### Inferences
Suggested pipeline (untested, design proposal):
- Run-in: no trend shown for the first 4 weeks; label it "learning her routine" (two weeks failed in ORCATECH; four weeks is a guess, not a validated minimum).
- Aggregate weekly, in the home's time zone, with exposure: questions per 10 covered hours, put-downs at home place per 10 put-downs.
- Baseline: rolling median and MAD over the previous 8 weeks, excluding the current week; robust z = (x - median) / (1.4826 x MAD).
- Count data: model wearer questions per week as negative binomial with exposure offset and run a one-sided CUSUM on standardized residuals; tune the threshold so expected false alerts are about one per 6 months per metric.
- Persistence: only surface a "noticeable change" when the change holds for 2-3 consecutive weeks; show single-week spikes only as a dot on the chart.
- Two time scales: acute (day-level jump in questions or night activity over 2-3 days, which in TIHM-style systems is where infections or delirium show up) and slow drift (months).
  Acute changes are the more actionable ones, but Save It must phrase them as "a change from usual", never as a possible illness.
- Few headline metrics: limit to about three tracked trends (wearer questions per week, home-place adherence, repeat-question share) to limit multiple-comparison false alarms across many items.
- Covariates and annotations: let family tag weeks (visitor, holiday, illness, new medication, hospital stay, new item registered, camera off) and exclude or flag them.
- Change in coverage: if covered hours drop more than about 30% week on week, show "not enough data this week" instead of a trend.
- Novelty: expect question rates to fall after the first weeks as the system becomes routine, and expect them to rise when new items are registered; neither is a change in the person.
- Minimum data (rough, to be validated): at least 20 wearer questions and 30 put-downs per 4-week window before computing rates; at least 10 stays per item before showing its entropy.

### Gaps
- No study reported false-alarm rates for personal-baseline alerts in family-facing dementia monitoring.
- No validated minimum monitoring duration for object or question metrics exists; ORCATECH's evidence says only that two weeks was too short.
- I did not find published effect sizes for week-to-week variability of question counts, which a proper CUSUM threshold would need.

## 5. Using the data to improve Save It itself

### Takeaway
The same tables can make Save It better at its main job: learning per-item place priors for "where to look" ranking, calibrating confidence with found and not-found outcomes, and detecting perception errors.
These are standard statistical techniques; nothing here needs clinical validation, and they are the safest analytics to build first.

### Cited Findings
- Modern neural networks are often poorly calibrated, and simple temperature scaling fixes much of it; reliability diagrams and expected calibration error are the standard checks - [Guo et al. 2017, "On Calibration of Modern Neural Networks", arXiv](https://arxiv.org/abs/1706.04599)
- The Dirichlet-multinomial is the conjugate model for category counts with a Dirichlet prior, giving smoothed posterior shares from few observations - [Dirichlet-multinomial distribution](https://en.wikipedia.org/wiki/Dirichlet-multinomial_distribution)
- The Brier score is the mean squared error of probabilistic predictions of binary outcomes and is decomposable into calibration and refinement - [Brier score](https://en.wikipedia.org/wiki/Brier_score)
- Ego4D-style episodic memory systems localise "where did I leave X" answers in first-person video, and the best 2024 challenge entries reached only about 23% recall at 1, showing perception from worn cameras is still error-prone - [ObjectNLQ, Ego4D Episodic Memory Challenge 2024, arXiv](https://arxiv.org/abs/2406.15778)
- CASAS treats item-use sensors as presence indicators during tasks, the closest prior analogue to Save It's per-place item states - [CASAS dataset](https://zenodo.org/records/15713579/latest)

### Inferences
Place prior per item (for ranked search when the last sighting is old, contradicted or missing):
- For item i and landmark l, posterior share = (alpha x g_l + w_il) / (alpha + sum over l of w_il), where g_l is a global prior (the registered home place gets extra mass; same-category items' habits next), w_il is a recency-weighted count of confirmed stays (weight exp(-age / tau), tau about 14 days), and alpha about 2-5.
- Condition on time of day with four buckets (night, morning, afternoon, evening) by keeping separate counts and backing off to the pooled counts when a bucket has fewer than about 5 stays.
- Use `misses` as negative evidence: multiply a landmark's weight by a factor (for example 0.3) for a few hours after a miss, so the agent does not send the person back to the same empty place.
- Use `record_outcome(found)` as the strongest positive label: when the person says where it was found, log it as a stay (event_type told by caller), which feeds the prior.
- Blend with recency: if there is an active sighting under a few hours old with good confidence, say it; otherwise read the top 2-3 places from the posterior ("usually your nightstand or the kitchen counter").
- Evaluate offline by replaying history: hit@1 and hit@3 of the ranked list against the eventual found place, compared with the current `item_usual_places` share.

Confidence calibration:
- Log for each answered question the model confidences (`det_conf`, `room_conf`, `id_conf`), the age of the sighting, the state, and the outcome.
- Fit a small logistic model of P(found | features) and check calibration with a reliability diagram and Brier score each month.
- Use the calibrated probability, not raw detector confidence, to choose the spoken hedge (for example over 0.8 say it plainly, 0.5-0.8 say "I think", under 0.5 offer the usual places).
- Beware selection bias: outcomes exist only when "did you find it?" was asked and answered.

Perception-error detectors (operations dashboard, not caregiver view):
- Tentative stays that never confirm, per landmark and per item (false detections or flicker).
- Contradicted rate per landmark (a landmark that is "seen empty" often may be misrecognised).
- Impossible room jumps: consecutive observations in rooms not linked in `room_links` within seconds.
- Same item active in two places within a short window.
- Confident `seen` answers followed by `not_found`: sample their crops for human review.
- Drift in `room_conf` distribution per room after lighting or furniture changes.
- Low `id_conf` crops queued for a family "is this Mum's glasses?" confirmation, which doubles as labelled data.

### Gaps
- No published work found on calibrating voice-agent object-location answers with user-reported outcomes; the design above is standard practice transferred, not tested on Save It data.
- The best recency half-life and time-of-day granularity are unknown and need tuning on real data.

## 6. What dementia caregivers want from monitoring technology, what they reject, and which dashboard views follow

### Takeaway
Caregivers want targeted, easy-to-read information about safety and daily rhythm that supports action, with summaries and graphs they can show professionals, and they fear information overload, false alarms and not knowing whether to act.
Trials of remote activity monitoring found no direct effect on caregiver outcomes and frequent disengagement (sensors turned off, alerts ignored), so Save It's dashboard should lead with reassurance and concrete help, and alert only on sustained change.
Cameras are less accepted than ambient sensors, which makes Save It's "no full frames, crops only, no bathroom" design central to acceptance.

### Cited Findings
Scale of the caregiving problem:
- In 2026 an estimated 7.4 million Americans aged 65 and older live with Alzheimer's, and nearly 13 million people provide unpaid dementia care, more than 19 billion hours in 2025 valued at more than $446 billion - [Alzheimer's Association, 2026 Facts and Figures](https://www.alz.org/alzheimers-dementia/facts-figures)
- 59% of dementia caregivers report high to very high emotional stress - [Alzheimer's Association, 2026 Facts and Figures](https://www.alz.org/alzheimers-dementia/facts-figures)
- AARP and the National Alliance for Caregiving estimate 63 million US family caregivers in 2025, a 45% increase over a decade - [AARP, Caregiving in the US 2025](https://www.aarp.org/caregiving/basics/caregiving-in-us-survey-2025/)
- A secondary summary of that report says 41% of family caregivers use technology to track the recipient's health records, up from 30% in 2020 - [ZenCaregiving summary, not verified against AARP text](https://zencaregiving.org/caregiving-statistics-us-2025/)

What caregivers want:
- Formal and informal caregivers saw unobtrusive monitoring as most useful for falls risk, day and night rhythm, personal hygiene, nocturnal restlessness, and eating and drinking - [JMIR Aging 2021](https://aging.jmir.org/2021/2/e26875/)
- Informal caregivers found it hard to explain daily challenges to others and felt monitoring graphs "would speak for themselves"; the study recommends summaries caregivers can understand intuitively - [JMIR Aging 2021](https://aging.jmir.org/2021/2/e26875/)
- The same study expected information overload and uncertainty about whether to act on data to be barriers, and most informal caregivers were willing to share monitoring information with formal caregivers - [JMIR Aging 2021](https://aging.jmir.org/2021/2/e26875/)
- A small interpretative study of family caregivers found themes of risk-benefit trade-off, usability and the need for tailored solutions - [Remote Monitoring Technologies in Dementia Care, IPA study](https://www.researchgate.net/publication/368008128_Remote_Monitoring_Technologies_in_Dementia_Care_An_Interpretative_Phenomenological_Analysis_of_Family_Caregivers'_Experiences)

What fails:
- In an 18-month embedded mixed-methods RCT with 171 family caregivers, remote activity monitoring had no direct effect on caregiver self-efficacy, competence or distress, and the authors suggest pairing technology with human care management - [Gaugler et al. 2021, Innovation in Aging](https://pmc.ncbi.nlm.nih.gov/articles/PMC8679209/)
- In the mixed-methods evaluation of that program, many caregivers either turned off the sensors or did not respond to alerts by changing day-to-day care - [Gaugler et al., PubMed 34922475](https://pubmed.ncbi.nlm.nih.gov/34922475/)
- Caregivers' reactions to alerts depended on alert utility, accuracy and delivery type - [Zmora et al. 2021](https://experts.umn.edu/en/publications/dementia-caregivers-experiences-and-reactions-to-remote-activity-/)
- Repetitive questioning, the behaviour Save It absorbs, was the most frequent agitated behaviour (94.8%) and agitation tracked caregiver burden, anxiety and depression - [Grossberg et al.](https://www.hmpgloballearningnetwork.com/site/altc/news/agitated-behaviors-alzheimer-disease-strongly-linked-caregiver-burden-us-survey)

Acceptance of cameras:
- In a 2023 survey of 400 older single and couple households in Japan, cameras and microphones met more resistance than door, temperature or gas sensors - [Igarashi and Nihei 2023, Sensors](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10305305/)
- Acceptance of video monitoring falls as the room is perceived as more private, with living room, home office and kitchen most accepted, and acceptance rises when people feel in control - [Maidhof et al. 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10352951)
- In a Swiss telephone survey (N = 1,211), over 80% accepted wearables for locating people with dementia or detecting falls, about 60% home sensors for detecting changes, and about 35% cameras for recognising falls or pain - [Swiss survey listing](https://www.synapsesocial.com/papers/696c79cde45ebfc9113cd561)

### Inferences
Dashboard views that follow from the evidence (proposals):
1. "Today" card, plain language, reassurance first: "Mum asked about 3 things today. All were found. Her glasses were last seen on the nightstand at 4:10 pm." Missing data stated plainly ("the camera was off from 1 pm to 3 pm").
2. Item cards: last confirmed crop photo, place, relative time, and a small bar of "usual places" (`item_usual_places`), so family can search and can calmly answer "someone took my purse" with "it's usually in the hall drawer".
3. "Where things end up" list: this week's unusual places, which doubles as practical advice (put a hook by the door, a tray on the nightstand).
4. Questions this week: one sparkline per top item with the personal baseline band shaded, no red colouring; a short sentence only when a change is sustained.
5. Time-of-day heatmap (hour by weekday) of wearer questions, to plan visits and help around hard times; titled "When questions come up", not "sundowning".
6. "Did it help?" panel: found rate and time to find, which reassures family that the tool works and gives the team a quality metric.
7. Shareable monthly summary (PDF or link) with 3-4 graphs and family notes, for a doctor's or care manager's visit, matching the "graphs speak for themselves" finding.
8. Alert settings owned by the family: off by default, weekly digest by default, optional notice only for sustained change; quiet hours; who receives what.
9. Transparency page for the person wearing the camera: what is stored (crops only), what is never stored (full frames, bathroom), pause button, and who can see it.

What to leave out: live video, continuous location dots, per-minute timelines as the default view, risk scores, and any colour coding that implies "bad" weeks.

### Gaps
- No caregiver study specifically about object-finding or question-log dashboards was found; the views above extrapolate from general monitoring studies.
- No study found that measured whether giving caregivers question-count trends changes burden or care decisions.
- The AARP technology statistic was seen only in a secondary summary.

## 7. Ethics and regulation: when do these analytics become a medical device claim, and how to phrase insights without diagnosing?

### Takeaway
Under FDA's January 2026 guidances, Save It stays outside device regulation as long as its intended use is finding belongings and keeping family informed about everyday routines, with no reference to a disease, no "abnormal" labels and no clinical thresholds.
Any analytics marketed to detect, screen for or monitor cognitive decline or dementia would be a device function, and the clinical decision support exemption does not help, because it covers only software for health care professionals and excludes analysis of patterns from signal-acquisition systems.
Separately, as a health app outside HIPAA, Save It likely falls under the FTC Health Breach Notification Rule (whether it counts as a personal health record vendor was not checked); it should say "built with HIPAA-style safeguards" and make no claim of HIPAA compliance.

### Cited Findings
FDA general wellness guidance (issued 6 Jan 2026, superseding the 2019 version):
- Software "intended for maintaining or encouraging a healthy lifestyle" and unrelated to "the diagnosis, cure, mitigation, prevention, or treatment of a disease or condition" is excluded from the device definition under FD&C Act section 520(o)(1)(B) - [FDA, General Wellness guidance page](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/general-wellness-policy-low-risk-devices)
- A general wellness product has either an intended use relating to "a general state of health or a healthy activity", or one relating healthy lifestyle to reducing the risk or impact of chronic conditions where that link is "well understood and accepted" - [FDA General Wellness guidance PDF, 2026](https://www.fda.gov/media/90652/download)
- First-category claims include "mental acuity" and "sleep management, such as to track sleep trends", and "Claims to improve mental acuity, instruction following, concentration, problem-solving, multitasking, resource management, decision-making, logic, pattern recognition, or eye-hand coordination" - [FDA General Wellness guidance PDF](https://www.fda.gov/media/90652/download)
- Counter-examples outside general wellness include "A claim that a computer game will diagnose or treat autism" and claims to restore a function impaired by disease - [FDA General Wellness guidance PDF](https://www.fda.gov/media/90652/download)
- The guidance's examples of chronic conditions where lifestyle links are accepted are heart disease, high blood pressure and type 2 diabetes, with disease-related claims phrased as "may help living well with" a condition - [FDA General Wellness guidance PDF](https://www.fda.gov/media/90652/download)
- For non-invasive sensing products, the 2026 guidance says they "may display values, ranges, trends, baselines, or longitudinal summaries", but are not general wellness if labeling, interface or functionality includes "references to specific diseases, clinical conditions, or diagnostic thresholds", alerts that "recommend or require specific clinical action", or intended-use statements targeting "diagnosis, screening, monitoring, or management of a disease or condition" - [FDA General Wellness guidance PDF](https://www.fda.gov/media/90652/download)
- A product may still be general wellness if it notifies that "evaluation by a healthcare professional may be helpful", provided the notice does not name a disease, does not call the output "abnormal, pathological, or diagnostic", includes no clinical thresholds, and provides no ongoing disease-management alerts - [FDA General Wellness guidance PDF](https://www.fda.gov/media/90652/download)

FDA clinical decision support guidance (2026):
- Non-device CDS must meet all four criteria: (1) not acquire, process or analyze a medical image, IVD signal, or "a pattern or signal from a signal acquisition system"; (2) display, analyze or print medical information; (3) support or provide recommendations "to a health care professional"; (4) let that professional independently review the basis - [FDA CDS guidance PDF](https://www.fda.gov/media/109618/download)
- "Software functions that support or provide recommendations to patients or caregivers - not HCPs - meet the definition of a device", with FDA pointing to its other policies (including general wellness) for such software - [FDA CDS guidance PDF](https://www.fda.gov/media/109618/download)
- FDA interprets "pattern" as "multiple, sequential, or repeated measurements of a signal or from a signal acquisition system" - [FDA CDS guidance PDF](https://www.fda.gov/media/109618/download)
- Activity monitors and other signal-acquisition systems not intended or marketed for a medical purpose are not medical devices - [FDA CDS guidance PDF](https://www.fda.gov/media/109618/download)
- The CDS PDF header says "Document issued on January 29, 2026", while law-firm commentary describes both guidances being released on 6 January 2026 without public comment, so the CDS document may have been reissued - [FDA CDS guidance PDF](https://www.fda.gov/media/109618/download); [Faegre Drinker, Jan 2026](https://faegredrinker.com/en/insights/publications/2026/1/key-updates-in-fdas-2026-general-wellness-and-clinical-decision-support-software-guidance)
- The main 2026 CDS change is that FDA no longer excludes per se software supporting time-critical HCP decisions and eases enforcement for CDS recommending a single diagnosis or treatment to an HCP - [Faegre Drinker](https://faegredrinker.com/en/insights/publications/2026/1/key-updates-in-fdas-2026-general-wellness-and-clinical-decision-support-software-guidance)
- Neither 2026 guidance expressly changes FDA's approach to AI - [Arnold & Porter, Jan 2026](https://www.arnoldporter.com/en/perspectives/advisories/2026/01/fda-cuts-red-tape-on-clinical-decision-support-software)

Privacy regulation outside HIPAA:
- The FTC's amended Health Breach Notification Rule (vote 26 Apr 2024, effective 29 Jul 2024) covers most health apps and similar technologies not covered by HIPAA, and treats unauthorized disclosures to third parties as breaches - [Covington Inside Privacy, 2024](https://www.insideprivacy.com/health-privacy/ftc-issues-final-rule-to-expand-scope-of-the-health-breach-notification-rule/)

Ethics:
- The need for monitoring rises as dementia progresses while the ability to consent decreases, and long-term video surveillance is considered socially and ethically problematic - [BMC Medical Ethics 2019](https://link.springer.com/doi/10.1186/s12910-019-0437-z)
- Carers have been found to consider home surveillance ethically acceptable despite privacy concerns - [BMC Medical Ethics 2019](https://link.springer.com/doi/10.1186/s12910-019-0437-z)
- A qualitative study argues for moving beyond the "safety versus autonomy" framing of surveillance in dementia care - [Hall et al. 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6534927)
- A 2026 scoping review in The Gerontologist covers ethics of home monitoring for people with cognitive impairment (not read) - [Wang et al. 2026, doi 10.1093/geront/gnaf261](https://doi.org/10.1093/geront/gnaf261)

### Inferences
Intended-use statement that keeps Save It in the non-device lane: "Save It helps a person find everyday belongings and helps family stay informed about everyday routines."
Analytics such as "MCI risk", "cognitive decline score", "progression tracking" or "early detection" combine a worn-camera signal pattern with a disease purpose and a caregiver audience, which fails CDS criteria 1 and 3 and exceeds general wellness, so they should exist only as IRB-approved research with consent, not in the product.

Phrasing guide:

| Avoid | Prefer |
|---|---|
| "Signs of cognitive decline", "memory score", "MCI risk", "dementia progression" | "Asked about her glasses 9 times this week; she usually asks about 4 times" |
| "Abnormal", "worsening", "alert: decline detected" | "This is a change from her usual pattern" |
| "Sundowning detected" | "Most questions came between 5 and 8 pm this week" |
| "Naming difficulty" or "anomia" for unknown items | "Save It did not recognise 3 requests; you can add these words as nicknames" |
| "Contact her doctor now" | "If this continues, you may want to mention it at her next appointment" (no disease named, no threshold) |
| Any claim of HIPAA compliance | "Built with HIPAA-style safeguards" |
| "Clinically validated", "medical-grade" | "Based on what the camera saw and what she asked" |

Ethical design points for analytics:
- Ask the person wearing the camera for consent while they can give it, record it, and revisit it; let them see their own summary and pause capture.
- Data minimisation already in place (crops only, no full frames, no bathroom rows) should extend to analytics: aggregate before display, keep raw `heard` text access limited, and set retention limits on `queries.heard` and crops.
- Do not rank or compare the person against others or norms; show only their own history.
- Avoid analytics that could be used against the person (for example in guardianship or driving disputes) without their agreement; say so in the privacy notice.
- Breach readiness: an incident plan that meets FTC Health Breach Notification Rule timelines, and no third-party analytics SDKs on the dashboard that would count as unauthorized disclosure.

### Gaps
- No FDA statement addresses object-finding or question-log analytics specifically; the analysis above applies general text and is not legal advice.
- Whether a worn phone camera used for object finding counts as a "signal acquisition system" depends on intended use; FDA invites manufacturers to engage when a system is repurposed, and a regulatory attorney should confirm before any clinical-sounding feature.
- I could not read the 2026 Gerontologist scoping review, and I could not confirm the source of a frequently cited claim that most dementia assistive technologies are designed without explicit ethical assessment.
- State privacy laws (for example Washington's My Health My Data Act) were not researched.
