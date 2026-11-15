#!/usr/bin/env bash
# Set up a tech-stack-builder Coder workspace for Save It. See docs/CODER.md.
# Run from the laptop:  ssh <name>.coder 'bash -s' < scripts/coder_setup.sh
# Optional branch:      ssh <name>.coder 'BRANCH=tom/read-side bash -s' < scripts/coder_setup.sh
# Everything goes under $HOME, the only part of the workspace that survives a restart. Safe to re-run.
set -euo pipefail
REPO="$HOME/Project-Saving-Granny"
mkdir -p "$HOME/.local/bin"
export PATH="$HOME/.local/bin:$HOME/.local/node/bin:$PATH"

# PATH for every new shell (home starts with no dotfiles)
LINE='export PATH="$HOME/.local/bin:$HOME/.local/node/bin:$PATH"'
touch "$HOME/.bashrc"
grep -qxF "$LINE" "$HOME/.bashrc" || echo "$LINE" >>"$HOME/.bashrc"
[ -f "$HOME/.profile" ] || printf '[ -f "$HOME/.bashrc" ] && . "$HOME/.bashrc"\n' >"$HOME/.profile"

cd "$REPO"
if [ -n "${BRANCH:-}" ]; then
  echo "== branch $BRANCH"
  git fetch -q origin
  git checkout -q "$BRANCH" 2>/dev/null || git checkout -q -b "$BRANCH" "origin/$BRANCH"
fi
git log --oneline -1

echo "== uv"
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh >/dev/null
uv --version

echo "== node 26 (agent tests fail on 24)"
if ! node --version 2>/dev/null | grep -q '^v26\.'; then
  BASE=https://nodejs.org/dist/latest-v26.x
  SUMS=$(curl -fsSL "$BASE/SHASUMS256.txt")
  TGZ=$(grep -o 'node-v[0-9.]*-linux-x64\.tar\.gz' <<<"$SUMS" | head -1)
  curl -fsSL "$BASE/$TGZ" -o /tmp/node.tgz
  (cd /tmp && grep " $TGZ\$" <<<"$SUMS" | sed "s| $TGZ\$| node.tgz|" | sha256sum -c --quiet -)
  rm -rf "$HOME/.local/node" && mkdir -p "$HOME/.local/node"
  tar -xzf /tmp/node.tgz -C "$HOME/.local/node" --strip-components=1 && rm /tmp/node.tgz
fi
node --version

echo "== cloudflared"
if ! command -v cloudflared >/dev/null; then
  curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
    -o "$HOME/.local/bin/cloudflared"
  chmod +x "$HOME/.local/bin/cloudflared"
fi
cloudflared --version

echo "== chert CLI (docs/CHERT.md)"
command -v chert >/dev/null || npm install -g --silent @trychert/facetime@beta >/dev/null
command -v chert

echo "== claude code"
command -v claude >/dev/null || curl -fsSL https://claude.ai/install.sh | bash >/dev/null
claude --version

echo "== python 3.12, deps, tests"
uv python install -q 3.12
uv sync -q
uv run pytest -q 2>&1 | tail -1

echo "== agent deps, tests"
(cd agent && npm ci --silent >/dev/null 2>&1 && npm test 2>&1 | grep -E '^ℹ (pass|fail)')

echo "Done. Next: copy .env and agent/.env.local (docs/CODER.md), open a new terminal."
