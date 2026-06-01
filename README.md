# ShivaAI Jarvis

ShivaAI Jarvis is organized as a small monorepo with a runnable FastAPI gateway and Vite React web app.

## Project Layout

```text
apps/web                 React + Vite frontend
services/gateway         FastAPI gateway service
infra/monitoring         Prometheus configuration
scripts                  Developer helper scripts
tests                    Smoke tests
docs                     Architecture and implementation notes
legacy/scaffold          Preserved original scaffold files
```

## Run (dev)

### Docker

```bash
docker compose up --build
```

Frontend: http://localhost:3000

Gateway: http://localhost:8000

```bash
curl http://localhost:8000/health
```

### Backend

```bash
cd services/gateway
python -m venv .venv
. .venv\Scripts\activate  # windows
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

## Tests

```bash
python -m pytest tests
```

## Feature Flags

The gateway uses durable local storage and an offline assistant by default:

```bash
DATABASE_PATH=data/gateway.db
LLM_PROVIDER=local
```

To use an OpenAI-compatible chat completion provider, set:

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
```

## Current APIs

- `POST /api/v1/auth/signup` creates a local user and bearer token.
- `POST /api/v1/auth/login` authenticates an existing local user.
- `GET /api/v1/auth/me` returns the authenticated user.
- `GET /api/v1/admin/users` lists users for admin tokens.
- `POST /api/v1/chat/sessions` creates a conversation.
- `POST /api/v1/chat/completions` sends a message and stores episodic memory.
- `POST /api/v1/chat/completions/stream` returns Server-Sent Events.
- `GET /api/v1/memory?query=...` searches local memory.
- `POST /api/v1/memory` stores manual semantic memory.
- `POST /api/v1/documents` chunks document text and optionally seeds knowledge memory.
- `GET /api/v1/documents` lists ingested documents.
- `GET /api/v1/documents/search?query=...` searches document chunks.
- `GET /api/v1/features` reports core feature status.
- `GET /api/v1/settings/modules` lists feature-domain settings.
- `PATCH /api/v1/settings/modules/{id}` turns a feature domain on or off.
- `POST /api/v1/workflows` creates a local deterministic workflow.
- `GET /api/v1/workflows` lists local workflows.
- `POST /api/v1/workflows/{id}/run` previews or runs workflow steps.
- `GET /api/v1/workflows/runs` lists workflow run history.
- `GET /api/v1/workflows/verification` lists workflow verification reports.
- `POST /api/v1/decisions/evaluate` returns local confidence/risk/cost/impact scoring with explainability and policy gates.
- `POST /api/v1/reflection/review` reviews content, suggests improvements, and returns a quality verdict.
- `POST /api/v1/voice/transcribe` returns text-backed local transcription, wake-word status, confidence, and speaker hint.
- `POST /api/v1/voice/synthesize` returns browser speech synthesis metadata.
- `GET /api/v1/voice/personas` lists available local voice personas.
- `POST /api/v1/voice/sentiment` estimates voice sentiment, energy, and urgency.
- `POST /api/v1/skill-graphs` creates a local skill graph dry-run plan.
- `POST /api/v1/skill-graphs/run` executes or previews an ordered local skill graph.
- `POST /api/v1/capabilities/evolve` proposes, registers, and verifies a new local capability.
- `POST /api/v1/world/facts` stores a world-model fact.
- `GET /api/v1/world/facts` lists stored world-model facts.
- `GET /api/v1/world/digital-twin` summarizes the saved profile, preferences, domains, and known facts.
- `GET /api/v1/connectors` lists enterprise connector adapters.
- `POST /api/v1/connectors/{id}/sync` previews or runs a connector sync.
- `GET /api/v1/connectors/{id}/search?query=...` searches local connector adapter records.
- `POST /api/v1/meetings/analyze` summarizes transcripts, action items, Jira stories, and follow-up email.
- `POST /api/v1/vision/analyze` analyzes supplied visual descriptions for objects, observations, and risk flags.
- `POST /api/v1/trading/analyze` returns local trading signal/risk analysis with approval guardrails.
- `POST /api/v1/robotics/readiness` returns robotics readiness scoring, blockers, and safety checklist.
- `GET /api/v1/capabilities` searches the dynamic capability registry.
- `POST /api/v1/capabilities` registers a new capability.
- `PATCH /api/v1/capabilities/{id}` updates capability metadata/status.
- `POST /api/v1/capabilities/{id}/invoke` previews or runs a guarded capability dispatch.
- `GET /api/v1/capabilities/invocations` lists recent capability invocation audit records.
- `POST /api/v1/feedback` captures response-quality feedback.
- `GET /api/v1/feedback` lists captured feedback signals.
- `GET /api/v1/feedback/summary` returns aggregate feedback counts.
- `GET /api/v1/profile` returns the saved Jarvis communication profile.
- `PATCH /api/v1/profile` updates profile preferences used in chat context.

## Docs
- `docs/PROJECT_STRUCTURE.md`
- `docs/SHIVAAI_PROJECT_DOCUMENTATION.md`
- `docs/SHIVAAI_JARVIS_1MONTH_ENTERPRISE_ROADMAP.md`
- `docs/CAPABILITY_REGISTRY.md`
- `docs/SELF_LEARNING_FEEDBACK.md`
- `docs/JARVIS_PROFILE.md`
- `docs/PDF_FEATURE_COMPLETION_AUDIT.md`
- `docs/blueprints/`

