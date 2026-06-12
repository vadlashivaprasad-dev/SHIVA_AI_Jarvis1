import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .auth import create_access_token, get_bearer_payload, hash_password, require_role, verify_password
from .config import get_settings
from .errors import (
    ConflictError,
    ErrorCode,
    NotFoundError,
    ShivaAIException,
    generic_exception_handler,
    shivaai_exception_handler,
)
from .llm import create_llm_provider
from .log_config import RequestIDMiddleware, configure_logging
from .middleware import (
    CSRFTokenMiddleware,
    InputValidationMiddleware,
    PerformanceMetricsMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    TrustedHostMiddleware,
)
from .schemas import (
    AssistantProfileUpdate,
    CapabilityCreate,
    CapabilityEntry,
    CapabilityEvolutionRequest,
    CapabilityInvocation,
    CapabilityInvocationRecord,
    CapabilityUpdate,
    ConnectorSyncRequest,
    Conversation,
    ConversationCreate,
    DecisionRequest,
    DocumentChunk,
    DocumentCreate,
    DocumentEntry,
    FeedbackCreate,
    FeedbackEntry,
    MemoryCreate,
    MemoryEntry,
    Message,
    MessageRequest,
    ModuleSettingUpdate,
    ReflectionRequest,
    RoboticsReadinessRequest,
    SkillGraphCreate,
    TradingAnalysisRequest,
    UserCreate,
    UserLogin,
    VisionAnalyzeRequest,
    VoiceSynthesisRequest,
    VoiceTranscriptionRequest,
    VoiceSentimentRequest,
    WorkflowCreate,
    WorkflowEntry,
    WorkflowRunRecord,
    WorldFact,
    WorldFactCreate,
)
from .storage import ChatRepository


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _database_path() -> str:
    explicit = os.getenv("DATABASE_PATH")
    if explicit:
        return explicit
    settings = get_settings()
    if settings.database_url.startswith("sqlite:///"):
        return settings.database_url.removeprefix("sqlite:///")
    return str(Path("data") / "gateway.db")


def _repository() -> ChatRepository:
    return ChatRepository(_database_path(), enable_pool=False)


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def _sse_event(event: str | None, data: str) -> bytes:
    payload = data.replace("\r\n", "\n").replace("\r", "\n")
    lines = payload.split("\n") or [""]
    prefix = f"event: {event}\n" if event else ""
    data_lines = "".join(f"data: {line}\n" for line in lines)
    return f"{prefix}{data_lines}\n".encode("utf-8")


def _chunk_text(text: str, size: int = 12) -> list[str]:
    chunks: list[str] = []
    current = ""
    for word in text.split(" "):
        candidate = f"{current} {word}".strip()
        if len(candidate) >= size and current:
            chunks.append(current + " ")
            current = word
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks or [""]


def _split_document(content: str, chunk_size: int = 900) -> list[str]:
    paragraphs = [part.strip() for part in content.split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs or [content.strip()]:
        if len(current) + len(paragraph) + 2 > chunk_size and current:
            chunks.append(current)
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}".strip()
    if current:
        chunks.append(current)
    return chunks


def _module_enabled(repo: ChatRepository, module_id: str) -> bool:
    setting = repo.get_module_setting(module_id)
    return True if setting is None else setting.enabled


def _require_module(repo: ChatRepository, module_id: str) -> None:
    if not _module_enabled(repo, module_id):
        raise HTTPException(status_code=403, detail=f"{module_id} is disabled")


CONNECTORS = [
    ("jira", "Jira", ["issues:read", "issues:write"]),
    ("salesforce", "Salesforce", ["accounts:read", "cases:read"]),
    ("slack", "Slack", ["channels:read", "messages:read"]),
    ("teams", "Teams", ["chat:read", "meetings:read"]),
    ("confluence", "Confluence", ["pages:read"]),
    ("servicenow", "ServiceNow", ["incidents:read"]),
    ("sharepoint", "SharePoint", ["files:read"]),
]


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(log_level=settings.log_level, environment=settings.environment)

    app = FastAPI(title="ShivaAI Jarvis - Backend")
    app.state.repository = _repository()

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(PerformanceMetricsMiddleware)
    app.add_middleware(InputValidationMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=60)
    app.add_middleware(CSRFTokenMiddleware)

    if settings.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def repo() -> ChatRepository:
        return app.state.repository

    @app.exception_handler(ShivaAIException)
    async def _shivaai_exception_handler(request, exc):
        return await shivaai_exception_handler(request, exc)

    @app.exception_handler(Exception)
    async def _generic_exception_handler(request, exc):
        return await generic_exception_handler(request, exc)

    @app.get("/health")
    def health():
        return {"status": "healthy"}

    @app.post("/api/v1/auth/signup", status_code=201)
    def signup(body: UserCreate, store: ChatRepository = Depends(repo)):
        try:
            user = store.create_user(
                user_id=str(uuid4()),
                email=body.email,
                password_hash=hash_password(body.password),
                full_name=body.full_name,
                role=body.role,
                created_at=_now(),
            )
        except sqlite3.IntegrityError as exc:
            raise ConflictError(code=ErrorCode.RESOURCE_ALREADY_EXISTS, message="Email already exists") from exc
        return {"access_token": create_access_token(user, settings), "token_type": "bearer", "user": user}

    @app.post("/api/v1/auth/login")
    def login(body: UserLogin, store: ChatRepository = Depends(repo)):
        row = store.get_user_by_email(body.email)
        if row is None or not verify_password(body.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        user = store.get_user_by_id(row["id"])
        return {"access_token": create_access_token(user, settings), "token_type": "bearer", "user": user}

    @app.get("/api/v1/auth/me")
    def me(payload: dict[str, Any] = Depends(get_bearer_payload), store: ChatRepository = Depends(repo)):
        user = store.get_user_by_id(str(payload["sub"]))
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user

    @app.get("/api/v1/admin/users")
    def admin_users(
        limit: int = Query(default=50, ge=1, le=200),
        payload: dict[str, Any] = Depends(get_bearer_payload),
        store: ChatRepository = Depends(repo),
    ):
        require_role(payload, {"admin"})
        return store.list_users(limit=limit)

    @app.get("/api/v1/chat/sessions")
    def list_chat_sessions(
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        store: ChatRepository = Depends(repo),
    ):
        result = store.list_conversations(limit=limit, offset=offset)
        return result["conversations"]

    @app.post("/api/v1/chat/sessions", status_code=201)
    def create_chat_session(body: ConversationCreate, store: ChatRepository = Depends(repo)):
        now = _now()
        conversation = Conversation(
            id=str(uuid4()),
            title=(body.title or "Workspace chat").strip()[:120] or "Workspace chat",
            system_prompt=body.system_prompt,
            model=body.model,
            created_at=now,
            updated_at=now,
        )
        return store.create_conversation(conversation)

    @app.get("/api/v1/chat/sessions/{conversation_id}")
    def get_chat_session(conversation_id: str, store: ChatRepository = Depends(repo)):
        conversation = store.get_conversation(conversation_id)
        if conversation is None:
            raise NotFoundError(message="Conversation not found")
        return conversation

    async def _generate_chat(body: MessageRequest, store: ChatRepository) -> tuple[Message, Message, dict[str, Any]]:
        conversation = store.get_conversation(body.conversation_id)
        if conversation is None:
            raise NotFoundError(message="Conversation not found")

        now = _now()
        user_message = Message(
            id=str(uuid4()),
            conversation_id=body.conversation_id,
            role="user",
            content=body.content,
            created_at=now,
        )
        history = conversation.messages[-10:]
        profile = store.get_profile()
        profile_message = Message(
            id="profile",
            conversation_id=body.conversation_id,
            role="system",
            content=(
                f"Communication style: {profile.communication_style}. "
                f"Response detail: {profile.response_detail}."
            ),
            created_at=now,
        )
        memories = [memory.content for memory in store.list_memories(query=body.content, limit=5)]
        provider = create_llm_provider(settings)
        result = await provider.generate(
            prompt=body.content,
            history=[profile_message, *history, user_message],
            memories=memories,
            model=body.model or conversation.model,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
        )
        assistant_message = Message(
            id=str(uuid4()),
            conversation_id=body.conversation_id,
            role="assistant",
            content=result.content,
            created_at=_now(),
            metadata=result.metadata,
        )
        return user_message, assistant_message, result.metadata

    @app.post("/api/v1/chat/completions")
    async def chat_completion(body: MessageRequest, store: ChatRepository = Depends(repo)):
        user_message, assistant_message, _ = await _generate_chat(body, store)
        store.add_messages(body.conversation_id, [user_message, assistant_message], updated_at=assistant_message.created_at)
        return assistant_message

    @app.post("/api/v1/chat/completions/stream")
    async def chat_completions_stream(body: MessageRequest, store: ChatRepository = Depends(repo)):
        async def gen() -> AsyncGenerator[bytes, None]:
            try:
                user_message, assistant_message, _ = await _generate_chat(body, store)
                for token in _chunk_text(assistant_message.content):
                    yield _sse_event("token", json.dumps({"text": token}))
                store.add_messages(body.conversation_id, [user_message, assistant_message], updated_at=assistant_message.created_at)
                yield _sse_event("done", json.dumps(assistant_message.model_dump()))
            except Exception as exc:
                yield _sse_event("error", json.dumps({"message": str(exc), "code": "LLM_STREAM_ERROR"}))

        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.post("/api/v1/memory", status_code=201)
    def create_memory(body: MemoryCreate, store: ChatRepository = Depends(repo)):
        now = _now()
        return store.create_memory(
            MemoryEntry(
                id=str(uuid4()),
                content=body.content,
                category=body.category,
                source=body.source,
                conversation_id=body.conversation_id,
                created_at=now,
                updated_at=now,
            )
        )

    @app.get("/api/v1/memory")
    def list_memories(
        query: str | None = None,
        category: str | None = None,
        limit: int = Query(default=20, ge=1, le=100),
        store: ChatRepository = Depends(repo),
    ):
        return store.list_memories(query=query, category=category, limit=limit)

    @app.delete("/api/v1/memory/{memory_id}", status_code=204)
    def delete_memory(memory_id: str, store: ChatRepository = Depends(repo)):
        if not store.delete_memory(memory_id):
            raise NotFoundError(message="Memory not found")
        return Response(status_code=204)

    @app.post("/api/v1/documents", status_code=201)
    def create_document(body: DocumentCreate, store: ChatRepository = Depends(repo)):
        now = _now()
        chunks = [
            DocumentChunk(id=str(uuid4()), document_id="", index=index, content=content, created_at=now)
            for index, content in enumerate(_split_document(body.content))
        ]
        document = DocumentEntry(
            id=str(uuid4()),
            title=body.title,
            source=body.source,
            tags=body.tags,
            chunk_count=len(chunks),
            created_at=now,
            updated_at=now,
        )
        chunks = [chunk.model_copy(update={"document_id": document.id}) for chunk in chunks]
        created = store.create_document(document, chunks)
        if body.add_to_memory:
            store.create_memory(
                MemoryEntry(
                    id=str(uuid4()),
                    content=f"{body.title}: {body.content[:1200]}",
                    category="knowledge",
                    source=body.source,
                    conversation_id=None,
                    created_at=now,
                    updated_at=now,
                )
            )
        return created

    @app.get("/api/v1/documents")
    def list_documents(limit: int = Query(default=20, ge=1, le=100), store: ChatRepository = Depends(repo)):
        return store.list_documents(limit=limit)

    @app.get("/api/v1/documents/search")
    def search_documents(
        query: str | None = None,
        document_id: str | None = None,
        limit: int = Query(default=10, ge=1, le=100),
        store: ChatRepository = Depends(repo),
    ):
        return store.search_document_chunks(query=query, document_id=document_id, limit=limit)

    @app.get("/api/v1/documents/{document_id}")
    def get_document(document_id: str, store: ChatRepository = Depends(repo)):
        document = store.get_document(document_id)
        if document is None:
            raise NotFoundError(message="Document not found")
        return document

    @app.post("/api/v1/feedback", status_code=201)
    def create_feedback(body: FeedbackCreate, store: ChatRepository = Depends(repo)):
        return store.create_feedback(
            FeedbackEntry(
                id=str(uuid4()),
                rating=body.rating,
                category=body.category,
                comment=body.comment,
                conversation_id=body.conversation_id,
                message_id=body.message_id,
                created_at=_now(),
            )
        )

    @app.get("/api/v1/feedback")
    def list_feedback(
        conversation_id: str | None = None,
        rating: str | None = None,
        limit: int = Query(default=20, ge=1, le=100),
        store: ChatRepository = Depends(repo),
    ):
        return store.list_feedback(conversation_id=conversation_id, rating=rating, limit=limit)

    @app.get("/api/v1/feedback/summary")
    def feedback_summary(conversation_id: str | None = None, store: ChatRepository = Depends(repo)):
        return store.summarize_feedback(conversation_id=conversation_id)

    @app.get("/api/v1/profile")
    def get_profile(store: ChatRepository = Depends(repo)):
        return store.get_profile()

    @app.patch("/api/v1/profile")
    def patch_profile(body: AssistantProfileUpdate, store: ChatRepository = Depends(repo)):
        return store.update_profile(body.model_dump(exclude_unset=True), updated_at=_now())

    def feature_rows(store: ChatRepository) -> list[dict[str, Any]]:
        caps = store.list_capabilities()
        by_feature: dict[str, int] = {}
        for cap in caps:
            key = str(cap.metadata.get("core_feature", cap.category))
            by_feature[key] = by_feature.get(key, 0) + 1
        feature_defs = [
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
        return [
            {
                "id": fid,
                "name": name,
                "status": "enabled" if _module_enabled(store, fid) else "disabled",
                "description": description,
                "capability_count": by_feature.get(fid, 0),
            }
            for fid, name, description in feature_defs
        ]

    @app.get("/api/v1/features")
    def list_features(store: ChatRepository = Depends(repo)):
        return feature_rows(store)

    @app.get("/api/v1/capabilities")
    def list_capabilities(query: str | None = None, category: str | None = None, status: str | None = None, store: ChatRepository = Depends(repo)):
        return store.list_capabilities(query=query, category=category, status=status)

    @app.post("/api/v1/capabilities", status_code=201)
    def create_capability(body: CapabilityCreate, store: ChatRepository = Depends(repo)):
        now = _now()
        return store.create_capability(
            CapabilityEntry(
                id=str(uuid4()),
                name=body.name,
                description=body.description,
                category=body.category,
                endpoint=body.endpoint,
                permissions=body.permissions,
                status=body.status,
                metadata=body.metadata,
                created_at=now,
                updated_at=now,
            )
        )

    @app.patch("/api/v1/capabilities/{capability_id}")
    def patch_capability(capability_id: str, body: CapabilityUpdate, store: ChatRepository = Depends(repo)):
        capability = store.update_capability(capability_id, body.model_dump(exclude_unset=True), updated_at=_now())
        if capability is None:
            raise NotFoundError(message="Capability not found")
        return capability

    @app.delete("/api/v1/capabilities/{capability_id}", status_code=204)
    def delete_capability(capability_id: str, store: ChatRepository = Depends(repo)):
        if not store.delete_capability(capability_id):
            raise NotFoundError(message="Capability not found or protected")
        return Response(status_code=204)

    def run_capability(capability: CapabilityEntry, body: CapabilityInvocation, store: ChatRepository) -> dict[str, Any]:
        if capability.status != "enabled":
            raise HTTPException(status_code=409, detail="Capability is disabled")
        if body.dry_run:
            return {"input_keys": sorted(body.input.keys()), "preview": f"{capability.name} dry run ready"}
        if capability.name == "agent.planner":
            objective = str(body.input.get("objective", "Complete requested work"))
            return {"steps": [f"Clarify {objective}", "Implement scoped change", "Run verification"], "constraints": body.input.get("constraints", [])}
        if capability.name == "memory.semantic_search":
            results = store.list_memories(query=str(body.input.get("query", "")), limit=int(body.input.get("limit", 5)))
            return {"count": len(results), "results": _jsonable(results)}
        if capability.name == "kernel.capability_registry":
            results = store.list_capabilities(query=str(body.input.get("query", "")) or None)
            return {"count": len(results), "capabilities": _jsonable(results)}
        return {"message": f"{capability.name} executed", "input": body.input}

    @app.post("/api/v1/capabilities/{capability_id}/invoke")
    def invoke_capability(capability_id: str, body: CapabilityInvocation, store: ChatRepository = Depends(repo)):
        capability = store.get_capability(capability_id)
        if capability is None:
            raise NotFoundError(message="Capability not found")
        output = run_capability(capability, body, store)
        now = _now()
        status_text = "dry_run" if body.dry_run else "completed"
        invocation = store.create_capability_invocation(
            CapabilityInvocationRecord(
                id=str(uuid4()),
                capability_id=capability.id,
                capability_name=capability.name,
                status=status_text,
                dry_run=body.dry_run,
                input=body.input,
                output=output,
                error=None,
                created_at=now,
            )
        )
        store.mark_capability_invoked(capability.id, now)
        return {"capability_id": capability.id, "status": status_text, "output": output, "invoked_at": now, "invocation_id": invocation.id}

    @app.get("/api/v1/capabilities/invocations")
    def list_invocations(capability_id: str | None = None, limit: int = Query(default=20, ge=1, le=100), store: ChatRepository = Depends(repo)):
        return store.list_capability_invocations(capability_id=capability_id, limit=limit)

    @app.post("/api/v1/workflows", status_code=201)
    def create_workflow(body: WorkflowCreate, store: ChatRepository = Depends(repo)):
        now = _now()
        return store.create_workflow(
            WorkflowEntry(
                id=str(uuid4()),
                name=body.name,
                trigger=body.trigger,
                steps=body.steps,
                status="enabled",
                conditions=body.conditions,
                schedule=body.schedule,
                external_actions=body.external_actions,
                metadata=body.metadata,
                created_at=now,
                updated_at=now,
            )
        )

    @app.get("/api/v1/workflows")
    def list_workflows(query: str | None = None, status: str | None = None, limit: int = Query(default=20, ge=1, le=100), store: ChatRepository = Depends(repo)):
        return store.list_workflows(query=query, status=status, limit=limit)

    @app.post("/api/v1/workflows/{workflow_id}/run")
    def run_workflow(workflow_id: str, body: dict[str, Any] | None = None, store: ChatRepository = Depends(repo)):
        workflow = store.get_workflow(workflow_id)
        if workflow is None:
            raise NotFoundError(message="Workflow not found")
        payload = body or {}
        dry_run = bool(payload.get("dry_run", True))
        steps = [{"name": step, "status": "dry_run" if dry_run else "completed"} for step in workflow.steps]
        output = {
            "step_count": len(workflow.steps),
            "steps": steps,
            "verification": {"verdict": "pass", "checks": ["steps ordered", "inputs accepted"]},
            "external_actions": [{"name": action, "status": "simulated"} for action in workflow.external_actions],
        }
        now = _now()
        return store.create_workflow_run(
            WorkflowRunRecord(
                id=str(uuid4()),
                workflow_id=workflow.id,
                workflow_name=workflow.name,
                status="dry_run" if dry_run else "completed",
                dry_run=dry_run,
                input=payload.get("input", {}),
                output=output,
                created_at=now,
            )
        )

    @app.get("/api/v1/workflows/runs")
    def list_workflow_runs(workflow_id: str | None = None, limit: int = Query(default=20, ge=1, le=100), store: ChatRepository = Depends(repo)):
        return store.list_workflow_runs(workflow_id=workflow_id, limit=limit)

    @app.get("/api/v1/workflows/verification")
    def workflow_verification(workflow_id: str | None = None, store: ChatRepository = Depends(repo)):
        runs = store.list_workflow_runs(workflow_id=workflow_id, limit=20)
        return [
            {
                "run_id": run.id,
                "workflow_id": run.workflow_id,
                "workflow_name": run.workflow_name,
                "verdict": run.output.get("verification", {}).get("verdict", "pass"),
                "checks": run.output.get("verification", {}).get("checks", []),
                "evidence": [f"{run.status} at {run.created_at}"],
                "created_at": run.created_at,
            }
            for run in runs
        ]

    @app.post("/api/v1/decisions/evaluate")
    def evaluate_decision(body: DecisionRequest):
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

    @app.post("/api/v1/reflection/review")
    def review_reflection(body: ReflectionRequest):
        improvements = ["Add acceptance checks", "Name the next action"]
        return {
            "summary": body.content[:180],
            "issues": ["Verification could be clearer"] if body.criteria else [],
            "improvements": improvements,
            "revised_content": f"{body.content}\n\nReflection improvements:\n- " + "\n- ".join(improvements),
            "quality_score": 84,
            "policy_verdict": "pass",
        }

    @app.get("/api/v1/settings/modules")
    def list_module_settings(store: ChatRepository = Depends(repo)):
        return store.list_module_settings()

    @app.patch("/api/v1/settings/modules/{module_id}")
    def patch_module_setting(module_id: str, body: ModuleSettingUpdate, store: ChatRepository = Depends(repo)):
        setting = store.update_module_setting(module_id, body.enabled, updated_at=_now())
        if setting is None:
            raise NotFoundError(message="Module setting not found")
        return setting

    @app.post("/api/v1/voice/transcribe")
    def transcribe_voice(body: VoiceTranscriptionRequest, store: ChatRepository = Depends(repo)):
        _require_module(store, "voice")
        return {"transcript": body.audio_text, "confidence": 92, "speaker": body.speaker_hint or "User", "wake_word_detected": "jarvis" in body.audio_text.lower()}

    @app.post("/api/v1/voice/synthesize")
    def synthesize_voice(body: VoiceSynthesisRequest, store: ChatRepository = Depends(repo)):
        _require_module(store, "voice")
        return {"text": body.text, "voice_id": body.voice_id, "format": "browser-speech", "audio_url": None, "browser_speech_supported": True}

    @app.post("/api/v1/voice/sentiment")
    def voice_sentiment(body: VoiceSentimentRequest, store: ChatRepository = Depends(repo)):
        _require_module(store, "voice")
        urgent = any(term in body.transcript.lower() for term in ["urgent", "now", "blocked"])
        return {"sentiment": "focused" if not urgent else "urgent", "energy": "high" if urgent else "normal", "urgency_score": 80 if urgent else 25}

    @app.post("/api/v1/skill-graphs/run")
    def run_skill_graph(body: SkillGraphCreate, dry_run: bool = True):
        ordered = body.nodes
        return {"id": str(uuid4()), "name": body.name, "objective": body.objective, "ordered_nodes": ordered, "status": "dry_run" if dry_run else "completed", "execution_plan": [{"node": node, "status": "planned" if dry_run else "completed"} for node in ordered]}

    @app.post("/api/v1/world/facts", status_code=201)
    def create_world_fact(body: WorldFactCreate, store: ChatRepository = Depends(repo)):
        return store.create_world_fact(WorldFact(id=str(uuid4()), subject=body.subject, relation=body.relation, object=body.object, confidence=body.confidence, created_at=_now()))

    @app.get("/api/v1/world/digital-twin")
    def digital_twin(store: ChatRepository = Depends(repo)):
        profile = store.get_profile()
        facts = store.list_world_facts(limit=50)
        return {"profile_id": profile.id, "preferred_name": profile.preferred_name, "domains": profile.domains, "preferences": profile.preferences, "inferred_work_style": profile.communication_style, "known_facts": facts}

    @app.get("/api/v1/connectors")
    def list_connectors():
        return [{"id": cid, "name": name, "provider": name, "status": "ready", "scopes": scopes, "last_sync_at": None} for cid, name, scopes in CONNECTORS]

    @app.post("/api/v1/connectors/{connector_id}/sync")
    def sync_connector(connector_id: str, body: ConnectorSyncRequest):
        provider = next((name for cid, name, _ in CONNECTORS if cid == connector_id), connector_id.title())
        return {"connector_id": connector_id, "status": "dry_run" if body.dry_run else "completed", "records_seen": 3, "actions": [f"Scanned {provider}", f"Matched query: {body.query or 'recent activity'}"]}

    @app.get("/api/v1/connectors/{connector_id}/search")
    def search_connector(connector_id: str, query: str = "recent activity"):
        provider = next((name for cid, name, _ in CONNECTORS if cid == connector_id), connector_id.title())
        return {"connector_id": connector_id, "query": query, "results": [{"source": provider, "title": f"{provider} result", "summary": f"Relevant item for {query}"}]}

    @app.post("/api/v1/capabilities/evolve", status_code=201)
    def evolve_capability(body: CapabilityEvolutionRequest, store: ChatRepository = Depends(repo)):
        now = _now()
        capability = store.create_capability(
            CapabilityEntry(
                id=str(uuid4()),
                name=f"custom.{body.category}.{str(uuid4())[:8]}",
                description=f"{body.objective}: {body.observed_gap}",
                category=body.category,
                endpoint=None,
                permissions=["custom:invoke"],
                status="enabled",
                metadata={"core_feature": "orchestration"},
                created_at=now,
                updated_at=now,
            )
        )
        graph = {"id": str(uuid4()), "name": "Capability evolution", "objective": body.objective, "ordered_nodes": ["agent.planner", "reflection.review"], "status": "completed", "execution_plan": [{"node": "agent.planner", "status": "completed"}, {"node": "reflection.review", "status": "completed"}]}
        return {"proposed_capability": capability, "skill_graph": graph, "verification_plan": ["Invoke dry run", "Review output", "Promote when useful"]}

    @app.post("/api/v1/meetings/analyze")
    def analyze_meeting(body: dict[str, Any], store: ChatRepository = Depends(repo)):
        _require_module(store, "domain_intelligence")
        transcript = str(body.get("transcript", ""))
        return {"title": body.get("title", "Meeting"), "summary": transcript[:180] or "No transcript supplied", "action_items": ["Assign owner", "Confirm next checkpoint"], "jira_stories": ["As a team, track the follow-up action"], "follow_up_email": "Sharing summary and next actions."}

    @app.post("/api/v1/vision/analyze")
    def analyze_vision(body: VisionAnalyzeRequest, store: ChatRepository = Depends(repo)):
        _require_module(store, "domain_intelligence")
        text = body.description.lower()
        objects = [word for word in ["dashboard", "chart", "screen", "robot", "document"] if word in text] or ["scene"]
        risks = [word for word in ["error", "blocked", "warning"] if word in text]
        return {"objects": objects, "observations": [f"Detected {', '.join(objects)}"], "risk_flags": risks, "confidence_score": 82}

    @app.post("/api/v1/trading/analyze")
    def analyze_trading(body: TradingAnalysisRequest, store: ChatRepository = Depends(repo)):
        _require_module(store, "domain_intelligence")
        approval = body.risk_tolerance.lower() == "low"
        return {"symbol": body.symbol.upper(), "signal": "watch", "risk_score": 62 if approval else 44, "rationale": ["Local deterministic analysis only", f"Strategy: {body.strategy}"], "approval_required": approval}

    @app.post("/api/v1/robotics/readiness")
    def robotics_readiness(body: RoboticsReadinessRequest, store: ChatRepository = Depends(repo)):
        _require_module(store, "domain_intelligence")
        return {"task": body.task, "readiness_score": 64, "blockers": ["Confirm safety boundary", "Validate environment sensors"], "checklist": ["Human override available", "Dry-run path", *body.safety_constraints]}

    @app.get("/", include_in_schema=True)
    def root():
        return {"name": settings.app_name, "version": settings.app_version, "docs": "/docs", "health": "/health"}

    return app


app = create_app()
