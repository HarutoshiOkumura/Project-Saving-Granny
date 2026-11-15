# Signals and features from passive egocentric camera data for a person living with dementia at home

Scope: what else the Save It lanyard stream (one JPEG every 0.5 s, SAM 3 gate plus Gemini Flash strict JSON, crops only, bathrooms no-capture) could detect or enable.
Research date: 15 Nov 2026.
Evidence is 2007-2026; older items are flagged where they matter.
Every claim carries an inline source; anything I could not source is listed under Gaps.

Pipeline facts used for the feasibility ratings (from this repo, not from the web):
the `observations` table already stores one row per processed keyframe with `captured_at`, `room_id`, `room_conf` and `landmarks_seen` (text only, no image) (`supabase/migrations/0001_save_it_memory.sql`, line 119).
Gemini only runs when the SAM 3 gate opens on an enrolled item, plus one "empty look" at most every 30 s, so room is known for every item frame but only about twice a minute otherwise (`.claude/rules/perception.md`).
No observation is written for a no-capture room or an unsure room, so bathroom visits and camera-off periods both show up as gaps.
The enrolled demo items already include a "dark blue bottle" (SAM 3 prompt list in `.claude/rules/perception.md`).

Feasibility scale used throughout:
**A** = cheap prompt or query change on data the pipeline already produces (hours).
**B** = new enum fields in the Gemini schema plus a new table or job (a day or so).
**C** = needs a new or fine-tuned model, a different sensor, or a clinical validation study (research problem).

## 1. What does egocentric and lifelogging research say about benefits for dementia or MCI?

### Takeaway
Reviewing a wearable camera's pictures of one's own recent day improves recall of those events in amnesia and in mild to moderate Alzheimer's disease, but the evidence base is small (single cases and a handful of patients) and comes mainly from Microsoft SenseCam work in 2007-2017.
The closest modern prior art to Save It is MemPal (MIT, 2025), a neck-mounted phone camera with GPT-4V that answers "where is my X" by voice and improved object finding in 15 older adults at home.

### Cited Findings
- Berry et al. (2007) used SenseCam as a pictorial diary for "Mrs B", a woman with severe memory impairment after limbic encephalitis; after reviewing the images she recalled about 80% of recent personally experienced events, and retention was maintained 11 months later - [Microsoft Research, Berry 2007](https://microsoft.com/research/publication/the-use-of-a-wearable-camera-sensecam-as-a-pictorial-diary-to-improve-autobiographical-memory-in-a-patient-with-limbic-encephalitis-a-preliminary-report)
- An fMRI follow-up on the same patient found that recognising SenseCam-rehearsed events activated frontal and posterior regions associated with normal episodic memory, unlike written-diary rehearsal - [Berry et al. 2009, JNNP](https://owenlab.uwo.ca/pdf/2009-Mar-Berry-JNNP-The%20neural%20basis%20of%20effective%20memory%20therapy%20in%20a%20patient%20with%20limbic%20encephalitis.pdf)
- Browne et al. (Memory, 2011) compared SenseCam review with a written diary in a patient with memory retrieval deficits; SenseCam review gave significantly more recalled detail, about twice as many details at 6 months - [Microsoft Research, Browne 2011](https://microsoft.com/en-us/research/?p=163388)
- Woodberry et al. (Memory, 2015) tested SenseCam with 6 patients with mild to moderate Alzheimer's disease over 40 events; SenseCam review beat a written diary for recall in 5 of 6 patients over two weeks - [Microsoft Research abstract](https://www.microsoft.com/en-us/research/?p=464112); [manuscript PDF](https://www.microsoft.com/en-us/research/wp-content/uploads/2018/02/Woodberry-et-al-Memory.pdf)
- A Microsoft Research summary of a version of that work says that at 1 and 3 months, 3 patients still recalled significantly more with SenseCam and 3 showed no significant difference (not checked against the published paper) - [Microsoft Research summary](https://microsoft.com/en-us/research/?p=166065)
- A 2017 Current Alzheimer Research study reported that SenseCam-based training improved autobiographical memory in mild Alzheimer's more than comparison memory-training programmes - [Eurekaselect](https://www.eurekaselect.com/article/83779)
- Gelonch et al. (BMC Geriatrics, 2019): 9 people with MCI plus caregiver relatives used a lifelogging camera after individual training; acceptance was good, they captured a sensible number of images per day, and privacy worries did not outweigh perceived memory benefits - [DOAJ record](https://doaj.org/article/0aa86582f4de415e95864ad95ee8359f)
- MemPal (Maniar, Chan, Zulfikar, Ren, Xu, Maes; arXiv Feb 2025, IUI 2025) used an iPhone on a magnetic neck mount tilted toward the hands, GPT-4V on tiled frames, CLIP embeddings for a spatial map, and a text diary (activity, objects in hand, scene, location, timestamps) in a vector database - [MemPal full text](https://arxiv.org/html/2502.01801v1)
- MemPal ran activity detection only when hands were visible, to limit processing - [MemPal full text](https://arxiv.org/html/2502.01801v1)
- MemPal study: 15 older adults aged 62-96 (8 cognitively normal, 4 subjective cognitive decline, 3 MCI), about 2.5 hours in each participant's own home, objects retrieved about 40 minutes after placement - [MemPal full text](https://arxiv.org/html/2502.01801v1)
- MemPal results: audio answer accuracy 72% (visual image answers 53%); errors were 24% misidentified object, 22% wrong location, 12% no object detected; rooms searched fell from 1.93 (no aid) to 1.10; mean answer latency 2.17 s over 204 queries; SUS 69.4 - [MemPal full text](https://arxiv.org/html/2502.01801v1)
- MemPal tested 33 context-based safety reminders and correctly triggered 28 (0.85) - [MemPal full text](https://arxiv.org/html/2502.01801v1)
- MemPal participants felt body-worn cameras were less intrusive than smart-home cameras; most were comfortable sharing activity logs with caregivers and physicians; the authors recommend storing text rather than images and moving processing on-device - [MemPal full text](https://arxiv.org/html/2502.01801v1)
- Ego4D's "episodic memory" benchmark is built around exactly this question type ("Where did I put the spanner?"): natural language queries, visual queries from an image crop, and moment queries over past first-person video - [Ego4D paper](https://arxiv.org/pdf/2110.07058v1)
- Ego4D episodic memory remains hard: the second-place entry in the CVPR 2024 natural-language-query track scored mean R@1 of 23.15 - [ObjectNLQ, arXiv 2406.15778](https://arxiv.org/abs/2406.15778v1)
- Ego4D's size is reported as 3,025 hours (arXiv v1) and 3,670 hours (later version) - [Ego4D paper](https://arxiv.org/pdf/2110.07058v1)
- Kelly et al. (2013) published an ethical framework for automated wearable cameras in health research, built on respect for autonomy, informed consent, and privacy and confidentiality controls, with particular concern for bystanders and for unflattering or unwanted images - [Kelly et al. 2013, AJPM](https://libmast.utm.my/Record/oxford-uuid:079a5a57-891d-4ad1-814d-9be593e9b63c)

### Inferences
- Save It's architecture (enrolled items, fixed landmarks, a database that derives "where is it now") is a constrained version of Ego4D episodic memory; the constraint is why it can be more reliable than open-ended video QA, and that is worth saying in the pitch.
- MemPal is the most direct prior art and should be acknowledged; Save It's differentiators are the phone-call and FaceTime read path, the two-frame and absence rules, crops-only storage, and no-capture rooms.
- MemPal's 72% answer accuracy at about 40 minutes is a useful external baseline to compare a Save It demo against.
- The SenseCam evidence supports a "review my day" feature, but it was based on reviewing images, which conflicts with Save It's "never store a full frame" rule; a text or crop-based diary is untested as a memory aid.

### Gaps
- I found no randomised controlled trial of wearable-camera review in dementia; all results above are case studies or small cohorts.
- I did not verify whether the ReMemory project (Gelonch's next phase) published efficacy results.
- MemPal's frame rate and its per-condition object-finding times were not reported in the parts I read.

## 2. Which ADLs and IADLs can be recognised from a chest-worn camera, and how accurately?

### Takeaway
Eating and food detection from wearable cameras is the most mature (roughly 89-95% accuracy in free-living studies, but weak at estimating how much was consumed), medication-taking from a wearable camera has small-study results around 93%, and general egocentric activity recognition across many classes is still modest (about 30-40% zero-shot on kitchen benchmarks).
For Save It, narrow yes/no questions tied to enrolled objects (is the water bottle at the mouth, is the pill box open in hand) are far more reliable than open activity labels.

### Cited Findings
- The ADL dataset (Pirsiavash and Ramanan, CVPR 2012) is about 10 hours (1 million frames) of unscripted first-person video from 20 people in 20 homes, with an activity list drawn from rehabilitation literature - [Pirsiavash and Ramanan 2012](https://people.csail.mit.edu/hpirsiav/papers/adl_cvpr12.pdf)
- A later CNN method reported beating prior egocentric activity recognition by over 6.6% without gaze information - [Ma, Fan, Kitani 2016](https://ar5iv.arxiv.org/html/1605.03688)
- GPT4Ego (2024), a CLIP-style zero-shot method, reported 33.2% on EPIC-KITCHENS-100, 39.6% on EGTEA and 31.5% on CharadesEgo - [GPT4Ego, arXiv 2401.10039](https://arxiv.org/html/2401.10039v2)
- Shrestha and Thomaz (IEEE CHASE 2024) compared pipelines for annotating egocentric ADL images (concept detector, concept detector plus GPT-3.5, BLIP-2, GPT-4 vision preview with few-shot prompts); BLIP-2 had the highest cosine similarity to human labels at 0.86, and the work targets annotation help rather than classification accuracy - [Shrestha and Thomaz 2024](https://ersearch2.cvtisr.sk/vufind/SummonRecord/FETCH-LOGICAL-a215t-aa43d22ddac18a8c9f15e0490e7e3087f21c114c952d60d66b24ad18bd35c1683/Details)
- A review of wearable eating-detection reports free-living accuracy up to 95% for food versus non-food images and 89.68% for eating-action detection, and a free-living F1 of 89% for drinking and eating episodes but only 56.7% precision at the fluid-intake level - [Encyclopedia.pub review entry](https://encyclopedia.pub/entry/46817)
- The same review notes wearable cameras capture 4,000-6,000 images a day with under 20% relevant to eating, that images suffer from poor light, low resolution and motion blur, and that camera-only systems false-alarm on food the wearer did not eat - [Encyclopedia.pub review entry](https://encyclopedia.pub/entry/46817)
- Hybrid designs use a watch or glasses to detect an intake gesture and only then turn on the camera, to reduce false alarms and battery use - [Encyclopedia.pub review entry](https://encyclopedia.pub/entry/46817)
- A preliminary drinking-detection study with a 3D CNN on video segments used 9 participants in a simulated home; earlier vision work mostly used single frames in labs - [Sensors 2022, 22(18):6747](https://mdpi.com/1424-8220/22/18/6747)
- AIM-2 work classifies the food-ingestion environment from a wearable sensor camera - [AIM-2 ingestion environment, arXiv 2405.07827](https://huggingface.co/papers/2405.07827.md)
- A 2021 wearable-camera pipeline combining object detection and action recognition reported 92.7% accuracy for medication-taking behaviour recognition - [Sensors 2021, 21(11):3594](https://mdpi.com/1424-8220/21/11/3594)
- A wrist-worn egocentric camera has been designed specifically to capture the micro-activities of pill taking - [NSF public access paper](https://par.nsf.gov/servlets/purl/10344382)
- Non-camera baseline: smartwatch accelerometer models detected natural medication-taking gestures with about 95% accuracy - [JMIR validation study, PMC10196892](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10196892/)
- Wearable cameras categorise the type and context of behaviour better than accelerometers: Doherty et al. (2013) annotated 386 accelerometer episodes from 49 adults with SenseCam images and concluded cameras were the best objective method then available for context - [Oxford NDPH listing](https://www.ndph.ox.ac.uk/publications/394986)
- Kerr et al. (2013) found accelerometers often labelled standing as sedentary, with nearly 30 minutes a day of disagreement against SenseCam - [ScienceDaily](https://sciencedaily.com/releases/2013/02/130205083054.htm)
- The Alzheimer's Association lists "difficulty completing familiar tasks" as one of its 10 warning signs - [Alzheimer's Association, 10 signs](https://www.alz.org/alzheimers-dementia/10_signs)

### Inferences
- A chest or neck camera angled down sees the hands, which is the right view for drinking, eating, pill handling and phone use, but not for dressing or grooming (the wearer's own body is mostly out of frame, and bathroom hygiene is excluded by design).
- At 0.5 s JPEGs with the SAM 3 gate, Save It only sends frames to Gemini when an enrolled item is visible; activity recognition therefore works best when the activity involves an enrolled object (water bottle, pill organiser, mug, phone), which is a feature, not a bug: enrol the object and the activity comes for free.
- Drinking: the "dark blue bottle" is already enrolled, so in-hand episodes of the bottle are already logged as `carried` stays; counting them per day is an A-level proxy for "picked up a drink" (not volume).
  Adding a Gemini field like `at_mouth: bool` for the in-hand item is a B-level change.
- Eating: a Gemini enum `wearer_activity` (eating, drinking, cooking, handling_pills, using_phone, none) is a B-level change, but it must be logged as text on the observation, not as an image, and it adds health data to the database.
- Expect false positives from food or cups seen but not consumed (the review's main failure mode) and false negatives whenever the gate is closed.
- Open-vocabulary activity recognition (20+ classes) on 0.5 s stills is a C-level research problem; do not promise it.

### Gaps
- I found no egocentric eating or drinking validation specifically in people with dementia; the closest work is in general adults or simulated homes.
- I found no published zero-shot accuracy for Gemini or GPT-4V class models on egocentric ADL benchmarks; the newest numbers above are CLIP-style methods.
- A search snippet attributed about 40.6% accuracy over 18 classes to the original ADL dataset baseline, but I could not confirm which paper reported it, so I left it out of the findings.
- Whether the ADL dataset camera was chest-mounted was not confirmed in the sources I read.
- I did not find an older-adult validation of eButton or AIM-2 cameras.

## 3. Which home-safety hazards are visible to a wearable camera, and does anyone detect them?

### Takeaway
Leaving the stove on is the hazard with the clearest caregiver demand, and fixed thermal cameras above the hob already detect unattended burners with about 94% sensitivity; I found no published system that detects stove, tap, kettle or door hazards from a worn camera.
A wearable can add a cheap "you walked away from a lit burner" nudge (the stove becomes another thing whose last seen state the database remembers), but it cannot see the stove once the wearer leaves the kitchen, so it is a supplement to an auto shut-off or fixed sensor, never a safety device.

### Cited Findings
- A 2025 narrative review of international literature plus English fire and rescue services says dementia can affect a person's ability to recognise and respond to fire, and that research on fire-risk reduction for people living with dementia is lacking - [James and Clark 2025, PMC12171083](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12171083/)
- The same review found all English fire services offer Home Fire Safety Visits but only four state that people living with dementia are eligible - [James and Clark 2025, PMC12171083](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12171083/)
- American Family Physician (2006) said the role of dementia as a risk factor for burns and fires was not clear, and listed failing to turn off the stove as a warning sign of unsafe behaviour - [AAFP 2006](https://www.aafp.org/pubs/afp/issues/2006/1115/p1688)
- A retrofit infrared camera mounted above the stove detected burner status, pot presence and human activity, with alert sensitivity 94% and positive predictive value 83% - [CMBES proceedings](https://proceedings.cmbes.ca/index.php/proceedings/article/download/363/357/726)
- A 2015 smart-kitchen review notes thermal cameras are sensitive to cooking heat and smoke, and that most kitchen systems focus on fire alone rather than wider cooking hazards - [Scitepress 2015](https://www.scitepress.org/PublishedPapers/2015/55389/55389.pdf)
- EGOFALLS is a visual-audio dataset and benchmark for fall detection from egocentric cameras in older people, using RGB, infrared and audio - [EGOFALLS, arXiv 2309.04579](https://ar5iv.labs.arxiv.org/html/2309.04579)
- MemPal included context-based safety reminders, 28 of 33 correctly triggered, but the paper does not specify which hazards - [MemPal full text](https://arxiv.org/html/2502.01801v1)
- MedaCareLLM (CareYaya) smart glasses claim to read pill bottles and remind users about doses; I found no published evaluation - [IoT World Today](https://iotworldtoday.com/health-care/ai-powered-smart-glasses-launched-to-assist-dementia-patients)
- Alzheimer society guidance recommends locking away valuables and hazardous items - [Alzheimer Society of PEI](https://admin.alzheimer.ca/pei/sites/pei/files/documents/Hoarding_Alzheimer-Society-PEI.pdf)

### Inferences
- Stove left on: a Gemini field `stove_state` (on_with_flame_or_glow, off, not_visible) on kitchen frames, stored as an event, plus a job that flags "last seen on, wearer has been in another room for N minutes" (B).
  It reuses Save It's own "last seen" logic, which is a neat story.
  False positives: reflections, a red indicator light, a hot but switched-off ring; false negatives: induction hobs with no visible glow, frames where the hob is out of view, gate closed because no enrolled item is visible (the gate would need "stove" or "kettle" as a SAM 3 concept, or a timed kitchen look).
  Privacy cost: low (text state only).
- Tap running and kettle left on: same pattern, but running water is hard to see in a 0.5 s still and kettles show little visible state; treat as C until tested on staged frames.
- Front door open at night: if "front door" is enrolled as a landmark, a field `door_open` is B; the wearer must be at the door wearing the lanyard, so a cheap contact sensor is more reliable.
- Floor trip hazards (cords, rugs, items on the floor in a walkway): a field `floor_hazard` is B, but it would fire constantly in a normal home; better as a weekly text summary for family than a live alert.
- Hazardous items left out (knives, cleaning products, medication bottles): prompt-level B; useful as a family dashboard note, low privacy cost.
- Falls from 0.5 s egocentric stills is C; the phone's accelerometer on the capture page is the better sensor for that, and that is a different modality.
- Any alert built on the write path inherits its "may fail softly" property; it must be labelled best-effort, and the pitch must not imply Save It prevents fires.

### Gaps
- I found no paper or product that detects stove, tap, kettle, door or floor hazards from a body-worn camera.
- I did not find incidence data for cooking fires caused by people with dementia; the 2025 review says this research is lacking.
- I did not research fall statistics or fall-hazard detection accuracy in depth.

## 4. Medication adherence verification by camera: what exists and how accurate is it?

### Takeaway
AiCure, the best-known product, verifies ingestion from a deliberate smartphone selfie video (face, pill, swallow), not from passive frames, and its peer-reviewed evidence is small and company-linked: 89.7% vs 71.9% pharmacokinetic adherence against modified directly observed therapy, a difference that was not statistically significant.
Passive 0.5 s frames can at best log "the pill organiser was handled at 8:05"; confirming ingestion is a research problem, and telling a person with dementia "you have not taken it" on a false negative risks a double dose.

### Cited Findings
- Bain et al. (JMIR mHealth uHealth, 2017) ran a pilot substudy of AiCure in a Phase 2 schizophrenia trial; mean cumulative pharmacokinetic adherence over 24 weeks was 89.7% (SD 24.92) with AiCure versus 71.9% (SD 39.81) with modified directly observed therapy - [Bain et al. 2017, PMC5340925](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5340925/)
- The group difference was 17.9% (95% CI -2 to 37.7; P=.08), so not statistically significant - [Bain et al. 2017, PMC5340925](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5340925/)
- AiCure uses facial recognition and computer vision on a phone to identify the patient and the drug and confirm ingestion; subjects used it for up to 6 months with early-termination rates comparable to non-substudy subjects - [Bain et al. 2017, PMC5340925](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5340925/)
- A registered AiCure feasibility study in opioid replacement therapy planned to compare the platform's adherence readings with pharmacokinetic data; I found no posted results - [ClinicalTrials.gov NCT02243670](https://clinicaltrials.gov/study/NCT02243670)
- A Tufts CSDD and AiCure analysis of about 260,000 dosing records from 2,796 volunteers found 48% had at least one intentionally non-adherent dose; AiCure co-authored and promoted it - [BioSpace press release](https://www.biospace.com/new-research-sheds-light-on-intentional-non-adherence-in-clinical-trials)
- A wearable-camera research pipeline reported 92.7% accuracy for medication-taking behaviour recognition - [Sensors 2021, 21(11):3594](https://mdpi.com/1424-8220/21/11/3594)
- Smartwatch accelerometer models detected medication-taking gestures with about 95% accuracy - [PMC10196892](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10196892/)

### Inferences
- Cheapest useful version (A to B): enrol the pill organiser as an item; Save It already logs when it is in hand and where it is put down, so the dashboard can show "pill box handled 8:05" and the voice agent can answer "where are my pills?".
  False-positive risk: handling is not ingestion; privacy cost: moderate (medication routine is health data, though no new images are stored).
- Next step (B): a Gemini field for "compartment open / pill in hand" on pill-box frames, shown to family as "probably taken, please confirm", never spoken to the person as a fact.
- Ingestion confirmation from 0.5 s stills is C; AiCure needs an active, face-on video, which also conflicts with "never describe people".
- Clinical framing: adherence verification is the highest-stakes feature in this list because a wrong "not taken" can cause a double dose; it should route to a caregiver, not to the person.

### Gaps
- I found no independent, peer-reviewed sensitivity and specificity for AiCure's vision component alone.
- I could not read AiCure's poster on detecting mock ingestion (behind a form).
- A search snippet said only 25-50% of patients take medications correctly and consistently, but the source page was a university licensing site and I did not verify the primary study, so it is not in the findings.
- I found no camera-based adherence study in people with dementia.

## 5. Wandering, time per room, nighttime activity and sedentary behaviour from room-level location over time

### Takeaway
Room-level location over days is a validated digital marker: in ORCATECH cohorts, people with MCI show less stable day-to-day room-transition patterns and more kitchen activity across day and night.
Save It already writes one text-only `observations` row per processed frame with room and time, so a per-room timeline is an A-level query; the main caveats are coarse sampling when no item is in view, and that a lanyard is only informative while worn (nights especially).

### Cited Findings
- Wu et al. (Frontiers in Digital Health, 2021; 139 participants, Kaye co-author) found that lower stability of indoor room transitions was associated with MCI (beta -0.04, p=0.03), with reliable test-retest measures - [Wu et al. 2021, Frontiers](https://www.frontiersin.org/articles/10.3389/fdgth.2021.764510/full)
- A companion conference abstract (159 older adults living alone, 14% MCI, motion sensors in four rooms) reported less consistent day-to-day room-transition patterns in MCI - [Wu et al. 2021 abstract, PMC8679803](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8679803/)
- A study of 24-hour patterns found participants with MCI were more likely to be in a high-kitchen-activity group with more kitchen transitions across day and night (OR 3.2, p=.03) - [PMC9536445](https://pmc.ncbi.nlm.nih.gov/articles/PMC9536445)
- A Kaye presentation lists night-time behaviour and sleep as differentiating early MCI, citing Hayes et al. 2014 (a slide deck, not a peer-reviewed result) - [Kaye slides 2015](https://files.alz.washington.edu/presentations/2015/spring/Kaye.pdf)
- CarePredict combines a wrist wearable, room beacons and a cloud platform; its peer-reviewed pilot in assisted living measured hospitalisation, falls, length of stay and staff response time, not dementia detection - [Wilmink et al. 2020, JMIR Aging](https://aging.jmir.org/2020/2/e19554/PDF)
- The Alzheimer's Association figure that 6 in 10 people with dementia will wander, many repeatedly, is widely repeated in secondary sources - [NCCDP](https://www.nccdp.org/understanding-wandering-and-exit-seeking-in-dementia-what-caregivers-need-to-know/)
- Other studies put wandering prevalence at 11-50%, and a 2024 Canadian home-care study found recent wandering in 3.0% of clients overall, with dementia associated with about 18 times greater prevalence of critical wandering - [PMC11485082](https://pmc.ncbi.nlm.nih.gov/articles/PMC11485082)
- About 20% of community-dwelling people with dementia wander, versus about 60% in institutional settings - [Practical Neurology](https://practicalneurology.com/diseases-diagnoses/alzheimer-disease-dementias/wandering-sundowning-in-dementia/31912/)
- Exit-seeking is the subtype of wandering involving attempts to leave a building or secured area, often with urgency or distress - [NCCDP](https://www.nccdp.org/understanding-wandering-and-exit-seeking-in-dementia-what-caregivers-need-to-know/)
- Wearable cameras categorise sedentary behaviour context better than accelerometers, which mislabel standing as sedentary - [ScienceDaily on Kerr et al. 2013](https://sciencedaily.com/releases/2013/02/130205083054.htm); [Oxford NDPH, Doherty et al. 2013](https://www.ndph.ox.ac.uk/publications/394986)
- The Alzheimer's Association lists "confusion with time or place" among its 10 warning signs - [Alzheimer's Association, 10 signs](https://www.alz.org/alzheimers-dementia/10_signs)

### Inferences
- Time per room and room-transition timeline (A): a SQL view over `observations` grouped by room and hour; show it on the dashboard as a day strip.
  Resolution is about one point per 30 s when no enrolled item is visible, which is enough for minutes-per-room but not for counting quick transitions.
- Room-transition stability (B to C): computable from the same data after a few weeks, and directly comparable to Wu et al. 2021, but only meaningful with high wear compliance; as a clinical marker it is research, not a hackathon claim.
- Nighttime activity (A query, C reliability): frames between, say, 23:00 and 06:00 in the kitchen or at the front door; people rarely wear a lanyard at night, so absence of frames means nothing and false reassurance is the main risk.
- Exit-seeking (B): front door enrolled as a landmark, plus `door_open`, plus coat or keys or bag in hand, plus time of day; but the existing in-hand tracking already gives "took the keys and bag at 02:10" for free (A).
  A door contact sensor is the robust tool; the camera adds context ("left with the bag").
- Sedentary behaviour (A to B): long runs of near-identical frames in the same room; the duplicate filter already computes SSIM against the last accepted frame, so a "still" counter is cheap.
  The same signal appears when the phone is put down on a table, so it needs a wear check.
- Wear-compliance indicator (A): share of waking hours with frames; necessary to interpret every signal in this section.
- Privacy: a room-by-time log is low to moderate in cost, but gaps also reveal bathroom visits and their timing (a potential clinical signal, e.g. nocturia, that the no-capture rule was designed not to collect); I would not surface bathroom gaps as data.

### Gaps
- I did not verify the Alzheimer's Association's own page for the 6 in 10 wandering figure; the figure appears to describe lifetime risk.
- I found no study isolating nighttime room transitions as an MCI or dementia marker, and none using a wearable camera rather than motion sensors for room location.
- I found no data on how many hours a day people with dementia tolerate wearing a lanyard camera.

## 6. "Memory replay": photos of the day, reminiscence therapy, and recall of who visited

### Takeaway
Image-based review of one's own day is the best-evidenced benefit of wearable cameras for memory (Section 1), while classic reminiscence therapy has only a very small, short-lived effect on cognition (Cochrane 2018).
Save It can offer a text and crop based "my day" replay without storing scenes; "who visited" should not be done by face recognition, and even face-free person detection conflicts with the project's "never describe people" rule.

### Cited Findings
- The 2018 Cochrane review of reminiscence therapy found high-quality evidence of a very small cognitive benefit at the end of treatment (SMD 0.11, 95% CI 0.00 to 0.23; 14 studies; 1,219 participants) that was not maintained, and moderate-quality evidence of no consistent effect on wellbeing or quality of life - [Cochrane CD001120 abstract](https://www.cochranelibrary.com/cdsr/doi/10.1002/14651858.CD001120.pub3/pdf/CDSR/CD001120/CD001120_abstract.pdf)
- The same review found care-home residents showed small quality-of-life and cognitive gains not seen in community settings, individual reminiscence was associated with probable benefits for cognition and mood, and no harmful effects were found - [Cochrane CD001120 abstract](https://www.cochranelibrary.com/cdsr/doi/10.1002/14651858.CD001120.pub3/pdf/CDSR/CD001120/CD001120_abstract.pdf)
- SenseCam review of recent events beat written diaries for recall in amnesia and in 5 of 6 Alzheimer's patients - [Woodberry et al. 2015](https://www.microsoft.com/en-us/research/?p=464112); [Browne et al. 2011](https://microsoft.com/en-us/research/?p=163388)
- MemPal's design guidance recommends storing text rather than images to protect privacy - [MemPal full text](https://arxiv.org/html/2502.01801v1)
- Face-recognition products for dementia exist: MedaCareLLM glasses claim to identify familiar faces and whisper names, unevaluated - [IoT World Today](https://iotworldtoday.com/health-care/ai-powered-smart-glasses-launched-to-assist-dementia-patients)
- A 2025 IEEE concept paper tested face-recognition glasses for Alzheimer's on 18 people and 440 images and reported difficulty with non-frontal poses and poor light - [Tecnológico de Monterrey record](https://research.tec.mx/vivo-tec/display/AcademicArticleSCO_105013465367)
- A 2025 Alzheimer's and Dementia conference abstract describes face-recognition glasses with GPS for wandering, with results asserted rather than measured - [PMC12741321](https://pmc.ncbi.nlm.nih.gov/articles/PMC12741321/)
- CrossSense (University of Sussex) is running a home study of smart glasses that link objects to names and uses with voice and visual prompts; the developers claim 75% of trial users reported better quality of life, which is not peer-reviewed - [NIHR Join Dementia Research](https://www.joindementiaresearch.nihr.ac.uk/news/smart-glasses); [Ground News](https://ground.news/article/new-ai-glasses-can-help-dementia-patients-live-more-independently)
- Kelly et al.'s ethical framework flags bystander privacy as the central concern for automated wearable cameras - [Kelly et al. 2013](https://libmast.utm.my/Record/oxford-uuid:079a5a57-891d-4ad1-814d-9be593e9b63c)

### Inferences
- "What did I do this morning?" (A): a voice tool and dashboard strip that reads the room timeline and item events ("You were in the kitchen around nine, you put your glasses on the chair at ten, then you went to the garden") uses only text already stored; privacy cost low, false-positive harm low.
- "Show me my day" with pictures (B, privacy trade-off): use only the existing item crops (glasses on the chair), which keeps the crops-only rule; scene photos would be closer to SenseCam's evidence but would break the "never store a full frame" rule and capture bystanders.
- Reminiscence therapy proper (old family photos) is not a camera-stream feature; given the Cochrane effect sizes, I would not prioritise it.
- "Who visited": face recognition is out by project rule, has bystander consent problems, and the cited dementia systems are unevaluated.
  A privacy-preserving alternative is a family-entered visit log on the dashboard ("Anna visited at 3 pm") that the voice agent can read back; no vision needed.
- Even an anonymous "a person was present" detector conflicts with the current prompt rule "never describe people" and would mean more processing of bystanders, so I would treat it as out of scope.

### Gaps
- I found no study of text-only or object-crop-only daily summaries as a memory aid; the effect may differ from image review.
- I did not research biometric-privacy law (for example state biometric statutes) for face recognition in homes.

## 7. Object misplacement in unusual places as a clinical sign

### Takeaway
Putting things in unusual places and being unable to retrace steps is one of the Alzheimer's Association's 10 warning signs, and a 2019 study of 787 symptom-tracker users found "odd places" misplacement becomes significantly more common as dementia severity increases.
Save It already has the data to flag "glasses on an odd landmark" (for example the fridge) and to count such events over time; that count is clinically plausible but unvalidated as a progression measure.

### Cited Findings
- Alzheimer's Association warning sign 7, "Misplacing things and losing the ability to retrace steps": a person "may put things in unusual places" and "may lose things and be unable to go back over their steps to find them again" - [Alzheimer's Association, 10 signs](https://www.alz.org/alzheimers-dementia/10_signs)
- Better Health Channel (Victoria) distinguishes normal temporary misplacing from more-than-usual trouble with misplacing objects, putting things in the wrong place such as a wallet in the fridge, or retracing steps - [Better Health Channel](https://www.betterhealth.vic.gov.au/health/conditionsandtreatments/dementia-early-signs)
- McGarrigle et al. (International Psychogeriatrics, 2019): of 2,775 DementiaGuide users tracking three or more symptoms, 787 (28%) tracked misplacing objects - [McGarrigle et al. 2019](https://resolve.cambridge.org/core/journals/international-psychogeriatrics/article/characterizing-the-symptom-of-misplacing-objects-in-people-with-dementia-findings-from-an-online-tracking-tool/9CD88B66B66EB8D98FD9430893378794)
- In that study, 96% of misplacing trackers targeted "lost and found", 56% targeted "odd places", and odd places increased significantly with dementia severity (p < 0.001); the authors conclude that as disease advances, misplacing more often reflects odd placement than simple loss - [McGarrigle et al. 2019](https://resolve.cambridge.org/core/journals/international-psychogeriatrics/article/characterizing-the-symptom-of-misplacing-objects-in-people-with-dementia-findings-from-an-online-tracking-tool/9CD88B66B66EB8D98FD9430893378794)
- Misplacing was most strongly associated with the tracked symptoms interaction with strangers (OR 4.60), reading (3.68), shopping (3.55) and travel (3.31), and the authors call it a clinically important target for quality of life and caregiver burden - [McGarrigle et al. 2019](https://resolve.cambridge.org/core/journals/international-psychogeriatrics/article/characterizing-the-symptom-of-misplacing-objects-in-people-with-dementia-findings-from-an-online-tracking-tool/9CD88B66B66EB8D98FD9430893378794)
- The Alzheimer's Society describes hiding, hoarding and losing things in dementia, including that a person may believe someone is hiding or taking their items - [Alzheimer's Society](https://www.alzheimers.org.uk/info/20064/symptoms/87/behaviour_changes/9)
- Caregiver guidance recommends keeping items in familiar places and keeping duplicates of important items - [Alzheimer Society of PEI](https://admin.alzheimer.ca/pei/sites/pei/files/documents/Hoarding_Alzheimer-Society-PEI.pdf)

### Inferences
- "Odd place" flag (A): mark some landmarks as unusual for some item kinds (fridge, freezer, oven, bin, under a cushion) or simply flag any stay that differs from `usual` and is on a landmark never used before for that item.
  The voice answer can stay gentle ("Your glasses are in the fridge"), while the dashboard counts odd placements per week for family.
  False-positive risk is low to moderate (depends on landmark accuracy; open fridge doors are hard frames); privacy cost is low (no new data).
- Hidden-away places (drawers, under cushions, inside bags) are where items are hardest to find and where the camera is least likely to see them; Save It's `wearer_went_to` and "last seen in hand" answers are the useful fallback.
- Defusing theft accusations (A): the item's own history (a crop of the keys going into the drawer at 3 pm, picked up in the wearer's hand) is neutral evidence a caregiver can use; it is sensitive and should be family-only, never volunteered to the person.
- Trend as a clinical marker (C): McGarrigle's sample was self-selected online users choosing which symptoms to track, so an odd-placement rate from Save It is a conversation starter for a clinician, not a validated score.

### Gaps
- I found no prospective study measuring misplacement frequency objectively (by camera or sensor) against disease stage.
- I found no rigorous prevalence figure for hiding or hoarding in dementia; a consumer site's 20% estimate cites no study.

## 8. Hackathon-sized additions versus long-term research, with the candidate list

### Takeaway
The highest value-per-hour additions reuse data Save It already stores: an "odd place" flag, a "my day" text timeline from `observations`, counting water-bottle and pill-box handling, and a wear-compliance indicator.
Hazard detection (stove), activity labels and exit-seeking are one schema change away but need staged testing and honest "best effort" framing; ingestion verification, falls, nighttime monitoring and clinical decline markers are long-term research.

### Cited Findings
- Room-transition stability and kitchen activity patterns distinguish MCI in motion-sensor cohorts - [Wu et al. 2021](https://www.frontiersin.org/articles/10.3389/fdgth.2021.764510/full); [PMC9536445](https://pmc.ncbi.nlm.nih.gov/articles/PMC9536445)
- Odd-place misplacement rises with dementia severity - [McGarrigle et al. 2019](https://resolve.cambridge.org/core/journals/international-psychogeriatrics/article/characterizing-the-symptom-of-misplacing-objects-in-people-with-dementia-findings-from-an-online-tracking-tool/9CD88B66B66EB8D98FD9430893378794)
- About 20% of older people in long-term residential care were dehydrated in the DRIE cohort, with dementia among the risk factors - [DRIE cohort, PMC5018558](https://pmc.ncbi.nlm.nih.gov/articles/PMC5018558)
- Reviews note dementia raises dehydration risk because cognitive impairment and age reduce thirst recognition - [Hydration Care in Dementia Care Homes, NCT04281550](https://clinicaltrials.gov/study/NCT04281550)
- A news summary claims residents with dementia were six times more likely to be dehydrated; I could not confirm this in the peer-reviewed paper - [carehome.co.uk](https://www.carehome.co.uk/news/article.cfm/id/1572412/One-in-five-older-people-at-risk-of-dehydration-in-care-homes)
- Wearable-camera fluid-intake detection reached F1 89% for episodes but 56.7% precision for intake amount - [Encyclopedia.pub review entry](https://encyclopedia.pub/entry/46817)
- Ray-Ban Meta glasses offer hands-free Be My Eyes volunteer calls and Meta AI scene and object description for blind users; Meta's terms warn not to rely on its AI, which matters for safety tasks - [Meta accessibility page](https://www.meta.com/ai-glasses/blind-visually-impaired/); [UploadVR](https://uploadvr.com/ray-ban-meta-glasses-meta-ai-detailed-responses-blind-low-vision)
- Meta's May 2026 post describes a feature that guides wearers toward an object with live audio feedback (company claim, not independently reviewed) - [Meta newsroom, May 2026](https://about.fb.com/news/2026/05/meta-ai-wearables-changing-the-game-for-disabled-people/)
- MemPal reported 28 of 33 proactive safety reminders correctly triggered and 72% object-answer accuracy - [MemPal full text](https://arxiv.org/html/2502.01801v1)

### Inferences

#### Candidate signals and features

Feasibility: A = query or prompt change on existing data (hours); B = new Gemini schema field plus table or job (about a day); C = new model, new sensor, or clinical validation (research).
False-positive (FP) risk and privacy cost: L / M / H.

| # | Signal or feature | What it detects | Value (evidence) | Feasibility | FP risk | Privacy cost |
|---|---|---|---|---|---|---|
| 1 | Odd-place flag | Enrolled item put on an unusual landmark (fridge, oven, bin) or a never-used place | Alzheimer's Association sign 7; odd places rise with severity (McGarrigle 2019) | A | L-M | L |
| 2 | Odd-place trend for family or clinician | Weekly count of odd placements | Plausible progression signal; unvalidated (self-selected sample) | A to build, C to validate | M | L |
| 3 | "My day" text timeline (voice and dashboard) | Rooms over time plus item events, from `observations` and `sightings` | SenseCam recall benefit (Woodberry 2015, Browne 2011), though those used images | A | L | L |
| 4 | Day replay with item crops | Existing crops shown in time order | Same as 3, closer to image review, still crops-only | A to B | L | M |
| 5 | Retrace my steps | Room path before an item was last seen (extends `wearer_went_to`) | Sign 7 "unable to retrace steps" | A | L-M | L |
| 6 | Time per room | Minutes per room per day | Context for caregivers; room patterns differ in MCI (Wu 2021) | A (about 30 s resolution when no item is in view) | M (camera off reads as absence) | L-M |
| 7 | Room-transition stability | Day-to-day variability of room sequences | Lower stability associated with MCI (Wu 2021) | C (weeks of data, wear compliance, validation) | M | M |
| 8 | Kitchen activity at night | Kitchen frames between 23:00 and 06:00 | More day and night kitchen transitions in MCI (PMC9536445) | A query, C reliability (lanyard rarely worn at night) | H (false reassurance) | M |
| 9 | Left with keys and bag at night | In-hand keys or bag plus front-door landmark plus hour | Wandering and exit-seeking risk (20% community, 60% institutional) | A for in-hand plus hour, B with `door_open` | M (normal outings) | L-M |
| 10 | Stove left on, wearer walked away | Burner flame or glow seen, then wearer in another room for N minutes | Stove left on is a recognised warning sign (AAFP 2006); research gap (James and Clark 2025) | B (and SAM 3 gate must open on the hob) | M-H | L |
| 11 | Tap running or kettle left on | Visible running water or active kettle, then wearer leaves | Same family as 10; no evidence found | C until tested on staged frames | H | L |
| 12 | Front door open at night | Door ajar while the lanyard is at the door | Wandering safety; contact sensors do this better | B | M | L |
| 13 | Floor trip hazards | Cords, rugs, items on walkway floor | Fall prevention (not researched in depth here) | B | H (nuisance) | L-M |
| 14 | Hazardous items left out | Knives, cleaning products, medication bottles in reach | Guidance to lock away hazardous items (Alzheimer Society PEI) | B | M | L |
| 15 | Drink pick-ups | In-hand episodes of the enrolled water bottle per day | Dehydration about 20% in care (DRIE); thirst blunted in dementia | A (already logged as `carried`) | M (pick-up is not a sip) | L |
| 16 | Drinking at mouth | `at_mouth` field for an in-hand cup or bottle | Same; episode F1 89%, volume precision 56.7% in other populations | B | M | L-M |
| 17 | Meals eaten | `wearer_activity = eating` with plate in view | Nutrition and weight loss concerns; eating-action accuracy 89.68% free-living (review) | B | M (food seen not eaten) | M |
| 18 | Pill box handled | Enrolled pill organiser in hand, with time | Adherence support; answers "where are my pills" | A | M (handling is not ingestion) | M |
| 19 | Pill probably taken | Compartment open and pill in hand | AiCure 89.7% vs 71.9% (n.s.); wearable-camera research 92.7% | B for "probably", C for confirmed ingestion | H, with double-dose risk if told to the person | M-H |
| 20 | Sedentary runs | Long runs of near-identical frames in one room | Cameras give sedentary context better than accelerometers (Kerr 2013, Doherty 2013) | A (SSIM already computed) | M (phone set down looks the same) | L |
| 21 | Wear-compliance indicator | Share of waking hours with frames; phone lying still | Needed to interpret 6-9, 15-20 | A | L | L |
| 22 | Looking-for-something prompt | Rapid room switching with no item put down, then proactive "your glasses are on the chair" | MemPal proactive reminders 28 of 33 correct | B | M (annoying if wrong) | L |
| 23 | Theft-accusation evidence | Item history with crops showing the wearer put it away | Hiding and theft beliefs (Alzheimer's Society) | A | L | M (sensitive, family-only) |
| 24 | Phone, TV or social activity | `wearer_activity = using_phone` | Withdrawal is warning sign 9; weak link to a camera signal | B | M | M |
| 25 | Fall detection | Sudden floor view then stillness | EGOFALLS dataset; phone IMU is the better sensor | C | H | L-M |
| 26 | Who visited | Visitor identity | Desired by families, but face recognition is out by rule; dementia products unevaluated | Out of scope; use a family-entered visit log instead | H | H |
| 27 | Unopened mail or bills piling up | IADL decline (finances) | Sign 2 "challenges in planning or solving problems"; no camera evidence found | C | H | H (reads private text) |

#### Recommended "few hours" additions (in priority order)
- #1 Odd-place flag with a gentle spoken note and a dashboard badge: strongest clinical link per hour of work, no new data, directly extends the demo ("Your glasses are in the fridge, which is not where they usually go").
- #3 "My day" text timeline from `observations`, as a dashboard strip and a voice tool ("What did I do this morning?"): text only, no new storage, ties to the SenseCam evidence base.
- #15 Drink pick-ups and #18 pill-box handling as daily counts on the dashboard: zero model work, uses the existing `carried` state; label clearly as "picked up", not "drank" or "took".
- #21 Wear-compliance indicator: makes every other number honest and prevents false reassurance.

#### Long-term research (do not claim for the demo)
- Ingestion verification (#19), falls (#25), tap and kettle state (#11), room-transition stability or nighttime patterns as decline markers (#7, #8), validating odd-place rate against disease stage (#2), and any person or visitor detection (#26).

#### Cross-cutting cautions
- Safety alerts would live on the write path, which "may fail softly" by design; they must be labelled best-effort, and the pitch must not claim to prevent fires, wandering or missed doses.
- Every new Gemini field means more analysis of each frame by a third party; the no-capture rule stops storage, not transmission (D12), so new fields should stay text-only and avoid describing people.
- Health-adjacent fields (eating, drinking, medication) raise the sensitivity of the database; keep the "HIPAA-style safeguards" framing and never "HIPAA compliant".
- Bathroom gaps in the timeline are themselves revealing; do not display or analyse them.
- Absence of frames is not absence of activity (lanyard off, gate closed, unsure room); every derived signal needs the wear-compliance context next to it.

### Gaps
- None of the candidate features above has been tested on Save It's own staged frames; feasibility ratings are my inference from the pipeline design and the cited accuracy figures.
- A search snippet reported a small care-home study (18 residents, mostly with dementia) where 15 of 18 did not meet recommended fluid intake (mean 1,065 ml a day), but I could not confirm which paper it came from, so it is not cited above.
- I found no product that derives safety or ADL signals from a passive body-worn camera for dementia care; Sensi.ai (audio-based) was named in the brief but I did not research it.
