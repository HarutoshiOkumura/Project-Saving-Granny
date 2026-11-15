// Offline tests: no network, no paid services (CLAUDE.md). Run with `npm test`.
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { beforeEach, test } from 'node:test';
import { cardLines, renderCard, HEIGHT, SAFE_X, WIDTH, wrap } from '../card.mjs';
import { applyEnvFile } from '../env.mjs';
import { createVoiceMeter } from '../voice-meter.mjs';
import { fakeRankItem, resetFakeHome, resolveItem } from '../fake-home.mjs';
import { ago, cleanPhrase, createSaveIt, matchKnown, placeOf, speakStub } from '../saveit.mjs';
import { createTestCall, localHost } from '../web-call.mjs';
import { GREETING, NAME, buildInstructions, lookalikeGroups } from '../prompt.mjs';

const quiet = () => {};
beforeEach(() => resetFakeHome());

const words = s => s.split(/(?<=[.?!])\s+/).map(x => x.split(/\s+/).length);
function followsVoiceRules(say) {
  const sentences = say.split(/(?<=[.?!])\s+/).filter(Boolean);
  assert.ok(sentences.length <= 2, `more than 2 sentences: ${say}`);
  for (const n of words(say)) assert.ok(n <= 12, `sentence over 12 words: ${say}`);
}

test('aliases resolve like find_item names and aliases', () => {
  assert.equal(resolveItem('my specs'), 'glasses');
  assert.equal(resolveItem('the clicker'), 'remote');
  assert.equal(resolveItem('where are my pills'), 'pill box');
  assert.equal(resolveItem('dentures'), null);
});

test('rank_item shape: probabilities sum to 1, band rule, search order present', () => {
  const r = fakeRankItem('keys');
  assert.equal(r.item, 'keys');
  assert.equal(r.band, 'high');
  assert.ok(Math.abs(r.places.reduce((s, p) => s + p.p, 0) - 1) < 0.01);
  assert.equal(r.search_order[0].landmark, 'the hook by the front door');
  assert.equal(fakeRankItem('pill box').band, 'low');
});

test('speak stand-in covers each case and follows the voice rules', () => {
  const cases = {
    keys: /^Your keys are on the hook by the front door\. I saw them there a few minutes ago\.$/,
    glasses: /^You said the kitchen table\. But I saw your glasses on the table beside your bed\.$/,
    remote: /^You had your remote in the kitchen\. Try the kitchen table first\.$/,
    'pill box': /^I'm not sure about your pill box\. Let's check the kitchen counter first\.$/,
    wallet: /^I haven't seen your wallet today\. Your wallet is usually on the dresser\.$/,
  };
  for (const [item, expected] of Object.entries(cases)) {
    const { say } = speakStub(fakeRankItem(item));
    assert.match(say, expected);
    followsVoiceRules(say);
  }
  assert.match(speakStub(fakeRankItem('dentures')).say, /don't know that one yet/);
});

test('directions: "not there" records a miss and moves to the next place, then offers family', async () => {
  const s = createSaveIt({ log: quiet });
  const first = await s.findObject('my phone');
  assert.equal(first.suggested.landmark, 'the kitchen counter');
  const second = await s.reportNotThere();
  assert.equal(second.suggested.landmark, 'the table beside your bed');
  followsVoiceRules(second.say);
  const third = await s.reportNotThere();
  assert.equal(third.suggested, null);
  assert.equal(third.say, "I'm not sure where else to look right now.");
});

test('"I put my keys on the shelf" changes the next answer', async () => {
  const s = createSaveIt({ log: quiet });
  const told = await s.recordPlacement('keys', 'the shelf by the door', 'placed');
  assert.match(told.say, /keys/);
  const r = fakeRankItem('keys');
  assert.equal(r.places.find(p => p.landmark === 'the shelf by the front door').why, 'you_said');
});

test('backend mode calls /find and falls back safely when the backend fails', async () => {
  const calls = [];
  const ok = createSaveIt({ backendUrl: 'http://backend.test/', appToken: 't0k', log: quiet, fetchImpl: async (url, init) => {
    calls.push({ url, auth: init.headers.Authorization });
    return { ok: true, json: async () => ({ say: 'Your keys are on the hook.', rank: { item: 'keys', search_order: [{ landmark_id: 'x', room: 'the hallway', landmark: 'the hook' }] } }) };
  } });
  const out = await ok.findObject('keys');
  assert.equal(out.say, 'Your keys are on the hook.');
  assert.equal(calls[0].url, 'http://backend.test/find?item=keys&channel=facetime');
  assert.equal(calls[0].auth, 'Bearer t0k');
  assert.equal(ok.state.suggested.landmark_id, 'x');

  const down = createSaveIt({ backendUrl: 'http://backend.test', log: quiet, fetchImpl: async () => { throw new Error('ECONNREFUSED'); } });
  assert.equal((await down.findObject('keys')).say, "I'm not sure right now.");
});

test('backend mode reads step 02 /find ({ sentence, result }) and copes before /miss and /told exist', async () => {
  // Shapes copied from the live GET /find (app/ask.py Answer, app/memory/schema.py FindResult).
  const replies = {
    glasses: { sentence: 'I last saw your glasses on the kitchen counter about forty minutes ago.',
      result: { state: 'seen', item: 'glasses', plural: true, room: 'the kitchen', landmark: 'the kitchen counter', relation: 'on',
        usual: { room: 'your bedroom', landmark: 'the table beside your bed', pct: null, minutes_ago: null }, query_id: 'q-1' } },
    keys: { sentence: "I haven't seen your keys yet, but they usually live on the hook by the front door.",
      result: { state: 'never_seen', item: 'keys', plural: true, usual: { room: 'the hallway', landmark: 'the hook by the front door' }, query_id: 'q-2' } },
    dentures: { sentence: "I'm sorry, which thing are you looking for?", result: { state: 'unknown_item', heard: 'dentures', query_id: 'q-3' } },
    wallet: { sentence: "I'm not sure right now.", result: null }, // the backend's own fallback
  };
  const calls = [];
  const s = createSaveIt({ backendUrl: 'http://backend.test', log: quiet, fetchImpl: async (url, init) => {
    calls.push(`${init.method} ${url}`);
    const u = new URL(url);
    if (u.pathname !== '/find') return { ok: false, status: 404, json: async () => ({ detail: 'Not Found' }) };
    return { ok: true, json: async () => replies[u.searchParams.get('item')] };
  } });

  const seen = await s.findObject('glasses');
  assert.equal(seen.say, replies.glasses.sentence, 'read verbatim');
  assert.deepEqual(seen.suggested, { room: 'the kitchen', landmark: 'the kitchen counter' });
  assert.equal(calls[0], 'GET http://backend.test/find?item=glasses&channel=facetime');
  assert.equal(s.state.queryId, 'q-1');

  const next = await s.reportNotThere(); // no /miss yet: the usual place, once
  assert.equal(next.say, "Okay. Let's look for your glasses on the table beside your bed.");
  assert.deepEqual(next.suggested, { room: 'your bedroom', landmark: 'the table beside your bed' });
  followsVoiceRules(next.say);
  const family = await s.reportNotThere(); // the usual place was just checked: offer family
  assert.equal(family.suggested, null);
  assert.equal(family.say, "I'm not sure where else to look right now.");
  assert.equal(calls.length, 1, 'no /miss call without a landmark id');

  const keys = await s.findObject('keys'); // never seen: the card shows the usual place...
  assert.deepEqual(keys.suggested, { room: 'the hallway', landmark: 'the hook by the front door' });
  assert.equal((await s.reportNotThere()).say, "I'm not sure where else to look right now."); // ...which they just checked

  const unknown = await s.findObject('dentures');
  assert.equal(unknown.say, replies.dentures.sentence);
  assert.equal(unknown.suggested, null);
  assert.equal((await s.reportNotThere()).say, 'Which thing are you looking for?');

  const fallback = await s.findObject('wallet');
  assert.equal(fallback.say, replies.wallet.sentence);
  assert.equal(fallback.suggested, null);

  const told = await s.recordPlacement('my keys', 'the shelf', 'placed'); // /told is a 404: promise nothing
  assert.equal(told.say, 'Okay, thank you for telling me.');
  assert.ok(calls.includes('POST http://backend.test/told'));
});

test('placeOf: where the card points for each step 02 state', () => {
  assert.deepEqual(placeOf({ state: 'carried', room: 'the kitchen', wearer_went_to: 'your bedroom' }), { room: 'your bedroom', landmark: null });
  assert.deepEqual(placeOf({ state: 'carried', room: 'the kitchen', wearer_went_to: null }), { room: 'the kitchen', landmark: null });
  assert.deepEqual(placeOf({ state: 'seen', room: 'the kitchen', landmark: null }), { room: 'the kitchen', landmark: null });
  assert.deepEqual(placeOf({ state: 'not_there_anymore', usual: { room: 'your bedroom', landmark: 'the desk' } }), { room: 'your bedroom', landmark: 'the desk' });
  assert.equal(placeOf({ state: 'not_there_anymore', usual: null }), null);
  assert.equal(placeOf({ state: 'unknown_item', heard: 'dentures' }), null);
  assert.equal(placeOf(null), null);
});

test('env: .env.local wins over the terminal (VS Code injects the repo .env), and database keys are dropped', () => {
  const dir = mkdtempSync(join(tmpdir(), 'saveit-env-'));
  try {
    const file = join(dir, '.env.local');
    writeFileSync(file, 'AGENT_NAME=save-it\nBACKEND_URL=http://localhost:8000\n');
    const env = applyEnvFile(file, { AGENT_NAME: 'my-agent', SUPABASE_SECRET_KEY: 'fake', SUPABASE_URL: 'https://fake.test', DATABASE_URL: 'postgres://fake', PATH: '/bin' });
    assert.equal(env.AGENT_NAME, 'save-it');
    assert.equal(env.BACKEND_URL, 'http://localhost:8000');
    assert.equal(env.PATH, '/bin');
    for (const key of ['SUPABASE_SECRET_KEY', 'SUPABASE_URL', 'DATABASE_URL']) assert.equal(key in env, false, key);
    assert.equal(applyEnvFile(join(dir, 'missing'), { A: '1' }).A, '1'); // no .env.local: nothing breaks
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('web-call: a fresh room per call, its token dispatches the agent as a test call; local hosts only', async () => {
  const keys = { url: 'wss://fake.livekit.cloud', apiKey: 'APIfake', apiSecret: 'fake-secret-long-enough-for-hmac-signing-0123456789' };
  const a = await createTestCall({ ...keys, agentName: 'save-it', now: 1 });
  const b = await createTestCall({ ...keys, agentName: 'save-it', now: 2 });
  assert.notEqual(a.room, b.room, 'dispatch only happens when the room is created');
  const claims = JSON.parse(Buffer.from(a.token.split('.')[1], 'base64url'));
  assert.equal(claims.video.room, a.room);
  assert.equal(claims.video.roomJoin, true);
  assert.equal(claims.roomConfig.agents[0].agentName, 'save-it');
  assert.deepEqual(JSON.parse(claims.roomConfig.agents[0].metadata), { test_call: true });
  await assert.rejects(createTestCall({ url: '', apiKey: '', apiSecret: '' }), /LIVEKIT_URL/);
  assert.ok(localHost('127.0.0.1:8090') && localHost('localhost:8090'));
  assert.ok(!localHost('evil.example:8090') && !localHost('127.0.0.1.evil.example') && !localHost(undefined));
});

const KNOWN = [
  { item: 'glasses', aliases: ['specs', 'reading glasses'], sentence: 'I last saw your glasses on the table about forty minutes ago.' },
  { item: 'water bottle', aliases: ['bottle', 'water'], sentence: 'I last saw your water bottle next to the chair about two hours ago.' },
  { item: 'watch', aliases: [], sentence: "Your watch isn't on the table anymore, and I haven't seen where it went." },
];

test('matchKnown: names and aliases as whole words, longest first', () => {
  assert.equal(matchKnown(KNOWN, 'Where are my specs?'), 'glasses');
  assert.equal(matchKnown(KNOWN, 'have you seen the water bottle'), 'water bottle');
  assert.equal(matchKnown(KNOWN, 'I need some water'), 'water bottle');
  assert.equal(matchKnown(KNOWN, 'thank you so much'), null);
  assert.equal(matchKnown(KNOWN, 'stopwatch'), null, 'whole words only');
  assert.equal(matchKnown([], 'glasses'), null);
});

test('snapshot at call start; what the caller says drives the logged lookup and the card', async () => {
  const calls = [];
  const s = createSaveIt({ backendUrl: 'http://b.test', log: quiet, fetchImpl: async url => {
    calls.push(url);
    const u = new URL(url);
    if (u.pathname === '/snapshot') return { ok: true, json: async () => KNOWN };
    if (u.pathname === '/find') return { ok: true, json: async () => ({ sentence: 'x', result: { state: 'seen', item: u.searchParams.get('item'), room: 'the classroom', landmark: 'the table', query_id: 'q-9' } }) };
    return { ok: false, status: 404, json: async () => ({}) };
  } });
  assert.equal((await s.loadSnapshot()).length, 3);
  const out = await s.noteHeard('Where are my specs?');
  assert.equal(calls.at(-1), 'http://b.test/find?item=glasses&channel=facetime', 'logged under the item name');
  assert.deepEqual(out.suggested, { room: 'the classroom', landmark: 'the table' });
  assert.equal(await s.noteHeard('thank you'), null);
  assert.equal(calls.length, 2, 'nothing looked up for small talk');
});

test('snapshot failure leaves the agent on per-question lookups', async () => {
  const logs = [];
  const s = createSaveIt({ backendUrl: 'http://b.test', log: e => logs.push(e), fetchImpl: async () => { throw new Error('ECONNREFUSED'); } });
  assert.deepEqual(await s.loadSnapshot(), []);
  assert.equal(logs[0].ok, false);
  assert.deepEqual(await createSaveIt({ log: quiet }).loadSnapshot(), [], 'fake mode has no snapshot');
});

test('"not there" can name the thing, when the model answered from the snapshot', async () => {
  const urls = [];
  const s = createSaveIt({ backendUrl: 'http://b.test', log: quiet, fetchImpl: async url => {
    urls.push(url);
    const u = new URL(url);
    if (u.pathname === '/snapshot') return { ok: true, json: async () => KNOWN };
    return { ok: true, json: async () => ({ sentence: 'x', result: { state: 'seen', item: 'glasses', room: 'the classroom', landmark: 'the table', usual: { room: 'the classroom', landmark: 'the chair' } } }) };
  } });
  await s.loadSnapshot();
  const next = await s.reportNotThere('my specs');
  assert.equal(urls.at(-1), 'http://b.test/find?item=glasses&channel=facetime');
  assert.equal(next.say, "Okay. Let's look for your glasses on the chair.");
});

test('env: X_OVERRIDE from the terminal beats the file, but never brings database keys back', () => {
  const dir = mkdtempSync(join(tmpdir(), 'saveit-env-'));
  try {
    const file = join(dir, '.env.local');
    writeFileSync(file, 'AGENT_NAME=save-it\nBACKEND_URL=http://localhost:8000\n');
    const env = applyEnvFile(file, { AGENT_NAME_OVERRIDE: 'save-it-bench', BACKEND_URL_OVERRIDE: 'http://127.0.0.1:8010', SUPABASE_SECRET_KEY_OVERRIDE: 'fake', DATABASE_URL_OVERRIDE: 'postgres://fake' });
    assert.equal(env.AGENT_NAME, 'save-it-bench');
    assert.equal(env.BACKEND_URL, 'http://127.0.0.1:8010');
    for (const key of Object.keys(env)) assert.ok(!key.startsWith('SUPABASE_') && !key.startsWith('DATABASE_URL'), key);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('card: green while the caller\'s voice comes in, orange while Save It talks, no word, inside the safe area', () => {
  const pixels = (px, rgb) => { let n = 0; for (let i = 0; i < px.length; i += 4) if (px[i] === rgb[0] && px[i + 1] === rgb[1] && px[i + 2] === rgb[2]) n++; return n; };
  const view = { kind: 'place', landmark: 'the table', room: 'the classroom' };
  const hear = renderCard(view, 'listening'), talk = renderCard(view, 'speaking'), idle = renderCard(view, 'idle');
  assert.ok(pixels(hear, [46, 204, 113]) > 1000, 'green ring');
  assert.equal(pixels(talk, [46, 204, 113]), 0);
  assert.ok(pixels(talk, [255, 180, 60]) > 500, 'orange ring while talking');
  assert.equal(pixels(idle, [46, 204, 113]) + pixels(idle, [255, 180, 60]), 0);
  assert.deepEqual(renderCard(view, true), talk, 'true still means talking');
  assert.deepEqual(renderCard(view, false), idle, 'false still means idle');
  let outside = 0;
  for (let y = 0; y < HEIGHT; y++) for (let x = 0; x < WIDTH; x++) {
    if (x >= SAFE_X && x < WIDTH - SAFE_X) continue;
    const i = (y * WIDTH + x) * 4;
    if (hear[i] === 46 && hear[i + 1] === 204 && hear[i + 2] === 113) outside++;
  }
  assert.equal(outside, 0, 'the light stays inside the part FaceTime shows');
});

test('only a word naming exactly one item is looked up: no junk logging, no blanked card', async () => {
  const urls = [];
  const s = createSaveIt({ backendUrl: 'http://b.test', log: quiet, fetchImpl: async url => {
    urls.push(url);
    if (new URL(url).pathname === '/snapshot') return { ok: true, json: async () => KNOWN };
    return { ok: true, json: async () => ({ sentence: 'x', result: { state: 'unknown_item' } }) };
  } });
  await s.loadSnapshot();
  assert.equal(await s.noteHeard('Where are my pencils?'), null, 'unknown things: the model answers, nothing logged');
  assert.equal(await s.noteHeard('Tell me where the blue one is first.'), null, 'follow-ups name no item');
  assert.equal(await s.noteHeard("That's pretty tough."), null);
  assert.deepEqual(urls, ['http://b.test/snapshot']);
});

const tone = (amplitude, ms = 10, rate = 16000) => {
  const n = (rate * ms) / 1000;
  return { data: Int16Array.from({ length: n }, (_, i) => Math.round(amplitude * Math.sin((2 * Math.PI * 220 * i) / rate))), sampleRate: rate, samplesPerChannel: n };
};

test('voice meter: on within 60 ms of voice, ignores clicks, waits out pauses between words, off after quiet', () => {
  const changes = [];
  const m = createVoiceMeter({ onChange: on => changes.push(on) });
  for (let i = 0; i < 50; i++) m.push(tone(80)); // half a second of a quiet room
  m.push(tone(4000)); m.push(tone(4000)); // a 20 ms click
  for (let i = 0; i < 5; i++) m.push(tone(80));
  assert.deepEqual(changes, [], 'a click does not light it');
  for (let i = 0; i < 6; i++) m.push(tone(3000)); // 60 ms of voice
  assert.deepEqual(changes, [true], 'on after 60 ms of voice');
  for (let i = 0; i < 30; i++) m.push(tone(80)); // a 300 ms pause between words
  assert.deepEqual(changes, [true], 'stays on through a pause');
  for (let i = 0; i < 20; i++) m.push(tone(80)); // 500 ms of quiet in all
  assert.deepEqual(changes, [true, false]);
});

test('voice meter: a steady hum never lights it, a voice over the hum does', () => {
  const changes = [];
  const m = createVoiceMeter({ onChange: on => changes.push(on) });
  for (let i = 0; i < 400; i++) m.push(tone(900)); // 4 s of a fan or traffic, louder than the quiet threshold
  assert.deepEqual(changes, [], 'the hum is learned as the room, not a voice');
  for (let i = 0; i < 8; i++) m.push(tone(6000));
  assert.deepEqual(changes, [true]);
  for (let i = 0; i < 2; i++) m.push(tone(0)); // a dropped packet mid-hum does not reset the room's level
  for (let i = 0; i < 60; i++) m.push(tone(900));
  assert.deepEqual(changes, [true, false]);
});

const TWO_BOTTLES = [
  { item: 'blue water bottle', aliases: ['water bottle', 'bottle'], looks_like: 'blue, steel', sentence: 'I last saw your blue water bottle next to the chair about two hours ago.' },
  { item: 'green water bottle', aliases: ['water bottle', 'bottle'], looks_like: 'green, plastic', sentence: 'I last saw your green water bottle on the table about ten minutes ago.' },
  { item: 'glasses', aliases: ['specs'], sentence: 'I last saw your glasses on the table about an hour ago.' },
];

test('prompt: Find It, looks for telling look-alikes apart, where it was before, ask only when it could be either', () => {
  const p = buildInstructions([{ ...TWO_BOTTLES[0], result: { previous: { landmark: 'the table', minutes_ago: 180 }, usual: { landmark: 'the chair' } } }, TWO_BOTTLES[1]], 'June');
  assert.equal(NAME, 'Find It');
  assert.match(p, /^You are Find It,/);
  assert.match(GREETING, /Find It/);
  assert.match(p, /  - blue water bottle, which looks like blue, steel: I last saw your blue water bottle[^\n]*before that: the table, about 3 hours ago; usually lives: the chair/);
  assert.match(p, /before that: the table, about 3 hours ago; usually lives: the chair/);
  assert.match(p, /- "water bottle", "bottle" could be:\n  - blue water bottle, which looks like blue, steel: I last saw your blue water bottle/);
  assert.match(p, /not on this list, tell them kindly that you do not know it yet/);
  assert.doesNotMatch(p, /find_object/, 'no lookup tool when the list is loaded');
  assert.match(buildInstructions([], 'June'), /call find_object/, 'without a list it looks things up');
  assert.doesNotMatch(p, /Save It/);
});

const CLASSROOM = [
  { item: 'bag', kind: 'bag', color: 'green', aliases: ['green bag', 'handbag', 'purse'], looks_like: 'green, green handbag with gold lettering', sentence: "I haven't seen your bag yet." },
  { item: 'brown bag', kind: 'bag', color: 'brown', aliases: ['bag', 'brown handbag'], looks_like: 'brown, brown bag', sentence: 'I last saw your brown bag on the floor about twenty minutes ago.' },
  { item: 'water bottle', kind: 'bottle', color: 'dark blue', aliases: ['bottle', 'blue bottle', 'drink bottle', 'flask'], looks_like: 'dark blue, dark blue water bottle', sentence: 'I last saw your water bottle next to the chair about four hours ago.' },
  { item: 'orange water bottle', kind: 'bottle', color: 'orange', aliases: ['water bottle', 'bottle', 'drink bottle'], looks_like: 'orange, orange water bottle', sentence: 'I last saw your orange water bottle on the table about fifteen minutes ago.' },
  { item: 'glasses', kind: 'glasses', color: 'black', aliases: ['specs'], sentence: 'I last saw your glasses on the table about two hours ago.' },
];

// Same colour, no shared aliases: only the kind and the descriptions tell them apart.
const CUPS = [
  { item: 'cup', kind: 'cup', aliases: [], looks_like: 'white, big white mug', sentence: 'I last saw your cup on the table about ten minutes ago.' },
  { item: 'small cup', kind: 'cup', aliases: [], looks_like: 'white, small white espresso cup', sentence: 'I last saw your small cup next to the chair about an hour ago.' },
  { item: 'glasses', kind: 'glasses', aliases: ['specs'], sentence: 'I last saw your glasses on the table about two hours ago.' },
];

test('look-alikes come from the kind (and shared words), worked out each call; nothing is renamed', () => {
  const groups = lookalikeGroups(CLASSROOM).map(g => ({ items: g.items, words: g.words.sort() }));
  assert.deepEqual(groups, [
    { items: ['bag', 'brown bag'], words: ['bag'] },
    { items: ['orange water bottle', 'water bottle'], words: ['bottle', 'drink bottle', 'water bottle'] },
  ]);
  assert.deepEqual(lookalikeGroups([CLASSROOM[0], CLASSROOM[4]]), [], 'one bag on its own is just "bag"');
  const p = buildInstructions(CLASSROOM);
  assert.match(p, /- "bag" could be:\n  - bag, which looks like green, green handbag with gold lettering: I haven't seen your bag yet\.\n  - brown bag, which looks like brown, brown bag: I last saw your brown bag on the floor/);
  assert.doesNotMatch(p, /^- bag[;:(]/m, 'look-alikes only in their group, under their own name ("bag")');
  assert.match(p, /^- glasses \(a glasses\)|^- glasses; also called specs/m, 'others stay in the main list');
  assert.doesNotMatch(p, /June|check with your family|alert_caregiver|recall_life_fact/);
  assert.match(p, /You cannot call, text or message anyone/);
});

test('a big and a small white cup with no aliases: grouped by kind, told apart by their descriptions', () => {
  assert.deepEqual(lookalikeGroups(CUPS).map(g => g.items), [['cup', 'small cup']]);
  const p = buildInstructions(CUPS);
  assert.match(p, /- "cup" could be:\n  - cup, which looks like white, big white mug: I last saw your cup on the table\.*[^\n]*\n  - small cup, which looks like white, small white espresso cup: I last saw your small cup next to the chair/);
  assert.match(p, /colour, size, shape, brand/);
  assert.equal(matchKnown(CUPS, 'Where is my cup?'), null, 'a bare kind word with two cups: ask');
  assert.equal(matchKnown(CUPS, 'Where is my small cup?'), 'small cup');
  assert.equal(matchKnown(CUPS, 'Your small cup is next to the chair.'), 'small cup');
});

test('matching: two items named apart are ambiguous; a word inside a longer name is part of it', () => {
  assert.equal(matchKnown(CLASSROOM, 'Where is my bag?'), null, 'two bags: ask');
  assert.equal(matchKnown(CLASSROOM, 'Where is my brown bag?'), 'brown bag', 'the "bag" inside "brown bag" is part of it');
  assert.equal(matchKnown(CLASSROOM, 'Which one? The green bag or the brown handbag?'), null, 'names two items: the card stays');
  assert.equal(matchKnown(CLASSROOM, "I haven't seen your green bag yet."), 'bag');
  const noAlias = [{ ...CLASSROOM[0] }, { ...CLASSROOM[1], aliases: ['brown handbag'] }];
  assert.equal(matchKnown(noAlias, 'Where is my bag?'), null, 'still ambiguous without the shared alias: same kind');
});

test('two water bottles: "water bottle" is ambiguous (the model asks), "blue water bottle" is not', () => {
  assert.equal(matchKnown(TWO_BOTTLES, 'Where is my water bottle?'), null);
  assert.equal(matchKnown(TWO_BOTTLES, 'where is my blue water bottle'), 'blue water bottle');
  assert.equal(matchKnown(TWO_BOTTLES, 'The blue one.'), null, 'the answer to "which one" names no item');
  assert.equal(matchKnown(TWO_BOTTLES, 'Your green water bottle is on the table.'), 'green water bottle');
});

test('the card follows the reply after "which one?", and each exchange is logged once', async () => {
  const urls = [];
  const s = createSaveIt({ backendUrl: 'http://b.test', log: quiet, fetchImpl: async url => {
    urls.push(url);
    const u = new URL(url);
    if (u.pathname === '/snapshot') return { ok: true, json: async () => TWO_BOTTLES };
    return { ok: true, json: async () => ({ sentence: 'x', result: { state: 'seen', item: u.searchParams.get('item'), room: 'the classroom', landmark: 'the table' } }) };
  } });
  await s.loadSnapshot();
  assert.equal(await s.noteHeard('Where is my water bottle?'), null, 'ambiguous: nothing looked up or logged yet');
  assert.equal(await s.noteSaid('The blue one or the green one?'), null);
  assert.equal(await s.noteSaid('Which one? Your blue water bottle or the green one?'), null, 'a question naming one bottle is still a question');
  assert.equal(await s.noteHeard('The green one.'), null);
  const out = await s.noteSaid('Your green water bottle is on the table, about ten minutes ago.');
  assert.deepEqual(out.suggested, { room: 'the classroom', landmark: 'the table' });
  assert.equal(urls.at(-1), 'http://b.test/find?item=green%20water%20bottle&channel=facetime');
  await s.noteHeard('Where are my specs?');
  assert.equal(await s.noteSaid('Your glasses are on the table.'), null, 'already looked up from the question');
  assert.equal(urls.filter(u => u.includes('/find')).length, 2, 'one logged question per exchange');
  const before = urls.length;
  const answer = await createSaveIt({ backendUrl: 'http://b.test', log: quiet, fetchImpl: async url => {
    urls.push(url);
    if (new URL(url).pathname === '/snapshot') return { ok: true, json: async () => TWO_BOTTLES };
    return { ok: true, json: async () => ({ sentence: 'x', result: { state: 'seen', item: 'glasses', room: 'the classroom', landmark: 'the table' } }) };
  } });
  await answer.loadSnapshot();
  assert.ok(await answer.noteSaid('I last saw your glasses on the table. Want me to stay while you look?'), 'an answer with a follow-up question still counts');
  assert.equal(urls.length - before, 2);
});

test('relative times only', () => {
  assert.equal(ago(1), 'just now');
  assert.equal(ago(40), 'about 40 minutes ago');
  assert.equal(ago(65), 'about an hour ago');
});

test('cleanPhrase: send the thing, not the question (find_item matches names exactly)', async () => {
  assert.equal(cleanPhrase('Where are my glasses?'), 'glasses');
  assert.equal(cleanPhrase('can you help me find my phone'), 'phone');
  assert.equal(cleanPhrase('my specs'), 'specs');
  assert.equal(cleanPhrase('reading glasses'), 'reading glasses');
  assert.equal(cleanPhrase('the green bag'), 'green bag');
  assert.equal(cleanPhrase('where did I put it'), 'where did I put it'); // nothing left: as given, so the backend asks
  const urls = [];
  const s = createSaveIt({ backendUrl: 'http://b.test', log: quiet, fetchImpl: async url => {
    urls.push(url);
    return { ok: true, json: async () => ({ sentence: 'x', result: null }) };
  } });
  await s.findObject('Where are my glasses?');
  assert.equal(urls[0], 'http://b.test/find?item=glasses&channel=facetime');
});

test('card: everything readable stays inside the part FaceTime shows (it cropped ~100 px each side)', () => {
  const views = [
    { kind: 'idle' },
    { kind: 'place', landmark: 'the shelf by the front door', room: 'the hallway' },
    { kind: 'place', landmark: 'the table beside your bed', room: 'your bedroom' },
    { kind: 'place', landmark: 'the kitchen counter', room: 'the kitchen' },
    { kind: 'place', landmark: null, room: 'your bedroom' },
    { kind: 'text', text: 'Take your time, no rush' },
  ];
  const isText = (px, i) => (px[i] === 255 && px[i + 1] === 255 && px[i + 2] === 255) || (px[i] === 140 && px[i + 1] === 180 && px[i + 2] === 190);
  for (const view of views) {
    for (const lit of [false, true]) {
      const px = renderCard(view, lit);
      let stray = null;
      for (let y = 0; y < HEIGHT && !stray; y++) {
        for (let x = 0; x < WIDTH; x++) {
          if (x >= SAFE_X && x < WIDTH - SAFE_X) continue;
          if (isText(px, (y * WIDTH + x) * 4)) { stray = { x, y }; break; }
        }
      }
      assert.equal(stray, null, `text drawn in the cropped margin for ${JSON.stringify(view)}`);
    }
  }
});

test('card: at most 2 lines of 16 characters, right frame size', () => {
  for (const view of [{ kind: 'idle' }, { kind: 'place', landmark: 'the table beside your bed', room: 'your bedroom' }, { kind: 'place', landmark: 'the shelf by the front door', room: 'the hallway' }]) {
    const lines = cardLines(view);
    assert.ok(lines.length >= 1 && lines.length <= 2);
    for (const l of lines) assert.ok(l.length <= 16, l);
  }
  assert.deepEqual(cardLines({ kind: 'place', landmark: 'the kitchen counter', room: 'the kitchen' }), ['KITCHEN COUNTER', 'IN THE KITCHEN']);
  assert.deepEqual(cardLines({ kind: 'place', landmark: null, room: 'your bedroom' }), ['YOUR BEDROOM']);
  assert.deepEqual(cardLines({ kind: 'place', landmark: 'the table beside your bed', room: 'your bedroom' }), ['TABLE BESIDE', 'YOUR BED']);
  assert.deepEqual(wrap('a very long place name that will not fit on two short lines at all'), ['A VERY LONG', 'PLACE NAME THAT']);
  assert.equal(renderCard({ kind: 'idle' }).length, WIDTH * HEIGHT * 4);
});
