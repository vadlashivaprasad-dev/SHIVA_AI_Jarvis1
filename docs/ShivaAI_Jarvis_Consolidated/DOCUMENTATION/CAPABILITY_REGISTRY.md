# Dynamic Capability Registry

The gateway now includes a persisted dynamic capability registry. It is the first concrete
implementation of the Cognitive OS "system call" layer described in the architecture docs:
agents and UI surfaces can discover what the system can do, inspect permissions, and request a
guarded dispatch.

## Implemented Scope

- SQLite-backed `capabilities` table with automatic default capabilities.
- Capability CRUD API for custom tools, agents, and service adapters.
- Core feature status API that groups capabilities by feature area.
- Invoke endpoint that can preview dispatches or run built-in local executors.
- Invocation audit ledger with recent history API.
- React panel for feature health, capability search, custom registration, preview/run, and history.
- Smoke tests for registry CRUD, guarded invocation, and feature status reporting.

## Default Capabilities

| Capability | Category | Purpose |
| --- | --- | --- |
| `chat.completions` | `assistant` | Chat generation with history and relevant memory. |
| `memory.semantic_search` | `memory` | Semantic and episodic memory storage/search. |
| `agent.planner` | `agent` | Local planning capability for complex requests. |
| `kernel.capability_registry` | `kernel` | Registry discovery, governance, and dispatch metadata. |

## API Reference

### List Core Features

```http
GET /api/v1/features
```

Returns feature groups such as `chat`, `memory`, `orchestration`, and `governance`, including
status and linked capability counts.

### List Capabilities

```http
GET /api/v1/capabilities?query=memory&category=memory&status=enabled
```

Filters are optional. Results are ordered by category and name.

### Register Capability

```http
POST /api/v1/capabilities
Content-Type: application/json

{
  "name": "custom.research.brief",
  "description": "Produce a structured research brief from workspace context.",
  "category": "custom",
  "permissions": ["custom:invoke"],
  "metadata": {"core_feature": "governance"}
}
```

Supported statuses are `enabled`, `disabled`, and `degraded`.

### Update Capability

```http
PATCH /api/v1/capabilities/{id}
Content-Type: application/json

{
  "status": "disabled"
}
```

### Dry-Run Invocation

```http
POST /api/v1/capabilities/{id}/invoke
Content-Type: application/json

{
  "dry_run": true,
  "input": {"source": "web-ui"}
}
```

The current implementation records intent and returns dispatch metadata. It does not execute
side effects.

### Execute Built-In Capabilities

```http
POST /api/v1/capabilities/agent.planner/invoke
Content-Type: application/json

{
  "dry_run": false,
  "input": {
    "objective": "Implement pending Jarvis features",
    "constraints": ["keep changes scoped"]
  }
}
```

Built-in local executors currently exist for:

| Capability | Execution |
| --- | --- |
| `agent.planner` | Produces deterministic implementation steps and a next action. |
| `memory.semantic_search` | Runs memory retrieval with `query`, `category`, and `limit`. |
| `kernel.capability_registry` | Searches registered capabilities by `query`, `category`, and `status`. |

Custom and external capabilities are recorded as `queued` until an executor adapter is attached.

### Invocation History

```http
GET /api/v1/capabilities/invocations?limit=20
```

Returns recent invocation audit records including capability name, status, input, output, dry-run
flag, and timestamp.

## Next Integration Points

- Attach real executor adapters for web search, file operations, code review, and workflow actions.
- Add authenticated owner/user scope to capabilities once public chat is disabled.
- Use capability permissions in agent planning before tool selection.
