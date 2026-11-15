// A stand-in for the backend while the database layer is being built (STATUS: step 10 "stubbed").
// It mirrors supabase/seed.example.sql (rooms, landmarks, items, aliases) and returns results in
// rank_item's shape (docs/RETRIEVAL.md), using the same band rule and search-order formula.
// State lives in this process only: misses and "I put it there" claims reset when the agent restarts.

const LANDMARKS = {
  nightstand: { landmark_id: 'lm-nightstand', room: 'your bedroom', landmark: 'the table beside your bed', kind: 'surface' },
  dresser: { landmark_id: 'lm-dresser', room: 'your bedroom', landmark: 'the dresser', kind: 'surface' },
  counter: { landmark_id: 'lm-counter', room: 'the kitchen', landmark: 'the kitchen counter', kind: 'surface' },
  table: { landmark_id: 'lm-table', room: 'the kitchen', landmark: 'the kitchen table', kind: 'surface' },
  hook: { landmark_id: 'lm-hook', room: 'the hallway', landmark: 'the hook by the front door', kind: 'fixture' },
  shelf: { landmark_id: 'lm-shelf', room: 'the hallway', landmark: 'the shelf by the front door', kind: 'surface' },
};

// docs/RETRIEVAL.md: find_chance and check_seconds by kind; walk seconds from the wearer's room.
const FIND_CHANCE = { surface: 0.9, fixture: 0.95, container: 0.6, floor: 0.7 };
const CHECK_SECONDS = { surface: 3, fixture: 2, container: 8, floor: 6 };
const LINKS = [['the hallway', 'your bedroom'], ['the hallway', 'the kitchen']];
function walkSeconds(from, to) {
  if (!from) return 15;
  if (from === to) return 6;
  return LINKS.some(([a, b]) => (a === from && b === to) || (a === to && b === from)) ? 15 : 25;
}

// w = unnormalised score; p = w / sum(w). Chosen so each item shows a different speak() case.
const ITEMS = {
  glasses: {
    plural: true, aliases: ['specs', 'spectacles', 'readers', 'reading glasses', 'eyeglasses'], wearer_room: 'the kitchen',
    places: [['nightstand', 0.5, 'camera', 40], ['table', 0.3, 'you_said', 20], ['dresser', 0.2, 'usual', null]],
  },
  keys: {
    plural: true, aliases: ['key', 'house keys', 'door keys'], wearer_room: 'the kitchen',
    places: [['hook', 0.85, 'camera', 10], ['shelf', 0.15, 'usual', null]],
  },
  phone: {
    plural: false, aliases: ['cell phone', 'cellphone', 'mobile'], wearer_room: 'your bedroom',
    places: [['counter', 0.7, 'camera', 5], ['nightstand', 0.3, 'usual', null]],
  },
  remote: {
    plural: false, aliases: ['clicker', 'tv remote', 'remote control'], wearer_room: 'the kitchen', carried_in: 'the kitchen',
    places: [['table', 0.45, 'usual', null], ['counter', 0.3, 'family_said', 90], ['nightstand', 0.25, 'usual', null]],
  },
  'pill box': {
    plural: false, aliases: ['pills', 'medication', 'pill organizer', 'pill organiser'], wearer_room: 'the kitchen',
    places: [['counter', 0.3, 'usual', null], ['table', 0.25, 'usual', null], ['dresser', 0.25, 'usual', null], ['nightstand', 0.2, 'usual', null]],
  },
  wallet: {
    plural: false, aliases: ['purse', 'billfold'], wearer_room: 'your bedroom',
    places: [['dresser', 0.7, 'usual', null], ['nightstand', 0.1, 'usual', null], ['table', 0.1, 'usual', null], ['shelf', 0.1, 'usual', null]],
  },
};

const misses = new Map(); // item -> Set of landmark keys checked and empty
const told = new Map();   // item -> landmark key the person said

const norm = s => String(s || '').toLowerCase().replace(/[^a-z ]/g, ' ').replace(/\b(my|the|a|an|where|is|are|did|i|put|leave|left)\b/g, ' ').replace(/\s+/g, ' ').trim();

/** Match spoken words to an item name, the way find_item matches names and aliases (plus a loose contains). */
export function resolveItem(phrase) {
  const q = norm(phrase);
  if (!q) return null;
  for (const [name, item] of Object.entries(ITEMS)) {
    if (q === name || item.aliases.includes(q)) return name;
  }
  for (const [name, item] of Object.entries(ITEMS)) {
    if ([name, ...item.aliases].some(a => q.includes(a) || a.includes(q))) return name;
  }
  return null;
}

/** Match spoken words to a landmark key ("by the bed" -> nightstand). */
export function resolveLandmark(phrase) {
  const q = norm(phrase);
  const hints = { nightstand: ['bed', 'nightstand', 'bedside'], dresser: ['dresser', 'drawers'], counter: ['counter'], table: ['kitchen table', 'table'], hook: ['hook'], shelf: ['shelf', 'shoe'] };
  return Object.keys(hints).find(k => hints[k].some(h => q.includes(h))) ?? null;
}

/** rank_item's result for the spoken phrase, from the fake home. */
export function fakeRankItem(phrase) {
  const name = resolveItem(phrase);
  if (!name) return { state: 'unknown_item', heard: String(phrase || '') };
  const item = ITEMS[name];
  const missed = misses.get(name) ?? new Set();
  let rows = item.places.map(([key, w, why, minutes_ago]) => ({ key, w, why, minutes_ago }));
  const saidKey = told.get(name);
  if (saidKey) {
    const row = rows.find(r => r.key === saidKey);
    if (row) Object.assign(row, { w: row.w + 0.5, why: row.why === 'camera' ? 'camera' : 'you_said', minutes_ago: 0 });
    else rows.push({ key: saidKey, w: 0.5, why: 'you_said', minutes_ago: 0 });
  }
  rows = rows.filter(r => !missed.has(r.key));
  const total = rows.reduce((s, r) => s + r.w, 0) || 1;
  const places = rows
    .map(r => ({ ...strip(LANDMARKS[r.key]), p: round(r.w / total), why: r.why, minutes_ago: r.minutes_ago, misses: 0 }))
    .sort((a, b) => b.p - a.p);
  const search_order = places
    .map(pl => {
      const lm = Object.values(LANDMARKS).find(l => l.landmark_id === pl.landmark_id);
      const seconds = walkSeconds(item.wearer_room, lm.room) + CHECK_SECONDS[lm.kind];
      return { ...strip(lm), p: pl.p, seconds, score: (pl.p * FIND_CHANCE[lm.kind]) / seconds };
    })
    .sort((a, b) => b.score - a.score)
    .map(({ score, ...rest }) => rest);
  const [p1 = { p: 0 }, p2 = { p: 0 }] = places;
  const band = p1.p >= 0.6 && p1.p - p2.p >= 0.25 ? 'high' : p1.p + p2.p >= 0.6 ? 'split' : 'low';
  const find = item.carried_in && !saidKey ? { state: 'carried', room: item.carried_in } : { state: places.length ? 'seen' : 'never_seen' };
  return { item: name, plural: item.plural, wearer_room: item.wearer_room, band, places, search_order, find };
}

/** record_miss stand-in: the person checked this place and the item wasn't there. */
export function fakeRecordMiss(itemName, landmarkId) {
  const key = Object.keys(LANDMARKS).find(k => LANDMARKS[k].landmark_id === landmarkId);
  if (!ITEMS[itemName] || !key) return false;
  if (!misses.has(itemName)) misses.set(itemName, new Set());
  misses.get(itemName).add(key);
  return true;
}

/** log_sighting(told, facetime_caller) stand-in. Returns the landmark it matched, or null. */
export function fakeTold(itemPhrase, placePhrase) {
  const name = resolveItem(itemPhrase);
  const key = resolveLandmark(placePhrase);
  if (!name || !key) return { item: name, landmark: null };
  told.set(name, key);
  misses.get(name)?.delete(key);
  return { item: name, plural: ITEMS[name].plural, landmark: strip(LANDMARKS[key]) };
}

// Patient-visible life facts (docs/TYPESENSE.md D29). Fictional demo data only.
const FACTS = [
  { keys: ['june', 'daughter'], say: 'June is your daughter. She visits on Sundays.' },
  { keys: ['doctor', 'appointment'], say: 'Your next doctor visit is Tuesday morning. June will drive you.' },
  { keys: ['pill', 'medicine', 'medication', 'tablet'], say: 'You take your pills at breakfast and at six.' },
  { keys: ['cat', 'whiskers'], say: 'Whiskers is your cat. Whiskers is probably asleep somewhere sunny.' },
];
export function fakeFact(question) {
  const q = String(question || '').toLowerCase();
  return FACTS.find(f => f.keys.some(k => q.includes(k)))?.say ?? null;
}

/** Test hook: forget misses and claims. */
export function resetFakeHome() { misses.clear(); told.clear(); }

const strip = ({ landmark_id, room, landmark }) => ({ landmark_id, room, landmark });
const round = x => Math.round(x * 1000) / 1000;
