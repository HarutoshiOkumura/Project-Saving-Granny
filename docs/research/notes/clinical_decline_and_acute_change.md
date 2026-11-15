# Clinical decline and acute change: what Save It's behavioural data could and could not track

Scope: which clinically meaningful changes in a person with dementia (slow decline, rapid decline, rapidly progressive dementia, delirium, repetitive behaviour, fluctuation, medication effects) could plausibly show up in Save It's put-down, room and question logs, how fast each change happens, and how a clinician would read it.
Research date: 15 Nov 2026.
This file builds on `database_analytics.md` in the same folder and does not repeat its questionnaire items (ECog, AD8, ADCS-ADL), ORCATECH room-transition findings, 16-metric catalog, CUSUM basics or FDA wellness and CDS analysis.
Everything about Save It below is an untested inference unless a citation says otherwise; no study has used object put-downs or "where is my X?" questions as a clinical measure.
Nothing here is a diagnosis, and Section 7 marks where a feature would become a medical-device function.

## 1. How fast does Alzheimer's disease progress, what counts as rapid decline, what change is clinically meaningful, and how long would a passive metric need to run to see it?

### Takeaway
Untreated Alzheimer's disease loses on average about 3 MMSE points a year (pooled 3.3, 95% CI 2.9-3.7), but individual rates vary so much that a single person's MMSE is unreliable for tracking change over less than about 3 years.
"Rapid cognitive decline" has no agreed definition: the common cut-off of 3 or more MMSE points a year labels roughly 30-50% of clinic patients as rapid, while stricter cut-offs (6 or more points a year) label about 12%.
Minimal clinically important differences are about 1-2 MMSE points or 1-2 CDR-SB points depending on stage, which is larger than the average 18-month effect of the anti-amyloid antibodies.
A back-of-envelope power calculation (Inferences) suggests a single noisy weekly behavioural metric would need roughly 1-2 years of consistent data to separate a typical slow decline from noise, but only days to detect an acute doubling, so Save It is far better placed to notice acute change than slow decline.

### Cited Findings
Average rates and individual variability:
- A meta-analysis of AD cohorts (Han et al. 2000) estimated the annual rate of MMSE change at 3.3 points (95% CI 2.9-3.7), with significant unexplained heterogeneity between studies; effect size depended on baseline MMSE and number of assessments - [Han et al. 2000, PubMed 10937543](https://pubmed.ncbi.nlm.nih.gov/10937543)
- In 372 CERAD patients the average decline was 3.4 MMSE points a year, but even after 4 years 15.8% had no clinically meaningful decline, and the authors concluded that MMSE has limited value for tracking an individual over less than 3 years - [Clark et al. 1999, Duke record (seen via search summary)](https://scholars.duke.edu/publication/740187)
- A 2016 French paper cites a typical annual MMSE decline in AD of 2.7 to 4.5 points - [Barbe et al. 2016, Dement Geriatr Cogn Dis Extra](https://pmc.ncbi.nlm.nih.gov/articles/PMC5216188)
- On ADAS-Cog, placebo-group slopes in two mild-to-moderate AD trials (MMSE 16-26) were 4.48 and 3.74 points a year, and in 186 ADNI participants with MMSE 21-26 the ADAS-Cog change was 4.3 (SD 6.4) at 12 months and 9.9 (SD 9.2) at 24 months - [search summary of PMC trial and ADNI analyses](https://pmc.ncbi.nlm.nih.gov/articles/PMC3321732)
- The ADAS-Cog annual change is smaller in mild than in moderate AD, and the variability of the change score has been about equal to or larger than the annual decline itself - [ACNP Generation of Progress, Table 5](https://acnp.org/g4/GN401000133/130_5.htm)
- In the Clarity AD lecanemab trial (early AD) the placebo group worsened by 1.66 CDR-SB points over 18 months - [Muir et al. 2024, Alzheimer's & Dementia](https://pmc.ncbi.nlm.nih.gov/articles/PMC11095473/)

Rapid cognitive decline (RCD):
- Barbe et al. (123 enrolled, 61 analysed at 12 months) defined RCD as a loss of 3 or more MMSE points in 12 months and found it in 45.9%, citing 46%, 47.9% and 51.2% in earlier studies; other definitions in use include 5 or more points a year, 3 or more in 6 months and 4 or more in 6 months, and the authors note "no widely accepted consensus" - [Barbe et al. 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC5216188)
- In that study, caregiver burden (Zarit, OR 3.50) predicted RCD, while having a spouse or child as caregiver (OR 0.27), independence in washing (OR 0.45) and taking 4 or more drugs (OR 0.61) were protective - [Barbe et al. 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC5216188)
- The paper's introduction states that RCD is associated with increased death or institutionalisation, citing earlier studies - [Barbe et al. 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC5216188)
- In the European ICTUS cohort (1,005 mild-to-moderate AD patients, mean MMSE 20.6, more than 90% on cholinesterase inhibitors), 52% declined 1 MMSE point or less in a year, 36% declined 2-5 points and 12% declined 6 or more points - [Canevelli et al., ICTUS accepted manuscript](https://research.stmarys.ac.uk/2386/3/Canevelli-et-al-Predicting-the-Rate-of-Cognitive-Decline.pdf)
- In ICTUS, higher baseline ADAS-Cog predicted rapid decline (OR 1.07 per point, 95% CI 1.04-1.10), older age was protective (OR 0.96 per year), rapid decliners had higher baseline NPI (behavioural symptom) scores, and the authors note trial cohorts may be healthier than clinic populations - [Canevelli et al.](https://research.stmarys.ac.uk/2386/3/Canevelli-et-al-Predicting-the-Rate-of-Cognitive-Decline.pdf)
- The same paper describes AD as traditionally having survival of about 8-10 years and decline of about 3 MMSE points a year, with important intra- and inter-individual variability - [Canevelli et al.](https://research.stmarys.ac.uk/2386/3/Canevelli-et-al-Predicting-the-Rate-of-Cognitive-Decline.pdf)
- A National Alzheimer's Coordinating Center neuropathology study (60 rapid decliners, defined as at least 3 MMSE points a year over the first three visits, vs 230 typical decliners) found no risk-factor model with clinical utility (AUC below 0.70) - [PubMed 31306127, via search summary](https://pubmed.ncbi.nlm.nih.gov/31306127/)

Minimal clinically important difference (MCID):
- A 2024 rapid review (10 studies, mostly anchor-based) summarised decline MCIDs as: MMSE -1 to -2 in MCI, -2 in mild AD, -1.4 to -3 in moderate-to-severe AD; CDR-SB +1 in MCI and +2 in mild and moderate-to-severe AD; ADAS-Cog +2 to +3 in MCI and +3 in mild AD; iADRS -5 in MCI and -9 in mild AD - [Muir et al. 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11095473/)
- The same review found the average treatment differences of lecanemab (-0.45 CDR-SB, 27.1% slowing), donanemab (2.92 iADRS, 22.3% slowing) and cholinesterase inhibitors (-2.57 ADAS-Cog) all fell below these MCIDs, and recommended reporting the share of each arm reaching a meaningful decline instead (for donanemab, about 37% of placebo vs 25% of treated participants had a CDR global increase of at least 0.5 at 18 months, NNT about 8) - [Muir et al. 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11095473/)
- Only two of the ten MCID studies used patient or caregiver anchors, and none had direct input from people with lived experience - [Muir et al. 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11095473/)

Detection with frequent monitoring:
- High-frequency in-home monitoring with individual-specific trajectories was estimated to cut trial sample sizes substantially compared with annual testing - [Dodge et al. 2015, PLoS ONE](https://pmc.ncbi.nlm.nih.gov/articles/PMC4574479) (already summarised in `database_analytics.md`)

### Inferences
How long a Save It metric would need to run (assumptions stated, not validated):
- Treat a weekly metric such as "wearer questions per 10 covered hours" as having a week-to-week coefficient of variation (CV) c, because nobody has measured it; plausible values are 0.3 (stable) to 0.5 (noisy, overdispersed counts).
- For a step change of relative size d against a well-estimated personal baseline, the number of post-change weeks needed for 80% power at one-sided alpha 0.05 is roughly n = 6.2 x c^2 / d^2.
  With c = 0.5, a 50% step (d = 0.5) needs about 6 weeks, and a 25% step needs about 25 weeks.
  With c = 0.3, a 50% step needs about 2 weeks.
- For a slow linear drift, the standard error of a least-squares slope over T weekly points is c / sqrt(T^3 / 12), so detecting a drift of 20% of baseline per year needs about 108 weeks at c = 0.5 and about 77 weeks at c = 0.3; a 50% per year drift needs about 59 weeks at c = 0.5.
  These figures ignore autocorrelation, seasonality, wear-time changes and novelty effects, all of which lengthen them.
- For an acute change, daily counts carry more information: if the person normally asks about 3 questions a day and that doubles to 6, a Poisson z-score passes 2.5 after about 2 days and 3.0 after about 3 days; overdispersion lengthens this somewhat.
- Conclusion: a single behavioural metric is unlikely to "see" a typical 3-point-per-year MMSE decline within a year, consistent with MMSE itself being unreliable for individuals over less than 3 years (Clark 1999); it can plausibly see acute changes within days and large subacute changes within weeks.
- "Rapid" for Save It therefore means a change in weeks that would usually take a year or more, which overlaps with the clinical red flags in Section 2 and Section 3 more than with the trial definition of RCD.
- Because ICTUS rapid decliners had more behavioural symptoms and Barbe found caregiver burden predicted RCD, a sustained rise in repeat questions plus family-reported strain is a plausible (untested) companion signal, not a predictor.
- There is no mapping from any Save It metric to MMSE, CDR-SB or ADAS-Cog points, so Save It must never report "points" or say a change is "clinically meaningful".

### Gaps
- No published week-to-week variability (CV, overdispersion, autocorrelation) exists for object-finding or question-count data, so the power figures above rest on assumed noise.
- I could not verify a frequently quoted claim that RCD prevalence ranges from 9.5% (ADAS-Cog gain of 7 or more in 6 months) to 54% (MMSE loss of 3 or more), attributed to the 2008 Soto et al. consensus paper in J Nutr Health Aging; nor a French 521-patient cohort reporting 40.9% 12-month RCD incidence.
- I did not retrieve clean annual natural-history CDR-SB slopes for mild AD outside trial placebo arms.
- No study links rate of change on a passive home metric to rate of change on MMSE or CDR-SB in dementia (ORCATECH work is mostly in MCI and cognitively intact adults).

## 2. Rapidly progressive dementia: how fast it moves and why an unusual speed of change matters

### Takeaway
Rapidly progressive dementia (RPD) develops over weeks to months rather than years; in specialist series 17-27% of RPD referrals had potentially treatable causes (autoimmune, infectious, toxic-metabolic, neoplastic), and earlier immunotherapy generally gives better outcomes.
Sporadic Creutzfeldt-Jakob disease, the main untreatable cause, has a median survival of about 5 months.
For Save It, the medically important signal is not the level of difficulty but its speed: a person whose everyday memory behaviour changes markedly over weeks deserves prompt clinical review, which Save It can prompt only in non-diagnostic words.

### Cited Findings
- There is no formal definition of RPD; the term is generally used when dementia develops in "less than 1-2 years from illness onset, but more commonly over weeks to months" - [Paterson, Takada and Geschwind 2012, Neurol Clin Pract](https://pmc.ncbi.nlm.nih.gov/articles/PMC3613204)
- At the UCSF Memory and Aging Center, 17% of RPD referrals had potentially treatable causes; in an Athens tertiary centre reversible causes (toxic-metabolic, infectious, autoimmune, vasculitis, hydrocephalus) were the largest group at 27%; in the US National Prion Disease Pathology Surveillance Center autopsy series 6.4% had potentially treatable causes - [Paterson et al. 2012](https://pmc.ncbi.nlm.nih.gov/articles/PMC3613204)
- The UCSF RPD series breakdown was prion disease 62%, other neurodegenerative 15%, autoimmune 8%, infectious 4%, and psychiatric, cancer, toxic-metabolic and vascular 2% each - [Paterson et al. 2012](https://pmc.ncbi.nlm.nih.gov/articles/PMC3613204)
- Autoimmune encephalopathy can develop over "days, weeks, or months", and in immunotherapy-responsive patients a shorter delay to treatment generally gives better outcomes - [Paterson et al. 2012](https://pmc.ncbi.nlm.nih.gov/articles/PMC3613204)
- More than 85% of people with CJD die within a year of onset - [Paterson et al. 2012](https://pmc.ncbi.nlm.nih.gov/articles/PMC3613204)
- In a Chinese probable sporadic CJD cohort (2020-2022), Kaplan-Meier median survival was 5 months (95% CI 4.2-5.8) - [China CDC Weekly 2025](https://weekly.chinacdc.cn/fileCCDCW/journal/article/ccdcw/2025/7/PDF/240417.pdf)
- StatPearls gives a mean survival of 4 to 8 months for sporadic CJD, with 90% dying within a year - [StatPearls, CJD](https://www.ncbi.nlm.nih.gov/books/NBK507860/)
- In a 2023 prospective RPD cohort, CJD accounted for 30 of 154 cases (19.4%) and the authors concluded potentially treatable causes were common - [Day et al., AAN 2023 abstract](https://index.mirasmart.com/aan2023/PDFfiles/AAN2023-004264.html)
- Of 72 Mayo Clinic patients treated with immunotherapy for suspected autoimmune dementia (2002-2009), 46 (64%) improved, 35% of responders had first been diagnosed with a neurodegenerative or prion disease, and 20 of 26 responders followed for more than a year (77%) relapsed after stopping treatment - [Flanagan et al. 2010, Mayo Clin Proc, via abstract record](https://mayoclinic.elsevierpure.com/en/publications/autoimmune-dementia-clinical-course-and-predictors-of-immunothera)
- A 2023 Annals of Neurology score (STAM3P) reportedly had 100% specificity for treatment-responsive RPD at 3 or more features in one cohort; this is a single-study result - [search summary of Satyadev et al. 2023](https://escholarship.org/uc/item/8gw6h6cm)
- Typical Alzheimer's disease can itself present rapidly in atypical forms, and AD, frontotemporal dementia and dementia with Lewy bodies are part of the RPD differential - [Paterson et al. 2012](https://pmc.ncbi.nlm.nih.gov/articles/PMC3613204)

### Inferences
- Speed comparison: typical AD loses about 3 MMSE points a year (Section 1); RPD can lose the equivalent of years of decline in weeks, so the ratio of current weekly change to the person's own historical weekly change is the natural quantity, not the absolute level.
- In Save It terms, a subacute pattern (2-8 weeks) of rising question rate, falling found rate, more unusual-place put-downs, more `unknown_item` answers (garbled or wrong words), and shrinking room range would be the visible shape, but every one of these also moves with delirium (Section 3), depression, new medication, a move or a perception fault.
- Save It cannot and should not distinguish RPD from delirium or anything else; the only defensible output is "this is a faster change than we have seen before" plus a family note, which the clinician then interprets.
- Clinician reading: a change over days points toward delirium and its triggers; a change over weeks to a few months without an acute trigger is the classic reason to consider an RPD work-up (MRI, CSF, antibody panels per Paterson); a change over many months is consistent with expected progression.
  Save It's value would be a dated timeline that answers the clinician's first question, "when did this start and how fast?", which families often struggle to answer.
- Any feature that says "possible rapidly progressive dementia" or "possible autoimmune cause" names a disease and prompts clinical action, which is a device function under the 2026 FDA guidance (see `database_analytics.md` Section 7).

### Gaps
- No study has measured RPD trajectories with passive home sensing, so the "shape" above is inferred from clinical descriptions.
- I did not find population incidence of RPD among people already diagnosed with AD (the "rapidly progressive AD" estimates of 10-30% I saw used varying definitions and were not verified).
- I did not verify the STAM3P paper itself; only a summary was seen.

## 3. Delirium superimposed on dementia, and passive detection of acute illness at home

### Takeaway
Delirium superimposed on dementia (DSD) is common: a recent meta-analysis of 27 community studies pooled a prevalence of about 30%, delirium onset is over hours to days with a fluctuating course, and it is missed in more than half of cases, most often in its hypoactive (quiet, withdrawn) form.
DSD carries much worse outcomes than dementia alone (mortality RR 5.4, institutionalisation RR 9.3 in dementia cohorts) and roughly doubles the rate of subsequent cognitive decline in Alzheimer's disease.
The best passive-sensing evidence is the UK Minder/TIHM programme: a 2024 npj Digital Medicine study of 117 people with dementia over 27,828 person-days detected UTIs with 65% sensitivity and 71% specificity in unseen participants (75% and 88% after risk stratification), using bathroom visits and night-time breathing, with alerts routed to clinicians.
No study has detected delirium itself from passive home data against clinical diagnoses; this is the most actionable signal for Save It but also the one most likely to be over-read.

### Cited Findings
Prevalence:
- A systematic review and meta-analysis of 27 studies of community-dwelling people with dementia (Burnand, Sampson, Walters, Davis, Davies et al., Alzheimer's & Dementia: Diagnosis, Assessment & Disease Monitoring, DOI 10.1002/dad2.70398) pooled DSD prevalence at 30.2% (sensitivity analysis 27.7%), varying by country, setting and ascertainment tool, and called the rate "higher-than-expected" - [citedrive record](https://www.citedrive.com/en/discovery/the-prevalence-and-incidence-of-delirium-superimposed-on-dementia-in-community-settings-a-systematic-review-and-metaanalysis/)
- An earlier systematic review (Fick, Agostini and Inouye 2002, J Am Geriatr Soc) found DSD prevalence of 22% to 89% in hospital and community populations aged 65 and over with dementia - [PubMed 12366629](https://pubmed.ncbi.nlm.nih.gov/12366629/)
- A three-year retrospective US managed-care study found 13% of community-dwelling older adults with dementia had superimposed delirium, with substantial added costs and utilisation - [Fick et al. 2005, J Gerontol A record](https://biomed.gerontologyjournals.org/cgi/content/abstract/60/6/748)
- Delirium prevalence is about 1-2% in the community overall, 8-17% of seniors in emergency departments and up to 50% of hospitalised seniors; dementia raises delirium risk about 2-5 fold, and Table 1 of the review lists 18% prevalence and 56% incidence in dementia populations - [Inouye, Westendorp and Saczynski 2014, Lancet](https://pmc.ncbi.nlm.nih.gov/articles/PMC4120864/)

Onset, course and signs:
- Key features of delirium are acute onset, fluctuating course, inattention, impaired consciousness and cognitive disturbance; supportive features include sleep-wake disturbance, perceptual disturbance, delusions, psychomotor change and emotional lability - [Inouye et al. 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4120864/)
- Hypoactive delirium is more common in older patients and generally has a worse prognosis; patients can shift between hypoactive and hyperactive forms - [Inouye et al. 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4120864/)
- NICE CG103 (2010, updated 2023) asks staff to look for recent changes or fluctuations in behaviour that appear within hours or days and may be reported by the person, a carer or a relative, and to be particularly vigilant for often-missed hypoactive signs such as withdrawal, slow responses, reduced mobility and movement, worse concentration and reduced appetite - [NICE CG103 (direct fetch blocked; wording from search snippet of this page)](https://www.nice.org.uk/guidance/cg103/chapter/1-Guidance)
- NICE says that if it is hard to distinguish delirium, dementia or DSD, delirium should be managed first, and that a competent practitioner should assess with the 4AT when indicators are present - [NICE CG103 (search snippet)](https://www.nice.org.uk/guidance/cg103/chapter/1-Guidance)
- In elderly hip-surgery patients, most of those who developed postoperative delirium already showed early symptoms in a prodromal phase, with memory impairment, incoherence and disorientation predicting delirium - [de Jonghe et al. 2007, PubMed 17272731](https://pubmed.ncbi.nlm.nih.gov/17272731)
- A review describes prodromal changes lasting 1-3 days, with sleep disturbance (including daytime sleepiness), restlessness, irritability and anxiety, often recognised only in retrospect - [Focus review (seen via search summary, not opened)](https://psychiatryonline.org/doi/10.1176/foc.3.2.320)

Triggers:
- Precipitating factors include multiple new medications, psychoactive drugs, sedative-hypnotics and benzodiazepines, infection, dehydration, abnormal sodium or glucose, urinary retention, constipation, pain, sleep disruption, hypoxia, urgent admission, catheters and restraints; predisposing factors include dementia, prior delirium, functional impairment, sensory impairment and depression - [Inouye et al. 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4120864/)
- UTI is reported as one of the top five reasons for hospital admission of people with dementia, about 9% of their UK admissions - [Enshaeifar et al. 2019, PLoS ONE](https://pmc.ncbi.nlm.nih.gov/articles/PMC6333356)
- Caution: there is no evidence that bacteriuria without urinary symptoms causes delirium or that antibiotics improve it, and the 2019 IDSA guideline recommends assessing other causes for delirium in people without urinary or systemic symptoms - [AAFP 2020, Asymptomatic Bacteriuria](https://www.aafp.org/afp/2020/0715/p99.html); [The Hospitalist commentary](https://blogs.the-hospitalist.org/content/should-you-treat-asymptomatic-bacteriuria-older-adult-altered-mental-status)

Recognition and outcomes:
- Delirium is "easily overlooked", and only about 3% of cases are coded in medical records - [Inouye et al. 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4120864/)
- Delirium is reported missed, detected late or misdiagnosed in over 50% of cases across settings, with hypoactive delirium and frail patients least often recognised - [BMJ Open 2013 (seen via search summary)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3549230); [BMC Medicine 2019 UK prevalence study](https://discovery-pp.ucl.ac.uk/id/eprint/10088268/1/2019%20-%20GeMRC%20-%20BMC%20Med%20-%20Delirium%20prev.pdf)
- In dementia, delirium was associated with a relative risk of death of 5.4 and of institutionalisation of 9.3; in 263 Alzheimer's patients cognitive decline roughly doubled in the year after delirium and stayed accelerated over 5 years - [Inouye et al. 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4120864/)
- In the Massachusetts ADRC registry (72 AD patients with delirium vs 336 without), decline on the Blessed Information-Memory-Concentration test rose from 2.5 points a year before delirium to 4.9 points a year after (p = 0.001); the lead author described 18 months' expected decline compressed into 12 - [Fong et al. 2009, Neurology](https://pubmed.ncbi.nlm.nih.gov/19414723/); [Newswise press release](https://www.newswise.com/articles/delirium-may-cause-rapid-cognitive-decline-in-alzheimers-disease)
- In 1,870 Chicago residents aged 65+, global cognition declined 0.031 units a year before a first hospitalisation and 0.075 after, a 2.4-fold increase that persisted after adjusting for illness severity and length of stay - [Wilson et al. 2012, Neurology](https://pmc.ncbi.nlm.nih.gov/articles/PMC3310309)
- A 2021 meta-analysis in hospitalised adults (81 studies) found DSD associated with longer stays, worse cognitive and functional outcomes and higher institutionalisation and mortality than dementia alone, with pooled hospital DSD prevalence of 48.9% - [JAMDA meta-analysis, PubMed 34648761](https://pubmed.ncbi.nlm.nih.gov/34648761)

Passive detection studies:
- Minder (UK DRI): 117 people with dementia, 27,828 person-days, low-cost devices measuring activity, sleep and nocturnal physiology; on unseen participants UTI detection had sensitivity 65.3% (95% CI 64.3-66.2) and specificity 70.9% (68.6-73.1), rising to 74.7% and 87.9% after risk stratification; top features were bathroom visit statistics, night-time respiratory rate and number of previous UTIs; PPV and lead time were not reported on the summary page - [Capstick et al. 2024, npj Digital Medicine, UK DRI page](https://ukdri.ac.uk/publications/digital-remote-monitoring-screening-and-early-detection-urinary-tract-infections)
- Minder hardware includes door, appliance and movement sensors and a bed mat for sleep and vital signs, with no audio or video - [Foundation for Science and Technology journal 2024](https://www.foundation.org.uk/Journal/2024/Volume-23-Issue-9/Edge-Technologies/How-AI-can-support-those-living-with-dementia)
- Imperial College Healthcare NHS Trust runs a clinical service (MinderCare) in which clinicians review the sensor data daily; people missed by the research model were mostly women over 65 - [National Health Executive](https://www.nationalhealthexecutive.com/articles/trust-launches-groundbreaking-service-dementia-patients)
- The earlier TIHM analysis (Enshaeifar et al. 2019) used 2 PIR sensors, 4 motion sensors (kitchen, pill drawer, bedroom and bathroom doors) and pressure sensors, with non-negative matrix factorisation and clustering to flag possible UTIs - [Enshaeifar et al. 2019, PLoS ONE](https://pmc.ncbi.nlm.nih.gov/articles/PMC6333356)
- A TIHM semi-supervised model is reported to reach 86% precision and 85% recall for UTI risk; this figure appeared in a search summary and is not in the arXiv abstract I read, so treat it as unverified - [Li et al. 2020, arXiv 2011.13916](https://arxiv.org/abs/2011.13916)
- A 2025 follow-up adapted the Minder UTI model for variation between homes and fairness across sexes, reporting 70.52% accuracy (metric context not confirmed) - [Fan, Capstick, Nilforooshan and Barnaghi 2025, arXiv 2502.17484](https://arxiv.org/html/2502.17484v1)
- At TigerPlace, sensor alerts flagged UTIs, pneumonia and upper respiratory infections, with night-time bathroom trips and restlessness as UTI signs; the often-quoted "10 to 26 days before anyone notices" comes from a press interview, not a peer-reviewed paper - [NSF story](https://www.nsf.gov/news/sensor-network-protect-elderly); [InformationWeek](https://www.informationweek.com/it-leadership/new-wireless-sensors-tackle-old-problems-like-pneumonia); [Skubic et al., PMC4848095](https://pmc.ncbi.nlm.nih.gov/articles/PMC4848095)
- A 2026 JMIR Formative Research proof-of-concept analysed motion, door, temperature and under-mattress sensor data from 17 people with dementia to flag delirium-like anomalies, and its authors state it lacks ground-truth validation against clinically confirmed delirium - [JMIR Formative Research 2026, e93258](https://formative.jmir.org/2026/1/e93258)
- A Zurich hospital study (WeSen_delirium, NCT05677646) is testing a Fitbit Charge 5 for early delirium detection in inpatients aged 65+; the registry notes no early-detection algorithm exists yet, and I found no results - [ClinicalTrials.gov NCT05677646](https://clinicaltrials.gov/study/NCT05677646)

### Inferences
What delirium would look like in Save It data (untested):
- Hyperactive or mixed delirium: a jump over 1-3 days in wearer questions per covered hour, more repeats within minutes of a `seen` answer, more `not_found` outcomes even after correct answers, more `unknown_item` or garbled `heard` text, more unusual-place put-downs, room changes at unusual hours, and activity at night if the lanyard is worn.
- Hypoactive delirium: the opposite direction, with fewer questions, fewer put-downs, fewer room transitions, more time in one room, shorter wear time or the phone not put on at all, and long daytime gaps; this is the form most often missed by people, and a naive "spike" detector would miss it too.
- Fluctuation across the day (a core delirium feature) would show as within-day variance: a burst of questions in the morning, near silence in the afternoon, found rate swinging between days.
- The detector therefore has to be two-sided (more or less than usual) and multivariate (questions, put-downs, rooms and wear time together), and it must treat a fall in wear time as information, not only as missing data.
- Save It lacks Minder's strongest UTI features: bathrooms are `capture_allowed = false`, so Save It must not write any row for them, and it has no bed mat for night breathing; a "bathroom visit count" would need a deliberate policy decision recorded in `docs/DECISIONS.md`, because the current hard rule says no row at all for no-capture rooms.
- Base rates make alerts mostly false even with good accuracy: with Minder's stratified sensitivity of 74.7% and specificity of 87.9%, and if 2% of person-days were true UTI days (an assumption), PPV would be about 11%; at 5% it would be about 25%.
  This is why Minder routes alerts to a clinical team, and why a family-facing Save It alert would cause alarm fatigue unless it is rare, sustained and phrased as a change from usual.
- Acute illness and hospital stays produce step changes in slope (Fong 2009; Wilson 2012), so Save It's trend lines should mark family-tagged illness and hospital weeks and expect a new, possibly steeper baseline afterwards rather than a return to the old one.
- Clinician reading of a Save It acute-change note: "new or fluctuating confusion over days" in a person with dementia is treated as delirium until proven otherwise (NICE), followed by a search for triggers (infection, dehydration, constipation, pain, retention, new drugs) and a 4AT; a UTI should not be assumed from confusion alone (IDSA, AAFP).
- Wording: "a possible infection" or "possible delirium" names a condition and implies clinical action, which crosses into device territory; "She asked about 4 times more than usual since Tuesday, and asked less in the afternoons; if this is new, you may want to check how she is" stays closer to the wellness side, but the FDA 2026 guidance bars ongoing disease-management alerts even without disease names.

### Gaps
- No study validated passive home data against clinically diagnosed delirium (the 2026 proof-of-concept says so explicitly).
- No passive-sensing study reported PPV, false alerts per person-month or lead time for UTI detection in dementia in the sources I read.
- No study measured delirium using question logs, voice-assistant use or object handling.
- I could not read the NICE CG103 page directly (403) and relied on search snippets for its wording; the pooled incidence figure from the 2025/2026 community DSD meta-analysis was not shown on the record I read.
- I found no community-specific data on which triggers (UTI, dehydration, constipation, medication) most often cause DSD at home.

## 4. Repetitive questioning, losing the same item and searching: prevalence, drivers, measurement, and responses

### Takeaway
Repetitive questioning is the most common form of verbal repetition in dementia (about 90% of those with verbal repetition), is reported in 31-90% of people with dementia depending on definition, and is most often a tracked concern in the mild stage and in Alzheimer's disease.
Its frequency does not track severity in a simple way: it is reported early, is not clearly related to MMSE, and other repetitive behaviours become more prominent later, so a falling question rate can mean worse, not better.
In a placebo-controlled trial, verbal repetition fell in 58% of galantamine-treated vs 24% of placebo-treated patients at 4 months, and written cues reduced repetitions in a small caregiver-training study, which makes repeat-question rate a plausible, untested responsiveness signal.
Misplacing is reported in 74% of people with mild-to-moderate AD, and in 81% of them it means not remembering where something was put down, exactly the event Save It records.

### Cited Findings
Prevalence and stage:
- In 1,707 SymptomGuide users (community-dwelling people with dementia, mostly reported by caregivers), verbal repetition was chosen as a symptom to track by 47.3%, more in mild (57.2%) than moderate (36.0%) or severe (39.9%) dementia, and more in AD than other dementias (65.2% vs 29.7%) - [Reeve, Molin, Hui and Rockwood 2017, Int Psychogeriatr](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/28BB08AD166CF991B27E79F371CF2F0A/S1041610216002180a.pdf/exploration_of_verbal_repetition_in_people_with_dementia_using_an_online_symptomtracking_tool.pdf)
- Among those tracking verbal repetition, repetitive questioning was the most common type (90.8%) and was targeted in similar proportions at every stage, while repetitive stories and perseveration were targeted more in moderate and severe stages; when chosen, verbal repetition was a top-three symptom in 65.3% - [Reeve et al. 2017](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/28BB08AD166CF991B27E79F371CF2F0A/S1041610216002180a.pdf/exploration_of_verbal_repetition_in_people_with_dementia_using_an_online_symptomtracking_tool.pdf)
- The most frequent descriptor was asking repeatedly about upcoming events or appointments; repetitive questions commonly concern upcoming events, whereabouts of people and objects, and time orientation - [Reeve et al. 2017](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/28BB08AD166CF991B27E79F371CF2F0A/S1041610216002180a.pdf/exploration_of_verbal_repetition_in_people_with_dementia_using_an_online_symptomtracking_tool.pdf)
- Earlier studies reported verbal repetition in 31% to 90% of people with dementia, the range reflecting definitions (for example, the Revised Memory and Behavior Problems Checklist asks whether the person asked repeated questions at all in the previous week); Hwang et al. (2000) found repetition reported early (within two years of diagnosis) and unrelated to MMSE - [Reeve et al. 2017, discussion](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/28BB08AD166CF991B27E79F371CF2F0A/S1041610216002180a.pdf/exploration_of_verbal_repetition_in_people_with_dementia_using_an_online_symptomtracking_tool.pdf)
- Tracking verbal repetition was most strongly associated with also tracking difficulty operating gadgets (OR 3.65), lack of interest or initiative (OR 3.52) and misplacing or losing objects (OR 3.25) - [Reeve et al. 2017](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/28BB08AD166CF991B27E79F371CF2F0A/S1041610216002180a.pdf/exploration_of_verbal_repetition_in_people_with_dementia_using_an_online_symptomtracking_tool.pdf)

Drivers:
- Repetitive questioning is considered an amnesic behaviour, but not every AD patient shows it, suggesting other factors; a SPECT study linked it to higher pericallosal blood flow, and a separate theory ties it to anxiety, agitation and emotional disturbance, supported by the dominance of questions about upcoming events - [Reeve et al. 2017, discussion](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/28BB08AD166CF991B27E79F371CF2F0A/S1041610216002180a.pdf/exploration_of_verbal_repetition_in_people_with_dementia_using_an_online_symptomtracking_tool.pdf)
- Repetitive stories and statements are attributed to executive dysfunction (attention shifting, inhibition, working memory), and one study of 54 AD patients linked dysexecutive scores to repetitive statements but not to repetitive questions - [Reeve et al. 2017, citing Cullen et al. 2005](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/28BB08AD166CF991B27E79F371CF2F0A/S1041610216002180a.pdf/exploration_of_verbal_repetition_in_people_with_dementia_using_an_online_symptomtracking_tool.pdf)
- Hamdy et al. describe repetitive questioning as arising from difficulty learning, retaining and recalling new information, aggravated by poor attention and distractibility, and note that events can trigger anxiety that starts and sustains it - [Hamdy et al. 2018, Gerontol Geriatr Med](https://etsu.elsevierpure.com/en/publications/repetitive-questioning-exasperates-caregivers/)

Treatment responsiveness:
- In the VISTA trial (130 community-dwelling mild-to-moderate AD, 4 months, galantamine vs placebo, goal attainment scaling), reducing verbal repetition was a goal for 44%; 58% of galantamine-treated vs 24% of placebo-treated patients showed less verbal repetition (p < 0.01), and the change tracked clinical but not standard psychometric measures - [Rockwood, Fay, Jarrett and Asp 2007, Neurology, via Epistemonikos](https://www.epistemonikos.org/en/documents/4db071bba50da8ff358bfec06ca7fd6309e64561)
- Reeve et al. note that few drug trials have measured verbal repetition as an outcome - [Reeve et al. 2017](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/28BB08AD166CF991B27E79F371CF2F0A/S1041610216002180a.pdf/exploration_of_verbal_repetition_in_people_with_dementia_using_an_online_symptomtracking_tool.pdf)

Non-drug responses:
- Seven spousal caregivers trained over 12 weekly home visits to use written cues reduced their partners' repetitive verbalisations compared with 7 matched controls who only logged them - [Bourgeois et al. 1997, The Gerontologist](https://gerontologist.gerontologyjournals.org/cgi/content/abstract/37/1/30)
- Caregiver guidance recommends staying calm (irritation raises anxiety), redirecting to an enjoyed activity, and looking for triggers such as time of day - [Easter Seals NH caregiver page](https://eastersealsnh.org/?p=1288); [Hamdy et al. 2018](https://etsu.elsevierpure.com/en/publications/repetitive-questioning-exasperates-caregivers/)

Misplacing and searching:
- In VISTA video interviews with 130 people with mild-to-moderate AD and their carers, recurrent misplacing was described for 74% (96/130); for 81% of those it was failing to recall where an item had been put down, and 25 of 96 put objects in unusual or wrong places; 58% were aware of misplacing and 31 of those 56 were distressed by it - [Hamilton, Fay and Rockwood 2009, JNNP](https://latam-cl.demo.elsevierpure.com/fr/publications/misplacing-objects-in-mild-to-moderate-alzheimers-disease-a-descr)
- Misplacing involves both not recalling where an item was placed and inappropriate placement, which may reflect impaired planning or monitoring as well as memory - [Reeve et al. 2017, citing Hamilton et al. 2009](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/28BB08AD166CF991B27E79F371CF2F0A/S1041610216002180a.pdf/exploration_of_verbal_repetition_in_people_with_dementia_using_an_online_symptomtracking_tool.pdf)

### Inferences
- Save It splits Hamilton's two misplacing types cleanly: "forgot where I put it" is a question about an item whose last put-down was at a usual place, while "put it somewhere odd" is an unusual-place put-down; tracking them separately would mirror the clinical distinction between memory and planning or monitoring problems (untested).
- Repeat-question rate (same item within minutes after a `seen` answer) is the closest analogue to clinical repetitive questioning; it captures "answer did not stick", which the VISTA result suggests can respond to treatment within months.
- Because repetitive questioning is reported early and not clearly tied to MMSE, and because later stages bring apathy and loss of initiative (associated with repetition in Reeve), a long-term fall in question rate is ambiguous: it may mean the person no longer initiates calls, cannot use FaceTime, or has hypoactive delirium, not that memory improved.
- Anxiety-driven repetition predicts that question bursts cluster around events (appointments, visitors, outings, evenings); family-tagged events would help separate anxiety from memory change.
- Save It is itself a "written cue"-like memory aid, so its introduction should be expected to change the behaviour it measures; a fall in questions to family and a rise in questions to Save It is substitution, not decline.
- Losing the same item repeatedly (one `item_id` dominating questions, many `misses` at the same landmark) points first to environmental fixes (a hook, a tray) rather than a clinical change.
- Displaying "she asked the same question 6 times in 20 minutes" to family risks feeding caregiver frustration; framing it as "the answer may not be sticking; a written note by the door may help" follows the non-drug guidance.

### Gaps
- No study measured repetitive-question frequency with time stamps (rather than caregiver report), so there are no norms for "questions per day" by stage.
- I found no study relating repeat-question frequency to anxiety scales over time in the same person, nor any data on whether repetition rises during delirium (likely, but not documented in the sources read).
- No study measured passively how often or how long people with dementia search for objects at home.
- The Bourgeois study is small (7 vs 7) and old (1997); I found no recent controlled trial of memory aids for repetitive questions.

## 5. Day-to-day fluctuation and sundowning: is variability itself a marker?

### Takeaway
Fluctuating cognition is a core feature of dementia with Lewy bodies (reported in 80-90%) and of delirium, and informant-reported disturbed arousal and disorganised speech separate DLB fluctuations from Alzheimer's disease and normal ageing.
Reaction-time variability in Lewy body dementia is measurable and reliable over weeks, and people with MCI show more within-day variability on smartphone tests, but no study shows that day-to-day variability in everyday behaviour predicts decline in a person already living with dementia.
For Save It, within-day and between-day variance of question timing and found rate is a plausible extra signal, but it would mostly flag "something is different" rather than identify a type of dementia.
(Sundowning's lack of a definition is covered in `database_analytics.md` Section 2 and not repeated.)

### Cited Findings
- Fluctuating confusion occurs in 80-90% of people with dementia with Lewy bodies, described as a spontaneous, periodic, transient interruption in the flow of awareness or attention - [search summary of qualitative and clinical studies](https://resolve.cambridge.org/core/product/3551BCD9A7C1039BF7170CC63ADE5F5D/core-reader)
- The Mayo Fluctuations Scale (Ferman et al. 2004, Neurology) is informant-rated; its 4-item short form covers daytime drowsiness or lethargy, daytime sleep of 2 or more hours and staring into space for long periods (the fourth item, on disorganised speech, was not confirmed from the original), and disturbed arousal and disorganised speech were the features that distinguished DLB from AD and normal ageing - [Ferman et al. 2004 coverage, ScienceDaily](https://sciencedaily.com/releases/2004/01/040116080751.htm); [review citing the short form, PMC10576013](https://pmc.ncbi.nlm.nih.gov/articles/PMC10576013)
- A later review calls the utility of fluctuation scales for separating DLB from other dementias uncertain - [search summary of OUP table](https://academic.oup.com/view-large/165812513)
- In 36 Lewy body dementia patients, simple and choice reaction times and the choice reaction time coefficient of variation had good test-retest reliability over days and up to 12 weeks (ICC at least 0.85), and LBD shows slower reaction times and more intra-individual variability than AD - [J Neurol 2022, s00415-022-10977-4](https://link.springer.com/article/10.1007/s00415-022-10977-4)
- A 2014 study found digit-span variability over 48 hours detected fluctuating mental status in DLB with a repeatable bedside test, but it did not track objective alertness fluctuations - [Movement Disorders 2014, doi 10.1002/mds.25707](https://zendy.io/title/10.1002/mds.25707)
- In a 2021 smartphone study, people with MCI showed greater within-day variability than cognitively unimpaired peers on processing speed and visual short-term memory binding, while day-to-day variability differed only for processing speed - [Frontiers in Digital Health 2021](https://www.frontiersin.org/journals/digital-health/articles/10.3389/fdgth.2021.758031/epub)
- Fluctuating course is a defining feature of delirium (Section 3) - [Inouye et al. 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4120864/)
- ORCATECH found walking and activity were more variable in MCI, with a larger gap in the afternoon (already in `database_analytics.md`) - [Hayes et al. 2008 record](https://katalog.lib.cas.cz/KNAV/EdsRecord/edselp,S1552526008028653)

### Inferences
How fluctuation would show in Save It (untested):
- Between-day: the daily found rate and daily repeat-question share swing from good to poor days more than the person's usual range; a rolling 14-day standard deviation (or mean absolute successive difference) of daily metrics would capture this.
- Within-day: question bursts clustered in specific hours, with long quiet stretches, and `heard` text that is sometimes clear and sometimes garbled on the same day.
- Daytime sleep and staring (Mayo items) would appear only indirectly, as long daytime gaps with the camera seeing the same room and no put-downs; Save It cannot distinguish dozing from the phone lying on a table.
- A new increase in variability (not a long-standing pattern) is more meaningful clinically, because delirium is defined by new fluctuation; a stable, long-standing variable pattern may simply be the person's normal.
- Clinician reading: marked fluctuation with drowsiness and disorganised speech raises the question of Lewy body disease or delirium; Save It should only report the pattern ("good and bad days are further apart than usual"), never a dementia subtype.
- Variability metrics need more data than mean metrics (variance estimates are noisy), so they need longer windows and minimum counts per day before display.

### Gaps
- No study used variability in everyday behaviour (rather than test scores) to track fluctuation in people already diagnosed with dementia.
- I found no longitudinal study showing that within-person behavioural variability predicts faster decline in established dementia; the evidence is cross-sectional or in MCI.
- I could not confirm the exact wording of the fourth Mayo Fluctuations Scale item from the original paper.

## 6. Medication and treatment effects: could home behaviour data detect response or side effects?

### Takeaway
Cholinesterase inhibitors give small average cognitive benefits (about 2.4-2.7 ADAS-Cog points), below published MCIDs, but verbal repetition improved in more than twice as many galantamine- as placebo-treated patients in VISTA, so repeat-question rate is the Save It metric most plausibly sensitive to treatment.
Anticholinergic and sedative drugs are common, avoidable delirium triggers (a 4-fold delirium risk at high combined exposure in one cohort), which makes "a change after a new medication" a key family annotation.
Anti-amyloid antibodies cause ARIA in about 13% (lecanemab) to 24% (donanemab) of treated patients, but only about 3-6% have symptoms (headache, confusion, visual disturbance), mostly in the first months; MRI, not behaviour, is the monitoring standard.
No completed study has used passive home monitoring to measure a dementia drug's effect; the closest is the EVALUATE-AD proof of concept.

### Cited Findings
Cholinesterase inhibitors:
- A Cochrane class review (2006 version) pooled ADAS-Cog -2.37 (95% CI -2.73 to -2.02; 10 trials, 4,236 participants) and MMSE +1.37 (1.13 to 1.61; 9 trials, 3,118 participants) at 6 months or later for optimum doses vs placebo - [Cochrane CD005593, via search summary](https://cochranelibrary.com/cdsr/doi/10.1002/14651858.CD005593/information/ta)
- The 2018 Cochrane donepezil review reported ADAS-Cog mean difference -2.67 - [Cochrane CD001190.pub3 abstract](https://cochranelibrary.com/cdsr/doi/10.1002/14651858.CD001190.pub3/pdf/CDSR/CD001190/CD001190_abstract.pdf)
- The MCID review places cholinesterase inhibitor effects (-2.57 ADAS-Cog) below the +3 mild-AD threshold - [Muir et al. 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11095473/)
- In VISTA, 58% of galantamine vs 24% of placebo patients had less verbal repetition after 4 months - [Rockwood et al. 2007 via Epistemonikos](https://www.epistemonikos.org/en/documents/4db071bba50da8ff358bfec06ca7fd6309e64561)
- In the parent VISTA report, clinician-rated goal attainment improved more on galantamine than placebo, while patient and caregiver ratings did not differ significantly - [Rockwood et al. 2006, CMAJ](https://pmc.ncbi.nlm.nih.gov/articles/PMC1421447)
- In ICTUS, the authors cite evidence that cholinesterase inhibitor treatment increases the probability of a slow course - [Canevelli et al.](https://research.stmarys.ac.uk/2386/3/Canevelli-et-al-Predicting-the-Rate-of-Cognitive-Decline.pdf)

Anticholinergic and sedative drugs:
- The 2023 AGS Beers Criteria state that cumulative anticholinergic exposure is associated with falls, delirium and dementia, advise considering total anticholinergic burden at regular medication reviews, and list benzodiazepines, opioids, antipsychotics and anticholinergics as drugs to avoid in people with delirium - [Beers 2023 summary, Nursing Center](https://nursingcenter.com/Clinical-Resources/Guideline-Summaries/Beers-Criteria); [AGS 2023 Beers pocket card](https://gwep.usc.edu/wp-content/uploads/2023/11/AGS-2023-BEERS-Pocket-PRINTABLE.pdf)
- Sedative-hypnotics including benzodiazepines and Z-drugs (eszopiclone, zaleplon, zolpidem) are associated with delirium, falls and fractures - [AGS 2023 Beers pocket card](https://gwep.usc.edu/wp-content/uploads/2023/11/AGS-2023-BEERS-Pocket-PRINTABLE.pdf)
- In 1,105 community-dwelling adults with cognitive impairment, high combined anticholinergic and sedative exposure was associated with a 4.09-fold higher risk of delirium than no exposure (observational) - [Int J Clin Pharm 2023, PubMed 36933080](https://pubmed.ncbi.nlm.nih.gov/36933080/)
- Psychoactive drugs and multiple new medications are listed among delirium precipitants - [Inouye et al. 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4120864/)

Anti-amyloid antibodies and ARIA:
- In Clarity AD (1,795 participants), ARIA-E occurred in 12.6% on lecanemab vs 1.7% on placebo, symptomatic ARIA-E in 2.8% vs 0.0%, and the most common symptoms were headache, visual disturbance and confusion; headache of any cause was 11.1% vs 8.1% (figures seen via search summaries) - [Clarity AD summaries, PMC11084061](https://pmc.ncbi.nlm.nih.gov/articles/PMC11084061/); [Alzforum](https://alzforum.org/node/3261916)
- Sources disagree on how silent ARIA is: trial summaries say about 78% of lecanemab ARIA-E episodes were asymptomatic (consistent with 2.8% symptomatic out of 12.6%), while a search summary of a toolkit document claimed 97.8%; the 78% figure matches the trial arithmetic and is preferred here - [Clarity AD coverage, NeurologyLive](https://neurologylive.com/view/lecanemab-represents-promising-therapy-alzheimer-disease-clarity-ad); [Alzheimer's Association lecanemab ARIA monitoring toolkit](https://alz.org/media/Documents/lecanemab-toolkit-aria-monitoring.pdf)
- Lecanemab appropriate use recommendations call for MRI before the 5th, 7th and 14th infusions (biweekly dosing, so about weeks 10, 14 and 28), and current FDA labelling as summarised by the Alzheimer's Association adds an MRI before the 3rd infusion, with an MRI also advised whenever symptoms suggest ARIA - [Alzheimer's Association clinical workflow](https://alz.org/media/Documents/lecanemab-toolkit-clinical-workflow.pdf); [JPAD appropriate use recommendations](https://www.jpreventionalzheimer.com/7065-appropriate-use-recommendations-for-lecanemab.html)
- In TRAILBLAZER-ALZ 2, ARIA-E occurred in about 24% of donanemab-treated vs about 2% of placebo participants, symptomatic ARIA-E in about 6% and serious ARIA-E in 1.5%; in 58.3% of those with ARIA-E the first event came by the third infusion (about month 3); three participants with serious ARIA died - [JAMA Neurology secondary analysis record](https://lib.hutech.edu.vn/chi-tiet?id=693805); [Lilly medical information](https://medical.lilly.com/us/products/answers/what-were-the-characteristics-of-aria-in-kisunla-donanemab-azbt-treated-study-participants-204116); [Practical Neurology](https://practicalneurology.com/news/kisunla-linked-to-increased-risk-of-aria-in-early-ad-treatment/2474755/)
- APOE e4 carriers, especially homozygotes, carry higher ARIA risk and need greater vigilance - [Alzheimer's Association ARIA toolkit](https://alz.org/media/Documents/lecanemab-toolkit-aria-monitoring.pdf)

Passive monitoring for treatment:
- EVALUATE-AD (30 people with AD and 30 spouse caregivers, mean 14.6 months of multisensor home monitoring) aims to build a behavioural signature of starting or stopping AD medications; electronic pillbox adherence was 77%, and the authors state the method's use in dementia trials is yet to be evaluated - [EVALUATE-AD proof of concept, JMIR](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7287724/)
- Variability in medication-taking patterns in healthy older adults reflected cognitive function in ORCATECH work - [search summary, PMC8329129](https://pmc.ncbi.nlm.nih.gov/articles/PMC8329129)

### Inferences
- Cholinesterase inhibitor start: if anything moves in Save It, the VISTA result suggests repeat-question rate (answers sticking better) over about 1-4 months; the average cognitive effect is small, so an individual response would be hard to see and its absence means little.
- Cholinesterase inhibitor stop: a rise in repeat questions over weeks after stopping is plausible but untested.
- New anticholinergic or sedative drug (for example a bladder antimuscarinic, an older antihistamine sleep aid or a benzodiazepine): an acute-change pattern over days, either hyperactive or hypoactive, which is why "new medicine" should be one tap in the family annotation list and should appear on any summary shared with a doctor.
- Anti-amyloid therapy: a sudden rise in confusion-type signals during the first 3-6 months of infusions coincides with the highest ARIA window, but because most ARIA is silent (about 78% of ARIA-E in Clarity AD) and symptoms like headache and visual change are invisible to Save It, behaviour data cannot rule ARIA in or out; any feature presented as "ARIA monitoring" would be a medical device and potentially dangerous if families trusted it over MRI.
- A defensible use is a dated "what changed and when" timeline with family-entered medication changes, which a clinician can line up against the prescribing history; Save It should not claim to measure response or side effects.
- Treatment monitoring is explicitly a device purpose under FDA's 2026 general wellness guidance ("diagnosis, screening, monitoring, or management of a disease"), so "see if her new medicine is working" must not be a product claim.

### Gaps
- No completed study has measured a dementia drug's effect or side effects with passive home monitoring; EVALUATE-AD reported feasibility only.
- I did not retrieve pooled adverse-event or withdrawal rates for cholinesterase inhibitors or specific memantine side effects from primary sources.
- I found no time-course data for when symptomatic ARIA symptoms resolve, or for how confusion from ARIA presents day to day at home.
- No study links anticholinergic burden scores to changes in passive home behaviour.

## 7. Translating clinical changes into Save It metrics: what would move, which way, how fast, and what confounds it

### Takeaway
Save It's signals separate best by timescale: acute changes (hours to days) are the most detectable and most actionable, subacute changes (weeks) are detectable for large shifts and clinically important because of treatable causes, and slow decline (months to years) is mostly below the noise floor of a single metric.
Direction is not fixed: delirium and late-stage decline can lower question counts as well as raise them, so every detector must be two-sided and read questions, put-downs, rooms and wear time together.
The dominant confounders are wear time, the novelty and substitution effects of Save It itself, other people in the home, perception errors and speech-to-text errors; none of the mappings below has been validated.

### Cited Findings
- Misplacing in mild-to-moderate AD is mainly forgetting where something was put down (81%), with a minority of unusual placements - [Hamilton et al. 2009](https://latam-cl.demo.elsevierpure.com/fr/publications/misplacing-objects-in-mild-to-moderate-alzheimers-disease-a-descr)
- Repetitive questioning is reported early and is not clearly tied to MMSE, while later stages bring other repetitive behaviours - [Reeve et al. 2017](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/28BB08AD166CF991B27E79F371CF2F0A/S1041610216002180a.pdf/exploration_of_verbal_repetition_in_people_with_dementia_using_an_online_symptomtracking_tool.pdf)
- Hypoactive delirium (withdrawal, slow responses, reduced movement) is common in older people, often missed and carries worse prognosis - [Inouye et al. 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4120864/); [NICE CG103 (search snippet)](https://www.nice.org.uk/guidance/cg103/chapter/1-Guidance)
- Minder's strongest UTI features were bathroom visits and night-time breathing, data Save It does not collect - [Capstick et al. 2024](https://ukdri.ac.uk/publications/digital-remote-monitoring-screening-and-early-detection-urinary-tract-infections)
- Night-time bathroom trips and restlessness were TigerPlace's UTI warning signs - [NSF story](https://www.nsf.gov/news/sensor-network-protect-elderly)
- Delirium and hospitalisation are followed by faster decline (about 2-fold) - [Fong et al. 2009](https://pubmed.ncbi.nlm.nih.gov/19414723/); [Wilson et al. 2012](https://pmc.ncbi.nlm.nih.gov/articles/PMC3310309)
- ORCATECH reported that people with MCI wore their watches less often, so wear time is itself confounded with cognition (from `database_analytics.md`) - [Alzforum](https://alzforum.org/node/1226746)
- Detection of MCI from home sensors is harder in two-person homes (from `database_analytics.md`) - [Muurling et al. 2023, JMIR Aging](https://preprints.jmir.org/preprint/45876/accepted)

### Inferences
Clinical change by Save It signal (direction: up, down, or either; all untested):

| Clinical change (timescale) | Wearer questions per covered hour | Repeat same item within 10 min | Put-down to question latency | Found rate | Put-downs at usual place | Unusual-place put-downs | Unknown-item or garbled `heard` | Room range and transitions | Night activity (if worn) | Wear time |
|---|---|---|---|---|---|---|---|---|---|---|
| Typical AD progression (months to years) | Slow rise in mild stage, may fall later | Slow rise | Slow shortening | Slow fall | Slow fall | Slow rise | Slow rise | Slow narrowing | Slow rise | Slow fall |
| Rapid decline or RPD (weeks to months) | Marked change over weeks | Rise | Shortening | Fall | Fall | Rise | Rise | Narrowing | Rise | Fall |
| Hyperactive or mixed delirium (hours to days) | Sharp rise, bursty | Sharp rise | Very short | Fall even with right answers | Fall | Rise | Rise | Erratic, odd hours | Rise | Erratic |
| Hypoactive delirium (hours to days) | Sharp fall | Little data | Little data | Little data | Fewer put-downs overall | Little data | Slower or fewer calls | Sharp narrowing, long stays in one room | Fall or unchanged | Sharp fall (phone not put on) |
| Fluctuation (DLB-like or delirium) | Day-to-day swings | Swings | Swings | Swings | Swings | Swings | Clear one day, garbled the next | Long daytime gaps | Variable | Variable |
| Anxiety-driven repetition (hours, event-linked) | Bursts around appointments, visitors, evenings | Rise | Not necessarily shorter | Usually unchanged | Unchanged | Unchanged | Unchanged | Unchanged | May rise | Unchanged |
| Cholinesterase inhibitor start (1-4 months) | Small fall or none | Possible fall (VISTA) | Possible lengthening | Possible rise | Possible rise | None expected | None expected | None expected | Possible rise (sleep effects, not verified) | None expected |
| New anticholinergic or sedative drug (days) | As delirium, either direction | Rise | Shortening | Fall | Fall | Rise | Rise | Narrowing, more daytime gaps | Variable | Fall |
| Post-illness or post-hospital step (weeks, then new slope) | Step up, then steeper trend | Step up | Step shorter | Step down | Step down | Step up | Step up | Step narrower | Variable | Step down |

How a clinician would read each pattern (inference from the cited clinical sources):
- Days, either direction, especially new fluctuation: treat as possible delirium until assessed; look for infection, dehydration, constipation, pain, urinary retention and new drugs; do not assume UTI from confusion alone.
- Weeks to a few months, no trigger: unusual speed for Alzheimer's; consider evaluation for other causes, some treatable.
- Months to years: expected progression; Save It's trend lines are a conversation aid alongside MMSE, CDR-SB or MoCA, not a substitute.
- Event-linked bursts: anxiety and routine; non-drug strategies (written cues, calm reassurance, planning around triggers).

Confounders and how to handle them:
- Wear time and coverage: normalise every count by covered hours, show "not enough data" when coverage falls by more than about a third, and also track wear time as its own signal, because a sudden drop may itself be the change (hypoactive delirium, illness, low mood).
- Novelty and substitution: question rates will be high in the first weeks and then settle; questions may shift from family to Save It; use a run-in of at least 4 weeks and re-baseline after major product changes.
- New items registered: each new item adds new possible questions; normalise per registered item or exclude an item's first 2 weeks.
- Visitors and other residents: visitors move objects (more `not_there_anymore`), prompt questions, and change routine; family tags for visits; two-person homes need per-person attribution that Save It does not have.
- Perception errors: missed detections look like "forgot where" (never seen) and misidentifications look like unusual places; require `active` two-frame sightings and decent confidence before counting a put-down, and watch operations metrics (tentative-never-confirmed rate, contradicted rate per landmark) for drifts that would masquerade as clinical change.
- Speech-to-text errors: hearing loss, dentures, a cold, a noisy room or a new phone can raise `unknown_item` without any cognitive change; never interpret `heard` text as language ability.
- Seasonal, daylight and weekday effects: compare like with like (same weekday, same season) and model daylight for evening metrics.
- Caregiver illness, holidays, moves, furniture changes and new landmarks: family tags; new landmarks reset place-based metrics.
- Multiple comparisons: with many items and metrics, false alerts multiply; limit headline metrics (as proposed in `database_analytics.md`) and require persistence for slow trends, but allow a faster path for large, multi-signal acute changes.

Suggested two-track design (proposal, not validated):
- Acute track: daily aggregates, two-sided, multivariate (questions, repeats, found rate, room range, wear time), flag only when at least two signals move together for 2 or more days or one moves by a large factor; message to family in plain everyday terms within a day.
- Slow track: weekly aggregates, monthly summaries, no alerts; shown as trend lines with uncertainty bands and family annotations, for sharing at appointments.

Where features cross into device claims (summary; legal detail is in `database_analytics.md` Section 7):
- Stays closer to wellness: showing counts, trends, baselines and "a change from her usual pattern", and a generic note that talking to a health professional may be helpful, without naming a disease, calling anything abnormal or using clinical thresholds.
- Becomes a device function: naming delirium, UTI, infection, rapidly progressive dementia, ARIA or "cognitive decline"; scoring severity or stage; alerts that recommend specific clinical action; "monitoring treatment response"; any output mapped to MMSE or CDR-SB.
- A research version that does name conditions would need clinical validation, ethics approval and consent, and would sit under FDA device rules.

### Gaps
- None of the cells in the table has been measured; all are reasoned from clinical descriptions and fixed-sensor studies.
- No study reports how wear time of a body-worn device changes during delirium or acute illness in dementia, though it is likely to fall.
- There are no published false-alert rates for a two-sided, multivariate acute-change detector in family-facing dementia monitoring.
- How question behaviour to a voice agent changes across dementia stages, and when people stop being able to use it, is unknown.
