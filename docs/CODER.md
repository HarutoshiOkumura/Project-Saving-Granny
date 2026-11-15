# Coder workspaces

How the team develops in Coder, and what is true of the event's deployment. Checked 14 Nov against the live deployment (v2.38.7) and https://coder.com/docs.

## What we use

- Deployment: `https://coder.c1.workshop.cdr.dev` (the event's, licensed). Not a self-hosted server.
- Template: `tech-stack-builder`. One workspace per teammate, all from the same template and repo URL.
- Tom's workspace: `save-it` (created 14 Nov 19:52 ET).
- You are inside a workspace when `$CODER` is `true`.

## Create a workspace (on your laptop)

```bash
brew install coder
coder login https://coder.c1.workshop.cdr.dev
coder create <name> -t tech-stack-builder
coder config-ssh            # adds the ssh host <name>.coder
coder open vscode <name>
```

Answers to the prompts: Team repo URL `https://github.com/HarutoshiOkumura/Project-Saving-Granny.git`; IDEs `vscode-desktop` (press space to tick); Languages: anything, the setup script installs Node itself; CPU 4; Memory 8; disk 10 (cannot change later).
Then run the setup script from your laptop, from the repo root:

```bash
ssh <name>.coder 'bash -s' < scripts/coder_setup.sh
```

It installs uv, Python 3.12, Node 26, `cloudflared`, the Chert CLI and Claude Code under `~/.local`, checks out `tom/read-side` if asked, and runs both test suites. Safe to re-run.
Then copy the env files (they are gitignored, never commit them):

```bash
scp .env <name>.coder:Project-Saving-Granny/.env
scp agent/.env.local <name>.coder:Project-Saving-Granny/agent/.env.local
```

The keys then sit on the event's servers, which its admins can reach. Rotate them after the hackathon.

## Facts about the workspace

- It is a Kubernetes pod. **Only `/home/coder` survives a restart.** Install tools under `~/.local`, never with `apt` or `sudo`.
- **No Docker.** The scratch Postgres database tests in `CLAUDE.md` run on a laptop, not here.
- System Python is 3.14; `uv` provides 3.12 for the project.
- The template's "Node.js" choice installed nothing. The setup script installs Node 26. Node 24 is not enough: `npm test` in `agent/` passes `test/` to `node --test`, which Node 24 treats as a file and fails.
- No `gh` and no GitHub login. Push from VS Code's Source Control panel, which signs in through the laptop's browser.
- Typesense (step 09) runs as a Docker container on Tom's Mac (`saveit-typesense`). In a workspace `TYPESENSE_HOST` has nothing to reach, so `names.resolve()` falls back to the raw words after at most 300 ms. Fix: Typesense Cloud or Typesense's Linux binary under `~/.local` (check typesense.org/docs first).
- `chert login --device` on this machine (docs/CHERT.md).
- `npm run web-call` listens on 127.0.0.1 in the workspace. Open it on the laptop with `coder port-forward <name> --tcp <port>:<port>`; the browser treats `localhost` as secure, so the microphone works.
- Kernel 6.12, no Linux capabilities. Enough for Agent Firewall's `landjail` backend (needs 6.7+), not for `nsjail` (needs `NET_ADMIN`).

## Facts about the deployment

- **No public ports.** Every template caps port sharing at `owner`, and the license enforces the cap. Vapi, Chert and the iPhone cannot use a Coder port URL. The public address is a Cloudflare Quick Tunnel started in the workspace (D5).
- **Autostop:** a workspace stops 40 hours after it starts; any VS Code, terminal or `coder ssh` session pushes the stop back by 1 hour. Users cannot turn this off. Traffic to a port is not activity. Restarting the workspace starts a new 40 hours.
- Turned on: audit log, connection log, Coder Agents (the chats API answers), AI Gateway (`aibridge`), Agent Firewall (`boundary`), template insights.
- About 34 accounts on the deployment (14 Nov evening).

## Daily commands (on the laptop)

```bash
coder list
coder open vscode save-it
coder ssh save-it
coder port-forward save-it --tcp 3000:3000   # the workspace API at localhost:3000
coder stop save-it / coder start save-it
coder update save-it --always-prompt         # change IDEs, languages, CPU, memory
```

In the workspace, two terminals for a call test:

```bash
uv run uvicorn app.main:app --port 3000
cloudflared tunnel --url http://localhost:3000
```

## Showing judges

What the organizers can see: workspaces per person, build history, and every VS Code, SSH and terminal connection (connection log). Commits made in a workspace carry the Coder account's name and email.

- Every teammate develops in their own workspace and commits from it, small and often.
- Screenshots for Devpost: the workspace page, VS Code connected to it, Claude Code running in it. A few seconds in the video.
- Name on Devpost only the Coder features we really used.

## Open, ask the Coder table

- What do judges check for the Coder track?
- May teams send Claude calls through the AI Gateway, and how do we connect Claude Code to it?
- Is a model configured for Coder Agents?
