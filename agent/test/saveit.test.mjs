// Offline tests: no network, no paid services (CLAUDE.md). Run with `npm test`.
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { beforeEach, test } from 'node:test';
import { cardLines, renderCard, HEIGHT, WIDTH, wrap } from '../card.mjs';
import { applyEnvFile } from '../env.mjs';
import { fakeRankItem, resetFakeHome, resolveItem } from '../fake-home.mjs';
import { ago, createSaveIt, placeOf, speakStub } from '../saveit.mjs';

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
  assert.match(third.say, /ask June/);
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
  assert.equal((await down.findObject('keys')).say, "I'm not sure. Let me check with June.");
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
    wallet: { sentence: "I'm not sure, let me check with your family.", result: null }, // the backend's own fallback
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
  assert.match(family.say, /ask June/);
  assert.equal(calls.length, 1, 'no /miss call without a landmark id');

  const keys = await s.findObject('keys'); // never seen: the card shows the usual place...
  assert.deepEqual(keys.suggested, { room: 'the hallway', landmark: 'the hook by the front door' });
  assert.match((await s.reportNotThere()).say, /ask June/); // ...which they just checked, so family

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

test('relative times only', () => {
  assert.equal(ago(1), 'just now');
  assert.equal(ago(40), 'about 40 minutes ago');
  assert.equal(ago(65), 'about an hour ago');
});

test('card: at most 2 lines of 22 characters, right frame size', () => {
  for (const view of [{ kind: 'idle' }, { kind: 'place', landmark: 'the table beside your bed', room: 'your bedroom' }, { kind: 'place', landmark: 'the shelf by the front door', room: 'the hallway' }]) {
    const lines = cardLines(view);
    assert.ok(lines.length >= 1 && lines.length <= 2);
    for (const l of lines) assert.ok(l.length <= 22, l);
  }
  assert.deepEqual(cardLines({ kind: 'place', landmark: 'the kitchen counter', room: 'the kitchen' }), ['KITCHEN COUNTER', 'IN THE KITCHEN']);
  assert.deepEqual(cardLines({ kind: 'place', landmark: null, room: 'your bedroom' }), ['YOUR BEDROOM']);
  assert.deepEqual(wrap('a very long place name that will not fit on two short lines at all'), ['A VERY LONG PLACE NAME', 'THAT WILL NOT FIT ON']);
  assert.equal(renderCard({ kind: 'idle' }).length, WIDTH * HEIGHT * 4);
});
