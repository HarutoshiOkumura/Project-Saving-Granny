// The agent's read side: what the FaceTime tools call. One instance per call (it keeps per-call state:
// the last item and the place we suggested, so the model never has to echo ids; docs/CHERT.md).
//
// BACKEND_URL set   -> HTTP to our backend (contract below; step 02 builds it).
// BACKEND_URL empty -> fake-home.mjs, so the call works before the database layer exists.
//
// Backend contract (proposed; docs/CHERT.md "Agent <-> backend"):
//   GET  /find?item=<words>                          -> { say, rank, suggested? }
//   POST /miss  { item, landmark_id }                -> { say, rank, suggested? }   record_miss, then re-rank
//   POST /told  { object_phrase, place_phrase, kind } -> { say }                      log_sighting told + facetime_caller
//   GET  /facts?q=<question>                         -> { say }                      Typesense facts, patient-visible
//   POST /alert { reason }                           -> { say? }                     dashboard alert
// `rank` is rank_item's JSON. `suggested` is { landmark_id, room, landmark }: the place `say` told them to check.
// Requests send `Authorization: Bearer $APP_TOKEN` when APP_TOKEN is set.

import { fakeFact, fakeRankItem, fakeRecordMiss, fakeTold } from './fake-home.mjs';

const TIMEOUT_MS = 3000;

export function createSaveIt({ backendUrl = '', appToken = '', familyName = 'June', fetchImpl = globalThis.fetch, log = defaultLog } = {}) {
  const base = backendUrl.replace(/\/+$/, '');
  const mode = base ? 'backend' : 'fake';
  const fallback = `I'm not sure. Let me check with ${familyName}.`;
  const state = { item: null, suggested: null, rank: null };

  async function http(method, path, body) {
    const headers = { Accept: 'application/json' };
    if (body) headers['Content-Type'] = 'application/json';
    if (appToken) headers.Authorization = `Bearer ${appToken}`;
    const res = await fetchImpl(base + path, { method, headers, body: body ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(TIMEOUT_MS) });
    if (!res.ok) throw new Error(`HTTP ${res.status} from ${path}`);
    return res.json();
  }

  async function timed(tool, fn) {
    const t0 = Date.now();
    try {
      const out = await fn();
      log({ tool, mode, ms: Date.now() - t0, ok: true, item: state.item, place: state.suggested?.landmark_id ?? null });
      return out;
    } catch (err) {
      log({ tool, mode, ms: Date.now() - t0, ok: false, error: String(err?.message ?? err) });
      return { say: fallback, suggested: null };
    }
  }

  function remember(rank, suggested) {
    state.rank = rank;
    state.item = rank?.item ?? null;
    state.suggested = suggested ?? rank?.search_order?.[0] ?? null;
  }

  return {
    mode,
    state,

    /** find_object: where is it? Returns { say, suggested }. */
    findObject: phrase => timed('find_object', async () => {
      if (mode === 'backend') {
        const r = await http('GET', `/find?item=${encodeURIComponent(phrase)}`);
        remember(r.rank, r.suggested);
        return { say: r.say, suggested: state.suggested };
      }
      const rank = fakeRankItem(phrase);
      const out = speakStub(rank, familyName);
      remember(rank.state === 'unknown_item' ? null : rank, out.suggested);
      if (rank.state === 'unknown_item') state.suggested = null;
      return out;
    }),

    /** report_not_there: the suggested place was empty. Records the miss and gives the next place. */
    reportNotThere: () => timed('report_not_there', async () => {
      if (!state.item || !state.suggested) return { say: 'Which thing are you looking for?', suggested: null };
      if (mode === 'backend') {
        const r = await http('POST', '/miss', { item: state.item, landmark_id: state.suggested.landmark_id });
        remember(r.rank, r.suggested);
        return { say: r.say, suggested: state.suggested };
      }
      fakeRecordMiss(state.item, state.suggested.landmark_id);
      const rank = fakeRankItem(state.item);
      const out = nextPlaceStub(rank, familyName);
      remember(rank, out.suggested);
      if (!out.suggested) state.suggested = null;
      return out;
    }),

    /** record_placement: "I put my keys in the drawer" (placed) or "found them on the shelf" (found). */
    recordPlacement: (objectPhrase, placePhrase, kind) => timed('record_placement', async () => {
      if (mode === 'backend') {
        const r = await http('POST', '/told', { object_phrase: objectPhrase, place_phrase: placePhrase, kind });
        return { say: r.say, suggested: null };
      }
      const t = fakeTold(objectPhrase, placePhrase);
      if (!t.item) return { say: "Okay. I'll tell your family about that.", suggested: null };
      const item = `your ${t.item}`;
      if (!t.landmark) return { say: `Okay. I'll remember ${item}.`, suggested: null };
      const verb = kind === 'found' ? "I'm glad you found" : 'Thank you. I will remember';
      return { say: `${verb} ${item}. ${cap(item)} ${t.plural ? 'are' : 'is'} on ${t.landmark.landmark}.`, suggested: t.landmark };
    }),

    /** recall_life_fact: "Who is June?" */
    recallLifeFact: question => timed('recall_life_fact', async () => {
      if (mode === 'backend') {
        const r = await http('GET', `/facts?q=${encodeURIComponent(question)}`);
        return { say: r.say || fallback, suggested: null };
      }
      return { say: fakeFact(question) ?? `I'm not sure. Let's ask ${familyName}.`, suggested: null };
    }),

    /** alert_caregiver: the person is upset, hurt or asks for family. */
    alertCaregiver: reason => timed('alert_caregiver', async () => {
      if (mode === 'backend') {
        const r = await http('POST', '/alert', { reason });
        return { say: r.say || `I've let ${familyName} know.`, suggested: null };
      }
      log({ tool: 'alert_caregiver', mode, alert: String(reason).slice(0, 120) });
      return { say: `I've sent ${familyName} a message. ${familyName} will call you soon.`, suggested: null };
    }),
  };
}

// --- speak() stand-in for fake mode. The real speak() is app/speak.py (docs/RETRIEVAL.md); keep these in step. ---

/** rank_item JSON -> { say, suggested }. Voice rules: <=2 sentences, <=12 words each, repeat the item name. */
export function speakStub(rank, family = 'June') {
  if (!rank || rank.state === 'unknown_item') return { say: "I don't know that one yet. I'll ask your family to add it.", suggested: null };
  const item = `your ${rank.item}`;
  const be = rank.plural ? 'are' : 'is';
  const [p1, p2] = rank.places;
  if (!p1) return { say: `I'm not sure where ${item} ${be}. Shall I ask ${family} to help?`, suggested: null };
  if (rank.find?.state === 'carried') {
    const first = rank.search_order[0] ?? p1;
    return { say: `You had ${item} in ${rank.find.room}. Try ${first.landmark} first.`, suggested: first };
  }
  if (p1.why === 'camera' && p2?.why === 'you_said') {
    return { say: `You said ${p2.landmark}. But I saw ${item} on ${p1.landmark}.`, suggested: p1 };
  }
  if (rank.band === 'high') {
    if (p1.why === 'usual') return { say: `I haven't seen ${item} today. ${cap(item)} ${be} usually on ${p1.landmark}.`, suggested: p1 };
    const seen = p1.why === 'camera' && p1.minutes_ago != null ? ` I saw ${rank.plural ? 'them' : 'it'} there ${ago(p1.minutes_ago)}.` : '';
    return { say: `${cap(item)} ${be} on ${p1.landmark}.${seen}`, suggested: p1 };
  }
  if (rank.band === 'split' && p2) {
    return { say: `${cap(item)} ${be} probably on ${p1.landmark}. If not, ${p2.landmark}.`, suggested: p1 };
  }
  const first = rank.search_order[0] ?? p1;
  return { say: `I'm not sure about ${item}. Let's check ${first.landmark} first.`, suggested: first };
}

/** After a miss: the next place to check, or offer family. */
export function nextPlaceStub(rank, family = 'June') {
  const item = `your ${rank.item}`;
  const next = rank.search_order?.[0];
  if (!next) return { say: `I'm not sure where else to look. Shall I ask ${family} to help?`, suggested: null };
  return { say: `Okay. Let's look for ${item} on ${next.landmark}.`, suggested: next };
}

/** Relative time, never a clock time (CLAUDE.md conventions). */
export function ago(minutes) {
  if (minutes < 3) return 'just now';
  if (minutes < 15) return 'a few minutes ago';
  if (minutes < 50) return `about ${Math.round(minutes / 10) * 10} minutes ago`;
  if (minutes < 90) return 'about an hour ago';
  if (minutes < 720) return `about ${Math.round(minutes / 60)} hours ago`;
  return 'earlier today';
}

const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
const defaultLog = entry => console.log(`[save-it] ${JSON.stringify(entry)}`);
