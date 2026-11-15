---
description: Step 00 - scaffold the Python app, settings and test harness
---

# Step 00: Scaffold

Read `docs/STATUS.md` and `docs/DECISIONS.md` D5 and D6.
Time box: 30 minutes.

Already done on 14 Nov: `.gitignore`, `.env.example`, `.env` (Supabase values filled in), `.mcp.json`, `.claude/`.

## Build

1. `pyproject.toml` for uv with `requires-python = ">=3.12,<3.13"`.
   Runtime dependencies: `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `supabase`, `google-genai`, `httpx`, `python-multipart`.
   Dev dependencies: `pytest`, `ruff`.
   Add perception libraries (OpenCV, scikit-image, the Roboflow SDK) in the steps that use them, not now.
   Let `uv add` pick current versions, and commit `uv.lock`.
2. Ruff settings in `pyproject.toml`: line length 100, target `py312`, rules `E`, `F`, `I`, `UP`, `B`.
3. The package layout from `CLAUDE.md`, with `__init__.py` files. Create only the modules this step needs.
4. `app/config.py`: one `Settings` class (pydantic-settings) reading `.env`, with field names matching `.env.example`.
   Keys and secrets are `SecretStr`; `HOME_ID` is a `UUID`; services used by later or optional steps are optional fields.
5. `app/main.py`: a FastAPI app with `GET /health` returning `{"ok": true}` and nothing else.
6. `tests/conftest.py` sets fake environment values so tests never read the real `.env`; `tests/test_health.py` uses FastAPI's `TestClient`.

## Checks

- `uv sync` succeeds.
- `uv run pytest -q` passes.
- `uv run ruff check . && uv run ruff format --check .` is clean.
- `uv run uvicorn app.main:app --port 8000` starts, and `curl -s localhost:8000/health` returns `{"ok":true}`.
- `git status` does not list `.env`.

## Humans, in parallel

- A Coder workspace from a shared template (D6); take a screenshot.
- Decide where the backend runs and get its public HTTPS address (D5); put it in `PUBLIC_BASE_URL`.
