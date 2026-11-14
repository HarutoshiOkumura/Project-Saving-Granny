// The agent's read side: what the FaceTime tools call. One instance per call (it keeps per-call state:
// the last item and the place we suggested, so the model never has to echo ids; docs/CHERT.md).
//
// BACKEND_URL set   -> HTTP to our backend (app/main.py).
// BACKEND_URL empty -> fake-home.mjs, so the call works without the backend.
//
// Backend (docs/CHERT.md "Agent <-> backend"):
//   GET  /find?item=<words>&channel=facetime          -> { sentence, result }     step 02 (built): ask_item -> speak()
//        Once /find ranks (rank_item, 0003) it may answer { say, rank, suggested? }; both shapes are read.
//   POST /miss  { item, landmark_id }                -> { say, rank, suggested? }   record_miss, then re-rank (not built)
//   POST /told  { object_phrase, place_phrase, kind } -> { say }                      log_sighting told + facetime_caller (not built)
//   GET  /facts?q=<question>                         -> { say }                      Typesense facts, patient-visible (not built)
//   POST /alert { reason }                           -> { say? }                     dashboard alert (not built)
// While an endpoint is missing (404), its tool answers without it and never claims to have saved anything.
// `result` is find_item's JSON (FindResult in app/memory/schema.py); `rank` is rank_item's JSON.
// `suggested` is { room, landmark, landmark_id? }: the place the card shows. The answer is read verbatim.
// Requests send `Authorization: Bearer $APP_TOKEN` when APP_TOKEN is set.

import { fakeFact, fakeRankItem, fakeRecordMiss, fakeTold } from './fake-home.mjs';

const TIMEOUT_MS = 3000;

export function createSaveIt({ backendUrl = '', appToken = '', familyName = 'June', fetchImpl = globalThis.fetch, log = defaultLog } = {}) {
  const base = backendUrl.replace(/\/+$/, '');
  const mode = base ? 'backend' : 'fake';
  const fallback = `I'm not sure. Let me check with ${familyName}.`;
  const state = { item: null, suggested: null, rank: null, result: null, queryId: null };
  const offerFamily = () => ({ say: `I'm not sure where else to look. Shall I ask ${familyName} to help?`, suggested: null });

  async function http(method, path, body) {
    const headers = { Accept: 'application/json' };
    if (body) headers['Content-Type'] = 'application/json';
    if (appToken) headers.Authorization = `Bearer ${appToken}`;
    const res = await fetchImpl(base + path, { method, headers, body: body ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(TIMEOUT_MS) });
    if (!res.ok) throw Object.assign(new Error(`HTTP ${res.status} from ${path}`), { status: res.status });
    return res.json();
  }

  async function timed(tool, fn) {
    const t0 = Date.now();
    try {
      const out = await fn();
      log({ tool, mode, ms: Date.now() - t0, ok: true, item: state.item, place: state.suggested?.landmark_id ?? state.suggested?.landmark ?? null, query: state.queryId });
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

  /** A /find reply: step 02's { sentence, result }, or the ranked { say, rank, suggested? }. */
  function rememberFind(r) {
    const say = r?.say ?? r?.sentence;
    if (typeof say !== 'string' || !say) throw new Error('no sentence in the /find reply');
    if (r.rank) {
      remember(r.rank, r.suggested);
      state.result = r.rank.find ?? null;
    } else {
      state.rank = null;
      state.result = r.result ?? null;
      state.item = state.result?.item ?? null;
      state.suggested = placeOf(state.result);
    }
    state.queryId = state.result?.query_id ?? null;
    return { say, suggested: state.suggested };
  }

  /** No /miss yet, so nothing is recorded: offer the usual place once, unless they just looked there; then family. */
  function nextAfterMiss() {
    const u = state.result?.usual;
    const usual = u?.landmark ? { room: u.room ?? null, landmark: u.landmark } : null;
    const checked = state.suggested;
    if (usual && !(checked?.landmark === usual.landmark && (checked?.room ?? null) === usual.room)) {
      state.suggested = usual;
      return { say: `Okay. Let's look for your ${state.item} on ${usual.landmark}.`, suggested: usual };
    }
    state.suggested = null;
    return offerFamily();
  }

  return {
    mode,
    state,

    /** find_object: where is it? Returns { say, suggested }. */
    findObject: phrase => timed('find_object', async () => {
      if (mode === 'backend') return rememberFind(await http('GET', `/find?item=${encodeURIComponent(phrase)}&channel=facetime`));
      const rank = fakeRankItem(phrase);
      const out = speakStub(rank, familyName);
      remember(rank.state === 'unknown_item' ? null : rank, out.suggested);
      if (rank.state === 'unknown_item') state.suggested = null;
      return out;
    }),

    /** report_not_there: the suggested place was empty. Records the miss and gives the next place. */
    reportNotThere: () => timed('report_not_there', async () => {
      if (!state.item) return { say: 'Which thing are you looking for?', suggested: null };
      if (!state.suggested) return offerFamily();
      if (mode === 'backend') {
        if (state.suggested.landmark_id) {
          try {
            return rememberFind(await http('POST', '/miss', { item: state.item, landmark_id: state.suggested.landmark_id }));
          } catch (err) {
            if (!missing(err)) throw err;
          }
        }
        return nextAfterMiss();
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
        try {
          const r = await http('POST', '/told', { object_phrase: objectPhrase, place_phrase: placePhrase, kind });
          return { say: r.say, suggested: null };
        } catch (err) {
          if (!missing(err)) throw err;
          return { say: 'Okay, thank you for telling me.', suggested: null }; // no /told yet: nothing is saved, so promise nothing
        }
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

/** Where the card points for a step 02 answer: the place it names, or where to look next. */
export function placeOf(result) {
  if (!result) return null;
  const at = (room, landmark) => (room || landmark ? { room: room ?? null, landmark: landmark ?? null } : null);
  switch (result.state) {
    case 'seen':
      return at(result.room, result.landmark);
    case 'carried':
      return at(result.wearer_went_to ?? result.room, null);
    case 'not_there_anymore':
    case 'never_seen':
      return result.usual ? at(result.usual.room, result.usual.landmark) : null;
    default:
      return null;
  }
}

const missing = err => err?.status === 404 || err?.status === 405;

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
