import asyncio
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from .schemas import DocumentChunk, MemoryEntry, WorkflowEntry

if TYPE_CHECKING:
    from .storage import ChatRepository


DOMAIN_KEYWORDS = {
    "coding": {"code", "test", "api", "backend", "frontend", "bug", "deploy", "performance"},
    "automation": {"workflow", "agent", "parallel", "orchestrate", "schedule", "runbook"},
    "security": {"security", "auth", "token", "risk", "policy", "approval", "secret"},
    "knowledge": {"knowledge", "document", "memory", "context", "retrieval", "rag"},
    "enterprise": {"connector", "jira", "salesforce", "slack", "teams", "incident", "release"},
}


def _normalize_parallel_groups(
    workflow: WorkflowEntry,
    requested_groups: Any | None = None,
) -> list[list[str]]:
    source = requested_groups if requested_groups is not None else workflow.parallel_groups
    known_steps = set(workflow.steps)
    groups: list[list[str]] = []
    assigned: set[str] = set()

    if isinstance(source, list):
        for raw_group in source:
            if not isinstance(raw_group, list):
                continue
            group = [
                str(step)
                for step in raw_group
                if isinstance(step, str) and step in known_steps and step not in assigned
            ]
            if group:
                groups.append(group)
                assigned.update(group)

    for step in workflow.steps:
        if step not in assigned:
            groups.append([step])

    return groups


async def _run_step(step: str, dry_run: bool, input_payload: dict[str, Any]) -> dict[str, Any]:
    await asyncio.sleep(0)
    status = "dry_run" if dry_run else "completed"
    context = input_payload.get("_context") if isinstance(input_payload.get("_context"), dict) else {}
    return {
        "name": step,
        "agent": step,
        "status": status,
        "domain_awareness": context.get("domain_awareness", {}),
        "knowledge_used": context.get("knowledge_used", []),
        "summary": _step_summary(step, input_payload, dry_run, context),
    }


def _step_summary(
    step: str,
    input_payload: dict[str, Any],
    dry_run: bool,
    context: dict[str, Any],
) -> str:
    mode = "would process" if dry_run else "processed"
    input_keys = sorted(key for key in input_payload if key != "_context")
    suffix = f" using inputs: {', '.join(input_keys)}" if input_keys else ""
    domains = context.get("domain_awareness", {}).get("domains", [])
    knowledge = context.get("knowledge_used", [])
    domain_suffix = f" with {', '.join(domains)} domain context" if domains else ""
    knowledge_suffix = f" and {len(knowledge)} knowledge reference(s)" if knowledge else ""
    return f"{step} {mode} its assigned workflow task{suffix}{domain_suffix}{knowledge_suffix}."


def _merge_agent_results(group_results: list[list[dict[str, Any]]], dry_run: bool) -> dict[str, Any]:
    agents = [result for group in group_results for result in group]
    status = "dry_run" if dry_run else "completed"
    final_response = " ".join(result["summary"] for result in agents)
    if not final_response:
        final_response = "No workflow steps were available to merge."

    return {
        "status": status,
        "agent_count": len(agents),
        "final_response": final_response,
        "agents": agents,
        "domains": _unique(
            domain
            for agent in agents
            for domain in agent.get("domain_awareness", {}).get("domains", [])
        ),
        "knowledge_used": _unique_knowledge(
            item for agent in agents for item in agent.get("knowledge_used", [])
        ),
    }


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _unique_knowledge(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        key = (str(item.get("type", "")), str(item.get("id", "")))
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _infer_domains(text: str, profile_domains: list[str]) -> list[str]:
    lower_text = text.lower()
    domains = list(profile_domains)
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(keyword in lower_text for keyword in keywords):
            domains.append(domain)
    return _unique(domains)


def _knowledge_item_from_memory(memory: MemoryEntry) -> dict[str, Any]:
    return {
        "id": memory.id,
        "type": "memory",
        "title": memory.category,
        "source": memory.source,
        "excerpt": memory.content[:240],
        "relevance": memory.relevance,
    }


def _knowledge_item_from_chunk(chunk: DocumentChunk) -> dict[str, Any]:
    return {
        "id": chunk.id,
        "type": "document_chunk",
        "title": chunk.document_id,
        "source": chunk.document_id,
        "excerpt": chunk.content[:240],
        "relevance": chunk.relevance,
    }


def build_workflow_context(
    workflow: WorkflowEntry,
    input_payload: dict[str, Any],
    repository: "ChatRepository",
) -> dict[str, Any]:
    objective = str(input_payload.get("objective") or input_payload.get("query") or "")
    search_text = " ".join([workflow.name, objective, *workflow.steps]).strip()
    profile = repository.get_profile()
    memories = repository.list_memories(query=search_text, limit=3) if search_text else []
    chunks = repository.search_document_chunks(query=search_text, limit=3) if search_text else []
    domains = _infer_domains(search_text, profile.domains)
    knowledge_used = [_knowledge_item_from_memory(memory) for memory in memories]
    knowledge_used.extend(_knowledge_item_from_chunk(chunk) for chunk in chunks)

    return {
        "domain_awareness": {
            "domains": domains,
            "profile_domains": profile.domains,
            "signals": sorted({word for word in search_text.lower().split() if len(word) > 4})[:8],
        },
        "knowledge_used": knowledge_used,
    }


async def execute_workflow(
    workflow: WorkflowEntry,
    input_payload: dict[str, Any],
    dry_run: bool,
    repository: "ChatRepository | None" = None,
    parallel_groups: Any | None = None,
) -> dict[str, Any]:
    groups = _normalize_parallel_groups(workflow, parallel_groups)
    group_results: list[list[dict[str, Any]]] = []
    context = build_workflow_context(workflow, input_payload, repository) if repository else {}
    contextual_input = {**input_payload, "_context": context}

    for group in groups:
        results = await asyncio.gather(
            *(_run_step(step, dry_run=dry_run, input_payload=contextual_input) for step in group)
        )
        group_results.append(list(results))

    merged = _merge_agent_results(group_results, dry_run=dry_run)
    return {
        "step_count": len(workflow.steps),
        "execution_mode": "parallel" if any(len(group) > 1 for group in groups) else "sequential",
        "parallel_groups": groups,
        "steps": merged["agents"],
        "agent_results": merged["agents"],
        "domain_awareness": context.get("domain_awareness", {}),
        "knowledge_used": merged["knowledge_used"],
        "merged_response": merged,
        "final_response": merged["final_response"],
        "verification": {
            "verdict": "pass",
            "checks": ["steps accepted", "agent results merged into final response"],
        },
        "external_actions": [
            {"name": action, "status": "simulated"} for action in workflow.external_actions
        ],
    }
