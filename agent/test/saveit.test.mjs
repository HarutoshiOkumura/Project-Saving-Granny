// Offline tests: no network, no paid services (CLAUDE.md). Run with `npm test`.
import assert from 'node:assert/strict';
import { beforeEach, test } from 'node:test';
import { cardLines, renderCard, HEIGHT, WIDTH, wrap } from '../card.mjs';
import { fakeRankItem, resetFakeHome, resolveItem } from '../fake-home.mjs';
import { ago, createSaveIt, speakStub } from '../saveit.mjs';

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
  assert.equal(calls[0].url, 'http://backend.test/find?item=keys');
  assert.equal(calls[0].auth, 'Bearer t0k');
  assert.equal(ok.state.suggested.landmark_id, 'x');

  const down = createSaveIt({ backendUrl: 'http://backend.test', log: quiet, fetchImpl: async () => { throw new Error('ECONNREFUSED'); } });
  assert.equal((await down.findObject('keys')).say, "I'm not sure. Let me check with June.");
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
  assert.deepEqual(wrap('a very long place name that will not fit on two short lines at all'), ['A VERY LONG PLACE NAME', 'THAT WILL NOT FIT ON']);
  assert.equal(renderCard({ kind: 'idle' }).length, WIDTH * HEIGHT * 4);
});
