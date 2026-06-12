from typing import Any

from fastapi import HTTPException

from .app_utils import jsonable, module_enabled, now_utc
from .llm import LLMHealth
from .schemas import (
    CapabilityEntry,
    CapabilityInvocation,
    DecisionRequest,
    ReflectionRequest,
    VoiceSentimentRequest,
    VoiceSynthesisRequest,
    VoiceTranscriptionRequest,
    WorkflowEntry,
)
from .storage import ChatRepository

CONNECTORS = [
    ("jira", "Jira", ["issues:read", "issues:write"]),
    ("salesforce", "Salesforce", ["accounts:read", "cases:read"]),
    ("slack", "Slack", ["channels:read", "messages:read"]),
    ("teams", "Teams", ["chat:read", "meetings:read"]),
    ("confluence", "Confluence", ["pages:read"]),
    ("servicenow", "ServiceNow", ["incidents:read"]),
    ("sharepoint", "SharePoint", ["files:read"]),
]

FEATURE_DEFINITIONS = [
    ("chat", "Chat", "Conversation, streaming, and LLM response flow"),
    ("memory", "Memory", "Semantic memory and document recall"),
    ("orchestration", "Orchestration", "Planner and skill graph execution"),
    ("governance", "Governance", "Capability registry and policy checks"),
    ("workflow", "Workflow", "Workflow creation, dry-runs, and verification"),
    ("decision", "Decision", "Decision scoring and reflective review"),
    ("domain_intelligence", "Domain Intelligence", "Meeting, vision, trading, and robotics tools"),
    ("connectors", "Connectors", "Enterprise connector search and sync"),
    ("voice", "Voice", "Browser voice transcription and synthesis helpers"),
]


def feature_rows(store: ChatRepository) -> list[dict[str, Any]]:
    caps = store.list_capabilities()
    by_feature: dict[str, int] = {}
    for cap in caps:
        key = str(cap.metadata.get("core_feature", cap.category))
        by_feature[key] = by_feature.get(key, 0) + 1
    return [
        {
            "id": feature_id,
            "name": name,
            "status": "enabled" if module_enabled(store, feature_id) else "disabled",
            "description": description,
            "capability_count": by_feature.get(feature_id, 0),
        }
        for feature_id, name, description in FEATURE_DEFINITIONS
    ]


def enterprise_overview_payload(
    store: ChatRepository,
    llm_health: LLMHealth,
) -> dict[str, Any]:
    features = feature_rows(store)
    capabilities = store.list_capabilities()
    workflows = store.list_workflows(limit=100)
    workflow_runs = store.list_workflow_runs(limit=12)
    invocations = store.list_capability_invocations(limit=12)
    modules = store.list_module_settings()
    feedback = store.summarize_feedback()
    documents = store.list_documents(limit=100)
    memories = store.list_memories(limit=100)
    conversations = store.list_conversations(limit=6)

    enabled_modules = sum(1 for module in modules if module.enabled)
    enabled_capabilities = sum(1 for capability in capabilities if capability.status == "enabled")
    disabled_features = [feature for feature in features if feature["status"] != "enabled"]
    negative_feedback = feedback.by_rating.get("negative", 0) + feedback.by_rating.get("correction", 0)
    failed_runs = [run for run in workflow_runs if run.status not in {"completed", "dry_run"}]

    readiness_score = 100
    readiness_score -= 20 if llm_health.status != "healthy" else 0
    readiness_score -= min(24, len(disabled_features) * 4)
    readiness_score -= min(18, (len(capabilities) - enabled_capabilities) * 3)
    readiness_score -= min(12, negative_feedback * 2)
    readiness_score -= min(10, len(failed_runs) * 5)
    readiness_score = max(0, readiness_score)

    risks = enterprise_risks(llm_health, disabled_features, negative_feedback, workflows, documents)
    next_actions = enterprise_next_actions(
        llm_health,
        disabled_features,
        negative_feedback,
        workflows,
        documents,
    )
    recent_activity = recent_enterprise_activity(invocations, workflow_runs)
    posture = "ready" if readiness_score >= 85 else "watch" if readiness_score >= 65 else "attention"

    return {
        "posture": posture,
        "readiness_score": readiness_score,
        "generated_at": now_utc(),
        "llm": {
            "provider": llm_health.provider,
            "status": llm_health.status,
            "model": llm_health.model,
            "details": llm_health.details,
        },
        "metrics": {
            "conversations": conversations["total"],
            "memories": len(memories),
            "documents": len(documents),
            "workflows": len(workflows),
            "workflow_runs": len(workflow_runs),
            "capabilities": len(capabilities),
            "connectors": len(CONNECTORS),
            "feedback": feedback.total,
        },
        "governance": {
            "enabled_modules": enabled_modules,
            "total_modules": len(modules),
            "enabled_capabilities": enabled_capabilities,
            "total_capabilities": len(capabilities),
            "disabled_features": jsonable(disabled_features),
        },
        "risks": risks[:5],
        "next_actions": next_actions[:5],
        "recent_activity": recent_activity[:8],
        "recent_conversations": jsonable(conversations["conversations"]),
    }


def enterprise_risks(
    llm_health: LLMHealth,
    disabled_features: list[dict[str, Any]],
    negative_feedback: int,
    workflows: list[WorkflowEntry],
    documents: list[Any],
) -> list[str]:
    risks: list[str] = []
    if llm_health.status != "healthy":
        risks.append(f"LLM provider is {llm_health.status}; chat quality may be degraded.")
    if disabled_features:
        risks.append(f"{len(disabled_features)} feature module(s) are disabled.")
    if negative_feedback:
        risks.append(f"{negative_feedback} feedback item(s) need review.")
    if not workflows:
        risks.append("No operational workflow is configured yet.")
    if not documents:
        risks.append("Knowledge base is empty; document recall is limited.")
    return risks or ["No active operational risks detected."]


def enterprise_next_actions(
    llm_health: LLMHealth,
    disabled_features: list[dict[str, Any]],
    negative_feedback: int,
    workflows: list[WorkflowEntry],
    documents: list[Any],
) -> list[str]:
    next_actions: list[str] = []
    if llm_health.status != "healthy":
        next_actions.append("Verify Ollama container health and configured model availability.")
    if not workflows:
        next_actions.append("Create a release or incident workflow with preview and run steps.")
    if not documents:
        next_actions.append("Ingest architecture, runbook, or project documents into knowledge.")
    if disabled_features:
        next_actions.append("Review disabled modules in Settings before enterprise rollout.")
    if negative_feedback:
        next_actions.append("Review negative feedback and update profile, memory, or prompts.")
    if len(next_actions) < 3:
        next_actions.append("Run a dry-run capability invocation to validate audit history.")
    if len(next_actions) < 3:
        next_actions.append("Sync a connector with dry-run first, then promote the workflow.")
    return next_actions


def recent_enterprise_activity(invocations: list[Any], workflow_runs: list[Any]) -> list[dict[str, Any]]:
    recent_activity = [
        {
            "label": invocation.capability_name,
            "status": "preview" if invocation.dry_run else invocation.status,
            "created_at": invocation.created_at,
            "type": "capability",
        }
        for invocation in invocations[:5]
    ] + [
        {
            "label": run.workflow_name,
            "status": "preview" if run.dry_run else run.status,
            "created_at": run.created_at,
            "type": "workflow",
        }
        for run in workflow_runs[:5]
    ]
    recent_activity.sort(key=lambda item: item["created_at"], reverse=True)
    return recent_activity


def run_capability(
    capability: CapabilityEntry,
    body: CapabilityInvocation,
    store: ChatRepository,
) -> dict[str, Any]:
    if capability.status != "enabled":
        raise HTTPException(status_code=409, detail="Capability is disabled")
    if body.dry_run:
        return {"input_keys": sorted(body.input.keys()), "preview": f"{capability.name} dry run ready"}
    if capability.name == "agent.planner":
        objective = str(body.input.get("objective", "Complete requested work"))
        return {
            "steps": [f"Clarify {objective}", "Implement scoped change", "Run verification"],
            "constraints": body.input.get("constraints", []),
        }
    if capability.name == "memory.semantic_search":
        results = store.list_memories(
            query=str(body.input.get("query", "")),
            limit=int(body.input.get("limit", 5)),
        )
        return {"count": len(results), "results": jsonable(results)}
    if capability.name == "kernel.capability_registry":
        results = store.list_capabilities(query=str(body.input.get("query", "")) or None)
        return {"count": len(results), "capabilities": jsonable(results)}
    return {"message": f"{capability.name} executed", "input": body.input}


def workflow_run_output(workflow: WorkflowEntry, dry_run: bool) -> dict[str, Any]:
    return {
        "step_count": len(workflow.steps),
        "steps": [
            {"name": step, "status": "dry_run" if dry_run else "completed"}
            for step in workflow.steps
        ],
        "verification": {"verdict": "pass", "checks": ["steps ordered", "inputs accepted"]},
        "external_actions": [
            {"name": action, "status": "simulated"} for action in workflow.external_actions
        ],
    }


def evaluate_decision_payload(body: DecisionRequest) -> dict[str, Any]:
    risks = len(body.risks)
    blocked_gates = body.policy_gates if body.policy_gates or risks >= 3 else []
    recommendation = body.options[0] if body.options else body.decision
    return {
        "decision": body.decision,
        "recommendation": recommendation,
        "confidence_score": 78 if blocked_gates else 86,
        "risk_score": min(100, 20 + risks * 22),
        "cost_score": 35 if (body.estimated_effort or "").lower() in {"small", "low"} else 55,
        "impact_score": 82 if body.expected_impact else 70,
        "rationale": ["Uses available local capability", "Keeps review and verification explicit"],
        "policy_verdict": "requires_review" if blocked_gates else "approved",
        "explainability": {"blocked_gates": blocked_gates, "risk_count": risks},
    }


def review_reflection_payload(body: ReflectionRequest) -> dict[str, Any]:
    improvements = ["Add acceptance checks", "Name the next action"]
    return {
        "summary": body.content[:180],
        "issues": ["Verification could be clearer"] if body.criteria else [],
        "improvements": improvements,
        "revised_content": f"{body.content}\n\nReflection improvements:\n- " + "\n- ".join(improvements),
        "quality_score": 84,
        "policy_verdict": "pass",
    }


def transcribe_voice_payload(body: VoiceTranscriptionRequest) -> dict[str, Any]:
    return {
        "transcript": body.audio_text,
        "confidence": 92,
        "speaker": body.speaker_hint or "User",
        "wake_word_detected": "jarvis" in body.audio_text.lower(),
    }


def synthesize_voice_payload(body: VoiceSynthesisRequest) -> dict[str, Any]:
    return {
        "text": body.text,
        "voice_id": body.voice_id,
        "format": "browser-speech",
        "audio_url": None,
        "browser_speech_supported": True,
    }


def voice_sentiment_payload(body: VoiceSentimentRequest) -> dict[str, Any]:
    urgent = any(term in body.transcript.lower() for term in ["urgent", "now", "blocked"])
    return {
        "sentiment": "urgent" if urgent else "focused",
        "energy": "high" if urgent else "normal",
        "urgency_score": 80 if urgent else 25,
    }


def list_connectors_payload() -> list[dict[str, Any]]:
    return [
        {"id": cid, "name": name, "provider": name, "status": "ready", "scopes": scopes, "last_sync_at": None}
        for cid, name, scopes in CONNECTORS
    ]


def connector_provider(connector_id: str) -> str:
    return next((name for cid, name, _ in CONNECTORS if cid == connector_id), connector_id.title())
