// What the caller sees: the agent's camera track (docs/DASHBOARD.md "FaceTime video card").
// 1280x720, but FaceTime on an iPhone held upright showed only about the middle 84% of the width (test call,
// 14 Nov), so everything readable stays inside SAFE_X: at most 2 lines of at most 16 characters, 70 px white
// text on a full-width dark band.
// Plain JavaScript with a built-in 5x7 pixel font, so it needs no canvas library or system fonts.
// Frames are rendered once per change and reused, so sending 10 frames a second costs almost nothing.
// A photo card shows the moment the thing was last seen (photo.mjs decodes it; the backend sizes it).

export const WIDTH = 1280;
export const HEIGHT = 720;
export const FPS = 10;

const BG = [16, 40, 52], PANEL = [6, 14, 18], WHITE = [255, 255, 255], DIM = [140, 180, 190];
const RING = [255, 180, 60], DOT = [255, 50, 50]; // marker colours from DASHBOARD.md: Save It is talking
const HEAR_RING = [46, 204, 113], HEAR_DOT = [200, 255, 215]; // green: Save It hears the caller's voice
const MAX_CHARS = 16, BIG = 10, SMALL = 4;         // 7 rows x 10 = 70 px glyphs; 16 x 60 px fits the safe width
export const SAFE_X = 160;                         // margin each side that FaceTime may crop (it cut ~100 px)

const FONT = {
  A: ['.###.', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'], B: ['####.', '#...#', '#...#', '####.', '#...#', '#...#', '####.'],
  C: ['.###.', '#...#', '#....', '#....', '#....', '#...#', '.###.'], D: ['####.', '#...#', '#...#', '#...#', '#...#', '#...#', '####.'],
  E: ['#####', '#....', '#....', '####.', '#....', '#....', '#####'], F: ['#####', '#....', '#....', '####.', '#....', '#....', '#....'],
  G: ['.###.', '#...#', '#....', '#.###', '#...#', '#...#', '.####'], H: ['#...#', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'],
  I: ['.###.', '..#..', '..#..', '..#..', '..#..', '..#..', '.###.'], J: ['..###', '...#.', '...#.', '...#.', '...#.', '#..#.', '.##..'],
  K: ['#...#', '#..#.', '#.#..', '##...', '#.#..', '#..#.', '#...#'], L: ['#....', '#....', '#....', '#....', '#....', '#....', '#####'],
  M: ['#...#', '##.##', '#.#.#', '#.#.#', '#...#', '#...#', '#...#'], N: ['#...#', '#...#', '##..#', '#.#.#', '#..##', '#...#', '#...#'],
  O: ['.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'], P: ['####.', '#...#', '#...#', '####.', '#....', '#....', '#....'],
  Q: ['.###.', '#...#', '#...#', '#...#', '#.#.#', '#..#.', '.##.#'], R: ['####.', '#...#', '#...#', '####.', '#.#..', '#..#.', '#...#'],
  S: ['.####', '#....', '#....', '.###.', '....#', '....#', '####.'], T: ['#####', '..#..', '..#..', '..#..', '..#..', '..#..', '..#..'],
  U: ['#...#', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'], V: ['#...#', '#...#', '#...#', '#...#', '#...#', '.#.#.', '..#..'],
  W: ['#...#', '#...#', '#...#', '#.#.#', '#.#.#', '#.#.#', '.#.#.'], X: ['#...#', '#...#', '.#.#.', '..#..', '.#.#.', '#...#', '#...#'],
  Y: ['#...#', '#...#', '.#.#.', '..#..', '..#..', '..#..', '..#..'], Z: ['#####', '....#', '...#.', '..#..', '.#...', '#....', '#####'],
  0: ['.###.', '#...#', '#..##', '#.#.#', '##..#', '#...#', '.###.'], 1: ['..#..', '.##..', '..#..', '..#..', '..#..', '..#..', '.###.'],
  2: ['.###.', '#...#', '....#', '...#.', '..#..', '.#...', '#####'], 3: ['####.', '....#', '....#', '.###.', '....#', '....#', '####.'],
  4: ['...#.', '..##.', '.#.#.', '#..#.', '#####', '...#.', '...#.'], 5: ['#####', '#....', '####.', '....#', '....#', '#...#', '.###.'],
  6: ['.###.', '#....', '#....', '####.', '#...#', '#...#', '.###.'], 7: ['#####', '....#', '...#.', '..#..', '.#...', '.#...', '.#...'],
  8: ['.###.', '#...#', '#...#', '.###.', '#...#', '#...#', '.###.'], 9: ['.###.', '#...#', '#...#', '.####', '....#', '....#', '.###.'],
  '.': ['.....', '.....', '.....', '.....', '.....', '.##..', '.##..'], ',': ['.....', '.....', '.....', '.....', '.##..', '..#..', '.#...'],
  '?': ['.###.', '#...#', '....#', '...#.', '..#..', '.....', '..#..'], '!': ['..#..', '..#..', '..#..', '..#..', '..#..', '.....', '..#..'],
  '-': ['.....', '.....', '.....', '#####', '.....', '.....', '.....'], "'": ['..#..', '..#..', '.#...', '.....', '.....', '.....', '.....'],
  ':': ['.....', '.##..', '.##..', '.....', '.##..', '.##..', '.....'],
};

/** Word-wrap into at most `lines` lines of at most `max` characters (the last line is cut if needed). */
export function wrap(text, max = MAX_CHARS, lines = 2) {
  const out = [];
  let cur = '';
  for (const word of String(text).toUpperCase().split(/\s+/).filter(Boolean)) {
    const next = cur ? `${cur} ${word}` : word;
    if (next.length <= max) { cur = next; continue; }
    if (cur) out.push(cur);
    cur = word.slice(0, max);
  }
  if (cur) out.push(cur);
  return out.slice(0, lines);
}

/** The two big lines for a view: { kind: 'idle' } | { kind: 'place', landmark, room } | { kind: 'text', text }. */
export function cardLines(view) {
  if (view?.kind === 'place' && view.landmark) {
    const name = wrap(String(view.landmark).replace(/^the\s+/i, ''));
    return name.length === 1 && view.room ? [name[0], ...wrap(`in ${view.room}`, MAX_CHARS, 1)] : name;
  }
  if (view?.kind === 'place' && view.room) return wrap(String(view.room).replace(/^the\s+/i, '')); // room only, e.g. carried
  if (view?.kind === 'text' && view.text) return wrap(view.text);
  return ['WHAT CAN I', 'HELP YOU FIND?'];
}

/** How much of the card FaceTime on an upright iPhone cut off each side (test call, 14 Nov). */
export const FACETIME_CROP = 100;

/**
 * Where a photo card puts things: the place name on a dark band along the bottom and the photo above it.
 * `safe` = [left, top, right, bottom] is the part of the card the caller surely sees and no text covers:
 * the width FaceTime keeps, down to the band. The backend fits the whole photo inside it, never cut
 * (GET /moments/{id}/photo?safe=...): on the 15 Nov test call a photo that filled the card was zoomed in
 * so far that it showed too little of the room.
 * The band names the landmark only, on one line when it fits: the photo shows the room, and each line of
 * text takes 90 px from the photo.
 */
export function photoLayout(view) {
  const lines = view?.landmark ? wrap(String(view.landmark).replace(/^the\s+/i, '')) : cardLines({ ...view, kind: 'place' });
  const bandY = HEIGHT - (lines.length * 9 * BIG + 40);
  return { lines, bandY, safe: [FACETIME_CROP, 0, WIDTH - FACETIME_CROP, bandY] };
}

/** True when `photo` is { rgba, circle? } with a full frame of pixels: the only kind renderCard can show. */
export const isPhoto = photo => photo?.rgba?.length === WIDTH * HEIGHT * 4;

/**
 * Render the card. `mode` sets the marker: 'speaking' (orange, pulsed by the caller of this function while
 * Save It talks), 'listening' (steady green: the caller's voice is coming in, see voice-meter.mjs), or 'idle'.
 * No word under the light (Tom, 14 Nov): the light alone, coming on the moment they speak.
 * true and false still mean 'speaking' and 'idle'.
 *
 * { kind: 'photo', landmark, room, photo: { rgba, circle } } shows the moment the thing was last seen: the
 * whole photo above a band with the place name, and a ring on the thing (`circle` = [x, y, radius], or none). `pulse` draws the ring's other beat (wider and thinner); the caller alternates the two,
 * once a second at most (docs/DASHBOARD.md). Without a usable photo it is drawn as a place card.
 */
export function renderCard(view, mode = 'idle', pulse = false) {
  if (mode === true) mode = 'speaking';
  if (mode === false) mode = 'idle';
  if (view?.kind === 'photo') {
    if (isPhoto(view.photo)) return renderPhotoCard(view, mode, pulse);
    view = { ...view, kind: 'place' };
  }
  const px = new Uint8Array(WIDTH * HEIGHT * 4);
  fill(px, 0, 0, WIDTH, HEIGHT, BG);
  drawText(px, 'FIND IT', Math.round((WIDTH - textWidth('FIND IT', SMALL)) / 2), 48, SMALL, DIM);
  const lines = cardLines(view);
  const lineH = 9 * BIG, panelH = lines.length * lineH + 64, panelY = Math.round((HEIGHT - panelH) / 2) - 20;
  fill(px, 0, panelY, WIDTH, panelH, PANEL); // full width: cropping its ends looks the same
  lines.forEach((line, i) => drawText(px, line, Math.round((WIDTH - textWidth(line, BIG)) / 2), panelY + 32 + i * lineH, BIG, WHITE));
  const cx = WIDTH / 2, cy = HEIGHT - 100;
  const [ring, dot] = mode === 'speaking' ? [RING, DOT] : mode === 'listening' ? [HEAR_RING, HEAR_DOT] : [PANEL, DIM];
  circle(px, cx, cy, 26, ring);
  circle(px, cx, cy, 14, dot);
  return px;
}

function renderPhotoCard(view, mode, pulse) {
  const { lines, bandY } = photoLayout(view);
  const px = new Uint8Array(view.photo.rgba); // a copy: the same photo is drawn on for every frame
  if (view.photo.circle) {
    const [x, y, radius] = view.photo.circle.map(Math.round);
    const [r, thick] = pulse ? [radius + 10, 8] : [radius, 12];
    ring(px, x, y, r, thick + 8, PANEL); // a dark edge, so the ring shows on a pale table too
    ring(px, x, y, r, thick, RING);
  }
  fill(px, 0, bandY, WIDTH, HEIGHT - bandY, PANEL);
  lines.forEach((line, i) => drawText(px, line, Math.round((WIDTH - textWidth(line, BIG)) / 2), bandY + 24 + i * 9 * BIG, BIG, WHITE));
  // The talking and listening light, on its own dark disc so it reads on any photo, in the top right corner
  // of what FaceTime shows: out of the way of the thing, which sits in the middle of its photo.
  const cx = WIDTH - FACETIME_CROP - 56, cy = 56;
  const [lightRing, dot] = mode === 'speaking' ? [RING, DOT] : mode === 'listening' ? [HEAR_RING, HEAR_DOT] : [PANEL, DIM];
  circle(px, cx, cy, 40, PANEL);
  circle(px, cx, cy, 26, lightRing);
  circle(px, cx, cy, 14, dot);
  return px;
}

export const textWidth = (text, scale) => Math.max(0, String(text).length * 6 * scale - scale);

function drawText(px, text, x0, y0, scale, color) {
  [...String(text).toUpperCase()].forEach((ch, n) => {
    const glyph = FONT[ch];
    if (!glyph) return; // spaces and unknown characters stay blank
    glyph.forEach((row, gy) => {
      for (let gx = 0; gx < 5; gx++) if (row[gx] === '#') fill(px, x0 + (n * 6 + gx) * scale, y0 + gy * scale, scale, scale, color);
    });
  });
}

function fill(px, x0, y0, w, h, [r, g, b]) {
  const x1 = Math.min(WIDTH, x0 + w), y1 = Math.min(HEIGHT, y0 + h);
  for (let y = Math.max(0, y0); y < y1; y++) {
    for (let x = Math.max(0, x0); x < x1; x++) {
      const i = (y * WIDTH + x) * 4;
      px[i] = r; px[i + 1] = g; px[i + 2] = b; px[i + 3] = 255;
    }
  }
}

function circle(px, cx, cy, radius, color) {
  for (let y = -radius; y <= radius; y++) {
    const half = Math.floor(Math.sqrt(radius * radius - y * y));
    fill(px, cx - half, cy + y, half * 2 + 1, 1, color);
  }
}

/** A ring `thickness` wide, centred on the circle of `radius` (the middle stays as it was). */
function ring(px, cx, cy, radius, thickness, color) {
  const outer = radius + thickness / 2, inner = Math.max(0, radius - thickness / 2);
  for (let y = -Math.floor(outer); y <= outer; y++) {
    const out = Math.floor(Math.sqrt(outer * outer - y * y));
    const hole = Math.abs(y) < inner ? Math.ceil(Math.sqrt(inner * inner - y * y)) : 0;
    if (!hole) { fill(px, cx - out, cy + y, out * 2 + 1, 1, color); continue; }
    fill(px, cx - out, cy + y, out - hole + 1, 1, color);
    fill(px, cx + hole, cy + y, out - hole + 1, 1, color);
  }
}
