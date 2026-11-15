# Making Save It's home data useful to clinicians, and the path to a validated tool

Scope: what clinicians would use, how to present it, Medicare payment context, precedent devices and their FDA path, validation study design, research partners near Emory, and ethics.
Research date: 15 Nov 2026.
This file deliberately does not repeat `database_analytics.md` (FDA General Wellness and CDS basics, caregiver dashboard preferences, the metric catalog, trend-detection defaults).
Throughout, "Save It data" means the `sightings`, `queries` (with `outcome`), `misses` and room `observations` tables.
Save It is not diagnostic, and nothing below proposes that it diagnose, screen for or stage dementia.
Facts carry a source; anything about Save It itself is in the Inferences subsections.

## 1. What do neurologists, geriatricians and primary care physicians want from home-collected data, and what do they ignore?

### Takeaway
Physicians say they want patient-generated data but almost none have built it into their workflow; the reasons given are liability, false positives, added work, lack of payment and thin evidence, not unwillingness.
In dementia care specifically, the clinicians who do use home monitoring data use it in a narrow way: they pull out the parts that bear on whether the person can stay safely at home, check them against other sources, and usually leave the care plan unchanged.
The best evidence that pre-visit input improves dementia visits comes from structured agenda-setting checklists (SAME Page), not from sensor data, which suggests Save It's clinical value starts as a better-prepared caregiver, not as a data feed.

### Cited Findings
Physician acceptance of remote data in general (2026):
- An AMA and Medscape survey of more than 2,200 physicians in six countries found 97% review wearable data in some capacity, but in no country did more than 6% actively incorporate it into clinical workflows; the authors blamed reimbursement, workflow support and evidence gaps rather than physician willingness - [Fierce Healthcare, 2026](https://www.fiercehealthcare.com/health-tech/doctors-want-wearable-data-healthcare-isnt-ready-it-ama-survey-finds); [Becker's Hospital Review](https://www.beckershospitalreview.com/digital-health/why-physicians-cant-get-wearable-data-into-routine-care-6-things-to-know/). (Both articles blocked direct fetching; figures are from search summaries of them.)
- In that survey, medical-legal liability was the top-ranked workflow concern among US physicians; 53% of French physicians rated liability a serious concern; physicians who had not integrated wearable data were more likely to cite liability, false positives and added workflow - [Fierce Healthcare](https://www.fiercehealthcare.com/health-tech/doctors-want-wearable-data-healthcare-isnt-ready-it-ama-survey-finds)
- The same coverage notes that US remote monitoring billing codes require FDA-cleared devices used under a clinician-directed plan of care and do not extend to consumer wearables, and that the AMA is asking for a separate payment pathway for in-visit review of consumer wearable data - [Fierce Healthcare](https://www.fiercehealthcare.com/health-tech/doctors-want-wearable-data-healthcare-isnt-ready-it-ama-survey-finds)
- A 2026 mixed-methods physician survey found perceived benefits mainly in better decision-making, with main concerns being data accuracy, added workload and thin evidence - [JMIR 2026, e86368](https://www.jmir.org/2026/1/e86368)

Clinicians using home monitoring in dementia and aging care:
- In a 2025 embedded mixed-methods multiple-case study in Montreal on activities-of-daily-living telemonitoring, clinicians followed four steps: extract the relevant telemonitoring data, compare it with other information sources, assess the risk to the person's ability to remain at home, and maintain or modify the intervention plan; most clinicians kept the existing plan rather than increase or reduce services - [JMIR 2025, e64713](https://www.jmir.org/2025/1/e64713) (full text did not load; details are from the search abstract).
- A co-design study of dementia remote monitoring included workshops with 12 health and social care clinicians alongside people with dementia and caregivers - [Tiersen et al. 2021, JMIR Aging](https://aging.jmir.org/2021/3/e27047)
- I found no study focused solely on neurologists' or geriatricians' views of passive home monitoring data in dementia; the closest neurologist survey is about fluid biomarkers.
- In a 2023 survey of Spanish neurologists, most viewed fluid biomarkers favourably in MCI but use stayed low, with consultation time and lumbar puncture logistics the most common barriers; the authors list lack of disease-modifying treatment, avoiding bad news and assuming decline is normal ageing as reasons for reluctance - [Journal of Alzheimer's Disease 2023](https://content.iospress.com/articles/journal-of-alzheimers-disease/jad221160)

Primary care capacity:
- In the Alzheimer's Association 2020 survey, 87% of primary care physicians expected more dementia patients, about half said the profession was not prepared, and 22% had no residency training in dementia diagnosis and care - [Alzheimer's Association, 2020](https://www.alz.org/news/2020/primary-care-physicians-on-the-front-lines-of-diagnosing-and-providing-alzheimer-s-and-dementia-care)
- In a 2019 Alzheimer's Association survey, 94% of primary care physicians said assessing all older patients for cognitive impairment is important but only 47% said it was standard protocol; absence of symptoms and lack of time were the most common reasons for not assessing - [Boston Globe, March 2019](https://www.bostonglobe.com/lifestyle/health-wellness/2019/03/10/most-doctors-don-screen-for-dementia-but-that-may-change-massachusetts/YeQBKU9xDhWxmNaAf1DPUP/story.html?s_campaign=8315)
- 55% of primary care physicians caring for people with Alzheimer's report too few dementia specialists in their communities - [2025 Alzheimer's Disease Facts and Figures, executive summary](https://www.alz.org/getmedia/c05f7ba4-9aea-4cb0-8898-5e8bff3f0930/executive-summary-2025-alzheimers-disease-facts-and-figures.pdf)

Pre-visit reports and caregiver logs:
- The SAME Page proof-of-concept randomized study found that visits of patient-companion dyads who completed a pre-visit agenda-setting checklist had significantly more patient-centred communication than usual care; the follow-on protocol planned 50 checklist dyads vs 50 usual-care dyads in primary care patients with cognitive impairment (main paper: Wolff et al. 2018, J Gen Intern Med) - [NIH R21 AG049967 abstract](https://grantome.com/grant/NIH/R21-AG049967-02); [ClinicalTrials.gov protocol NCT02986958](https://cdn.clinicaltrials.gov/large-docs/58/NCT02986958/Prot_SAP_000.pdf)
- OurNotes embeds agenda-setting in a pre-visit questionnaire sent through the patient portal; clinicians (mostly physicians) said that optimising its use by care partners may support agenda setting for persons with dementia - [GSA 2023 abstract, PMC10736861](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10736861/)
- Caregivers describe preparing for visits as a distinct burden; reported barriers include the person's anxiety, confusion and repetitive questioning about the purpose of the visit, sometimes well before it - [Caregiver perspectives abstract, PMC12759623](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12759623/)
- WeCareAdvisor, an app that walks caregivers through the DICE approach (Describe, Investigate, Create, Evaluate) for behavioural symptoms, produced modestly but significantly lower caregiver distress at 3 months than delayed use, plus fewer reported behavioural symptoms, in what the authors call the first randomized trial of such an app (J Am Geriatr Soc, 2026; NIA R01AG061116; NCT02420535); caregivers used it about once a month - [UC Davis Health, Aug 2026](https://health.ucdavis.edu/medical-center/news/headlines/app-helps-caregivers-manage-dementia-related-behavioral-symptoms-improves-well-being/2026/08)

### Inferences
What clinicians would likely use (ranked by fit with the evidence above):
1. A short, pre-visit summary that a caregiver brings or sends, built like an agenda (SAME Page style), with 2-3 facts from Save It as supporting evidence ("asked about glasses 31 times this month vs about 12 a month in the spring").
2. Facts that bear on "can she stay safely at home?" (the Montreal step 3): items repeatedly not found, items in unsafe places (keys or wallet left outside the home), night activity, a sudden change in question volume over days.
3. Concrete examples that make a caregiver's report credible and specific, which are what clinicians use when rating informant-based scales (see section 2).

What clinicians will likely ignore or resent:
- Raw timelines, per-item logs, dashboards they must log into, and any alert that implies they must act (liability is the top US concern).
- Composite "scores" with no validation behind them.
- Anything that arrives outside the EHR without a billing code to pay for the review time.

Save It should therefore target the caregiver as the carrier of information first (no device claim, no clinician workflow change), and only later a clinician-facing report, once validation exists.
Data in a one-page PDF a caregiver hands over is not a device feature by itself, but the wording on that page still has to stay within General Wellness limits (see `database_analytics.md` section 7).

### Gaps
- No study found that tested a caregiver-carried report built from passive home data (sensors or cameras) and measured visit quality, visit length or decisions.
- No figure found for minutes per visit that neurologists or primary care physicians would spend reviewing home data; the 2020 Alzheimer's report PDF with time-constraint percentages was not retrieved.
- No dementia-specific study of alert fatigue among clinicians receiving home monitoring alerts was found (TigerPlace and TIHM route alerts to clinical teams, but alert-burden figures were not found).
- The full SAME Page trial results (effect sizes, visit length) were not read; the finding above is from the grant abstract.

## 2. How is cognitive and functional change documented clinically, how could home metrics supplement it, and what would a one-page monthly clinician report look like?

### Takeaway
Clinicians document change with informant-based staging (CDR, FAST), brief cognitive tests (MoCA, MMSE), function scales (FAQ, ADLs) and behaviour inventories, and these tools are noisy at the individual level: a MoCA change needs about 4 points and a CDR-SB change about 1-2 points before it is meaningful.
Save It's data maps onto specific informant-reported items (finding belongings, repeating questions) and can make the informant interview more concrete, but it cannot substitute for any of these instruments.
A useful monthly page leads with coverage (how much was observed), shows 2-3 personal-baseline trend lines with uncertainty, lists notable events and caregiver context, and carries an explicit "not a diagnostic test" statement.

### Cited Findings
Staging and cognitive tests:
- The CDR rates six domains (memory, orientation, judgment and problem solving, community affairs, home and hobbies, personal care) at 0, 0.5, 1, 2 or 3 from a semi-structured interview with the person and an informant; the sum of boxes (CDR-SB) runs 0 to 18; raters judge decline from the person's usual level due to cognitive loss alone, and memory is the primary domain for the global score - [Knight ADRC, CDR scoring rules](https://knightadrc.wustl.edu/professionals-clinicians/cdr-dementia-staging-instrument/cdr-scoring-rules/)
- Andrews et al. (2019) found that a 1 to 2 point worsening in CDR-SB was the minimum within-person change associated with a noticeable decline; Andrews has since said it is inappropriate to apply this as a required between-group difference in drug trials - [Alzforum](https://alzforum.org/node/2681356)
- A Roche-led analysis of MCI trial data reported 1 to 2.5 point CDR-SB increases at 12 months as minimal-to-moderate within-patient deterioration - [J Prev Alz Dis 2023](https://www.jpreventionalzheimer.com/6687-establishing-clinically-meaningful-change-on-outcome-assessments-frequently-used-in-trials-of-mild-cognitive-impairment-due-to-alzheimers-disease.html)
- A rapid review lists +1 CDR-SB point as the minimal clinically important difference for MCI and +2 for mild Alzheimer's - [Muir et al. rapid review, aggregator record](https://bohrium.dp.tech/paper/arxiv/e1e9273880cd6e51d795a240d46489c68614758b51986dbd50a7837c17d7ca76) (aggregator page; verify against the journal before citing).
- In 130 community-dwelling adults aged 55+ retested 2-4 months apart, MoCA reliability was ICC 0.81 with SEM 1.5, giving a 95% minimal detectable change of 4 points - [Feeney et al. 2016, PubMed 27258421](https://www.pubmed.gov/27258421/); [UEA repository](https://ueaeprints.uea.ac.uk/58620)
- In cognitively healthy older adults, MoCA temporal stability was reported as 0.33 at 1 year and 0.48 at 4 years - [PMC11345112](https://pmc.ncbi.nlm.nih.gov/articles/PMC11345112)

Behaviour inventories that include repeated questions:
- The Revised Memory and Behavior Problems Checklist (RMBPC) is a 24-item caregiver report covering the past week; item 1 is "repetitive questions" and sits in the memory subscale; each item gets a frequency rating 0-4 (4 = daily or more often) plus a caregiver reaction rating - [RMBPC factor table, PMC2579275](https://pmc.ncbi.nlm.nih.gov/articles/PMC2579275/table/T3); [APA caregiver assessment tools page](https://www.apa.org/pi/about/publications/caregivers/practice-settings/assessment/tools/memory-behavior.aspx)
- (ECog, AD8, ADCS-ADL item 11, the FAQ and the CMAI repetitive-questioning prevalence are covered in `database_analytics.md` section 1.)

What a dementia care-planning visit must document (Medicare 99483):
- A 99483 visit requires examining cognition, assessing activities of daily living and decision-making capacity, staging dementia with a standardized tool (FAST or CDR), reconciling high-risk medicines, screening for neuropsychiatric symptoms and depression or anxiety, evaluating home and driving safety, identifying social supports and caregiver needs, and addressing advance care planning - [CMS, Cognitive Assessment and Care Plan Services](https://www.cms.gov/medicare/payment/fee-schedules/physician/cognitive-assessment)
- An independent historian (for example a spouse, parent or guardian) must be present to bill 99483 - [CMS](https://www.cms.gov/medicare/payment/fee-schedules/physician/cognitive-assessment); [HHS guidance document](https://hhs.gov/guidance/document/cognitive-assessment-care-plan-services-0)

What GUIDE programs measure:
- GUIDE tiers combine dementia stage with caregiver status and strain; tier changes are triggered by a change in stage, caregiver status or burden, or residence - [CMS GUIDE overview fact sheet](https://www.cms.gov/files/document/guide-model-overview-fs.pdf); [GUIDE Performance Measurement Manual v3.0, 18 May 2026](https://www.cms.gov/priorities/innovation/files/guide-performance-msr-manual.pdf)
- GUIDE collects PROMIS-10 from patients and the 22-item Zarit Burden Interview (ZBI-22) from identified caregivers at alignment and each annual comprehensive assessment - [GUIDE PMM v3.0](https://www.cms.gov/priorities/innovation/files/guide-performance-msr-manual.pdf)

### Inferences
Mapping Save It facts to what clinicians already document (supplement only, never a score):

| Save It fact (from tables) | Clinical construct | Where clinicians record it | Use in a visit | Caveat |
|---|---|---|---|---|
| Wearer questions per week, by item; repeat-within-10-min share | Repetitive questioning | RMBPC item 1; CMAI; informant interview for CDR memory box | Gives the informant a number instead of "all the time" | Novelty and new items registered raise counts |
| Found / not found outcomes, time to find | Finding belongings without help | ADCS-ADL item 11; CDR home and hobbies | Concrete examples of needing help | Outcome often missing |
| Unusual-place put-downs (keys in fridge) | Judgment, misplacement | CDR judgment box; ECog item 4 | Safety discussion (99483 home safety element) | Perception errors look like unusual places |
| Items leaving home and not returning (wallet, keys) | Safety, community function | CDR community affairs; home safety review | Prompts a safety conversation | Cannot see outside the home |
| Night-time observations and questions | Sleep and night behaviour | Neuropsychiatric screen; caregiver strain | Context for caregiver burden (ZBI-22) | Low night coverage |
| Weekly question volume jump over days | Acute change from usual | Not a staging item; a reason to call | Possible reason to contact the care team | Must not be framed as illness detection |

A one-page monthly report (design proposal, not tested):
- Header: name, month, "Prepared from Save It by [caregiver]. Everyday observations, not a medical test."
- Coverage strip first: days with the lanyard worn, average hours observed per day, rooms never observed (bathroom by design), with weeks under a coverage floor greyed out.
- Three small-multiple trend panels, 6-12 months, weekly points: wearer questions per 10 observed hours; share of questions that ended "found"; put-downs at the usual place.
  Each shows the personal baseline as a shaded band (median plus or minus a robust spread from the run-in period) and no red colouring.
- An events list: caregiver-tagged context (visitor, illness, hospital stay, medicine change, new items registered), plus 2-3 concrete examples ("keys found in the freezer on 12 Oct").
- A "caregiver's questions for this visit" box (SAME Page style), which the evidence supports more than charts.
- Footer: data provenance, what is never recorded, and that the numbers have no established norms.

Minimum detectable change matters for the report: a home metric that moves less than its own week-to-week noise should not be called a change, the same logic that makes a 4-point MoCA change the floor.

### Gaps
- No source fetched for the NPI or NPI-Q domain list; I could not confirm whether repetitive questioning falls under any NPI domain.
- No study tested whether showing clinicians objective counts changes informant-based CDR or FAQ ratings (risk of anchoring as well as benefit).
- No published template for a home-monitoring summary page for dementia visits was found.

## 3. Medicare payment context: RPM vs RTM, CPT 99483, and the CMS GUIDE model

### Takeaway
Remote Patient Monitoring pays only for physiologic data from an FDA-defined device, and Remote Therapeutic Monitoring covers respiratory, musculoskeletal and cognitive behavioural therapy monitoring; neither code family covers cognition or memory-lapse monitoring, and from 1 Jan 2027 both require an established patient and an initiating visit.
CPT 99483 pays for a roughly one-hour cognitive assessment and care plan that needs an independent historian, which is where caregiver-prepared Save It facts could help without any billing of their own.
GUIDE (July 2024 to June 2032) pays programs a monthly per-patient amount for comprehensive dementia care, measures caregiver burden and quality of life, and requires no particular technology, so Save It would fit as a tool a GUIDE program chooses to supply, not as a billable service.

### Cited Findings
RPM and RTM:
- RPM codes describe "remote monitoring of physiologic parameter(s) (e.g., weight, blood pressure, pulse oximetry, respiratory flow rate)", while RTM describes "therapy adherence, therapy response, digital therapeutic intervention" with device-supply codes for the respiratory system, the musculoskeletal system and cognitive behavioural therapy - [Foley & Lardner, July 2025](https://www.foley.com/insights/publications/2025/07/remote-patient-monitoring-rpm-and-remote-therapeutic-monitoring-rtm-what-you/)
- Device-supply codes historically required at least 16 days of data in 30; CMS proposed new 2-15 day device-supply codes for 2026 - [Foley & Lardner](https://www.foley.com/insights/publications/2025/07/remote-patient-monitoring-rpm-and-remote-therapeutic-monitoring-rtm-what-you/)
- The RTM set now has 10 codes: an RTM code for cognitive behavioural therapy was added in 2023 and four more codes came with the 2026 fee schedule final rule; 98978 is the CBT device-supply code (16-30 days) - [APTA practice advisory](https://www.apta.org/contentassets/95321a10e951408db650e2f19b96699f/apta-practice-advisory-rtm-codes.pdf)
- The CY2027 Physician Fee Schedule final rule (issued 4 Nov 2026) requires, from 1 Jan 2027, that RTM be furnished only to established patients and that both RPM and RTM start with a face-to-face (in-person or telehealth) initiating visit with the billing practitioner - [Nixon Peabody alert, 9 Nov 2026](https://www.nixonpeabody.com/-/media/files/alerts/2026/11/cms_finalizes_2027_medicare_rpm_rtm_changes.pdf)
- The same rule finalized a requirement that RPM and RTM clinical staff be direct employees of the billing practice, delayed to 1 Jan 2029; outside vendors may still supply devices, software, hosting and interoperability, but not clinical staff time - [Nixon Peabody](https://www.nixonpeabody.com/-/media/files/alerts/2026/11/cms_finalizes_2027_medicare_rpm_rtm_changes.pdf)
- CMS revalued several setup and device-supply codes (phased over at least two years), priced CBT codes 98978 and 98986 the same as 98977 for 2027, did not adopt proposed consolidated G-codes, and noted the AMA RUC will review all 19 RPM and RTM codes in January 2027 - [Nixon Peabody](https://www.nixonpeabody.com/-/media/files/alerts/2026/11/cms_finalizes_2027_medicare_rpm_rtm_changes.pdf)

CPT 99483:
- Billable by physicians, nurse practitioners, clinical nurse specialists and physician assistants; typically about 60 minutes face-to-face with the patient and independent historian; allowed by telehealth; includes elements of a level-5 E/M visit; G2212 adds time beyond 60 minutes; not billable the same day as office visits 99202-99215, home visits or advance care planning codes 99497-99498 - [CMS](https://www.cms.gov/medicare/payment/fee-schedules/physician/cognitive-assessment)
- One practitioner should not report 99483 more than once every 180 days, and the required elements can be split across visits and partly done by trained clinical staff - [Alzheimer's Association billing codes page](https://alz.org/professionals/health-systems-medical-professionals/billing-codes) (figure from search summary; sources disagree on whether there are nine or ten required elements).

GUIDE:
- GUIDE is an 8-year voluntary CMS Innovation Center model in all states, with performance years running July 2024 to June 2032; care teams must include at least a trained care navigator and a clinician with dementia proficiency - [CMS GUIDE overview fact sheet](https://www.cms.gov/files/document/guide-model-overview-fs.pdf)
- Eligible patients have dementia confirmed by clinician attestation, Medicare Parts A and B as primary payer, are not in Medicare Advantage, hospice or PACE, and do not live in a long-term nursing home - [CMS GUIDE fact sheet](https://www.cms.gov/files/document/guide-model-overview-fs.pdf)
- Patients fall into five tiers by stage (mild vs moderate or severe) and caregiver status and strain; payments are a monthly per-beneficiary Dementia Care Management Payment, respite payments for some patients, and a one-time infrastructure payment for safety-net new programs - [CMS GUIDE fact sheet](https://www.cms.gov/files/document/guide-model-overview-fs.pdf)
- Required services include a person-centred care plan from a comprehensive assessment (including a home visit), ongoing monitoring and support by care navigators, 24/7 access to the care team, caregiver education and respite - [CMS GUIDE fact sheet](https://www.cms.gov/files/document/guide-model-overview-fs.pdf); [GUIDE PMM v3.0, Appendix B](https://www.cms.gov/priorities/innovation/files/guide-performance-msr-manual.pdf)
- Five performance measures: high-risk medications (claims, NCQA), Quality of Life for Patients Living with Dementia (PROMIS-10), Caregiver-Reported Impact in Dementia (ZBI-22), total per-capita cost, and admissions to long-term nursing home stay; participant-reported data go to CMS on the Patient Assessment and Alignment Form within 60 days of alignment and each annual assessment, and an optional FHIR-based API exists for submission - [GUIDE PMM v3.0](https://www.cms.gov/priorities/innovation/files/guide-performance-msr-manual.pdf)
- CMS reported 390 participating organizations at launch: 96 established programs started 1 July 2024 and 294 new programs on 1 July 2025 - [Healthcare Innovation](https://www.hcinnovationgroup.com/policy-value-based-care/alternative-payment-models/news/55094332/details-emerge-about-participants-in-dementia-alternative-payment-model)
- A July 2026 CMS MLN fact sheet says the application period has ended and gives the PY2026 respite cap as $2,625 per patient - [CMS MLN7172818, July 2026](https://www.cms.gov/sites/default/files/2026-07/mln7172818-guiding-improved-dementia-experience-model.pdf) (from search summary).
- Emory's Integrated Memory Care, a nurse-managed primary care practice for people with dementia operating since 2015, was the only Georgia practice selected for GUIDE in 2024 and is described as a basis for the model - [Emory News, June 2025](https://news.emory.edu/features/2025/06/emorys-integrated-memory-care); [iAdvance Senior Care](https://www.iadvanceseniorcare.com/emory-integrated-memory-care-tests-medicare-dementia-care-model/)

### Inferences
- Cognition is not an RTM category; billing RTM for Save It would require reframing it as monitoring a therapy (for example a CBT-based caregiver program) and an FDA-defined device, which conflicts with staying a wellness product.
  The 2027 rules (established patient, initiating visit, direct-employee staff from 2029) raise the bar further.
  Recommendation: do not build the business on RPM or RTM.
- 99483 is the natural "moment of use": the visit requires a caregiver historian, function and safety review and neuropsychiatric screening, all of which a caregiver-prepared Save It summary can inform without Save It billing anything.
- GUIDE is the best fit: programs are paid per patient per month, are measured on caregiver burden (ZBI-22), quality of life and avoiding nursing home admission, and run 24/7 support lines and navigator check-ins.
  A GUIDE program could supply Save It to reduce repetitive-question burden and to give navigators better information, paying from its care management payment.
  Emory Integrated Memory Care is a GUIDE participant in Atlanta, so it is the obvious first conversation.
- The GUIDE optional FHIR API is for program-to-CMS reporting, not a channel for Save It; it does show that FHIR is the expected interoperability format.

### Gaps
- Exact 2026 and 2027 national payment amounts for 99483 and for GUIDE monthly payments by tier were not retrieved (the payment methodology paper is on GUIDE Connect).
- Whether GUIDE programs may pay for or provide consumer technology to patients within model rules (beneficiary inducement limits) was not researched; a GUIDE participant agreement review is needed.
- Current GUIDE participant count for late 2026 was not found.
- A 2026 JAGS paper on billing for comprehensive dementia care among traditional Medicare beneficiaries (doi 10.1111/jgs.70557) was found but not read.

## 4. Precedent products and their regulatory path

### Takeaway
Every FDA-authorized digital cognitive product I could verify is an active test (a task battery) regulated as a Class II "computerized cognitive assessment aid" (21 CFR 882.1470), created by Cognivue's 2015 De Novo and now mostly 510(k) exempt, with labelling that forbids diagnostic claims.
No FDA-authorized passive home-monitoring product for cognition or dementia was found; the closest regulatory analogue for caregiver-collected home data is Cognoa's Canvas Dx autism De Novo (2021).
A passive misplacement or question-log marker would almost certainly be a new intended use, implying a De Novo (FY2027 FDA fee $191,020, or $47,755 for small businesses) on top of the cost of the validation study.

### Cited Findings
The device type:
- 21 CFR 882.1470 defines a computerized cognitive assessment aid as a prescription device that uses scores on a battery of cognitive tasks to interpret current cognitive function; it "does not identify the presence or absence of clinical diagnoses" and is "not intended as a stand-alone or adjunctive diagnostic device" - [21 CFR 882.1470, LII](https://www.law.cornell.edu/cfr/text/21/882.1470)
- It is Class II with special controls and exempt from 510(k) subject to 882.9 limits, but the exemption does not apply when intended for diagnostic assessment of specific diseases and relying on visual, auditory or hand-function inputs - [21 CFR 882.1470](https://www.law.cornell.edu/cfr/text/21/882.1470)
- Special controls require full hardware and software characterization, verification, validation and hazard analysis, electrical safety, and labelling that summarizes clinical performance (sensitivity, specificity, predictive values, repeatability, how cut-offs were set, construct validity) and warns the device is not diagnostic - [21 CFR 882.1470](https://www.law.cornell.edu/cfr/text/21/882.1470)

Cognitive test precedents:
- Cognivue (De Novo DEN130033) was granted on 5 June 2015 as a screening aid for adults 55+; its pivotal study enrolled 401 people aged 55-95 at 13 independent living communities, stratified by SLUMS score, with blinded paired testing against SLUMS (r = 0.71), a separate 92-person cut-off sample, and 1-2 week test-retest in 358 people (r = 0.90) - [Innolitics record of DEN130033](https://fda.innolitics.com/device/DEN130033); [BioSpace press release](https://www.biospace.com/b-cerebral-assessment-systems-b-receives-fda-de-novo-approval-for-cognivue-cognitive-assessment-aid)
- The DEN130033 file lists 24 June 2013 as the De Novo date, implying roughly two years to decision (Innolitics shows 711-723 days depending on the start date used) - [Innolitics](https://fda.innolitics.com/device/DEN130033); [Innolitics 510k search](https://510k.innolitics.com/device/DEN130033)
- Cognetivity's Integrated Cognitive Assessment (CognICA), a roughly 5-minute iPad test already CE-marked, was cleared through 510(k) under 882.1470 in October 2021 - [FDAnews](https://www.fdanews.com/articles/204999-cognetivity-neurosciences-gets-fdas-510k-clearance-for-cognitive-assessment); [Newswire](https://newswire.ca/news-releases/cognetivity-neurosciences-granted-fda-clearance-for-commercial-distribution-of-ica-throughout-us-healthcare-market-880568554.html)
- ImPACT (concussion) was cleared as K181223 on 20 Oct 2018 under the sister regulation 882.1471 - [Innolitics K181223](https://510k.innolitics.com/device/K181223)
- BrainCheck describes BrainCheck Assess as an FDA Class II device; no 510(k) number was found - [BrainCheck](https://braincheck.com/platform/assess)
- Linus Health holds EU MDR Class IIa certification for its Core Cognitive Evaluation (including the Digital Clock and Recall); its DCTclock appears in FDA's device database under product code PTY "Computerized Cognitive Assessment Aid, Exempt" with no premarket number - [Medical Device Network](https://www.medicaldevice-network.com/news/linus-health-lands-eu-mdr-certification-for-cognitive-impairment-screening-tool/); [AccessGUDID DCTclock](https://accessgudid.nlm.nih.gov/devices/B626100930)
- Altoida announced FDA Breakthrough Device Designation for a device intended for Alzheimer's prediction and describes its product as a Class II, 510(k)-exempt computerized cognitive assessment aid - [VI Partners announcement](https://www.vipartners.ch/news/altoida-awarded-fda-breakthrough-designation-for-development-of-world-s-first-precision-neurology-device-for-prediction-of-alzheimer-s-disease)

Caregiver-collected home data precedent:
- Cognoa's Canvas Dx received De Novo authorization (DEN200069, June 2021) as an aid to diagnose autism in children 18-72 months, combining a caregiver questionnaire completed at home in an app, home video and physician input; its pivotal study enrolled 425 children at 14 sites, with 81% agreement among positives and 98% among negatives vs a specialist panel, and it gave a determinate result for only 32% of children - [MobiHealthNews](https://www.mobihealthnews.com/news/fda-greenlights-cognoas-tool-detect-autism-spectrum-disorder-kids); [Fierce Biotech](https://www.fiercebiotech.com/medtech/cognoa-s-ai-app-for-diagnosing-childhood-autism-gets-fda-green-light)
- A later Canvas Dx 510(k) (K243558, 11 April 2025) needed no new clinical testing because it relied on the De Novo's clinical data - [Innolitics K243558](https://fda.innolitics.com/device/K243558)

Blood biomarkers now available as reference standards:
- FDA cleared Fujirebio's Lumipulse plasma test through 510(k) in May 2025 as the first blood test to aid diagnosis of Alzheimer's (amyloid plaques) in adults 55+ with signs and symptoms; FDA said it is not a screening or stand-alone test - [FDA press release, May 2025](https://www.fda.gov/news-events/press-announcements/fda-clears-first-blood-test-used-diagnosing-alzheimers-disease)
- Roche's Elecsys pTau217 plasma test was cleared through 510(k) (Roche release 24 Aug 2026) for people 55+ with signs, symptoms or complaints of cognitive decline; it is not intended to predict dementia or monitor therapy response - [Practical Neurology, 26 Aug 2026](https://practicalneurology.com/news/fda-clears-the-elecsys-ptau217-blood-test-to-aid-in-alzheimer-disease-assessment/2488227/)

Costs and FDA context:
- FY2027 FDA user fees (1 Oct 2026 to 30 Sep 2027): 510(k) $28,653 ($7,163 small business); De Novo $191,020 ($47,755 small business); annual establishment registration $13,785 - [RAPS](https://www.raps.org/resource/fda-unveils-fy-2027-user-fee-rates.html); [Registrar Corp](https://www.registrarcorp.com/blog/medical-devices/medical-device-registration/fda-medical-device-user-fees-fy-2027/)
- FDA's Digital Health Advisory Committee met on 6 Nov 2025 on generative AI-enabled digital mental health devices; commentators expect new generative-AI diagnostic devices to be new intended uses likely needing De Novo and special controls; no 2026 meeting or dementia topic was found - [Orrick, Nov 2025](https://www.orrick.com/en/insights/2025/11/fdas-digital-health-advisory-committee-considers-generative-ai-therapy-chatbots-for-depression); [Psychiatric Times](https://www.psychiatrictimes.com/view/fda-committee-meets-on-generative-ai-digital-mental-health-devices)
- UK DRI's Minder platform is delivered as an NHS service (MinderCare) at Imperial College Healthcare, with a monitoring team reviewing data daily; no US FDA status was found - [Imperial College, Minder](https://www.imperial.ac.uk/uk-dri-care-research-technology/minder/)

### Inferences
- Precedent shows the shape of a future Save It device claim: a prescription aid for health care professionals, labelled "not diagnostic", with a pivotal study reporting agreement with a reference standard, test-retest repeatability and construct validity.
- 882.1470 covers a "battery of cognitive tasks", which Save It is not; passive object-placement and question-log analytics would likely need their own De Novo, as Cognoa's caregiver-data tool did.
  Breakthrough designation (as Altoida obtained) is worth asking for because dementia is serious and irreversible, but it does not lower the evidence bar.
- Order-of-magnitude budget for a De Novo (inference from the precedents, not a sourced figure): FDA fee about $48,000 as a small business, plus a multi-site study of hundreds of participants over 1-2 years, plus quality-system and software documentation; Cognivue took about two years in review alone.
- The realistic order is: wellness product, then IRB research with Emory, then (only if signals hold) a research-use-only clinician report, then a regulatory submission.

### Gaps
- FDA records were not found for BrainCheck's 510(k) number, Linus Health's DCR, Cambridge Cognition CANTAB or Cumulus Neuroscience; their US status could not be verified.
- Altoida's designation date and whether it has received marketing authorization were not found.
- I found no reliable published total development cost for any of these devices.
- I found no FDA-authorized passive home-monitoring device with a cognition or dementia claim.

## 5. Validation study design for a passive behavioural marker

### Takeaway
The accepted structure is V3: verify the sensing (did the camera see the put-down?), analytically validate the metric (is "repeat-question rate" computed correctly against human-labelled ground truth?), then clinically validate it against reference standards in a defined population.
ORCATECH, CART and Minder show the practical template: long (months to years), small-to-mid cohorts (82 to 301 people), annual reference assessments, technology-agnostic platforms and diverse recruitment.
For Save It, the hardest design issues are consent in Georgia (Emory IRB guidance allows surrogate consent only for treatment studies, unless the representative holds a research power of attorney) and the noise floor of reference measures (MoCA change of 4 points, CDR-SB 1-2 points).

### Cited Findings
Frameworks:
- The V3 framework splits evaluation of biometric monitoring technologies into verification (sample-level sensor output), analytical validation (the algorithm turning data into a measure) and clinical validation (the measure means something in a defined population and context of use), adapted from the FDA-NIH BEST biomarker resource - [Goldsack et al. 2020, npj Digital Medicine 3:55](https://www.nature.com/articles/s41746-020-0260-4)
- FDA's final guidance "Digital Health Technologies for Remote Data Acquisition in Clinical Investigations" (December 2023) covers DHT selection, verification and validation (applying whether or not the DHT is a device), usability, endpoint contextualization, risk, cybersecurity and record retention, and warns that changing a DHT mid-study can make results unreliable - [FDA Law Blog, Feb 2024](https://www.thefdalawblog.com/2024/02/fda-releases-final-guidance-on-use-of-digital-health-technologies-for-remote-data-acquisition-in-clinical-investigations/); [DLA Piper, Jan 2024](https://www.dlapiper.com/en/insights/publications/2024/01/fda-issues-final-guidance-on-digital-health-technologies-for-data-acquisition)

How the passive-sensing programs ran:
- ORCATECH's ISAAC study placed sensors in the homes of 265 older adults (mean age 83.3, 73% women, Portland) for an average of 33 months, measuring total activity, time out of home, walking speed and computer use, with annual health, function and neuropsychological assessments - [Kaye et al. 2011, J Gerontol B, PMC3132763](https://pmc.ncbi.nlm.nih.gov/articles/PMC3132763)
- CART was an NIH and VA interagency project (RFA-AG-16-021, U2C AG054397) built on ORCATECH, designed as a four-year non-randomized longitudinal infrastructure study with iterative user-centred design; partners included OHSU, Rush, the University of Miami and VA VISN20 - [CART OHSU protocol template](https://www.ohsu.edu/sites/default/files/2019-11/CART-OHSU-Protocol-Template.pdf); [NIH U2C AG054397](https://grantome.com/grant/NIH/U2C-AG054397-01)
- CART deployed to 232 homes (301 older adults) in four cohorts chosen for diversity (African American, Latinx, low-income, rural veterans), recruiting mainly through presentations and mailings to people already in research at the sites, with a deliberately unobtrusive, technology-agnostic platform - [Beattie et al. 2020, Digital Biomarkers, PMC7768162](https://pmc.ncbi.nlm.nih.gov/articles/PMC7768162)
- Minder's 2023 feasibility report covered 82 people with dementia (mean age 80.4) contributing 147,203 measurements over 958,000 participant-hours - [JMIR Aging 2023, e43777](https://aging.jmir.org/2023/1/e43777/PDF)
- A Minder analysis modelled daily activity changes in 120 households with a Markov chain - [arXiv 2307.11126](https://ar5iv.labs.arxiv.org/html/2307.11126)
- The MinderCare evaluation is registered as an ongoing non-randomised cohort compared with similar people receiving usual care, using linked health and care records, funded by LifeArc and UK DRI - [ISRCTN14997677](https://www.isrctn.com/pdf/ISRCTN14997677)

Reference standards and their noise:
- MoCA 95% minimal detectable change is about 4 points over 2-4 months (ICC 0.81) - [Feeney et al. 2016](https://www.pubmed.gov/27258421/)
- CDR-SB within-person meaningful change is about 1-2 points (up to 2.5 in an MCI trial analysis) - [Alzforum](https://alzforum.org/node/2681356); [J Prev Alz Dis 2023](https://www.jpreventionalzheimer.com/6687-establishing-clinically-meaningful-change-on-outcome-assessments-frequently-used-in-trials-of-mild-cognitive-impairment-due-to-alzheimers-disease.html)
- Cognivue's pivotal design (401 participants, stratified by impairment, blinded paired reference test, separate cut-off sample, 1-2 week test-retest in 358) is a worked example of what FDA accepted for a cognitive aid - [Innolitics DEN130033](https://fda.innolitics.com/device/DEN130033)
- FDA-cleared plasma tests (Lumipulse, May 2025; Elecsys pTau217, Aug 2026) are indicated for people 55+ with symptoms or complaints of cognitive decline - [FDA](https://www.fda.gov/news-events/press-announcements/fda-clears-first-blood-test-used-diagnosing-alzheimers-disease); [Practical Neurology](https://practicalneurology.com/news/fda-clears-the-elecsys-ptau217-blood-test-to-aid-in-alzheimer-disease-assessment/2488227/)

Consent and capacity in Georgia:
- Emory IRB guidance (version 3 Oct 2018, written under the pre-2018 Common Rule and Georgia law) says a legally authorized representative (LAR) can consent for adults only in studies with a treatment component; for studies without treatment, only the subject can consent unless the adult's LAR holds a durable power of attorney for research, and next of kin alone cannot - [Emory IRB guidance PDF](https://irb.emory.edu/_includes/documents/sections/guidance--enrolling_peopl_with_-diminished_-capacity.pdf)
- A University of Georgia policy says that for an adult lacking capacity only an LAR can consent (unless the IRB waives consent), that Georgia law controls research in Georgia, and that LARs include an appointed health care agent - [UGA LAR policy](https://research.uga.edu/docs/policies/compliance/hso/PP-Legally-Authorized-Representatives-Adults-Diminished-Consent-Capacity-Children.pdf)

Data standards:
- IEEE 1752.1 (mobile health data), co-shepherded by the Open mHealth community, supersedes Open mHealth schemas; device data can be normalised to it and then expressed as FHIR resources - [Frontiers in Digital Health 2025](https://www.frontiersin.org/journals/digital-health/articles/10.3389/fdgth.2025.1636775/full)
- A 2026 study mapping FHIR to the OMOP Common Data Model reached 74% coverage from FHIR to OMOP (Observation maps to the OMOP Measurement table) but only about 23% from OMOP back to FHIR - [Frontiers in Medicine 2026](https://www.frontiersin.org/journals/medicine/articles/10.3389/fmed.2026.1736785/full)
- An Austrian group built a FHIR server for bidirectional exchange with OMOP aimed at patient-generated health data - [Stud Health Technol Inform, SHTI240367](https://ebooks.iospress.nl/pdf/doi/10.3233/SHTI240367)

### Inferences
A staged validation plan for Save It (proposal; sizes are rough, not powered):

| Stage | Question | Design | Ground truth | Output |
|---|---|---|---|---|
| 1. Verification | Does the worn camera log put-downs and places correctly? | Scripted home sessions with staff (no patients), 20-50 sessions | Video annotated by two raters (research-only, never Roboflow) | Sensitivity and precision per item and landmark, by lighting and room |
| 2. Analytical validation | Are metrics (questions per observed hour, repeat rate, found rate) computed correctly and stably? | 10-20 cognitively normal volunteers, 4-8 weeks | Hand-audited query logs and diaries | Agreement, week-to-week reliability (ICC), minimal detectable change per metric |
| 3. Feasibility in target users | Will people with MCI or mild dementia wear it, and do caregivers accept it? | 20-40 dyads, 3 months, single site (Emory) | Wear-time logs, SUS usability, interviews | Wear time, dropout, burden, privacy concerns |
| 4. Clinical validation (cross-sectional) | Do metrics differ by stage and track informant reports? | 100-200 dyads stratified by CDR 0, 0.5, 1 (Cognivue-style stratification) | CDR-SB, MoCA, FAQ, RMBPC, ZBI-22; plasma pTau217 where clinically indicated | Correlations, known-groups validity |
| 5. Longitudinal validation | Do metric changes precede or track decline? | Same cohort, 12-24 months, 6-monthly assessments | Change in CDR-SB beyond 1-2 points, MoCA beyond 4 | Sensitivity to change, lead time |

Design rules that follow from the evidence:
- Make the run-in long; ORCATECH-scale programs measured over months to years, and test-retest reliability of every home metric should be established before any clinical claim.
- Report exposure (observed hours) for every metric, because wear time is itself linked to cognition.
- Pre-register the metric definitions, since many candidate metrics invite fishing.
- Recruit for diversity from the start (CART's four cohorts; the Goizueta ADRC Minority Engagement Core).
- Keep the device version fixed during a study phase, as FDA's DHT guidance warns.
- Consent: enroll people while they can consent for themselves (MCI and mild dementia), build in assent and dissent procedures and periodic re-consent, and use LARs only if they hold research powers of attorney or Emory's current policy allows otherwise; confirm the 2018 guidance is still current with Emory IRB.
- Standards: export metrics as FHIR Observations (custom codes, since no LOINC codes exist for these metrics) and keep a research copy mapped to OMOP Measurement; keep raw crops out of research exports.

### Gaps
- No published reliability, norms or minimal detectable change exist for any object-placement or question-log metric.
- I could not confirm whether Emory IRB updated its LAR guidance after 2018 or whether current Georgia law now allows surrogate consent for non-treatment research.
- No sample-size calculation is possible without variance estimates from pilot data.
- No LOINC codes for these constructs were found; whether LOINC would accept new codes was not researched.
- MinderCare outcome results were not yet published as of this search.

## 6. Research partners at or near Emory, funding, and how a student team would approach them

### Takeaway
Atlanta has unusually good partners: Emory's Goizueta ADRC (NIA-funded cohort and biomarker infrastructure), Emory Integrated Memory Care (a GUIDE participant and the model's prototype), and the Emory and Georgia Tech Cognitive Empowerment Program (MCI, with a technology core and Georgia Tech's IPaT HomeLab).
External money for early-stage dementia tech exists (NIA AITC a2 pilot awards up to $200,000; NIA SBIR/STTR, reauthorized through 2031 after a lapse; AARP's AgeTech Collaborative), but SBIR needs a company and AITC pilots now ask for regulatory and reimbursement plans.
The best first move for a student team is a faculty sponsor and a small IRB feasibility study, not a validation claim.

### Cited Findings
Emory and Georgia Tech:
- The Goizueta Alzheimer's Disease Research Center received a five-year, $21.9 million renewal of its NIA P30 grant in July 2025 - [Emory News, July 2025](https://news.emory.edu/stories/2025/07/hs_alzheimers_research_grant_29-07-2025/story.html)
- Its Clinical Core maintains a diverse longitudinal cohort of well-characterized participants, alongside a Longitudinal Biomarker Collection, a Minority Engagement Core supporting African American recruitment, and an Outreach, Recruitment and Engagement Core (2020 grant record) - [NIH P30 AG066511](https://grantome.com/grant/NIH/P30-AG066511-01)
- Emory Integrated Memory Care, run by the Nell Hodgson Woodruff School of Nursing, is a nurse-managed dementia primary care practice at Executive Park that also serves 18 senior living communities, with about 650 active patients, a GUIDE participant offering a 24/7 support line - [Emory Nursing, IMC](https://www.nursing.emory.edu/imc); [Emory News, June 2025](https://news.emory.edu/features/2025/06/emorys-integrated-memory-care); [iAdvance Senior Care](https://www.iadvanceseniorcare.com/emory-integrated-memory-care-tests-medicare-dementia-care-model/)
- The Charlie and Harriet Shaffer Cognitive Empowerment Program (CEP), part of the Goizueta Institute at Emory Brain Health, received a $10 million, four-year Cox Foundation grant (Phase II, January 2024); it partners with Georgia Tech's Institute for People and Technology and SimTigrate Design Lab and has therapeutics, built environment, technology and innovation accelerator cores - [Emory News, Jan 2024](https://news.emory.edu/stories/2024/01/som_bhc_cep_cox_grant/story.html)
- CEP requires an MCI diagnosis, runs a six-month on-site program at Executive Park, uses a MyCEP app and tracks members' activity, sleep and behaviours with digital technology - [CEP About page](https://empowerment.emory.edu/about/index.html); [Goizueta Brain Health, CEP](https://goizuetabrainhealth.emory.edu/program-initiatives/cep.html)
- Georgia Tech's IPaT HomeLab (director Brad Fain) tests assistive technology in people's homes, and Christopher Hertzog's group studies everyday memory interventions - [Georgia Tech news](https://hg.gatech.edu/node/628929)
- CEP says it reaches more people through Georgia Memory Net locations across the state - [Goizueta Brain Health, CEP](https://goizuetabrainhealth.emory.edu/program-initiatives/cep.html)

National programs and funding:
- NIA's Artificial Intelligence and Technology Collaboratories (AITCs), funded September 2021 with a coordinating center (sites include Johns Hopkins, MassAITC and PennAITech), have $65 million over five years; a2 pilot awards allow up to $200,000 in direct costs over 12 months; the first cohort (January 2023) funded 33 projects for more than $6.7 million, 61% on cognitive decline - [AITC overview, PMC10788144](https://pmc.ncbi.nlm.nih.gov/articles/PMC10788144/); [PR Newswire](https://prnewswire.com/news-releases/nia-funded-a2-collective-awards-first-tranche-of-40m-to-spur-innovation-at-the-intersection-of-ai-technology-and-aging-in-the-united-states-301716064.html) (sources differ on whether there are three or four collaboratories).
- A later a2 pilot call (fifth annual) sought AI projects on healthy aging and ADRD care and asked for a go-to-market strategy and regulatory and reimbursement pathways - [LeadingAge](https://leadingage.org/a2-pilot-awards-open-for-ai-based-healthy-aging-projects/)
- SBIR and STTR authority lapsed on 1 Oct 2025 and was reauthorized through 30 Sep 2031 in April 2026 (S. 3971); NIH had closed its SBIR/STTR opportunities in November 2025 - [SSTI](https://ssti.org/node/91454); [Granted AI summary](https://grantedai.com/news/sbir-sttr-reauthorized-through-2031-what-small-businesses-and-innovators-need-to) (consultancy blog; check NIH notices)
- A late-October 2026 law-firm recap described pent-up NIH small business applications, rescheduled peer review and award timelines stretching well into 2027 - [Duane Morris, 29 Oct 2026](https://blogs.duanemorris.com/lifescienceslaw/2026/10/29/recap-inside-nih-in-2026-practical-realities-for-companies-seeking-federal-funding/)
- NIA small business interest areas listed by aggregators include AI/ML tools for early detection and monitoring of AD/ADRD and wearable or mobile technology for direct, objective, continuous capture of everyday function in people living with AD/ADRD - [Granted AI listing](https://grantedai.com/grants/technology-to-detect-monitor-and-assess-daily-functions-in-individuals-w-national-institutes-of-health-2132d67c) (aggregator; verify on nia.nih.gov)
- The AgeTech Collaborative from AARP admits startups to its accelerator after an invited pitch; it runs four accelerator cohorts a year of up to 14 startups, charges no fee, and has run pitch events with $10,000 prizes - [AgeTech Collaborative, About](https://agetechcollaborative.org/about/); [MassChallenge AARP 2023](https://apply.masschallenge.org/aarp-2023)
- CART's platform came from OHSU's ORCATECH with partners including Rush, Miami, Oregon State, Penn and the VA - [CART OHSU protocol template](https://www.ohsu.edu/sites/default/files/2019-11/CART-OHSU-Protocol-Template.pdf)

### Inferences
Who to approach, for what:

| Partner | What they offer | What Save It offers them | First ask |
|---|---|---|---|
| Emory Integrated Memory Care (Nursing) | GUIDE patients and caregivers, navigators, 24/7 line | A tool aimed at the ZBI-22 burden measure and at navigator calls about lost items | A 30-minute demo to the care team; co-design of the caregiver summary page |
| Cognitive Empowerment Program (Emory Brain Health + Georgia Tech IPaT) | MCI participants who can consent, a technology core, HomeLab | A new everyday-memory data stream for people with MCI | Testing in HomeLab with staff (stage 1-2 of the validation plan) |
| Goizueta ADRC | Characterized cohort, CDR and biomarkers, diverse recruitment cores | A low-burden home measure to add to annual visits | Ask the Clinical Core about an ancillary study after feasibility data exist |
| ORCATECH / CART | Methods, platform experience | A new modality (object and question data) | Advice on study design; possible platform integration |
| NIA AITC a2 pilots | Up to $200k, mentoring | AI aging project | Apply with an Emory faculty PI once a feasibility protocol exists |
| AgeTech Collaborative | Accelerator, AARP network | Consumer AgeTech product | Pitch as a consumer wellness product |

How a student team should approach them:
- Find one faculty sponsor first (nursing, neurology or geriatrics at Emory, or IPaT at Georgia Tech); IRB submissions and ADRC ancillary studies need a faculty PI.
- Lead with the caregiver problem and the privacy design (crops only, no bathroom, no full frames), not with "early detection".
- Bring a one-page protocol for stage 1-3 (staff-only verification, then a small consented feasibility study) and the phrasing guide from `database_analytics.md`.
- Ask what data would be useful to them (for example, the IMC navigators' most common calls) before proposing metrics.
- Do not request patient data or identifiable images before an IRB-approved protocol.
- SBIR money requires a for-profit small business, so it is a later step; AITC pilots and AgeTech pitches fit sooner.

### Gaps
- Names of current Goizueta ADRC leadership and the right technology contact were not confirmed.
- I did not confirm whether Emory or Georgia Tech have a current digital biomarker or passive-sensing group beyond CEP and IPaT HomeLab.
- Current NIA SBIR/STTR receipt dates and NIA's 2026 small business interest areas were only seen on aggregators.
- Whether the CART consortium is still active as a funded network in 2026 was not established.
- AgeTech Collaborative's 2026 accelerator application dates were not found.

## 7. Ethics: who sees the data, the right not to know, stigma, and retention for research

### Takeaway
Ethics reviews conclude that digital early dementia detection at scale does not meet screening-programme standards, that predictive labels for people without established disease are hard to justify, and that people have a recognised right not to know.
For Save It this means three audiences with different views (the wearer, the family, the clinician), no derived "risk" outputs, the wearer's own choice about what is shared with clinicians, and research use only under separate, revocable consent.

### Cited Findings
- Ford, Milne and Curlewis judge that early dementia detection deployed at scale via digital technologies does not meet the standards for a screening programme, warn of worsening inequality from biased training data and unequal digital access, say acceptability is not established, and note that follow-up and support would be needed for anyone flagged - [Ford et al. 2023, PMC10909482](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10909482/)
- Ursin, Timmermann and Steger list the right not to know, the lack of disease-modifying treatment and the accuracy of AI-aided prediction among reasons against offering predictive tests to asymptomatic people - [Ursin et al., PhilArchive](https://philarchive.org/archive/URSEIO)
- A secondary summary of a study from Largent's group reports widespread fears that a biomarker indication could lead to stigma and discrimination by employers and insurers - [Oxford Global summary](https://www.oxfordglobal.co.uk/resources/the-ethical-issues-of-pre-emptive-dementia-diagnosis/) (secondary; original not read).
- Even FDA-authorized tools carry labelling limits: computerized cognitive assessment aids must warn they do not identify clinical diagnoses, and the Elecsys pTau217 test is not intended to predict dementia - [21 CFR 882.1470](https://www.law.cornell.edu/cfr/text/21/882.1470); [Practical Neurology](https://practicalneurology.com/news/fda-clears-the-elecsys-ptau217-blood-test-to-aid-in-alzheimer-disease-assessment/2488227/)
- GUIDE treats the caregiver as part of the care team, with caregiver assessment and support as required services - [CMS GUIDE fact sheet](https://www.cms.gov/files/document/guide-model-overview-fs.pdf)
- Emory IRB guidance limits surrogate consent for non-treatment research - [Emory IRB guidance](https://irb.emory.edu/_includes/documents/sections/guidance--enrolling_peopl_with_-diminished_-capacity.pdf)
- (Consent decreasing as need rises, carers' acceptance of surveillance, camera acceptance and the FTC Health Breach Notification Rule are covered in `database_analytics.md` sections 6 and 7.)

### Inferences
Who sees what (proposal):

| Viewer | Default view | Never shown by default |
|---|---|---|
| Wearer | Their own items and places, what is stored, a pause button, who has access | Trend charts framed as decline |
| Family (named caregivers) | Today card, item cards, weekly patterns with baselines | Raw question audio or full `heard` text beyond what is needed; comparisons with other people |
| Clinician | Only the monthly page the wearer (or their authorised representative) chooses to share | Live access, alerts, continuous feeds |
| Researchers | De-identified aggregates under separate IRB consent | Crops, transcripts, exact timestamps unless consented |

Ethical design rules:
- Ask the wearer, while they can decide, whether family may share summaries with clinicians, and record that choice as an advance preference (honouring the right not to know).
- Never compute or display risk scores, "decline detected" messages or comparisons to norms; show the person's own history only.
- Separate product consent from research consent: research participation must be opt-in, revocable, and not a condition of using Save It.
- Retention for research: keep aggregates, not crops or transcripts; set a fixed retention period in the protocol and delete on withdrawal where feasible.
- Prepare for misuse: monthly summaries could be used in guardianship, driving or family disputes; say in the privacy notice that Save It is not designed or validated for those purposes.
- Equity: Save It needs a smartphone, Wi-Fi and English-language voice recognition, so any research sample will skew; plan recruitment through the ADRC Minority Engagement Core and CART-style community outreach.
- Copy rule: keep using "built with HIPAA-style safeguards" and never claim HIPAA compliance.

### Gaps
- NIH Data Management and Sharing Policy requirements and typical retention periods for NIA-funded digital data were not researched.
- No study found on how people with MCI want passive monitoring results shared with their doctors, or on advance directives for data sharing in dementia.
- Georgia-specific rules on research use of data from people who later lose capacity were not researched.
- The original Largent study on stigma fears was not read.
