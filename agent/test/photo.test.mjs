// Offline tests for the photo card and the description search: no network, no paid services. `npm test`.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import sharp from 'sharp';
import { FACETIME_CROP, HEIGHT, SAFE_X, WIDTH, isPhoto, photoLayout, renderCard } from '../card.mjs';
import { decodePhoto } from '../photo.mjs';
import { buildInstructions } from '../prompt.mjs';
import { createSaveIt, photoOf } from '../saveit.mjs';

const quiet = () => {};
const PANEL = [6, 14, 18], RING = [255, 180, 60], GREY = [120, 120, 120];
const at = (px, x, y) => [...px.slice((y * WIDTH + x) * 4, (y * WIDTH + x) * 4 + 3)];
const greyPhoto = circle => ({ rgba: new Uint8Array(WIDTH * HEIGHT * 4).fill(120), circle });
const TABLE = { landmark: 'the table', room: 'the classroom' };
const SIGHTING = '69f24f92-bc4e-4bd6-b537-f01f526d4693';

const seen = { state: 'seen', item: 'watch', sighting_id: SIGHTING, photo: 'crops/home/watch/x.jpg', room: 'the classroom', landmark: 'the table', query_id: 'q1' };

/** A fake backend: `routes` maps a path prefix to (url, init) => Response-like. Records every request. */
function backend(routes) {
  const calls = [];
  const fetchImpl = async (url, init = {}) => {
    calls.push({ url: String(url), headers: init.headers ?? {} });
    const path = String(url).replace('http://backend.test', '');
    const hit = Object.keys(routes).find(prefix => path.startsWith(prefix));
    if (!hit) return { ok: false, status: 404, json: async () => ({}) };
    return routes[hit](path);
  };
  return { calls, fetchImpl };
}
const json = body => ({ ok: true, status: 200, json: async () => body });

test('photoOf: a photo only when the answer says where the thing is now', () => {
  assert.equal(photoOf(seen), SIGHTING);
  assert.equal(photoOf({ ...seen, photo: null }), null);
  assert.equal(photoOf({ ...seen, state: 'not_there_anymore' }), null); // it has left that place
  assert.equal(photoOf({ ...seen, state: 'carried' }), null);
  assert.equal(photoOf(null), null);
});

test('photo layout: the photo gets everything FaceTime shows above a one-line band', () => {
  const one = photoLayout(TABLE);
  assert.deepEqual(one.lines, ['TABLE']); // the landmark alone: the photo shows the room
  assert.equal(one.bandY, 590);
  assert.deepEqual(one.safe, [FACETIME_CROP, 0, WIDTH - FACETIME_CROP, 590]);
  const two = photoLayout({ landmark: 'the table beside your bed', room: 'your bedroom' });
  assert.deepEqual(two.lines, ['TABLE BESIDE', 'YOUR BED']);
  assert.equal(two.bandY, 500); // a long name still gets its two lines
  assert.deepEqual(photoLayout({ room: 'the classroom' }).lines, ['CLASSROOM']); // no landmark: the room
});

test('photo card: the photo above, the place name on a dark band, a ring on the thing', () => {
  const view = { kind: 'photo', ...TABLE, photo: greyPhoto([640, 290, 95]) };
  const px = renderCard(view, 'idle');
  assert.equal(px.length, WIDTH * HEIGHT * 4);
  assert.deepEqual(at(px, 300, 300), GREY);             // the photo itself
  assert.deepEqual(at(px, 640, 290), GREY);             // the middle of the ring is the thing, untouched
  assert.deepEqual(at(px, 640 + 95, 290), RING);        // the ring
  assert.deepEqual(at(px, 640 + 95 + 9, 290), PANEL);   // its dark edge
  assert.deepEqual(at(px, 640, 580), GREY);             // the photo reaches down to the band
  assert.deepEqual(at(px, 10, 600), PANEL);             // the band, full width
  assert.deepEqual(at(px, 1270, 715), PANEL);
  let white = 0;
  for (let x = SAFE_X; x < WIDTH - SAFE_X; x++) if (at(px, x, 630).every(v => v === 255)) white++;
  assert.ok(white > 50, 'the place name is on the band, inside the safe width');
  for (let y = 590; y < HEIGHT; y++) for (const x of [0, 80, 159, 1121, 1200, 1279]) assert.deepEqual(at(px, x, y), PANEL); // no text where FaceTime crops
  assert.equal(view.photo.rgba[0], 120, 'the photo is not drawn on: it is reused for every frame');
});

test('photo card: the ring has a second, wider beat, and the light still shows who is talking', () => {
  const view = { kind: 'photo', ...TABLE, photo: greyPhoto([640, 290, 95]) };
  const steady = renderCard(view, 'idle', false), wide = renderCard(view, 'idle', true);
  assert.deepEqual(at(steady, 640 + 105, 290), PANEL);
  assert.deepEqual(at(wide, 640 + 105, 290), RING);
  const lightX = WIDTH - FACETIME_CROP - 56; // top right of what FaceTime shows, away from the thing
  assert.deepEqual(at(renderCard(view, 'speaking'), lightX, 56), [255, 50, 50]);
  assert.deepEqual(at(renderCard(view, 'listening'), lightX, 56), [200, 255, 215]);
  assert.deepEqual(at(renderCard(view, 'idle'), lightX, 22), PANEL); // the light sits on its own dark disc
  assert.deepEqual(at(renderCard(view, 'speaking'), 640, 64), GREY); // nothing over the middle of the photo
});

test('photo card: no ring without a circle; no usable photo falls back to the place card', () => {
  const plain = renderCard({ kind: 'photo', ...TABLE, photo: greyPhoto(null) }, 'idle');
  assert.deepEqual(at(plain, 640 + 95, 290), GREY);
  const broken = renderCard({ kind: 'photo', ...TABLE, photo: { rgba: new Uint8Array(10) } }, 'idle');
  assert.deepEqual([...broken], [...renderCard({ kind: 'place', ...TABLE }, 'idle')]);
  assert.equal(isPhoto(greyPhoto(null)), true);
  assert.equal(isPhoto({ rgba: new Uint8Array(10) }), false);
  assert.equal(isPhoto(null), false);
});

test('decodePhoto: a JPEG from the backend becomes a full frame of pixels, whatever its size', async () => {
  const jpeg = await sharp({ create: { width: 640, height: 360, channels: 3, background: { r: 200, g: 30, b: 30 } } }).jpeg().toBuffer();
  const photo = await decodePhoto({ jpeg, circle: [640, 290, 95] });
  assert.equal(isPhoto(photo), true);
  assert.deepEqual(photo.circle, [640, 290, 95]);
  const [r, g, b, a] = photo.rgba.slice(0, 4);
  assert.ok(r > 180 && g < 60 && b < 60 && a === 255);
  await assert.rejects(decodePhoto({ jpeg: Buffer.from('not an image') }));
});

test('loadPhoto: asks the backend for the moment, sized for the card, with the app token', async () => {
  const { calls, fetchImpl } = backend({
    '/moments/': () => ({ ok: true, status: 200, headers: new Headers({ 'x-item-circle': '640,294,95' }), arrayBuffer: async () => new Uint8Array([255, 216, 255]).buffer }),
  });
  const s = createSaveIt({ backendUrl: 'http://backend.test/', appToken: 'tok', fetchImpl, log: quiet });
  const photo = await s.loadPhoto(SIGHTING, { width: 1280, height: 720, safe: [100, 0, 1180, 590] });
  assert.deepEqual([...photo.jpeg], [255, 216, 255]);
  assert.deepEqual(photo.circle, [640, 294, 95]);
  assert.equal(calls[0].url, `http://backend.test/moments/${SIGHTING}/photo?w=1280&h=720&safe=100,0,1180,590`);
  assert.equal(calls[0].headers.Authorization, 'Bearer tok');
});

test('loadPhoto: no ring header means no ring; a missing photo or a dead backend means no photo, never an error', async () => {
  const noRing = backend({ '/moments/': () => ({ ok: true, status: 200, headers: new Headers(), arrayBuffer: async () => new ArrayBuffer(3) }) });
  const s1 = createSaveIt({ backendUrl: 'http://backend.test', fetchImpl: noRing.fetchImpl, log: quiet });
  assert.equal((await s1.loadPhoto(SIGHTING, { width: 1280, height: 720, safe: [1, 2, 3, 4] })).circle, null);

  const logged = [];
  const s2 = createSaveIt({ backendUrl: 'http://backend.test', fetchImpl: backend({}).fetchImpl, log: e => logged.push(e) });
  assert.equal(await s2.loadPhoto(SIGHTING, { width: 1280, height: 720, safe: [1, 2, 3, 4] }), null);
  assert.equal(logged.at(-1).tool, 'photo');
  assert.equal(logged.at(-1).ok, false);

  const s3 = createSaveIt({ backendUrl: 'http://backend.test', fetchImpl: async () => { throw new Error('down'); }, log: quiet });
  assert.equal(await s3.loadPhoto(SIGHTING, { width: 1280, height: 720, safe: [1, 2, 3, 4] }), null);
  assert.equal(await s3.loadPhoto(null, { width: 1280, height: 720, safe: [1, 2, 3, 4] }), null);
  assert.equal(await createSaveIt({ log: quiet }).loadPhoto(SIGHTING, { width: 1280, height: 720, safe: [1, 2, 3, 4] }), null); // fake home
});

test('find answers carry the sighting whose photo to show', async () => {
  const { fetchImpl } = backend({ '/find': () => json({ sentence: 'I last saw your watch on the table just now.', result: seen }) });
  const s = createSaveIt({ backendUrl: 'http://backend.test', fetchImpl, log: quiet });
  const out = await s.findObject('watch');
  assert.equal(out.sighting, SIGHTING);
  assert.deepEqual(out.suggested, { room: 'the classroom', landmark: 'the table' });
});

test('find_by_description: one clear fit is answered like find_object, and the model is told which thing', async () => {
  const { calls, fetchImpl } = backend({
    '/describe': () => json({ sentence: 'I last saw your watch on the table just now.', result: seen, item: 'watch', candidates: [{ item: 'watch', sighting_id: SIGHTING, distance: 0.34 }] }),
    '/find': () => json({ sentence: 'I last saw your watch on the table just now.', result: seen }),
  });
  const s = createSaveIt({ backendUrl: 'http://backend.test', fetchImpl, log: quiet });
  s.state.known = [{ item: 'watch', aliases: [], sentence: 'x' }];
  const out = await s.findByDescription('the silver one I wear on my wrist');
  assert.equal(out.say, 'They mean their watch. I last saw your watch on the table just now.');
  assert.deepEqual(out.suggested, { room: 'the classroom', landmark: 'the table' });
  assert.equal(out.sighting, SIGHTING);
  assert.equal(s.state.item, 'watch'); // "it's not there" now means the watch
  assert.equal(calls[0].url, 'http://backend.test/describe?q=the%20silver%20one%20I%20wear%20on%20my%20wrist&channel=facetime');
  // The reply then names the watch; that is the same exchange, not a second question to log.
  assert.equal(await s.noteSaid('Ah, your watch! I last saw your watch on the table just now.'), null);
  assert.equal(calls.length, 1);
});

test('find_by_description: "which one?" or "I do not know it" point the card nowhere', async () => {
  const which = backend({ '/describe': () => json({ sentence: 'Do you mean your green bag or your brown bag?', result: null, item: null, candidates: [{ item: 'green bag' }, { item: 'brown bag' }] }) });
  const s1 = createSaveIt({ backendUrl: 'http://backend.test', fetchImpl: which.fetchImpl, log: quiet });
  assert.deepEqual(await s1.findByDescription('my bag'), { say: 'Do you mean your green bag or your brown bag?', suggested: null });

  const unknown = backend({ '/describe': () => json({ sentence: "I don't know your wallet yet, but your family can teach me.", result: { state: 'unknown_item', heard: 'wallet' }, item: null, candidates: [] }) });
  const s2 = createSaveIt({ backendUrl: 'http://backend.test', fetchImpl: unknown.fetchImpl, log: quiet });
  const out = await s2.findByDescription('my wallet');
  assert.match(out.say, /don't know your wallet yet/);
  assert.equal(out.suggested, null);
  assert.equal(out.sighting, undefined);
});

test('find_by_description: a dead backend gives the fallback; the fake home answers like find_object', async () => {
  const s = createSaveIt({ backendUrl: 'http://backend.test', fetchImpl: async () => { throw new Error('down'); }, log: quiet });
  assert.deepEqual(await s.findByDescription('the silver one'), { say: "I'm not sure right now.", suggested: null });
  const fake = createSaveIt({ log: quiet });
  assert.match((await fake.findByDescription('my specs')).say, /glasses/);
});

test('instructions: the description tool is offered only when the backend can search', () => {
  const known = [{ item: 'watch', aliases: [], sentence: 'I last saw your watch on the table just now.' }];
  const withTool = buildInstructions(known, { describe: true });
  assert.match(withTool, /call find_by_description with their own words/);
  assert.match(withTool, /If they name something that is not on this list, tell them kindly/);
  assert.match(withTool, /a photo of the thing where it was last seen, with a ring around it/);
  assert.match(withTool, /never describe what is in it/);
  assert.doesNotMatch(buildInstructions(known), /find_by_description/);
  assert.match(buildInstructions([], { describe: true }), /find_object.*find_by_description/s);
});
