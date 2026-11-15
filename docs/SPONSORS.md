# Sponsors, prizes, judging, and facts for the pitch

## EmoryHacks challenges (from the event packet)
- **Coder for Good:** build something that makes technology more inclusive (accessibility).
  - Criteria: Impact and Purpose; Technical Innovation; User Experience & Design; **Project Completion**.
  - 1st: Nintendo Switch 2 + Coder Education License + a $1K donation to a non-profit.
  - 2nd: Flipper + Coder Education License.
- **Best Use of Search with Typesense:** $1,500 of Typesense Cloud credit. Criteria in `docs/TYPESENSE.md`.
- **Chert: Best Use of FaceTime:** see `docs/CHERT.md`.
- **Gemini:** an MLH partner page for Gemini was in the event materials. Check Devpost for whether there is a Gemini prize.
- **Rules:**
  - Repos and teams had to be formed by 12 PM Saturday. This repo's first commit is 11:55, so keep all work here.
  - Submit on Devpost by **8:00 AM Sunday** with a 2-minute YouTube video (unlisted is fine).
  - Pick tracks in the Devpost draft.
- **General judging sheet** (from the Typesense deck): innovation and creativity; technical difficulty and implementation; practical impact; design and UX (accessibility); pitch and presentation.

## Coder
- The event's hosted deployment is `https://coder.c1.workshop.cdr.dev/`, with the "Tech Stack Builder" template.
- Workspaces have ≤ 8 cores and 8 GB, **no GPU and no USB**, so cameras stay on laptops.
- Port sharing levels are owner, organization, authenticated and public, but this deployment caps them at owner. Chert, Vapi and the phone capture page need a public HTTPS URL, so they use a Quick Tunnel (D5, `docs/CODER.md`).
- Coder Agents can run coding agents in workspaces; screenshot it (D6). AI Gateway and Agent Firewall are Premium features, and both are turned on for this deployment.
- Coder Tasks (`coder tasks create`) was removed in v2.34; tutorials that use it no longer apply.
- **Optional governance demo:** Coder's open-source `boundary` restricts an agent's network to an allowlist.
  - Install: `curl -fsSL https://raw.githubusercontent.com/coder/boundary/main/install.sh | bash`
  - Run: `boundary --log-level info --allow "domain=api.anthropic.com" --allow "domain=pypi.org" … -- claude`
  - The default nsjail backend needs sudo.
  - Denied requests are logged and sent to the workspace agent as audit logs.
  - Don't call it compliance.
- Judges look at the commit history, so commit small and often.

## Gemini (if used for Typesense NL/RAG)
- **Model IDs** (Google docs, Nov 2026):
  - `gemini-3.5-flash` (GA, stable)
  - `gemini-3.1-flash-lite` (stable, cheap)
  - `gemini-3.1-pro-preview`
  - `gemini-3-flash-preview`
  - `gemini-3.6-flash` also appears on Google's latest-model page.

  Check with `client.models.list()` before hardcoding one.
- Use a **billing-enabled key**. The free tier's terms say not to send personal information.
- `thinking_level` "minimal" is supported on 3.5 Flash and 3.1 Flash-Lite and gives the lowest latency.

## Facts for the pitch
- **MemPal** (IUI '25, Maniar et al.):
  - a chest-worn iPhone with a 235° fisheye lens, answering with what it saw last: "Your [object] was last seen at [time] in the [location] near [background]."
  - Reported: 72% accuracy with audio answers, 53% with visual, 78% room localization, 2.17 s mean response time.
  - **Ours differs in four ways:**
    - we weigh who saw it (camera > family > the person's own memory);
    - we learn from "it wasn't there";
    - we send the person to the nearest likely place first;
    - there is no wake word and no app: just FaceTime.
- **Mira** (TreeHacks 2026; AR glasses + 3D scans):
  - Lessons we adopted: voice first (touchscreens fail with low vision, tremor and cognitive impairment), big targets, slow animations, minimal patient data sent to LLMs.
  - The difference: their scans are static. Our memory updates all day and needs no glasses.
- Keep the three lines in `PLAN.md` "What to say you did not build".
- **Comparison chart:** run the same replayed walks through `find_item` (last seen) and `rank_item` (ranked). Report searches-to-find and top-1 accuracy, even on a small set (D22).
