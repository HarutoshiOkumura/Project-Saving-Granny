// Loads .env.local so it wins over variables the terminal already had. `node --env-file` never overrides a
// variable that is already set, and VS Code's "python.terminal.useEnvFile" puts the repo's .env into every
// terminal. Its AGENT_NAME was not ours, so the agent registered under the wrong name and Chert declined calls.
// The database keys that come along are dropped: the agent talks to the backend over HTTP and never holds them.
// agent.mjs imports this first, before anything reads process.env.
import { readFileSync } from 'node:fs';
import { parseEnv } from 'node:util';

export function applyEnvFile(path, env = process.env) {
  let text = '';
  try {
    text = readFileSync(path, 'utf8');
  } catch (err) {
    if (err.code !== 'ENOENT') throw err;
  }
  Object.assign(env, parseEnv(text));
  for (const key of Object.keys(env)) if (key.startsWith('SUPABASE_') || key === 'DATABASE_URL') delete env[key];
  return env;
}

applyEnvFile(new URL('./.env.local', import.meta.url));
