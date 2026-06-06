# NOTE: This file is the fully runnable version of `main_sse_fixed.py`.
# It applies the SSE contract fix directly to the main gateway routes.
#
# Run this file with: uvicorn services/gateway/src/main_sse_fixed_full:app --reload --port 8000

import sqlite3
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import structlog
import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .errors import shivaai_exception_handler, generic_exception_handler, ShivaAIException
from .logging import RequestIDMiddleware, LoggingMiddleware, configure_logging

from .auth import create_access_token, get_bearer_payload, hash_password, require_role, verify_password
from .capabilities import execute_capability
from .config import get_settings

from .llm_retry import create_llm_provider
from .storage import ChatRepository

from .schemas import (
    AssistantProfile,
    AssistantProfileUpdate,
    AuthToken,
    CapabilityCreate,
    CapabilityEntry,
    CapabilityEvolutionRequest,
    CapabilityEvolutionResult,
    CapabilityInvocation,
    CapabilityInvocationRecord,
    CapabilityInvocationResult,
    CapabilityUpdate,
    Conversation,
    ConversationCreate,
    CoreFeature,
    DecisionEvaluation,
    DecisionRequest,
    DigitalTwin,
    DocumentChunk,
    DocumentCreate,
    DocumentEntry,
    FeedbackCreate,
    FeedbackEntry,
    FeedbackSummary,
    ConnectorEntry,
    ConnectorSearchResult,
    ConnectorSyncRequest,
    ConnectorSyncResult,
    MemoryCreate,
    MemoryEntry,
    MeetingAnalyzeRequest,
    MeetingAnalyzeResult,
    Message,
    MessageRequest,
    ModuleSetting,
    ModuleSettingUpdate,
    ReflectionRequest,
    ReflectionResult,
    RoboticsReadinessRequest,
    RoboticsReadinessResult,
    SkillGraphCreate,
    SkillGraphResult,
    SkillGraphRun,
    TradingAnalysisRequest,
    TradingAnalysisResult,
    UserCreate,
    UserLogin,
    UserPublic,
    VisionAnalyzeRequest,
    VisionAnalyzeResult,
    VoiceSentimentRequest,
    VoiceSentimentResult,
    VoiceSynthesisRequest,
    VoiceSynthesisResult,
    VoiceTranscriptionRequest,
    VoiceTranscriptionResult,
    WorldFact,
    WorldFactCreate,
    WorkflowCreate,
    WorkflowEntry,
    WorkflowRunRecord,
    WorkflowRunRequest,
    WorkflowVerificationReport,
)

from pathlib import Path


MAX_EPISODIC_MEMORY_CHARS = 6000
MAX_MESSAGE_CONTENT_CHARS = 8000

settings = get_settings()

# Initialize repository with SQLite database in data/ directory
data_dir = Path(__file__).parent.parent.parent.parent / "data"
data_dir.mkdir(parents=True, exist_ok=True)
database_path = data_dir / "chat.db"
repository = ChatRepository(str(database_path))
llm_provider = create_llm_provider(settings)

# Configure structlog (base) - middleware/modules may also reconfigure via configure_logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("gateway")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_module(module_id: str) -> None:
    setting = repository.get_module_setting(module_id)
    if setting is not None and not setting.enabled:
        raise HTTPException(status_code=403, detail=f"{setting.name} module is disabled")


def sse_event(event: str, payload: object) -> str:
    """Build an SSE event with safe JSON payload.

    Important: This sends JSON that is safe inside the SSE `data:` field.
    - payload is JSON-stringified
    - raw newlines inside JSON are escaped
    - client can safely parse `data` for `event: done`
    """
    import json

    data = json.dumps(payload, ensure_ascii=False)
    data = data.replace("\r", "").replace("\n", "\\n")
    return f"event: {event}\ndata: {data}\n\n"


def profile_system_prompt(profile: AssistantProfile) -> str:
    parts = [
        "Use the saved ShivaAI Jarvis user profile when responding.",
        f"Communication style: {profile.communication_style}.",
        f"Response detail: {profile.response_detail}.",
    ]
    if profile.preferred_name:
        parts.append(f"Address the user as {profile.preferred_name} when natural.")
    if profile.domains:
        parts.append(f"User focus domains: {', '.join(profile.domains)}.")
    if profile.preferences:
        preferences = "; ".join(
            f"{key}: {value}" for key, value in sorted(profile.preferences.items())
        )
        parts.append(f"Additional preferences: {preferences}.")
    return " ".join(parts)


def chunk_document(content: str, max_chars: int = 900) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in content.splitlines() if paragraph.strip()]
    if not paragraphs:
        paragraphs = [content.strip()]

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(
                paragraph[index : index + max_chars].strip()
                for index in range(0, len(paragraph), max_chars)
            )
            continue

        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) > max_chars and current:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate

    if current:
        chunks.append(current)
    return [chunk for chunk in chunks if chunk]


def truncate_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars].rstrip()}\n\n[truncated]"


# --- Deterministic local intelligence helpers (unchanged from main.py) ---

def run_workflow_locally(workflow: WorkflowEntry, payload: WorkflowRunRequest) -> WorkflowRunRecord:
    output_steps = [
        {
            "index": index,
            "name": step,
            "status": "preview" if payload.dry_run else "completed",
            "message": (
                "Step previewed without side effects."
                if payload.dry_run
                else "Step completed by the local workflow executor."
            ),
        }
        for index, step in enumerate(workflow.steps, start=1)
    ]
    status_value = "dry_run" if payload.dry_run else "completed"
    condition_checks = [
        {
            "condition": condition,
            "passed": condition.lower() not in {"blocked", "requires_external_secret"},
        }
        for condition in workflow.conditions
    ]
    action_results = [
        {
            "action": action,
            "status": "preview" if payload.dry_run else "simulated",
            "message": "External action adapter was not called in local mode.",
        }
        for action in workflow.external_actions
    ]
    verification = {
        "verdict": "pass" if all(check["passed"] for check in condition_checks) else "review",
        "checks": [
            {"name": "steps_defined", "passed": len(workflow.steps) > 0},
            {"name": "conditions_satisfied", "passed": all(check["passed"] for check in condition_checks)},
            {"name": "external_actions_guarded", "passed": True},
        ],
        "evidence": [
            f"{len(output_steps)} workflow steps evaluated.",
            f"{len(condition_checks)} conditions checked.",
            f"{len(action_results)} external actions guarded.",
        ],
    }
    return WorkflowRunRecord(
        id=str(uuid4()),
        workflow_id=workflow.id,
        workflow_name=workflow.name,
        status=status_value,
        dry_run=payload.dry_run,
        input=payload.input,
        output={
            "trigger": workflow.trigger,
            "schedule": workflow.schedule,
            "step_count": len(workflow.steps),
            "steps": output_steps,
            "conditions": condition_checks,
            "external_actions": action_results,
            "verification": verification,
            "message": (
                "Workflow execution preview recorded."
                if payload.dry_run
                else "Workflow completed in local deterministic mode."
            ),
        },
        created_at=now_iso(),
    )


def evaluate_decision(payload: DecisionRequest) -> DecisionEvaluation:
    risk_count = len(payload.risks)
    option_count = len(payload.options)
    confidence = max(35, min(95, 82 + min(option_count, 4) * 3 - risk_count * 8))
    risk = max(5, min(95, 20 + risk_count * 18))
    cost = 45
    effort = (payload.estimated_effort or "").lower()
    if any(term in effort for term in {"high", "large", "month", "quarter"}):
        cost = 75
    elif any(term in effort for term in {"low", "small", "hour", "day"}):
        cost = 25

    impact = 60
    expected_impact = (payload.expected_impact or "").lower()
    if any(term in expected_impact for term in {"high", "critical", "revenue", "security"}):
        impact = 85
    elif any(term in expected_impact for term in {"low", "minor"}):
        impact = 35

    recommendation = payload.options[0] if payload.options else payload.decision
    rationale = [
        f"Evaluated {option_count or 1} option(s).",
        f"Detected {risk_count} explicit risk(s).",
        "Scores are deterministic local heuristics for planning support.",
    ]
    if risk > 60:
        rationale.append("Risk is elevated; require review before execution.")
    if confidence >= 75 and impact >= 70:
        rationale.append("High confidence and impact favor proceeding with safeguards.")
    blocked_gates = [
        gate
        for gate in payload.policy_gates
        if gate.lower() in {"human_approval", "security_review"} and risk > 60
    ]
    policy_verdict = "requires_review" if blocked_gates or risk > 70 else "approved"

    return DecisionEvaluation(
        decision=payload.decision,
        recommendation=recommendation,
        confidence_score=confidence,
        risk_score=risk,
        cost_score=cost,
        impact_score=impact,
        rationale=rationale,
        policy_verdict=policy_verdict,
        explainability={
            "option_count": option_count,
            "risk_count": risk_count,
            "policy_gates": payload.policy_gates,
            "blocked_gates": blocked_gates,
            "scoring_mode": "local_deterministic",
        },
    )


def reflect_on_content(payload: ReflectionRequest) -> ReflectionResult:
    content = payload.content.strip()
    criteria = payload.criteria or ["clarity", "completeness", "risk"]
    issues: list[str] = []
    improvements: list[str] = []

    if len(content.split()) < 20:
        issues.append("Content is brief and may miss context.")
        improvements.append("Add objective, constraints, and expected outcome.")
    if "test" not in content.lower():
        issues.append("Testing or verification is not mentioned.")
        improvements.append("Include a concrete verification step.")
    if "risk" not in content.lower():
        issues.append("Risks are not explicitly called out.")
        improvements.append("Add known risks or state that no major risks are known.")

    quality = max(40, 92 - len(issues) * 12)
    revised = content
    if improvements and payload.auto_correct:
        revised = (
            f"{content}\n\nReflection improvements:\n" + "\n".join(f"- {item}" for item in improvements)
        )
    policy_verdict = "revise" if quality < 80 else "pass"

    return ReflectionResult(
        summary=f"Reviewed content against: {', '.join(criteria)}.",
        issues=issues,
        improvements=improvements,
        revised_content=revised,
        quality_score=quality,
        policy_verdict=policy_verdict,
    )


def transcribe_voice(payload: VoiceTranscriptionRequest) -> VoiceTranscriptionResult:
    transcript = payload.audio_text.strip()
    speaker = payload.speaker_hint or ("Keerthi" if "keerthi" in transcript.lower() else "unknown")
    return VoiceTranscriptionResult(
        transcript=transcript,
        confidence=92 if len(transcript.split()) >= 3 else 76,
        speaker=speaker,
        wake_word_detected="jarvis" in transcript.lower() or "shiva" in transcript.lower(),
    )


def analyze_voice_sentiment(payload: VoiceSentimentRequest) -> VoiceSentimentResult:
    text = payload.transcript.lower()
    urgent_terms = {"urgent", "asap", "critical", "blocked", "failed", "now"}
    positive_terms = {"great", "good", "done", "thanks", "perfect"}
    urgency = min(95, 25 + sum(1 for term in urgent_terms if term in text) * 20)
    sentiment = "positive" if any(term in text for term in positive_terms) else "neutral"
    if urgency >= 65:
        sentiment = "urgent"
    return VoiceSentimentResult(
        sentiment=sentiment,
        energy="high" if "!" in payload.transcript or urgency >= 65 else "steady",
        urgency_score=urgency,
    )


def run_skill_graph(graph_id: str, payload: SkillGraphCreate, run: SkillGraphRun) -> SkillGraphResult:
    execution_plan = [
        {
            "index": index,
            "node": node,
            "status": "preview" if run.dry_run else "completed",
            "input_keys": sorted(run.input.keys()),
        }
        for index, node in enumerate(payload.nodes, start=1)
    ]
    return SkillGraphResult(
        id=graph_id,
        name=payload.name,
        objective=payload.objective,
        ordered_nodes=payload.nodes,
        status="dry_run" if run.dry_run else "completed",
        execution_plan=execution_plan,
    )


def enterprise_connectors() -> list[ConnectorEntry]:
    providers = ["Jira", "Salesforce", "Slack", "Teams", "Confluence", "ServiceNow", "SharePoint"]
    return [
        ConnectorEntry(
            id=provider.lower().replace(" ", "-"),
            name=f"{provider} connector",
            provider=provider,
            status="ready",
            scopes=["search", "sync", "summarize"],
        )
        for provider in providers
    ]


def search_connector_records(connector_id: str, query: str) -> ConnectorSearchResult:
    connector = next((item for item in enterprise_connectors() if item.id == connector_id), None)
    if connector is None:
        raise HTTPException(status_code=404, detail="Connector not found")
    base = query.strip() or "recent activity"
    return ConnectorSearchResult(
        connector_id=connector_id,
        query=base,
        results=[
            {
                "id": f"{connector_id}-local-1",
                "title": f"{connector.provider} result for {base}",
                "summary": "Local adapter search result ready for indexing and review.",
                "source": connector.provider,
            },
            {
                "id": f"{connector_id}-local-2",
                "title": f"{connector.provider} follow-up candidate",
                "summary": "Use sync to convert this result into local document memory.",
                "source": connector.provider,
            },
        ],
    )


def verification_report_from_run(run: WorkflowRunRecord) -> WorkflowVerificationReport:
    verification = run.output.get("verification", {})
    return WorkflowVerificationReport(
        run_id=run.id,
        workflow_id=run.workflow_id,
        workflow_name=run.workflow_name,
        verdict=str(verification.get("verdict", "unknown")),
        checks=list(verification.get("checks", [])),
        evidence=list(verification.get("evidence", [])),
        created_at=run.created_at,
    )


def analyze_meeting(payload: MeetingAnalyzeRequest) -> MeetingAnalyzeResult:
    sentences = [item.strip() for item in payload.transcript.replace("\n", " ").split(".") if item.strip()]
    action_items = [
        sentence
        for sentence in sentences
        if any(term in sentence.lower() for term in {"action", "todo", "follow up", "assign", "owner"})
    ][:5]
    if not action_items:
        action_items = ["Confirm owners, due dates, and verification criteria."]
    return MeetingAnalyzeResult(
        title=payload.title,
        summary=(sentences[0] if sentences else payload.transcript)[:300],
        action_items=action_items,
        jira_stories=[f"As a user, I need {item[:80]}" for item in action_items],
        follow_up_email=f"Subject: {payload.title} follow-up\n\nSummary: {(sentences[0] if sentences else payload.transcript)[:220]}\n\nActions:\n- "
        + "\n- ".join(action_items),
    )


def analyze_vision(payload: VisionAnalyzeRequest):
    text = f"{payload.description} {payload.context or ''}".lower()
    objects = [
        item
        for item in ["screen", "document", "chart", "code", "person", "error", "robot", "dashboard"]
        if item in text
    ] or ["scene"]
    risk_flags = [item for item in ["error", "blocked", "unsafe", "collision", "private"] if item in text]
    return VisionAnalyzeResult(
        objects=objects,
        observations=[f"Detected {item} context from the supplied visual description." for item in objects],
        risk_flags=risk_flags,
        confidence_score=88 if objects != ["scene"] else 62,
    )


def analyze_trading(payload: TradingAnalysisRequest) -> TradingAnalysisResult:
    high_risk = payload.risk_tolerance.lower() == "high"
    conservative = payload.risk_tolerance.lower() in {"low", "conservative"}
    risk_score = 35 if conservative else 68 if high_risk else 52
    signal = "watch" if risk_score > 60 else "paper_trade"
    return TradingAnalysisResult(
        symbol=payload.symbol.upper(),
        signal=signal,
        risk_score=risk_score,
        rationale=[
            f"Strategy mode: {payload.strategy}.",
            f"Risk tolerance: {payload.risk_tolerance}.",
            "Local mode does not execute live trades; it prepares human-in-the-loop analysis.",
        ],
        approval_required=True,
    )


def assess_robotics(payload: RoboticsReadinessRequest) -> RoboticsReadinessResult:
    blockers: list[str] = []
    if not payload.safety_constraints:
        blockers.append("Safety constraints are required before physical execution.")
    if payload.environment == "unknown":
        blockers.append("Environment must be specified.")
    score = max(20, 90 - len(blockers) * 25)
    return RoboticsReadinessResult(
        task=payload.task,
        readiness_score=score,
        blockers=blockers,
        checklist=[
            "Validate environment map",
            "Confirm human override path",
            "Run dry-run simulation",
            "Record verification evidence",
        ],
    )


def create_app() -> FastAPI:
    configure_logging(log_level=settings.log_level, log_format=settings.log_format, environment=settings.environment)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Gateway service for the ShivaAI Jarvis cognitive assistant.",
    )

    app.add_exception_handler(ShivaAIException, shivaai_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: Any) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None) or str(uuid4())
        return JSONResponse(
            status_code=404,
            content={
                "code": "RES_001",
                "message": "Resource not found",
                "severity": "error",
                "request_id": request_id,
                "timestamp": now_iso(),
                "status_code": 404,
                "user_message": "Not Found",
            },
        )

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from .middleware import (
        CSRFTokenMiddleware,
        InputValidationMiddleware,
        PerformanceMetricsMiddleware,
        RateLimitMiddleware,
        SecurityHeadersMiddleware,
        TrustedHostMiddleware,
    )

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    app.add_middleware(InputValidationMiddleware)
    app.add_middleware(PerformanceMetricsMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    app.add_middleware(RateLimitMiddleware, requests_per_minute=1000)
    app.add_middleware(CSRFTokenMiddleware)

    @app.on_event("startup")
    async def startup_event():
        app_logger = structlog.get_logger("gateway")
        app_logger.info("application_startup", app_name=settings.app_name, version=settings.app_version)

    @app.on_event("shutdown")
    async def shutdown_event():
        # Avoid importing/using SQLAlchemy shutdown hooks in this SSE-fixed dev file.
        # Also avoid structlog event kwarg collision.
        app_logger = structlog.get_logger("gateway")




    @app.get("/")
    async def root() -> dict:
        return {"name": settings.app_name, "version": settings.app_version, "docs": "/docs", "health": "/health"}

    @app.get("/health")
    @app.get("/api/v1/health")
    async def health() -> dict:
        return {"status": "healthy", "service": "gateway", "environment": settings.environment, "llm_provider": settings.llm_provider}

    # ---- Auth ----
    @app.post("/api/v1/auth/signup", status_code=201)
    async def signup(payload: UserCreate) -> AuthToken:
        if payload.role not in {"admin", "user", "analyst", "trader"}:
            raise HTTPException(status_code=400, detail="Unsupported role")
        if repository.get_user_by_email(payload.email):
            raise HTTPException(status_code=409, detail="User already exists")

        timestamp = now_iso()
        user = repository.create_user(
            user_id=str(uuid4()),
            email=payload.email,
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
            role=payload.role,
            created_at=timestamp,
        )
        return AuthToken(access_token=create_access_token(user, settings), user=user)

    @app.post("/api/v1/auth/login")
    async def login(payload: UserLogin) -> AuthToken:
        from .auth_enhanced import check_account_lockout, record_failed_login, record_successful_login

        email = payload.email.lower()
        check_account_lockout(email, settings)

        row = repository.get_user_by_email(payload.email)
        if row is None or not verify_password(payload.password, row["password_hash"]):
            record_failed_login(email, settings)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        record_successful_login(email)

        user = UserPublic(
            id=row["id"],
            email=row["email"],
            full_name=row["full_name"],
            role=row["role"],
            created_at=row["created_at"],
        )
        return AuthToken(access_token=create_access_token(user, settings), user=user)

    @app.post("/api/v1/auth/refresh")
    async def refresh(payload: dict = Depends(get_bearer_payload)) -> AuthToken:
        from .auth_enhanced import create_refresh_token

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user = repository.get_user_by_id(payload["sub"])
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        return AuthToken(access_token=create_access_token(user, settings), user=user)

    @app.post("/api/v1/auth/logout", status_code=204)
    async def logout(payload: dict = Depends(get_bearer_payload)) -> Response:
        return Response(status_code=204)

    @app.get("/api/v1/auth/me")
    async def me(payload: dict = Depends(get_bearer_payload)) -> UserPublic:
        user = repository.get_user_by_id(payload["sub"])
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    @app.get("/api/v1/admin/users")
    async def list_users(limit: int = 50, payload: dict = Depends(get_bearer_payload)) -> list[UserPublic]:
        require_role(payload, {"admin"})
        return repository.list_users(limit=max(1, min(limit, 100)))

    # ---- Chat ----
    @app.post("/api/v1/chat/sessions", status_code=201)
    async def create_conversation(payload: ConversationCreate) -> Conversation:
        require_module("chat")
        timestamp = now_iso()
        conversation = Conversation(
            id=str(uuid4()),
            title=payload.title or "New conversation",
            system_prompt=payload.system_prompt,
            model=payload.model,
            created_at=timestamp,
            updated_at=timestamp,
        )
        return repository.create_conversation(conversation)

    @app.get("/api/v1/chat/sessions")
    async def list_conversations() -> list[Conversation]:
        require_module("chat")
        return repository.list_conversations()

    @app.get("/api/v1/chat/sessions/{conversation_id}")
    async def get_conversation(conversation_id: str) -> dict:
        require_module("chat")
        conversation = repository.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation.model_dump()

    @app.post("/api/v1/chat/completions")
    async def send_message(payload: MessageRequest) -> Message:
        require_module("chat")

        if len(payload.content) > MAX_MESSAGE_CONTENT_CHARS:
            payload.content = payload.content[:MAX_MESSAGE_CONTENT_CHARS]
        if payload.max_tokens is not None:
            payload.max_tokens = max(1, min(payload.max_tokens, 2048))

        conversation = repository.get_conversation(payload.conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

        timestamp = now_iso()
        user_message = Message(
            id=str(uuid4()),
            conversation_id=payload.conversation_id,
            role="user",
            content=payload.content,
            created_at=timestamp,
        )

        profile = repository.get_profile()
        history = [
            Message(
                id="profile",
                conversation_id=conversation.id,
                role="system",
                content=profile_system_prompt(profile),
                created_at=profile.updated_at,
            ),
            *conversation.messages,
        ]
        if conversation.system_prompt:
            history = [
                Message(
                    id="system",
                    conversation_id=conversation.id,
                    role="system",
                    content=conversation.system_prompt,
                    created_at=conversation.created_at,
                ),
                *history,
            ]

        relevant_memories = repository.list_memories(query=payload.content, limit=5)
        try:
            llm_result = await llm_provider.generate(
                prompt=payload.content,
                history=history,
                memories=[memory.content for memory in relevant_memories],
                model=payload.model or conversation.model,
                temperature=payload.temperature,
                max_tokens=payload.max_tokens,
            )
        except httpx.HTTPError as exc:
            logger.error("llm_http_error", error=str(exc))
            return JSONResponse(status_code=502, content={"detail": "Upstream LLM provider error", "error": "llm_http_error"})
        except Exception:
            logger.exception("llm_unexpected_error")
            return JSONResponse(status_code=500, content={"detail": "LLM generation failed", "error": "llm_failed"})

        assistant_message = Message(
            id=str(uuid4()),
            conversation_id=payload.conversation_id,
            role="assistant",
            content=llm_result.content,
            created_at=now_iso(),
            metadata={**llm_result.metadata, "input_words": len(payload.content.split())},
        )

        repository.add_messages(payload.conversation_id, [user_message, assistant_message], updated_at=assistant_message.created_at)
        repository.create_memory(
            MemoryEntry(
                id=str(uuid4()),
                content=truncate_text(
                    f"User said: {payload.content}\nAssistant replied: {assistant_message.content}",
                    MAX_EPISODIC_MEMORY_CHARS,
                ),
                category="episodic",
                source="chat",
                conversation_id=payload.conversation_id,
                created_at=assistant_message.created_at,
                updated_at=assistant_message.created_at,
            )
        )

        return assistant_message

    @app.post("/api/v1/chat/completions/stream")
    async def stream_message(payload: MessageRequest) -> StreamingResponse:
        assistant_message = await send_message(payload)

        async def events():
            yield ": stream-start\n\n"
            for word in assistant_message.content.split():
                yield sse_event("token", {"text": f"{word} "})
            yield sse_event("done", assistant_message.model_dump())

        headers = {
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream; charset=utf-8",
            "Connection": "keep-alive",
        }
        return StreamingResponse(events(), media_type="text/event-stream", headers=headers)

    # NOTE: For brevity in this “fixed full” file, not all endpoints from main.py
    # are included. If you need 1:1 parity, swap `main.py` with this SSE change
    # using the new `sse_event()` function and stream endpoint logic.
    return app


app = create_app()

