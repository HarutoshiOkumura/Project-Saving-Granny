// Save It on FaceTime: Chert bridges the call into a LiveKit room; this agent answers in it.
// Voice: Gemini Live (speech in, speech out). Answers: saveit.mjs (backend /find, or the fake home).
// Video: card.mjs shows where to look: the place name, then the photo of the moment the thing was last seen
// there, with a ring around it. Rules from docs/CHERT.md, docs/RETRIEVAL.md and docs/DASHBOARD.md.

import './env.mjs'; // first: .env.local wins over the terminal's variables (VS Code injects the repo's .env)
import { appendFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { AutoSubscribe, defineAgent, llm, voice } from '@livekit/agents';
import * as google from '@livekit/agents-plugin-google';
import { AudioStream, LocalVideoTrack, RoomEvent, TrackKind, TrackSource, VideoBufferType, VideoFrame, VideoSource } from '@livekit/rtc-node';
import { FPS, HEIGHT, photoLayout, renderCard, WIDTH } from './card.mjs';
import { runAgent } from './chert-rooms.mjs';
import { greetOnBridgeReady } from './greet.mjs';
import { GUIDE_TOOL, createGuide, sayGuidance } from './guide.mjs';
import { decodePhoto } from './photo.mjs';
import { GREETING, buildInstructions } from './prompt.mjs';
import { CONCERN_ANSWERS, CONCERN_KINDS, createConcernReporter } from './concern.mjs';
import { createSaveIt } from './saveit.mjs';
import { createVoiceMeter } from './voice-meter.mjs';

const FAMILY = process.env.FAMILY_NAME || 'June';

// The ring around the thing on a photo card breathes (once a second) this long after the photo appears, then
// holds still. A call keeps this many decoded photos, so asking again shows the photo at once.
const RING_PULSE_MS = 8000;
const PHOTOS_KEPT = 6;

// Gemini Live model. Keep a 2.5 native-audio model: in @livekit/agents-plugin-google 1.8.0, any model with
// "3.1" in its name rejects generateReply, so the greeting would fail and Chert would end the call.
const MODEL = process.env.GEMINI_LIVE_MODEL || 'gemini-2.5-flash-native-audio-preview-12-2025';
const VOICE = process.env.GEMINI_VOICE || 'Aoede';

// Thinking off by default. Measured 14 Nov through LiveKit with spoken questions: answering from the snapshot,
// first sound came 2.6 to 3.1 s after the question with the model's own thinking, 1.8 to 2.4 s with
// thinkingBudget 0, same answers. Google's docs only say this model "uses thinkingBudget". Set
// GEMINI_THINKING_BUDGET=default for the model's own behaviour, or a number of tokens.
const THINKING_BUDGET = process.env.GEMINI_THINKING_BUDGET === 'default' ? '' : (process.env.GEMINI_THINKING_BUDGET ?? '0');

// Turn-taking (Gemini's automatic activity detection). GEMINI_SILENCE_MS is how long the caller must be quiet
// before Gemini answers; Google: a larger value "will increase the model's latency", a smaller one cuts in on
// slow speakers. GEMINI_END_SENSITIVITY is HIGH or LOW. Unset: Gemini's defaults.
const SILENCE_MS = process.env.GEMINI_SILENCE_MS;
const END_SENSITIVITY = process.env.GEMINI_END_SENSITIVITY;
const VAD = {
  ...(SILENCE_MS ? { silenceDurationMs: Number(SILENCE_MS) } : {}),
  ...(END_SENSITIVITY ? { endOfSpeechSensitivity: `END_SENSITIVITY_${END_SENSITIVITY.toUpperCase()}` } : {}),
};

// One JSON line per event, to the console and to logs/calls.jsonl (gitignored), so a test call can be
// measured afterwards. Timings and tool names always; what was said only with LOG_TRANSCRIPTS=1 (testing).
// CALL_LOG_FILE, AGENT_HTTP_PORT and any X_OVERRIDE (env.mjs) let a benchmark worker run beside the real one.
const LOG_FILE = new URL(process.env.CALL_LOG_FILE || './logs/calls.jsonl', import.meta.url);
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

/** Dispatch metadata from web-call.mjs (browser test calls). Chert's jobs carry {"chert_warm":true} or {"chert_call":...}. */
const isTestCall = metadata => {
  try {
    return JSON.parse(metadata || '{}').test_call === true;
  } catch {
    return false;
  }
};

// Said once, as soon as FaceTime is ready (greet.mjs). Chert ends a silent call 10 s after bridge_ready.

const agent = defineAgent({
  entry: async ctx => {
    await ctx.connect(undefined, AutoSubscribe.AUDIO_ONLY);
    // Chert prepares a warm room before a caller exists. Join promptly, but wait for the caller
    // before opening a paid model session or sending video (docs/CHERT.md "Warm room").
    const caller = await ctx.waitForParticipant();

    // Per-call read-side state lives here, not in the model.
    const saveIt = createSaveIt({ backendUrl: process.env.BACKEND_URL || '', appToken: process.env.APP_TOKEN || '', familyName: FAMILY, log: callLog });
    const concerns = createConcernReporter({ backendUrl: process.env.BACKEND_URL || '', appToken: process.env.APP_TOKEN || '', log: callLog });
    const testCall = isTestCall(ctx.job?.metadata);
    const knownSoon = saveIt.loadSnapshot(); // loads while the card is published
    callLog({ event: 'call_start', test_call: testCall, answers_from: saveIt.mode === 'backend' ? process.env.BACKEND_URL : 'fake home (BACKEND_URL is empty)', thinking_budget: THINKING_BUDGET || 'default', vad: Object.keys(VAD).length ? VAD : 'default', transcripts: TRANSCRIPTS });

    // Video card: render on change, reuse frames. The marker pulses at 1 Hz while Save It speaks.
    const source = new VideoSource(WIDTH, HEIGHT);
    const track = LocalVideoTrack.createVideoTrack('save-it-card', source);
    // The marker: orange and pulsing while Save It talks; steady green the moment the caller's voice comes in
    // (a level meter on their audio, below); dim otherwise. Talking wins over hearing (echo of our own voice).
    // A photo card comes in two beats of the ring around the thing (frames[1] is the wider one); every other
    // card uses one set for both.
    const framesFor = view => {
      const set = pulse => ({ off: renderCard(view, 'idle', pulse), on: renderCard(view, 'speaking', pulse), hear: renderCard(view, 'listening', pulse) });
      const steady = set(false);
      return view.kind === 'photo' ? [steady, set(true)] : [steady, steady];
    };
    let frames = framesFor({ kind: 'idle' });
    let speaking = false, hearing = false;
    let shown = 0;          // goes up with every card, so a photo that arrives late never replaces a newer card
    let ringPulseUntil = 0;
    const show = view => {
      shown += 1;
      frames = framesFor(view);
      ringPulseUntil = view.kind === 'photo' ? Date.now() + RING_PULSE_MS : 0;
    };
    const send = () => {
      const beat = Math.floor(Date.now() / 500) % 2 === 0;
      const set = frames[Date.now() < ringPulseUntil && !beat ? 1 : 0];
      const frame = speaking ? (beat ? set.on : set.off) : hearing ? set.hear : set.off;
      source.captureFrame(new VideoFrame(frame, WIDTH, HEIGHT, VideoBufferType.RGBA));
    };
    send();
    await ctx.room.localParticipant.publishTrack(track, { source: TrackSource.SOURCE_CAMERA });
    const timer = setInterval(send, 1000 / FPS);

    // Light up green as soon as the caller's voice arrives (about 60 ms), not when Gemini reports it (after the
    // first words are transcribed). A frame goes out at once on each change. The log gets 'voice' on/off: the
    // off time is when the caller stopped talking, so replies can be timed from it.
    const meter = createVoiceMeter({ onChange: on => { hearing = on; send(); callLog({ event: 'voice', on }); } });
    const metered = new Set();
    const meterIfCaller = (track, _pub, participant) => {
      if (participant?.identity !== caller.identity || track?.kind !== TrackKind.KIND_AUDIO || metered.has(track.sid)) return;
      metered.add(track.sid);
      (async () => { for await (const frame of new AudioStream(track, 16000, 1)) meter.push(frame); })().catch(() => {});
    };
    ctx.room.on(RoomEvent.TrackSubscribed, meterIfCaller);
    for (const pub of caller.trackPublications.values()) if (pub.track) meterIfCaller(pub.track, pub, caller);
    const known = await knownSoon;

    // Where to look. The place name goes up at once; the photo of that moment replaces it when it has loaded,
    // so the answer never waits on a picture. A where-is answer with no place clears the card (`clearIfNoPlace`),
    // so it never shows a place from an earlier question.
    const photos = new Map(); // sighting -> decoded photo, for this call
    const showAnswer = ({ suggested, sighting }, clearIfNoPlace = false) => {
      if (!suggested) {
        if (clearIfNoPlace) show({ kind: 'idle' });
        return;
      }
      const place = { kind: 'place', landmark: suggested.landmark, room: suggested.room };
      if (sighting && photos.has(sighting)) return show({ ...place, kind: 'photo', photo: photos.get(sighting) });
      show(place);
      if (!sighting) return;
      const mine = shown;
      saveIt.loadPhoto(sighting, { width: WIDTH, height: HEIGHT, safe: photoLayout(place).safe })
        .then(loaded => loaded && decodePhoto(loaded))
        .then(photo => {
          if (!photo) return;
          photos.set(sighting, photo);
          if (photos.size > PHOTOS_KEPT) photos.delete(photos.keys().next().value);
          if (mine !== shown) return; // another card went up while this one loaded
          show({ ...place, kind: 'photo', photo });
          callLog({ event: 'photo_shown', ring: Boolean(photo.circle) });
        })
        .catch(err => callLog({ event: 'photo_failed', error: String(err?.message ?? err).slice(0, 200) }));
    };
    // Each tool returns the sentence to say, and updates the card.
    const reply = (out, clearIfNoPlace = false) => {
      showAnswer(out, clearIfNoPlace);
      return out.say;
    };
    const findObjectTool = llm.tool({
        name: 'find_object',
        description: 'Look up where one of their things is, when it is not in your list.',
        parameters: { type: 'object', properties: { phrase: { type: 'string', description: 'Just the thing they are looking for, in their words, e.g. "glasses" or "my specs". Not the whole question.' } }, required: ['phrase'] },
        execute: async ({ phrase }) => reply(await saveIt.findObject(phrase), true),
      });
    // With a snapshot there is no lookup tool: known items are in the instructions, unknown ones get "I don't know
    // it yet" at once. The 14 Nov test call showed the model answering from the list AND calling find_object,
    // then saying the same sentence twice, and each lookup cost a second model round (about 1.5 s).
    // No recall_life_fact or alert_caregiver: nothing answers /facts or /alert yet, and on the test call each
    // failed and made the agent say a second sentence ("Let me check with June"). Family calling is paused.
    // find_by_description needs the backend's search over the moments (GET /describe); the fake home has none.
    const describeTool = llm.tool({
      name: 'find_by_description',
      description: 'They describe one of their things by how it looks or what it is for instead of naming it, or their answer to "which one?" does not settle it. Finds the thing that fits best among the photos of their things. Returns which thing they mean and what to say.',
      parameters: { type: 'object', properties: { description: { type: 'string', description: 'What they said about the thing, in their own words, e.g. "the silver one I wear on my wrist".' } }, required: ['description'] },
      execute: async ({ description }) => reply(await saveIt.findByDescription(description), true),
    });
    const tools = [
      ...(known.length ? [] : [findObjectTool]),
      // Always offered, snapshot or not (docs/INSIGHTS.md design 3): ask once, report, the family decides.
      llm.tool({
        name: 'report_concern',
        description: 'They fell, are hurt, need help (not with finding a thing), smell smoke, are lost outside, or someone wants money from them. Ask "Are you hurt?" first, except for smoke or money. Returns what to say.',
        parameters: {
          type: 'object',
          properties: {
            kind: { type: 'string', enum: CONCERN_KINDS },
            answer: { type: 'string', enum: CONCERN_ANSWERS, description: 'Their answer to "Are you hurt?": hurt, ok (even if they say they are fine), or no_answer. Leave out for smoke or money.' },
          },
          required: ['kind'],
        },
        execute: async ({ kind, answer }) => (await concerns.report(kind, answer)).say,
      }),
      ...(saveIt.mode === 'backend' ? [describeTool] : []),
      llm.tool({
        name: 'report_not_there',
        description: 'They checked the place and the thing was not there. Returns what to say next.',
        parameters: { type: 'object', properties: { thing: { type: 'string', description: 'The thing they were looking for, e.g. "glasses".' } } },
        execute: async ({ thing } = {}) => reply(await saveIt.reportNotThere(thing), true),
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
    ];

    // Guided directions (guide.mjs): once they ask for help getting there, GET /guide is polled while they walk
    // and Find It speaks up when they get closer. Voice only; the card keeps showing the place. It needs the
    // backend (the camera's view lives there), so the fake home has no such tool.
    const guide = createGuide({
      saveIt,
      backendUrl: process.env.BACKEND_URL || '',
      appToken: process.env.APP_TOKEN || '',
      log: callLog,
      onLookup: found => reply(found, true),
      announce: g => {
        if (speaking || hearing) return false; // never over the caller, never over ourselves; tried again next poll
        session.generateReply({ instructions: sayGuidance(g.sentence) });
        return true;
      },
    });
    if (saveIt.mode === 'backend') {
      tools.push(llm.tool({
        name: 'guide_to_thing',
        description: GUIDE_TOOL,
        parameters: { type: 'object', properties: { thing: { type: 'string', description: 'The thing they are looking for, e.g. "glasses".' } } },
        execute: async ({ thing } = {}) => guide.begin(thing),
      }));
    }
    ctx.addShutdownCallback(async () => guide.stop('call_end'));

    const session = new voice.AgentSession({
      llm: new google.realtime.RealtimeModel({
        model: MODEL,
        voice: VOICE,
        ...(THINKING_BUDGET ? { thinkingConfig: { thinkingBudget: Number(THINKING_BUDGET) } } : {}),
        ...(Object.keys(VAD).length ? { realtimeInputConfig: { automaticActivityDetection: VAD } } : {}),
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
      // The model answers known items from its instructions; the card and the question log follow what was heard.
      saveIt.noteHeard(event.transcript).then(out => {
        if (out) showAnswer(out, true);
      });
    });
    session.on(voice.AgentSessionEventTypes.ConversationItemAdded, event => {
      if (event.item?.role !== 'assistant') return;
      callLog({ event: 'said', ...(TRANSCRIPTS ? { text: event.item.textContent ?? '' } : {}) });
      // The card and the log follow what the reply settled on: after "the blue one?" "Yes", the caller's words
      // name no item, but the answer names the blue water bottle.
      saveIt.noteSaid(event.item.textContent ?? '').then(out => {
        if (out) showAnswer(out, true);
      });
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
      agent: new voice.Agent({ instructions: buildInstructions(known, { describe: saveIt.mode === 'backend' }), tools }),
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
    // Browser test calls have no FaceTime bridge, so no bridge_ready ever comes: greet once now instead.
    if (testCall) {
      callLog({ event: 'greet', test_call: true });
      session.generateReply({ instructions: GREETING });
    }
    const stopGreeting = greetOnBridgeReady(ctx.room, () => {
      callLog({ event: 'greet' });
      return session.generateReply({ instructions: GREETING });
    });
    ctx.addShutdownCallback(async () => stopGreeting());
  },
});

export default agent;

// Own LiveKit project when .env.local has its three LIVEKIT_ values; otherwise Chert rooms through chert dev.
runAgent(agent, {
  file: fileURLToPath(import.meta.url),
  agentName: process.env.AGENT_NAME || 'save-it',
  port: Number(process.env.AGENT_HTTP_PORT) || undefined, // set for a second worker (benchmarks); default 8081
});
