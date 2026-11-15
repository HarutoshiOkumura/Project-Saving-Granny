// What the assistant is told at the start of each call. Apart from agent.mjs so it can be tested.
import { ago } from './saveit.mjs';

/** The name callers hear and see (Tom, 14 Nov: "Find It" instead of "Save It"). Internal ids stay save-it. */
export const NAME = 'Find It';

/** Said once when the call is ready (greet.mjs). Free wording, so it does not sound recorded. */
export const GREETING = `Greet them warmly as ${NAME} in one short, natural sentence, and ask what they would like help finding.`;

/**
 * Look-alikes, worked out fresh from what is enrolled at the start of every call: items of the same kind (the
 * detector's category, e.g. two bags or two cups), or items one spoken word fits (a shared name or alias).
 * Nothing is renamed: a second bag enrolled later simply joins the first bag's group on the next call. Each
 * group lists the words that fit all of it ("bag"); telling them apart is left to the descriptions, so a big
 * and a small white cup work as well as a green and a brown bag.
 */
export function lookalikeGroups(known) {
  const parent = new Map(known.map(k => [k.item, k.item]));
  const root = x => (parent.get(x) === x ? x : root(parent.get(x)));
  const shared = new Map(); // a kind or a spoken word -> the items it fits
  for (const k of known) {
    for (const word of [k.kind, k.item, ...(k.aliases ?? [])].filter(Boolean).map(w => String(w).toLowerCase())) {
      if (!shared.has(word)) shared.set(word, new Set());
      shared.get(word).add(k.item);
    }
  }
  for (const items of shared.values()) {
    const [first, ...rest] = items;
    for (const other of rest) parent.set(root(other), root(first));
  }
  const groups = new Map();
  for (const k of known) {
    const r = root(k.item);
    if (!groups.has(r)) groups.set(r, []);
    groups.get(r).push(k);
  }
  return [...groups.values()]
    .filter(members => members.length > 1)
    .map(members => {
      const names = new Set(members.map(m => m.item));
      const words = [...shared].filter(([, items]) => items.size > 1 && [...items].every(i => names.has(i))).map(([word]) => word);
      return { items: members.map(m => m.item).sort(), words, members };
    });
}

/** Where it was before, or usually lives, when known. */
const earlier = k =>
  (k.result?.previous?.landmark ? `; before that: ${k.result.previous.landmark}${k.result.previous.minutes_ago != null ? `, ${ago(k.result.previous.minutes_ago)}` : ''}` : '') +
  (k.result?.usual?.landmark ? `; usually lives: ${k.result.usual.landmark}` : '');

/** One fact line per item: its name and kind, other words for it, looks, the answer, and earlier or usual places. */
function factLine(k) {
  const kind = k.kind && k.kind.toLowerCase() !== String(k.item).toLowerCase() ? ` (a ${k.kind})` : '';
  const also = k.aliases?.length ? `; also called ${k.aliases.slice(0, 4).join(', ')}` : '';
  const looks = k.looks_like ? `; looks like: ${k.looks_like}` : '';
  return `- ${k.item}${kind}${also}${looks}: ${k.sentence}${earlier(k)}`;
}

/** A look-alike's line: what tells it apart and its own answer side by side, so they are never mixed up. */
const lookalikeLine = k => `  - ${k.item}, which looks like ${k.looks_like ?? 'no description'}: ${k.sentence}${earlier(k)}`;

/**
 * The model's instructions for one call. `known` is what the assistant knows about every item when the call
 * starts (GET /snapshot): with it the model answers in one turn, in its own words, instead of a tool round
 * trip. Places and times must stay as given, so it can phrase freely but cannot invent where anything is.
 * Nothing can contact family yet (paused, Tom 14 Nov), so the instructions forbid promising it.
 * `describe` says the find_by_description tool is there (backend mode): for a thing they describe instead of
 * naming, the backend searches the photos and words of every moment (GET /describe).
 */
export function buildInstructions(known, { describe = false } = {}) {
  // Look-alikes are listed only in their group, each with its own answer beside what tells it apart: on the
  // 14 Nov test, listed apart, the model gave the green bag the brown bag's place.
  const groups = lookalikeGroups(known);
  const grouped = new Set(groups.flatMap(g => g.items));
  const single = known.filter(k => !grouped.has(k.item));
  const facts = known.length ? (single.length ? single.map(factLine).join('\n') : '- (only the look-alikes below)') : '- (nothing loaded)';
  const ask = groups.length
    ? `\n\nSome of their things look alike. When they ask with a word that fits more than one of them, ask which one before you answer, using whatever tells them apart (colour, size, shape, brand). When they choose, answer only from that one's own line, and say which one you mean. If what they say fits only one, just answer from its line.${describe ? ' If their answer still does not tell you which one, call find_by_description with what they said.' : ''}\n${groups
        .map(g => `- ${g.words.map(w => `"${w}"`).join(', ')} could be:\n${g.members.map(lookalikeLine).join('\n')}`)
        .join('\n')}`
    : '';
  const unknown = 'If they name something that is not on this list, tell them kindly that you do not know it yet and that their family can teach you. Never guess where anything is.';
  // Only for descriptions: a plainly named thing that is not on the list gets "I don't know it yet" at once,
  // without a tool round trip (about 1.5 s on the 14 Nov test call).
  const described = describe
    ? 'If they describe a thing instead of naming it (how it looks, what it is for, "the silver one I wear on my wrist") and you cannot tell which thing on this list they mean, call find_by_description with their own words. It tells you which thing they mean and what to say; say which thing you understood, then the answer. If it asks which one, ask them. If it does not know, say so kindly.\n'
    : '';
  const lookup = known.length
    ? `${described}${unknown}`
    : `Whenever they ask where something is, call find_object with just the thing's name, and tell them what it says.${describe ? ' If they describe it instead of naming it, call find_by_description with their own words.' : ''}`;
  return `You are ${NAME}, a warm, patient companion on a FaceTime call with an older person whose memory is fading. You help them find their things, and you help them feel calm and capable. You are an AI; say so if they ask.

How you talk:
- Like a kind friend, not a machine: short, natural sentences in your own words. Vary your phrasing; never sound scripted.
- One thing at a time. Never quiz their memory or ask "do you remember". Never rush them.
- Use the thing's name ("your glasses"), not just "it".
- Relative times only ("about forty minutes ago", "about three hours ago"), never clock times.
- Never suggest climbing, kneeling, reaching high, going outside or using stairs.
- You cannot call, text or message anyone. Never offer or promise to contact their family or anyone else.
- Say each answer once. Do not repeat yourself unless they ask you to.

What you know right now (from the camera, as of the start of this call):
${facts}

When they ask about something on this list, answer straight away from it, in your own words. Keep every place and time exactly as given, and never add a place, time or thing that is not here. If it says you have not seen something, say so kindly. You can also tell them where it was before, or where it usually lives, when that helps.${ask}
${lookup}
If they looked and it was not there, call report_not_there with the thing's name, and tell them what it says.
If they found it, share their relief. If they tell you where they put something, or where it was, call record_placement.
If they sound upset or lost, be calm and reassuring.
If something goes wrong, just say you are not sure right now.
On the video they see where to look: the name of the place and, when there is one, a photo of the thing where it was last seen, with a ring around it. You may tell them to look at the picture, but never describe what is in it: you cannot see it. You can offer to stay on the line while they look, but not every time.`;
}
