onimport sqlite3
from datetime import datetime, timezone
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
from .llm import create_llm_provider
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
from .storage import ChatRepository
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


def sse_chunk(event: str, data: str) -> str:
    escaped = data.replace("\n", "\\n")
    return f"event: {event}\ndata: {escaped}\n\n"


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
                paragraph[index:index + max_chars].strip()
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


def run_workflow_locally(
    workflow: WorkflowEntry,
    payload: WorkflowRunRequest,
) -> WorkflowRunRecord:
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
        gate for gate in payload.policy_gates
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
            f"{content}\n\nReflection improvements:\n"
            + "\n".join(f"- {item}" for item in improvements)
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
        sentence for sentence in sentences
        if any(term in sentence.lower() for term in {"action", "todo", "follow up", "assign", "owner"})
    ][:5]
    if not action_items:
        action_items = ["Confirm owners, due dates, and verification criteria."]
    return MeetingAnalyzeResult(
        title=payload.title,
        summary=(sentences[0] if sentences else payload.transcript)[:300],
        action_items=action_items,
        jira_stories=[f"As a user, I need {item[:80]}" for item in action_items],
        follow_up_email=f"Subject: {payload.title} follow-up\n\nSummary: {(sentences[0] if sentences else payload.transcript)[:220]}\n\nActions:\n- " + "\n- ".join(action_items),
    )


def analyze_vision(payload: VisionAnalyzeRequest) -> VisionAnalyzeResult:
    text = f"{payload.description} {payload.context or ''}".lower()
    objects = [
        item for item in ["screen", "document", "chart", "code", "person", "error", "robot", "dashboard"]
        if item in text
    ] or ["scene"]
    risk_flags = [
        item for item in ["error", "blocked", "unsafe", "collision", "private"]
        if item in text
    ]
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
    blockers = []
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
    # Configure logging first
    configure_logging(
        log_level=settings.log_level,
        log_format=settings.log_format,
        environment=settings.environment,
    )

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Gateway service for the ShivaAI Jarvis cognitive assistant.",
    )

    # Register exception handlers for proper error responses with request tracing
    app.add_exception_handler(ShivaAIException, shivaai_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Add middleware (order matters)
    # Request ID needs to be early so downstream logging/handlers can access it
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Security/performance middlewares
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

    # Rate limiting (in-memory stopgap; replace with Redis when distributed cache is used)
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=60,
    )

    # CSRF protection for state-changing methods
    app.add_middleware(CSRFTokenMiddleware)

    return app



    @app.on_event("startup")
    async def startup_event():
        """Initialize services on startup"""
        app_logger = structlog.get_logger("gateway")
        app_logger.info(
            "application_startup",
            event="startup",
            app_name=settings.app_name,
            version=settings.app_version,
        )

    @app.on_event("shutdown")
    async def shutdown_event():
        """Clean up resources on shutdown"""
        app_logger = structlog.get_logger("gateway")
        app_logger.info(
            "application_shutdown",
            event="shutdown",
        )

    @app.get("/")
    async def root() -> dict:
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/health",
        }

    @app.get("/health")
    @app.get("/api/v1/health")
    async def health() -> dict:
        return {
            "status": "healthy",
            "service": "gateway",
            "environment": settings.environment,
            "llm_provider": settings.llm_provider,
        }

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
        from .auth_enhanced import (
            check_account_lockout,
            record_failed_login,
            record_successful_login,
        )

        email = payload.email.lower()
        check_account_lockout(email, settings)

        row = repository.get_user_by_email(payload.email)
        if row is None or not verify_password(payload.password, row["password_hash"]):
            record_failed_login(email, settings)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

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

        # Enforce refresh token type
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user = repository.get_user_by_id(payload["sub"])
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        # Return a new access token (refresh token rotation would require persistence)
        return AuthToken(access_token=create_access_token(user, settings), user=user)

    @app.post("/api/v1/auth/logout", status_code=204)
    async def logout(payload: dict = Depends(get_bearer_payload)) -> Response:
        # Minimal stopgap: without a token blacklist store, we cannot truly revoke stateless JWTs.
        # Clients should discard the token on logout.
        return Response(status_code=204)


    @app.get("/api/v1/auth/me")
    async def me(payload: dict = Depends(get_bearer_payload)) -> UserPublic:
        user = repository.get_user_by_id(payload["sub"])
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    @app.get("/api/v1/admin/users")
    async def list_users(
        limit: int = 50,
        payload: dict = Depends(get_bearer_payload),
    ) -> list[UserPublic]:
        require_role(payload, {"admin"})
        return repository.list_users(limit=max(1, min(limit, 100)))

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

        # Basic guard rails (do not change request schema/behavior)
        if len(payload.content) > MAX_MESSAGE_CONTENT_CHARS:
            payload.content = payload.content[:MAX_MESSAGE_CONTENT_CHARS]
        if payload.max_tokens is not None:
            # Clamp max_tokens to a safe range to reduce abuse
            payload.max_tokens = max(1, min(payload.max_tokens, 2048))

        conversation = repository.get_conversation(payload.conversation_id)

    @app.post("/api/v1/chat/completions")
    async def send_message(payload: MessageRequest) -> Message:
        require_module("chat")
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
            logger.error(
                "llm_http_error",
                error=str(exc),
                request_id=getattr(getattr(payload, "request_id", None), "__str__", lambda: None)(),
            )
            return JSONResponse(
                status_code=502,
                content={"detail": "Upstream LLM provider error", "error": "llm_http_error"},
            )
        except Exception:
            logger.exception("llm_unexpected_error")
            return JSONResponse(
                status_code=500,
                content={"detail": "LLM generation failed", "error": "llm_failed"},
            )


        assistant_message = Message(
            id=str(uuid4()),
            conversation_id=payload.conversation_id,
            role="assistant",
            content=llm_result.content,
            created_at=now_iso(),
            metadata={
                **llm_result.metadata,
                "input_words": len(payload.content.split()),
            }
        )

        repository.add_messages(
            payload.conversation_id,
            [user_message, assistant_message],
            updated_at=assistant_message.created_at,
        )
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
            # SSE keep-alive/comment so proxies establish the stream.
            yield ": stream-start\n\n"
            for word in assistant_message.content.split():
                yield sse_chunk("token", f"{word} ")
            yield sse_chunk("done", assistant_message.model_dump_json())

        headers = {
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream; charset=utf-8",
            "Connection": "keep-alive",
        }
        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers=headers,
        )



    @app.post("/api/v1/memory", status_code=201)
    async def create_memory(payload: MemoryCreate) -> MemoryEntry:
        require_module("memory")
        timestamp = now_iso()
        memory = MemoryEntry(
            id=str(uuid4()),
            content=payload.content,
            category=payload.category,
            source=payload.source,
            conversation_id=payload.conversation_id,
            created_at=timestamp,
            updated_at=timestamp,
        )
        return repository.create_memory(memory)

    @app.get("/api/v1/memory")
    async def list_memory(
        query: str | None = None,
        category: str | None = None,
        limit: int = 20,
    ) -> list[MemoryEntry]:
        require_module("memory")
        return repository.list_memories(query=query, category=category, limit=limit)

    @app.delete("/api/v1/memory/{memory_id}", status_code=204)
    async def delete_memory(memory_id: str) -> Response:
        require_module("memory")
        if not repository.delete_memory(memory_id):
            raise HTTPException(status_code=404, detail="Memory not found")
        return Response(status_code=204)

    @app.post("/api/v1/documents", status_code=201)
    async def create_document(payload: DocumentCreate) -> DocumentEntry:
        require_module("knowledge")
        timestamp = now_iso()
        document_id = str(uuid4())
        chunks = [
            DocumentChunk(
                id=str(uuid4()),
                document_id=document_id,
                index=index,
                content=chunk,
                created_at=timestamp,
            )
            for index, chunk in enumerate(chunk_document(payload.content))
        ]
        document = DocumentEntry(
            id=document_id,
            title=payload.title,
            source=payload.source,
            tags=[tag.strip() for tag in payload.tags if tag.strip()],
            chunk_count=len(chunks),
            created_at=timestamp,
            updated_at=timestamp,
        )
        created = repository.create_document(document, chunks)
        if payload.add_to_memory:
            for chunk in chunks:
                repository.create_memory(
                    MemoryEntry(
                        id=str(uuid4()),
                        content=f"{payload.title}\n\n{chunk.content}",
                        category="knowledge",
                        source=f"document:{payload.source}",
                        conversation_id=None,
                        created_at=timestamp,
                        updated_at=timestamp,
                    )
                )
        return created

    @app.get("/api/v1/documents")
    async def list_documents(limit: int = 20) -> list[DocumentEntry]:
        require_module("knowledge")
        return repository.list_documents(limit=max(1, min(limit, 100)))

    @app.get("/api/v1/documents/search")
    async def search_documents(
        query: str | None = None,
        document_id: str | None = None,
        limit: int = 10,
    ) -> list[DocumentChunk]:
        require_module("knowledge")
        return repository.search_document_chunks(
            query=query,
            document_id=document_id,
            limit=max(1, min(limit, 50)),
        )

    @app.get("/api/v1/documents/{document_id}")
    async def get_document(document_id: str) -> dict:
        require_module("knowledge")
        document = repository.get_document(document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")
        return document

    @app.post("/api/v1/feedback", status_code=201)
    async def create_feedback(payload: FeedbackCreate) -> FeedbackEntry:
        feedback = FeedbackEntry(
            id=str(uuid4()),
            rating=payload.rating,
            category=payload.category,
            comment=payload.comment,
            conversation_id=payload.conversation_id,
            message_id=payload.message_id,
            created_at=now_iso(),
        )
        return repository.create_feedback(feedback)

    @app.get("/api/v1/feedback")
    async def list_feedback(
        conversation_id: str | None = None,
        rating: str | None = None,
        limit: int = 20,
    ) -> list[FeedbackEntry]:
        return repository.list_feedback(
            conversation_id=conversation_id,
            rating=rating,
            limit=max(1, min(limit, 100)),
        )

    @app.get("/api/v1/feedback/summary")
    async def feedback_summary(conversation_id: str | None = None) -> FeedbackSummary:
        return repository.summarize_feedback(conversation_id=conversation_id)

    @app.get("/api/v1/profile")
    async def get_profile() -> AssistantProfile:
        require_module("personalization")
        return repository.get_profile()

    @app.patch("/api/v1/profile")
    async def update_profile(payload: AssistantProfileUpdate) -> AssistantProfile:
        require_module("personalization")
        updates = payload.model_dump(exclude_unset=True)
        if updates.get("communication_style") not in {None, "concise", "balanced", "warm", "technical"}:
            raise HTTPException(status_code=400, detail="Unsupported communication style")
        if updates.get("response_detail") not in {None, "brief", "balanced", "detailed"}:
            raise HTTPException(status_code=400, detail="Unsupported response detail")
        if updates.get("domains") is not None:
            updates["domains"] = [
                str(domain).strip()
                for domain in updates["domains"]
                if str(domain).strip()
            ]
        return repository.update_profile(updates, now_iso())

    @app.get("/api/v1/features")
    async def list_features() -> list[CoreFeature]:
        capabilities = repository.list_capabilities()
        module_settings = {setting.id: setting for setting in repository.list_module_settings()}
        counts: dict[str, int] = {}
        statuses: dict[str, set[str]] = {}
        for capability in capabilities:
            feature_id = str(capability.metadata.get("core_feature", capability.category))
            counts[feature_id] = counts.get(feature_id, 0) + 1
            statuses.setdefault(feature_id, set()).add(capability.status)

        feature_descriptions = {
            "chat": "Persistent chat, LLM routing, SSE streaming, and conversation history.",
            "memory": "Semantic and episodic memory capture with lightweight relevance ranking.",
            "orchestration": "Planner and agent-facing capability dispatch foundation.",
            "governance": "Dynamic capability registry with permission metadata and invoke guardrails.",
            "personalization": "Saved Jarvis communication profile and preference context.",
            "knowledge": "Manual document ingestion and searchable RAG-ready chunks.",
            "workflow": "Local workflow definitions, dry-runs, execution records, and run history.",
            "decision": "Deterministic decision scoring and reflection checks for planning support.",
            "voice": "Browser and API voice loop with transcription, synthesis metadata, sentiment, and speaker hints.",
            "skill_graph": "Ordered skill graph execution over local capability nodes.",
            "world_model": "Persisted world facts and digital twin summaries from profile and known facts.",
            "connectors": "Enterprise connector adapters for Jira, Salesforce, Slack, Teams, Confluence, ServiceNow, and SharePoint.",
            "domain_intelligence": "Vision, meeting, trading, and robotics readiness intelligence endpoints.",
            "capability_evolution": "Local capability evolution engine for proposed capability creation and verification plans.",
        }
        features = []
        for feature_id, description in feature_descriptions.items():
            current_statuses = statuses.get(feature_id, set())
            status_value = "enabled"
            if module_settings.get(feature_id) and not module_settings[feature_id].enabled:
                status_value = "disabled"
            elif "disabled" in current_statuses:
                status_value = "degraded"
            elif "degraded" in current_statuses:
                status_value = "degraded"
            features.append(
                CoreFeature(
                    id=feature_id,
                    name=feature_id.replace("_", " ").title(),
                    status=status_value,
                    description=description,
                    capability_count=counts.get(feature_id, 0),
                )
            )
        return features

    @app.get("/api/v1/settings/modules")
    async def list_module_settings() -> list[ModuleSetting]:
        return repository.list_module_settings()

    @app.patch("/api/v1/settings/modules/{module_id}")
    async def update_module_setting(
        module_id: str,
        payload: ModuleSettingUpdate,
    ) -> ModuleSetting:
        setting = repository.update_module_setting(module_id, payload.enabled, now_iso())
        if setting is None:
            raise HTTPException(status_code=404, detail="Module not found")
        return setting

    @app.post("/api/v1/workflows", status_code=201)
    async def create_workflow(payload: WorkflowCreate) -> WorkflowEntry:
        require_module("workflow")
        cleaned_steps = [step.strip() for step in payload.steps if step.strip()]
        if not cleaned_steps:
            raise HTTPException(status_code=400, detail="Workflow requires at least one step")

        timestamp = now_iso()
        workflow = WorkflowEntry(
            id=str(uuid4()),
            name=payload.name,
            trigger=payload.trigger,
            steps=cleaned_steps,
            status="enabled",
            conditions=[condition.strip() for condition in payload.conditions if condition.strip()],
            schedule=payload.schedule,
            external_actions=[action.strip() for action in payload.external_actions if action.strip()],
            metadata=payload.metadata,
            created_at=timestamp,
            updated_at=timestamp,
        )
        try:
            return repository.create_workflow(workflow)
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="Workflow already exists") from exc

    @app.get("/api/v1/workflows")
    async def list_workflows(
        query: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[WorkflowEntry]:
        require_module("workflow")
        return repository.list_workflows(
            query=query,
            status=status,
            limit=max(1, min(limit, 100)),
        )

    @app.get("/api/v1/workflows/runs")
    async def list_workflow_runs(
        workflow_id: str | None = None,
        limit: int = 20,
    ) -> list[WorkflowRunRecord]:
        require_module("workflow")
        return repository.list_workflow_runs(
            workflow_id=workflow_id,
            limit=max(1, min(limit, 100)),
        )

    @app.get("/api/v1/workflows/verification")
    async def list_workflow_verification_reports(
        workflow_id: str | None = None,
        limit: int = 20,
    ) -> list[WorkflowVerificationReport]:
        require_module("workflow")
        runs = repository.list_workflow_runs(workflow_id=workflow_id, limit=max(1, min(limit, 100)))
        return [verification_report_from_run(run) for run in runs]

    @app.post("/api/v1/workflows/{workflow_id}/run")
    async def run_workflow(
        workflow_id: str,
        payload: WorkflowRunRequest,
    ) -> WorkflowRunRecord:
        require_module("workflow")
        workflow = repository.get_workflow(workflow_id)
        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        if workflow.status != "enabled":
            raise HTTPException(status_code=409, detail="Workflow is not enabled")

        run = run_workflow_locally(workflow, payload)
        return repository.create_workflow_run(run)

    @app.post("/api/v1/decisions/evaluate")
    async def decision_evaluation(payload: DecisionRequest) -> DecisionEvaluation:
        require_module("decision")
        return evaluate_decision(payload)

    @app.post("/api/v1/reflection/review")
    async def reflection_review(payload: ReflectionRequest) -> ReflectionResult:
        require_module("decision")
        return reflect_on_content(payload)

    @app.post("/api/v1/voice/transcribe")
    async def voice_transcribe(payload: VoiceTranscriptionRequest) -> VoiceTranscriptionResult:
        require_module("voice")
        return transcribe_voice(payload)

    @app.post("/api/v1/voice/synthesize")
    async def voice_synthesize(payload: VoiceSynthesisRequest) -> VoiceSynthesisResult:
        require_module("voice")
        return VoiceSynthesisResult(
            text=payload.text,
            voice_id=payload.voice_id,
            format="browser-speech",
            audio_url=None,
            browser_speech_supported=True,
        )

    @app.get("/api/v1/voice/personas")
    async def voice_personas() -> list[dict]:
        require_module("voice")
        return [
            {"id": "jarvis-default", "name": "Jarvis Default", "style": "warm technical"},
            {"id": "jarvis-brief", "name": "Jarvis Brief", "style": "concise operations"},
        ]

    @app.post("/api/v1/voice/sentiment")
    async def voice_sentiment(payload: VoiceSentimentRequest) -> VoiceSentimentResult:
        require_module("voice")
        return analyze_voice_sentiment(payload)

    @app.post("/api/v1/skill-graphs", status_code=201)
    async def create_skill_graph(payload: SkillGraphCreate) -> SkillGraphResult:
        require_module("skill_graph")
        return run_skill_graph(str(uuid4()), payload, SkillGraphRun(dry_run=True))

    @app.post("/api/v1/skill-graphs/run")
    async def execute_skill_graph(payload: SkillGraphCreate, dry_run: bool = True) -> SkillGraphResult:
        require_module("skill_graph")
        return run_skill_graph(str(uuid4()), payload, SkillGraphRun(dry_run=dry_run))

    @app.post("/api/v1/capabilities/evolve", status_code=201)
    async def evolve_capability(payload: CapabilityEvolutionRequest) -> CapabilityEvolutionResult:
        require_module("capability_evolution")
        timestamp = now_iso()
        slug = "-".join(payload.objective.lower().split()[:4]) or "capability"
        capability = CapabilityEntry(
            id=str(uuid4()),
            name=f"{payload.category}.{slug}.{str(uuid4())[:8]}",
            description=f"Auto-proposed capability for: {payload.observed_gap}",
            category=payload.category,
            endpoint=None,
            permissions=[f"{payload.category}:invoke"],
            status="enabled",
            metadata={"core_feature": "capability_evolution", "objective": payload.objective},
            created_at=timestamp,
            updated_at=timestamp,
        )
        created = repository.create_capability(capability)
        graph = run_skill_graph(
            str(uuid4()),
            SkillGraphCreate(
                name=f"Evolve {payload.category} capability",
                objective=payload.objective,
                nodes=["agent.planner", created.name, "reflection.review"],
                edges=[
                    {"from": "agent.planner", "to": created.name},
                    {"from": created.name, "to": "reflection.review"},
                ],
            ),
            SkillGraphRun(dry_run=True),
        )
        return CapabilityEvolutionResult(
            proposed_capability=created,
            skill_graph=graph,
            verification_plan=[
                "Dry-run the proposed capability with representative input.",
                "Review policy gates and permissions.",
                "Add a smoke test before enabling external side effects.",
            ],
        )

    @app.post("/api/v1/world/facts", status_code=201)
    async def create_world_fact(payload: WorldFactCreate) -> WorldFact:
        require_module("world_model")
        return repository.create_world_fact(
            WorldFact(
                id=str(uuid4()),
                subject=payload.subject,
                relation=payload.relation,
                object=payload.object,
                confidence=payload.confidence,
                created_at=now_iso(),
            )
        )

    @app.get("/api/v1/world/facts")
    async def list_world_facts(subject: str | None = None, limit: int = 20) -> list[WorldFact]:
        require_module("world_model")
        return repository.list_world_facts(subject=subject, limit=max(1, min(limit, 100)))

    @app.get("/api/v1/world/digital-twin")
    async def digital_twin() -> DigitalTwin:
        require_module("world_model")
        profile = repository.get_profile()
        facts = repository.list_world_facts(limit=10)
        work_style = f"{profile.communication_style} communication with {profile.response_detail} detail"
        return DigitalTwin(
            profile_id=profile.id,
            preferred_name=profile.preferred_name,
            domains=profile.domains,
            preferences=profile.preferences,
            inferred_work_style=work_style,
            known_facts=facts,
        )

    @app.get("/api/v1/connectors")
    async def list_connectors() -> list[ConnectorEntry]:
        require_module("connectors")
        return enterprise_connectors()

    @app.post("/api/v1/connectors/{connector_id}/sync")
    async def sync_connector(
        connector_id: str,
        payload: ConnectorSyncRequest,
    ) -> ConnectorSyncResult:
        require_module("connectors")
        if connector_id not in {connector.id for connector in enterprise_connectors()}:
            raise HTTPException(status_code=404, detail="Connector not found")
        actions = ["validate credentials", "scan accessible records", "index summaries"]
        if payload.query:
            actions.append(f"filter by query: {payload.query}")
        return ConnectorSyncResult(
            connector_id=connector_id,
            status="dry_run" if payload.dry_run else "completed",
            records_seen=0 if payload.dry_run else 7,
            actions=actions,
        )

    @app.get("/api/v1/connectors/{connector_id}/search")
    async def connector_search(connector_id: str, query: str = "recent activity") -> ConnectorSearchResult:
        require_module("connectors")
        return search_connector_records(connector_id, query)

    @app.post("/api/v1/meetings/analyze")
    async def meeting_analysis(payload: MeetingAnalyzeRequest) -> MeetingAnalyzeResult:
        require_module("domain_intelligence")
        return analyze_meeting(payload)

    @app.post("/api/v1/vision/analyze")
    async def vision_analysis(payload: VisionAnalyzeRequest) -> VisionAnalyzeResult:
        require_module("domain_intelligence")
        return analyze_vision(payload)

    @app.post("/api/v1/trading/analyze")
    async def trading_analysis(payload: TradingAnalysisRequest) -> TradingAnalysisResult:
        require_module("domain_intelligence")
        return analyze_trading(payload)

    @app.post("/api/v1/robotics/readiness")
    async def robotics_readiness(payload: RoboticsReadinessRequest) -> RoboticsReadinessResult:
        require_module("domain_intelligence")
        return assess_robotics(payload)

    @app.post("/api/v1/capabilities", status_code=201)
    async def create_capability(payload: CapabilityCreate) -> CapabilityEntry:
        require_module("governance")
        if payload.status not in {"enabled", "disabled", "degraded"}:
            raise HTTPException(status_code=400, detail="Unsupported capability status")

        timestamp = now_iso()
        capability = CapabilityEntry(
            id=str(uuid4()),
            name=payload.name,
            description=payload.description,
            category=payload.category,
            endpoint=payload.endpoint,
            permissions=payload.permissions,
            status=payload.status,
            metadata=payload.metadata,
            created_at=timestamp,
            updated_at=timestamp,
        )
        try:
            return repository.create_capability(capability)
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="Capability already exists") from exc

    @app.get("/api/v1/capabilities")
    async def list_capabilities(
        query: str | None = None,
        category: str | None = None,
        status: str | None = None,
    ) -> list[CapabilityEntry]:
        require_module("governance")
        return repository.list_capabilities(query=query, category=category, status=status)

    @app.get("/api/v1/capabilities/invocations")
    async def list_capability_invocations(
        capability_id: str | None = None,
        limit: int = 20,
    ) -> list[CapabilityInvocationRecord]:
        require_module("governance")
        return repository.list_capability_invocations(
            capability_id=capability_id,
            limit=max(1, min(limit, 100)),
        )

    @app.get("/api/v1/capabilities/{capability_id}")
    async def get_capability(capability_id: str) -> CapabilityEntry:
        require_module("governance")
        capability = repository.get_capability(capability_id)
        if capability is None:
            raise HTTPException(status_code=404, detail="Capability not found")
        return capability

    @app.patch("/api/v1/capabilities/{capability_id}")
    async def update_capability(capability_id: str, payload: CapabilityUpdate) -> CapabilityEntry:
        require_module("governance")
        updates = payload.model_dump(exclude_unset=True)
        if updates.get("status") and updates["status"] not in {"enabled", "disabled", "degraded"}:
            raise HTTPException(status_code=400, detail="Unsupported capability status")

        capability = repository.update_capability(capability_id, updates, now_iso())
        if capability is None:
            raise HTTPException(status_code=404, detail="Capability not found")
        return capability

    @app.post("/api/v1/capabilities/{capability_id}/invoke")
    async def invoke_capability(
        capability_id: str,
        payload: CapabilityInvocation,
    ) -> CapabilityInvocationResult:
        require_module("governance")
        capability = repository.get_capability(capability_id)
        if capability is None:
            raise HTTPException(status_code=404, detail="Capability not found")
        if capability.status != "enabled":
            raise HTTPException(status_code=409, detail="Capability is not enabled")
        core_feature = str(capability.metadata.get("core_feature", capability.category))
        if core_feature != "governance":
            require_module(core_feature)

        invoked_at = now_iso()
        execution = execute_capability(capability, payload, repository)
        invocation = repository.create_capability_invocation(
            CapabilityInvocationRecord(
                id=str(uuid4()),
                capability_id=capability.id,
                capability_name=capability.name,
                status=execution.status,
                dry_run=payload.dry_run,
                input=payload.input,
                output=execution.output,
                error=execution.error,
                created_at=invoked_at,
            )
        )
        repository.mark_capability_invoked(capability.id, invoked_at)
        return CapabilityInvocationResult(
            capability_id=capability.id,
            status=execution.status,
            invoked_at=invoked_at,
            invocation_id=invocation.id,
            output=execution.output,
        )

    @app.delete("/api/v1/capabilities/{capability_id}", status_code=204)
    async def delete_capability(capability_id: str) -> Response:
        require_module("governance")
        if not repository.delete_capability(capability_id):
            raise HTTPException(status_code=404, detail="Capability not found or protected")
        return Response(status_code=204)

    return app


app = create_app()
