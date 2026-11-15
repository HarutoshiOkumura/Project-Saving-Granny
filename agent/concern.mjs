// report_concern: the caller fell, is hurt, needs help, smells smoke, is lost outside, or someone wants money
// from them. The agent asks once ("Are you hurt?"), reports, and the family decides what happens next
// (docs/INSIGHTS.md design 3). Nothing here calls 911, and no sentence claims to have told anyone: nothing can
// reach family yet (.claude/rules/voice.md).
//
// Backend: POST /concerns { kind, answer, channel: 'facetime' } -> 201 { id, urgency, room }, with
// `Authorization: Bearer $APP_TOKEN` when APP_TOKEN is set. Any failure is logged and swallowed: what the agent
// says never depends on the backend. BACKEND_URL empty -> nothing is sent (fake mode).

export const CONCERN_KINDS = ['fall', 'hurt', 'help', 'smoke', 'scam', 'lost_outside'];
export const CONCERN_ANSWERS = ['hurt', 'ok', 'no_answer'];

const TIMEOUT_MS = 3000;

/** What the agent says after reporting. Same wording as the "Safety" section of .claude/rules/voice.md. */
export const SAFETY_SAY = {
  hurt: "I'm here with you. If you're hurt, call 911 or ask someone nearby.",
  fallOk: "I'm glad you're okay. Take your time getting up.",
  ok: "I'm glad you're okay. I'm right here with you.",
  smoke: 'Please move away from the smoke. Call 911 if you see fire.',
  scam: "That sounds like a trick some people try. Please don't send any money, and it's fine to hang up.",
};

/** The sentence for one report. Smoke and money never wait for "are you hurt?". */
export function safetySay(kind, answer) {
  if (kind === 'scam') return SAFETY_SAY.scam;
  if (kind === 'smoke') return SAFETY_SAY.smoke;
  if (answer === 'ok') return kind === 'fall' ? SAFETY_SAY.fallOk : SAFETY_SAY.ok;
  return SAFETY_SAY.hurt; // hurt, no answer, or not asked: assume the worst, kindly
}

export function createConcernReporter({ backendUrl = '', appToken = '', fetchImpl = globalThis.fetch, log = () => {} } = {}) {
  const base = backendUrl.replace(/\/+$/, '');
  const mode = base ? 'backend' : 'fake';

  /** Returns { say, urgency }; urgency is the backend's ("urgent", "check_in", "note") or null when not sent. */
  async function report(kind, answer) {
    const k = CONCERN_KINDS.includes(kind) ? kind : 'help';
    const a = CONCERN_ANSWERS.includes(answer) ? answer : null;
    const say = safetySay(k, a);
    const t0 = Date.now();
    if (mode === 'fake') {
      log({ tool: 'report_concern', mode, kind: k, answer: a, ms: 0, ok: true, sent: false });
      return { say, urgency: null };
    }
    try {
      const headers = { Accept: 'application/json', 'Content-Type': 'application/json' };
      if (appToken) headers.Authorization = `Bearer ${appToken}`;
      const res = await fetchImpl(`${base}/concerns`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ kind: k, answer: a, channel: 'facetime' }),
        signal: AbortSignal.timeout(TIMEOUT_MS),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status} from /concerns`);
      const body = await res.json();
      log({ tool: 'report_concern', mode, kind: k, answer: a, ms: Date.now() - t0, ok: true, id: body?.id ?? null, urgency: body?.urgency ?? null });
      return { say, urgency: body?.urgency ?? null };
    } catch (err) {
      log({ tool: 'report_concern', mode, kind: k, answer: a, ms: Date.now() - t0, ok: false, error: String(err?.message ?? err) });
      return { say, urgency: null };
    }
  }

  return { mode, report };
}
