// What the assistant is told at the start of each call. Apart from agent.mjs so it can be tested.
import { ago } from './saveit.mjs';

/** The name callers hear and see (Tom, 14 Nov: "Find It" instead of "Save It"). Internal ids stay save-it. */
export const NAME = 'Find It';

/** Said once when the call is ready (greet.mjs). Free wording, so it does not sound recorded. */
export const GREETING = `Greet them warmly as ${NAME} in one short, natural sentence, and ask what they would like help finding.`;

/**
 * Spoken words that fit more than one item, grouped: "bag" fits `bag` (green) and `brown bag`. Built from names and
 * aliases, so the model is told outright to ask "which one?". On the 14 Nov test call it asked for the water bottle
 * but not the bag, whose item is named plain "bag".
 */
export function sharedWords(known) {
  const byWord = new Map();
  for (const k of known) {
    for (const word of [k.item, ...(k.aliases ?? [])].map(w => String(w).toLowerCase())) {
      if (!byWord.has(word)) byWord.set(word, new Set());
      byWord.get(word).add(k.item);
    }
  }
  const groups = new Map(); // one line per set of items: "water bottle", "bottle" -> both bottles
  for (const [word, items] of byWord) {
    if (items.size < 2) continue;
    const key = [...items].sort().join('|');
    if (!groups.has(key)) groups.set(key, { words: [], items: [...items].sort() });
    groups.get(key).words.push(word);
  }
  return [...groups.values()];
}

/** How to name an item so it stands apart: an item called plain "bag", sharing that word, is "the green bag". */
export function label(k, shared) {
  const plain = shared.some(g => g.items.includes(k.item) && g.words.includes(String(k.item).toLowerCase()));
  if (!plain || !k.color || String(k.item).toLowerCase().includes(String(k.color).toLowerCase())) return k.item;
  return `${k.color} ${k.item}`;
}

/** One fact line per item: names, looks, the current answer, and where it was before or usually lives. */
function factLine(k, shared) {
  const name = label(k, shared);
  const called = name !== k.item ? `; its name is "${k.item}"` : '';
  const also = k.aliases?.length ? `; also called ${k.aliases.slice(0, 4).join(', ')}` : '';
  const looks = k.looks_like ? `; looks like: ${k.looks_like}` : '';
  const prev = k.result?.previous?.landmark ? `; before that: ${k.result.previous.landmark}${k.result.previous.minutes_ago != null ? `, ${ago(k.result.previous.minutes_ago)}` : ''}` : '';
  const usual = k.result?.usual?.landmark ? `; usually lives: ${k.result.usual.landmark}` : '';
  return `- ${name}${called}${also}${looks}: ${k.sentence}${prev}${usual}`;
}

/**
 * The model's instructions for one call. `known` is what the assistant knows about every item when the call
 * starts (GET /snapshot): with it the model answers in one turn, in its own words, instead of a tool round
 * trip. Places and times must stay as given, so it can phrase freely but cannot invent where anything is.
 * Nothing can contact family yet (paused, Tom 14 Nov), so the instructions forbid promising it.
 */
export function buildInstructions(known) {
  const shared = sharedWords(known);
  const facts = known.length ? known.map(k => factLine(k, shared)).join('\n') : '- (nothing loaded)';
  const byItem = new Map(known.map(k => [k.item, label(k, shared)]));
  const ask = shared.length
    ? `\nSome words fit more than one of their things. When they use one of these, ask which one by how it looks before you answer, then use that one's facts:\n${shared
        .map(g => `- ${g.words.map(w => `"${w}"`).join(', ')}: ${g.items.map(i => `the ${byItem.get(i) ?? i}`).join(' or ')}`)
        .join('\n')}\nIf they say a word that fits only one thing (like "brown bag"), just answer.`
    : '';
  const lookup = known.length
    ? 'If they ask about something that is not on this list, tell them kindly that you do not know it yet and that their family can teach you. Never guess where anything is.'
    : "Whenever they ask where something is, call find_object with just the thing's name, and tell them what it says.";
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
They can see a card on the video showing where to look. You can offer to stay on the line while they look, but not every time.`;
}
