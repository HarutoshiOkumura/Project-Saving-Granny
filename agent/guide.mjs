// Guided directions for one call: while the caller walks, poll GET /guide (app/guide.py) and speak up when
// they get closer. The backend compares where the worn camera last saw them with where the thing was last
// seen; it calls no vision model, so a poll costs two database reads.
//
// Per-call state lives here, not in the model and not in the backend. That state is what keeps the voice calm:
//   - closer (the step's `progress` rises) is said at once;
//   - a step that is no closer (they turned away, or walked out again) is said only after it has held for
//     `settlePolls` polls, so one odd frame never makes Find It take a direction back;
//   - at least `minGapMs` between directions, at most `maxSays` of them, and `maxMs` of guiding in all;
//   - nothing is said while the caller or Find It is talking (announce() returns false, and it is retried).
// Guiding ends by itself when the backend says there is nothing more to guide (`done`: the thing is in their
// hand, or it is not there anymore), when the caller moves on to another thing or reports "not there", and
// when the call ends.
//
// Voice only. The card keeps showing the place the answer named; this module never draws.

import { cleanPhrase, matchKnown } from './saveit.mjs';

const TIMEOUT_MS = 3000;
const NOT_SURE = "I'm not sure right now.";

/** The guide_to_thing tool's description: when the model should start guiding. */
export const GUIDE_TOOL =
  'Guide them to the thing while they walk. Call it when they ask for help getting to it ("show me the way", "help me get there", "where do I go") ' +
  'or say yes to you staying on the line while they look. Returns the first direction to say. More directions will reach you as they walk.';

/** What the model is told when a new direction arrives mid-call. Places stay exactly as given (voice rules). */
export const sayGuidance = sentence =>
  `They are walking to find the thing. Tell them this now, gently, in one short sentence. Keep the place and the thing exactly as written, and add nothing else: "${sentence}"`;

/**
 * @param {object} options
 * @param {{ state: { item: string | null, suggested: { room?: string | null, landmark?: string | null } | null, known: unknown[] }, findObject(phrase: string): Promise<unknown> }} options.saveIt
 *   the call's read side (saveit.mjs): which thing the caller is on, and the lookup that points the card.
 * @param {(guidance: { sentence: string, step: string }) => boolean} options.announce
 *   say one direction; false when nobody may be spoken over right now (it is tried again on the next poll).
 * @param {(found: unknown) => void} [options.onLookup] called with a lookup's reply, so the card can follow.
 */
export function createGuide({
  saveIt,
  announce,
  onLookup = () => {},
  backendUrl = '',
  appToken = '',
  fetchImpl = globalThis.fetch,
  log = () => {},
  intervalMs = 2000,
  minGapMs = 5000,
  settlePolls = 3,
  maxSays = 8,
  maxMs = 180000,
  now = Date.now,
  setTimer = setInterval,
  clearTimer = clearInterval,
} = {}) {
  const base = backendUrl.replace(/\/+$/, '');
  let run = null; // { item, key, progress, saidAt, says, startedAt, about, pending, timer }
  let busy = false;

  async function fetchStep(item) {
    const headers = { Accept: 'application/json' };
    if (appToken) headers.Authorization = `Bearer ${appToken}`;
    const res = await fetchImpl(`${base}/guide?item=${encodeURIComponent(item)}`, { headers, signal: AbortSignal.timeout(TIMEOUT_MS) });
    if (!res.ok) throw new Error(`HTTP ${res.status} from /guide`);
    const g = await res.json();
    if (typeof g?.sentence !== 'string' || !g.sentence || typeof g.key !== 'string') throw new Error('no step in the /guide reply');
    return g;
  }

  /** What the caller is on right now: the thing, and the place the card shows for it. */
  const about = () => `${saveIt.state.item ?? ''}|${saveIt.state.suggested?.room ?? ''}|${saveIt.state.suggested?.landmark ?? ''}`;

  function stop(reason) {
    if (!run) return;
    clearTimer(run.timer);
    log({ tool: 'guide', event: 'stop', reason, item: run.item, says: run.says, ms: now() - run.startedAt });
    run = null;
  }

  /** One poll. Exported for tests; the timer calls it. */
  async function tick() {
    if (!run || busy) return;
    const mine = run;
    if (now() - mine.startedAt > maxMs) return stop('timeout');
    // Another thing, or "not there" moved the card to the next place: they are no longer walking to this one.
    if (about() !== mine.about) return stop('moved_on');
    busy = true;
    let g;
    try {
      g = await fetchStep(mine.item);
    } catch (err) {
      log({ tool: 'guide', event: 'poll', ok: false, error: String(err?.message ?? err) });
      return;
    } finally {
      busy = false;
    }
    if (run !== mine || g.step === 'unsure') return;
    if (g.key === mine.key) {
      mine.pending = null;
      return;
    }
    const closer = g.done || g.progress > mine.progress;
    if (!closer) {
      mine.pending = mine.pending?.key === g.key ? { key: g.key, polls: mine.pending.polls + 1 } : { key: g.key, polls: 1 };
      if (mine.pending.polls < settlePolls) return;
    }
    if (now() - mine.saidAt < minGapMs) return;
    let said = false;
    try {
      said = announce(g) === true;
    } catch (err) {
      log({ tool: 'guide', event: 'say', ok: false, error: String(err?.message ?? err) });
    }
    if (!said) return; // someone is talking, or the call is ending: the same step is tried on the next poll
    Object.assign(mine, { key: g.key, progress: g.progress, saidAt: now(), says: mine.says + 1, pending: null });
    log({ tool: 'guide', event: 'say', ok: true, step: g.step, progress: g.progress, view_age_s: g.view_age_s ?? null });
    if (g.done) stop('done');
    else if (mine.says >= maxSays) stop('enough_said');
  }

  return {
    tick,
    stop,
    get active() {
      return run !== null;
    },
    get item() {
      return run?.item ?? null;
    },

    /**
     * The guide_to_thing tool: the first direction to say, and the polling starts. `thing` (optional) names the
     * item when it is not the one the caller was just on; it is then looked up first, so the card follows.
     */
    async begin(thing) {
      stop('restart');
      try {
        const named = thing ? matchKnown(saveIt.state.known, thing) ?? cleanPhrase(thing) : null;
        if (named && named !== saveIt.state.item) onLookup(await saveIt.findObject(named));
        const item = saveIt.state.item;
        if (!item) return 'Which thing are you looking for?';
        const g = await fetchStep(item);
        if (g.step === 'unsure') return g.sentence;
        log({ tool: 'guide', event: 'start', item, step: g.step, guiding: !g.done, view_age_s: g.view_age_s ?? null });
        if (!g.done) {
          run = { item, key: g.key, progress: g.progress, saidAt: now(), says: 1, startedAt: now(), about: about(), pending: null, timer: null };
          run.timer = setTimer(() => { tick().catch(() => {}); }, intervalMs);
        }
        return g.sentence;
      } catch (err) {
        log({ tool: 'guide', event: 'start', ok: false, error: String(err?.message ?? err) });
        return NOT_SURE;
      }
    },
  };
}
