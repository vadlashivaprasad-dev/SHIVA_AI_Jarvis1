from typing import Any

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)
    full_name: str | None = None
    role: str = "user"


class UserLogin(BaseModel):
    email: str
    password: str


class UserPublic(BaseModel):
    id: str
    email: str
    full_name: str | None = None
    role: str
    created_at: str


class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class ConversationCreate(BaseModel):
    title: str | None = None
    system_prompt: str | None = None
    model: str | None = None


class MessageRequest(BaseModel):
    conversation_id: str
    content: str = Field(min_length=1)
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


class Conversation(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0
    system_prompt: str | None = None
    model: str | None = None


class Message(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: str
    metadata: dict | None = None


class ConversationDetail(Conversation):
    messages: list[Message]


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1)
    category: str = "semantic"
    source: str = "manual"
    conversation_id: str | None = None


class MemoryEntry(BaseModel):
    id: str
    content: str
    category: str
    source: str
    conversation_id: str | None = None
    relevance: float | None = None
    created_at: str
    updated_at: str


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    source: str = Field(default="manual", max_length=120)
    tags: list[str] = Field(default_factory=list)
    add_to_memory: bool = True


class DocumentEntry(BaseModel):
    id: str
    title: str
    source: str
    tags: list[str] = Field(default_factory=list)
    chunk_count: int = 0
    created_at: str
    updated_at: str


class DocumentChunk(BaseModel):
    id: str
    document_id: str
    index: int
    content: str
    relevance: float | None = None
    created_at: str


class FeedbackCreate(BaseModel):
    rating: str = Field(pattern="^(positive|negative|correction)$")
    category: str = "response_quality"
    comment: str | None = Field(default=None, max_length=1000)
    conversation_id: str | None = None
    message_id: str | None = None


class FeedbackEntry(BaseModel):
    id: str
    rating: str
    category: str
    comment: str | None = None
    conversation_id: str | None = None
    message_id: str | None = None
    created_at: str


class FeedbackSummary(BaseModel):
    total: int
    by_rating: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)


class AssistantProfileUpdate(BaseModel):
    preferred_name: str | None = Field(default=None, max_length=80)
    communication_style: str | None = Field(default=None, max_length=80)
    response_detail: str | None = Field(default=None, max_length=40)
    domains: list[str] | None = None
    preferences: dict[str, Any] | None = None


class AssistantProfile(BaseModel):
    id: str
    preferred_name: str | None = None
    communication_style: str = "concise"
    response_detail: str = "balanced"
    domains: list[str] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class CapabilityCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=1, max_length=500)
    category: str = Field(default="tool", max_length=80)
    endpoint: str | None = Field(default=None, max_length=300)
    permissions: list[str] = Field(default_factory=list)
    status: str = "enabled"
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=500)
    category: str | None = Field(default=None, max_length=80)
    endpoint: str | None = Field(default=None, max_length=300)
    permissions: list[str] | None = None
    status: str | None = None
    metadata: dict[str, Any] | None = None


class CapabilityEntry(BaseModel):
    id: str
    name: str
    description: str
    category: str
    endpoint: str | None = None
    permissions: list[str] = Field(default_factory=list)
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    last_invoked_at: str | None = None


class CapabilityInvocation(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = True


class CapabilityInvocationResult(BaseModel):
    capability_id: str
    status: str
    output: dict[str, Any]
    invoked_at: str
    invocation_id: str | None = None


class CapabilityInvocationRecord(BaseModel):
    id: str
    capability_id: str
    capability_name: str
    status: str
    dry_run: bool
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: str


class CoreFeature(BaseModel):
    id: str
    name: str
    status: str
    description: str
    capability_count: int = 0


class ModuleSetting(BaseModel):
    id: str
    name: str
    enabled: bool = True
    category: str = "core"
    description: str
    updated_at: str


class ModuleSettingUpdate(BaseModel):
    enabled: bool


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    trigger: str = Field(default="manual", max_length=80)
    steps: list[str] = Field(min_length=1)
    conditions: list[str] = Field(default_factory=list)
    schedule: str | None = Field(default=None, max_length=120)
    external_actions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowEntry(BaseModel):
    id: str
    name: str
    trigger: str
    steps: list[str]
    status: str = "enabled"
    conditions: list[str] = Field(default_factory=list)
    schedule: str | None = None
    external_actions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    last_run_at: str | None = None


class WorkflowRunRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = True


class WorkflowRunRecord(BaseModel):
    id: str
    workflow_id: str
    workflow_name: str
    status: str
    dry_run: bool
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class WorkflowVerificationReport(BaseModel):
    run_id: str
    workflow_id: str
    workflow_name: str
    verdict: str
    checks: list[dict[str, Any]]
    evidence: list[str]
    created_at: str


class DecisionRequest(BaseModel):
    decision: str = Field(min_length=1, max_length=300)
    options: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    expected_impact: str | None = Field(default=None, max_length=300)
    estimated_effort: str | None = Field(default=None, max_length=120)
    policy_gates: list[str] = Field(default_factory=list)


class DecisionEvaluation(BaseModel):
    decision: str
    recommendation: str
    confidence_score: int
    risk_score: int
    cost_score: int
    impact_score: int
    rationale: list[str]
    policy_verdict: str = "approved"
    explainability: dict[str, Any] = Field(default_factory=dict)


class ReflectionRequest(BaseModel):
    content: str = Field(min_length=1)
    criteria: list[str] = Field(default_factory=list)
    auto_correct: bool = True


class ReflectionResult(BaseModel):
    summary: str
    issues: list[str]
    improvements: list[str]
    revised_content: str
    quality_score: int
    policy_verdict: str = "pass"


class VoiceTranscriptionRequest(BaseModel):
    audio_text: str = Field(min_length=1)
    speaker_hint: str | None = Field(default=None, max_length=80)


class VoiceTranscriptionResult(BaseModel):
    transcript: str
    confidence: int
    speaker: str
    wake_word_detected: bool


class VoiceSynthesisRequest(BaseModel):
    text: str = Field(min_length=1)
    voice_id: str = "jarvis-default"
    speed: float = 1
    pitch: float = 1


class VoiceSynthesisResult(BaseModel):
    text: str
    voice_id: str
    format: str
    audio_url: str | None = None
    browser_speech_supported: bool = True


class VoiceSentimentRequest(BaseModel):
    transcript: str = Field(min_length=1)


class VoiceSentimentResult(BaseModel):
    sentiment: str
    energy: str
    urgency_score: int


class SkillGraphCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    objective: str = Field(min_length=1, max_length=300)
    nodes: list[str] = Field(min_length=1)
    edges: list[dict[str, str]] = Field(default_factory=list)


class SkillGraphRun(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = True


class SkillGraphResult(BaseModel):
    id: str
    name: str
    objective: str
    ordered_nodes: list[str]
    status: str
    execution_plan: list[dict[str, Any]]


class CapabilityEvolutionRequest(BaseModel):
    objective: str = Field(min_length=1, max_length=300)
    observed_gap: str = Field(min_length=1, max_length=500)
    category: str = "custom"


class CapabilityEvolutionResult(BaseModel):
    proposed_capability: CapabilityEntry
    skill_graph: SkillGraphResult
    verification_plan: list[str]


class WorldFactCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=120)
    relation: str = Field(min_length=1, max_length=80)
    object: str = Field(min_length=1, max_length=300)
    confidence: int = Field(default=80, ge=0, le=100)


class WorldFact(BaseModel):
    id: str
    subject: str
    relation: str
    object: str
    confidence: int
    created_at: str


class DigitalTwin(BaseModel):
    profile_id: str
    preferred_name: str | None = None
    domains: list[str]
    preferences: dict[str, Any]
    inferred_work_style: str
    known_facts: list[WorldFact]


class ConnectorEntry(BaseModel):
    id: str
    name: str
    provider: str
    status: str
    scopes: list[str]
    last_sync_at: str | None = None


class ConnectorSyncRequest(BaseModel):
    query: str | None = None
    dry_run: bool = True


class ConnectorSyncResult(BaseModel):
    connector_id: str
    status: str
    records_seen: int
    actions: list[str]


class ConnectorSearchResult(BaseModel):
    connector_id: str
    query: str
    results: list[dict[str, Any]]


class MeetingAnalyzeRequest(BaseModel):
    transcript: str = Field(min_length=1)
    title: str = "Meeting"


class MeetingAnalyzeResult(BaseModel):
    title: str
    summary: str
    action_items: list[str]
    jira_stories: list[str]
    follow_up_email: str


class VisionAnalyzeRequest(BaseModel):
    description: str = Field(min_length=1)
    context: str | None = None


class VisionAnalyzeResult(BaseModel):
    objects: list[str]
    observations: list[str]
    risk_flags: list[str]
    confidence_score: int


class TradingAnalysisRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    strategy: str = "balanced"
    risk_tolerance: str = "medium"


class TradingAnalysisResult(BaseModel):
    symbol: str
    signal: str
    risk_score: int
    rationale: list[str]
    approval_required: bool


class RoboticsReadinessRequest(BaseModel):
    task: str = Field(min_length=1, max_length=300)
    environment: str = "unknown"
    safety_constraints: list[str] = Field(default_factory=list)


class RoboticsReadinessResult(BaseModel):
    task: str
    readiness_score: int
    blockers: list[str]
    checklist: list[str]
