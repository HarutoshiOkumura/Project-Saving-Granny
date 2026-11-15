// What the caller sees: the agent's camera track (docs/DASHBOARD.md "FaceTime video card").
// 1280x720, but FaceTime on an iPhone held upright showed only about the middle 84% of the width (test call,
// 14 Nov), so everything readable stays inside SAFE_X: at most 2 lines of at most 16 characters, 70 px white
// text on a full-width dark band.
// Plain JavaScript with a built-in 5x7 pixel font, so it needs no canvas library or system fonts.
// Frames are rendered once per change and reused, so sending 10 frames a second costs almost nothing.

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

/**
 * Render the card. `mode` sets the marker: 'speaking' (orange, pulsed by the caller of this function while
 * Save It talks), 'listening' (steady green: the caller's voice is coming in, see voice-meter.mjs), or 'idle'.
 * No word under the light (Tom, 14 Nov): the light alone, coming on the moment they speak.
 * true and false still mean 'speaking' and 'idle'.
 */
export function renderCard(view, mode = 'idle') {
  if (mode === true) mode = 'speaking';
  if (mode === false) mode = 'idle';
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
