# Fall detection and automatic emergency escalation for Save It (United States, Georgia)

Scope: whether "if the patient falls during FaceTime, it calls 911 automatically" is a good idea, how to do it responsibly, and which other cheap safety features fit a FaceTime voice agent (Chert -> LiveKit -> Gemini Live) plus a lanyard iPhone that posts a frame every 0.5 s.
All pages were accessed on 15 Nov 2026 unless noted.
Every figure carries the year of the study or report it comes from.

## 1. How does fall detection work, and how accurate is it (wearables, phones, egocentric cameras, fixed cameras, radar)?

### Takeaway
Accelerometer fall detectors look accurate in the lab but lose a lot on real falls by older adults: on the FARSEEING real-world falls, published algorithms averaged about 57% sensitivity (2012), and the best newer method still makes roughly one false alarm every two hours of daytime wear (2020).
Video and radar products for care homes report big outcome gains, but the evidence is small and mostly comes from the vendors, and egocentric (wearable-camera) fall detection has only been tested on simulated falls by a handful of volunteers.

### Cited Findings
- Bagalà et al. (PLOS ONE, 2012) tested 13 published accelerometer algorithms on 29 real-world falls from the FARSEEING project. Average sensitivity was 57.0% ± 27.3%, with a maximum of 82.8% - [Bagalà et al. 2012, PMC3353905](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3353905/)
- In the same 2012 study, the algorithms produced between 3 and 85 false alarms during one day of monitoring three representative fallers - [Bagalà et al. 2012](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3353905/)
- Palmerini et al. (Sensors, 2020) trained and tested machine-learning detectors on 143 real-world falls in the FARSEEING repository, recorded with a lower-back inertial sensor.
  The best method (a support vector machine on multiphase fall-model features) reached sensitivity above 80%, a false alarm rate of 0.56 per hour, and an F-measure of 64.6% - [Palmerini et al. 2020, PMC7697900](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7697900/)
- The 2020 paper also cites a commercial wearable whose manufacturer-reported sensitivity was about 94% but which dropped to 25% when evaluated on real-world falls (as summarized from the paper; I did not read the original commercial-device study) - [Palmerini et al. 2020](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7697900/)
- A 2018 scoping review of real-world evaluation methods (Broadley et al., Sensors) reports that 13 previously published approaches, tested on real-world fall data, had mean sensitivity 0.57 and specificity 0.83, "considerably worse" than originally reported.
  It recommends sensitivity, precision and F-measure as more robust metrics than specificity, and notes most studies use small datasets - [Broadley et al. 2018, PMC6068511](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6068511/)
- A 2022 review in Frontiers in Public Health screened 267 studies and kept 15 on smartphone-accelerometer fall apps; it found the studies often lacked proper test sets, which "put into question whether reported results would correspond to real-world performance" - [Frontiers in Public Health 2022](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2022.996021/text)
- Egocentric camera: Wang et al. (IEEE Sensors Journal, 2023) recorded 5,858 short clips from volunteers wearing cameras at the neck and waist.
  Their late-fusion method reached 91.8% accuracy, 93.6% sensitivity and 89.2% specificity in leave-one-subject-out testing; the study used five volunteers and simulated falls - [Wang et al. 2023, University of Groningen](https://research.rug.nl/en/publications/fall-detection-with-a-non-intrusive-and-first-person-vision-appro/)
- An earlier single-volunteer case study (Wang et al., ICPR workshops, 2021) with chest and waist cameras detected all falls with one false positive - [University of Twente record](https://research.utwente.nl/en/publications/fall-detection-and-recognition-from-egocentric-visual-data-25th-i/)
- EGOFALLS (arXiv, 2023) is a public egocentric fall dataset of 10,948 clips with RGB, infrared and audio, recorded with action cameras and bodycams - [EGOFALLS, arXiv 2309.04579](https://arxiv.org/pdf/2309.04579v2)
- Fixed camera: a SafelyYou-linked pilot (American Journal of Managed Care, 2019) ran AI video fall detection in 6 dementia care facilities with 55 enrolled residents (of 193 eligible) for about 3 months.
  Controls had 147 falls, with 35.4% leading to EMT visits and 24.5% to ED visits; the intervention group had 83 falls, with 15.7% EMT and 8.3% ED visits (about 80% fewer ED visits) - [AJMC 2019](https://www.ajmc.com/view/realtime-video-detection-of-falls-in-dementia-care-facility-and-reduced-emergency-care)
- The 2019 SafelyYou pilot authors disclose they are board members, employees, patent holders or stockholders of SafelyYou; a registered randomized trial (NCT03685240) exists, but I found no published results - [AJMC 2019](https://www.ajmc.com/view/realtime-video-detection-of-falls-in-dementia-care-facility-and-reduced-emergency-care); [ClinicalTrials.gov NCT03685240](https://clinicaltrials.gov/study/NCT03685240)
- Radar: I found no independent peer-reviewed accuracy study of Vayyar Care. Vendor and partner material claims "exceptionally high accuracy" without figures, and a customer care home (Vayyar blog, April 2026) says it still sees some false alarms - [Austco press release 2023](https://prnewswire.com/news-releases/austco-augments-industry-leading-nurse-call-and-healthcare-communications-solutions-with-4d-imaging-radar-fall-detection-by-vayyar-301770239.html); [Vayyar blog, Sambrook House, 2026](https://vayyar.com/blog/elderly-care/how-sambrook-house-improved-resident-safety-with-vayyar-cares-falldetection-system/)
- A Vayyar blog post on alert fatigue (2021) says senior care operators "anecdotally" report about 80% of nurse-call callouts are false alarms, and admits there is "scant hard data" - [Vayyar blog 2021](https://vayyar.com/blog/elderly-care/alert-fatigue/)

### Inferences
- 0.56 false alarms per hour is roughly 13 per 24 hours if it held around the clock (my extrapolation; the 2020 paper measured 12-hour daytime sessions). Any detector at that rate wired straight to 911 would be unacceptable; wired to an "are you OK?" question it is merely annoying.
- A phone on a lanyard is a worse place for an accelerometer than the lower back (the FARSEEING sensor site): it swings, gets lifted to look at, and gets taken off and put down. Expect more false alarms than the figures above, and treat lanyard motion as a trigger for a question, never as proof of a fall.
- The camera already in Save It gives a second signal for free: after a real fall the frames tend to show floor or ceiling, blur, then a stable unusual view. Combining "impact on the accelerometer" with "camera stuck on the floor or ceiling for N seconds" should cut false alarms, but no study measures this exact combination.
- SafelyYou's outcome gain came largely from staff reviewing the video and deciding whether an ED visit was needed, not from automatic dispatch; this supports human-review escalation over auto-911.

### Gaps
- No real-world sensitivity or false-alarm data found for a chest or lanyard-worn smartphone specifically; the FARSEEING figures are for a lower-back sensor.
- No published Apple Watch fall-detection sensitivity or false-alarm rate on real elderly falls found in this pass.
- No independent accuracy figures for Nobi or Vayyar; no published results for the SafelyYou RCT.
- Egocentric camera studies use young volunteers and simulated falls; nothing on older adults or real falls.

## 2. Apple Fall Detection and Crash Detection: how they work, the false-call problem, and what a third-party app can access

### Takeaway
Apple does auto-call 911, but only after layered confirmation: Fall Detection waits for about one minute of immobility and then a 30-second loud countdown, and Crash Detection uses a 10-second alert plus a 30-second countdown; even so, Crash Detection flooded some 911 centers with false calls in 2022-2023.
A third-party iOS app cannot silently dial 911 (iOS shows a confirmation for `tel:` links since iOS 10.3), and the watchOS fall API only reports a fall to an app after Apple's own SOS flow has finished.

### Cited Findings
- Apple Watch Fall Detection (SE, Series 4 or later, Ultra): on a hard fall the watch taps the wrist, sounds an alarm and shows an alert that can be dismissed with "I'm OK" - [Apple Support 108896](https://support.apple.com/en-us/108896)
- If the watch detects movement it waits for the user and "won't call emergency services automatically"; if there is no movement for about a minute, it starts a 30-second countdown with a growing alert, then calls emergency services and the emergency contacts - [Apple Support 108896](https://support.apple.com/en-us/108896)
- On connection the watch plays a recorded message reporting a hard fall and the latitude and longitude, repeating until stopped; afterwards it texts emergency contacts with the location - [Apple Support 108896](https://support.apple.com/en-us/108896)
- Fall Detection turns on automatically for users who entered an age of 55 or older, is only available to people 18 or older, and requires Wrist Detection for automatic calls - [Apple Support 108896](https://support.apple.com/en-us/108896)
- Apple's own caveats: "Apple Watch cannot detect all falls" and it "might detect high-impact activity as a fall"; if you call by accident, "don't hang up" and tell the responder you do not need help - [Apple Support 108896](https://support.apple.com/en-us/108896)
- Crash Detection (iPhone 14 or later with iOS 16, Apple Watch Series 8 / SE 2nd gen / Ultra with watchOS 9): a 10-second spoken alert, then a 30-second countdown with loud whoops, then an automatic call that loops a recorded message with the estimated location every five seconds - [Apple Support 104959](https://support.apple.com/en-us/104959)
- Waukesha County, Wisconsin dispatchers reported about 300 unintentional Crash Detection calls over a few weeks; dispatchers in several states reported false crash alerts from roller coasters, skiing and snowmobiling (reported early 2023) - [KTVU / FOX, 2023](https://www.ktvu.com/news/apple-crash-detection-software-triggers-fake-911-calls-first-responders-say)
- Dispatchers said each false call must still be checked, diverting resources and risking desensitization; some ski resorts asked visitors to turn the feature off - [KTVU / FOX, 2023](https://www.ktvu.com/news/apple-crash-detection-software-triggers-fake-911-calls-first-responders-say); [EMS1](https://www.ems1.com/technology/articles/accidental-911-calls-increase-with-new-iphone-crash-detection-technology-gFQyqLGe9N8bJ8Vc)
- Apple said it optimized Crash Detection in iOS 16.1.2 and watchOS 9.2 (late 2022) to reduce false calls, and promised further optimizations (Feb 2023) - [MacRumors, 3 Feb 2023](https://www.macrumors.com/2023/02/03/apple-responds-to-false-crash-detection-report/); [MacRumors, 26 Dec 2022](https://www.macrumors.com/2022/12/26/iphone-14-car-crash-detection)
- iOS 10.3 and later show an alert and require user confirmation before dialing when a native app opens a `tel:` URL - [Apple Phone Links reference](https://developer.apple.com/library/ios/featuredarticles/iphoneurlscheme_reference/phonelinks/phonelinks.html); [Apple Developer Forums 73406](https://developer.apple.com/forums/thread/73406)
- The confirmation followed a 2017 exploit in which published code made iPhones repeatedly dial 911, causing thousands of accidental calls across the US; iOS 10.3 fixed it - [MacRumors, 30 Mar 2017](https://macrumors.com/2017/03/30/ios-10-3-fixes-911-exploit)
- A developer reported (2025 forum thread, unofficial) that for national emergency numbers the confirmation sheet does not appear and the call is placed immediately once the user taps the link; this is still a user-initiated tap, not silent dialing - [Apple Developer Forums 802156](https://developer.apple.com/forums/thread/802156)
- watchOS `CMFallDetectionManager` lets an app receive fall events, but it requires a special entitlement (`com.apple.developer.health.fall-detection`) requested from Apple - [Apple docs, CMFallDetectionManager](https://developer.apple.com/documentation/coremotion/cmfalldetectionmanager.md); [Apple Developer Forums 685761](https://developer.apple.com/forums/thread/685761)
- Developers report that the app is only notified after Apple's first-party flow and SOS resolution finish; if an emergency call is placed, the app hears about it after the call ends - [Apple Developer Forums 751373](https://developer.apple.com/forums/thread/751373)
- In a web page, `DeviceMotionEvent.requestPermission()` (needed on iOS Safari) requires a user gesture ("transient activation") and a secure (HTTPS) context - [MDN](https://developer.mozilla.org/en-US/docs/Web/API/DeviceMotionEvent/requestPermission_static)
- Since iOS 18 (fall 2024), participating 911 centers can ask an iPhone caller to share live video or photos during an emergency call (Emergency SOS Live Video); RapidSOS made this available free to its 5,700+ emergency communications centers, which it says cover over 99% of the US population (Oct 2024) - [RapidSOS](https://rapidsos.com/rapidsos-will-be-integrated-with-apple-emergency-sos-live-video/); [AppleInsider, Jul 2024](https://appleinsider.com/articles/24/07/24/first-responder-network-rapidsos-adds-emergency-sos-video-support-with-ios-18)

### Inferences
- Apple, with years of sensor data and a wrist sensor, still needs about 90 seconds of immobility plus countdown before dialing and still produced false-call waves. A hackathon detector should not dial anything without confirmation.
- The realistic Apple path for a family is "buy an Apple Watch and leave Fall Detection on" (default-on for 55+), not re-implementing it. Save It can say so in its pitch and focus its own effort on caregiver notification.
- The lanyard capture page can read the accelerometer only after a tap on an HTTPS page; that fits the existing capture page, which already needs a tap to start the camera.
- If the FaceTime agent detects a fall, the person is already on a call with a voice; the natural "are you OK?" step costs nothing extra.

### Gaps
- Whether `devicemotion` events keep firing when the iOS capture page is in the background or the screen locks was not confirmed from documentation (MDN page does not say).
- Apple does not publish which kinds of apps get the fall-detection entitlement.
- No current (2025-2026) data on whether Crash Detection false calls have fallen since Apple's updates.

## 3. May software automatically contact 911 in the United States? (federal law, Kari's Law, RAY BAUM'S Act, Georgia)

### Takeaway
No federal rule found that flatly bans an automated call to 911 for a real emergency (Apple places recorded-message 911 calls at scale), but autodialed calls to registered PSAP numbers are prohibited except for an "emergency purpose", with FCC fines of $10,000 to $100,000 per call, and a system that originates 911 calls takes on location-delivery duties under RAY BAUM'S Act.
In Georgia the false-alarm crime requires "knowingly" transmitting a false alarm, so an honest false positive is unlikely to be criminal, but the legal exposure of repeated false automated calls is unclear and no source settled it; this is "legally risky and unclear", not "clearly prohibited".

### Cited Findings
- 47 CFR 64.1202 bars operators of automatic telephone dialing systems (as defined in 47 USC 227(a)(1)) from contacting any number on the PSAP Do-Not-Call registry, by voice or text, except for an emergency purpose - [47 CFR 64.1202, Cornell LII](https://www.law.cornell.edu/cfr/text/47/64.1202)
- The rule defines "emergency purpose" as "a call made necessary in any situation affecting the health and safety of any person" - [47 CFR 64.1202, Cornell LII](https://www.law.cornell.edu/cfr/text/47/64.1202)
- The statute behind it (47 USC 1473, from section 6507 of the Middle Class Tax Relief and Job Creation Act of 2012) requires fines of not less than $10,000 and not more than $100,000 per call, and $100,000 to $1,000,000 per incident for unauthorized disclosure of registry numbers - [47 USC 1473, Justia 2019](https://law.justia.com/codes/us/2019/title-47/chapter-13/subchapter-v/sec-1473/)
- Penalty amounts depend on factors such as negligence, recklessness, willfulness and repeat violations (2012 commentary) - [Davis Wright Tremaine, 2012](https://www.dwt.com/insights/2012/10/fcc-adopts-rules-requiring-all-users-of-autodialin)
- In 2021 the FCC proposed requiring voice providers to block autodialed calls to numbers on the PSAP Do-Not-Call registry; I could not confirm whether it was adopted - [Mintz, Sep 2021](https://www.mintz.com/insights-center/viewpoints/2776/2021-09-21-tcpa-regulatory-update-fcc-attempts-curb-robocalls-911); [Route Fifty, Dec 2021](https://www.route-fifty.com/infrastructure/2021/12/protecting-911-from-unwanted-robocalls/316495/)
- Kari's Law (implemented by the FCC in 2019) covers multi-line telephone systems (offices, hotels): direct 911 dialing without a prefix and an on-site notification when 911 is called - [FCC 911 dispatchable location](https://www.fcc.gov/911-dispatchable-location); [911.gov](https://www.911.gov/project_mltsdispatchablelocation.html)
- RAY BAUM'S Act section 506 rules (adopted Aug 2019, effective 6 Jan 2020) aim to deliver a caller's "dispatchable location" with 911 calls regardless of platform, covering MLTS, fixed telephony, interconnected VoIP, TRS and mobile text - [FCC 911 dispatchable location](https://www.fcc.gov/911-dispatchable-location); [FCC 19-76 Report and Order](https://docs.fcc.gov/public/attachments/FCC-19-76A1.pdf)
- Georgia O.C.G.A. 16-10-28 ("Transmitting a false public alarm") applies to a person who "knowingly" transmits a false alarm (2006 text, about destructive devices and hazardous substances) - [Justia, O.C.G.A. 16-10-28 (2006)](https://law.justia.com/codes/georgia/2006/16/16-10-28.html)
- Georgia HB 118 (2019, "Protection Against False Claims for Emergency Services Act") added an offense of making an unlawful request for emergency services assistance (aimed at swatting); SB 421 amended the section again effective 1 Jul 2024. I could not extract the current penalty text - [HB 118 signed text](https://gov.georgia.gov/document/signed-legislation/hb-118pdf/download); [SB 421 signed text](https://gov.georgia.gov/document/2024-signed-legislation/sb-421/download); [Justia, current 16-10-28](https://law.justia.com/codes/georgia/title-16/chapter-10/article-2/section-16-10-28)
- Georgia O.C.G.A. 35-1-9 (HB 59, effective 1 Jul 2013) requires alarm monitoring companies to attempt "alarm verification" (contacting the site or user by phone or other electronic means, two numbers under Enhanced Call Verification) before requesting police for a burglar alarm signal - [Justia, O.C.G.A. 35-1-9 (2019)](https://law.justia.com/codes/georgia/2019/title-35/chapter-1/section-35-1-9/); [Security Systems News](https://www.securitysystemsnews.com/article/enhanced-call-verification-now-law-georgia)
- The Georgia verification requirement does not apply to fire alarms, panic or robbery-in-progress alarms, or when a crime in progress has been verified by video or audio - [GA HB 59 text, APCO](https://psc-legacy.apcointl.org/wp-content/uploads/GA-HB-59-CALL-VERIFICATION074.pdf); [Security Systems News](https://www.securitysystemsnews.com/article/enhanced-call-verification-now-law-georgia)

### Inferences
- What is prohibited: autodialing registered PSAP numbers for non-emergency purposes (fines per call), and knowingly causing a false emergency report (Georgia criminal law).
  What is legally unclear: whether a false-positive automated call counts as "for an emergency purpose" under 64.1202; a court or the FCC could go either way, and nothing found addresses software false positives.
  What is merely discouraged: automatic, unconfirmed calls to 911 by consumer devices in general (dispatcher complaints, Apple's own two-stage countdowns).
- If the Save It backend placed 911 calls itself through a cloud telephony number, it would be acting as a 911-capable calling service and would have to deliver a dispatchable location (the home address) with each call; this pulls the project into regulated E911 territory and is out of scope for a hackathon.
- Georgia's verification law is written for burglar alarms, but its logic (verify with the person before sending police; skip verification for panic alarms a person pressed) is a useful model: a fall the person confirms ("I fell, I need help") is like a panic alarm; a sensor-only guess should be verified first.
- Never test by calling real 911 during development or the demo; use a team member's phone standing in for "911" or the monitoring center.

### Gaps
- Civil liability (negligence) for a missed fall or a false automated 911 call: no case law or guidance found.
- Local false-alarm ordinances and fees (for example City of Atlanta or DeKalb County alarm permits) were not researched; they target registered alarm systems and may not apply to an app.
- Next Generation 911 and text-to-911 rules for automated messages were not researched.
- Whether Vapi or the underlying carrier numbers can dial 911 at all was not checked; check the provider's terms before assuming either way.
- The current text and penalties of O.C.G.A. 16-10-28 after the 2019 and 2024 amendments could not be extracted.

## 4. What does the industry do instead of dialing 911 directly? (monitoring centers, caregiver-first escalation, countdowns)

### Takeaway
Voice assistants and medical-alert companies route an alarm to a staffed monitoring center that talks to the person first and only then asks 911 for help (Alexa Emergency Assist says outright that it "is not a 911 service"), and some fall back to family or emergency contacts when the person cannot be reached.
For a developer, Noonlight's Dispatch API packages this: a trained dispatcher texts and calls the user within about 30 seconds, closes false alarms, and contacts the 911 center only when needed.

### Cited Findings
- Amazon Alexa Emergency Assist: saying "Alexa, call for help" connects to Urgent Response agents, who can request police, fire or ambulance dispatch based on the caller's information after confirming the address; Amazon states Urgent Response is not a 911 service and that Alexa does not call 911 by default - [Amazon, Alexa Emergency Assist](https://aboutamazon.com/news/devices/alexa-emergency-assist); [Amazon help: Urgent Response FAQs](https://digprjsurvey.amazon.com/csad/help/node/ThxMPNFnsaSBNhzSah)
- If the Urgent Response agent cannot reach the user, they call the user's Emergency Contacts (up to 3) and ask permission to dispatch; the service needs a paid subscription, a verified emergency address and a verified phone number, and is limited to the 50 US states - [Amazon help: Urgent Response FAQs](https://digprjsurvey.amazon.com/csad/help/node/ThxMPNFnsaSBNhzSah); [Tom's Guide](https://tomsguide.com/news/alexa-emergency-assist-what-it-is-how-much-it-costs-and-how-it-could-save-your-life)
- Noonlight Dispatch API: after a device triggers an alarm, Noonlight says its dispatchers "will text and call your user" within the first 30 seconds; if the situation resolves, the agent closes the alarm before routing to dispatch, and otherwise passes location and event details to 911 dispatchers - [Noonlight Dispatch API](https://noonlight.com/products/dispatch-api); [Noonlight panic button API blog](https://www.noonlight.com/blog/panic-button-api)
- Noonlight users cancel false alarms with a four-digit PIN or by talking to the dispatcher; the API emits webhooks such as `alarm.psap_contacted` and user-cancelled events - [Noonlight help](https://help.noonlight.com/using-noonlight/how-does-the-button-work); [Noonlight Dispatch API](https://noonlight.com/products/dispatch-api)
- The Noonlight API has endpoints to create an alarm, update its location, add device events, and add people who "will be notified of the alarm and be able to cancel it"; status is `ACTIVE` or `CANCELED` - [Noonlight docs](https://docs.noonlight.com/)
- Noonlight's claim that it resolves "over 99% of false alarms" is its own marketing, not independently verified - [Noonlight Dispatch API](https://noonlight.com/products/dispatch-api)
- Medical Guardian (a PERS company) answers alarms in a US-based monitoring center whose operators can dispatch emergency and non-emergency help, see family contact details and send a member of the user's "Care Circle"; it cites UL listing and TMA Five Diamond operator certification - [Medical Guardian monitoring center](https://www.medicalguardian.com/monitoring-center)
- TMA's Five Diamond designation is awarded annually to monitoring centers meeting standards for training, customer service and false dispatch reduction - [Best Company, medical alert certifications](https://bestcompany.com/blog/medical-alert-systems/medical-alert-safety-certifications); [TMA 2026 Five Diamond application packet](https://tma.us/wp-content/uploads/2026/05/2026-Five-Diamond-Application-Packet-NEW.pdf)
- UL 827 is the standard for central-station alarm services, covering fire, burglar and residential monitoring - [UL central station service certification](https://ul.com/resources/central-station-service-certification); [Intertek, UL 827](https://www.intertek.com/life-safety-security/standards/ul-827/)
- In home security, a common procedure is to call a subscriber-provided number, then retry, within about two minutes before calling police (industry article) - [SDM, enhanced alarm verification](https://www.sdmmag.com/articles/83237-field-guide-to-monitoring-a-notify-a-verifyatm-for-top-monitoring-results)
- Ring's professional monitoring calls the customer's emergency contacts first and dispatches if none can be reached (consumer practice, not a UL requirement) - [Ring support](https://ring.com/support/articles/5075g/Receiving-a-Call-from-Ring-Professional-Monitoring-Center)
- Apple's escalation sends a text with location to the user's emergency contacts after an automatic call - [Apple Support 108896](https://support.apple.com/en-us/108896)

### Inferences
- The consistent industry pattern is: detect, confirm with the person (countdown or human voice), escalate to a human who decides (monitoring agent or family), and only then involve 911.
- For Save It the cheapest responsible version is caregiver-first: the family member is the "monitoring center" for the demo, and Noonlight-style professional monitoring is the stated production path.
- Noonlight's developer page is "talk to sales", so a working integration may not be possible by Sunday morning; pitch it as the production design and show a stub (a webhook-shaped log line) rather than a live call.

### Gaps
- Noonlight pricing, sandbox access and turnaround for developer keys: not published on the pages read.
- Exact Medical Guardian, Life Alert and Bay Alarm Medical escalation rules (when they call family vs 911, what happens if the user does not answer) are not stated on their public pages.
- UL 1981 (central station automation) and any PERS-specific UL requirements were not confirmed.

## 5. Ethical and clinical constraints for people with dementia

### Takeaway
Falls in very old people often end in long lies on the floor, cognition is the strongest predictor of a long lie, and existing pendant alarms usually go unused in those falls, so passive detection has real value for this group.
The same cognitive impairment means the person may not be able to cancel a false alarm or consent meaningfully to monitoring, which argues for caregiver-first escalation, conservative alerting, and family consent recorded during setup.

### Cited Findings
- Fleming and Brayne (BMJ, 2008) followed 110 people over 90 in Cambridge for a year: 60% fell, 80% (53/66) of fallers were unable to get up after at least one fall, and 30% (20/66) lay on the floor for an hour or more - [Fleming and Brayne 2008, BMJ](https://www.bmj.com/content/337/bmj.a2227.abstract)
- In that cohort 82% of falls happened when the person was alone, and long lies were strongly associated with serious injury, hospital admission and moves into long-term care - [Fleming and Brayne 2008, BMJ](https://www.bmj.com/content/337/bmj.a2227.abstract)
- Call alarms were widely available but "were not used in most cases of falls that led to lying on the floor for a long time"; reasons included perceived irrelevance, concerns about independence and practical difficulties - [Fleming and Brayne 2008, BMJ](https://www.bmj.com/content/337/bmj.a2227.abstract)
- Difficulty getting up was associated with age, mobility and severe cognitive impairment, and cognition was the only characteristic that predicted lying on the floor for a long time - [Fleming and Brayne 2008, BMJ](https://www.bmj.com/content/337/bmj.a2227.abstract)
- Hall et al. (BMC Geriatrics, 2019) studied monitoring technology in three dementia-specialist care homes (175 hours of observation, 36 interviews) and argue for moving beyond the "safety versus autonomy" framing, including attention to effects on staff and to cost and access - [Hall et al. 2019, PMC6534927](https://pmc.ncbi.nlm.nih.gov/articles/PMC6534927)
- A literature overview of surveillance technology in residential care for people with dementia or intellectual disabilities (Niemeijer et al., International Psychogeriatrics) found no consensus on its ethical viability - [Niemeijer et al., International Psychogeriatrics](https://core-prod.cambridgecore.org/core/journals/international-psychogeriatrics/article/ethical-and-practical-concerns-of-surveillance-technologies-in-residential-care-for-people-with-dementia-or-intellectual-disabilities-an-overview-of-the-literature/1B88C75F3CA757988C4263EF966AF59A)
- Alarm fatigue on the responder side is documented anecdotally: dispatchers warned that Crash Detection false calls risked desensitizing them (2023), and care operators report about 80% of nurse-call callouts are false (vendor blog, 2021, anecdotal) - [KTVU / FOX, 2023](https://www.ktvu.com/news/apple-crash-detection-software-triggers-fake-911-calls-first-responders-say); [Vayyar blog 2021](https://vayyar.com/blog/elderly-care/alert-fatigue/)
- Apple's design assumes the user can respond (tap "I'm OK", tap Cancel, or tell the dispatcher it was an accident) - [Apple Support 108896](https://support.apple.com/en-us/108896)

### Inferences
- A person with dementia may say "I'm fine" after a real fall (anosognosia, wish to avoid fuss) or may not understand the question, so "are you OK? -> yes" should lower urgency, not cancel the family notification entirely. A soft notice ("possible fall at 3:12 pm in the kitchen; she said she was OK") keeps the family informed without false 911 calls.
- Conversely, a false 911 dispatch can frighten and disorient a person with dementia (strangers, sirens, possible transport), so the cost of a false positive is higher for this user than for an average Apple Watch wearer.
- Consent: monitoring and escalation rules should be set up with the family (and the person, while they can take part), written down, and shown on the dashboard. The project already avoids storing full frames; the safety features should follow the same rule.
- Sending the family a full-frame snapshot of a fall would conflict with the repo's hard rule "Never store a full frame" (an MMS or push image is stored on the recipient's phone). Options: send text only (room and landmark from the database), send the existing private item crop via a short-lived signed URL, or record an explicit decision in `docs/DECISIONS.md` before sending any image.
- Do not market this as replacing a medical alert service or as a medical device; frame it as "tells the family sooner".

### Gaps
- No study found on how well people with moderate dementia can cancel or confirm automated fall alerts.
- No US-specific guidance found on capacity and consent for home monitoring of people with dementia; the Alzheimer's Association has guidance on wandering (section 7) but I did not find a position statement on fall-detection monitoring.

## 6. Voice-based distress signals during a call ("help", "I fell", "I can't get up", silence, confusion)

### Takeaway
Research on detecting spoken distress in older adults exists (keyword spotting, keyword plus vocal stress, fine-tuned speech models), but I found no field-trial accuracy figures for older adults at home, and none for people with dementia.
The strongest industry precedent is explicit voice triggers ("Alexa, call for help") routed to a human agent, which suggests that Save It's agent should treat clear distress phrases as a trigger for confirmation and family notification, not as an automatic 911 call.

### Cited Findings
- A Duke Kunshan University paper (ICMI ASMMC workshop, 2021) fires an alert only when a call-for-help keyword and paralinguistic distress (shouting, screaming) occur together, and argues keywords alone miss many real emergencies because emergency speech often has no trigger word - [Duke Kunshan, ICMI ASMMC 2021](https://sites.duke.edu/dkusmiip/files/2023/03/ICMI_ASMMC21_paper_1.pdf)
- An ICCS 2025 paper runs wake-word detection, speech-to-text and intent recognition with tiny models on edge devices for seniors living alone, and tests keyword detection under noise - [ICCS 2025](https://www.iccs-meeting.org/archive/iccs2025/papers/159120016.pdf)
- A 2025 arXiv paper fine-tunes Whisper to classify utterances such as "help me" as emergencies, aiming past fixed keyword lists - [arXiv 2501.11631](https://web3.arxiv.org/pdf/2501.11631)
- An ICCS 2021 paper compares cloud speech and language-understanding services for detecting help requests from a person wearing an IoT pendant - [ICCS 2021](https://www.iccs-meeting.org/archive/iccs2021/papers/127450459.pdf)
- A 2024 arXiv preprint classifies emergencies from dementia caregivers' speech (not the patient's) - [arXiv 2412.16341](https://arxiv.org/html/2412.16341v1)
- Amazon's voice emergency feature requires an explicit phrase ("Alexa, call for help") and routes to Urgent Response agents, not 911 - [Amazon, Alexa Emergency Assist](https://aboutamazon.com/news/devices/alexa-emergency-assist)

### Inferences
- In Save It, Gemini Live already understands the conversation, so the cheapest detector is a function tool (for example `report_concern(kind, quote)`) that the agent calls when the person says they fell, are hurt, cannot get up, smell smoke, or asks for help. That needs a prompt and one backend endpoint, not a new model.
- Silence is a weak signal on a FaceTime call (the person may have walked off or put the phone down), but "the person said they fell, then stopped answering for 30 seconds" is a strong one and is worth escalating to family immediately.
- Confusion and agitation are normal in dementia and would cause constant false alerts; log them for the family dashboard (trend over days) rather than alerting.
- Test the tool with scripted phrases and with near-misses ("I almost fell yesterday", "my glasses fell") to keep false alerts down; report the results honestly in the Devpost entry.

### Gaps
- No accuracy figures found for LLM-based (Gemini Live or similar) distress detection in real conversations.
- No evidence on how dementia-related speech changes affect keyword or intent detection.
- Full-text accuracy numbers of the cited papers were not extracted.

## 7. Other low-cost safety features that fit a FaceTime agent plus lanyard camera

### Takeaway
Several safety features reuse what Save It already has (room and landmark perception on the write path, the database, the voice agent, the family dashboard) and carry less risk than auto-911: night-time exit alerts, "did I take my pills?" answers, a scam guard in the agent, "no check-in today" alerts, and pointing families to Apple's free Fall Detection, Find My and Check In.
The evidence base is strongest for wandering (6 in 10 people with dementia wander) and scams (adults 60+ reported $7.7 billion in losses to the FBI for 2025).

### Cited Findings
- "Six in 10 people living with dementia will wander at least once; many do so repeatedly", and many are found within 1.5 miles of where they disappeared (Alzheimer's Association) - [Alzheimer's Association, wandering](https://www.alz.org/help-support/caregiving/stages-behaviors/wandering)
- Warning signs include trying to "go home" while at home, talking about old duties like going to work, pacing and restlessness; wandering is often most likely in the early evening for people who experience sundowning - [Alzheimer's Association, wandering](https://www.alz.org/help-support/caregiving/stages-behaviors/wandering)
- The Association recommends door-open monitors or warning bells, pressure-sensitive mats at the door or bedside, GPS devices and enrolling in a wandering response service; if the person is not found within 15 minutes, call 911 and say the person has dementia - [Alzheimer's Association, wandering](https://www.alz.org/help-support/caregiving/stages-behaviors/wandering)
- Early-stage options include daily check-ins and reviewing the day's plans together - [Alzheimer's Association, wandering](https://www.alz.org/help-support/caregiving/stages-behaviors/wandering)
- FBI IC3 2025 annual report (published April 2026): adults 60+ filed 201,266 complaints with about $7.7 billion in reported losses, about 59-60% more than 2024; investment fraud was the largest category for this group at $3.52 billion, and complaints referencing AI exceeded $352 million in losses - [AARP, 2026](https://www.aarp.org/money/scams-fraud/fbi-ftc-report-2025-losses.html); [HousingWire, 2026](https://www.housingwire.com/articles/fbi-seniors-cybercrime-2025/); [Bitdefender, 2026](https://www.bitdefender.com/en-us/blog/hotforsecurity/older-adults-lost-billions-to-scammers-2026)
- One secondary source reported a conflicting $5.1 billion and 24% increase for 2025; I treat it as unreliable since three others agree on $7.7 billion - [SeniorDaily](https://seniordaily-news.pages.dev/articles/elder-fraud-losses-fbi-report-2026)
- For comparison, the IC3 2024 report put losses for 60+ at about $4.8-4.9 billion from 147,127 complaints - [InvestmentNews, 2025](https://www.investmentnews.com/industry-news/elder-fraud-complaints-surge-past-48-billion-as-investment-scams-lead-losses/260273)
- iPhone Check In (iOS 17 and later, in Messages) notifies a chosen contact when the user arrives, or if the iPhone stops moving for an extended period or does not reach the destination, sharing location, battery and signal depending on settings - [Tom's Guide](https://www.tomsguide.com/news/ios-17-check-in-explained-heres-how-the-new-safety-feature-works); [TidBITS, Oct 2023](https://tidbits.com/2023/10/09/ios-17s-check-in-feature-provides-peace-of-mind-and-could-even-save-lives/)
- Apple Watch Fall Detection is on by default for users who give an age of 55 or older - [Apple Support 108896](https://support.apple.com/en-us/108896)

### Inferences
Ratings below are my estimates for this repo (FastAPI worker with landmarks and rooms already in perception, Supabase, Gemini Live agent, static dashboard).
Hours assume one developer who knows the codebase; "risk" means harm from false alerts, misses or privacy.

| Feature | How it fits Save It | Build effort | Impact | Main risk |
|---|---|---|---|---|
| Caregiver-first fall escalation (core) | Trigger -> agent or capture page asks "are you OK?" -> SMS or push to family with room and landmark from the database -> family decides on 911 | 3-5 h | High | Missed falls if the phone is not worn; image privacy (see section 5) |
| Spoken distress tool in the FaceTime agent | Gemini function tool `report_concern` on "I fell", "help", "I can't get up", "I smell smoke" -> same family alert | 2-3 h | High during calls only | False alerts from near-miss phrases; test with scripted sentences |
| Lanyard impact plus "camera stuck on floor or ceiling" | `devicemotion` spike on the capture page, confirmed by N consecutive frames classed as floor or ceiling or blurred | 4-6 h | Medium | Lanyard swinging and phone taken off cause false triggers; background page may stop sensor events |
| "Frames stopped" or "no check-in today" alert | Worker or a cron notices no frames for X hours in the daytime, or no call by a set time -> soft family notice | 1-2 h | Medium | Annoying if the phone is simply charging; make it a dashboard notice first |
| Night-time exit-seeking alert | A "front door" landmark in view between, say, 10 pm and 6 am -> family alert; matches the Alzheimer's Association's door-monitor advice | 2-3 h | High (6 in 10 wander) | Needs the door to be a registered landmark; never lock the person in |
| "Did I take my pills?" | Register the pill organizer as an item; answer from sightings ("you picked up your pill box at 8:10 this morning") through the existing read path | 1-2 h | Medium | Must not claim the pills were swallowed; say only what the camera saw |
| Scam guard in the agent prompt | If the person mentions gift cards, wire transfers, crypto, a grandchild in jail, the IRS, or "don't tell anyone", the agent says to hang up and that it will tell the family, and logs a family alert | 1-2 h | High ($7.7 B, 2025) | Lectures on false matches; keep it a gentle suggestion plus a family note |
| Sundowning check-in | An early-evening calming call or reminder, the time when wandering is most likely | 2-4 h if outbound calls work | Medium | Depends on whether Chert can place outbound FaceTime calls (unverified) |
| Stove left on | Stove landmark in view with flame or a pot, then the person leaves the kitchen for N minutes -> family alert | 6-10 h | Medium | Hard vision problem with many false alerts; a commercial auto-shutoff device is more reliable (not researched) |
| Apple Watch Fall Detection, Find My, Check In | Setup advice on the dashboard and in the pitch, no code | 0-1 h | High value per hour | Requires the family to buy and configure devices |
| Heat or cold check | Weather API plus a spoken reminder to drink water or dress warmly | 2 h | Low for an indoor demo | Little evidence of benefit; low priority |

- The night-time door alert and the pill question are the best fit for the demo story because they reuse the landmark and sighting machinery the team already built and need no new model calls.
- The scam guard costs almost nothing and is easy to show in the 2-minute video, and the problem is large and growing.

### Gaps
- Whether Chert supports outbound FaceTime calls (needed for check-in and sundowning calls) was not checked; see `docs/CHERT.md`.
- No outcome evidence found for any of these features in a camera-plus-voice-agent product.
- Stove auto-shutoff devices and heat-risk guidance for older adults were not researched.

## 8. Recommended safe design pattern for the hackathon demo

### Takeaway
Do not auto-dial 911: detect, ask "are you OK?", notify the family with where and when, and let the family decide to call 911; present a professional monitoring center (Noonlight-style, with human verification within 30 seconds) as the production path.
This matches what Amazon, Noonlight, PERS companies and Georgia's alarm-verification law all do, and avoids the FCC autodialer and Georgia false-alarm exposure described in section 3.

### Cited Findings
- Apple confirms with the person (about one minute of immobility plus a 30-second countdown for falls; a 10-second alert plus a 30-second countdown for crashes) before dialing - [Apple Support 108896](https://support.apple.com/en-us/108896); [Apple Support 104959](https://support.apple.com/en-us/104959)
- Even with those steps, automatic crash calls overloaded some 911 centers in 2022-2023 - [KTVU / FOX, 2023](https://www.ktvu.com/news/apple-crash-detection-software-triggers-fake-911-calls-first-responders-say)
- Noonlight's dispatchers text and call the user within 30 seconds and close resolved alarms before routing to 911 - [Noonlight Dispatch API](https://noonlight.com/products/dispatch-api)
- Alexa's Urgent Response falls back to the user's emergency contacts and asks permission to dispatch when the user cannot be reached - [Amazon help: Urgent Response FAQs](https://digprjsurvey.amazon.com/csad/help/node/ThxMPNFnsaSBNhzSah)
- Georgia requires monitoring companies to try to verify a burglar alarm with the user before calling police, but exempts panic alarms - [Justia, O.C.G.A. 35-1-9](https://law.justia.com/codes/georgia/2019/title-35/chapter-1/section-35-1-9/); [Security Systems News](https://www.securitysystemsnews.com/article/enhanced-call-verification-now-law-georgia)
- Long lies are common and harmful in the very old, and pendant alarms usually go unused in them, so passive detection plus quick human follow-up addresses a real gap - [Fleming and Brayne 2008, BMJ](https://www.bmj.com/content/337/bmj.a2227.abstract)

### Inferences
Proposed flow for the demo:

1. Triggers, any of: the FaceTime agent hears a distress phrase (function tool); the capture page sees an acceleration spike and the next frames show floor or ceiling; or the camera has been stuck on an unusual view for N seconds.
2. Confirm: during a call, the agent asks "Did you fall? Are you hurt?" in one short sentence; outside a call, the capture page plays a loud spoken prompt and shows a big "I'm OK" button. Wait about 30-60 seconds.
3. If the person says "I'm OK": log the event and send the family a soft notice ("possible fall at 3:12 pm in the kitchen, she said she was OK"). Do not cancel silently.
4. If the person says they need help, or does not answer: send the family an urgent SMS or push with the time, room and landmark from the database, a link to the dashboard, and two choices: "I'm on my way" or "I'm calling 911". The agent tells the person, calmly, "I've told Anna. She's coming." (use the family name from config).
5. The family member, not the software, decides whether to call 911; the dashboard can show the home address to read out to the dispatcher.
6. Production path (pitch only): replace or back up step 4 with a professional monitoring center API (Noonlight-style), which verifies by text and call within about 30 seconds and contacts the local 911 center with the address when needed.

Guardrails for the demo and the pitch:

- Never call real 911 in testing or on stage; use a teammate's phone as "family".
- Say "notifies the family" and "can connect to a professional monitoring center", never "calls 911 automatically" and never "detects all falls"; follow the project rule of saying "built with HIPAA-style safeguards" and never "HIPAA compliant".
- Respect the existing hard rules: no full frames stored or sent; nothing written for rooms with `capture_allowed = false`; safety logic runs on the write path, and the read path stays model-free.
- Show one honest metric in the Devpost entry (for example, scripted falls detected and false alerts during a 10-minute walk-around), since judges will know fall detection is hard.

### Gaps
- Exact SMS or push provider and its cost were not researched (the team may already have Twilio through Vapi).
- How quickly a family member typically responds to an urgent SMS, compared with a monitoring center, was not found.
- Whether judges or sponsors weight safety features was not checked against `docs/SPONSORS.md`.
