// A moment photo from the backend (GET /moments/{id}/photo, a JPEG already sized for the card) into the raw
// pixels card.mjs draws on. sharp is the one image library here; @livekit/agents already ships it.
// It is loaded on first use, not at start-up: if it cannot load on some machine, calls still work and
// the card simply stays on the place name.

import { HEIGHT, WIDTH } from './card.mjs';

let sharpSoon;

/** JPEG bytes -> { rgba, circle } for renderCard's photo view. Throws when the bytes are not an image. */
export async function decodePhoto({ jpeg, circle = null }) {
  sharpSoon ??= import('sharp').then(module => module.default);
  const sharp = await sharpSoon;
  // The backend sends exactly WIDTH x HEIGHT; resizing anyway means a wrong size can never tear the frame.
  const { data, info } = await sharp(jpeg).resize(WIDTH, HEIGHT, { fit: 'fill' }).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  if (info.width !== WIDTH || info.height !== HEIGHT || info.channels !== 4) throw new Error(`photo decoded to ${info.width}x${info.height}x${info.channels}`);
  return { rgba: new Uint8Array(data.buffer, data.byteOffset, data.byteLength), circle };
}
