---
description: Step 03 - Vapi phone number answering through the find API
---

# Step 03: Phone voice (Vapi)

Read `docs/STATUS.md`, `.claude/rules/voice.md`, and `docs/DECISIONS.md` D5, D14 and D15.
Depends on: 02, and a public HTTPS URL in `PUBLIC_BASE_URL`.
Time box: 1.5 hours.

Before writing any code, read https://docs.vapi.ai/tools/custom-tools.md and the pages it links for the tool request and response format and for authenticating server requests.
Write the shapes you found into STATUS; if they differ from anything in our docs, add them under "Things that differ".

## Build

1. `app/voice/vapi.py`: parse Vapi's tool-call request into Pydantic models, call `db.ask_item(item, channel="phone")` and `speak()`, and return the sentence in the result format the doc specifies.
   Unknown tool names and bad payloads get a valid response containing the fallback sentence, never a 500.
2. `POST /vapi/tool` in `app/main.py`, thin. Reject requests without the shared secret (`VAPI_SERVER_SECRET`), using the mechanism the Vapi doc describes.
3. If step 01 added `query_id` and D15 is kept, a second tool `report_outcome(query_id, found)` that calls `record_outcome`. Otherwise one tool only.
4. `docs/vapi-assistant.md`: everything the humans paste into the Vapi dashboard: the system prompt (from the voice rules), the tool definition JSON, the server URL `${PUBLIC_BASE_URL}/vapi/tool`, the first message, and the voice and speed (D14).
   The assistant must call the tool for every "where is" question and read the result word for word.

## Tests

- Request fixtures copied from the Vapi doc's own examples, not invented. Database faked.

## Checks

- pytest and ruff are clean.
- `curl` the public URL with a doc-shaped request and the secret: correct body. Without the secret: rejected.
- CP1: a teammate calls the number and hears the seeded place. If the phone line fails, use a Vapi web call and note it (`docs/PLAN.md` CP1).

## Humans

Create the Vapi account, claim the free number, create the assistant from `docs/vapi-assistant.md`, and set the server secret.
