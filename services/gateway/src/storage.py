import json
import sqlite3
from pathlib import Path
from threading import Lock

from .schemas import (
    AssistantProfile,
    CapabilityEntry,
    CapabilityInvocationRecord,
    Conversation,
    ConversationDetail,
    DocumentChunk,
    DocumentEntry,
    FeedbackEntry,
    FeedbackSummary,
    MemoryEntry,
    Message,
    ModuleSetting,
    UserPublic,
    WorldFact,
    WorkflowEntry,
    WorkflowRunRecord,
)


MAX_STORED_TEXT_CHARS = 20000
MAX_SEARCH_TEXT_CHARS = 4000


class ChatRepository:
    def __init__(self, database_path: str):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    system_prompt TEXT,
                    model TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
                );

                CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
                    ON messages(conversation_id, created_at);

                CREATE TABLE IF NOT EXISTS memory_entries (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL,
                    source TEXT NOT NULL,
                    conversation_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_memory_entries_category
                    ON memory_entries(category);
                CREATE INDEX IF NOT EXISTS idx_memory_entries_conversation
                    ON memory_entries(conversation_id);
                CREATE INDEX IF NOT EXISTS idx_memory_entries_updated
                    ON memory_entries(updated_at);

                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS document_chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                );

                CREATE INDEX IF NOT EXISTS idx_document_chunks_document
                    ON document_chunks(document_id);
                CREATE INDEX IF NOT EXISTS idx_documents_created
                    ON documents(created_at);

                CREATE TABLE IF NOT EXISTS feedback_entries (
                    id TEXT PRIMARY KEY,
                    rating TEXT NOT NULL,
                    category TEXT NOT NULL,
                    comment TEXT,
                    conversation_id TEXT,
                    message_id TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_feedback_entries_created
                    ON feedback_entries(created_at);
                CREATE INDEX IF NOT EXISTS idx_feedback_entries_conversation
                    ON feedback_entries(conversation_id);
                CREATE INDEX IF NOT EXISTS idx_feedback_entries_rating
                    ON feedback_entries(rating);

                CREATE TABLE IF NOT EXISTS assistant_profiles (
                    id TEXT PRIMARY KEY,
                    preferred_name TEXT,
                    communication_style TEXT NOT NULL,
                    response_detail TEXT NOT NULL,
                    domains TEXT NOT NULL,
                    preferences TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    role TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS capabilities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    endpoint TEXT,
                    permissions TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_invoked_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_capabilities_category
                    ON capabilities(category);
                CREATE INDEX IF NOT EXISTS idx_capabilities_status
                    ON capabilities(status);

                CREATE TABLE IF NOT EXISTS capability_invocations (
                    id TEXT PRIMARY KEY,
                    capability_id TEXT NOT NULL,
                    capability_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    dry_run INTEGER NOT NULL,
                    input TEXT NOT NULL,
                    output TEXT NOT NULL,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(capability_id) REFERENCES capabilities(id)
                );

                CREATE INDEX IF NOT EXISTS idx_capability_invocations_created
                    ON capability_invocations(created_at);
                CREATE INDEX IF NOT EXISTS idx_capability_invocations_capability
                    ON capability_invocations(capability_id);

                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    trigger TEXT NOT NULL,
                    steps TEXT NOT NULL,
                    status TEXT NOT NULL,
                    conditions TEXT NOT NULL DEFAULT '[]',
                    schedule TEXT,
                    external_actions TEXT NOT NULL DEFAULT '[]',
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_run_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_workflows_status
                    ON workflows(status);
                CREATE INDEX IF NOT EXISTS idx_workflows_trigger
                    ON workflows(trigger);
                CREATE INDEX IF NOT EXISTS idx_workflows_updated
                    ON workflows(updated_at);

                CREATE TABLE IF NOT EXISTS workflow_runs (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    workflow_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    dry_run INTEGER NOT NULL,
                    input TEXT NOT NULL,
                    output TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(workflow_id) REFERENCES workflows(id)
                );

                CREATE INDEX IF NOT EXISTS idx_workflow_runs_created
                    ON workflow_runs(created_at);
                CREATE INDEX IF NOT EXISTS idx_workflow_runs_workflow
                    ON workflow_runs(workflow_id);

                CREATE TABLE IF NOT EXISTS world_facts (
                    id TEXT PRIMARY KEY,
                    subject TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    object TEXT NOT NULL,
                    confidence INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_world_facts_subject
                    ON world_facts(subject);
                CREATE INDEX IF NOT EXISTS idx_world_facts_created
                    ON world_facts(created_at);

                CREATE TABLE IF NOT EXISTS module_settings (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    enabled INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._ensure_workflow_columns(connection)
            self._trim_oversized_text(connection)
            self._seed_default_capabilities(connection)
            self._seed_default_profile(connection)
            self._seed_module_settings(connection)
            connection.execute("PRAGMA optimize")

    def _ensure_workflow_columns(self, connection: sqlite3.Connection) -> None:
        existing_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(workflows)").fetchall()
        }
        migrations = {
            "conditions": "ALTER TABLE workflows ADD COLUMN conditions TEXT NOT NULL DEFAULT '[]'",
            "schedule": "ALTER TABLE workflows ADD COLUMN schedule TEXT",
            "external_actions": "ALTER TABLE workflows ADD COLUMN external_actions TEXT NOT NULL DEFAULT '[]'",
        }
        for column, statement in migrations.items():
            if column not in existing_columns:
                connection.execute(statement)

    def _trim_oversized_text(self, connection: sqlite3.Connection) -> None:
        suffix = "\n\n[truncated by gateway storage maintenance]"
        for table in ("messages", "memory_entries", "document_chunks"):
            connection.execute(
                f"""
                UPDATE {table}
                SET content = substr(content, 1, ?) || ?
                WHERE length(content) > ?
                """,
                (MAX_STORED_TEXT_CHARS, suffix, MAX_STORED_TEXT_CHARS),
            )

    def _seed_default_capabilities(self, connection: sqlite3.Connection) -> None:
        defaults = [
            {
                "id": "cap-chat",
                "name": "chat.completions",
                "description": "Generate assistant responses with conversation history and relevant memory.",
                "category": "assistant",
                "endpoint": "/api/v1/chat/completions",
                "permissions": ["chat:write", "memory:read"],
                "status": "enabled",
                "metadata": {"core_feature": "chat"},
            },
            {
                "id": "cap-memory",
                "name": "memory.semantic_search",
                "description": "Store, search, and rank semantic or episodic memory entries.",
                "category": "memory",
                "endpoint": "/api/v1/memory",
                "permissions": ["memory:read", "memory:write"],
                "status": "enabled",
                "metadata": {"core_feature": "memory"},
            },
            {
                "id": "cap-planner",
                "name": "agent.planner",
                "description": "Break complex requests into goals, constraints, steps, and next actions.",
                "category": "agent",
                "endpoint": None,
                "permissions": ["agent:plan"],
                "status": "enabled",
                "metadata": {"core_feature": "orchestration", "mode": "local"},
            },
            {
                "id": "cap-registry",
                "name": "kernel.capability_registry",
                "description": "Discover, govern, and invoke registered cognitive OS capabilities.",
                "category": "kernel",
                "endpoint": "/api/v1/capabilities",
                "permissions": ["capability:read", "capability:write"],
                "status": "enabled",
                "metadata": {"core_feature": "governance"},
            },
            {
                "id": "cap-workflow",
                "name": "workflow.local_executor",
                "description": "Create, preview, run, and audit deterministic local workflows.",
                "category": "workflow",
                "endpoint": "/api/v1/workflows",
                "permissions": ["workflow:read", "workflow:write", "workflow:run"],
                "status": "enabled",
                "metadata": {"core_feature": "workflow"},
            },
            {
                "id": "cap-decision",
                "name": "decision.local_intelligence",
                "description": "Evaluate decisions and review outputs with deterministic local heuristics.",
                "category": "decision",
                "endpoint": "/api/v1/decisions/evaluate",
                "permissions": ["decision:evaluate", "reflection:review"],
                "status": "enabled",
                "metadata": {"core_feature": "decision"},
            },
            {
                "id": "cap-voice",
                "name": "voice.local_loop",
                "description": "Transcribe text-backed voice input, synthesize browser speech, detect wake words, and infer speaker hints.",
                "category": "voice",
                "endpoint": "/api/v1/voice",
                "permissions": ["voice:read", "voice:write"],
                "status": "enabled",
                "metadata": {"core_feature": "voice"},
            },
            {
                "id": "cap-skill-graph",
                "name": "skill_graph.local_executor",
                "description": "Create and execute ordered skill graphs over registered local capabilities.",
                "category": "orchestration",
                "endpoint": "/api/v1/skill-graphs",
                "permissions": ["skill_graph:run"],
                "status": "enabled",
                "metadata": {"core_feature": "skill_graph"},
            },
            {
                "id": "cap-world-model",
                "name": "world_model.local_facts",
                "description": "Persist world facts and generate a user digital twin summary from profile, memory, and facts.",
                "category": "memory",
                "endpoint": "/api/v1/world",
                "permissions": ["world:read", "world:write"],
                "status": "enabled",
                "metadata": {"core_feature": "world_model"},
            },
            {
                "id": "cap-connectors",
                "name": "connectors.enterprise_hub",
                "description": "Expose local connector adapters for Jira, Salesforce, Slack, Teams, Confluence, ServiceNow, and SharePoint.",
                "category": "connector",
                "endpoint": "/api/v1/connectors",
                "permissions": ["connector:read", "connector:sync"],
                "status": "enabled",
                "metadata": {"core_feature": "connectors"},
            },
            {
                "id": "cap-domain-intelligence",
                "name": "domain.multi_intelligence",
                "description": "Run deterministic local intelligence for vision, meetings, trading, and robotics readiness.",
                "category": "domain",
                "endpoint": "/api/v1/intelligence",
                "permissions": ["vision:analyze", "meeting:analyze", "trading:analyze", "robotics:assess"],
                "status": "enabled",
                "metadata": {"core_feature": "domain_intelligence"},
            },
            {
                "id": "cap-evolution",
                "name": "capability.evolution_engine",
                "description": "Propose, register, and verify new local capabilities from observed gaps.",
                "category": "kernel",
                "endpoint": "/api/v1/capabilities/evolve",
                "permissions": ["capability:write", "skill_graph:run"],
                "status": "enabled",
                "metadata": {"core_feature": "capability_evolution"},
            },
        ]
        for capability in defaults:
            connection.execute(
                """
                INSERT OR IGNORE INTO capabilities (
                    id, name, description, category, endpoint, permissions, status,
                    metadata, created_at, updated_at, last_invoked_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), NULL)
                """,
                (
                    capability["id"],
                    capability["name"],
                    capability["description"],
                    capability["category"],
                    capability["endpoint"],
                    json.dumps(capability["permissions"]),
                    capability["status"],
                    json.dumps(capability["metadata"]),
                ),
            )

    def _seed_default_profile(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            INSERT OR IGNORE INTO assistant_profiles (
                id, preferred_name, communication_style, response_detail,
                domains, preferences, created_at, updated_at
            )
            VALUES (
                'local', NULL, 'concise', 'balanced', '[]', '{}',
                datetime('now'), datetime('now')
            )
            """
        )

    def _seed_module_settings(self, connection: sqlite3.Connection) -> None:
        defaults = [
            ("chat", "Chat", "core", "Persistent chat, streaming responses, and LLM routing."),
            ("memory", "Memory", "core", "Semantic and episodic memory APIs."),
            ("knowledge", "Knowledge", "core", "Document ingestion and searchable chunks."),
            ("workflow", "Workflow", "operations", "Workflow definitions, runs, and verification reports."),
            ("decision", "Decision", "intelligence", "Decision scoring, policy gates, and reflection review."),
            ("voice", "Voice", "interface", "Voice transcription, synthesis metadata, personas, and sentiment."),
            ("skill_graph", "Skill Graph", "orchestration", "Ordered skill graph execution."),
            ("world_model", "World Model", "intelligence", "World facts and digital twin summaries."),
            ("connectors", "Connectors", "enterprise", "Enterprise connector search and sync adapters."),
            ("domain_intelligence", "Domain Intelligence", "intelligence", "Meeting, vision, trading, and robotics modules."),
            ("capability_evolution", "Capability Evolution", "kernel", "Capability proposal, registration, and verification planning."),
            ("governance", "Governance", "kernel", "Capability registry, invocation, and audit controls."),
            ("personalization", "Personalization", "core", "Jarvis profile and preference context."),
        ]
        for module_id, name, category, description in defaults:
            connection.execute(
                """
                INSERT OR IGNORE INTO module_settings (
                    id, name, enabled, category, description, updated_at
                )
                VALUES (?, ?, 1, ?, ?, datetime('now'))
                """,
                (module_id, name, category, description),
            )

    def create_user(
        self,
        user_id: str,
        email: str,
        password_hash: str,
        full_name: str | None,
        role: str,
        created_at: str,
    ) -> UserPublic:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO users (id, email, password_hash, full_name, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, email.lower(), password_hash, full_name, role, created_at),
            )
        return UserPublic(
            id=user_id,
            email=email.lower(),
            full_name=full_name,
            role=role,
            created_at=created_at,
        )

    def get_user_by_email(self, email: str) -> sqlite3.Row | None:
        with self._connect() as connection:
            return connection.execute(
                "SELECT * FROM users WHERE email = ?",
                (email.lower(),),
            ).fetchone()

    def get_user_by_id(self, user_id: str) -> UserPublic | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return self._user_from_row(row) if row else None

    def list_users(self, limit: int = 50) -> list[UserPublic]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM users
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._user_from_row(row) for row in rows]

    def create_conversation(self, conversation: Conversation) -> Conversation:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversations (
                    id, title, system_prompt, model, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation.id,
                    conversation.title,
                    conversation.system_prompt,
                    conversation.model,
                    conversation.created_at,
                    conversation.updated_at,
                ),
            )
        return conversation

    def list_conversations(self) -> list[Conversation]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    conversations.*,
                    COUNT(messages.id) AS message_count
                FROM conversations
                LEFT JOIN messages ON messages.conversation_id = conversations.id
                GROUP BY conversations.id
                ORDER BY conversations.updated_at DESC
                """
            ).fetchall()

        return [self._conversation_from_row(row) for row in rows]

    def get_conversation(self, conversation_id: str) -> ConversationDetail | None:
        with self._connect() as connection:
            conversation_row = connection.execute(
                "SELECT * FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
            if conversation_row is None:
                return None

            message_rows = connection.execute(
                """
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                """,
                (conversation_id,),
            ).fetchall()

        conversation = self._conversation_from_row(
            conversation_row,
            message_count=len(message_rows),
        )
        return ConversationDetail(
            **conversation.model_dump(),
            messages=[self._message_from_row(row) for row in message_rows],
        )

    def add_messages(
        self,
        conversation_id: str,
        new_messages: list[Message],
        updated_at: str,
    ) -> None:
        with self._lock, self._connect() as connection:
            for message in new_messages:
                connection.execute(
                    """
                    INSERT INTO messages (
                        id, conversation_id, role, content, metadata, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        message.id,
                        message.conversation_id,
                        message.role,
                        message.content,
                        json.dumps(message.metadata or {}),
                        message.created_at,
                    ),
                )

            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (updated_at, conversation_id),
            )

    def create_memory(self, memory: MemoryEntry) -> MemoryEntry:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO memory_entries (
                    id, content, category, source, conversation_id, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory.id,
                    memory.content,
                    memory.category,
                    memory.source,
                    memory.conversation_id,
                    memory.created_at,
                    memory.updated_at,
                ),
            )
        return memory

    def list_memories(
        self,
        query: str | None = None,
        category: str | None = None,
        limit: int = 20,
    ) -> list[MemoryEntry]:
        clauses = []
        parameters: list[str | int] = []
        if category:
            clauses.append("category = ?")
            parameters.append(category)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        content_limit = MAX_SEARCH_TEXT_CHARS if query else MAX_STORED_TEXT_CHARS
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    id,
                    CASE
                        WHEN length(content) > ? THEN substr(content, 1, ?) || char(10) || '[truncated]'
                        ELSE content
                    END AS content,
                    category,
                    source,
                    conversation_id,
                    created_at,
                    updated_at
                FROM memory_entries
                {where_sql}
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                [content_limit, content_limit, *parameters, limit * 4 if query else limit],
            ).fetchall()

        memories = [self._memory_from_row(row) for row in rows]
        if not query:
            return memories[:limit]

        ranked = [
            memory.model_copy(update={"relevance": self._score_memory(query, memory.content)})
            for memory in memories
        ]
        return [
            memory
            for memory in sorted(ranked, key=lambda item: item.relevance or 0, reverse=True)
            if (memory.relevance or 0) > 0
        ][:limit]

    def delete_memory(self, memory_id: str) -> bool:
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM memory_entries WHERE id = ?",
                (memory_id,),
            )
        return cursor.rowcount > 0

    def create_document(
        self,
        document: DocumentEntry,
        chunks: list[DocumentChunk],
    ) -> DocumentEntry:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO documents (id, title, source, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    document.id,
                    document.title,
                    document.source,
                    json.dumps(document.tags),
                    document.created_at,
                    document.updated_at,
                ),
            )
            for chunk in chunks:
                connection.execute(
                    """
                    INSERT INTO document_chunks (
                        id, document_id, chunk_index, content, created_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        chunk.id,
                        chunk.document_id,
                        chunk.index,
                        chunk.content,
                        chunk.created_at,
                    ),
                )
        return document.model_copy(update={"chunk_count": len(chunks)})

    def list_documents(self, limit: int = 20) -> list[DocumentEntry]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT documents.*, COUNT(document_chunks.id) AS chunk_count
                FROM documents
                LEFT JOIN document_chunks ON document_chunks.document_id = documents.id
                GROUP BY documents.id
                ORDER BY documents.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._document_from_row(row) for row in rows]

    def get_document(self, document_id: str) -> dict | None:
        with self._connect() as connection:
            document_row = connection.execute(
                "SELECT * FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
            if document_row is None:
                return None
            chunk_rows = connection.execute(
                """
                SELECT * FROM document_chunks
                WHERE document_id = ?
                ORDER BY chunk_index ASC
                """,
                (document_id,),
            ).fetchall()
        document = self._document_from_row(document_row, chunk_count=len(chunk_rows))
        return {
            **document.model_dump(),
            "chunks": [self._document_chunk_from_row(row) for row in chunk_rows],
        }

    def search_document_chunks(
        self,
        query: str | None = None,
        document_id: str | None = None,
        limit: int = 10,
    ) -> list[DocumentChunk]:
        clauses = []
        parameters: list[str | int] = []
        if document_id:
            clauses.append("document_id = ?")
            parameters.append(document_id)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM document_chunks
                {where_sql}
                ORDER BY created_at DESC, chunk_index ASC
                LIMIT ?
                """,
                [*parameters, limit * 4 if query else limit],
            ).fetchall()

        chunks = [self._document_chunk_from_row(row) for row in rows]
        if not query:
            return chunks[:limit]

        ranked = [
            chunk.model_copy(update={"relevance": self._score_memory(query, chunk.content)})
            for chunk in chunks
        ]
        return [
            chunk
            for chunk in sorted(ranked, key=lambda item: item.relevance or 0, reverse=True)
            if (chunk.relevance or 0) > 0
        ][:limit]

    def create_feedback(self, feedback: FeedbackEntry) -> FeedbackEntry:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO feedback_entries (
                    id, rating, category, comment, conversation_id, message_id, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feedback.id,
                    feedback.rating,
                    feedback.category,
                    feedback.comment,
                    feedback.conversation_id,
                    feedback.message_id,
                    feedback.created_at,
                ),
            )
        return feedback

    def list_feedback(
        self,
        conversation_id: str | None = None,
        rating: str | None = None,
        limit: int = 20,
    ) -> list[FeedbackEntry]:
        clauses = []
        parameters: list[str | int] = []
        if conversation_id:
            clauses.append("conversation_id = ?")
            parameters.append(conversation_id)
        if rating:
            clauses.append("rating = ?")
            parameters.append(rating)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM feedback_entries
                {where_sql}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                [*parameters, limit],
            ).fetchall()
        return [self._feedback_from_row(row) for row in rows]

    def summarize_feedback(
        self,
        conversation_id: str | None = None,
    ) -> FeedbackSummary:
        clauses = []
        parameters: list[str] = []
        if conversation_id:
            clauses.append("conversation_id = ?")
            parameters.append(conversation_id)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rating_rows = connection.execute(
                f"""
                SELECT rating, COUNT(*) AS count
                FROM feedback_entries
                {where_sql}
                GROUP BY rating
                """,
                parameters,
            ).fetchall()
            category_rows = connection.execute(
                f"""
                SELECT category, COUNT(*) AS count
                FROM feedback_entries
                {where_sql}
                GROUP BY category
                """,
                parameters,
            ).fetchall()

        by_rating = {row["rating"]: row["count"] for row in rating_rows}
        by_category = {row["category"]: row["count"] for row in category_rows}
        return FeedbackSummary(
            total=sum(by_rating.values()),
            by_rating=by_rating,
            by_category=by_category,
        )

    def get_profile(self, profile_id: str = "local") -> AssistantProfile:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM assistant_profiles WHERE id = ?",
                (profile_id,),
            ).fetchone()
            if row is None:
                self._seed_default_profile(connection)
                row = connection.execute(
                    "SELECT * FROM assistant_profiles WHERE id = ?",
                    (profile_id,),
                ).fetchone()
        return self._profile_from_row(row)

    def update_profile(
        self,
        updates: dict,
        updated_at: str,
        profile_id: str = "local",
    ) -> AssistantProfile:
        current = self.get_profile(profile_id)
        next_profile = current.model_copy(
            update={
                **{key: value for key, value in updates.items() if value is not None},
                "updated_at": updated_at,
            }
        )
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE assistant_profiles
                SET preferred_name = ?, communication_style = ?, response_detail = ?,
                    domains = ?, preferences = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    next_profile.preferred_name,
                    next_profile.communication_style,
                    next_profile.response_detail,
                    json.dumps(next_profile.domains),
                    json.dumps(next_profile.preferences),
                    next_profile.updated_at,
                    next_profile.id,
                ),
            )
        return next_profile

    def create_capability(self, capability: CapabilityEntry) -> CapabilityEntry:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO capabilities (
                    id, name, description, category, endpoint, permissions, status,
                    metadata, created_at, updated_at, last_invoked_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    capability.id,
                    capability.name,
                    capability.description,
                    capability.category,
                    capability.endpoint,
                    json.dumps(capability.permissions),
                    capability.status,
                    json.dumps(capability.metadata),
                    capability.created_at,
                    capability.updated_at,
                    capability.last_invoked_at,
                ),
            )
        return capability

    def list_capabilities(
        self,
        query: str | None = None,
        category: str | None = None,
        status: str | None = None,
    ) -> list[CapabilityEntry]:
        clauses = []
        parameters: list[str] = []
        if category:
            clauses.append("category = ?")
            parameters.append(category)
        if status:
            clauses.append("status = ?")
            parameters.append(status)
        if query:
            clauses.append("(LOWER(name) LIKE ? OR LOWER(description) LIKE ?)")
            needle = f"%{query.lower()}%"
            parameters.extend([needle, needle])

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM capabilities
                {where_sql}
                ORDER BY category ASC, name ASC
                """,
                parameters,
            ).fetchall()
        return [self._capability_from_row(row) for row in rows]

    def get_capability(self, capability_id: str) -> CapabilityEntry | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM capabilities WHERE id = ? OR name = ?",
                (capability_id, capability_id),
            ).fetchone()
        return self._capability_from_row(row) if row else None

    def update_capability(
        self,
        capability_id: str,
        updates: dict,
        updated_at: str,
    ) -> CapabilityEntry | None:
        existing = self.get_capability(capability_id)
        if existing is None:
            return None

        next_capability = existing.model_copy(
            update={
                **{key: value for key, value in updates.items() if value is not None},
                "updated_at": updated_at,
            }
        )
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE capabilities
                SET description = ?, category = ?, endpoint = ?, permissions = ?,
                    status = ?, metadata = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    next_capability.description,
                    next_capability.category,
                    next_capability.endpoint,
                    json.dumps(next_capability.permissions),
                    next_capability.status,
                    json.dumps(next_capability.metadata),
                    next_capability.updated_at,
                    next_capability.id,
                ),
            )
        return next_capability

    def mark_capability_invoked(self, capability_id: str, invoked_at: str) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE capabilities
                SET last_invoked_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (invoked_at, invoked_at, capability_id),
            )

    def delete_capability(self, capability_id: str) -> bool:
        with self._lock, self._connect() as connection:
            protected = connection.execute(
                "SELECT 1 FROM capabilities WHERE id = ? AND id LIKE 'cap-%'",
                (capability_id,),
            ).fetchone()
            if protected:
                return False

            existing = connection.execute(
                "SELECT 1 FROM capabilities WHERE id = ?",
                (capability_id,),
            ).fetchone()
            if existing is None:
                return False

            connection.execute(
                "DELETE FROM capability_invocations WHERE capability_id = ?",
                (capability_id,),
            )
            cursor = connection.execute(
                "DELETE FROM capabilities WHERE id = ?",
                (capability_id,),
            )
        return cursor.rowcount > 0

    def create_capability_invocation(
        self,
        invocation: CapabilityInvocationRecord,
    ) -> CapabilityInvocationRecord:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO capability_invocations (
                    id, capability_id, capability_name, status, dry_run, input,
                    output, error, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invocation.id,
                    invocation.capability_id,
                    invocation.capability_name,
                    invocation.status,
                    1 if invocation.dry_run else 0,
                    json.dumps(invocation.input),
                    json.dumps(invocation.output),
                    invocation.error,
                    invocation.created_at,
                ),
            )
        return invocation

    def list_capability_invocations(
        self,
        capability_id: str | None = None,
        limit: int = 20,
    ) -> list[CapabilityInvocationRecord]:
        clauses = []
        parameters: list[str | int] = []
        if capability_id:
            clauses.append("capability_id = ?")
            parameters.append(capability_id)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM capability_invocations
                {where_sql}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                [*parameters, limit],
            ).fetchall()
        return [self._capability_invocation_from_row(row) for row in rows]

    def create_workflow(self, workflow: WorkflowEntry) -> WorkflowEntry:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO workflows (
                    id, name, trigger, steps, status, conditions, schedule, external_actions, metadata,
                    created_at, updated_at, last_run_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workflow.id,
                    workflow.name,
                    workflow.trigger,
                    json.dumps(workflow.steps),
                    workflow.status,
                    json.dumps(workflow.conditions),
                    workflow.schedule,
                    json.dumps(workflow.external_actions),
                    json.dumps(workflow.metadata),
                    workflow.created_at,
                    workflow.updated_at,
                    workflow.last_run_at,
                ),
            )
        return workflow

    def list_workflows(
        self,
        query: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[WorkflowEntry]:
        clauses = []
        parameters: list[str | int] = []
        if status:
            clauses.append("status = ?")
            parameters.append(status)
        if query:
            clauses.append("(LOWER(name) LIKE ? OR LOWER(trigger) LIKE ?)")
            needle = f"%{query.lower()}%"
            parameters.extend([needle, needle])

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM workflows
                {where_sql}
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                [*parameters, limit],
            ).fetchall()
        return [self._workflow_from_row(row) for row in rows]

    def get_workflow(self, workflow_id: str) -> WorkflowEntry | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM workflows WHERE id = ? OR name = ?",
                (workflow_id, workflow_id),
            ).fetchone()
        return self._workflow_from_row(row) if row else None

    def create_workflow_run(self, run: WorkflowRunRecord) -> WorkflowRunRecord:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO workflow_runs (
                    id, workflow_id, workflow_name, status, dry_run,
                    input, output, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.id,
                    run.workflow_id,
                    run.workflow_name,
                    run.status,
                    1 if run.dry_run else 0,
                    json.dumps(run.input),
                    json.dumps(run.output),
                    run.created_at,
                ),
            )
            connection.execute(
                """
                UPDATE workflows
                SET last_run_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (run.created_at, run.created_at, run.workflow_id),
            )
        return run

    def list_workflow_runs(
        self,
        workflow_id: str | None = None,
        limit: int = 20,
    ) -> list[WorkflowRunRecord]:
        clauses = []
        parameters: list[str | int] = []
        if workflow_id:
            clauses.append("workflow_id = ?")
            parameters.append(workflow_id)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM workflow_runs
                {where_sql}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                [*parameters, limit],
            ).fetchall()
        return [self._workflow_run_from_row(row) for row in rows]

    def list_module_settings(self) -> list[ModuleSetting]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM module_settings
                ORDER BY category ASC, name ASC
                """
            ).fetchall()
        return [self._module_setting_from_row(row) for row in rows]

    def get_module_setting(self, module_id: str) -> ModuleSetting | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM module_settings WHERE id = ?",
                (module_id,),
            ).fetchone()
        return self._module_setting_from_row(row) if row else None

    def update_module_setting(
        self,
        module_id: str,
        enabled: bool,
        updated_at: str,
    ) -> ModuleSetting | None:
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE module_settings
                SET enabled = ?, updated_at = ?
                WHERE id = ?
                """,
                (1 if enabled else 0, updated_at, module_id),
            )
            if cursor.rowcount == 0:
                return None
            row = connection.execute(
                "SELECT * FROM module_settings WHERE id = ?",
                (module_id,),
            ).fetchone()
        return self._module_setting_from_row(row) if row else None

    def create_world_fact(self, fact: WorldFact) -> WorldFact:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO world_facts (id, subject, relation, object, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (fact.id, fact.subject, fact.relation, fact.object, fact.confidence, fact.created_at),
            )
        return fact

    def list_world_facts(
        self,
        subject: str | None = None,
        limit: int = 20,
    ) -> list[WorldFact]:
        clauses = []
        parameters: list[str | int] = []
        if subject:
            clauses.append("LOWER(subject) LIKE ?")
            parameters.append(f"%{subject.lower()}%")
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM world_facts
                {where_sql}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                [*parameters, limit],
            ).fetchall()
        return [self._world_fact_from_row(row) for row in rows]

    @staticmethod
    def _conversation_from_row(
        row: sqlite3.Row,
        message_count: int | None = None,
    ) -> Conversation:
        return Conversation(
            id=row["id"],
            title=row["title"],
            system_prompt=row["system_prompt"],
            model=row["model"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            message_count=message_count if message_count is not None else row["message_count"],
        )

    @staticmethod
    def _message_from_row(row: sqlite3.Row) -> Message:
        metadata = json.loads(row["metadata"]) if row["metadata"] else None
        return Message(
            id=row["id"],
            conversation_id=row["conversation_id"],
            role=row["role"],
            content=row["content"],
            created_at=row["created_at"],
            metadata=metadata,
        )

    @staticmethod
    def _memory_from_row(row: sqlite3.Row) -> MemoryEntry:
        return MemoryEntry(
            id=row["id"],
            content=row["content"],
            category=row["category"],
            source=row["source"],
            conversation_id=row["conversation_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _document_from_row(
        row: sqlite3.Row,
        chunk_count: int | None = None,
    ) -> DocumentEntry:
        return DocumentEntry(
            id=row["id"],
            title=row["title"],
            source=row["source"],
            tags=json.loads(row["tags"] or "[]"),
            chunk_count=chunk_count if chunk_count is not None else row["chunk_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _document_chunk_from_row(row: sqlite3.Row) -> DocumentChunk:
        return DocumentChunk(
            id=row["id"],
            document_id=row["document_id"],
            index=row["chunk_index"],
            content=row["content"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _feedback_from_row(row: sqlite3.Row) -> FeedbackEntry:
        return FeedbackEntry(
            id=row["id"],
            rating=row["rating"],
            category=row["category"],
            comment=row["comment"],
            conversation_id=row["conversation_id"],
            message_id=row["message_id"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _profile_from_row(row: sqlite3.Row) -> AssistantProfile:
        return AssistantProfile(
            id=row["id"],
            preferred_name=row["preferred_name"],
            communication_style=row["communication_style"],
            response_detail=row["response_detail"],
            domains=json.loads(row["domains"] or "[]"),
            preferences=json.loads(row["preferences"] or "{}"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _user_from_row(row: sqlite3.Row) -> UserPublic:
        return UserPublic(
            id=row["id"],
            email=row["email"],
            full_name=row["full_name"],
            role=row["role"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _capability_from_row(row: sqlite3.Row) -> CapabilityEntry:
        return CapabilityEntry(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            category=row["category"],
            endpoint=row["endpoint"],
            permissions=json.loads(row["permissions"] or "[]"),
            status=row["status"],
            metadata=json.loads(row["metadata"] or "{}"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_invoked_at=row["last_invoked_at"],
        )

    @staticmethod
    def _capability_invocation_from_row(row: sqlite3.Row) -> CapabilityInvocationRecord:
        return CapabilityInvocationRecord(
            id=row["id"],
            capability_id=row["capability_id"],
            capability_name=row["capability_name"],
            status=row["status"],
            dry_run=bool(row["dry_run"]),
            input=json.loads(row["input"] or "{}"),
            output=json.loads(row["output"] or "{}"),
            error=row["error"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _workflow_from_row(row: sqlite3.Row) -> WorkflowEntry:
        return WorkflowEntry(
            id=row["id"],
            name=row["name"],
            trigger=row["trigger"],
            steps=json.loads(row["steps"] or "[]"),
            status=row["status"],
            conditions=json.loads(row["conditions"] or "[]"),
            schedule=row["schedule"],
            external_actions=json.loads(row["external_actions"] or "[]"),
            metadata=json.loads(row["metadata"] or "{}"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_run_at=row["last_run_at"],
        )

    @staticmethod
    def _workflow_run_from_row(row: sqlite3.Row) -> WorkflowRunRecord:
        return WorkflowRunRecord(
            id=row["id"],
            workflow_id=row["workflow_id"],
            workflow_name=row["workflow_name"],
            status=row["status"],
            dry_run=bool(row["dry_run"]),
            input=json.loads(row["input"] or "{}"),
            output=json.loads(row["output"] or "{}"),
            created_at=row["created_at"],
        )

    @staticmethod
    def _module_setting_from_row(row: sqlite3.Row) -> ModuleSetting:
        return ModuleSetting(
            id=row["id"],
            name=row["name"],
            enabled=bool(row["enabled"]),
            category=row["category"],
            description=row["description"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _world_fact_from_row(row: sqlite3.Row) -> WorldFact:
        return WorldFact(
            id=row["id"],
            subject=row["subject"],
            relation=row["relation"],
            object=row["object"],
            confidence=row["confidence"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _score_memory(query: str, content: str) -> float:
        query = query[:1000]
        content = content[:MAX_SEARCH_TEXT_CHARS]
        query_terms = {
            term.strip(".,!?;:()[]{}\"'").lower()
            for term in query.split()
            if len(term.strip(".,!?;:()[]{}\"'")) > 2
        }
        if not query_terms:
            return 0

        content_terms = {
            term.strip(".,!?;:()[]{}\"'").lower()
            for term in content.split()
            if len(term.strip(".,!?;:()[]{}\"'")) > 2
        }
        if not content_terms:
            return 0

        overlap = len(query_terms & content_terms)
        return overlap / len(query_terms)
