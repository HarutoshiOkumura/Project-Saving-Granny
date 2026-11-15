// A browser call to the Save It agent without FaceTime, so it uses no Chert minutes.
//   Terminal 1: the backend. Terminal 2: npm start. Terminal 3: npm run web-call, then open
//   http://127.0.0.1:8090 and press Call. chert dev is not needed.
// The page joins a fresh LiveKit room on our own project with a token that dispatches the agent
// (docs.livekit.io/agents/server/agent-dispatch, "Dispatch via access token"; dispatch happens only
// when the room is created, hence a new room per call). Same agent, voice, tools and card as on
// FaceTime; the agent greets at once because there is no FaceTime bridge to wait for.
// Listens on 127.0.0.1 only and checks the Host header: the token endpoint must never be reachable
// from another machine or a rebinding web page. LiveKit's key and secret stay in this process.
import './env.mjs';
import { readFileSync } from 'node:fs';
import { createServer } from 'node:http';
import { pathToFileURL } from 'node:url';
import { RoomAgentDispatch, RoomConfiguration } from '@livekit/protocol';
import { AccessToken } from 'livekit-server-sdk';

const PORT = Number(process.env.WEB_CALL_PORT || 8090);
const AGENT = process.env.AGENT_NAME || 'save-it';

/** A token for one fresh room; joining it creates the room and dispatches the agent with test_call metadata. */
export async function createTestCall({ url, apiKey, apiSecret, agentName = AGENT, now = Date.now() }) {
  if (!url || !apiKey || !apiSecret) throw new Error('Set LIVEKIT_URL, LIVEKIT_API_KEY and LIVEKIT_API_SECRET in agent/.env.local');
  const room = `save-it-test-${now}`;
  const at = new AccessToken(apiKey, apiSecret, { identity: `tester-${now}`, name: 'Tester', ttl: '30m' });
  at.addGrant({ roomJoin: true, room, canPublish: true, canSubscribe: true });
  at.roomConfig = new RoomConfiguration({
    agents: [new RoomAgentDispatch({ agentName, metadata: JSON.stringify({ test_call: true }) })],
  });
  return { url, room, token: await at.toJwt() };
}

/** Only this computer, by name: refuses DNS-rebinding hosts that resolve to 127.0.0.1. */
export const localHost = host => /^(127\.0\.0\.1|localhost)(:\d+)?$/.test(host ?? '');

function serve() {
  const page = readFileSync(new URL('./web-call.html', import.meta.url));
  const client = readFileSync(new URL('./node_modules/livekit-client/dist/livekit-client.umd.js', import.meta.url));
  const send = (res, status, type, body) => {
    res.writeHead(status, { 'Content-Type': type, 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
    res.end(body);
  };
  createServer(async (req, res) => {
    try {
      if (!localHost(req.headers.host)) return send(res, 403, 'text/plain', 'local only');
      if (req.method === 'GET' && (req.url === '/' || req.url === '/index.html')) return send(res, 200, 'text/html; charset=utf-8', page);
      if (req.method === 'GET' && req.url === '/livekit-client.js') return send(res, 200, 'text/javascript; charset=utf-8', client);
      if (req.method === 'POST' && req.url === '/token') {
        const call = await createTestCall({ url: process.env.LIVEKIT_URL, apiKey: process.env.LIVEKIT_API_KEY, apiSecret: process.env.LIVEKIT_API_SECRET });
        console.log(`[web-call] ${new Date().toISOString()} room ${call.room}: dispatching "${AGENT}"`);
        return send(res, 200, 'application/json', JSON.stringify(call));
      }
      send(res, 404, 'text/plain', 'not found');
    } catch (err) {
      console.error('[web-call]', err.message);
      send(res, 500, 'text/plain', err.message);
    }
  }).listen(PORT, '127.0.0.1', () => {
    console.log(`[web-call] Open http://127.0.0.1:${PORT} and press Call. Needs the backend and npm start; chert dev is not needed.`);
  });
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) serve();
