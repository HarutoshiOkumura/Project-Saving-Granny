// Save It on FaceTime: Chert bridges the call into a LiveKit room; this agent answers in it.
// Voice: Gemini Live (speech in, speech out). Answers: saveit.mjs (backend /find, or the fake home).
// Video: card.mjs shows where to look. Rules from docs/CHERT.md, docs/RETRIEVAL.md and docs/DASHBOARD.md.

import './env.mjs'; // first: .env.local wins over the terminal's variables (VS Code injects the repo's .env)
import { appendFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { AutoSubscribe, defineAgent, llm, voice } from '@livekit/agents';
import * as google from '@livekit/agents-plugin-google';
import { LocalVideoTrack, TrackSource, VideoBufferType, VideoFrame, VideoSource } from '@livekit/rtc-node';
import { FPS, HEIGHT, renderCard, WIDTH } from './card.mjs';
import { runAgent } from './chert-rooms.mjs';
import { greetOnBridgeReady } from './greet.mjs';
import { createSaveIt } from './saveit.mjs';

const FAMILY = process.env.FAMILY_NAME || 'June';

// Gemini Live model. Keep a 2.5 native-audio model: in @livekit/agents-plugin-google 1.8.0, any model with
// "3.1" in its name rejects generateReply, so the greeting would fail and Chert would end the call.
const MODEL = process.env.GEMINI_LIVE_MODEL || 'gemini-2.5-flash-native-audio-preview-12-2025';
const VOICE = process.env.GEMINI_VOICE || 'Aoede';

// Optional, and not confirmed for this model in Google's docs (checked 14 Nov): GEMINI_THINKING_BUDGET=0 may
// stop the model thinking before it answers. Unset means the model's default. Compare ttft_ms in the call log.
const THINKING_BUDGET = process.env.GEMINI_THINKING_BUDGET;

// One JSON line per event, to the console and to logs/calls.jsonl (gitignored), so a test call can be
// measured afterwards. Timings and tool names always; what was said only with LOG_TRANSCRIPTS=1 (testing).
const LOG_FILE = new URL('./logs/calls.jsonl', import.meta.url);
const TRANSCRIPTS = process.env.LOG_TRANSCRIPTS === '1';
function callLog(entry) {
  const line = JSON.stringify({ t: new Date().toISOString(), ...entry });
  console.log(`[save-it] ${line}`);
  try {
    mkdirSync(new URL('./', LOG_FILE), { recursive: true });
    appendFileSync(LOG_FILE, `${line}\n`);
  } catch {
    // logging must never break a call
  }
}

const instructions = `You are Save It, a calm, kind helper on a FaceTime call with an older person who has memory loss.
You help them find their belongings. You are an AI; say so if they ask.

How you talk:
- Speak slowly and warmly. Keep your own sentences short: one idea each, about twenty words at most.
- Say the item's name every time ("your glasses"). Never say just "it" or "them".
- One instruction per turn. Never quiz their memory. Never ask "do you remember".
- Never tell them to climb, kneel, reach high, go outdoors or use stairs. Offer to call ${FAMILY} instead.
- Use relative times only, like "about an hour ago". Never say a clock time.

Use your tools. Never guess.
- They ask where something is: call find_object with their words. Then say the tool's sentence exactly, word for word, even when it is long. Do not shorten it or add to it.
- Never name a place that a tool did not give you.
- After you say where to look, ask: "Would you like me to stay on the line while you look?"
- They looked and it was not there: call report_not_there. Say its sentence exactly.
- They found it: say you are glad. If they say where it was, call record_placement with kind "found".
- They tell you where they put something: call record_placement with kind "placed". Say its sentence exactly.
- They ask about people or their day ("Who is ${FAMILY}?"): call recall_life_fact. Say its sentence exactly.
- They sound upset, hurt or lost, or ask for family: call alert_caregiver. Say its sentence exactly.
- If a tool gives no answer, say: "I'm not sure. Let me check with ${FAMILY}."
The caller can see a card on the video showing the place to look.`;

// Said once, as soon as FaceTime is ready (greet.mjs). Chert ends a silent call 10 s after bridge_ready.
const greeting = 'Say exactly this, warmly and slowly: "Hi, it\'s Save It. What can I help you find?"';

const agent = defineAgent({
  entry: async ctx => {
    await ctx.connect(undefined, AutoSubscribe.AUDIO_ONLY);
    // Chert prepares a warm room before a caller exists. Join promptly, but wait for the caller
    // before opening a paid model session or sending video (docs/CHERT.md "Warm room").
    const caller = await ctx.waitForParticipant();

    // Per-call read-side state lives here, not in the model.
    const saveIt = createSaveIt({ backendUrl: process.env.BACKEND_URL || '', appToken: process.env.APP_TOKEN || '', familyName: FAMILY, log: callLog });
    callLog({ event: 'call_start', answers_from: saveIt.mode === 'backend' ? process.env.BACKEND_URL : 'fake home (BACKEND_URL is empty)', thinking_budget: THINKING_BUDGET || 'default', transcripts: TRANSCRIPTS });

    // Video card: render on change, reuse frames. The marker pulses at 1 Hz while Save It speaks.
    const source = new VideoSource(WIDTH, HEIGHT);
    const track = LocalVideoTrack.createVideoTrack('save-it-card', source);
    let frames = { off: renderCard({ kind: 'idle' }, false), on: renderCard({ kind: 'idle' }, true) };
    let speaking = false;
    const show = view => { frames = { off: renderCard(view, false), on: renderCard(view, true) }; };
    const send = () => {
      const lit = speaking && Math.floor(Date.now() / 500) % 2 === 0;
      source.captureFrame(new VideoFrame(lit ? frames.on : frames.off, WIDTH, HEIGHT, VideoBufferType.RGBA));
    };
    send();
    await ctx.room.localParticipant.publishTrack(track, { source: TrackSource.SOURCE_CAMERA });
    const timer = setInterval(send, 1000 / FPS);

    // Each tool returns the sentence to read verbatim, and updates the card when there is a place to show.
    // A where-is answer with no place clears the card, so it never shows a place from an earlier question.
    const reply = ({ say, suggested }, clearIfNoPlace = false) => {
      if (suggested) show({ kind: 'place', landmark: suggested.landmark, room: suggested.room });
      else if (clearIfNoPlace) show({ kind: 'idle' });
      return say;
    };
    const tools = [
      llm.tool({
        name: 'find_object',
        description: 'Find where one of the person\'s belongings is. Call this whenever they ask where something is.',
        parameters: { type: 'object', properties: { phrase: { type: 'string', description: 'Just the thing they are looking for, in their words, e.g. "glasses" or "my specs". Not the whole question.' } }, required: ['phrase'] },
        execute: async ({ phrase }) => reply(await saveIt.findObject(phrase), true),
      }),
      llm.tool({
        name: 'report_not_there',
        description: 'The person checked the place you suggested and the item was not there. Returns the next place to check.',
        execute: async () => reply(await saveIt.reportNotThere(), true),
      }),
      llm.tool({
        name: 'record_placement',
        description: 'The person says where they put something ("placed") or where they found it ("found").',
        parameters: {
          type: 'object',
          properties: {
            object_phrase: { type: 'string', description: 'The item, in their words.' },
            place_phrase: { type: 'string', description: 'Where it is, in their words.' },
            kind: { type: 'string', enum: ['placed', 'found'] },
          },
          required: ['object_phrase', 'place_phrase', 'kind'],
        },
        execute: async ({ object_phrase, place_phrase, kind }) => reply(await saveIt.recordPlacement(object_phrase, place_phrase, kind)),
      }),
      llm.tool({
        name: 'recall_life_fact',
        description: `Answer a question about the person's life, family or day, e.g. "Who is ${FAMILY}?" or "When are my pills?".`,
        parameters: { type: 'object', properties: { question: { type: 'string' } }, required: ['question'] },
        execute: async ({ question }) => reply(await saveIt.recallLifeFact(question)),
      }),
      llm.tool({
        name: 'alert_caregiver',
        description: `Tell ${FAMILY} that the person needs help: upset, hurt, lost, or asking for family.`,
        parameters: { type: 'object', properties: { reason: { type: 'string', description: 'A short reason, without personal details.' } }, required: ['reason'] },
        execute: async ({ reason }) => {
          show({ kind: 'text', text: `${FAMILY} is on the way` });
          return reply(await saveIt.alertCaregiver(reason));
        },
      }),
    ];

    const session = new voice.AgentSession({
      llm: new google.realtime.RealtimeModel({
        model: MODEL,
        voice: VOICE,
        ...(THINKING_BUDGET ? { thinkingConfig: { thinkingBudget: Number(THINKING_BUDGET) } } : {}),
      }),
    });
    // The call log's timeline: caller stops speaking (caller: listening) -> agent thinking -> agent speaking.
    session.on(voice.AgentSessionEventTypes.AgentStateChanged, event => {
      speaking = event.newState === 'speaking';
      callLog({ event: 'agent', state: event.newState });
    });
    session.on(voice.AgentSessionEventTypes.UserStateChanged, event => callLog({ event: 'caller', state: event.newState }));
    session.on(voice.AgentSessionEventTypes.UserInputTranscribed, event => {
      if (!event.isFinal) return;
      callLog({ event: 'heard', ...(TRANSCRIPTS ? { text: event.transcript } : { words: event.transcript.split(/\s+/).filter(Boolean).length }) });
    });
    session.on(voice.AgentSessionEventTypes.ConversationItemAdded, event => {
      if (event.item?.role === 'assistant') callLog({ event: 'said', ...(TRANSCRIPTS ? { text: event.item.textContent ?? '' } : {}) });
    });
    session.on(voice.AgentSessionEventTypes.MetricsCollected, event => {
      const m = event.metrics;
      if (m?.type === 'realtime_model_metrics') callLog({ event: 'model', ttft_ms: Math.round(m.ttftMs), duration_ms: Math.round(m.durationMs), cancelled: m.cancelled });
    });
    session.on(voice.AgentSessionEventTypes.Error, event => {
      const err = event.error?.error ?? event.error;
      callLog({ event: 'error', error: String(err?.message ?? err?.type ?? err ?? 'unknown').slice(0, 200) });
    });
    ctx.addShutdownCallback(async () => {
      callLog({ event: 'call_end' });
      clearInterval(timer);
      await session.close();
      await track.close();
      await source.close();
    });
    await session.start({
      room: ctx.room,
      agent: new voice.Agent({ instructions, tools }),
      record: false,
      inputOptions: {
        participantIdentity: caller.identity,
        audioEnabled: true,
        videoEnabled: false, // caller video: later, once Chert confirms caller capture on our line (D4)
        textEnabled: false,
        closeOnDisconnect: true,
        deleteRoomOnClose: false,
      },
      outputOptions: { audioEnabled: true, transcriptionEnabled: false },
    });
    // Greet once when chert dev reports FaceTime is ready (bridge_ready in the room metadata). Never on join.
    const stopGreeting = greetOnBridgeReady(ctx.room, () => {
      callLog({ event: 'greet' });
      return session.generateReply({ instructions: greeting });
    });
    ctx.addShutdownCallback(async () => stopGreeting());
  },
});

export default agent;

// Own LiveKit project when .env.local has its three LIVEKIT_ values; otherwise Chert rooms through chert dev.
runAgent(agent, { file: fileURLToPath(import.meta.url), agentName: process.env.AGENT_NAME || 'save-it' });
