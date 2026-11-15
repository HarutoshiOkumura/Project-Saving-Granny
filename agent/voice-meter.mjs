// A small level meter on the caller's audio, so the card lights up the moment the caller's voice arrives.
// Gemini only reports speech once it has transcribed the first words; this reacts after about 60 ms of voice.
// It drives the light and the call log, never the conversation (Gemini decides turns).
//
// Voice = louder than the room by `ratio`. The room's noise is one of the quietest moments of the last 1.5 s
// (5th percentile, so a dropped packet does not count): speech always has gaps between words, a hum does not.

/**
 * @param {{ onChange?: (on: boolean) => void, startMs?: number, stopMs?: number, minLevel?: number, ratio?: number,
 *           windowMs?: number, warmupMs?: number }} options
 *   startMs: voice needed before lighting up (ignores clicks); stopMs: quiet needed before going dark (bridges
 *   pauses between words); minLevel: 16-bit RMS that always counts as quiet; warmupMs: listen before deciding.
 */
export function createVoiceMeter({ onChange, startMs = 60, stopMs = 450, minLevel = 350, ratio = 3, windowMs = 1500, warmupMs = 200 } = {}) {
  const recent = []; // [level, ms] for the last windowMs
  let recentMs = 0, heardMs = 0, on = false, loudMs = 0, quietMs = 0;
  return {
    get on() { return on; },
    /** One audio frame ({ data: Int16Array, sampleRate, samplesPerChannel }); returns its level (RMS). */
    push({ data, sampleRate, samplesPerChannel }) {
      let sum = 0;
      for (let i = 0; i < data.length; i++) sum += data[i] * data[i];
      const level = Math.sqrt(sum / Math.max(1, data.length));
      const ms = (samplesPerChannel / sampleRate) * 1000;
      recent.push([level, ms]);
      recentMs += ms;
      heardMs += ms;
      while (recent.length > 1 && recentMs - recent[0][1] >= windowMs) recentMs -= recent.shift()[1];
      if (heardMs < warmupMs) return level;
      const sorted = recent.map(([l]) => l).sort((a, b) => a - b);
      const floor = sorted[Math.floor(sorted.length * 0.05)];
      const voice = level > Math.max(minLevel, floor * ratio);
      if (voice) { loudMs += ms; quietMs = 0; } else { quietMs += ms; loudMs = 0; }
      if (!on && loudMs >= startMs) { on = true; onChange?.(true); }
      else if (on && quietMs >= stopMs) { on = false; onChange?.(false); }
      return level;
    },
  };
}
