# Save It catches sudden change, not slow decline

Save It's strongest medical use is not tracking slow Alzheimer's decline but noticing when a person's everyday memory behaviour changes unusually fast, and giving the family and the clinician a dated record of when the change started and how fast it moved.
A rough power estimate on assumed noise suggests one weekly metric needs about **1-2 years** to separate a typical 3-MMSE-point-a-year decline from noise, but only **2-3 days** to see daily questions double.
Fast change is where the stakes are: delirium affects about **30% of community-dwelling people with dementia**, is missed in more than half of cases, and roughly doubles the later rate of decline ([Burnand et al. meta-analysis](https://www.citedrive.com/en/discovery/the-prevalence-and-incidence-of-delirium-superimposed-on-dementia-in-community-settings-a-systematic-review-and-metaanalysis/); [Inouye et al. 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4120864/)).
The tables already hold passive, timestamped versions of validated informant questions (ECog "where he/she has placed objects" and "repeating questions", AD8 item 3, ADCS-ADL item 11, RMBPC item 1), but no published study has used object put-downs or "where is my X?" questions as a clinical measure, so every metric here is new and unvalidated.
FaceTime calls add interaction signals (re-asking after a confident answer, clarification turns, reply latency), not voice biomarkers: those need minutes of speech and are distorted by speech-recognition errors that themselves rise with dementia.
Clinicians would use the data as a one-page monthly summary that the caregiver brings to a cognitive care-planning visit (CPT 99483) or a CMS GUIDE dementia program such as Emory Integrated Memory Care, not as a live feed: **97% of physicians review wearable data in some way, but in no country do more than 6% build it into their workflow** ([Fierce Healthcare](https://www.fiercehealthcare.com/health-tech/doctors-want-wearable-data-healthcare-isnt-ready-it-ama-survey-finds)).
Under the FDA's January 2026 wellness guidance, Save It may show values, trends and baselines, but naming a disease, using clinical thresholds or sending alerts that call for clinical action ("possible delirium", "decline detected") would make it a medical device, and proper validation is a staged study lasting years.
On safety, automatically calling 911 when a FaceTime caller falls is the wrong design.
The responsible pattern, used by Apple, Amazon and professional monitoring centers, is to confirm with the person and then alert a human who decides.
With the demo freeze hours away, the best returns are a phrasing guide and an evidence slide, a prompt-level distress and scam tool, and two or three SQL views, with the clinical story pitched as future research.

## Save It's logs match validated memory questions, but no one has tested them passively

Misplacing things and repeating questions are among the most common problems families report, not side issues.
In 130 people with mild-to-moderate Alzheimer's disease interviewed for the VISTA trial, **74% misplaced objects recurrently, and for 81% of them the problem was not remembering where an item had been put down**, which is exactly the event Save It records ([Hamilton, Fay and Rockwood 2009](https://latam-cl.demo.elsevierpure.com/fr/publications/misplacing-objects-in-mild-to-moderate-alzheimers-disease-a-descr)).
In the same sample, 25 of 96 put objects in unusual places, and 31 of the 56 who knew they misplaced things were distressed by it.
Among 787 online symptom-tracker users who followed misplacing, 56% tracked "odd places", and odd places became significantly more common as dementia severity rose ([McGarrigle et al. 2019](https://resolve.cambridge.org/core/journals/international-psychogeriatrics/article/characterizing-the-symptom-of-misplacing-objects-in-people-with-dementia-findings-from-an-online-tracking-tool/9CD88B66B66EB8D98FD9430893378794)).
Repetitive questioning is reported in 31% to 90% of people with dementia, depending on the definition, makes up 90.8% of tracked verbal repetition, appears early, and is not clearly tied to MMSE score ([Reeve et al. 2017](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/28BB08AD166CF991B27E79F371CF2F0A/S1041610216002180a.pdf/exploration_of_verbal_repetition_in_people_with_dementia_using_an_online_symptomtracking_tool.pdf)).
In a survey of 250 US family caregivers it was the most common agitated behaviour (94.8%), and every 5-point rise on the agitation scale (CMAI) came with 19% higher odds of high caregiver burden ([Grossberg et al.](https://www.hmpgloballearningnetwork.com/site/altc/news/agitated-behaviors-alzheimer-disease-strongly-linked-caregiver-burden-us-survey)).

Clinicians already ask family members about these exact behaviours.
The Everyday Cognition scale (ECog) memory section asks about "remembering where he/she has placed objects" and "repeating stories and/or questions"; ECog-II rewords the second as "unknowingly repeating" them multiple times ([Farias et al. 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC8387334)).
The AD8 screen asks whether the person repeats "questions, stories, or statements" ([AD8 form](https://alz.org/getmedia/6e7291bf-4ac8-40ed-a148-824d4591ed7e/ad8-dementia-screening.pdf)).
Item 11 of the ADCS-ADL activities scale asks whether the person found their belongings at home without help, with supervision or with physical help ([ADCS-ADL form](https://dementiaresearch.org.au/wp-content/uploads/2016/01/ADCS-ADL_Form.pdf)).
Item 1 of the Revised Memory and Behavior Problems Checklist (RMBPC) rates "repetitive questions" on a 0-4 weekly frequency scale ([RMBPC factor table](https://pmc.ncbi.nlm.nih.gov/articles/PMC2579275/table/T3)).
These family reports predict real outcomes: in the Sydney Memory and Ageing Study (873 adults followed for six years), each point on a family-rated memory-complaint index raised the fully adjusted hazard of dementia by a factor of **1.20**, and only the family-rated indices held up after adjusting for mood and personality ([Numbers et al. 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7217434/)).
Save It's `sightings` and `queries` tables are therefore a passive, timestamped version of questions clinicians already trust, and that is the strongest argument for the medical angle.
Two cautions come with it.
The AD8 is copyrighted and may not be modified or used to derive a score without Washington University's permission ([Knight ADRC AD8 worksheet](https://knightadrc.wustl.edu/app/uploads/2021/06/AD8-Worksheet-English-2005.pdf)).
And the Sydney result argues for pairing Save It's numbers with a short caregiver check-in, not replacing it.

The research stops short of Save It's exact signal.
The validated passive markers from the long-running home-sensor studies (ORCATECH and CART) are mobility, walking speed, how regular room-to-room movement is, sleep and time out of the home.
In those studies, less regular day-to-day room transitions were linked to mild cognitive impairment (MCI) (adjusted beta -0.04, p = 0.03), while raw transition counts were not ([Wu et al. 2021](https://www.frontiersin.org/journals/digital-health/articles/10.3389/fdgth.2021.764510/full)), and two weeks of monitoring was not enough to predict MCI ([Alzforum](https://alzforum.org/node/1226746)).
The closest work on voice-assistant logs is an 18-month Alexa pilot in which 15 people's commands at home told MCI apart from healthy users with an **F1 score of 72.67%** ([Cog-TiPRO, Qi et al. 2025](https://arxiv.org/abs/2505.17137)).
The closest product is MIT's MemPal, a neck-worn phone camera that answered "where is my X?" with 72% spoken-answer accuracy for 15 older adults ([MemPal](https://arxiv.org/html/2502.01801v1)).
A 2017 Cochrane review found **no randomised trials at all** of assistive technology for memory support in dementia ([Cochrane CD009627](https://www.cochrane.org/evidence/CD009627_assistive-technology-memory-support-dementia)).
No study has passively measured search time, how often things are misplaced, or how consistently things are put down in real homes, and related it to cognitive status.

Save It's data has three properties no questionnaire can match.
First, it cleanly separates Hamilton's two kinds of misplacing.
A question about an item last put down in its usual place is "forgot where"; a put-down on a landmark that item never visits is "odd place".
That split mirrors the clinical distinction between a memory failure and a planning or self-monitoring failure.
Second, it can measure the time between putting something down and asking where it is, which no existing instrument captures.
Third, every event is timestamped, so it can answer a clinician's first question about any change, "when did this start, and how fast?", which families often cannot answer.
The trap is direction.
Repetition shows up early, and later stages bring apathy and loss of initiative ([Reeve et al. 2017](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/28BB08AD166CF991B27E79F371CF2F0A/S1041610216002180a.pdf/exploration_of_verbal_repetition_in_people_with_dementia_using_an_online_symptomtracking_tool.pdf)).
So a long-term fall in questions can mean the person no longer starts calls, can no longer manage FaceTime, or is in hypoactive delirium, not that their memory improved.

## Speed of change, not level, is what the data can see

### Typical decline stays hidden in one metric's noise for 1-2 years

Untreated Alzheimer's disease costs on average **3.3 MMSE points a year (95% CI 2.9-3.7)** ([Han et al. 2000](https://pubmed.ncbi.nlm.nih.gov/10937543)).
Individual rates vary so much that 15.8% of 372 patients in the CERAD study showed no clinically meaningful decline after four years, and the authors judged the MMSE of little use for tracking one person over less than three years ([Clark et al. 1999](https://scholars.duke.edu/publication/740187)).
"Rapid cognitive decline" has no agreed definition.
The common cut-off of 3 or more MMSE points a year labelled 45.9% of one clinic cohort as rapid ([Barbe et al. 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC5216188)), while a cut-off of 6 or more labelled 12% of the 1,005-patient ICTUS cohort ([Canevelli et al.](https://research.stmarys.ac.uk/2386/3/Canevelli-et-al-Predicting-the-Rate-of-Cognitive-Decline.pdf)).
The smallest change that matters clinically in mild Alzheimer's disease is about 2 MMSE points or 2 CDR-SB points (CDR Sum of Boxes, a dementia staging score) ([Muir et al. 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11095473/)).

The notes' power estimate has to assume a week-to-week coefficient of variation (CV) of 0.3-0.5, because nobody has measured one for this kind of data.
On that assumption, detecting a step change of relative size d with 80% power takes roughly n = 6.2 x CV^2 / d^2 weeks of data after the change.
At CV 0.5, a 50% step takes about 6 weeks and a 25% step about 25 weeks.
A slow drift of 20% of baseline per year takes about **77-108 weeks** of clean data to detect.
For acute change, daily counts carry more information: if someone normally asks 3 questions a day and that doubles to 6, a Poisson z-score passes 2.5 after about 2 days and 3.0 after about 3.
Save It is therefore far better placed to notice acute and medium-term change than slow decline.
And because no mapping exists from any Save It metric to MMSE, CDR-SB or ADAS-Cog, it must never report "points" or call a change "clinically meaningful".

### Delirium is the most actionable target, and the easiest to over-read

Delirium on top of dementia is common, dangerous and often missed.
A meta-analysis of 27 community studies put its prevalence at **30.2%** ([Burnand et al.](https://www.citedrive.com/en/discovery/the-prevalence-and-incidence-of-delirium-superimposed-on-dementia-in-community-settings-a-systematic-review-and-metaanalysis/)).
It develops over hours to days, comes and goes, and is missed, caught late or misdiagnosed in over half of cases, the hypoactive (quiet, withdrawn) form most of all ([BMJ Open 2013](https://pmc.ncbi.nlm.nih.gov/articles/PMC3549230)).
In dementia cohorts, delirium raised the relative risk of death to **5.4** and of moving into institutional care to **9.3** ([Inouye et al. 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4120864/)).
In the Massachusetts ADRC registry, decline on the Blessed memory test rose from **2.5 to 4.9 points a year** after an episode of delirium ([Fong et al. 2009](https://pubmed.ncbi.nlm.nih.gov/19414723/)).
Among 1,870 Chicago residents, a first hospital stay made cognitive decline 2.4 times faster ([Wilson et al. 2012](https://pmc.ncbi.nlm.nih.gov/articles/PMC3310309)).
NICE guidance asks staff to look for changes or swings in behaviour that appear within hours or days, as reported by the person, a carer or a relative, and to watch for easily missed hypoactive signs such as withdrawal, slow responses and moving less ([NICE CG103](https://www.nice.org.uk/guidance/cg103/chapter/1-Guidance)).
That is the same timescale and the same family-observer role Save It already fills.

The best passive-sensing evidence shows both the promise and the limits.
The UK Minder programme followed 117 people with dementia for 27,828 person-days.
Using bathroom-visit patterns and night-time breathing, it detected urinary tract infections in participants it had not been trained on with **65.3% sensitivity and 70.9% specificity**, rising to 74.7% and 87.9% after risk stratification, and it sent alerts to clinicians rather than families ([Capstick et al. 2024](https://ukdri.ac.uk/publications/digital-remote-monitoring-screening-and-early-detection-urinary-tract-infections)).
Save It collects neither of those inputs: bathrooms are `capture_allowed = false` and must never produce a row, and there is no bed sensor.
Even at Minder's best accuracy, if 2% of person-days were true infection days (an assumption), only about 11% of alerts would be real, or about 25% at a 5% base rate.
That is why Minder routes alerts to a clinical team, and why a family-facing Save It alert would quickly cause alarm fatigue unless it is rare, sustained, and worded as a change from usual.
No study has yet checked passive home data against clinically diagnosed delirium, and a 2026 proof of concept in 17 people with dementia says so explicitly ([JMIR Formative Research 2026](https://formative.jmir.org/2026/1/e93258)).
Confusion alone also does not justify assuming a urinary infection, since bacteria in the urine without urinary symptoms have not been shown to cause delirium ([AAFP 2020](https://www.aafp.org/afp/2020/0715/p99.html)).

Delirium also defeats a simple "spike detector".
Hyperactive or mixed delirium would likely show up over 1-3 days as more questions per covered hour, more repeats within minutes of a `seen` answer, more `not_found` outcomes even after correct answers, more `unknown_item` mishearings, and more activity at odd hours.
Hypoactive delirium, which is more common in older people and has the worse outlook ([Inouye et al. 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4120864/)), would show the opposite.
Questions and put-downs would fall, the person would stay in fewer rooms, and wear time would drop suddenly because the lanyard never goes on.
The detector therefore has to look for change in both directions, combine several signals, and treat a drop in coverage as information rather than missing data.

### Change over weeks is the classic red flag for treatable causes

Rapidly progressive dementia develops over weeks to months rather than years.
In specialist case series, **17% (UCSF) to 27% (Athens) of referrals had potentially treatable causes** such as autoimmune, infectious or toxic-metabolic disease, and starting immune treatment sooner generally gave better outcomes ([Paterson, Takada and Geschwind 2012](https://pmc.ncbi.nlm.nih.gov/articles/PMC3613204)).
Of 72 Mayo Clinic patients treated for suspected autoimmune dementia, 64% improved, and 35% of those who improved had first been diagnosed with a neurodegenerative or prion disease ([Flanagan et al. 2010](https://mayoclinic.elsevierpure.com/en/publications/autoimmune-dementia-clinical-course-and-predictors-of-immunothera)).
The useful quantity for Save It is the ratio of this week's change to the person's own usual week-to-week change.
The pattern that would justify a prompt review is a 2-8 week rise in questions, a falling found rate, more odd-place put-downs and a shrinking room range, with no obvious acute trigger.
Save It cannot tell rapidly progressive dementia apart from delirium, depression, a new drug, a house move or a camera fault, and should not try.
What it can honestly say is "this is a faster change than we have seen before", and hand over the dated timeline for a clinician to interpret.

### Repetition and medication give the clearest causal hooks

Repeat-question rate is the metric most likely to respond to treatment.
In the VISTA trial, **58% of patients on galantamine versus 24% on placebo repeated themselves less** after four months, and the change matched clinicians' judgement rather than standard test scores ([Rockwood et al. 2007](https://www.epistemonikos.org/en/documents/4db071bba50da8ff358bfec06ca7fd6309e64561)).
In a small study, seven spouses trained to use written cues also cut their partners' repetitive talk compared with seven controls ([Bourgeois et al. 1997](https://gerontologist.gerontologyjournals.org/cgi/content/abstract/37/1/30)).
Medication changes are also a leading trigger of acute change.
Among 1,105 community-dwelling adults with cognitive impairment, heavy combined use of anticholinergic and sedative drugs came with a **4.09-fold** higher risk of delirium ([Int J Clin Pharm 2023](https://pubmed.ncbi.nlm.nih.gov/36933080/)), which makes "new medicine" the single most valuable thing a family can tag.
Behaviour cannot monitor anti-amyloid therapy, though.
In the Clarity AD trial, brain swelling (ARIA-E) occurred in 12.6% of lecanemab patients but caused symptoms in only 2.8%, so most episodes are silent ([PMC11084061](https://pmc.ncbi.nlm.nih.gov/articles/PMC11084061/); [NeurologyLive](https://neurologylive.com/view/lecanemab-represents-promising-therapy-alzheimer-disease-clarity-ad)), and scheduled MRI is the monitoring standard ([Alzheimer's Association clinical workflow](https://alz.org/media/Documents/lecanemab-toolkit-clinical-workflow.pdf)).
Any feature presented as "ARIA monitoring" would be a medical device, and dangerous if families trusted it over scans.
Fluctuation is another possible signal.
It is a core feature of dementia with Lewy bodies and of delirium, and reaction-time variability in Lewy body dementia is reliable over 12 weeks (ICC at least 0.85) ([J Neurol 2022](https://link.springer.com/article/10.1007/s00415-022-10977-4)).
But no study shows that day-to-day variability in everyday behaviour tracks decline in people already diagnosed with dementia, so variability metrics belong in research and need longer windows than averages.

| Timescale and likely cause | How it might look in Save It data (untested) | How a clinician reads it | Wording Save It can use |
|---|---|---|---|
| Hours to days: hyperactive or mixed delirium, or a new anticholinergic or sedative drug | Sharp, bursty rise in questions and repeats; found rate falls even after correct answers; activity at odd hours | Delirium until proven otherwise; look for infection, dehydration, constipation, pain, urinary retention, new drugs; screen with the 4AT test | "She asked about four times more than usual since Tuesday" |
| Hours to days: hypoactive delirium | Fewer questions and put-downs, fewer rooms used, wear time drops | Same, and the form most often missed | "Fewer calls and less moving about than usual since Tuesday" |
| Hours, tied to events: anxiety | Bursts before appointments or visits, or in the evening | Non-drug strategies: written cues, planning around triggers | "Most questions came the morning of her appointment" |
| Weeks to a few months, no trigger: rapid decline or rapidly progressive dementia | Sustained rise in questions and odd places, falling found rate, more `unknown_item` | Unusually fast for Alzheimer's; consider tests for other, sometimes treatable, causes | "This is a bigger change over six weeks than we have seen before" |
| 1-4 months after starting a cholinesterase inhibitor | Possible fall in the repeat-after-answer rate | Small average effect; no change means little | Trend line only |
| Months to years: expected progression | Slow drift, mostly within the noise | A conversation aid alongside MoCA or CDR | Trend lines with uncertainty bands, no alerts |

## Thirteen metrics run on today's tables, all divided by coverage

Every metric below runs on today's schema (migrations `0001` and `0003`) and relies on three shared definitions.
"Wearer questions" are `queries` rows with `channel in ('phone','facetime')`.
With Vapi cut (D33), that means `facetime` in practice, and the agent already logs with `channel=facetime`.
`web` rows come from family, the dashboard and tests, and must be reported separately.
"Put-downs" are `sightings` rows with `event_type = 'seen'`, `in_hand = false`, `source = 'worn_cam'` and `status <> 'tentative'`, so only stays confirmed by two frames count.
"Covered hours" are distinct 5-minute blocks with at least one `observations` row.
Five-minute blocks are needed because Gemini writes an observation only when the SAM 3 gate opens on a registered item, or for an empty look at most every 30 seconds, and writes nothing in no-capture or uncertain rooms.
Every count must be divided by covered hours, and coverage is a signal in its own right: ORCATECH found people with MCI wore their watches less ([Alzforum](https://alzforum.org/node/1226746)).

| # | Metric | Definition on the tables | Clinical idea it echoes | Main confounder | Audience |
|---|---|---|---|---|---|
| 1 | Coverage | Distinct 5-minute blocks of `observations.captured_at` per local day (`homes.timezone`), divided by 12 | Wear time; a sudden drop can itself be the change | Charging, camera off; bathrooms and uncertain rooms leave gaps | Everyone, always shown first |
| 2 | Wearer questions per 10 covered hours | Wearer `queries` per day or week, divided by covered hours, times 10; total and per `item_id` | RMBPC item 1, ECog memory item 5, AD8 item 3 | Novelty, newly registered items, questions moving from family to Save It | Family (weekly), clinician page |
| 3 | Repeat-after-answer rate | Share of wearer questions where the previous question about the same `item_id` got a `seen` answer within 10 (and 60) minutes | ECog-II "unknowingly repeating"; responded to treatment in VISTA | Wrong or stale answer, hearing loss, habit of double-checking | Family patterns tab, clinician page |
| 4 | Forgetting latency | `queries.asked_at` minus `sightings.first_seen_at` for the stay in `queries.sighting_id` | Nothing existing; how soon a put-down is forgotten | Unmeasured when nobody asks | Research |
| 5 | Found rate and time to find | `outcome = 'found'` divided by (found + not_found); `outcome_at` minus `asked_at` | ADCS-ADL item 11 | Outcome missing for many calls, biased toward easy cases | Family, product team |
| 6 | Home-place use | Share of an item's weekly put-downs on `items.home_landmark_id` | ECog memory item 4; suggests changes to the home | The family's chosen "home" may not match the person's habit | Family |
| 7 | Odd-place rate | Put-downs on a landmark that holds under about 5% of that item's past stays (smoothed), or a landmark that makes no sense for it (glasses in the fridge) | Alzheimer's Association warning sign 7; odd places rise with severity | Recognition errors look like odd places; require `status = 'active'` and adequate `id_conf` | Family (as tips), clinician page (as examples) |
| 8 | Placement entropy | Shannon entropy of `landmark_id` per item over 28 days, normalised by the log of the number of places used | Like the room-transition regularity measure | Rises with more registered landmarks and more coverage | Research |
| 9 | Misses per place | `misses` rows per `item_id` and `landmark_id` | Old habits; where a label would help | `misses.source` mixes caller, manual and camera entries | Family |
| 10 | `unknown_item` rate | Share of wearer questions with `state = 'unknown_item'` | Weak hint of word-finding trouble | Speech-recognition errors that grow with dementia; unregistered items | Internal only, never labelled as a naming problem |
| 11 | Room range and regularity | Distinct `room_id` per covered day; hourly transitions; week-level regularity | Less regular movement linked to MCI ([Wu et al. 2021](https://www.frontiersin.org/journals/digital-health/articles/10.3389/fdgth.2021.764510/full)) | Worn camera, not fixed sensors; visitors | Research, context |
| 12 | Time-of-day profile | Wearer questions by local hour and weekday against the person's own baseline; night share (22:00-06:00) | Delirium's swings; "sundowning" has no agreed definition ([Frontiers in Medicine 2016](https://www.frontiersin.org/articles/10.3389/fmed.2016.00073/full)) | Lanyard rarely worn at night; idle evenings | Family heatmap titled "When questions come up" |
| 13 | Day-to-day variability | Rolling 14-day standard deviation, or mean absolute difference between consecutive days, of metrics 2, 3 and 5 | Fluctuation in Lewy body disease and delirium | Variability estimates need long windows | Research |

The two queries below show the pattern.
Both were run against an empty scratch database built from migrations `0001` to `0003`; production versions should live as views behind row-level security.

```sql
-- Covered hours per local day: 5-minute bins with at least one processed frame
select (o.captured_at at time zone h.timezone)::date as day,
       count(distinct date_bin('5 minutes', o.captured_at, timestamptz '2000-01-01')) / 12.0 as covered_hours
from observations o
join homes h on h.id = o.home_id
group by 1
order by 1;

-- Weekly share of wearer questions that repeat an item within 10 minutes of a "seen" answer
with q as (
  select q.home_id, q.item_id, q.asked_at,
         lag(q.asked_at) over w as prev_at,
         lag(q.state)    over w as prev_state
  from queries q
  where q.channel in ('phone', 'facetime') and q.item_id is not null
  window w as (partition by q.home_id, q.item_id order by q.asked_at)
)
select date_trunc('week', q.asked_at at time zone h.timezone) as week,
       count(*) as wearer_questions,
       count(*) filter (where q.prev_state = 'seen'
                          and q.asked_at - q.prev_at < interval '10 minutes')::float
         / count(*) as repeat_after_seen_10min
from q
join homes h on h.id = q.home_id
group by 1
order by 1;
```

Three schema gaps matter.
First, `queries` stores `state` but not the `confident` flag that `find_item` returns.
The cleanest version of metric 3, "repeat after a confident answer", needs a `confident` column added in the next numbered migration (applied migrations are frozen); until then, the `seen` state stands in for it.
Second, the `misses` table arrives with migration `0003`, which STATUS still lists as not yet applied to Supabase.
Third, the per-call speech metrics in the next section need a new table that stores numbers only.

The metrics also need a detector that is honest about noise.
The notes propose two tracks, both unvalidated.
The acute track works on daily totals, looks for change in either direction, and combines questions, repeats, found rate, room range and wear time.
It flags only when at least two signals move together for two or more days, or one moves by a large factor.
The slow track works on weekly totals and starts with a 4-week "learning her routine" period; two weeks was too short in ORCATECH.
Its baseline is the median and median absolute deviation (MAD) of the previous 8 weeks, giving a robust score z = (x - median) / (1.4826 x MAD).
Question counts are modelled as negative binomial with covered hours as the exposure, feeding a one-sided CUSUM chart ([NIST CUSUM](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc323.htm)) tuned to roughly one false alert per six months per metric.
A change must persist for 2-3 weeks before it is called a change.
Headline trends should be limited to about three (wearer questions per 10 covered hours, home-place use, repeat-after-answer rate) to keep false alarms from multiple comparisons down.
Rough minimums are 20 wearer questions and 30 put-downs per 4-week window, with a "not enough data" state when coverage falls by more than about 30% from one week to the next.
The evidence on family-facing monitoring argues against anything louder.
In an 18-month randomised trial with 171 family caregivers, remote activity monitoring had no direct effect on confidence, competence or distress, and many caregivers switched sensors off or ignored alerts ([Gaugler et al. 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC8679209/); [Gaugler et al., mixed methods](https://pubmed.ncbi.nlm.nih.gov/34922475/)).

The confounders are bigger than most of the signals.
Save It is itself a memory aid, so it changes what it measures.
Questions move from family to Save It, rates run high in the first weeks, and every newly registered item adds new questions.
That calls for a starting period, per-item normalisation, and a fresh baseline after product changes, including edits to the agent's prompt or voice.
Visitors and people who live with the wearer move things and prompt questions, and passive detection works less well in two-person homes ([Muurling et al. 2023](https://preprints.jmir.org/preprint/45876/accepted)).
Recognition errors can look like clinical change: a missed detection looks like "forgot where", and a misidentified item looks like an odd place.
Answering "where did I leave it" from worn-camera video is still hard, at about 23% top-1 recall on the Ego4D benchmark ([ObjectNLQ](https://arxiv.org/abs/2406.15778)), so quality metrics (tentative stays that never confirm, contradicted rate per landmark) must be watched alongside the clinical ones.
Weather, season and weekday shift daily routines ([Petersen et al. 2015](https://econpapers.repec.org/RePEc:plo:pone00:0139643)).
Family tags (visitor, illness, hospital stay, new medicine, new item, camera off, new hearing aids) are the cheapest way to control for all of this.

## FaceTime calls add interaction timing, not voice biomarkers

Speech analysis can detect dementia, but the evidence is built on long, structured recordings.
A ten-year review found most studies report over 88% accuracy for Alzheimer's disease and over 80% for MCI on tasks such as picture descriptions and interviews ([Martinez-Nicolas et al. 2021](https://www.frontiersin.org/articles/10.3389/fpsyg.2021.620251/full)).
Fraser and colleagues reached about 82% on the DementiaBank picture descriptions with 35 features ([Fraser et al. 2016](https://pubmed.ncbi.nlm.nih.gov/26484921/)).
In the ADReSSo challenge, a fully automatic baseline using only audio and unedited speech-recognition output reached **78.87%** ([Luz et al. 2021](https://arxiv.org/abs/2106.08689v1)).
Telephone audio is good enough: in calls of about 20 minutes with 91 older adults, language models separated mild Alzheimer's, amnestic MCI and healthy controls better than two standard screening tests ([Diaz-Asper et al. 2022](https://doi.org/10.1016/j.cortex.2022.08.005)).
Speech can also track change over time: a Winterlight speech score from staging interviews changed over 18 months by about as much as CDR-SB (beta 0.29 versus 0.30) in 101 people with early Alzheimer's ([Xu et al. 2023](https://rcastoragev2.blob.core.windows.net/8286c328c4b6f1e2ded71401d6057767/DAD2-15-e12445.PMC10286224.pdf)).
The weakness is generalisation: a review found that only 2 of 86 AI models for Alzheimer's had been tested on outside data ([AI4X Roadmap](https://arxiv.org/pdf/2511.20976)).

Save It's calls are the wrong shape for the classic voice markers.
Five-minute samples tracked Alzheimer's-related change more reliably than one-minute samples ([Petti et al. 2023](https://karger.com/dib/article/7/1/157/870178/How-Much-Speech-Data-Is-Needed-for-Tracking)).
About 97% of acoustic voice features did not reproduce across tasks, partly because one task was short ([Almaghrabi et al. 2022](https://doaj.org/article/4f2470feb51d470face5a21ba5ad427d)).
So a 3-second "where are my glasses?" will not give trustworthy measures of pitch, voice tremor (jitter) or vocabulary range.
What survives is behaviour and interaction.
In the 18-month Alexa pilot, the features that separated MCI from healthy users included vague placeholders ("that thing"), bursts of three or more identical requests within 30 seconds, re-asking for the same information right after getting an answer, failing to recover when a command did not work, and very short commands ([Qi et al. 2025](https://arxiv.org/abs/2505.17137)).
In everyday conversation, gaps before replies, long silences and turn length separated Alzheimer's from other patients with 83-90% accuracy ([Nasreen, Hough and Purver 2021](https://www.frontiersin.org/articles/10.3389/fcomp.2021.640669/text)).
Save It's fixed task helps here.
The same request, assistant and answer format repeat many times a week, so each person's interaction measures are more comparable over time than in free conversation, although this setup has never been validated.

Speech recognition makes more mistakes in exactly the people the product is for.
In a study of 83 older adults reading commands to Alexa, recognition errors were significantly higher for people with dementia, and quiet voices, poor voice quality and frequent pauses predicted the errors ([Cohn et al. 2026](https://arxiv.org/abs/2602.23436)).
Five commercial systems averaged a word error rate of 0.35 for Black speakers versus 0.19 for white speakers ([Koenecke et al. 2020](https://ideas.repec.org/a/nas/journl/v117y2020p7684-7689.html)).
A person who speaks quietly or haltingly will therefore trigger more mishearings and more "which one?" questions, which look like word-finding trouble.
So every metric derived from transcripts needs a speech-recognition quality check beside it, and must only ever be compared with the same person's history.
Hearing loss is a second confounder: a caller who cannot hear the agent asks for repeats and answers slowly.
The telephone study that found a speech signal excluded people with poor hearing ([Diaz-Asper et al. 2022](https://ckchandler.github.io/files/publications/diazasper_cortex2022.pdf)).
Logging "asked to repeat the answer" separately from "asked again later" partly separates hearing from memory.
Production speech recognition also tends to drop fillers like "um", so pauses measured from timestamps are more reliable than filler counts in the text.

| Per-call field | How to compute | Source today | Expected value | Main noise |
|---|---|---|---|---|
| `asks_same_item_after_confident_answer` | Later questions about the same `item_id` within 10 minutes of a confident `seen` answer, in the same call or a later one | `queries` (needs a `confident` column) | Highest; mirrors "re-asking right after an answer" | Wrong or stale answer, habit, growing use |
| `within_call_repeats` | Same request asked again in a call after an answer | Agent log | High | Unclear answer, bad audio, hearing |
| `asked_to_repeat_answer` | "What?" or "say that again" right after an answer (intent tag only) | Agent log | Control for hearing problems | Agent voice, volume |
| `clarification_turns`, `turns_to_resolution` | Times the agent asked "which one?"; caller turns until an answer | Agent log | Medium: failure to recover | Recognition errors, prompt changes |
| `response_latency_ms` (median) | From the end of the agent's speech to the start of the caller's | Agent log; needs turn timestamps | Medium, only when pooled weekly | Network lag, interruptions, TV in the background |
| `caller_words_per_turn` (median) | Word count only | Agent log | Low to medium | Recognition dropping words |
| `asr_failed_turns` | Turns with no usable text | Agent log | Speech-recognition quality check | Network, microphone, audio compression |
| `calls_per_day`, `night_call_share` | Calls per local day; share between 22:00 and 06:00 | `queries` | Feeds the sudden-change view | Routine, visitors, growing use |

The rule is to store numbers, not voices.
Keep only this numeric row per call, under the same row-level security as `queries`.
Keep transcripts, if at all, for days rather than months, and never store raw audio, voice embeddings or speaker vectors.
Compute confusion metrics only on calls where Save It itself answered confidently, so the system's own failures are not read as the caller's decline.
Before building the logger, the team must check the LiveKit Agents and Gemini Live documentation for whether turn-level timestamps are available, since the project rule forbids guessing third-party formats.
For acute illness the evidence is thin and comes from clinics.
Computer-measured language features raised delirium classification to 78% in 33 hospitalised older adults ([Tang et al. 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10322161)), and voice detected low blood sugar with an AUROC of 0.87-0.90 in 22 people with type 1 diabetes ([University of Bern](https://mediarelations.unibe.ch/media_releases/2025/media_releases_2025/low_blood_sugar_detected_by_speaking_into_a_smartphone/index_eng.html)).
None of this carries over to short assistant calls, so a change in speech can only ever feed "calls look different this week".
Slurred speech is a stroke warning sign, so the only responsible product behaviour is an emergency script, not a detector.

Voice data carries its own legal risk.
Lawsuits over voiceprints under Illinois's biometric privacy law (BIPA) are rising, including one over a drive-through AI voice assistant ([ABA Litigation](https://www.americanbar.org/groups/litigation/resources/newsletters/class-actions-derivative-suits/voiceprints-ai-bipa-new-trends-biometric-privacy-litigation/)).
Texas's biometric law, enforced by the state Attorney General, carries penalties of up to **$25,000 per violation** ([Winston & Strawn](https://www.winston.com/en/class-action-insider/texas-ag-dont-mess-with-texans-biometric-info.html)).
Voice embeddings are the thing most likely to be argued to be a voiceprint; counts and timings taken from transcripts are much less likely to be.
Georgia lets one party record a conversation ([O.C.G.A. 16-11-66](https://law.justia.com/codes/georgia/2022/title-16/chapter-11/article-3/part-1/section-16-11-66)), but video in a private place needs the consent of everyone filmed ([DMLP](https://www.dmlp.org/node/1293)).
That matters as soon as the FaceTime agent's currently blocked caller video (D33) is switched on.
And 11-15 states require every party's consent for recorded calls ([Rev](https://www.rev.com/blog/productivity/phone-call-recording-laws-state)).

## Clinicians want a caregiver's one-page agenda, and validation takes years

### Clinicians use home data to judge whether the person can stay at home

Clinicians want home data in principle but rarely use it in practice.
In a 2026 AMA and Medscape survey of more than 2,200 physicians in six countries, **97% reviewed wearable data in some way, but in no country did more than 6% actively build it into their workflow**.
Legal liability was the top concern among US doctors, ahead of false positives and extra work ([Fierce Healthcare](https://www.fiercehealthcare.com/health-tech/doctors-want-wearable-data-healthcare-isnt-ready-it-ama-survey-finds)).
In dementia and aging care, clinicians using remote monitoring of daily activities worked in four steps: pull out the relevant data, check it against other sources, judge the risk to the person's ability to stay at home, then keep or change the care plan.
Most kept the existing plan ([JMIR 2025](https://www.jmir.org/2025/1/e64713)).
The best evidence for preparing before a visit comes from SAME Page, a structured checklist for the patient and companion to set the visit agenda, which produced significantly more patient-centred conversations than usual care ([NIH R21 AG049967](https://grantome.com/grant/NIH/R21-AG049967-02)).
Caregivers in another study said monitoring graphs "would speak for themselves" when explaining daily struggles to professionals ([JMIR Aging 2021](https://aging.jmir.org/2021/2/e26875/)).
Save It's clinical value therefore starts with a better-prepared caregiver, not a data feed.
Clinicians will ignore raw timelines, dashboards they have to log into, unvalidated combined scores, and any alert that implies they must act.

| Save It fact | Clinical idea | Where clinicians record it | Caveat |
|---|---|---|---|
| Wearer questions per week; repeat-after-answer share | Repetitive questioning | RMBPC item 1; family interview for the CDR memory score | Novelty and new items push counts up |
| Found or not found, time to find | Finding belongings without help | ADCS-ADL item 11; CDR home and hobbies | Outcome often missing |
| Odd-place put-downs ("keys in the freezer on 12 Oct") | Judgement, misplacing | CDR judgement score; ECog memory item 4; home-safety part of the 99483 visit | Recognition errors look like odd places |
| Wallet or keys leaving home and not coming back | Safety, life outside the home | CDR community affairs; home-safety review | Camera cannot see outside |
| Questions and activity at night | Sleep and night-time behaviour | Behaviour screen; caregiver strain (ZBI-22) | Little night coverage |
| Question volume jumping over a few days | Sudden change from usual | Not a staging item; a reason to call | Must not be presented as illness detection |

A monthly page should lead with coverage, not conclusions.
The proposed layout has a header reading "Prepared from Save It by [caregiver]. Everyday observations, not a medical test".
Next comes a coverage strip: days worn, hours observed, rooms never observed by design, and low-coverage weeks greyed out.
Then three small trend charts covering 6-12 months: wearer questions per 10 observed hours, share of questions that ended "found", and put-downs in the usual place.
Each chart has a shaded band for the person's own baseline and no red.
Below that sit a list of caregiver-tagged events with two or three concrete examples, a SAME Page-style "questions for this visit" box, and a footer stating what is never recorded and that the numbers have no established norms.
The same noise logic that makes a 4-point MoCA change the minimum for a real change (ICC 0.81, SEM 1.5) applies here ([Feeney et al. 2016](https://www.pubmed.gov/27258421/)).
A home metric that moves less than its own week-to-week noise must not be called a change.

### GUIDE and the 99483 visit fit; remote-monitoring billing codes do not

The money points to GUIDE and the 99483 visit, not to remote-monitoring billing codes.
Remote Patient Monitoring pays for body measurements (such as blood pressure) from an FDA-defined device.
Remote Therapeutic Monitoring covers breathing, musculoskeletal and cognitive behavioural therapy monitoring.
Neither covers monitoring of memory lapses ([Foley & Lardner 2025](https://www.foley.com/insights/publications/2025/07/remote-patient-monitoring-rpm-and-remote-therapeutic-monitoring-rtm-what-you/)).
From 1 January 2027, both will also require a starting face-to-face visit, and Remote Therapeutic Monitoring will be limited to existing patients ([Nixon Peabody 2026](https://www.nixonpeabody.com/-/media/files/alerts/2026/11/cms_finalizes_2027_medicare_rpm_rtm_changes.pdf)).
CPT 99483, the roughly hour-long cognitive assessment and care-planning visit, requires an independent historian (usually a family member) and covers daily function, home safety, behaviour symptoms and staging with FAST or CDR ([CMS](https://www.cms.gov/medicare/payment/fee-schedules/physician/cognitive-assessment)).
A caregiver-prepared Save It page supports exactly that visit without billing anything itself.
The CMS GUIDE model (July 2024 to June 2032) pays programs a monthly amount per patient for comprehensive dementia care.
It measures caregiver burden with the ZBI-22, quality of life with PROMIS-10, and long-term nursing home admissions ([GUIDE Performance Measurement Manual v3.0](https://www.cms.gov/priorities/innovation/files/guide-performance-msr-manual.pdf)).
It requires no particular technology, so a GUIDE program could provide Save It to reduce the burden of repeated questions and to give its care navigators better information.
Emory Integrated Memory Care, a nurse-led dementia practice with about 650 active patients and a 24/7 support line, was the only Georgia practice chosen for GUIDE in 2024 ([Emory News 2025](https://news.emory.edu/features/2025/06/emorys-integrated-memory-care); [Emory Nursing](https://www.nursing.emory.edu/imc)), which makes it the obvious first conversation.
Whether GUIDE rules let programs give patients consumer technology (Medicare limits on inducements) has not been researched.

### Validation is a five-stage program, with Atlanta partners

The accepted framework, V3, has three parts: verify the sensing, check that each metric is computed correctly (analytical validation), then show it means something clinically in a defined group of people ([Goldsack et al. 2020](https://www.nature.com/articles/s41746-020-0260-4)).
Earlier programs ran for a long time with small to mid-sized groups.
ORCATECH's ISAAC study followed 265 older adults for an average of 33 months ([Kaye et al. 2011](https://pmc.ncbi.nlm.nih.gov/articles/PMC3132763)).
CART installed sensors in 232 homes with 301 older adults, in four groups chosen for diversity ([Beattie et al. 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7768162)).
Minder's feasibility report covered 82 people with dementia over 958,000 participant-hours ([JMIR Aging 2023](https://aging.jmir.org/2023/1/e43777/PDF)).

| Stage | Question | Design (rough, not powered) | Ground truth | Output |
|---|---|---|---|---|
| 1 Verification | Does the worn camera log put-downs and places correctly? | 20-50 scripted home sessions with staff, no patients | Video labelled by two raters, for research only and never uploaded to Roboflow | Sensitivity and precision by item, landmark and lighting |
| 2 Analytical validation | Are the metrics computed correctly, and are they stable? | 10-20 cognitively healthy volunteers, 4-8 weeks | Hand-checked logs and diaries | Agreement, week-to-week reliability (ICC), smallest detectable change, and the CV every power estimate needs |
| 3 Feasibility | Will people with MCI or mild dementia wear it, and will caregivers accept it? | 20-40 pairs, 3 months, at Emory | Wear-time logs, usability scale, interviews | Wear time, dropout, burden, privacy concerns |
| 4 Cross-sectional validation | Do metrics differ by stage, and do they match family reports? | 100-200 pairs split by CDR 0, 0.5 and 1 | CDR-SB, MoCA, FAQ, RMBPC, ZBI-22 | Correlations, separation between stages |
| 5 Longitudinal validation | Do metric changes come before, or track, decline? | Same group, 12-24 months, visits every 6 months | CDR-SB change beyond 1-2 points, MoCA beyond 4 | Sensitivity to change, lead time |

Some design rules follow from the evidence.
Pre-register the metric definitions so results cannot be cherry-picked, and report observed hours next to every metric.
Freeze the device and software version during each phase, as the FDA's guidance on digital health tools in trials warns ([FDA Law Blog 2024](https://www.thefdalawblog.com/2024/02/fda-releases-final-guidance-on-use-of-digital-health-technologies-for-remote-data-acquisition-in-clinical-investigations/)).
Recruit for diversity from the start through the Goizueta ADRC's minority engagement core.
Export metrics as FHIR Observations with custom codes, since no standard LOINC codes exist for these measures.
Consent is the hardest constraint in Georgia.
Emory IRB guidance (2018 version) lets a legally authorised representative consent for an adult only in studies that include treatment, unless the representative holds a durable power of attorney for research ([Emory IRB guidance](https://irb.emory.edu/_includes/documents/sections/guidance--enrolling_peopl_with_-diminished_-capacity.pdf)).
An observational study without treatment should therefore enrol people with MCI or mild dementia who can consent for themselves, with ongoing agreement, the right to refuse, and periodic re-consent built in; the team must confirm that guidance is still current.

Atlanta has unusually good partners, but a student team needs a faculty sponsor before approaching them.
Emory Integrated Memory Care has GUIDE patients and care navigators.
The Cognitive Empowerment Program, backed by a $10 million Cox Foundation grant and partnered with Georgia Tech's Institute for People and Technology (IPaT), has participants with MCI who can consent and a technology team ([Emory News 2024](https://news.emory.edu/stories/2024/01/som_bhc_cep_cox_grant/story.html)).
Georgia Tech's IPaT HomeLab tests assistive technology in real homes ([Georgia Tech](https://hg.gatech.edu/node/628929)).
The Goizueta Alzheimer's Disease Research Center (ADRC), renewed with $21.9 million from the National Institute on Aging (NIA) in 2025, holds a well-characterised group of participants with biomarker data ([Emory News 2025](https://news.emory.edu/stories/2025/07/hs_alzheimers_research_grant_29-07-2025/story.html)).
Outside funding exists: NIA's AI and Technology Collaboratories give pilot awards of up to $200,000 in direct costs ([AITC overview](https://pmc.ncbi.nlm.nih.gov/articles/PMC10788144/)), and their later calls ask for regulatory and reimbursement plans ([LeadingAge](https://leadingage.org/a2-pilot-awards-open-for-ai-based-healthy-aging-projects/)).
SBIR grants, renewed through 2031, require a for-profit company ([SSTI](https://ssti.org/node/91454)).
The approach the evidence supports is to lead with the caregiver problem and the privacy design, ask what data the care team wants before proposing metrics, and request no patient data or identifiable images until an IRB-approved protocol is in place.

### A device claim would mean a De Novo submission and about two years

If validation succeeded, the path to FDA clearance would still be long.
Every FDA-authorised digital cognitive product found is an active test (a set of cognitive tasks) regulated as a Class II "computerized cognitive assessment aid" under 21 CFR 882.1470, and its labelling must say it does not identify clinical diagnoses ([21 CFR 882.1470](https://www.law.cornell.edu/cfr/text/21/882.1470)).
Passive put-down and question analytics match neither that definition nor any earlier product, and no FDA-authorised passive home monitor for cognition was found.
The closest templates are Cognivue's De Novo submission, whose main study enrolled 401 people at 13 sites with blinded comparison testing and 1-2 week retests and took roughly two years to decide ([Innolitics DEN130033](https://fda.innolitics.com/device/DEN130033)), and Cognoa's Canvas Dx, a De Novo built on caregiver questionnaires and home video ([MobiHealthNews](https://www.mobihealthnews.com/news/fda-greenlights-cognoas-tool-detect-autism-spectrum-disorder-kids)).
The FY2027 De Novo filing fee alone is **$191,020, or $47,755 for a small business** ([RAPS](https://www.raps.org/resource/fda-unveils-fy-2027-user-fee-rates.html)).

## Disease words, not the data, push Save It over the medical-device line

Under the FDA's general wellness guidance issued on 6 January 2026, products that sense without touching the body "may display values, ranges, trends, baselines, or longitudinal summaries".
They stop counting as wellness products if their labelling, interface or functions include "references to specific diseases, clinical conditions, or diagnostic thresholds", alerts that "recommend or require specific clinical action", or an intended use of "diagnosis, screening, monitoring, or management of a disease or condition" ([FDA General Wellness guidance](https://www.fda.gov/media/90652/download)).
A product may still say that "evaluation by a healthcare professional may be helpful", as long as it names no disease, calls nothing "abnormal, pathological, or diagnostic", uses no clinical thresholds and sends no ongoing disease-management alerts.
The clinical decision support exemption does not help Save It.
It covers only software that supports health care professionals, treats software for patients or caregivers as a device unless another policy applies, and excludes analysis of "a pattern or signal from a signal acquisition system" ([FDA CDS guidance](https://www.fda.gov/media/109618/download)).
The intended-use statement that keeps Save It outside device rules is "Save It helps a person find everyday belongings and helps family stay informed about everyday routines".
"MCI risk", "cognitive decline score", "progression tracking", "early detection", "possible delirium" and "ARIA monitoring" belong only in IRB-approved research.
None of this is legal advice, and a regulatory lawyer should confirm before any clinical-sounding feature ships.

| Avoid | Prefer |
|---|---|
| "Signs of cognitive decline", "memory score", "MCI risk" | "Asked about her glasses 9 times this week; she usually asks about 4" |
| "Abnormal", "worsening", "alert: decline detected" | "This is a change from her usual pattern" |
| "Possible delirium", "possible infection" | "She asked about four times more than usual since Tuesday, and less in the afternoons" |
| "Sundowning detected" | "Most questions came between 5 and 8 pm this week" |
| "Naming difficulty" for `unknown_item` | "Save It did not recognise 3 requests; you can add these words as nicknames" |
| "Contact her doctor now" | "If this continues, you may want to mention it at her next appointment" |
| "Biomarker", "clinically validated", "medical-grade" | "Based on what the camera saw and what she asked" |
| Any claim of HIPAA compliance | "Built with HIPAA-style safeguards" |

Outside HIPAA, Save It likely falls under the FTC's updated Health Breach Notification Rule, which covers most health apps that HIPAA does not and treats unauthorised sharing with third parties as a breach ([Covington Inside Privacy](https://www.insideprivacy.com/health-privacy/ftc-issues-final-rule-to-expand-scope-of-the-health-breach-notification-rule/)).
Whether Save It counts as a "personal health record vendor" under the rule was not checked, but the practical consequences are clear: an incident plan that meets the rule's deadlines, and no third-party analytics code on the dashboard.
Health-related fields (drinking, eating, handling medication) make the database more sensitive.
Gaps in the room timeline reveal bathroom timing, which the no-capture rule was designed not to collect, so those gaps must never be shown or analysed.
Using Minder's strongest infection signal would require an explicit, recorded change to that rule, which this report does not recommend.

The ethics literature points to separate views for different people, and no risk scores.
Reviewers judge that large-scale digital early detection of dementia does not meet the standards for a screening programme and risks widening inequality ([Ford, Milne and Curlewis 2023](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10909482/)).
People have a recognised right not to know ([Ursin, Timmermann and Steger](https://philarchive.org/archive/URSEIO)).
The need for monitoring rises as the ability to consent falls ([BMC Medical Ethics 2019](https://link.springer.com/doi/10.1186/s12910-019-0437-z)).
Cameras meet more resistance than door or gas sensors ([Igarashi and Nihei 2023](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10305305/)).
In a Swiss survey of 1,211 people, over 80% accepted wearables for locating people with dementia or detecting falls, but only about 35% accepted cameras ([Swiss survey](https://www.synapsesocial.com/papers/696c79cde45ebfc9113cd561)).
That makes Save It's crops-only, no-bathroom, no-full-frame design central to acceptance.
The resulting rules are concrete.
The wearer sees their own items, what is stored, and a pause control, never trend charts framed as decline.
Family sees daily cards, item cards and weekly patterns against the person's own baseline, never comparisons with other people.
Clinicians see only the monthly page that the wearer (or their authorised representative) chooses to share.
Researchers get de-identified totals under a separate consent that can be withdrawn.
While able, the wearer is asked whether summaries may go to clinicians, and the answer is recorded as an advance preference.
The privacy notice should also say Save It is not designed or validated for guardianship, driving or family disputes, because monthly summaries invite that misuse.

## Never auto-dial 911: confirm with the person, then escalate to a human

Automatic 911 calls after a fall on FaceTime fail on accuracy, on law, and on harm specific to dementia.
Fall detectors that use motion sensors lose much of their lab accuracy on real falls.
Thirteen published methods averaged **57% sensitivity** on 29 real-world falls ([Bagalà et al. 2012](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3353905/)), and the best newer method, tested on 143 real falls, still gave **0.56 false alarms per hour** of daytime wear ([Palmerini et al. 2020](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7697900/)).
Fall detection from a worn camera has only been tested on staged falls by five volunteers ([Wang et al. 2023](https://research.rug.nl/en/publications/fall-detection-with-a-non-intrusive-and-first-person-vision-appro/)), and a phone swinging on a lanyard is a worse place for a sensor than the lower back.
Apple, with years of data, waits for about a minute without movement and then runs a 30-second countdown before dialling ([Apple Support 108896](https://support.apple.com/en-us/108896)).
Even so, its Crash Detection made about 300 unintended 911 calls in a few weeks in one Wisconsin county ([KTVU](https://www.ktvu.com/news/apple-crash-detection-software-triggers-fake-911-calls-first-responders-say)).
Legally, automated calls to registered 911 center numbers are banned except for an "emergency purpose", with fines of **$10,000 to $100,000 per call** ([47 CFR 64.1202](https://www.law.cornell.edu/cfr/text/47/64.1202); [47 USC 1473](https://law.justia.com/codes/us/2019/title-47/chapter-13/subchapter-v/sec-1473/)).
Whether a software false alarm counts as an emergency purpose has never been tested.
A backend that places 911 calls itself must also deliver the caller's exact location under the RAY BAUM'S Act ([FCC](https://www.fcc.gov/911-dispatchable-location)).
Georgia's false-alarm crime requires "knowingly" sending a false alarm ([O.C.G.A. 16-10-28](https://law.justia.com/codes/georgia/2006/16/16-10-28.html)), so the honest verdict is "legally risky and unclear" rather than "clearly illegal".
iOS also does not let an app dial silently: since iOS 10.3, a phone link needs the user to confirm ([Apple Phone Links](https://developer.apple.com/library/ios/featuredarticles/iphoneurlscheme_reference/phonelinks/phonelinks.html)).
For a person with dementia, a false dispatch does more harm than usual: strangers, sirens and possibly being taken to hospital frighten and disorient, and the person may not be able to cancel.

The underlying need is real, so the answer is a better design, not nothing.
Among 110 people over 90 followed for a year, 80% of those who fell could not get up after at least one fall, and 30% lay on the floor for an hour or more.
Cognition was the only factor that predicted a long lie, and call alarms went unused in most of those falls ([Fleming and Brayne 2008](https://www.bmj.com/content/337/bmj.a2227.abstract)).
SafelyYou's video pilot in dementia care homes cut emergency-department visits after falls from 24.5% to 8.3%.
But the gain came from staff reviewing the video and deciding what to do, and the authors had financial ties to the company ([AJMC 2019](https://www.ajmc.com/view/realtime-video-detection-of-falls-in-dementia-care-facility-and-reduced-emergency-care)).

The industry pattern is: detect, confirm with the person, pass to a human who decides, and only then involve 911.
Alexa Emergency Assist sends "call for help" to a team of Urgent Response agents and says plainly that it is not a 911 service ([About Amazon](https://aboutamazon.com/news/devices/alexa-emergency-assist)).
Noonlight's Dispatch API has dispatchers text and call the user within about 30 seconds and close false alarms before passing the location to 911 ([Noonlight](https://noonlight.com/products/dispatch-api)).
For Save It, the flow would start with a trigger.
Today that means the FaceTime agent hears "I fell", "help" or "I can't get up" and calls a `report_concern` tool; later, it could be a jolt picked up by the capture page's motion sensor, confirmed by frames stuck on the floor or ceiling.
Next comes one short question to confirm, with a 30-60 second wait.
If the person says they are fine, the family still gets a gentle notice, because people with dementia sometimes deny a real fall.
If they need help or go silent, the family gets an urgent text or push with the time, room and landmark from the database, and two buttons: "I'm on my way" or "I'm calling 911".
The family member decides, not the software.
A professional monitoring service like Noonlight is the production path, and families should be pointed to Apple Watch Fall Detection, which is on by default for users aged 55 and over, rather than Save It rebuilding it.
The current repo limits what the demo can show.
The capture page is deferred (D33), so only the spoken trigger can be built.
No family-notification backend exists, and promises to contact family were deliberately removed from the agent, so it must not say "I've told Anna" until a real channel does.
Alerts must carry text or a short-lived signed crop link, never a full frame.
And nobody should call the real 911 in testing or on stage.

| Feature | How it fits | Effort | Impact | Main risk |
|---|---|---|---|---|
| Spoken distress tool in the FaceTime agent | `report_concern` on "I fell", "help", "I can't get up", "I smell smoke", then confirm, then family | 2-3 h | High, but only during calls | Near-miss phrases ("my glasses fell"); test them |
| Scam guard in the agent prompt | Gift cards, wire transfers, crypto, "grandchild in jail", "don't tell anyone": a gentle "hang up" and a note to family | 1-2 h | High: adults 60+ reported about $7.7 billion lost to fraud in 2025 ([AARP](https://www.aarp.org/money/scams-fraud/fbi-ftc-report-2025-losses.html)) | Lecturing on false matches |
| "No frames" or "no check-in" notice | No frames for X daytime hours, or no call by a set time, shows a dashboard notice | 1-2 h | Medium | Phone is simply charging |
| Night-time exit notice | Keys or bag in hand, plus the front-door landmark, plus the hour | 2-3 h | High: 6 in 10 people with dementia wander ([Alzheimer's Association](https://www.alz.org/help-support/caregiving/stages-behaviors/wandering)) | Demo home has no front-door landmark; never lock anyone in |
| Pill box handled | Pill organiser registered as an item, answered from sightings | 1-2 h | Medium | Picking it up is not swallowing a pill |
| Lanyard fall trigger | Motion-sensor jolt plus frames showing floor or ceiling | 4-6 h | Medium | Capture page deferred; lanyard swing |
| Stove left on | Burner glow seen, then the wearer elsewhere for N minutes | 6-10 h | Medium | No worn-camera system exists; fixed thermal cameras reach 94% sensitivity ([CMBES](https://proceedings.cmbes.ca/index.php/proceedings/article/download/363/357/726)) |

## The camera and database support more than medicine

### Cheap visual signals reuse what is already stored

The cheapest visual signals reuse data Save It already stores.
An odd-place flag (a registered item on a fridge, oven, bin or never-used landmark) takes hours to build.
It ties directly to the Alzheimer's Association warning sign "misplacing things and losing the ability to retrace steps" ([Alzheimer's Association](https://www.alz.org/alzheimers-dementia/10_signs)).
It also gives the voice agent a gentle line ("your glasses are in the fridge, which is not where they usually go") and gives family a weekly count.
A "my day" text timeline built from `observations` and `sightings`, read aloud on request and shown as a dashboard strip, draws on SenseCam research: reviewing images of the day beat a written diary for recall in 5 of 6 people with mild-to-moderate Alzheimer's ([Woodberry et al. 2015](https://www.microsoft.com/en-us/research/?p=464112)).
That research used images, though, and a diary made only of text or item crops is untested.
Counting pick-ups of the already-registered water bottle and the pill box only needs existing `carried` stays.
That matters because about 20% of older people in long-term care were dehydrated in the DRIE study ([DRIE](https://pmc.ncbi.nlm.nih.gov/articles/PMC5018558)).
But the counts must be labelled "picked up", never "drank" or "took".
Camera-based drinking detection reaches 89% F1 for spotting drinking episodes but only 56.7% precision for amounts ([wearable eating review](https://encyclopedia.pub/entry/46817)).
AiCure's pill-swallowing verification needs a deliberate face-on video, and it was not significantly better than modified directly observed therapy (89.7% versus 71.9%, P = .08) ([Bain et al. 2017](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5340925/)).
A wrong "not taken" told to the person could cause a double dose, so medication signals go to family only.
A wear-time indicator keeps every other number honest.
An item's own history (keys going into the drawer at 3 pm) gives family neutral evidence when the person believes something was stolen, the most common delusion reported in Alzheimer's samples ([Frontiers in Psychiatry 2021](https://www.frontiersin.org/articles/10.3389/fpsyt.2021.808724/full)), as long as it stays family-only.
Stove, door and hazard states are one Gemini field away but need testing on staged frames.
Confirming pills were swallowed, detecting falls from half-second stills, using room-transition regularity as a decline marker, and reading night patterns from a lanyard rarely worn at night are all research problems.
Face recognition for "who visited" is ruled out by project rules and bystander consent; a visit log typed in by family does the job without vision.
Every new Gemini field means more of each frame is analysed by a third party, and the no-capture rule currently stops storage, not sending (D12 is still open).

### Non-medical analytics are the safest to ship first

The same tables can improve Save It's core job without any clinical validation.
Per-item place estimates feed the judge-requested "where to look" ranking that `app/look.py` already begins.
They start from each landmark's share of an item's confirmed stays, smoothed with a Dirichlet prior and weighted toward recent stays with a half-life of about 14 days.
Stays are split into four time-of-day buckets, `misses` lower a landmark's weight for a few hours, and a "found" from `record_outcome` counts as the strongest positive evidence.
The ranking can be tested offline by replaying history and checking whether the right place came first (hit@1) or in the top three (hit@3).
Confidence calibration is a small logistic model of the chance an item is found, using `det_conf`, `room_conf`, `id_conf`, sighting age and state, checked monthly with a reliability diagram and Brier score.
It lets the spoken hedge follow a calibrated probability rather than the raw detector score, since modern neural networks are often poorly calibrated ([Guo et al. 2017](https://arxiv.org/abs/1706.04599)).
Recognition-quality monitors keep errors from masquerading as clinical change.
They track tentative stays that never confirm, contradicted rate per landmark, impossible room jumps checked against `room_links`, the same item active in two places, and confident `seen` answers followed by `not_found`.
The caregiver digest is the strongest product story.
It holds a "today" card ("asked about 3 things today; all were found"), item cards with crops and usual places, and a "where things end up" list that doubles as advice (a hook by the door).
It also has a "when questions come up" heatmap and a "did it help?" panel.
Funded startups sell exactly this pairing of a patient-facing voice with caregiver insight ([Meela, Business Wire](https://www.businesswire.com/news/home/20250911525548/en/Meela-Launches-Personalized-AI-Companion-to-Combat-Loneliness-Epidemic-Among-Seniors)).

### Every competitor watches the person; none tracks belongings

Every passive monitor on the market watches the person, and none keeps track of belongings.
Being camera-free is now the main selling point of products such as Vayyar's radar sensor and Nobi's ceiling lamp ([Vayyar Care](https://vayyar.com/care); [Digital Trends](https://digitaltrends.com/home/nobi-smart-lamp-provides-help-when-older-people-fall/)).
Amazon has discontinued Alexa Together ([About Amazon](https://www.aboutamazon.com/md/news/devices/alexa-together-launches-to-help-customers-remotely-care-for-loved-ones)).
The largest randomised trial of assistive technology and telecare for dementia (ATTILA, 495 people) found no delay in moving into a care home (HR 0.84, 95% CI 0.63-1.12) and no wellbeing benefit ([ATTILA](https://doaj.org/article/d12126d002194de2bf1160a89d5c136d)).
The funded leader in object recognition is CrossSense, AI glasses that won the GBP 1 million Longitude Prize on Dementia in March 2026 without published trial results ([Nesta](https://www.nesta.org.uk/blog/ai-smart-glasses-companion-winner-of-longitude-prize-on-dementia/)).
Save It's defensible differences are an ordinary phone or FaceTime call instead of an app or glasses, memory that persists with honest uncertainty, the question log as caregiver insight, and written-down privacy rules.
ATTILA's null result is the reason to stay narrow and matched to one specific need.

## Ranked recommendations, from tonight's freeze to a multi-year study

The ranking weighs medical and caregiver impact against effort, given a 05:00 freeze, a dashboard (step 08) that is not yet built, and a deferred capture page.

| Rank | Recommendation | Horizon and effort | Impact | Main limit |
|---|---|---|---|---|
| 1 | Reframe the pitch around speed of change: one evidence slide (74% misplace; 81% "where did I put it down"; delirium in 30% and missed in half; the question log mirrors ECog, AD8 and ADCS-ADL items), the intended-use statement, and the phrasing guide | Tonight, under 1 h | High: a believable medical story with no false claim | Say "could support research", never "detects decline" |
| 2 | Spoken distress and scam handling in the FaceTime agent: a `report_concern` tool that confirms, logs and shows a placeholder family notice, presented as "confirm, then the family decides" | Tonight, 2-3 h | High during calls | No notification backend; test near-miss phrases; no auto-911; no promises the agent cannot keep |
| 3 | Three SQL views: coverage, wearer questions per 10 covered hours with the repeat-after-answer rate, and found rate | Tonight, 1-2 h | Medium-high: the data backbone for every later feature | Demo data covers only a few hours; show counts, not trends |
| 4 | Odd-place flag with a gentle spoken note | Tonight, 1-2 h | Medium | Recognition errors; count only active stays |
| 5 | Sample one-page monthly summary built from `supabase/dummy_data.sql` | Tonight, 1-2 h if time remains | Medium (as a story) | Label it as a sample; no real person's data |
| 6 | Store `confident` on `queries`, add family event tags, and add a numbers-only per-call metrics table (next numbered migration), after checking LiveKit and Gemini Live turn timestamps | 2-4 days | High: unlocks clean repeat and interaction metrics | Never store audio or voice embeddings |
| 7 | Two-track change detector with a starting period, a persistence rule and a weekly digest; alerts off by default | 1-2 weeks | High once baselines exist | Untested thresholds; alarm fatigue |
| 8 | Real caregiver-first escalation (text or push), a capture-page motion trigger once step 07 exists, and a Noonlight-style monitoring service for production | 1-2 weeks | High for falls, since dementia makes long lies on the floor more likely | False alerts; liability; no-full-frame rule |
| 9 | Place estimates, confidence calibration and recognition-quality monitors | About 1 week | High for the core product, no clinical risk | Outcomes are only recorded for some questions |
| 10 | "My day" timeline, pill-box and drink counts, wear-time indicator | Days | Medium | "Picked up" wording; never show bathroom gaps |
| 11 | Faculty sponsor and IRB stages 1-3 with Emory Integrated Memory Care, the Cognitive Empowerment Program and IPaT HomeLab; the first result to deliver is the measured week-to-week CV of each metric | 6-12 months | Very high: replaces every assumed number in this report | Georgia consent rules; diversity |
| 12 | Clinical validation stages 4-5 (100-200 pairs, 12-24 months), and only then a decision on a De Novo submission | 2-4 years | Very high if the results are positive | Cost, De Novo fee, dropout |
| 13 | Sudden-change detection checked against clinically confirmed delirium | Years, after stage 3 | Highest clinical value | Highest risk of over-reading; device territory |

## Conclusion

The research changes what Save It is, medically.
It is not an early-detection tool, which both the evidence and the regulators push back on.
It is a fine-grained clock for change that tells a clinician when something started and how fast it moved, the one question families most often cannot answer.
That framing has three consequences the team can act on.
First, keeping the lanyard worn is a clinical problem, not just an engineering one: the most dangerous and most often missed acute state, hypoactive delirium, shows up as missing data rather than a spike, so wear time must be measured, shown and modelled as a signal.
Second, Save It distorts its own measurements by working: every question it answers is one the family no longer hears.
Starting periods, fresh baselines and metrics that allow for this shift (repeat-after-confident-answer rather than raw question counts) are what separate a real measure from a usage counter.
Third, the line between a wellness product and a medical device runs through wording, not data: the same weekly count is fine as "asked about her glasses 9 times, usually 4" and regulated as "possible decline".

The most valuable next step is therefore unglamorous.
Every power estimate, alert threshold and minimum detectable change in this report rests on an assumed week-to-week variability that nobody has measured for object or question data.
A small study with staff and volunteers that measures it, run with an Emory faculty sponsor, would do more for Save It's medical credibility than any feature built tonight.
GUIDE, not remote-monitoring billing, is where that credibility would eventually be paid for.
