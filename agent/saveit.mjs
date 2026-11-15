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

import { fakeRankItem, fakeRecordMiss, fakeTold } from './fake-home.mjs';

const TIMEOUT_MS = 3000;

// Dropped from the caller's words before /find, which matches item names and aliases exactly: on the 14 Nov
// test call "where are my glasses" matched nothing. Keep in step with FILLER_WORDS in app/speak.py.
const FILLER = new Set(
  "where wheres where's is are my the did i put find lost please can you help me have seen your a an to look for looking it that this thing things something stuff um uh er hmm".split(' '),
);

/** "Where are my glasses?" -> "glasses". When nothing is left, the words go as given (the backend then asks). */
export function cleanPhrase(phrase) {
  const given = String(phrase ?? '').trim();
  const kept = (given.toLowerCase().match(/[a-z0-9']+/g) ?? []).filter(word => !FILLER.has(word));
  return kept.length ? kept.join(' ') : given;
}

export function createSaveIt({ backendUrl = '', appToken = '', familyName = 'June', fetchImpl = globalThis.fetch, log = defaultLog } = {}) {
  const base = backendUrl.replace(/\/+$/, '');
  const mode = base ? 'backend' : 'fake';
  // Nothing can call or message family yet (paused, Tom 14 Nov), so no sentence may promise it.
  const fallback = "I'm not sure right now.";
  const state = { item: null, suggested: null, rank: null, result: null, queryId: null, known: [] };
  let lastLookup = { item: null, at: 0 }; // one logged lookup per item per exchange, whoever names it first
  const noMorePlaces = () => ({ say: "I'm not sure where else to look right now.", suggested: null });

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

  /** No /miss yet, so nothing is recorded: offer the usual place once, unless they just looked there; then say so. */
  function nextAfterMiss() {
    const u = state.result?.usual;
    const usual = u?.landmark ? { room: u.room ?? null, landmark: u.landmark } : null;
    const checked = state.suggested;
    if (usual && !(checked?.landmark === usual.landmark && (checked?.room ?? null) === usual.room)) {
      state.suggested = usual;
      return { say: `Okay. Let's look for your ${state.item} on ${usual.landmark}.`, suggested: usual };
    }
    state.suggested = null;
    return noMorePlaces();
  }

  /** Look an item up (logs the question, sets the card) unless it was just looked up for this exchange. */
  const lookupOnce = async item => {
    if (lastLookup.item === item && Date.now() - lastLookup.at < 20000) return null;
    lastLookup = { item, at: Date.now() };
    return api.findObject(item);
  };

  const api = {
    mode,
    state,

    /** Everything Save It knows right now (GET /snapshot), loaded when a call starts, so the model can
     *  answer in one turn without a tool round trip. [] when there is no backend or it fails. */
    loadSnapshot: async () => {
      state.known = [];
      if (mode !== 'backend') return state.known;
      const t0 = Date.now();
      try {
        const known = await http('GET', '/snapshot');
        state.known = Array.isArray(known) ? known.filter(k => k?.item && typeof k.sentence === 'string') : [];
        log({ tool: 'snapshot', mode, ms: Date.now() - t0, ok: true, items: state.known.length });
      } catch (err) {
        log({ tool: 'snapshot', mode, ms: Date.now() - t0, ok: false, error: String(err?.message ?? err) });
      }
      return state.known;
    },

    /** After each thing the caller says: when it names a known item, look it up in the background. That logs
     *  the question, points the card and sets the item for "not there"; the model answers from the snapshot. */
    noteHeard: async text => {
      const item = matchKnown(state.known, text);
      // Only a word that names exactly one item. Follow-ups ("the blue one") and unknown things are not looked
      // up here: on the test call they logged junk questions and blanked the card right after the answer.
      return item ? lookupOnce(item) : null;
    },

    /** After each reply: when it names exactly one known item, follow it (card, log, "not there"). This is how
     *  the card catches up after "The blue one or the green one?" "The blue one." */
    noteSaid: async text => {
      // Statements only: "Which one? Your green bag or the brown one?" is a question, not an answer, and the card
      // must not follow it (on the test call it looked up the green bag while asking which bag).
      const statements = String(text ?? '').split(/(?<=[.!?])\s+/).filter(s => !s.trim().endsWith('?')).join(' ');
      const item = matchKnown(state.known, statements);
      return item ? lookupOnce(item) : null;
    },

    /** find_object: where is it? Returns { say, suggested }. */
    findObject: phrase => timed('find_object', async () => {
      if (mode === 'backend') return rememberFind(await http('GET', `/find?item=${encodeURIComponent(cleanPhrase(phrase))}&channel=facetime`));
      const rank = fakeRankItem(phrase);
      const out = speakStub(rank, familyName);
      remember(rank.state === 'unknown_item' ? null : rank, out.suggested);
      if (rank.state === 'unknown_item') state.suggested = null;
      return out;
    }),

    /** report_not_there: the suggested place was empty. Records the miss and gives the next place.
     *  `thing` (optional) names the item, for when the model answered from the snapshot. */
    reportNotThere: thing => timed('report_not_there', async () => {
      const named = thing ? matchKnown(state.known, thing) ?? cleanPhrase(thing) : null;
      if (named && named !== state.item) await api.findObject(named);
      if (!state.item) return { say: 'Which thing are you looking for?', suggested: null };
      if (!state.suggested) return noMorePlaces();
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
      if (!t.item) return { say: 'Okay, thank you for telling me.', suggested: null };
      const item = `your ${t.item}`;
      if (!t.landmark) return { say: `Okay. I'll remember ${item}.`, suggested: null };
      const verb = kind === 'found' ? "I'm glad you found" : 'Thank you. I will remember';
      return { say: `${verb} ${item}. ${cap(item)} ${t.plural ? 'are' : 'is'} on ${t.landmark.landmark}.`, suggested: t.landmark };
    }),
  };
  return api;
}

/** Every mention of a known name or alias in the words, as whole words, with where it sits. */
function mentions(known, text) {
  const words = ` ${String(text ?? '').toLowerCase().replace(/[^a-z0-9' ]+/g, ' ').replace(/\s+/g, ' ').trim()} `;
  // A kind word shared by several items ("cup" for a big and a small cup) fits all of them, even without aliases.
  const kinds = new Map();
  for (const k of known ?? []) if (k.kind) kinds.set(String(k.kind).toLowerCase(), (kinds.get(String(k.kind).toLowerCase()) ?? 0) + 1);
  const found = [];
  for (const k of known ?? []) {
    const kind = k.kind && kinds.get(String(k.kind).toLowerCase()) > 1 ? [k.kind] : [];
    for (const name of [k.item, ...(k.aliases ?? []), ...kind].map(n => String(n).toLowerCase()).filter(Boolean)) {
      for (let at = words.indexOf(` ${name} `); at !== -1; at = words.indexOf(` ${name} `, at + 1)) {
        found.push({ item: k.item, start: at + 1, end: at + 1 + name.length });
      }
    }
  }
  return found;
}

/**
 * The one known item the words name, or null. A mention inside a longer one is part of it ("bag" in "brown bag"),
 * so "brown bag" is the brown bag. A bare kind word with several items of that kind ("cup") fits all of them.
 * Null when nothing matches, when a word fits two items ("bag" with two bags:
 * the model asks which one), or when the words name two items apart ("the green bag or the brown handbag?":
 * the card must not jump while the question is being asked).
 */
export function matchKnown(known, text) {
  const all = mentions(known, text);
  const outer = all.filter(m => !all.some(o => o.start <= m.start && o.end >= m.end && o.end - o.start > m.end - m.start));
  const items = new Set(outer.map(m => m.item));
  return items.size === 1 ? [...items][0] : null;
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
  if (!rank || rank.state === 'unknown_item') return { say: "I don't know that one yet. Your family can teach me.", suggested: null };
  const item = `your ${rank.item}`;
  const be = rank.plural ? 'are' : 'is';
  const [p1, p2] = rank.places;
  if (!p1) return { say: `I'm not sure where ${item} ${be} right now.`, suggested: null };
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

/** After a miss: the next place to check, or that there is nowhere else. */
export function nextPlaceStub(rank, family = 'June') {
  const item = `your ${rank.item}`;
  const next = rank.search_order?.[0];
  if (!next) return { say: "I'm not sure where else to look right now.", suggested: null };
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
