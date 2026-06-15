# Parallel Workflow Knowledge and Domain Awareness

Status: Implemented foundation
Last updated: 2026-06-12
Primary scope: Gateway workflows, parallel agents, knowledge retrieval, domain-aware merged responses

## Purpose

ShivaAI Jarvis now supports a workflow execution pattern where independent workflow steps can run as parallel agents and return one consolidated final response.

The goal is not to produce multiple disconnected answers. The goal is:

1. Split independent work into parallel step groups.
2. Give each step compact project knowledge and domain context.
3. Collect every agent result.
4. Merge the results into one final response for the user.

This creates faster multi-step analysis while preserving a single clear answer.

## Current Capability

Workflows can define `parallel_groups` alongside normal ordered `steps`.

Example:

```json
{
  "name": "Domain aware performance review",
  "trigger": "manual",
  "steps": [
    "Research project knowledge",
    "Review risks",
    "Check tests",
    "Summarize answer"
  ],
  "parallel_groups": [
    ["Research project knowledge", "Review risks", "Check tests"]
  ]
}
```

In this example, the first three steps can run together. The final output still returns one `final_response`.

## Execution Model

The workflow executor normalizes the workflow into groups:

- Steps inside the same group run concurrently.
- Steps not assigned to a parallel group run as single-step groups.
- Groups run in order, so later steps can still represent synthesis or completion stages.
- The run result stores all agent outputs and one merged response.

The implementation lives in:

- `services/gateway/src/workflow_executor.py`
- `services/gateway/src/main.py`
- `services/gateway/src/schemas.py`
- `services/gateway/src/storage.py`

## Output Shape

A workflow run output now includes these important fields:

```json
{
  "execution_mode": "parallel",
  "parallel_groups": [["Research project knowledge", "Review risks"]],
  "steps": [],
  "agent_results": [],
  "domain_awareness": {},
  "knowledge_used": [],
  "merged_response": {
    "status": "completed",
    "agent_count": 3,
    "final_response": "...",
    "agents": [],
    "domains": [],
    "knowledge_used": []
  },
  "final_response": "..."
}
```

The user-facing answer should use `final_response`. The other fields are useful for audit, debugging, traceability, and UI inspection.

## Knowledge Awareness

Before running workflow agents, the executor builds a compact context packet from existing project knowledge systems.

Knowledge sources:

- Assistant profile domains from the saved profile.
- Relevant memory entries from `ChatRepository.list_memories`.
- Relevant document chunks from `ChatRepository.search_document_chunks`.
- Workflow name, objective, and step text.

The context is attached internally to each agent step. Each result can report:

- `knowledge_used`
- `domain_awareness`
- `summary`

This makes the agent output explainable without flooding the final response with raw database content.

## Domain Awareness

The executor infers lightweight domain hints from workflow text and objective text.

Current domain hints include:

- `coding`
- `automation`
- `security`
- `knowledge`
- `enterprise`

The executor also respects profile domains already saved for the assistant.

Example:

If the user objective is:

```text
Improve parallel workflow performance with knowledge context
```

The executor can infer domains such as:

- `automation`
- `knowledge`
- `coding`

These are returned in `domain_awareness.domains`.

## Why This Matters

Parallel agents are useful only when they avoid fragmentation. A naive multi-agent design can produce several partial answers and force the user to reconcile them.

This design keeps the product behavior simple:

- Parallel work happens internally.
- The user receives one final response.
- The system keeps agent-level evidence for review.
- Knowledge and domain context are reused consistently.

## Recommended Use Cases

Good fits:

- Project risk review
- Release readiness checks
- Test gap analysis
- Connector impact review
- Knowledge-base research
- Multi-document summarization
- Architecture decision support
- Incident triage workflows

Poor fits:

- Simple chat replies
- Single-step deterministic actions
- Tasks where every step depends on the previous step
- Workflows that require multiple agents editing the same artifact at the same time

## API Example

Create a workflow:

```http
POST /api/v1/workflows
Content-Type: application/json
```

```json
{
  "name": "Parallel project review",
  "trigger": "manual",
  "steps": [
    "Research project knowledge",
    "Review risks",
    "Check tests",
    "Summarize response"
  ],
  "parallel_groups": [
    ["Research project knowledge", "Review risks", "Check tests"]
  ],
  "metadata": {
    "owner": "workspace"
  }
}
```

Run the workflow:

```http
POST /api/v1/workflows/{workflow_id}/run
Content-Type: application/json
```

```json
{
  "dry_run": false,
  "input": {
    "objective": "Improve project performance with domain-aware workflow agents"
  }
}
```

Read the result:

```json
{
  "status": "completed",
  "output": {
    "execution_mode": "parallel",
    "final_response": "Research project knowledge processed...",
    "domain_awareness": {
      "domains": ["coding", "automation", "knowledge"]
    },
    "knowledge_used": []
  }
}
```

## Verification

Current tests cover:

- Creating and running normal workflows.
- Running parallel workflow groups.
- Merging parallel agent results into one final response.
- Using memory, documents, and profile domains as workflow context.

Test command:

```bash
pytest tests/test_gateway_smoke.py -k "workflow"
```

Lint command for the new execution path:

```bash
python -m ruff check services/gateway/src/main.py services/gateway/src/schemas.py services/gateway/src/workflow_executor.py
```

## Next Improvements

Recommended next steps:

1. Replace placeholder step summaries with real capability dispatch.
2. Add per-step capability references, such as `capability_id` or `agent_type`.
3. Add bounded concurrency settings, such as `MAX_PARALLEL_WORKFLOW_AGENTS`.
4. Store richer execution traces for each agent step.
5. Let the frontend visualize parallel groups and the final merged answer.
6. Add a knowledge ingestion button for this document.

## Key Principle

Parallel execution is an internal performance and reasoning strategy. The product should still feel like one assistant giving one coherent answer.
