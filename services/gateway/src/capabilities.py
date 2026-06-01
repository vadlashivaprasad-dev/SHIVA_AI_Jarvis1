from dataclasses import dataclass
from typing import Any

from .schemas import CapabilityEntry, CapabilityInvocation
from .storage import ChatRepository


@dataclass
class CapabilityExecution:
    status: str
    output: dict[str, Any]
    error: str | None = None


def execute_capability(
    capability: CapabilityEntry,
    payload: CapabilityInvocation,
    repository: ChatRepository,
) -> CapabilityExecution:
    if payload.dry_run:
        return CapabilityExecution(
            status="dry_run",
            output={
                "name": capability.name,
                "category": capability.category,
                "permissions": capability.permissions,
                "input_keys": sorted(payload.input.keys()),
                "message": "Capability dispatch preview recorded.",
            },
        )

    core_feature = str(capability.metadata.get("core_feature", capability.category))

    # Prefer dispatch by core_feature to avoid brittle name mismatches
    if capability.name in {"agent.planner", "planner"} or core_feature == "orchestration":
        return _run_planner(payload.input)
    if capability.name in {"memory.semantic_search", "semantic_search"} or core_feature == "memory":
        return _run_memory_search(payload.input, repository)
    if capability.name in {"kernel.capability_registry", "capability_registry"} or core_feature == "governance":
        return _run_registry_search(payload.input, repository)

    # Fallback: external executor adapter


    return CapabilityExecution(
        status="queued",
        output={
            "name": capability.name,
            "category": capability.category,
            "input_keys": sorted(payload.input.keys()),
            "message": "Invocation recorded for an external executor adapter.",
        },
    )


def _run_planner(input_payload: dict[str, Any]) -> CapabilityExecution:
    objective = str(
        input_payload.get("objective")
        or input_payload.get("prompt")
        or input_payload.get("task")
        or "Clarify the user objective"
    ).strip()
    constraints = input_payload.get("constraints") or []
    if isinstance(constraints, str):
        constraints = [constraints]
    if not isinstance(constraints, list):
        constraints = []

    normalized = objective.rstrip(".")
    steps = [
        f"Confirm scope for: {normalized}",
        "Gather relevant project context and constraints",
        "Choose the smallest safe implementation slice",
        "Apply the change with tests and documentation",
        "Verify behavior and report remaining risks",
    ]
    return CapabilityExecution(
        status="completed",
        output={
            "objective": objective,
            "constraints": constraints,
            "steps": steps,
            "next_action": steps[1],
        },
    )


def _run_memory_search(
    input_payload: dict[str, Any],
    repository: ChatRepository,
) -> CapabilityExecution:
    query = input_payload.get("query")
    category = input_payload.get("category")
    limit = _coerce_limit(input_payload.get("limit"), default=5, maximum=20)
    memories = repository.list_memories(
        query=str(query) if query else None,
        category=str(category) if category else None,
        limit=limit,
    )
    return CapabilityExecution(
        status="completed",
        output={
            "count": len(memories),
            "memories": [memory.model_dump() for memory in memories],
        },
    )


def _run_registry_search(
    input_payload: dict[str, Any],
    repository: ChatRepository,
) -> CapabilityExecution:
    query = input_payload.get("query")
    category = input_payload.get("category")
    status = input_payload.get("status")
    capabilities = repository.list_capabilities(
        query=str(query) if query else None,
        category=str(category) if category else None,
        status=str(status) if status else None,
    )
    return CapabilityExecution(
        status="completed",
        output={
            "count": len(capabilities),
            "capabilities": [capability.model_dump() for capability in capabilities],
        },
    )


def _coerce_limit(value: Any, default: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(parsed, maximum))
