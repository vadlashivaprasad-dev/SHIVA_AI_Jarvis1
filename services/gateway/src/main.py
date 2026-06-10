import json
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .config import get_settings
from .errors import generic_exception_handler, shivaai_exception_handler, ShivaAIException
from .log_config import configure_logging, RequestIDMiddleware
from .middleware import (
    CSRFTokenMiddleware,
    InputValidationMiddleware,
    PerformanceMetricsMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    TrustedHostMiddleware,
)
from .llm import LocalAssistantProvider


# -------------------------------
# Chat streaming implementation
# -------------------------------

class _ChatSessionStore:
    """Minimal in-memory session/message store.

    This is only to make the frontend chat UI functional.
    """

    def __init__(self) -> None:
        self.sessions: dict[str, dict[str, Any]] = {}

    def list_sessions(self) -> list[dict[str, Any]]:
        # Match UI expectation: {id,title,updated_at,message_count}
        items = list(self.sessions.values())
        items.sort(key=lambda s: s["updated_at"], reverse=True)
        return [
            {
                "id": s["id"],
                "title": s["title"],
                "updated_at": s["updated_at"],
                "message_count": s["message_count"],
            }
            for s in items
        ]

    def create_session(self, title: str) -> dict[str, Any]:
        import datetime
        import uuid

        sid = str(uuid.uuid4())
        now = datetime.datetime.utcnow().isoformat()
        session = {
            "id": sid,
            "title": title,
            "updated_at": now,
            "message_count": 0,
            "messages": [],
        }
        self.sessions[sid] = session
        return session

    def append_user_message(self, sid: str, content: str) -> None:
        import datetime
        from uuid import uuid4

        if sid not in self.sessions:
            raise KeyError(sid)

        now = datetime.datetime.utcnow().isoformat()
        self.sessions[sid]["messages"].append(
            {
                "id": str(uuid4()),
                "role": "user",
                "content": content,
                "timestamp": now,
            }
        )
        self.sessions[sid]["message_count"] += 1
        self.sessions[sid]["updated_at"] = now

    def append_assistant_message(self, sid: str, content: str) -> None:
        import datetime
        from uuid import uuid4

        if sid not in self.sessions:
            raise KeyError(sid)

        now = datetime.datetime.utcnow().isoformat()
        self.sessions[sid]["messages"].append(
            {
                "id": str(uuid4()),
                "role": "assistant",
                "content": content,
                "timestamp": now,
            }
        )
        self.sessions[sid]["message_count"] += 1
        self.sessions[sid]["updated_at"] = now

    def get_session(self, sid: str) -> dict[str, Any] | None:
        return self.sessions.get(sid)


_session_store = _ChatSessionStore()


async def _sse_event(event: str | None, data: str) -> bytes:
    # SSE framing: optional `event:` line + `data:` line, terminated by a blank line.
    if event:
        return f"event: {event}\ndata: {data}\n\n".encode("utf-8")
    return f"data: {data}\n\n".encode("utf-8")



def create_app() -> FastAPI:

    settings = get_settings()

    configure_logging(
        log_level=settings.log_level,
        environment=settings.environment,
    )

    app = FastAPI(title="ShivaAI Jarvis - Backend")

    # Request ID must exist even for errors.
    # RequestIDMiddleware is an ASGI-compatible callable. Add it via add_middleware
    # so FastAPI/Starlette instantiates it correctly.
    app.add_middleware(RequestIDMiddleware)


    # Security headers + performance headers.
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(PerformanceMetricsMiddleware)
    app.add_middleware(InputValidationMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    # Rate limiting middleware (disabled automatically for pytest).
    app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

    # CSRF middleware (disabled in tests per implementation).
    app.add_middleware(CSRFTokenMiddleware)

    if settings.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"] ,
            allow_headers=["*"],
        )

    @app.exception_handler(ShivaAIException)
    async def _shivaai_exception_handler(request, exc):
        return await shivaai_exception_handler(request, exc)

    @app.exception_handler(Exception)
    async def _generic_exception_handler(request, exc):
        # Prevent double-wrapping FastAPI/Starlette HTTPException
        return await generic_exception_handler(request, exc)

    @app.get("/health")
    def health():
        return {"status": "healthy"}

    @app.get("/api/v1/chat/sessions")
    def list_chat_sessions():
        return _session_store.list_sessions()

    @app.post("/api/v1/chat/sessions")
    def create_chat_session(body: dict[str, Any]):
        title = str(body.get("title") or "Conversation")
        session = _session_store.create_session(title=title)
        return {
            "id": session["id"],
            "title": session["title"],
            "updated_at": session["updated_at"],
            "message_count": session["message_count"],
        }

    # -------------------------------
    # UI stubs (return safe defaults)
    # -------------------------------
    # The current repository only wires up the chat endpoints.
    # The frontend App.tsx calls many additional endpoints during initial render.
    # To prevent UI crashes while those routes are implemented, return safe defaults.

    @app.get("/api/v1/memory", include_in_schema=True)

    def list_memories():
        return []

    @app.get("/api/v1/documents")
    def list_documents():
        return []

    @app.get("/api/v1/features")
    def list_features():
        return []

    @app.get("/api/v1/capabilities")
    def list_capabilities():
        return []

    @app.get("/api/v1/capabilities/invocations")
    def list_capability_invocations():
        return []

    @app.get("/api/v1/workflows")
    def list_workflows():
        return []

    @app.get("/api/v1/workflows/runs")
    def list_workflow_runs():
        return []

    @app.get("/api/v1/connectors")
    def list_connectors():
        return []

    @app.get("/api/v1/world/digital-twin")
    def get_digital_twin():
        return {
            "preferred_name": None,
            "domains": [],
            "inferred_work_style": "",
            "known_facts": [],
        }

    @app.get("/api/v1/profile")
    def get_profile():
        return {
            "communication_style": "concise",
            "response_detail": "balanced",
            "domains": [],
            "preferences": {},
        }

    @app.get("/api/v1/feedback/summary")
    def get_feedback_summary():
        return {
            "total": 0,
            "by_rating": {},
            "by_category": {},
        }

    @app.get("/api/v1/settings/modules")
    def list_module_settings():
        return []

    @app.patch("/api/v1/settings/modules/{module_id}")
    def patch_module_setting(module_id: str, body: dict[str, Any] | None = None):
        enabled = bool((body or {}).get("enabled", True))
        return {
            "id": module_id,
            "name": module_id,
            "enabled": enabled,
            "category": "core",
            "description": "",
        }


    @app.post("/api/v1/chat/completions/stream")
    async def chat_completions_stream(request: Request):
        payload = await request.json()
        conversation_id = str(payload.get("conversation_id") or "")
        content = str(payload.get("content") or "")

        if not conversation_id:
            return StreamingResponse(
                iter([await _sse_event("error", json.dumps({"message": "conversation_id is required"}))]),
                media_type="text/event-stream",
                status_code=400,
            )

        if not content.strip():
            return StreamingResponse(
                iter([await _sse_event("error", json.dumps({"message": "content is required"}))]),
                media_type="text/event-stream",
                status_code=400,
            )

        llm = LocalAssistantProvider()

        async def gen() -> AsyncGenerator[bytes, None]:
            # Always send tokens as events to match frontend parser.
            # LocalAssistantProvider is non-streaming, so we simulate token streaming.
            import asyncio

            last_yield_ts: float | None = None
            buffered_full: list[str] = []
            try:
                _session_store.append_user_message(conversation_id, content)

                # Fetch conversation messages for history (best-effort)
                session = _session_store.get_session(conversation_id) or {}
                history = []
                for m in session.get("messages", []):
                    # Map to llm.schemas.Message shape loosely
                    history.append(type("_Msg", (), {"role": m["role"], "content": m["content"]})())

                # Generate full response
                result = await llm.generate(
                    prompt=content,
                    history=history[-10:],
                    memories=None,
                    model=payload.get("model"),
                    temperature=payload.get("temperature"),
                    max_tokens=payload.get("max_tokens"),
                )

                full = result.content or ""
                buffered_full.append(full)

                # Simulated tokenization by small chunks.
                # Must be valid UTF-8 and small enough for incremental UI.
                chunk_size = 8
                flush_every_tokens = 5
                token_count = 0
                assembled = []

                for i in range(0, len(full), chunk_size):
                    token = full[i : i + chunk_size]
                    assembled.append(token)
                    token_count += 1
                    yield await _sse_event("token", json.dumps({"text": token}))

                    # Periodic flush/yield to avoid abrupt termination under some proxies.
                    # Also yields control to the event loop.
                    if token_count % flush_every_tokens == 0:
                        await asyncio.sleep(0)

                assembled_text = "".join(assembled)

                # Persist assistant message once complete
                _session_store.append_assistant_message(conversation_id, assembled_text)

                # Final event
                yield await _sse_event("done", json.dumps({"content": assembled_text}))

                # Explicit final flush hint for some servers
                if last_yield_ts is not None:
                    await asyncio.sleep(0)

            except Exception as e:
                # Emit error and keep stream well-formed.
                yield await _sse_event(
                    "error",
                    json.dumps({"message": str(e), "code": "LLM_STREAM_ERROR"}),
                )

        return StreamingResponse(gen(), media_type="text/event-stream")

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

