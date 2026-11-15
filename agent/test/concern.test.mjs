// report_concern, offline: no network, no paid services (CLAUDE.md). Run with `npm test`.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { CONCERN_KINDS, SAFETY_SAY, createConcernReporter, safetySay } from '../concern.mjs';
import { SAFETY_RULES, buildInstructions } from '../prompt.mjs';

const VOICE_RULES = readFileSync(new URL('../../.claude/rules/voice.md', import.meta.url), 'utf8');

test('report_concern posts { kind, answer, channel } with the token and says the safety sentence', async () => {
  const calls = [];
  const logs = [];
  const r = createConcernReporter({
    backendUrl: 'http://backend.test/',
    appToken: 't0k',
    log: e => logs.push(e),
    fetchImpl: async (url, init) => {
      calls.push({ url, method: init.method, auth: init.headers.Authorization, body: JSON.parse(init.body) });
      return { ok: true, status: 201, json: async () => ({ id: 'c-1', urgency: 'urgent', room: 'the classroom' }) };
    },
  });
  const out = await r.report('fall', 'no_answer');
  assert.deepEqual(calls, [{ url: 'http://backend.test/concerns', method: 'POST', auth: 'Bearer t0k', body: { kind: 'fall', answer: 'no_answer', channel: 'facetime' } }]);
  assert.equal(out.say, SAFETY_SAY.hurt);
  assert.equal(out.urgency, 'urgent');
  assert.equal(logs[0].ok, true);
  assert.equal(logs[0].id, 'c-1');
});

test('a failing backend never changes what the agent says', async () => {
  for (const fetchImpl of [
    async () => { throw new Error('ECONNREFUSED'); },
    async () => ({ ok: false, status: 503, json: async () => ({}) }),
    async () => ({ ok: false, status: 401, json: async () => ({}) }),
  ]) {
    const logs = [];
    const r = createConcernReporter({ backendUrl: 'http://backend.test', log: e => logs.push(e), fetchImpl });
    const out = await r.report('scam');
    assert.equal(out.say, SAFETY_SAY.scam);
    assert.equal(out.urgency, null);
    assert.equal(logs[0].ok, false);
  }
});

test('fake mode (no BACKEND_URL) sends nothing and still answers', async () => {
  let fetched = false;
  const logs = [];
  const r = createConcernReporter({ log: e => logs.push(e), fetchImpl: async () => { fetched = true; } });
  assert.equal(r.mode, 'fake');
  assert.equal((await r.report('fall', 'ok')).say, SAFETY_SAY.fallOk);
  assert.equal(fetched, false);
  assert.equal(logs[0].sent, false);
});

test('unknown kinds and answers are cleaned, never sent as given', async () => {
  const bodies = [];
  const r = createConcernReporter({
    backendUrl: 'http://backend.test',
    fetchImpl: async (_url, init) => { bodies.push(JSON.parse(init.body)); return { ok: true, json: async () => ({}) }; },
  });
  await r.report('alien', 'maybe');
  assert.deepEqual(bodies[0], { kind: 'help', answer: null, channel: 'facetime' });
});

test('the right sentence for each kind and answer', () => {
  assert.equal(safetySay('fall', 'hurt'), SAFETY_SAY.hurt);
  assert.equal(safetySay('fall', 'no_answer'), SAFETY_SAY.hurt);
  assert.equal(safetySay('fall', 'ok'), SAFETY_SAY.fallOk);
  assert.equal(safetySay('help', 'ok'), SAFETY_SAY.ok);
  assert.equal(safetySay('lost_outside', null), SAFETY_SAY.hurt);
  assert.equal(safetySay('smoke', 'ok'), SAFETY_SAY.smoke);
  assert.equal(safetySay('scam', 'hurt'), SAFETY_SAY.scam);
  assert.deepEqual(CONCERN_KINDS, ['fall', 'hurt', 'help', 'smoke', 'scam', 'lost_outside']);
});

test('safety sentences follow the voice rules and promise nothing', () => {
  for (const say of Object.values(SAFETY_SAY)) {
    const sentences = say.split(/(?<=[.?!])\s+/).filter(Boolean);
    assert.ok(sentences.length <= 2, `more than 2 sentences: ${say}`);
    for (const s of sentences) assert.ok(s.split(/\s+/).length <= 12, `sentence over 12 words: ${say}`);
    assert.doesNotMatch(say, /I('ll| will| have|'ve) (call|told|tell|let|contact|message)|calling 911 now|help is on the way|family/i);
    assert.ok(VOICE_RULES.includes(say), `not in .claude/rules/voice.md (the wording's source of truth): ${say}`);
  }
});

test('prompt: safety rules with triggers, near misses and ask-first, with or without a snapshot', () => {
  for (const known of [[], [{ item: 'glasses', aliases: [], sentence: 'I last saw your glasses on the table just now.' }]]) {
    const text = buildInstructions(known);
    assert.ok(text.includes(SAFETY_RULES));
  }
  for (const phrase of ['fell', 'cannot get up', 'smoke', 'gift cards', 'wire transfer', 'bank details', 'grandchild in jail', "don't tell anyone", 'lost outside']) {
    assert.ok(SAFETY_RULES.includes(phrase), `missing trigger: ${phrase}`);
  }
  for (const nearMiss of ['"my glasses fell"', '"the bag fell off the chair"', '"help me find my keys"', '"I lost my keys"']) {
    assert.ok(SAFETY_RULES.includes(nearMiss), `missing near miss: ${nearMiss}`);
  }
  assert.match(SAFETY_RULES, /"Are you hurt\?"/);
  assert.match(SAFETY_RULES, /never call 911 yourself/);
  assert.match(SAFETY_RULES, /Never say you have called or told anyone/);
});
