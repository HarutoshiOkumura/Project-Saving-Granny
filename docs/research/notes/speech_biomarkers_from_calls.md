# Speech and conversation biomarkers of cognitive decline from routine assistant calls

Scope: which speech and language markers are validated for MCI and Alzheimer's disease (AD), how well they work, which survive short task-specific assistant calls like "where are my glasses?", what is known about sudden change, how to compute them without storing audio, the legal and ethical limits, and a minimal metric set Save It could log.
Research date: 15 Nov 2026.
Nothing below is a diagnosis or a validated clinical claim for Save It; places where a feature would become a medical-device claim are marked.

Save It context used for the recommendations (from the repo, not the web): every question already lands in the `queries` table with `asked_at`, `channel`, `heard` (speech-to-text output), `item_id`, `state` (what `find_item` returned) and `outcome` (`found` / `not_found`), see `supabase/migrations/0001_save_it_memory.sql`.

## 1. Which acoustic and linguistic markers distinguish MCI/AD from healthy ageing, and how accurate are they?

### Takeaway
On long, structured tasks (picture description, interviews, fluency) automated speech analysis separates AD from controls at roughly 78-90% accuracy and MCI from controls at roughly 70-85%, using a mix of pause/tempo features (acoustic) and content, lexical and syntactic features (linguistic).
The strongest and most repeated single signals are more and longer pauses / hesitations, slower speech tempo, fewer information units (semantic content), vaguer word choice, and repetition; almost all results come from small, English-heavy, cross-sectional datasets with very little external validation.

### Cited Findings

Reviews
- A systematic review (2000-2019 literature, PROSPERO CRD42018116606) screened 3,654 records and kept 51 studies; nearly all reported promising results, but very few had been implemented in clinical research or practice - [de la Fuente Garcia, Ritchie, Luz 2020, J Alzheimers Dis 78:1547-1574](https://pmc.ncbi.nlm.nih.gov/articles/PMC7836050); [arXiv preprint](https://arxiv.org/pdf/2010.06047)
- A ten-year review of automatic voice and speech analysis included 35 papers (11 descriptive, 24 diagnostic), judged them of good quality (JBI, QUADAS-2), and found most report diagnostic accuracy over 88% for AD and over 80% for MCI - [Martinez-Nicolas et al. 2021, Frontiers in Psychology](https://www.frontiersin.org/articles/10.3389/fpsyg.2021.620251/full)
- That review cites earlier work (Singh et al. 2001) where verbal rate, mean pause duration and standardised phonation time discriminated healthy older people from people with AD - [Martinez-Nicolas et al. 2021](https://www.frontiersin.org/articles/10.3389/fpsyg.2021.620251/full)
- A 2026 narrative review lists the main barriers as demographic and language/dialect bias, task and label heterogeneity, device/environment domain shift, and error propagation from automatic speech recognition (ASR) - [JMAI narrative review 2026](https://jmai.amegroups.org/article/view/10893/html)
- A roadmap paper reports that of 86 AI models for AD reviewed, only 2 had undergone external validation, and that speech models are mostly trained on small homogeneous cohorts - [AI4X Roadmap, arXiv 2511.20976](https://arxiv.org/pdf/2511.20976)

DementiaBank Pitt corpus and the ADReSS challenges (Cookie Theft picture description)
- Fraser, Meltzer and Rudzicz used 240 picture descriptions from 167 people with possible/probable AD and 233 from 97 controls (DementiaBank), extracted linguistic and acoustic features, and reached about 82% accuracy with 35 features - [Fraser et al. 2016, J Alzheimers Dis 49(2):407-422](https://pubmed.ncbi.nlm.nih.gov/26484921/); [author PDF](https://www.cs.utoronto.ca/~kfraser/Fraser15-JAD.pdf)
- Their factor analysis grouped the impairments into semantics, acoustics, syntax and descriptive clarity (information content); the acoustic contribution was described by the authors as "somewhat unanticipated" - [Psychiatric News 2016](https://psychnews.psychiatryonline.org/doi/10.1176/appi.pn.2016.1b4)
- ADReSS 2020 released an age- and gender-balanced subset of DementiaBank with two tasks (AD vs control classification, MMSE regression) - [Luz et al., Interspeech 2020](https://www.isca-archive.org/interspeech_2020/luz20_interspeech.html)
- Reported ADReSS 2020 test-set accuracies include 89.6% (Yuan et al.) and 85.45% (Syed et al.); these are not comparable with ADReSSo numbers - [ADReSSo-era comparison, Frontiers in Computer Science 2021](https://www.frontiersin.org/journals/computer-science/articles/10.3389/fcomp.2021.780169/pdf)
- ADReSS 2020 attracted 34 teams - [Luz et al. 2021, ADReSSo overview, arXiv 2106.08689](https://arxiv.org/abs/2106.08689v1)
- ADReSSo 2021 gave only audio plus uncorrected ASR output (no manual transcripts): 237 recordings, 166 train / 71 test, balanced for gender and AD status - [Luz et al., Interspeech 2021](https://www.isca-archive.org/interspeech_2021/luz21_interspeech.html); [arXiv](https://arxiv.org/abs/2106.08689v1)
- ADReSSo baseline was 78.87% accuracy for AD classification (acoustic plus linguistic features from audio without human intervention), MMSE regression RMSE 5.28, and 68.75% for the cognitive-decline prediction task - [Luz et al. 2021, arXiv](https://arxiv.org/abs/2106.08689v1)
- Teams reported 81.69% (Chen et al.) and 83.1% (Qiao et al.) on the ADReSSo test set, i.e. a few points over baseline - [Frontiers in Computer Science 2021](https://www.frontiersin.org/journals/computer-science/articles/10.3389/fcomp.2021.780169/pdf); [secondary summary](https://api.emergentmind.com/topics/adresso-2021-challenge)

MCI-specific acoustic/temporal work
- Toth et al. (Hungarian) compared 48 MCI patients and 38 controls using temporal parameters (hesitation ratio, speech tempo, number and length of pauses), extracted both by hand in Praat and automatically from an ASR system; the largest group differences were speech tempo in delayed recall and number of pauses in question answering, and hesitation was described as the most important MCI indicator - [Toth et al. 2018, Current Alzheimer Research](https://rgai.inf.u-szeged.hu/node/20); [PDF](https://www.inf.u-szeged.hu/~ggabor/publlist/2018-car.pdf)
- A later cross-lingual study by the same group found no performance difference between mono- and cross-lingual MCI detection from temporal speech parameters - [Gosztolya et al. 2021, Computer Speech & Language (record)](https://katalog.lib.cas.cz/KNAV/EdsRecord/edsair,edsair.doi...........a792abf1a430dd2285893febd43ace05)
- In the Wisconsin Registry for Alzheimer's Prevention, 39 people with preclinical amnestic MCI vs 39 matched controls differed mainly on content measures (number of semantic units, unique words) in Cookie Theft descriptions - [Mueller et al. 2016, J Alzheimers Dis (record)](https://experts.mcmaster.ca/scholarly-works/1725604)

Conversation and interaction features (closest to Save It's setting)
- In the Carolinas Conversation Collection (15 AD vs 15 non-AD patients, spontaneous interviews), AD and non-AD differed on lapses, gaps, attributable silences, turn switches per minute and turn length; interactional features alone gave 83% accuracy and 90% combined with disfluency features - [Nasreen, Hough, Purver 2021, Frontiers in Computer Science](https://www.frontiersin.org/articles/10.3389/fcomp.2021.640669/text)
- A companion paper reported 87% accuracy for interactional (pausing and floor-control) features alone and 90% combined with acoustic features, and argued these can be extracted from everyday conversation - [Nasreen et al., Interspeech 2021](https://www.isca-archive.org/interspeech_2021/nasreen21_interspeech.html)
- Sheffield's virtual-agent work used acoustic, lexical and conversation-analysis-inspired features; neurodegenerative vs functional memory disorder classification reached 90.0% on neurologist-patient conversations, and patients' average turn length differed between virtual-agent and human-led conversations - [Mirheidari et al. 2019, Computer Speech & Language (author version)](https://eprints.whiterose.ac.uk/id/eprint/136339/8/CSL_2018_Revised.pdf)
- CognoSpeak (a virtual agent asking memory questions plus fluency and picture tasks, done remotely) reached F1 0.873 with DistilBERT for cognitive impairment vs healthy volunteers in 126 subjects - [Pahar et al. 2025, arXiv 2501.05755](https://arxiv.org/html/2501.05755v1)

Telephone speech
- Speech recorded over the telephone (about 20-minute call: 1-minute animal fluency plus a free childhood memory) from 91 community-dwelling older adults (one third each mild AD, amnestic MCI, healthy) was good enough for NLP; the models separated the three groups more accurately than two traditional screeners and a clinician reading transcripts - [Diaz-Asper et al. 2022, Cortex 156:26-38](https://doi.org/10.1016/j.cortex.2022.08.005); [author PDF](https://ckchandler.github.io/files/publications/diazasper_cortex2022.pdf)
- An MIT Lincoln Laboratory analysis of audio from an automated telephone (IVR) system used in the Alzheimer's Disease Cooperative Study home assessments reported an average equal error rate of 13.5% - [Yu et al., Interspeech 2015](https://www.isca-archive.org/interspeech_2015/yu15b_interspeech.pdf)
- An Italian study found acoustic features of continuous speech separated normal from mildly impaired cognition, with accuracy up to 0.80 when age and education were added, and proposed analysing voice during phone calls (search-result abstract only) - [record](https://vufind.katalog.k.utb.cz/SummonRecord/FETCH-LOGICAL-i302t-f067e1a99c7318cf95dcb8bf429788a4cf9bfb704dec99b24ace1eb089e221fa3)
- ki:elements' Speech Biomarker for Cognition (70 speech features) delivered by an AI voice agent in a 10-minute phone call was tested in 736 participants across five cohorts (Spain, UK, Germany, Sweden), with AUC up to 0.74 for amyloid-beta positivity and up to 0.82 for p-tau181 positivity; this is vendor-led (corresponding author is the company's chief clinical research officer) and reported via trade press - [HospiMedica, 22 May 2026](https://mobile.hospimedica.com/ai/articles/294810750/automated-phone-speech-test-identifies-alzheimers-pathology-for-prescreening.amp.html)

Framingham Heart Study voice recordings
- The FHS voice archive analysis covered 7,874 recordings from 4,950 participants (453 with MCI), relating acoustic features to neuropsychological test scores - [JMIR 2022](https://jmir.org/2022/12/e42886/PDF)
- A matched FHS sample of 100 MCI cases and 100 controls was used to build acoustic MCI detection - [JMIR Aging 2024](https://aging.jmir.org/2024/1/e55126/PDF)

Commercial programs (vendor claims, flagged)
- Sonde Cognitive Fitness tracks "cognitive effort" from eight vocal features and is marketed as not a diagnostic tool - [Sonde Health press release](https://www.sondehealth.com/news-blog/sonde-health-introduces-innovative-cognitive-fitness-health-tracking-solution)
- Canary Speech's CEO-authored marketing claims a 40-second voice sample can screen several conditions at once; no peer-reviewed accuracy was found in this search - [Canary Speech blog](https://canaryspeech.com/blog/5-vocal-biomarker-trends-to-watch/)

### Inferences
- The markers with the most cross-study agreement are temporal (pause count, pause length, hesitation ratio, speech tempo) and content (information units, unique content words, vague placeholders); syntax and lexical diversity are less consistent, and Mueller 2018 (question 2) found they did not track early decline.
- Accuracy numbers in the 80-90% range come from balanced, small, curated, mostly English datasets with picture description; they should be read as "there is signal", not as expected performance in a home with one speaker, short calls and a commercial ASR.
- Interactional features (gaps before replies, lapses, turn length, turns per minute) are the family of markers that most naturally exists in an assistant call, and they are computable from timestamps without the words.

### Gaps
- I could not open the full ADReSS 2020 paper to confirm dataset size and baseline numbers (commonly cited as 156 speakers and a 75% baseline, but not verified here).
- König et al. (2015, 2018) accuracy figures for MCI vs AD vs controls were not retrieved.
- Winterlight Labs' cross-sectional accuracy papers and Linus Health's voice component accuracy were not retrieved; Cambridge Cognition now hosts Winterlight's study write-ups (see question 2 source), but I did not verify the acquisition terms.
- Feature-by-feature effect sizes (pooled) for pause and rate measures were not available in the reviews' abstracts.

## 2. Longitudinal evidence: does within-person speech change track progression or predict MCI-to-AD conversion? Any repeated naturalistic speech (phone, voice assistants)?

### Takeaway
There is moderate evidence that speech predicts future diagnosis (AUC about 0.74, accuracy about 70-79%) and that a speech composite can track 18-month change about as sensitively as the CDR Sum of Boxes in early AD, but all of it uses structured clinical tasks recorded a few times a year.
Evidence for dense, repeated naturalistic speech (daily assistant commands) is limited to one small 18-month Alexa pilot (15 home users) that classifies MCI vs healthy at about 74% accuracy; nobody has shown within-person change detection from everyday assistant calls.

### Cited Findings

Predicting future diagnosis
- Framingham (Eyigoz et al.): linguistic variables from a single Cookie Theft description (written, not spoken) in cognitively normal people predicted later AD onset with AUC 0.74 and accuracy 0.70; mean time to mild AD diagnosis was 7.59 years; 703 samples from 270 participants, with a held-out test set of 80 - [Eyigoz et al. 2020, EClinicalMedicine](https://pmc.ncbi.nlm.nih.gov/articles/PMC7700896)
- Eyigoz et al. report that these linguistic variables outperformed models using APOE, demographics and neuropsychological tests; telegraphic speech, repetitiveness and agraphia (punctuation and spelling errors) marked future onset - [Eyigoz et al. 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7700896)
- That study was funded by Pfizer with IBM Research involvement, and press accounts gave 75% vs the paper's 70% accuracy - [Eyigoz et al. 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7700896); [Psychology Today 2020](https://www.psychologytoday.com/nz/blog/the-future-brain/202010/ai-could-help-predict-alzheimer-s-disease-early-using-language)
- Framingham (Amini et al.): automated transcription plus language models on neuropsychological test interviews of 166 people with MCI (90 who progressed, 76 stable) predicted progression to AD within six years with 78.5% accuracy and 81.1% sensitivity - [Amini et al. 2024, Alzheimer's & Dementia, doi 10.1002/alz.13886](https://doi.org/10.1002/alz.13886); [Boston University summary](https://www.bu.edu/hic/2024/06/25/the-brink-boston-university-ai-method-early-prediction-alzeimers)

Tracking change over time
- Wisconsin Registry: picture descriptions from 264 participants at two time points; people classified as very early MCI declined faster in speech fluency and semantic content than stable peers, while lexical diversity and grammatical complexity were not associated - [Mueller et al. 2018, Frontiers in Aging Neuroscience](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5767238/)
- Winterlight/Genentech: speech from Clinical Dementia Rating interviews at baseline, 6, 12 and 18 months in 101 participants with prodromal-to-mild AD (Tauriel trial); a composite of acoustic and linguistic features changed over time with an effect size (beta 0.29) similar to CDR Sum of Boxes (beta 0.30), and a held-out set of 26 showed similar progression - [Xu et al. 2023, Alzheimer's & Dementia: DADM (PMC10286224)](https://rcastoragev2.blob.core.windows.net/8286c328c4b6f1e2ded71401d6057767/DAD2-15-e12445.PMC10286224.pdf); [NeurologyLive](https://www.neurologylive.com/view/composite-speech-score-detects-longitudinal-cognitive-changes-better-than-some-traditional-measures); [Cambridge Cognition summary](https://cambridgecognition.com/speech-based-biomarkers-for-monitoring-progressive-changes-in-alzheimers-disease/)
- Public figures on YouTube: 110 speech samples from 17 public figures (9 later developed AD), 456 language features; 5-minute samples tracked disease evolution more reliably than 1-minute samples - [Petti, Baker, Korhonen, Robin 2023, Digital Biomarkers](https://karger.com/dib/article/7/1/157/870178/How-Much-Speech-Data-Is-Needed-for-Tracking)
- In cognitively unimpaired adults doing remote, repeated tablet speech tasks over five days, averaged features reached high test-retest reliability (ICC 0.75 or more); this comes from a search summary that I did not confirm in full text - [PMC11293000](https://pmc.ncbi.nlm.nih.gov/articles/PMC11293000)

Repeated naturalistic speech with voice assistants
- An 18-month at-home Alexa pilot (2022-2024) enrolled 35 adults aged 65 or older; 15 (8 MCI, 7 healthy by MoCA cut-off 26) used Alexa daily at home and produced about 47 commands per person per week, with seven quarterly Zoom sessions including MoCA - [Qi et al., Cog-TiPRO, arXiv 2505.17137](https://arxiv.org/abs/2505.17137)
- Using monthly HuBERT acoustic embeddings plus LLM-summarised linguistic features and a time-series transformer, leave-one-subject-out classification of MCI vs healthy reached 73.80% accuracy and 72.67% F1; acoustic features alone gave 66.67%, removing temporal modelling dropped accuracy to 60.00% and removing acoustics to 64.39% - [Qi et al. 2025](https://arxiv.org/abs/2505.17137)
- The earlier controlled study collected 1,685 Alexa commands from 18 healthy and 22 MCI older adults and extracted 163 command features; the most influential feature sets were overall performance, music-related commands, call-related commands and features from Alexa's ASR - [Liang et al. 2022, Computer Speech & Language 72](https://www.cs.dartmouth.edu/dfk/research/liang-vas/index.html); [UMass Boston record](https://collaborate.umb.edu/en/publications/evaluating-voice-assistant-commands-for-dementia-detection/)
- Reported accuracy for Liang et al. 2022 conflicts between sources: 80-90% for decision tree / random forest on selected features in one abstract, and 68% for fusion features with MoCA regression RMSE 3.53 in another listing - [Dartmouth page](https://www.cs.dartmouth.edu/dfk/research/liang-vas/index.html); [UNC record](https://ccpah.cpc.unc.edu/resources/publications/bib/14707/)
- The same group's audio is shared through DementiaBank as a voice-assistant corpus - [Liang et al., DementiaBank document](https://dementia.talkbank.org/access/0docs/Liang23.pdf)

### Inferences
- The longitudinal evidence supports "speech changes as AD progresses" at the group level over 6-18 month intervals; it does not yet support detecting a single person's decline from weeks of short calls.
- Save It's natural advantage is density (many calls a week) and a fixed task, which is exactly what the 5-day averaging and the Alexa pilot suggest can buy reliability; its disadvantage is that each call carries maybe 5-20 words from the caller.
- A within-person design (each caller is their own baseline) is the only realistic framing; Save It would never have the labels (MoCA, diagnosis) needed to train a classifier, and should not try.

### Gaps
- No study found that used telephone check-ins or voice-assistant logs to predict MCI-to-AD conversion.
- No published within-person change-point analysis of daily assistant use was found; Cog-TiPRO predicts a fixed label, not change.
- I did not find whether Amazon, Google or Apple run any cognitive-decline detection on assistant data.

## 3. Do markers survive short, constrained utterances? Minimum duration? What can repeated near-identical prompts provide?

### Takeaway
Classic acoustic and lexical markers degrade sharply on short samples: no validated minimum exists, studies use 1-5 minutes or 150+ words, and acoustic features lose reproducibility as samples shorten.
What does survive in short assistant interactions is behavioural and interactional: repeated identical requests within seconds, vague placeholders instead of names, abandoned self-corrections, failure to recover from a misunderstood command, very short commands, filler pauses before the command, and the pattern of turns, gaps and repeats around a fixed task.

### Cited Findings

How much speech is needed
- No standard exists: studies have used 150-word interviews, 1-minute, 4-minute and 1,400-word samples - [Petti et al. 2023, Digital Biomarkers](https://karger.com/dib/article/7/1/157/870178/How-Much-Speech-Data-Is-Needed-for-Tracking)
- 5-minute samples tracked AD-related change more reliably than 1-minute samples - [Petti et al. 2023](https://karger.com/dib/article/7/1/157/870178/How-Much-Speech-Data-Is-Needed-for-Tracking)
- In 185 English-speaking adults, bio-acoustic features were less reproducible in shorter samples and were affected by gender; about 97% of features were not reproducible across tasks, partly because one task was short - [Almaghrabi et al. 2022, IEEE TNSRE](https://doaj.org/article/4f2470feb51d470face5a21ba5ad427d)

What short assistant commands show
- Commands to voice assistants are short and unstructured, unlike the spontaneous speech used in clinical assessments, which the Cog-TiPRO authors name as the core analysis challenge - [Qi et al. 2025](https://arxiv.org/abs/2505.17137)
- LLM-extracted features that distinguished MCI from healthy users in daily Alexa commands were: vague placeholders and context-mismatched nouns ("that thing", "turn off the rock"); abrupt topic jumps; abandoned self-corrections and persisting with failed commands; weaker grammar and imperative-only style; bursts of 3 or more identical requests within 30 seconds and re-asking the same information despite an immediate answer; narrow use (alarm, light, volume) and very short commands; filler pauses before commands - [Qi et al. 2025, Table III](https://arxiv.org/abs/2505.17137)
- The same paper reports that MCI participants were less able to respond to unsuccessful attempts or ask useful follow-ups, while healthy participants showed more varied vocabulary and information-seeking - [Qi et al. 2025](https://arxiv.org/abs/2505.17137)
- Generating a command (the person decides what to say) carried more cognitive load and detected MCI better than reading a command aloud, in 35 participants over seven sessions; intent and audio features were more sensitive than textual features - [Liang group preprint, arXiv 2411.04158](https://arxiv.org/html/2411.04158v1)
- Among Alexa command features, ASR-derived features (how well Alexa understood the person) and overall task performance were among the most influential - [Liang et al. 2022](https://www.cs.dartmouth.edu/dfk/research/liang-vas/index.html)

Interaction structure in short exchanges
- Gaps at turn changes, lapses, attributable silences, turns per minute and turn length separated AD from non-AD in conversations - [Nasreen et al. 2021](https://www.frontiersin.org/articles/10.3389/fcomp.2021.640669/text)
- In Hungarian MCI work, the number of pauses during a question-answering task was among the most significant differences - [Toth et al. 2018](https://rgai.inf.u-szeged.hu/node/20)
- Repetitiveness is one of the linguistic markers that predicted future AD onset - [Eyigoz et al. 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7700896)

### Inferences
- Per-call acoustic biomarkers (jitter, shimmer, spectral features, articulation rate) from a 3-second "where are my glasses?" are not defensible; at best they could be pooled across a week of calls, and even then device, network codec (FaceTime) and room noise will dominate.
- Save It's question is a natural standardised task: same intent, same assistant, same answer format, many times a week.
  That makes within-person interactional measures more interpretable than in free conversation, because the task demand is held roughly constant (analogous to, but not validated like, the command-generation task above).
- Candidate task-anchored measures, all inferred from the cited behaviours rather than validated: response latency after the agent finishes speaking; number of turns to resolution; number of clarification turns the agent needed; whether the caller asks for the answer to be repeated; re-asking the same item within the same call or within minutes of a confident answer; use of vague or wrong item names (resulting in `unknown_item`); and whether the caller reports finding it (`outcome`).
- Repeat asking is confounded by product adoption: Save It invites repeated questions, so a rising count may mean the person trusts and likes it, not that they are declining.
  Only within-call repeats and repeats within minutes after a confident `seen` answer approximate the "re-asking despite an immediate answer" marker.

### Gaps
- No study was found that tested speech markers on a fixed single question repeated over weeks (an "N-of-1 repeated probe" design).
- No minimum-duration validation exists specifically for MCI/AD linguistic features; the Petti and Almaghrabi studies are small or not in a cognitive cohort.
- Canary Speech's "40 seconds is enough" claim was not backed by a peer-reviewed source I could find.

## 4. Sudden change: do speech markers shift with delirium, infection, hypoglycaemia, sedation or stroke?

### Takeaway
Yes in principle, but the evidence is small and mostly from structured tasks in clinical settings: delirium (one 33-patient study, 78% accuracy), hypoglycaemia (22 people, AUROC 0.87-0.90 on reading and syllable tasks) and stroke (speech-only around 75% sensitivity in one secondary report; multimodal tools do better).
Nothing validates acute-change detection from short assistant calls, so Save It should frame any sudden-change signal as "calls look different this week, check in", never as a delirium or stroke alert.

### Cited Findings
- Delirium: in 33 hospitalised older adults (10 with delirium), the delirium group had more language disturbance and incoherence and lower category fluency; adding computational language features raised delirium classification accuracy to 78%; the authors call the results preliminary - [Tang et al. 2023, J Psychiatry Neurosci 48(4):E255](https://www.jpn.ca/content/48/4/E255); [PMC10322161](https://pmc.ncbi.nlm.nih.gov/articles/PMC10322161)
- An NIH-funded study at the Feinstein Institutes is testing digital speech biomarkers to identify delirium and predict cognitive decline in hospitalised adults aged 75+ - [NIH project listing](https://www.findatrial.com/research/using-speech-analysis-to-identify-delirium-and-predict-cognitive-decline-in-olde-NIH-10806491)
- Hypoglycaemia: 540 smartphone recordings from 22 people with type 1 diabetes; a machine-learning model detected hypoglycaemia from voice with AUROC 0.90 (reading text) and 0.87 (rapid syllable repetition); the team next plans to test everyday speech such as voice-assistant use - [University of Bern media release on Lehmann et al., Diabetes Care 2025](https://mediarelations.unibe.ch/media_releases/2025/media_releases_2025/low_blood_sugar_detected_by_speaking_into_a_smartphone/index_eng.html)
- A related completed trial enrolled 7 participants to identify vocal biomarkers of hypoglycaemia - [HypoVoice, NCT05569876](https://clinicaltrials.gov/study/NCT05569876)
- Stroke: a smartphone tool combining speech and facial movement reached 79% accuracy on an emergency-department dataset, comparable to ER physicians (Penn State / Houston Methodist, 80+ patients) - [Penn State 2020](https://www.psu.edu/news/research/story/new-tool-can-diagnose-strokes-smartphone)
- A smartphone app's speech component detected slurred speech with 75% sensitivity and 75% specificity, while the combined face/arm/speech output reached 99% sensitivity and 90% specificity (secondary news report only) - [MIMS](https://www.mims.com/india/news-updates/topic/ai-as-accurate-as-neurologists-in-detecting-acute-stroke--bell-s-palsy)
- A 2025 conference abstract (10 large-vessel-occlusion strokes vs 10 controls, iPhone speech) reported wav2vec2 AUC 0.89-0.97, a feasibility result - [Digital Health and Wellbeing abstract](https://openjournals.library.sydney.edu.au/DHW/article/view/21470)

### Inferences
- Acute states plausibly show up in Save It's interaction metrics as a step change: many more calls, more repeats within a call, longer gaps, more `unknown_item` mishearings, more calls at unusual hours.
  That is consistent with the delirium findings (incoherence, lower fluency) but not tested.
- A family-facing "unusual week" notice is defensible as a descriptive observation; naming a cause (infection, delirium, stroke, low sugar) would be a diagnostic claim and is clinically unsafe because a 1-2 day delay or a false reassurance can matter.
- For stroke, slurred speech is a FAST sign, so the only responsible product behaviour is the existing emergency script ("if you feel unwell, call 911 or press your help button"), not a detector.

### Gaps
- No studies found on speech changes from sedating medications (benzodiazepines, anticholinergics, opioids) or infection without delirium in older adults with dementia.
- No studies found on "delirium superimposed on dementia" detected from speech, which is the actual Save It population.
- I could not open the Diabetes Care paper itself; figures are from the university release.

## 5. Practical stack: can markers be computed from ASR transcripts and timestamps alone? ASR error rates and bias

### Takeaway
Yes for most interactional and temporal markers (latency, gaps, turns, words per turn, repeats) and for content markers that tolerate ASR noise; ADReSSo showed about 79-83% AD accuracy from uncorrected ASR plus audio features, and Hungarian MCI work extracted pause and tempo features automatically from ASR output.
But ASR errors are systematically higher for people with dementia (Cohn et al. 2026, 83 older adults, Alexa) and for Black speakers (Koenecke et al. 2020, WER 0.35 vs 0.19), and the acoustic traits that predict ASR failure (low intensity, voice quality, pause ratio) overlap with the cognitive markers themselves, so transcript-derived markers are biased in the direction of the disease.

### Cited Findings
- ADReSSo deliberately supplied only audio and uncorrected ASR output (no manual transcripts); the fully automatic baseline reached 78.87% for AD classification - [Luz et al. 2021](https://arxiv.org/abs/2106.08689v1)
- Toth et al. computed hesitation ratio, tempo and pause features automatically with an ASR-based tool, as well as manually in Praat - [Toth et al. 2018](https://rgai.inf.u-szeged.hu/node/20)
- Telephone-quality audio was sufficient for NLP-based separation of AD, aMCI and healthy controls despite variable recording quality - [Diaz-Asper et al. 2022](https://doi.org/10.1016/j.cortex.2022.08.005)
- Cohn et al. tested ASR (Amazon Alexa) on 83 older adults (cognitively normal, MCI, dementia) reading voice-assistant commands; ASR errors were significantly higher for people with dementia, and speaker intensity, voice quality and pause ratio predicted ASR accuracy - [Cohn et al. 2026, arXiv 2602.23436](https://arxiv.org/abs/2602.23436)
- Cohn et al. recommend speaker-personalised ASR, human-in-the-loop transcript correction and interaction-level personalisation - [Cohn et al. 2026](https://arxiv.org/abs/2602.23436)
- The PDF header states the paper was accepted to CHI 2026; a secondary summary gives WER about 0.21 for dementia vs about 0.08 for cognitively normal speakers with MCI not significantly different, which I could not confirm in the paper - [search summary of arXiv PDF](https://arxiv.org/pdf/2602.23436); [secondary review](https://a11y-paradise.onrender.com/reviews/69e6e64a2b9f98a10479f43a)
- Five commercial ASR systems averaged WER 0.35 for Black speakers vs 0.19 for white speakers, and the gap held on identical phrases, pointing to acoustic models rather than vocabulary - [Koenecke et al. 2020, PNAS 117(14):7684-7689](https://ideas.repec.org/a/nas/journl/v117y2020p7684-7689.html)
- In the Alexa studies, Alexa's own ASR behaviour was one of the most informative feature groups - [Liang et al. 2022](https://www.cs.dartmouth.edu/dfk/research/liang-vas/index.html)
- The Cog-TiPRO pipeline had to discard ASR failure cases ("audio could not be understood"), wrong-device triggers and empty commands before analysis - [Qi et al. 2025](https://arxiv.org/abs/2505.17137)

### Inferences
- Save It can compute almost all recommended markers from (a) per-turn start and end timestamps for caller and agent, (b) the transcript text of each caller turn, and (c) what the agent did (state, clarification asked, outcome), then discard audio.
  No raw audio and no voice embeddings need to be stored.
- Transcript-derived markers inherit ASR bias in a dangerous direction: a person who speaks more quietly or haltingly gets more misrecognitions, which looks like "more word-finding trouble" and "more clarification turns". The mitigation is to also log an ASR-quality proxy (the agent had to ask "sorry, which item?" or the query hit `unknown_item`) and to read trends within one person, never across people.
- Many production ASR systems normalise away fillers ("um", "uh") and false starts, so filled-pause counts from a Gemini Live transcript would be unreliable; pause and gap measures from timestamps are more robust than counting fillers in text.
- Keeping transcripts is itself the most sensitive part; derived counts per call (numbers only) carry most of the signal for trend purposes.

### Gaps
- I did not verify whether Gemini Live's input transcription in the LiveKit agent exposes word-level or turn-level timestamps and confidence, or keeps disfluencies; this must be checked in the LiveKit Agents and Gemini Live docs before designing the logger (project rule: do not guess third-party shapes).
- I did not find WER figures for Gemini Live or Whisper on dementia speech specifically.
- No study quantified how much ASR error inflates specific linguistic markers (e.g. type-token ratio) in dementia speech.

## 6. Ethics and law: consent capacity, recording consent, biometric laws, FDA status, fairness

### Takeaway
Consent is the hardest problem: capacity fluctuates and declines, so studies use a legally authorised representative plus ongoing assent from the person; Georgia allows one-party audio recording (but all-party consent for video in private places), while about 11-15 states (incl. California, Florida, Illinois, Washington) require all-party consent for calls.
Voiceprint laws (Illinois BIPA with a private right of action, Texas CUBI, Washington RCW 19.375) are a live litigation risk for anything that stores voice-derived identifiers; no speech-based cognitive tool appears to have FDA 510(k) clearance as of this research, and any feature that claims to detect, score or monitor cognitive decline would fall under device rules (21 CFR 882.1470 at minimum).

### Cited Findings

Consent capacity
- Frequent lack of decision-making capacity in people with dementia creates specific ethical problems for sensor-based surveillance; the paper proposes when such monitoring can be justified without legally valid informed consent - [Ethics of Sensor-Based Surveillance of People with Dementia, 2025](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11990963/)
- A 2026 scoping review notes that ambient sensing can collect data without any physical engagement, raising the risk of non-consensual data collection, and that wearables are often treated as implying consent, which may not hold in dementia - [arXiv 2603.05516](https://arxiv.org/pdf/2603.05516)
- A dementia caregiver monitoring trial used caregiver consent, legally authorised representative consent and HIPAA forms, plus verbal assent from the person with dementia, with assent only when SLUMS score was below 20 - [NCT03665909 protocol](https://cdn.clinicaltrials.gov/large-docs/09/NCT03665909/Prot_SAP_003.pdf)
- In the telephone speech study, authorised representatives also consented for participants in the mild AD group - [Diaz-Asper et al. 2022](https://doi.org/10.1016/j.cortex.2022.08.005)
- In the 18-month Alexa pilot, participants raised data-privacy concerns that the authors list as a limitation to address - [Qi et al. 2025](https://arxiv.org/abs/2505.17137)

Recording consent
- Georgia: O.C.G.A. 16-11-66 allows a party to a conversation, or someone with one party's prior consent, to record it - [Justia, O.C.G.A. 16-11-66](https://law.justia.com/codes/georgia/2022/title-16/chapter-11/article-3/part-1/section-16-11-66)
- Georgia's one-party rule covers sound; recording video (images) in a private place requires consent of all persons observed - [Georgia wiretapping laws overview](https://en.wikipedia.org/wiki/Georgia_(U.S._state)_wiretapping_laws); [DMLP Georgia recording law](https://www.dmlp.org/node/1293)
- All-party consent for phone calls is commonly listed for California, Delaware, Florida, Illinois, Maryland, Massachusetts, Montana, Nevada, New Hampshire, Pennsylvania and Washington, but counts vary between 11 and 15 depending on how states with mixed rules are classified - [Rev call recording laws](https://www.rev.com/blog/productivity/phone-call-recording-laws-state); [Vibe one/two-party states](https://vibe.us/blog/one-party-two-party-consent-states/)
- Guides for AI voice agents treat the agent's operator as needing consent under all-party states when calls are recorded or transcribed - [Thoughtly AI voice agents guide](https://thoughtly.com/blog/call-recording-consent-ai-voice-agents-state-guide)

Biometric and voiceprint laws
- BIPA voiceprint litigation is rising; one case alleged McDonald's collected customers' voiceprints through its drive-through AI voice assistant - [ABA Litigation, Voiceprints, AI, and BIPA](https://www.americanbar.org/groups/litigation/resources/newsletters/class-actions-derivative-suits/voiceprints-ai-bipa-new-trends-biometric-privacy-litigation/)
- An AI meeting-assistant (Fireflies.ai) was sued over voice data from meeting participants who never agreed to it - [Epstein Becker Green](https://www.ebglaw.com/insights/publications/ai-meeting-assistants-and-biometric-privacy-lessons-from-the-fireflies-ai-lawsuit)
- In May 2026 suits under BIPA accused large tech companies of using voiceprints to train AI models - [Biometric Update, May 2026](https://www.biometricupdate.com/202605/tech-giants-sued-under-bipa-over-voiceprints-used-to-train-ai)
- Texas CUBI covers voiceprints, has no private right of action, is enforced by the Attorney General (who sued Google in 2022 over Nest "voice match"), with penalties up to $25,000 per violation - [Winston & Strawn](https://www.winston.com/en/class-action-insider/texas-ag-dont-mess-with-texans-biometric-info.html); [JD Supra](https://jdsupra.com/legalnews/lessons-from-the-texas-biometric-data-9378458)
- Washington's biometric law (RCW 19.375) prohibits enrolling a biometric identifier for a commercial purpose without notice and consent (from a law-firm summary; statute text not opened) - [Perkins Coie summary](https://perkinscoie.com/print/pdf/node/4558)

FDA status
- 21 CFR 882.1470 classifies a "computerized cognitive assessment aid" as Class II (special controls, 510(k)); it is an aid to assess level of cognitive functioning, not a stand-alone or adjunctive diagnostic device - [eCFR via Cornell LII](https://www.law.cornell.edu/cfr/text/21/882.1470); [Federal Register classification](https://regulations.vlex.com/vid/medical-devices-neurological-devices-582363242)
- An exempt variant (product code PTY) covers aids not intended for diagnosis of specific diseases that rely on visual or auditory cues and/or hand function; cleared non-exempt devices under code PKQ include Cognivue (DEN130033), Cantab Mobile (K161328) and ANAM (K150154), none of them speech-based - [Innolitics PTY](https://fda.innolitics.com/submissions/NE/neurological-diagnostic-devices/PTY); [RegDataLab PKQ](https://www.regdatalab.com/device-class/PKQ)
- Aural Analytics announced in Oct 2022 that FDA "registered" its Speech Vitals as a Class II computerized cognitive assessment aid; this is registration and listing, which is consistent with the exempt pathway, not a 510(k) clearance - [BusinessWire](https://www.businesswire.com/news/home/20221025005337/en/FDA-Registers-Aural-Analytics-Clinical-Grade-Speech-Analytics-as-a-Computerized-Cognitive-Assessment-Aid); [Speech Technology Magazine](https://speechtechmag.com/Articles/News/Speech-Technology-News/Aural-Analytics-Gets-FDA-Approval-155602.aspx)
- Linus Health's DCTclock is described as an FDA-registered Class II device (a clock-drawing test, with a later voice and recall component) - [NeurologyLive interview](https://www.neurologylive.com/view/incorporating-voice-analytics-into-cognitive-assessments-alvaro-pascual-leone)
- A trade newsletter states no voice biomarker platform had received FDA approval, with FDA's Digital Health Center of Excellence reviewing first-in-class submissions (date unclear) - [Healthy Innovations newsletter](https://healthy-innovations.beehiiv.com/p/voice-biomarkers)
- FDA's revised General Wellness guidance (6 Jan 2026) keeps the two-part test (intended only for general wellness, and low risk) and more explicitly allows some non-invasive sensing that estimates physiologic parameters; how a product is marketed decides whether it qualifies - [King & Spalding](https://www.kslaw.com/insights/articles/fda-updates-general-wellness-and-clinical-decision-support-guidance-documents); [Ropes & Gray](https://www.ropesgray.com/en/insights/alerts/2026/01/fda-adapts-with-the-times-on-digital-health-updated-guidances-on-general-wellness-products); [Honigman](https://www.honigman.com/alert-3236)

Fairness
- Commercial ASR is substantially worse for Black speakers (WER 0.35 vs 0.19) - [Koenecke et al. 2020](https://ideas.repec.org/a/nas/journl/v117y2020p7684-7689.html)
- ASR is worse for people with dementia - [Cohn et al. 2026](https://arxiv.org/abs/2602.23436)
- Acoustic and linguistic classifiers were reported biased against multilingual speakers, especially on memory, fluency and reading tasks (search summary of a UK study) - [arXiv 2602.13047](https://arxiv.org/pdf/2602.13047.pdf)
- Cross-lingual transfer (English, Greek, Slovak) worked for some language pairs but not others - [JMIR 2025](https://www.jmir.org/2025/1/e74200/PDF)
- Adding age and education changed accuracy in phone-call acoustic models (up to 0.80 only with them), showing education and age are confounders - [Italian phone study record](https://vufind.katalog.k.utb.cz/SummonRecord/FETCH-LOGICAL-i302t-f067e1a99c7318cf95dcb8bf429788a4cf9bfb704dec99b24ace1eb089e221fa3)
- The telephone study required adequate hearing for inclusion, so hearing-impaired callers are absent from that evidence base - [Diaz-Asper et al. 2022](https://ckchandler.github.io/files/publications/diazasper_cortex2022.pdf)

### Inferences
- Where a Save It feature becomes a medical-device claim: showing a family "Mum asked 9 times today, usually 4" is descriptive logging; calling it a "memory score", "cognitive decline trend", "early warning of dementia progression", or alerting to "possible delirium / stroke / low blood sugar" is an intended use to diagnose, monitor or mitigate a disease, which takes Save It out of general wellness and toward 882.1470 or a higher-risk pathway.
- Voice-derived embeddings (HuBERT, speaker vectors) are the most likely thing to be argued a "voiceprint" under BIPA/CUBI/RCW 19.375; counts and timings derived from transcripts are much less likely to be.
  This is a strong reason to log numbers, not embeddings, and to never send call audio to a third party for training.
- FaceTime is video: if the Chert/LiveKit path records or analyses the video stream, Georgia's all-party rule for images in a private place applies to anyone else visible, separate from the one-party audio rule.
- Hearing loss is a large confounder for Save It specifically: a caller who cannot hear the agent will ask for repeats and take longer to reply, which mimics the cognitive markers.
  Logging "asked to repeat the answer" separately from "asked again later" partly separates the two.
- Consent should be designed for the trajectory: consent from the person while capacity is clearer, a named family proxy, a visible "this call helps your family see how things are going" notice, and an easy off switch for metrics separate from the find feature.

### Gaps
- I could not verify the Google Assistant BIPA settlement amounts mentioned in search snippets ($68M / $100M) against dockets, so they are omitted.
- No direct study found on hearing loss as a confounder of speech biomarkers of cognition.
- Not verified: whether Aural Analytics or Winterlight have since been acquired (Linus Health and Cambridge Cognition respectively are commonly reported) and whether any successor product holds a 510(k).
- I did not check whether any state treats transcripts (not audio) of an AI agent call as a "recording" for all-party consent purposes.

## 7. Recommended minimal, privacy-preserving speech metric set for Save It (expected signal and noise)

### Takeaway
Log a small set of per-call interaction counts and timings (no audio, no embeddings, transcripts optional with short retention), aggregate weekly per person, compare only with that person's own rolling baseline, and show families a plain "how calls are going" view with no medical interpretation.
The highest-value signals are the ones the literature ties to dementia and that Save It's fixed task makes comparable over time: re-asking the same item after a confident answer, turns and clarifications to resolution, caller response latency, and words per caller turn; acoustic quality and lexical diversity are not worth computing from 3-second questions.

### Cited Findings
- Re-asking identical information despite an immediate answer, and bursts of 3+ identical requests within 30 seconds, were characteristic of MCI in daily Alexa use - [Qi et al. 2025](https://arxiv.org/abs/2505.17137)
- Repetitiveness predicted future AD onset in Framingham - [Eyigoz et al. 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7700896)
- Gaps at turn change, lapses, turns per minute and turn length separated AD from non-AD in conversation - [Nasreen et al. 2021](https://www.frontiersin.org/articles/10.3389/fcomp.2021.640669/text)
- Failure to recover from unsuccessful commands and fewer information-seeking follow-ups marked MCI - [Qi et al. 2025](https://arxiv.org/abs/2505.17137)
- Vague placeholders and wrong nouns ("that thing") marked word-finding difficulty - [Qi et al. 2025](https://arxiv.org/abs/2505.17137)
- Very short commands where healthy users phrase in more detail marked MCI - [Qi et al. 2025](https://arxiv.org/abs/2505.17137)
- Number of pauses in question answering and speech tempo separated MCI from controls - [Toth et al. 2018](https://rgai.inf.u-szeged.hu/node/20)
- ASR success itself carried signal in Alexa data, and ASR failure is predicted by intensity, voice quality and pause ratio - [Liang et al. 2022](https://www.cs.dartmouth.edu/dfk/research/liang-vas/index.html); [Cohn et al. 2026](https://arxiv.org/abs/2602.23436)
- Averaging repeated short sessions improves reliability, and longer samples track change better - [Petti et al. 2023](https://karger.com/dib/article/7/1/157/870178/How-Much-Speech-Data-Is-Needed-for-Tracking); [PMC11293000 (unverified)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11293000)

### Inferences

Proposed per-call fields (one row per call, numbers only).
"Source" says whether the `queries` table already has it or the agent must log it.

| Metric | How to compute | Source | Evidence link | Expected signal | Main noise |
|---|---|---|---|---|---|
| `asks_same_item_after_confident_answer` | Count of later questions for the same `item_id` within 10 min after a `seen` answer, within the call or across calls | `queries` already (asked_at, item_id, state) | Re-asking despite immediate answer; repetitiveness | Highest of the set; directly ties to the product task | Item truly not there (answer wrong), stale sighting, person checking twice by habit, adoption growth |
| `within_call_repeats` | Same intent asked again in the same call after the agent answered | Agent log | Bursts of identical requests | High | Agent answer unclear, bad audio, caller did not hear (hearing loss) |
| `asked_to_repeat_answer` | Caller says "what?", "say that again" right after an answer | Agent log (intent tag, no text needed) | Separates hearing from memory | Mostly a noise control | Hearing, volume, accent of TTS voice |
| `clarification_turns` | Times the agent had to ask "which item?" or similar | Agent log | Failure to recover, word-finding | Medium | ASR errors (worse in dementia and for some accents), vocabulary not in item list |
| `unknown_item` / vague-name rate | `state = unknown_item`, or name heard is a placeholder ("that thing") | `queries` already (state, heard); placeholder flag via small word list | Vague placeholders, wrong nouns | Medium | ASR mishearing, new item not registered, family naming differs from caller naming |
| `turns_to_resolution` | Caller turns until the agent gave an answer or the call ended | Agent log | Turn structure, recovery | Medium | Agent behaviour changes (prompt edits), clarifying-question design |
| `response_latency_ms` (median per call) | Time from agent speech end to caller speech start, per turn | Agent log; needs VAD or turn timestamps | Gaps and lapses at turn change | Medium, only when pooled weekly | FaceTime/network latency, barge-in, TV, agent end-of-turn detection, someone else answering |
| `caller_words_per_turn` (median) | Word count of caller turns | Agent log (count only) | Short commands; reduced content | Low-medium | ASR dropping words, very short task by design |
| `outcome` and `not_found` rate | Existing "did you find it?" answer | `queries` already | Task performance | Low as a cognitive signal, high as a product-quality signal | Camera coverage, item actually lost |
| `calls_per_day`, `night_call_share` | Calls per local day; share between, say, 22:00 and 06:00 local | `queries` already (asked_at, home timezone) | Not validated; behavioural | Useful for sudden-change view | Routine changes, visitors, adoption, holidays |
| `asr_failed_turns` | Turns where no usable text came back | Agent log | ASR-quality control | Noise control, weak signal | Network, mic, codec |

What not to log: raw audio, voice embeddings or any speaker vector, per-call acoustic features (pitch, jitter, shimmer), lexical diversity or syntax scores from 3-second questions, and transcripts beyond a short debug retention.

How to turn per-call rows into something a family sees:
- Aggregate per ISO week per person: medians for latency and words, rates per call for the counts, with the number of calls shown next to each figure.
- Baseline = the person's own first 4 weeks (or a rolling 8-week median once enough data exists); never compare across people.
- Only compute "confusion" metrics on calls where the system itself answered confidently (`state = seen`, `confident = true`), so Save It's own failures are not read as the caller's decline.
- Flag a "change" only if it is both large (for example 2 or more times the person's baseline interquartile range) and sustained (2 consecutive weeks), or abrupt (3 or more days in a row far above baseline for calls per day or within-call repeats); these thresholds are judgement calls, not validated.
- Record known confounders as events the family can tag (new hearing aids, illness, hospital stay, new medication, visitors, app or agent prompt changes), and reset or annotate the baseline when the agent's prompt or voice changes.

Expected signal and noise overall:
- Realistic: Save It can show a family a clear, honest picture of "how the calls are going" and an "unusual week" change; that has value because families otherwise see nothing between visits.
- Not realistic with current evidence: a validated per-person estimate of cognitive decline, MCI detection, or acute delirium/stroke detection from these calls; the closest study (Cog-TiPRO) is 15 people, a label rather than change, and 74% accuracy.
- The largest noise sources are Save It's own answer quality, ASR errors that grow with the disease, hearing loss, network latency on FaceTime, and adoption effects on call volume.

Wording guardrails (to stay on the non-device side):
- Use: "calls this week", "asked again soon after an answer", "took more back-and-forth than usual", "worth checking in".
- Avoid: "memory score", "cognitive decline", "dementia progression", "early warning", "detects delirium/stroke/infection", "biomarker" in user-facing copy; in the pitch say "could one day support research" rather than "monitors decline".
- Always pair a change notice with "this is not a medical assessment; if you are worried, talk to their doctor", and keep the emergency path separate from the metrics.

Privacy defaults:
- Metrics on by consent of the person (while able) plus the family proxy, with a separate off switch from the find feature.
- Store only the numeric per-call row in Supabase under the same RLS as `queries`; keep transcripts (if at all) for days, not months, and never log them in plaintext server logs (matches the existing rule "never log image bytes or keys").
- Do not send call audio or transcripts to any vendor for training; check that the Gemini path used by the agent does not retain inputs (the project already requires this for frames, D24).

### Gaps
- None of these per-call metrics has been validated as a cognitive measure in a fixed-question assistant setting; the table's "expected signal" is an inference from adjacent studies.
- Change thresholds (2x IQR, 2 weeks, 3 days) are proposals; no study gives evidence-based alert thresholds for assistant-interaction metrics.
- Whether the LiveKit / Gemini Live stack exposes the turn timestamps needed for `response_latency_ms` was not verified.
- No data on how families interpret such dashboards, or whether "unusual week" notices cause alarm or false reassurance.
