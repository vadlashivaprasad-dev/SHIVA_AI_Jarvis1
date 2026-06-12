import json
import sqlite3
from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .app_utils import chunk_text, now_utc, repository, require_module, split_document, sse_event
from .auth import (
    create_access_token,
    get_bearer_payload,
    hash_password,
    require_role,
    verify_password,
)
from .config import get_settings
from .domain_services import (
    connector_provider,
    enterprise_overview_payload,
    evaluate_decision_payload,
    feature_rows,
    list_connectors_payload,
    review_reflection_payload,
    run_capability,
    synthesize_voice_payload,
    transcribe_voice_payload,
    voice_sentiment_payload,
    workflow_run_output,
)
from .errors import (
    ConflictError,
    ErrorCode,
    NotFoundError,
    ShivaAIException,
    generic_exception_handler,
    http_exception_handler,
    shivaai_exception_handler,
)
from .llm import create_llm_provider, get_llm_health
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
    VoiceSentimentRequest,
    VoiceSynthesisRequest,
    VoiceTranscriptionRequest,
    WorkflowCreate,
    WorkflowEntry,
    WorkflowRunRecord,
    WorldFact,
    WorldFactCreate,
)
from .storage import ChatRepository


def _now() -> str:
    return now_utc()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(log_level=settings.log_level, environment=settings.environment)

    app = FastAPI(title="ShivaAI Jarvis - Backend")
    app.state.repository = repository()

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

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(request, exc):
        return await http_exception_handler(request, exc)

    @app.exception_handler(Exception)
    async def _generic_exception_handler(request, exc):
        return await generic_exception_handler(request, exc)

    @app.get("/health")
    def health():
        return {"status": "healthy"}

    @app.get("/ready")
    async def readiness(store: ChatRepository = Depends(repo)):
        checks: dict[str, Any] = {}

        try:
            store.list_module_settings()
            checks["database"] = {"status": "healthy"}
        except Exception as exc:
            checks["database"] = {"status": "unhealthy", "error": str(exc)}

        llm_health = await get_llm_health(settings)
        checks["llm"] = {
            "provider": llm_health.provider,
            "status": llm_health.status,
            "model": llm_health.model,
            "details": llm_health.details,
        }

        ready = checks["database"]["status"] == "healthy" and llm_health.status == "healthy"
        return {
            "status": "ready" if ready else "degraded",
            "app": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "checks": checks,
        }

    @app.get("/api/v1/llm/status")
    async def llm_status():
        llm_health = await get_llm_health(settings)
        return {
            "provider": llm_health.provider,
            "status": llm_health.status,
            "model": llm_health.model,
            "details": llm_health.details,
        }

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
            raise ConflictError(
                code=ErrorCode.RESOURCE_ALREADY_EXISTS, message="Email already exists"
            ) from exc
        return {
            "access_token": create_access_token(user, settings),
            "token_type": "bearer",
            "user": user,
        }

    @app.post("/api/v1/auth/login")
    def login(body: UserLogin, store: ChatRepository = Depends(repo)):
        row = store.get_user_by_email(body.email)
        if row is None or not verify_password(body.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        user = store.get_user_by_id(row["id"])
        return {
            "access_token": create_access_token(user, settings),
            "token_type": "bearer",
            "user": user,
        }

    @app.get("/api/v1/auth/me")
    def me(
        payload: dict[str, Any] = Depends(get_bearer_payload), store: ChatRepository = Depends(repo)
    ):
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

    async def _generate_chat(
        body: MessageRequest, store: ChatRepository
    ) -> tuple[Message, Message, dict[str, Any]]:
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
        store.add_messages(
            body.conversation_id,
            [user_message, assistant_message],
            updated_at=assistant_message.created_at,
        )
        return assistant_message

    @app.post("/api/v1/chat/completions/stream")
    async def chat_completions_stream(body: MessageRequest, store: ChatRepository = Depends(repo)):
        async def gen() -> AsyncGenerator[bytes, None]:
            try:
                user_message, assistant_message, _ = await _generate_chat(body, store)
                for token in chunk_text(assistant_message.content):
                    yield sse_event("token", json.dumps({"text": token}))
                store.add_messages(
                    body.conversation_id,
                    [user_message, assistant_message],
                    updated_at=assistant_message.created_at,
                )
                yield sse_event("done", json.dumps(assistant_message.model_dump()))
            except Exception as exc:
                yield sse_event(
                    "error", json.dumps({"message": str(exc), "code": "LLM_STREAM_ERROR"})
                )

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
            DocumentChunk(
                id=str(uuid4()), document_id="", index=index, content=content, created_at=now
            )
            for index, content in enumerate(split_document(body.content))
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
    def list_documents(
        limit: int = Query(default=20, ge=1, le=100), store: ChatRepository = Depends(repo)
    ):
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

    @app.get("/api/v1/enterprise/overview")
    async def enterprise_overview(store: ChatRepository = Depends(repo)):
        llm_health = await get_llm_health(settings)
        return enterprise_overview_payload(store, llm_health)

    @app.get("/api/v1/features")
    def list_features(store: ChatRepository = Depends(repo)):
        return feature_rows(store)

    @app.get("/api/v1/capabilities")
    def list_capabilities(
        query: str | None = None,
        category: str | None = None,
        status: str | None = None,
        store: ChatRepository = Depends(repo),
    ):
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
    def patch_capability(
        capability_id: str, body: CapabilityUpdate, store: ChatRepository = Depends(repo)
    ):
        capability = store.update_capability(
            capability_id, body.model_dump(exclude_unset=True), updated_at=_now()
        )
        if capability is None:
            raise NotFoundError(message="Capability not found")
        return capability

    @app.delete("/api/v1/capabilities/{capability_id}", status_code=204)
    def delete_capability(capability_id: str, store: ChatRepository = Depends(repo)):
        if not store.delete_capability(capability_id):
            raise NotFoundError(message="Capability not found or protected")
        return Response(status_code=204)

    @app.post("/api/v1/capabilities/{capability_id}/invoke")
    def invoke_capability(
        capability_id: str, body: CapabilityInvocation, store: ChatRepository = Depends(repo)
    ):
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
        return {
            "capability_id": capability.id,
            "status": status_text,
            "output": output,
            "invoked_at": now,
            "invocation_id": invocation.id,
        }

    @app.get("/api/v1/capabilities/invocations")
    def list_invocations(
        capability_id: str | None = None,
        limit: int = Query(default=20, ge=1, le=100),
        store: ChatRepository = Depends(repo),
    ):
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
    def list_workflows(
        query: str | None = None,
        status: str | None = None,
        limit: int = Query(default=20, ge=1, le=100),
        store: ChatRepository = Depends(repo),
    ):
        return store.list_workflows(query=query, status=status, limit=limit)

    @app.post("/api/v1/workflows/{workflow_id}/run")
    def run_workflow(
        workflow_id: str, body: dict[str, Any] | None = None, store: ChatRepository = Depends(repo)
    ):
        workflow = store.get_workflow(workflow_id)
        if workflow is None:
            raise NotFoundError(message="Workflow not found")
        payload = body or {}
        dry_run = bool(payload.get("dry_run", True))
        output = workflow_run_output(workflow, dry_run)
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
    def list_workflow_runs(
        workflow_id: str | None = None,
        limit: int = Query(default=20, ge=1, le=100),
        store: ChatRepository = Depends(repo),
    ):
        return store.list_workflow_runs(workflow_id=workflow_id, limit=limit)

    @app.get("/api/v1/workflows/verification")
    def workflow_verification(
        workflow_id: str | None = None, store: ChatRepository = Depends(repo)
    ):
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
        return evaluate_decision_payload(body)

    @app.post("/api/v1/reflection/review")
    def review_reflection(body: ReflectionRequest):
        return review_reflection_payload(body)

    @app.get("/api/v1/settings/modules")
    def list_module_settings(store: ChatRepository = Depends(repo)):
        return store.list_module_settings()

    @app.patch("/api/v1/settings/modules/{module_id}")
    def patch_module_setting(
        module_id: str, body: ModuleSettingUpdate, store: ChatRepository = Depends(repo)
    ):
        setting = store.update_module_setting(module_id, body.enabled, updated_at=_now())
        if setting is None:
            raise NotFoundError(message="Module setting not found")
        return setting

    @app.post("/api/v1/voice/transcribe")
    def transcribe_voice(body: VoiceTranscriptionRequest, store: ChatRepository = Depends(repo)):
        require_module(store, "voice")
        return transcribe_voice_payload(body)

    @app.post("/api/v1/voice/synthesize")
    def synthesize_voice(body: VoiceSynthesisRequest, store: ChatRepository = Depends(repo)):
        require_module(store, "voice")
        return synthesize_voice_payload(body)

    @app.post("/api/v1/voice/sentiment")
    def voice_sentiment(body: VoiceSentimentRequest, store: ChatRepository = Depends(repo)):
        require_module(store, "voice")
        return voice_sentiment_payload(body)

    @app.post("/api/v1/skill-graphs/run")
    def run_skill_graph(body: SkillGraphCreate, dry_run: bool = True):
        ordered = body.nodes
        return {
            "id": str(uuid4()),
            "name": body.name,
            "objective": body.objective,
            "ordered_nodes": ordered,
            "status": "dry_run" if dry_run else "completed",
            "execution_plan": [
                {"node": node, "status": "planned" if dry_run else "completed"} for node in ordered
            ],
        }

    @app.post("/api/v1/world/facts", status_code=201)
    def create_world_fact(body: WorldFactCreate, store: ChatRepository = Depends(repo)):
        return store.create_world_fact(
            WorldFact(
                id=str(uuid4()),
                subject=body.subject,
                relation=body.relation,
                object=body.object,
                confidence=body.confidence,
                created_at=_now(),
            )
        )

    @app.get("/api/v1/world/digital-twin")
    def digital_twin(store: ChatRepository = Depends(repo)):
        profile = store.get_profile()
        facts = store.list_world_facts(limit=50)
        return {
            "profile_id": profile.id,
            "preferred_name": profile.preferred_name,
            "domains": profile.domains,
            "preferences": profile.preferences,
            "inferred_work_style": profile.communication_style,
            "known_facts": facts,
        }

    @app.get("/api/v1/connectors")
    def list_connectors():
        return list_connectors_payload()

    @app.post("/api/v1/connectors/{connector_id}/sync")
    def sync_connector(connector_id: str, body: ConnectorSyncRequest):
        provider = connector_provider(connector_id)
        return {
            "connector_id": connector_id,
            "status": "dry_run" if body.dry_run else "completed",
            "records_seen": 3,
            "actions": [f"Scanned {provider}", f"Matched query: {body.query or 'recent activity'}"],
        }

    @app.get("/api/v1/connectors/{connector_id}/search")
    def search_connector(connector_id: str, query: str = "recent activity"):
        provider = connector_provider(connector_id)
        return {
            "connector_id": connector_id,
            "query": query,
            "results": [
                {
                    "source": provider,
                    "title": f"{provider} result",
                    "summary": f"Relevant item for {query}",
                }
            ],
        }

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
        graph = {
            "id": str(uuid4()),
            "name": "Capability evolution",
            "objective": body.objective,
            "ordered_nodes": ["agent.planner", "reflection.review"],
            "status": "completed",
            "execution_plan": [
                {"node": "agent.planner", "status": "completed"},
                {"node": "reflection.review", "status": "completed"},
            ],
        }
        return {
            "proposed_capability": capability,
            "skill_graph": graph,
            "verification_plan": ["Invoke dry run", "Review output", "Promote when useful"],
        }

    @app.post("/api/v1/meetings/analyze")
    def analyze_meeting(body: dict[str, Any], store: ChatRepository = Depends(repo)):
        require_module(store, "domain_intelligence")
        transcript = str(body.get("transcript", ""))
        return {
            "title": body.get("title", "Meeting"),
            "summary": transcript[:180] or "No transcript supplied",
            "action_items": ["Assign owner", "Confirm next checkpoint"],
            "jira_stories": ["As a team, track the follow-up action"],
            "follow_up_email": "Sharing summary and next actions.",
        }

    @app.post("/api/v1/vision/analyze")
    def analyze_vision(body: VisionAnalyzeRequest, store: ChatRepository = Depends(repo)):
        require_module(store, "domain_intelligence")
        text = body.description.lower()
        objects = [
            word for word in ["dashboard", "chart", "screen", "robot", "document"] if word in text
        ] or ["scene"]
        risks = [word for word in ["error", "blocked", "warning"] if word in text]
        return {
            "objects": objects,
            "observations": [f"Detected {', '.join(objects)}"],
            "risk_flags": risks,
            "confidence_score": 82,
        }

    @app.post("/api/v1/trading/analyze")
    def analyze_trading(body: TradingAnalysisRequest, store: ChatRepository = Depends(repo)):
        require_module(store, "domain_intelligence")
        approval = body.risk_tolerance.lower() == "low"
        return {
            "symbol": body.symbol.upper(),
            "signal": "watch",
            "risk_score": 62 if approval else 44,
            "rationale": ["Local deterministic analysis only", f"Strategy: {body.strategy}"],
            "approval_required": approval,
        }

    @app.post("/api/v1/robotics/readiness")
    def robotics_readiness(body: RoboticsReadinessRequest, store: ChatRepository = Depends(repo)):
        require_module(store, "domain_intelligence")
        return {
            "task": body.task,
            "readiness_score": 64,
            "blockers": ["Confirm safety boundary", "Validate environment sensors"],
            "checklist": ["Human override available", "Dry-run path", *body.safety_constraints],
        }

    @app.get("/", include_in_schema=True)
    def root():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()
