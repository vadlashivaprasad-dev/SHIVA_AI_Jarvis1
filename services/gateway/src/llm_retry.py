from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from .config import Settings
from .schemas import Message


@dataclass
class LLMResult:
    content: str
    metadata: dict[str, Any]


class LocalAssistantProvider:
    name = "local"
    memory_preview_chars = 600

    async def generate(
        self,
        prompt: str,
        history: list[Message],
        memories: list[str] | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResult:
        recent_context = " ".join(message.content for message in history[-4:])
        profile_hint = next(
            (
                message.content
                for message in history
                if message.role == "system" and "Communication style:" in message.content
            ),
            "",
        )
        focus = prompt.strip()
        if len(focus) > 180:
            focus = f"{focus[:177]}..."

        memory_text = ""
        if memories:
            memory_text = "\n\nRelevant memory:\n" + "\n".join(
                f"- {memory[:self.memory_preview_chars]}" for memory in memories[:3]
            )

        content = (
            f"I can help with that. You said: \"{focus}\".\n\n"
            "Current local mode can organize the request, preserve the conversation, "
            "and hand off to a configured LLM provider when credentials are added. "
            "A practical next step is to break the request into goal, constraints, "
            "inputs, and the first action to take."
            f"{memory_text}"
        )
        if profile_hint:
            content += "\n\nI am also using your saved communication profile for tone and detail."

        return LLMResult(
            content=content,
            metadata={
                "provider": self.name,
                "model": model or "local-assistant",
                "history_messages": len(history),
                "context_chars": len(recent_context),
                "memories_used": len(memories or []),
                "profile_applied": bool(profile_hint),
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )


async def _post_with_retries(
    client: httpx.AsyncClient,
    url: str,
    *,
    headers: dict[str, str],
    json_payload: dict[str, Any],
    timeout_exc: type[Exception] | tuple[type[Exception], ...] = (httpx.RequestError, httpx.HTTPStatusError),
    retries: int = 3,
) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            resp = await client.post(url, headers=headers, json=json_payload)
            # Retry on transient 429/503.
            if resp.status_code in {429, 500, 502, 503, 504}:
                resp.raise_for_status()
            resp.raise_for_status()
            return resp
        except timeout_exc as exc:  # type: ignore[misc]
            last_exc = exc
            if attempt == retries - 1:
                raise

            # Exponential backoff with jitter
            base = 0.5 * (2**attempt)
            jitter = 0.1 * base
            await asyncio.sleep(base + jitter)

    # Should be unreachable
    assert last_exc is not None
    raise last_exc


class OpenAICompatibleProvider:
    name = "openai"

    def __init__(self, settings: Settings):
        self.settings = settings

    async def generate(
        self,
        prompt: str,
        history: list[Message],
        memories: list[str] | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResult:
        if not self.settings.openai_api_key:
            fallback = LocalAssistantProvider()
            result = await fallback.generate(prompt, history, memories, model, temperature, max_tokens)
            result.metadata["provider_warning"] = "OPENAI_API_KEY is not configured"
            return result

        messages = [
            {"role": message.role, "content": message.content}
            for message in history
            if message.role in {"system", "user", "assistant"}
        ]
        if memories:
            messages.append(
                {
                    "role": "system",
                    "content": "Relevant user memory:\n" + "\n".join(f"- {item}" for item in memories[:5]),
                }
            )
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": model or self.settings.openai_model,
            "messages": messages,
            "temperature": temperature if temperature is not None else 0.7,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
            response = await _post_with_retries(
                client,
                f"{self.settings.openai_api_base.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                json_payload=payload,
            )
            data = response.json()

        choice = data["choices"][0]
        return LLMResult(
            content=choice["message"]["content"],
            metadata={
                "provider": self.name,
                "model": data.get("model", payload["model"]),
                "usage": data.get("usage"),
            },
        )


class OllamaProvider:
    name = "ollama"

    def __init__(self, settings: Settings):
        self.settings = settings

    async def generate(
        self,
        prompt: str,
        history: list[Message],
        memories: list[str] | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResult:
        base_url = getattr(self.settings, "ollama_base_url", "http://localhost:11434")
        ollama_model = model or getattr(self.settings, "ollama_model", "llama3")

        messages: list[dict[str, str]] = []
        for m in history:
            if m.role not in {"system", "user", "assistant"}:
                continue
            messages.append({"role": m.role, "content": m.content})

        if memories:
            messages.append(
                {
                    "role": "system",
                    "content": "Relevant user memory:\n" + "\n".join(f"- {item}" for item in memories[:8]),
                }
            )

        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": ollama_model,
            "messages": messages,
            "stream": False,
        }
        if temperature is not None:
            payload["options"] = {"temperature": temperature}
        if max_tokens is not None:
            payload.setdefault("options", {})["num_predict"] = max_tokens

        async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
            try:
                response = await _post_with_retries(
                    client,
                    f"{base_url.rstrip('/')}/api/chat",
                    headers={},
                    json_payload=payload,
                )
                data = response.json()
            except httpx.HTTPStatusError:
                # Fallback: /api/generate expects prompt, not messages.
                prompt_text = "\n".join(m.get("content", "") for m in messages)
                gen_payload: dict[str, Any] = {
                    "model": ollama_model,
                    "prompt": prompt_text,
                    "stream": False,
                }
                if temperature is not None:
                    gen_payload["options"] = {"temperature": temperature}
                if max_tokens is not None:
                    gen_payload.setdefault("options", {})["num_predict"] = max_tokens

                response = await _post_with_retries(
                    client,
                    f"{base_url.rstrip('/')}/api/generate",
                    headers={},
                    json_payload=gen_payload,
                )
                data = response.json()

        content = (data.get("message") or {}).get("content")
        if not isinstance(content, str):
            content = str(content or "")

        return LLMResult(
            content=content,
            metadata={
                "provider": self.name,
                "model": data.get("model", ollama_model),
            },
        )


def create_llm_provider(settings: Settings):
    provider = settings.llm_provider.lower()
    if provider == "openai":
        return OpenAICompatibleProvider(settings)
    if provider == "ollama":
        return OllamaProvider(settings)
    return LocalAssistantProvider()

