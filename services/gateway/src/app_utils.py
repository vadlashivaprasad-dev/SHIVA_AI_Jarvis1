import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from .config import get_settings
from .storage import ChatRepository


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def database_path() -> str:
    explicit = os.getenv("DATABASE_PATH")
    if explicit:
        return explicit
    settings = get_settings()
    if settings.database_url.startswith("sqlite:///"):
        return settings.database_url.removeprefix("sqlite:///")
    return str(Path("data") / "gateway.db")


def repository() -> ChatRepository:
    return ChatRepository(database_path(), enable_pool=False)


def jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    return value


def sse_event(event: str | None, data: str) -> bytes:
    payload = data.replace("\r\n", "\n").replace("\r", "\n")
    lines = payload.split("\n") or [""]
    prefix = f"event: {event}\n" if event else ""
    data_lines = "".join(f"data: {line}\n" for line in lines)
    return f"{prefix}{data_lines}\n".encode()


def chunk_text(text: str, size: int = 12) -> list[str]:
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


def split_document(content: str, chunk_size: int = 900) -> list[str]:
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


def module_enabled(repo: ChatRepository, module_id: str) -> bool:
    setting = repo.get_module_setting(module_id)
    return True if setting is None else setting.enabled


def require_module(repo: ChatRepository, module_id: str) -> None:
    if not module_enabled(repo, module_id):
        raise HTTPException(status_code=403, detail=f"{module_id} is disabled")
