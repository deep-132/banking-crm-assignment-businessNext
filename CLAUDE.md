# CLAUDE.md

Project conventions for `banking-crm` — an agentic AI system that helps a Relationship Manager
(RM) find high-value customers likely to convert for a personal loan and generate personalized
WhatsApp outreach. Read this before making changes; it's the shared context for anyone (human or
agent) working on this repo.

## What this is

- **Backend**: Python, FastAPI, LangGraph, Azure OpenAI, SQLite, pandas — `backend/`
- **Frontend**: React + TypeScript + Tailwind CSS — `frontend/`
- **Specs**: acceptance criteria for the RM use case, written Given/When/Then — `specs/`

Full architecture, execution flow, and design rationale live in [README.md](README.md). This
file is about *how the code is organized and why*, so changes stay consistent with it.

## Architecture in one paragraph

The backend is a LangGraph state machine, not a single prompt. Every RM message hits a
**Supervisor node** (one Azure OpenAI call) that classifies intent into `full_search` / `refine` /
`explain` / `clarify`, then the graph runs only the nodes that intent needs. All retrieval,
scoring, and eligibility logic lives in plain Python **tool functions**
(`backend/app/tools/`) with no LLM involvement — the LLM is only used to route (supervisor) and
to write outreach copy (`tools/messaging.py`), and never to invent a score or a fact.

## Conventions to follow

- **Tools are plain functions, agent code is orchestration.** Anything in `backend/app/tools/`
  should be callable and testable with no FastAPI/LangGraph/Azure OpenAI context beyond
  `messaging.py`'s one LLM call. If you're adding scoring/retrieval/eligibility logic, it belongs
  in a tool, not inlined in a node.
- **Nodes wrap tools, they don't duplicate logic.** `backend/app/agent/nodes.py` functions are
  named `*_node` and should stay thin: pull from `AgentState`, call one or more tools, write back
  to `AgentState`. Business logic (weights, thresholds, eligibility rules) stays in `tools/`.
- **Every LLM call site must degrade gracefully.** Both call sites (`supervisor.route`,
  `messaging.generate_whatsapp_message`) wrap the Azure OpenAI call in try/except and fall back
  to a safe default (a conservative intent, or a deterministic template) rather than raising.
  Keep this pattern for any new LLM call — a bad API key should never crash a request.
- **Grounded generation only.** If you add a new LLM-generated customer-facing text, feed it a
  structured fact sheet (not raw DB rows) and an explicit system-prompt instruction forbidding
  invented facts, the same way `messaging.py` does. This is a hard requirement, not a style
  preference — see the "no hardcoded outputs without reasoning" constraint in the original brief.
- **Session state is `AgentState`, cached per `session_id`.** `all_scored_records` is the "memory"
  that lets `refine`/`explain` reuse a prior `full_search` without re-querying. If you add a new
  intent action, decide explicitly whether it needs the cached universe or can be served from it.
- **Rules before ML.** Scoring (`tools/scoring.py`) is rules-based and transparent by default,
  with named weight constants. The `SCORING_MODE=ml` path (`tools/train_model.py`) is an explicit,
  documented extensibility hook — don't make ML the default without real historical labels to
  validate against.
- **Tests mock the LLM, not the pipeline.** See `backend/tests/test_agent_graph.py` —
  `chat_completion` is monkeypatched at the module that imports it
  (`app.agent.supervisor.chat_completion`, `app.tools.messaging.chat_completion`), so tests
  exercise real scoring/retrieval/ranking logic against the seeded SQLite DB, only faking the
  network call.

## Where to look for what

| I want to... | Go to |
|---|---|
| Add a new intent/route | `agent/prompts.py` (schema + rules) → `agent/supervisor.py` (guardrails) → `agent/graph.py` (wiring) |
| Change scoring weights | `tools/scoring.py` — `HVC_WEIGHTS` / `CONVERSION_WEIGHTS` |
| Add a new loan product | `db/seed_data.py` `LOAN_OFFERS` + reseed |
| Change outreach tone/rules | `tools/messaging.py` `SYSTEM_PROMPT` |
| Add a UI element for a result | `frontend/src/components/CustomerCard.tsx` |

## Specs

Acceptance criteria for the core use cases are in [specs/personal-loan-outreach.feature](specs/personal-loan-outreach.feature),
written Given/When/Then. They map directly onto `backend/tests/test_agent_graph.py` — if you
change routing or ranking behavior, update both.
