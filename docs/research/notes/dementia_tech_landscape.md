# Assistive technology for people living with dementia at home: landscape, gaps and extension ideas for Save It

Research date: 15 Nov 2026.
Scope: 2020-2026 products, research prototypes, caregiver-need data, design and privacy evidence, recent hackathon and startup work.
Convention: "company claim" marks a figure that comes only from the vendor or a vendor-affiliated study.

## 1. Object finding for dementia: trackers, key finders, camera-based research systems

### Takeaway
Misplacing is one of the most common and most distressing everyday symptoms, and it is mostly a "forgot where I set it down" problem, which is exactly what a passive put-down log answers.
Existing answers each break for dementia: tags need the person to tag and then operate an app, Meta's glasses need the person to say "remember this" at put-down time, Astra's memory is short and session-based, general egocentric video search is still far from reliable, and no randomized trial shows any memory-support device works.

### Cited Findings
- In the VISTA galantamine trial sample (130 community-dwelling people with mild to moderate Alzheimer's and their carers, video-recorded interviews), misplacing came up for 74% of patients (96 of 130), and 45 of them chose it as a treatment goal to track - [Hamilton, Fay, Rockwood 2009, JNNP (abstract)](https://pesquisa.bvsalud.org/bvseps/resource/pt/mdl-19293172)
- In the same study, misplacing was "the inability to recall where an item had been set down or put away" in 81% of cases, rather than putting items in odd places; hiding items appeared in about 15% - [Hamilton et al. 2009 (abstract record)](https://latam-cl.demo.elsevierpure.com/es/publications/misplacing-objects-in-mild-to-moderate-alzheimers-disease-a-descr)
- 58% of those patients were aware of their misplacing, and most of those aware were distressed by it - [Hamilton et al. 2009 (abstract)](https://pesquisa.bvsalud.org/bvseps/resource/pt/mdl-19293172)
- An online symptom-tracker study of 787 people found most who tracked misplacing picked the "lost and found" type (forgetting where items are), with odd placements becoming more common as severity rose - [International Psychogeriatrics, "Characterizing the symptom of misplacing objects..."](https://resolve.cambridge.org/core/journals/international-psychogeriatrics/article/characterizing-the-symptom-of-misplacing-objects-in-people-with-dementia-findings-from-an-online-tracking-tool/9CD88B66B66EB8D98FD9430893378794) (abstract-level only; full text not read)
- The 2017 Cochrane review of assistive technology for memory support in dementia found zero randomized trials meeting its criteria, so it could neither support nor refute effectiveness - [Cochrane CD009627](https://www.cochrane.org/evidence/CD009627_assistive-technology-memory-support-dementia)
- AirTag and Tile do not report their own position; they depend on passing phones, are not real-time GPS, and AirTag has no geofence or departure alert - [iMore](https://www.imore.com/apple/airtags-have-a-controversial-new-use-tracking-loved-ones-with-dementia); [AARP on tracking devices](https://www.aarp.org/home-family/personal-technology/info-2020/tracking-apps-devices)
- Caregivers report using AirTags on people with dementia, including a case where the location had not updated for 20 minutes during a search, and guides warn tags are easily removed by a confused person - [iMore](https://www.imore.com/apple/airtags-have-a-controversial-new-use-tracking-loved-ones-with-dementia); [FOX 5 Atlanta](https://www.fox5atlanta.com/news/americans-are-using-apple-airtags-to-track-loved-ones-with-dementia-report-says) (news and consumer guides, not research)
- An NIH SBIR Phase I grant (R43 AG065130) funded an ultra-wideband tag system for memory care units to locate belongings within about a foot and alert staff when an object leaves its expected room; it is a development project, not a trial - [Grantome R43 AG065130-01](https://grantome.com/grant/NIH/R43-AG065130-01); [listing](https://www.findatrial.com/research/tool-to-help-caregivers-find-items-lost-by-people-with-dementia-NIH-11181987)
- University of Waterloo (2023) built a mobile robot that detects and tracks objects a user registered and guides them to it; testing with people with dementia was planned after tests with people without disabilities - [Labroots](https://labroots.com/trending/technology/25290/robots-help-people-dementia-lost-items)
- Google Project Astra (I/O, May 2024) demo: after walking around an office, the user asked where his glasses were and Astra said they were next to a red apple, although they had not been pointed out - [Engadget](https://www.engadget.com/googles-project-astra-uses-your-phones-camera-and-ai-to-find-noise-makers-misplaced-items-and-more-172642329.html)
- Google described Astra as "continuously encoding video frames, combining the video and speech input into a timeline of events, and caching this information for efficient recall"; hands-on coverage called the recall short-term and likely session-based and raised concern that the memory is uploaded to Google - [Engadget](https://www.engadget.com/googles-project-astra-uses-your-phones-camera-and-ai-to-find-noise-makers-misplaced-items-and-more-172642329.html); [TechRadar hands-on](https://techradar.com/computing/artificial-intelligence/hands-on-with-googles-project-astra-the-ai-that-knows-where-you-left-your-keys)
- Ray-Ban Meta (Connect, Sept 2024) added a memory feature: the user asks Meta AI to remember something such as where they parked, and it takes a photo and creates a reminder - [Meta newsroom](https://about.fb.com/news/2024/09/ray-ban-meta-glasses-new-ai-features-and-partner-integrations/); [Maginative](https://www.maginative.com/article/meta-begins-rolling-out-memory-feature-to-ray-ban-smart-glasses/)
- Meta's own example phrase is "Hey Meta, remember where I put my keys", i.e. an explicit, user-initiated save - [Meta AI glasses voice assistant page](https://www.meta.com/ai-glasses/ai-glasses-voice-assistant/)
- The Dec 2024 v11 update added "Live AI" (continuous video, no wake word, remembers earlier questions) for Early Access members only - [Kowatek summary of v11](https://blog.kowatek.com/2024/12/17/ray-ban-meta-glasses-just-got-their-most-futuristic-ai-update-yet) (secondary source)
- Ego4D (3,000+ hours of egocentric video) defines an "episodic memory" benchmark that makes a long video history queryable by object and natural-language question - [Ego4D paper, arXiv 2110.07058](https://arxiv.org/abs/2110.07058)
- Ego4D-derived query templates include "Where did I put X before event Y?" - [Emergent Mind summary of Ego4D-Haystack](https://www.emergentmind.com/topics/ego4d-haystack-dataset) (aggregator; not verified against the paper)
- State of the art is still weak: a 2nd-place entry in the CVPR 2024 Ego4D Natural Language Queries challenge reached a mean Recall@1 of 23.15 - [ObjectNLQ, arXiv 2406.15778](https://arxiv.org/abs/2406.15778v1)
- CrossSense, AI smart glasses whose assistant "identifies objects in the user's surroundings" and guides daily routines, won the GBP 1 million Longitude Prize on Dementia (announced 24 Mar 2026), aiming for public availability in early 2027; no trial results or privacy design were reported - [Nesta](https://www.nesta.org.uk/blog/ai-smart-glasses-companion-winner-of-longitude-prize-on-dementia/)
- As a finalist (Oct 2024), CrossSense was described as glasses that help users recognise objects and people and prompt what to say or do, working with prescription lenses - [Alzheimer's Society](https://www.alzheimers.org.uk/cy/node/94506)

### Inferences
- The dominant failure mode of trackers for dementia is that they require a new habit (attach tag, open app, press a button) from the person whose memory is failing, and glasses and keys are hard to tag; Save It's passive capture plus a phone call asks nothing new of the patient at put-down or retrieval time.
- Meta's "remember this" model fails for exactly this population, because the person must anticipate forgetting at the moment of put-down.
- Ego4D numbers (R@1 about 23%) show unconstrained "where did I put X" over raw video is unsolved; Save It's constrained design (registered items, named landmarks, a database of stays, two-frame rule) is a defensible engineering answer, and the pitch can say so.
- CrossSense is the most important precedent: a funded, prize-winning, glasses-based dementia assistant with object recognition. Save It differentiates on hardware the family already owns (a phone on a lanyard), access by an ordinary phone or FaceTime call, persistent cross-session memory with timestamps and photos, and documented privacy rules.
- Because the Cochrane review found no RCTs, Save It should not claim clinical benefit; it can claim it targets the most common sub-type of misplacing (81% "where did I set it down").

### Gaps
- No peer-reviewed usability study of AirTag or Tile with people with dementia was found; findings above come from news and consumer guides.
- Could not confirm whether Ray-Ban Meta or Astra memory has been evaluated with people with cognitive impairment; none found.
- No Alzheimer's Society or Dementia UK guidance page specific to Bluetooth item locators was retrieved.

## 2. Voice assistants and companions for dementia: Alexa Together, reminders, ElliQ, Echo Show, day clocks

### Takeaway
Big-tech caregiver voice products have retreated (Alexa Together launched Dec 2021 at USD 19.99/month and is now discontinued, replaced by a narrower USD 5.99/month Emergency Assist), while the momentum has moved to AI companions (ElliQ, Meela) whose headline benefits are vendor or self-reported.
Speech recognition is measurably worse for people with dementia, so any voice product must tolerate slow, quiet, paused speech.

### Cited Findings
- Alexa Together was announced Sept 2021 and launched Dec 2021 at USD 19.99/month or USD 199/year, building on the free Alexa Care Hub - [TechCrunch](https://techcrunch.com/2021/12/07/amazon-launches-its-19-99-per-month-alexa-together-elder-care-subscription-for-families/)
- Amazon's launch post now states "Alexa Together is no longer available. You can now subscribe to Alexa Emergency Assist for remote caregiver service" (update dated 21 May 2025 in the search index) - [About Amazon](https://www.aboutamazon.com/md/news/devices/alexa-together-launches-to-help-customers-remotely-care-for-loved-ones)
- Alexa Together's caregiver features included an activity feed and alerts when there was no activity within a set time - [The Senior List](https://www.theseniorlist.com/caregiving/alexa-together)
- Vayyar's consumer radar fall sensor was "sold exclusively with Alexa Together", so the discontinuation also removed a consumer fall-detection channel - [Vayyar Care device page](https://vayyar.com/care-docs/b2c/)
- Alexa Emergency Assist costs USD 5.99/month or USD 59/year, lets up to 25 contacts drop in, get emergency notifications and add reminders, but provides no active monitoring: the user must initiate the call - [Tom's Guide](https://tomsguide.com/news/alexa-emergency-assist-what-it-is-how-much-it-costs-and-how-it-could-save-your-life)
- ElliQ (Intuition Robotics): NYSOFA's state-funded rollout to 800+ older New Yorkers reported a "95% reduction in loneliness" and users interacting 30+ times a day, 6 days a week (Aug 2023) - [NYSOFA press release](https://aging.ny.gov/news/nysofas-rollout-ai-companion-robot-elliq-shows-95-reduction-loneliness)
- The ElliQ figures were announced jointly by the agency and vendor and are described as self-reported pilot data, not a controlled trial - [Robotics 24/7](https://robotics247.com/article/elliq_companion_robot_reduces_loneliness_95_percent_finds_new_york_state_rollout) (marketing claim without independent evaluation)
- ElliQ pricing: USD 249.99 enrollment plus USD 59.99/month (or USD 49.99/month on an annual plan), which includes a device lease - [ElliQ subscription page](https://elliq.com/products/annual-subscription); [ElliQ FAQ](https://elliq.com/pages/faqs)
- Meela (Bain Capital Ventures-led USD 3.5M seed, Sept 2025) reaches seniors by scheduled phone calls "no apps, no devices, just the phone they already use", with a caregiver dashboard of alerts and conversation insights - [Business Wire](https://www.businesswire.com/news/home/20250911525548/en/Meela-Launches-Personalized-AI-Companion-to-Combat-Loneliness-Epidemic-Among-Seniors); [Bain Capital Ventures](https://baincapitalventures.com/insight/meela-delivers-companionship-and-ai-powered-conversation-to-america-s-seniors/)
- Meela is reported at about USD 40/month (aggregator, unverified) - [Chatgate](https://chatgate.ai/post/meela)
- A Dec 2025 report described an AI voice companion "showing promise in reducing depression, anxiety in nursing home residents" (RiverSpring and Meela) - [Skilled Nursing News](https://skillednursingnews.com/2025/12/ai-voice-companion-shows-promise-in-reducing-depression-anxiety-in-nursing-home-residents/) (headline only; methods not read)
- Cohn et al. (arXiv preprint, Feb 2026): 83 older adults (cognitively normal, MCI, dementia) read commands to Alexa; ASR errors were significantly higher for people with dementia, and vocal intensity, voice quality and pause ratio predicted accuracy - [arXiv 2602.23436](https://arxiv.org/abs/2602.23436)
- The same paper recommends speaker-personalized ASR, human-in-the-loop correction and adapting the interaction to the user's abilities - [arXiv 2602.23436](https://arxiv.org/abs/2602.23436)
- Jiménez et al. 2024 (Universal Access in the Information Society): 3 older adults used an Echo with Alexa for 20 days; they had some difficulties but could use it and wanted to continue; the paper frames repetitive questions as among the most common symptoms driving caregiver burden - [AMiner record](https://www.aminer.org/pub/65d16e0e939a5f4082436cdb/evaluating-smart-speakers-as-assistants-for-informal-caregivers-of-people-with-dementia)
- Family carers and professionals interviewed in 2022 used voice assistants mainly for reminders, leisure and monitoring, and reported barriers to use - [Frontiers in Dementia 2022](https://www.frontiersin.org/journals/dementia/articles/10.3389/frdem.2022.1049464/text)
- Playlist for Life tested Alexa with five people with dementia and two carers over ten weeks for music, and its guidance warns voice technology may not suit everyone with dementia - [Playlist for Life guidance PDF](https://playlistforlife.org.uk/wp-content/uploads/2025/01/Advice-on-smart-speakers_Playlist-for-Life.pdf)
- A CHI EA 2025 prototype voice assistant for care partners delivering cognitive stimulation therapy was feasible and acceptable to five care partners; requirements were personalization to severity and interests, collaboration with the care partner, and interactions that minimize frustration - [Penn State record](https://pure.psu.edu/en/publications/voice-assistants-to-deliver-cognitive-stimulation-therapy-for-per/)

### Inferences
- The retreat of Alexa Together suggests that a general-purpose smart speaker plus a monitoring subscription was not a strong enough product; single-purpose, high-value answers (where is my thing) are a more defensible wedge.
- Meela validates the "plain phone call, no app, no device" access model that Save It uses (phone and FaceTime), and pairs it with caregiver insight from conversation logs, a pattern Save It can copy cheaply.
- Given Cohn et al., Save It's voice line should accept partial and misheard item names (the Typesense fuzzy layer and "which one?" clarification are directly supported by this evidence) and should never punish a failed recognition with a long error message.
- ElliQ's 95% figure is a marketing claim; cite it only with the caveat.

### Gaps
- Exact Alexa Together shutdown date was not confirmed from a primary source (the only verified fact is Amazon's "no longer available" notice).
- No study of digital day clocks or calendar clocks with outcome data was found.
- No independent (non-vendor) evaluation of ElliQ outcomes was found, and no source states whether ElliQ is suitable for moderate dementia.
- No current documentation was found on whether Echo Show check-in and inactivity alerts survived in Emergency Assist.

## 3. Passive monitoring: CarePredict, Sensi.ai, Vayyar, Nobi, SafelyYou, Cherish, motion sensors

### Takeaway
Passive monitoring sells mainly to agencies and facilities, prices run from about USD 250 per sensor to about USD 2,500 per room, and the market is moving to camera-free sensing (radar, audio, light sensors) because cameras are the main privacy objection.
The best evidence (SafelyYou) is small, observational and vendor-affiliated, and the only large RCT of assistive technology and telecare for dementia (ATTILA, n=495) found no delay in care home admission and no wellbeing benefit.

### Cited Findings
- Sensi.AI raised a USD 31M Series B (June 2024, Insight Partners and Zeev Ventures) for audio "pods" that analyze sound for 100+ health and safety indicators and are sold to home care agencies, not families - [TechCrunch](https://techcrunch.com/2024/06/26/sensi-ai-grabs-31m-series-b-from-insight-zeev-to-monitor-seniors-24-7)
- Sensi says it supports over 80% of the largest US home care networks across 41 states (company claim) - [Maginative](https://www.maginative.com/article/sensi-ai-secures-31m-to-expand-ai-powered-home-care/)
- Sensi's earlier USD 3.5M seed was in March 2021 - [PR Newswire](https://prnewswire.com/news-releases/sensiai-raises-3-5m-seed-round-for-its-ai-quality-of-care-management-platform-in-senior-care-environments-301245626.html)
- CarePredict's Tempo wrist wearable learns a person's usual eating, walking, location, activity and sleep and alerts family on deviation; the @Home Kit lists at USD 499 plus a subscription, and the company says it is not a personal emergency response system and not connected to 911 - [CarePredict shop](https://shop.carepredict.com/products/the-carepredict-home-kit); [VentureBeat 2019](https://venturebeat.com/ai/carepredict-raises-9-5-million-for-ai-wearable-that-monitors-seniors-health/)
- SafelyYou (camera AI in memory care): a 2019 pilot (55 residents) reported EMT visits after falls dropping from 35.4% to 15.7% and ED visits from 24.5% to 8.3% versus control, with authors who are SafelyYou board members, employees, patent holders or stockholders - [AJMC](https://www.ajmc.com/view/safelyyou-new-research-reveals-safelyyous-aienabled-fall-detection-reduces-need-for-emergency-service-care-in-dementia-care-facilities)
- A SafelyYou study across 6 California facilities (66 residents, 436 falls) reported time on the ground after a fall falling by 29.6 minutes - [PR Newswire](https://prnewswire.com/news-releases/new-research-reveals-safelyyous-ai-enabled-fall-detection-reduces-time-on-the-ground-after-a-resident-falls-in-memory-care-facility-301323116.html); [PMC8277400](https://pmc.ncbi.nlm.nih.gov/articles/PMC8277400/)
- SafelyYou cites "41% fewer falls and 69% fewer ER visits" from an NIH-sponsored study in 11 communities (company claim; no peer-reviewed paper found) - [SafelyYou blog](https://www.safely-you.com/blog/fall-detection/)
- Nobi is a ceiling lamp that detects falls and says it shares no images with any cloud or server (company claim); pricing reported at about EUR/USD 2,490 to 2,499 plus USD 19/month - [Digital Trends](https://digitaltrends.com/home/nobi-smart-lamp-provides-help-when-older-people-fall/); [Pickr 2021](https://pickr.com.au/news/2021/nobi-keeps-a-watch-over-the-relatives-with-a-smart-lamp)
- Vayyar Care is a touchless, camera-free radar fall detector integrated with nurse call; its CEO put it at USD 250 per device with on average three per household - [Vayyar Care](https://vayyar.com/care); [Calcalist](https://www.calcalistech.com/ctechnews/article/rj0cnyqiq)
- Cherish Serenity (AT&T, 2023) is a radar device that detects body position, movement and biometrics without cameras or wearables, tracking up to two people within about 40 feet - [Medical Design & Development](https://www.medicaldesigndevelopment.com/topics/devices/news/22833720/att-launches-radar-tech-for-inhome-patient-monitoring); [TechCrunch Jan 2024](https://techcrunch.com/2024/01/09/cherish-health-serenity)
- Cherish partnered with Alarm.com (Jan 2024) and, in March 2026, with Aileen to combine radar monitoring with AI companionship - [Business Wire Mar 2026](https://www.businesswire.com/news/home/20260309434089/en/)
- Longitude Prize finalist Supersense is a "privacy-friendly" sensor box with no cameras or wearables that sends family automated wellbeing updates by WhatsApp or text - [Alzheimer's Society](https://www.alzheimers.org.uk/cy/node/94506)
- ATTILA RCT (12 English councils, 495 people with dementia): full assistive technology and telecare did not extend time living at home (adjusted HR for care home admission 0.84, 95% CI 0.63 to 1.12, p=0.20) and did not improve wellbeing of people with dementia or carers; participant-rated QALYs were slightly lower in the intervention arm - [ATTILA, Health Technology Assessment 2021](https://doaj.org/article/d12126d002194de2bf1160a89d5c136d); [UEA record](https://ueaeprints.uea.ac.uk/id/eprint/79857)
- ATTILA notes variable compliance and variable quality of needs assessments - [UEA record](https://ueaeprints.uea.ac.uk/id/eprint/79857)

### Inferences
- Every passive system above watches the person (falls, movement, routine deviation); none tracks belongings, so Save It's object memory is a complementary, not competing, data stream.
- Camera-free is now a headline selling point (Nobi, Vayyar, Cherish, Supersense), so Save It must lead with its privacy rules (crops only, no faces, no-capture rooms, no full frames) to avoid being lumped with surveillance cameras.
- ATTILA implies that bolting generic sensors onto a home does not move outcomes; matching technology to a specific, individual need is the lesson, which favours Save It's narrow scope.
- Prices (USD 250 to 2,500 hardware plus USD 19 to 60/month) give Save It a cost story: a spare phone on a lanyard plus cloud calls.

### Gaps
- No systematic collection of caregiver reviews (app store, forums) for these products was done; "what caregivers say" about false alarms, installation and cost is not evidenced here.
- No current official prices for Sensi, Cherish or Vayyar senior-living deployments were found.
- A claim that 60% of users of an in-home monitoring system had privacy concerns that grew after a year appeared in search summaries, but the primary source could not be identified, so it is not cited.

## 4. What people with dementia and caregivers say they need most

### Takeaway
The burden is large and rising (nearly 13 million US dementia caregivers, 19+ billion unpaid hours, 59% reporting high or very high emotional stress), and the daily stressors that technology can plausibly touch are misplacing (74% in one clinical sample), repetitive questions (driven by the same episodic-memory loss), wandering (6 in 10), and medication management.
Long-standing reviews list the unmet needs as personalized information, help with symptoms, social contact, and health monitoring and perceived safety.

### Cited Findings
- 2026 Facts and Figures: 7.4 million Americans aged 65+ have Alzheimer's dementia; nearly 13 million provide unpaid care; more than 19 billion hours in 2025 valued at over USD 446 billion - [Alzheimer's Association Facts and Figures](https://www.alz.org/alzheimers-dementia/facts-figures)
- 59% of dementia caregivers report high to very high emotional stress, and 66% of caregivers live with the person with dementia - [Alzheimer's Association Facts and Figures](https://www.alz.org/alzheimers-dementia/facts-figures)
- 2025 Facts and Figures: about 11.5 million caregivers gave 19 billion hours of unpaid care in 2024 (USD 413.4 billion); lifetime care cost is USD 405,262 with 70% borne by families; 60% of dementia caregivers were employed, 57% went in late, left early or took time off, and 16% took a leave of absence - [2025 Facts and Figures executive summary (PDF)](https://www.alz.org/getmedia/c05f7ba4-9aea-4cb0-8898-5e8bff3f0930/executive-summary-2025-alzheimers-disease-facts-and-figures.pdf)
- As many as 40% of family caregivers of people with dementia have depression (older Facts and Figures edition) - [Alzheimer's Association caregivers fact sheet](https://act.alz.org/site/PageNavigator/Advocacy_PublicPolicy/DocServer/caregivers_fact_sheet.pdf?docID=3022)
- AARP and NAC, Caregiving in the US 2025: 63 million family caregivers (up 45% in a decade), 44% providing high-intensity care, nearly 1 in 4 giving 40+ hours a week, 20% in fair or poor health due to caregiving, and almost 40% saying respite would help - [AARP press release, July 2025](https://www.aarp.org/press/releases/2025-07-24-new-report-reveals-crisis-point-for-americas-63-million-family-caregivers.html); [AARP report page](https://www.aarp.org/caregivingintheus2025)
- About half of caregivers report negative financial impact and a quarter take on debt - [AARP report page](https://www.aarp.org/pri/topics/ltss/family-caregiving/caregiving-in-the-us-2025/)
- Misplacing affected 74% of a clinical mild to moderate Alzheimer's sample, and most aware patients were distressed by it - [Hamilton et al. 2009](https://pesquisa.bvsalud.org/bvseps/resource/pt/mdl-19293172)
- Repetitive questioning "exasperates caregivers"; a teaching-case paper attributes it to impaired episodic memory and recommends finding and addressing triggers - [Hamdy et al. 2018, Gerontology and Geriatric Medicine](https://etsu.elsevierpure.com/en/publications/repetitive-questioning-exasperates-caregivers/)
- "Six in 10 people living with dementia will wander at least once; many do so repeatedly", and everyone with dementia is at risk - [Alzheimer's Association, wandering](https://www.alz.org/help-support/caregiving/stages-behaviors/wandering)
- A conflicting estimate puts wandering at about 36% of community-dwelling people with dementia (citing ECRI) - [NCOA adviser](https://ncoa.org/adviser/medical-alert-systems/dementia-wandering)
- The Alzheimer's Association advises calling 911 if a missing person is not found within about 15 minutes, and notes many are found within 1.5 miles of where they were last seen - [NCOA](https://www.ncoa.org/article/understanding-wandering-risks/)
- Lauriks et al. 2007 (Ageing Research Reviews): unmet needs are (1) general and personalized information, (2) support with symptoms of dementia, (3) social contact and company, (4) health monitoring and perceived safety; people with mild to moderate dementia can use simple electronic equipment and gain confidence from it - [Ulster record](https://pure.ulster.ac.uk/en/publications/review-of-ict-based-services-for-identified-unmet-needs-in-people-5/)
- Medication: a 2020 meta-analysis of technology for community-dwelling people with dementia found a "severe shortage of applicable studies"; included tools were a reminder calendar, a medication-adherence bottle and an automatic dispenser - [Technology Implementation in Persons With Dementia (PMC)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7742085/)
- A 2023 review of adherence technology for memory disorders included 15 studies, with reminder programs as one of four categories - [Applied Clinical Informatics](https://www.thieme-connect.com/products/ejournals/html/10.1055/s-0043-1776792)
- A registered RCT is testing a face-recognition medication dispenser for people with dementia at home - [ClinicalTrials.gov NCT07600684](https://clinicaltrials.gov/study/NCT07600684)
- Co-design: Lazar, Edasis and Piper (CHI 2017) argue HCI should use a "critical dementia" lens that challenges deficit narratives about how people with dementia are positioned in design - [A Critical Lens on Dementia and Design in HCI (PDF)](https://www.ics.uci.edu/~ampiper/papers/critical-dementia.pdf)
- The Longitude Prize on Dementia required all finalists to co-create with people with lived experience, and its winner was chosen with a panel of people affected by dementia - [Alzheimer's Society](https://www.alzheimers.org.uk/cy/node/94506); [Nesta](https://www.nesta.org.uk/blog/ai-smart-glasses-companion-winner-of-longitude-prize-on-dementia/)
- Longitude finalists' chosen problems map the perceived needs: object and person recognition (CrossSense), fall prediction (Theora 360), routine-learning reminders with carer escalation (AUTONOMOUS), camera-free wellbeing updates to family (Supersense), and a phone-style device with personalized reminders, recorded voice prompts and images of household items (MemoryAid) - [Alzheimer's Society](https://www.alzheimers.org.uk/cy/node/94506)

### Inferences
- Misplacing and repetitive questions share one cause (episodic memory loss), so a system that remembers on the person's behalf and answers patiently addresses both; Save It's question log is evidence of repeated asking that no product above surfaces to families.
- The strongest caregiver pain is emotional stress and time, so features that reduce interruptions ("she called Save It instead of me 6 times today") or give peace of mind at work map onto the 57% who disrupt work schedules.
- Two Longitude finalists (AUTONOMOUS, MemoryAid) and Supersense show that personalized reminders and family updates are what expert judges and lived-experience panels rewarded.

### Gaps
- Could not retrieve a ranked list of daily stressors from a large caregiver survey that explicitly includes "misplacing items"; the AARP and Alzheimer's Association reports measure intensity, health and finances, not specific behaviours.
- No quantitative source on sundowning prevalence or caregiver burden from sundowning was retrieved.
- Did not retrieve primary Dementia UK or Alzheimer's Society UK guidance on misplacing or repetitive questions.

## 5. Accessibility and design principles for voice and AI with people with dementia

### Takeaway
The evidence supports patient, plain but adult speech (slow, repeated key words, no baby talk), tolerance for misrecognition, personalization to stage and interests, carer involvement, and explicit respect for autonomy and consent.
Elderspeak is rated patronizing and is linked to resistance to care.

### Cited Findings
- In a University of Iowa study, 31 older adults rated most elderspeak features as more patronizing and less respectful than neutral speech - [PMC10738631](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10738631/)
- A concept analysis and review links elderspeak to a higher chance of resistance to care in people with dementia, while noting inconsistent definitions - [Understanding Elderspeak, PubMed 34476301](https://pubmed.ncbi.nlm.nih.gov/34476301/)
- Simplified vocabulary and grammar are the most problematic elderspeak features, while slow speech and repetition may help comprehension; Corwin describes alternatives that keep language rich while limiting breakdowns - [Corwin, Overcoming Elderspeak (PDF)](https://researchgate.net/profile/Anna-Corwin/publication/315545904_Overcoming_Elderspeak_A_Qualitative_Study_of_Three_Alternatives/links/60bfc753299bf1e6b71b8fc8/Overcoming-Elderspeak-A-Qualitative-Study-of-Three-Alternatives.pdf)
- Speakers with dementia had higher ASR error rates; vocal intensity, voice quality and pause ratio predicted errors; recommended fixes are personalized ASR, human correction, and Ability-Based Design (system adapts to the user) - [Cohn et al., arXiv 2602.23436](https://arxiv.org/abs/2602.23436)
- Design requirements from carers of people with dementia: personalization to severity and interests, collaboration between care partner and person with dementia, and interactions that minimize frustration and distress - [CHI EA 2025 CST voice assistant](https://pure.psu.edu/en/publications/voice-assistants-to-deliver-cognitive-stimulation-therapy-for-per/)
- Alzheimer Europe's Jan 2026 discussion paper and guidelines, written by the European Working Group of People with Dementia and the European Dementia Carers Working Group, ground technology design in the UN Convention on the Rights of Persons with Disabilities and name eight key issues for developers and funders - [Alzheimer Europe news, 21 Jan 2026](https://www.alzheimer-europe.org/news/alzheimer-europe-launches-discussion-paper-and-guidelines-ethical-use-technology-and-people)
- The same paper says monitoring and tracking should respect autonomy and consent: "overly intrusive systems may compromise dignity and trust, whereas inadequate safeguards can leave the person exposed to harm", and flags fraud and misuse of personal data - [Alzheimer Europe discussion paper (PDF)](https://www.alzheimer-europe.org/sites/default/files/2026-01/2026-01_alzheimer_europe_discussion_paper_on_the_use_of_technology.pdf) (quoted from search excerpt; full text not read)
- A 2025 review in Dementia reports persistent ethical concerns about surveillance, depersonalization and stigmatization, and criticism of tracking devices for privacy violation and power imbalance - [Dementia journal 2025 (Crossref record)](https://api.crossref.org/works/10.1177/14713012251341374)
- Alzheimer Europe's 2010 report set out ethical guidelines for assistive technology in dementia care - [Alzheimer Europe 2010 report](https://www.alzheimer-europe.org/resources/publications/2010-alzheimer-europe-report-ethical-issues-linked-use-assistive-technology)

### Inferences
- Save It's existing voice rules in `docs/DASHBOARD.md` (repeat the item name, one instruction per turn, no memory quizzing, landmark words, never send the person to climb or go outdoors) already match this evidence; the pitch should state them as design principles with these citations.
- Error tolerance is a research-backed requirement, not polish: a clarifying "the blue one or the green one?" and fuzzy name matching directly answer the Cohn et al. finding.
- Consent and dignity should be visible in the product (who agreed, what is captured, how to pause), because the current ethics literature treats tracking as a power-imbalance risk.

### Gaps
- No primary source was found for a "consistent persona" recommendation specific to dementia voice agents; it is plausible but unevidenced here.
- No study comparing a familiar family voice versus a synthetic voice for people with dementia was retrieved.

## 6. Privacy expectations for in-home cameras among older adults and caregivers

### Takeaway
Acceptance of cameras is conditional: it drops sharply for intimate activities and private rooms (bathroom, bedroom), rises with care need and perceived benefit, and depends on control (on/off, where and when), privacy-preserving processing, and data going only to authorized people.
Carers of people with dementia can be highly supportive (over 90% in one Northern Ireland study) but tie support to consent.

### Cited Findings
- Maidhof, Offermann and Ziefle 2023 (Frontiers in Public Health, n=146, scenario survey, mean age 37): rated privacy need was highest for sexual activity (3.90 of 4), toileting (3.70) and showering (3.55), and lowest for gardening (1.43) and washing dishes (1.82) - [Eyes on privacy](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2023.1186944/full)
- In that study, intention to use video monitoring was highest for household activity (4.07), then social (3.78), then intimate (3.57), and privacy barriers such as "invasion of privacy" rose from 4.13 to 4.71 with intimacy - [Eyes on privacy](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2023.1186944/full)
- Prior work cited there found living room, home office and kitchen the most accepted rooms and bedroom and bathroom the least - [Eyes on privacy (citing Himmel and Ziefle)](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2023.1186944/full)
- A scoping-review protocol on older adults and camera-based assisted living notes that privacy is the most discussed issue, that monitoring can make people feel "watched" or "spied on", that older adults may trade privacy for clearly beneficial features, and that negative attitudes are attenuated among people with higher care needs - [Tham et al. 2023, Open Research Europe](https://pmc.ncbi.nlm.nih.gov/articles/PMC10882197)
- The same protocol codes as acceptance factors: perceived control (turning cameras on or off, deciding where, when and how recording happens), whether images are processed for privacy, and whether data goes only to authorized people - [Tham et al. 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10882197)
- An Ulster University and Age NI study found over 90% of dementia carers supported in-home video monitoring, conditional on caveats including the older person's initial consent - [Telecare Aware](https://telecareaware.com/tag/ageni/) (small focus-group study; primary page returned 403)
- Vendors now advertise not using cameras or not sending images to the cloud as a feature (Nobi, Vayyar, Cherish, Supersense) - [Digital Trends on Nobi](https://digitaltrends.com/home/nobi-smart-lamp-provides-help-when-older-people-fall/); [Vayyar Care](https://vayyar.com/care); [Alzheimer's Society on Supersense](https://www.alzheimers.org.uk/cy/node/94506)
- Reviewers of Project Astra flagged that its memory is uploaded to Google as a concern - [TechRadar](https://techradar.com/computing/artificial-intelligence/hands-on-with-googles-project-astra-the-ai-that-knows-where-you-left-your-keys)

### Inferences
- Save It's rules (no full frames, item crops only, no faces described or stored, `capture_allowed = false` rooms dropped, crops purged after 7 days, Gemini `store=False`) map almost one-to-one onto the acceptance factors above; making them visible (a privacy card on the dashboard, a "paused" state, a no-capture room list) is cheap and is what judges and caregivers look for.
- A lanyard camera moves through the bathroom and bedroom, the least accepted rooms, so an explicit bathroom rule plus a one-tap or voice "pause" control is the single most important privacy feature to demonstrate.
- The Frontiers sample was young (mean 37), so older adults' and dementia dyads' views may differ; the protocol's "higher care need attenuates objections" finding suggests families of people with dementia are a more accepting audience than the general public.

### Gaps
- No empirical study was retrieved that tested silhouette, blur or crops-only views with people with dementia; a search summary mentioned silhouettes causing no privacy concerns, but the primary source was not identified.
- No data retention preference data (how long footage may be kept) for older adults was found.
- Completed results of the Tham et al. scoping review were not located (only the protocol).

## 7. Recent hackathon projects and startups in dementia tech (2023-2026): how to avoid being derivative

### Takeaway
Camera-based "where did I leave it" is now a common hackathon pattern (RecallAI, Memory Companion, TrackBack, Loupe) and a Big Tech demo (Astra, Meta), and smart glasses for dementia are crowded (MemoLens, CrossSense).
Save It's distinct angles are: the person with dementia uses only an ordinary phone or FaceTime call; memory persists across days with honest uncertainty states and outcome feedback; the family gets insight from the question log; and privacy rules are designed in.

### Cited Findings
- MemoLens / Empowering Memories (DubHacks '24, Oct 2024): first place in the AWS Gen-AI and Cloud Computing track; Vuzix M400 smart glasses with facial recognition and a customizable AI assistant for people with Alzheimer's - [Georgia Tech news](https://hg.gatech.edu/node/677961)
- RecallAI (Cal Hacks 13.0): detects registered belongings with YOLO plus visual embeddings, stores timestamped sightings and snapshots in SQLite, and answers with Claude, e.g. "Your AirPods were last seen on your desk 23 minutes ago"; not framed for dementia; no award stated - [DEV Community write-up](https://dev.to/rihaan_hashmani_3070e3d22/recall-ai-1ncm)
- Memory Companion uses a room camera and an LLM to help patients find misplaced objects (no award found) - [Devpost](https://devpost.com/software/memory-companion) (from search snippet; page returned 403)
- Loupe (a "Lost and Found" themed hackathon) guides a wearer toward a misplaced wallet or keys; TrackBack plans object finding from camera footage - [Devpost Loupe](https://devpost.com/software/loupe); [Devpost TrackBack](https://devpost.com/software/trackback)
- Other Devpost dementia projects focus on routines and confusion detection (EverCare), photo-based reminiscence (MemoReplay) and education (VitAlz) - [Devpost EverCare](https://devpost.com/software/evercare-tneovq); [Devpost VitAlz](https://devpost.com/software/vitalz)
- CrossSense won the GBP 1M Longitude Prize on Dementia (Mar 2026) with AI glasses that identify objects and guide routines - [Nesta](https://www.nesta.org.uk/blog/ai-smart-glasses-companion-winner-of-longitude-prize-on-dementia/)
- AARP AgeTech After Dark 2026 (CES, Jan 2026) was won by Captify (captioning glasses); the dementia finalist Memcara is a music-therapy platform at USD 29.99/month in 15 pilots - [AARP](https://www.aarp.org/personal-technology/captify-wins-agetech-after-dark-2026/)
- Funded startup patterns: Sensi.AI (audio, agencies, USD 31M Series B 2024), Meela (phone-call companion with caregiver dashboard, USD 3.5M seed 2025), ElliQ (tabletop companion, USD 59.99/month), Cherish plus Aileen (radar plus AI companionship, 2026) - [TechCrunch](https://techcrunch.com/2024/06/26/sensi-ai-grabs-31m-series-b-from-insight-zeev-to-monitor-seniors-24-7); [Business Wire Meela](https://www.businesswire.com/news/home/20250911525548/en/Meela-Launches-Personalized-AI-Companion-to-Combat-Loneliness-Epidemic-Among-Seniors); [ElliQ](https://elliq.com/products/annual-subscription); [Business Wire Cherish](https://www.businesswire.com/news/home/20260309434089/en/)

### Inferences
- Judges who have seen RecallAI-style demos will ask "what is different?"; the answers Save It can show live are: no screen or app for the patient (a call), dementia-specific speech rules, belief states (`not_there_anymore`, `carried`, `possible_glimpse`) instead of a single "last seen", the two-frame rule against hallucinated sightings, and caregiver-facing insight.
- Glasses are a crowded and expensive form factor with a prize-funded incumbent (CrossSense); a phone on a lanyard is cheaper, uses hardware families already own, and avoids putting a camera on the face.
- The funded companies show a durable business pattern: patient-facing voice plus caregiver-facing insight (Meela, Sensi), which Save It can mirror with its question log.

### Gaps
- Could not confirm prize outcomes for RecallAI, Memory Companion, TrackBack or Loupe, or the year of Cal Hacks 13.0 from the sources read.
- No complete list of 2025-2026 dementia hackathon winners was found; Devpost galleries were not systematically browsed.

## 8. Ranked extension ideas for Save It: (impact for patient and caregiver) x (feasibility in hours to days)

### Takeaway
The highest-value, lowest-effort extensions reuse what Save It already stores (the question log, item sightings, rooms, the call channel) rather than adding new sensors: a caregiver insight digest, family-written answers to non-object repeated questions, a visible dignity and pause layer, and a "not there / I put it here" correction loop come first; pill-box tracking, a leaving-home check and lanyard fall alerts follow with more risk.

### Cited Findings
Ranked list (rank, idea, effort estimate, evidence):

1. **Caregiver insight digest from the question log** (hours).
   Daily or weekly card and text message: what was asked, how often, at what times (late-afternoon clusters may suggest sundowning, to be phrased cautiously), most-lost items and rooms, and the found rate from "did you find it?".
   Evidence: repetitive questioning strains caregivers - [Hamdy et al. 2018](https://etsu.elsevierpure.com/en/publications/repetitive-questioning-exasperates-caregivers/); 59% report high or very high emotional stress - [Alzheimer's Association](https://www.alz.org/alzheimers-dementia/facts-figures); funded products sell exactly this caregiver view (Meela's alerts and conversation insights, Supersense's WhatsApp updates, Alexa Together's activity feed) - [Business Wire Meela](https://www.businesswire.com/news/home/20250911525548/en/Meela-Launches-Personalized-AI-Companion-to-Combat-Loneliness-Epidemic-Among-Seniors); [Alzheimer's Society](https://www.alzheimers.org.uk/cy/node/94506); [The Senior List](https://www.theseniorlist.com/caregiving/alexa-together)
2. **Family-written answers to repeated non-object questions on the same call** (hours; matches open decision D29 "life facts").
   "What day is it?", "Who is coming today?", "Who is June?", answered from a short list the family edits on the dashboard, in the same patient voice.
   Evidence: personalized information is the first unmet need in Lauriks et al. - [Ulster record](https://pure.ulster.ac.uk/en/publications/review-of-ict-based-services-for-identified-unmet-needs-in-people-5/); carers already use voice assistants for reminders - [Frontiers in Dementia 2022](https://www.frontiersin.org/journals/dementia/articles/10.3389/frdem.2022.1049464/text); two Longitude finalists (AUTONOMOUS, MemoryAid) are built on personalized reminders and prompts - [Alzheimer's Society](https://www.alzheimers.org.uk/cy/node/94506)
3. **Dignity and control layer** (hours).
   A "stop watching" voice command and a pause button on the lanyard page, a visible capture indicator, the no-capture room list and retention rule shown on the dashboard, and a recorded consent step.
   Evidence: perceived control over when and where cameras record and data going only to authorized people are acceptance factors - [Tham et al. 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10882197); bathroom and bedroom are least accepted and intimate activities most objected to - [Maidhof et al. 2023](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2023.1186944/full); carer support is conditional on consent - [Telecare Aware](https://telecareaware.com/tag/ageni/); ethics guidance stresses autonomy, consent and dignity - [Alzheimer Europe 2026](https://www.alzheimer-europe.org/news/alzheimer-europe-launches-discussion-paper-and-guidelines-ethical-use-technology-and-people)
4. **Spoken correction loop: "it's not there" and "I put it in my bag"** (hours to a day; the contract already has `record_outcome`, and STATUS lists `/miss` and `/told` as not yet saving).
   Evidence: ASR and recognition errors are higher for people with dementia, and human-in-the-loop correction is a recommended fix - [Cohn et al. 2026](https://arxiv.org/abs/2602.23436); minimizing frustration is a stated design requirement - [CHI EA 2025](https://pure.psu.edu/en/publications/voice-assistants-to-deliver-cognitive-stimulation-therapy-for-per/)
5. **"Did I take my pills?" via the pill organizer as a tracked item** (about a day).
   Register the pill box; answer with a hedged fact ("I last saw your pill box picked up at 8:10 this morning"), and flag to family if it was not seen handled by a set time; never state that a dose was taken.
   Evidence: medication management is a recognized need with weak technology evidence, where reminder systems look most promising - [PMC7742085](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7742085/); [Applied Clinical Informatics 2023](https://www.thieme-connect.com/products/ejournals/html/10.1055/s-0043-1776792); active trial interest in dispensers - [NCT07600684](https://clinicaltrials.gov/study/NCT07600684)
6. **Leaving-home check and "gone outside" notice** (about a day).
   "Do I have my keys?" and "What am I carrying?" answered from the `carried` state, plus a family notification when the wearer's camera sees the front door or outdoors; labelled as a heads-up, not a safety device.
   Evidence: 6 in 10 people with dementia wander - [Alzheimer's Association](https://www.alz.org/help-support/caregiving/stages-behaviors/wandering); searches should escalate after about 15 minutes and most are found within 1.5 miles - [NCOA](https://www.ncoa.org/article/understanding-wandering-risks/); tags lack departure alerts - [iMore](https://www.imore.com/apple/airtags-have-a-controversial-new-use-tracking-loved-ones-with-dementia)
7. **Lanyard fall or no-movement alert from the phone's motion sensors** (one to two days; highest false-alarm and liability risk).
   Evidence: faster response after falls in memory care reduced time on the ground by 29.6 minutes and emergency visits in vendor-affiliated studies - [PR Newswire](https://prnewswire.com/news-releases/new-research-reveals-safelyyous-ai-enabled-fall-detection-reduces-time-on-the-ground-after-a-resident-falls-in-memory-care-facility-301323116.html); [AJMC](https://www.ajmc.com/view/safelyyou-new-research-reveals-safelyyous-aienabled-fall-detection-reduces-need-for-emergency-service-care-in-dementia-care-facilities); Alexa Emergency Assist needs the user to start the call - [Tom's Guide](https://tomsguide.com/news/alexa-emergency-assist-what-it-is-how-much-it-costs-and-how-it-could-save-your-life); dedicated sensors cost USD 250 to 2,500 - [Calcalist](https://www.calcalistech.com/ctechnews/article/rj0cnyqiq); [Digital Trends](https://digitaltrends.com/home/nobi-smart-lamp-provides-help-when-older-people-fall/)
8. **Voice persona tuning** (minutes; partly done in `docs/DASHBOARD.md`).
   Adult, unhurried phrasing, repeat the item name, use the family's names for people and places, no "sweetie", no quizzing.
   Evidence: elderspeak is rated patronizing and linked to resistance to care - [PMC10738631](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10738631/); [PubMed 34476301](https://pubmed.ncbi.nlm.nih.gov/34476301/); slow speech and repetition may aid comprehension - [Corwin](https://researchgate.net/profile/Anna-Corwin/publication/315545904_Overcoming_Elderspeak_A_Qualitative_Study_of_Three_Alternatives/links/60bfc753299bf1e6b71b8fc8/Overcoming-Elderspeak-A-Qualitative-Study-of-Three-Alternatives.pdf)

### Inferences
- Ideas 1 to 4 need no new hardware or perception work: they read tables Save It already writes (`ask_item` logs every question with channel and time; `record_outcome` exists), so they fit the remaining hours and strengthen the core demo rather than distracting from it.
- Idea 1 is the strongest judge story because it turns a symptom (repeated asking) into a caregiver signal, which no product reviewed here does for belongings, and it mirrors the business model of funded startups.
- Ideas 5 to 7 carry a safety-claim risk: they must be worded as "last seen" facts and family heads-ups, never as confirmation of a dose taken or a guarantee of fall detection, consistent with the absence of RCT evidence (Cochrane, ATTILA).
- A one-slide "evidence" panel (74% misplace, 81% "where did I set it down", 59% high stress, 6 in 10 wander, ASR worse for dementia, privacy acceptance conditions) would let judges see the problem is real and the design choices are grounded.
- Effort estimates are this researcher's judgement from the repo layout in `CLAUDE.md`, `docs/STATUS.md` and `docs/DECISIONS.md`, not measured.

### Gaps
- No direct evidence was found that caregivers want a digest of their relative's questions specifically; the support is indirect (products that sell caregiver insight, caregiver stress data).
- No evidence was found on how accurately a chest-worn phone detects falls in older adults; idea 7's feasibility is untested.
- No evidence was found on whether people with dementia accept a camera on a lanyard specifically (as opposed to fixed cameras or glasses); this is the biggest open question for Save It's acceptability and would need co-design sessions.
