// Offline tests for guided directions: no network, no timers, no paid services. Run with `npm test`.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { GUIDE_TOOL, createGuide, sayGuidance } from '../guide.mjs';

const KNOWN = [
  { item: 'glasses', aliases: ['specs'], sentence: 'I last saw your glasses on the table just now.' },
  { item: 'keys', aliases: ['key'], sentence: 'I last saw your keys on the chair just now.' },
];
const TABLE = { room: 'the classroom', landmark: 'the table' };

const step = (name, progress, extra = {}) => ({ step: name, key: `${name}:${extra.detail ?? 'x'}`, progress, done: false, sentence: `${name} sentence.`, view_age_s: 2, ...extra });
const NO_VIEW = step('no_view', 0);
const GO = step('go_to_room', 1, { detail: 'the hallway>the kitchen' });
const LOOK = step('look_for', 2);
const IN_VIEW = step('in_view', 3);
const SEEN = step('item_in_view', 4);
const IN_HAND = step('in_hand', 5, { done: true });
const GONE = step('none', 0, { done: true, detail: 'not_there_anymore' });
const UNSURE = step('unsure', 0, { key: 'unsure', sentence: "I'm not sure right now." });

/** A call with a fake backend, clock and timer. `next` is what GET /guide answers; `quiet` is whether Find It may speak. */
function call({ item = 'glasses', suggested = TABLE, ...options } = {}) {
  const c = {
    next: NO_VIEW,
    quiet: true,
    clock: 1_000_000,
    said: [],
    urls: [],
    headers: [],
    logs: [],
    lookups: [],
    shown: [],
    timers: [],
    cleared: [],
    saveIt: {
      state: { item, suggested, known: KNOWN },
      findObject: async phrase => {
        c.lookups.push(phrase);
        c.saveIt.state.item = phrase;
        c.saveIt.state.suggested = { room: 'the classroom', landmark: 'the chair' };
        return { say: 'found', suggested: c.saveIt.state.suggested };
      },
    },
  };
  c.guide = createGuide({
    saveIt: c.saveIt,
    backendUrl: 'http://backend.test/',
    announce: g => (c.quiet ? (c.said.push(g.sentence), true) : false),
    onLookup: out => c.shown.push(out),
    fetchImpl: async (url, init) => {
      c.urls.push(url);
      c.headers.push(init.headers);
      if (c.next instanceof Error) throw c.next;
      if (typeof c.next === 'number') return { ok: false, status: c.next, json: async () => ({}) };
      return { ok: true, status: 200, json: async () => c.next };
    },
    log: entry => c.logs.push(entry),
    now: () => c.clock,
    setTimer: (fn, ms) => (c.timers.push({ fn, ms }), c.timers.length),
    clearTimer: id => c.cleared.push(id),
    ...options,
  });
  /** One poll, `seconds` later, with the backend answering `answer`. */
  c.poll = async (answer, seconds = 2) => {
    c.next = answer;
    c.clock += seconds * 1000;
    await c.guide.tick();
  };
  return c;
}

test('begin returns the first direction and starts polling', async () => {
  const c = call();
  c.next = GO;
  assert.equal(await c.guide.begin(), 'go_to_room sentence.');
  assert.equal(c.guide.active, true);
  assert.equal(c.guide.item, 'glasses');
  assert.deepEqual(c.urls, ['http://backend.test/guide?item=glasses']);
  assert.deepEqual(c.timers.map(t => t.ms), [2000]);
  assert.deepEqual(c.said, [], 'the first direction is the tool reply, not an announcement');
});

test('getting closer is said at once, and the same step is never said twice', async () => {
  const c = call();
  c.next = GO;
  await c.guide.begin();
  await c.poll(GO, 6);
  await c.poll(LOOK);
  await c.poll(LOOK);
  await c.poll(IN_VIEW, 6);
  await c.poll(IN_VIEW);
  assert.deepEqual(c.said, ['look_for sentence.', 'in_view sentence.']);
});

test('directions are at least five seconds apart', async () => {
  const c = call();
  c.next = GO;
  await c.guide.begin();
  await c.poll(LOOK, 2);
  await c.poll(LOOK, 2);
  assert.deepEqual(c.said, [], 'four seconds after the first direction is too soon');
  await c.poll(LOOK, 2);
  assert.deepEqual(c.said, ['look_for sentence.']);
});

test('nothing is said while someone is talking, and the step is tried again', async () => {
  const c = call();
  c.next = GO;
  await c.guide.begin();
  c.quiet = false;
  await c.poll(LOOK, 6);
  await c.poll(LOOK);
  assert.deepEqual(c.said, []);
  c.quiet = true;
  await c.poll(LOOK);
  assert.deepEqual(c.said, ['look_for sentence.']);
});

test('one odd frame never takes a direction back', async () => {
  const c = call();
  c.next = IN_VIEW;
  await c.guide.begin();
  await c.poll(LOOK, 6); // they glanced away
  await c.poll(IN_VIEW);
  await c.poll(LOOK);
  await c.poll(LOOK);
  await c.poll(IN_VIEW); // back before it held for three polls
  assert.deepEqual(c.said, []);
});

test('a step back is said once it has held for three polls', async () => {
  const c = call();
  c.next = LOOK;
  await c.guide.begin();
  await c.poll(GO, 6); // they walked out of the room
  await c.poll(GO);
  assert.deepEqual(c.said, []);
  await c.poll(GO);
  assert.deepEqual(c.said, ['go_to_room sentence.']);
  await c.poll(LOOK, 6); // and came back: closer again, said at once
  assert.deepEqual(c.said, ['go_to_room sentence.', 'look_for sentence.']);
});

test('a different room at the same distance waits to settle too', async () => {
  const c = call();
  c.next = GO;
  await c.guide.begin();
  const other = step('go_to_room', 1, { detail: 'your bedroom>the hallway', sentence: 'other room sentence.' });
  await c.poll(other, 6);
  await c.poll(other);
  assert.deepEqual(c.said, []);
  await c.poll(other);
  assert.deepEqual(c.said, ['other room sentence.']);
});

test('in the hand: said, and the guiding ends', async () => {
  const c = call();
  c.next = IN_VIEW;
  await c.guide.begin();
  await c.poll(SEEN, 6);
  await c.poll(IN_HAND, 6);
  assert.deepEqual(c.said, ['item_in_view sentence.', 'in_hand sentence.']);
  assert.equal(c.guide.active, false);
  assert.deepEqual(c.cleared, [1]);
  assert.equal(c.logs.at(-1).reason, 'done');
  await c.poll(IN_VIEW, 6);
  assert.equal(c.urls.length, 3, 'no polling after the end');
});

test('not there anymore: the plain answer is said, and the guiding ends', async () => {
  const c = call();
  c.next = IN_VIEW;
  await c.guide.begin();
  await c.poll(GONE, 6);
  assert.deepEqual(c.said, ['none sentence.']);
  assert.equal(c.guide.active, false);
});

test('nothing to guide to: begin gives the plain answer and does not poll', async () => {
  const c = call();
  c.next = GONE;
  assert.equal(await c.guide.begin(), 'none sentence.');
  assert.equal(c.guide.active, false);
  assert.deepEqual(c.timers, []);
});

test('backend trouble: begin says it is not sure and does not poll', async () => {
  for (const trouble of [UNSURE, 500, new Error('connection refused'), { step: 'look_for' }]) {
    const c = call();
    c.next = trouble;
    assert.equal(await c.guide.begin(), "I'm not sure right now.");
    assert.equal(c.guide.active, false);
  }
});

test('trouble on a poll is skipped quietly and the guiding carries on', async () => {
  const c = call();
  c.next = GO;
  await c.guide.begin();
  await c.poll(new Error('timeout'), 6);
  await c.poll(503);
  await c.poll(UNSURE);
  assert.deepEqual(c.said, []);
  assert.equal(c.guide.active, true);
  await c.poll(LOOK);
  assert.deepEqual(c.said, ['look_for sentence.']);
});

test('asking about another thing ends the guiding', async () => {
  const c = call();
  c.next = GO;
  await c.guide.begin();
  c.saveIt.state.item = 'keys';
  c.saveIt.state.suggested = { room: 'the classroom', landmark: 'the chair' };
  await c.poll(LOOK, 6);
  assert.deepEqual(c.said, []);
  assert.equal(c.guide.active, false);
  assert.equal(c.logs.at(-1).reason, 'moved_on');
  assert.equal(c.urls.length, 1, 'the poll is not even sent');
});

test('"not there" moves the card to the next place, which ends the guiding', async () => {
  const c = call();
  c.next = IN_VIEW;
  await c.guide.begin();
  c.saveIt.state.suggested = null; // report_not_there with nowhere else to look
  await c.poll(IN_VIEW, 6);
  assert.equal(c.guide.active, false);
});

test('looking the same thing up again does not end the guiding', async () => {
  const c = call();
  c.next = GO;
  await c.guide.begin();
  c.saveIt.state.suggested = { ...TABLE }; // noteSaid looked it up again: a new object, the same place
  await c.poll(LOOK, 6);
  assert.deepEqual(c.said, ['look_for sentence.']);
});

test('guiding stops by itself after three minutes', async () => {
  const c = call();
  c.next = GO;
  await c.guide.begin();
  await c.poll(GO, 181);
  assert.equal(c.guide.active, false);
  assert.equal(c.logs.at(-1).reason, 'timeout');
});

test('guiding stops after eight directions', async () => {
  const c = call({ maxSays: 3 });
  c.next = GO;
  await c.guide.begin(); // 1
  await c.poll(LOOK, 6); // 2
  await c.poll(IN_VIEW, 6); // 3
  assert.equal(c.guide.active, false);
  assert.equal(c.logs.at(-1).reason, 'enough_said');
});

test('a named thing that is not the current one is looked up first, so the card follows', async () => {
  const c = call();
  c.next = GO;
  await c.guide.begin('my key');
  assert.deepEqual(c.lookups, ['keys']);
  assert.equal(c.shown.length, 1);
  assert.deepEqual(c.urls, ['http://backend.test/guide?item=keys']);
  await c.poll(LOOK, 6);
  assert.deepEqual(c.said, ['look_for sentence.'], 'the lookup before the start does not count as moving on');
});

test('naming the current thing looks nothing up', async () => {
  const c = call();
  c.next = GO;
  await c.guide.begin('where are my specs');
  assert.deepEqual(c.lookups, []);
  assert.deepEqual(c.urls, ['http://backend.test/guide?item=glasses']);
});

test('no thing at all: it asks which one', async () => {
  const c = call({ item: null, suggested: null });
  assert.equal(await c.guide.begin(), 'Which thing are you looking for?');
  assert.deepEqual(c.urls, []);
});

test('beginning again restarts cleanly', async () => {
  const c = call();
  c.next = GO;
  await c.guide.begin();
  await c.guide.begin();
  assert.deepEqual(c.cleared, [1]);
  assert.equal(c.timers.length, 2);
  assert.equal(c.guide.active, true);
});

test('stop is safe when nothing is running, and the token is sent when set', async () => {
  const c = call({ appToken: 'secret' });
  c.guide.stop('call_end');
  assert.deepEqual(c.logs, []);
  c.next = GO;
  await c.guide.begin();
  assert.equal(c.headers[0].Authorization, 'Bearer secret');
  c.guide.stop('call_end');
  assert.equal(c.guide.active, false);
});

test('an announce that throws (the call is ending) is not counted as said', async () => {
  const c = call({ announce: () => { throw new Error('AgentSession is not running'); } });
  c.next = GO;
  await c.guide.begin();
  await c.poll(LOOK, 6);
  assert.equal(c.guide.active, true);
  assert.equal(c.logs.at(-1).ok, false);
});

test('the wording handed to the model keeps the sentence whole and says when to guide', () => {
  assert.ok(sayGuidance('Look for the table.').includes('"Look for the table."'));
  assert.match(GUIDE_TOOL, /staying on the line/);
});
