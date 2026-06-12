import asyncio
from dataclasses import dataclass

import httpx

from .config import Settings
from .errors import ErrorCode, ExternalServiceError
from .schemas import Message



@dataclass
class LLMResult:
    content: str
    metadata: dict


@dataclass
class LLMHealth:
    provider: str
    status: str
    model: str
    details: dict


class LocalAssistantProvider:
    name = "local"
    memory_preview_chars = 600

    async def health_check(self) -> LLMHealth:
        return LLMHealth(
            provider=self.name,
            status="healthy",
            model="local-assistant",
            details={"mode": "deterministic-fallback"},
        )

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


class OpenAICompatibleProvider:
    name = "openai"

    def __init__(self, settings: Settings):
        self.settings = settings

    async def health_check(self) -> LLMHealth:
        if not self.settings.openai_api_key:
            return LLMHealth(
                provider=self.name,
                status="degraded",
                model=self.settings.openai_model,
                details={"reason": "OPENAI_API_KEY is not configured; local fallback will be used"},
            )
        return LLMHealth(
            provider=self.name,
            status="healthy",
            model=self.settings.openai_model,
            details={"base_url": self.settings.openai_api_base},
        )

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

        # Sanitize history for OpenAI-compatible function calling.
        # OpenAI rejects orphaned `tool` messages that must follow an assistant message
        # with a matching `tool_calls` block.
        clean_messages: list[dict[str, str]] = []

        pending_tool_expected = False
        for message in history:
            role = message.role
            content = message.content

            if role == "assistant":
                # We don't have tool_calls in our internal Message schema,
                # so conservatively assume no pending tool calls.
                # This still fixes the invalid `tool`-message sequence error.
                pending_tool_expected = False
                if role in {"system", "user", "assistant"}:
                    clean_messages.append({"role": "assistant", "content": content})
                continue

            if role == "tool":
                # If there is no preceding assistant tool_calls, drop tool messages.
                # If later we add tool_calls support, we can safely re-enable this.
                if pending_tool_expected:
                    clean_messages.append({"role": "assistant", "content": content})
                continue

            if role in {"system", "user"}:
                clean_messages.append({"role": role, "content": content})

        messages = clean_messages
        if memories:
            messages.append(
                {
                    "role": "system",
                    "content": "Relevant user memory:\n" + "\n".join(f"- {item}" for item in memories[:5]),
                }
            )
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model or self.settings.openai_model,
            "messages": messages,
            "temperature": temperature if temperature is not None else 0.7,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
            response = await client.post(
                f"{self.settings.openai_api_base.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                json=payload,
            )
            response.raise_for_status()
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

    @property
    def base_url(self) -> str:
        return self.settings.ollama_base_url.rstrip("/")

    @property
    def configured_model(self) -> str:
        return self.settings.ollama_model

    async def health_check(self) -> LLMHealth:
        try:
            async with httpx.AsyncClient(timeout=min(self.settings.llm_timeout_seconds, 5.0)) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            return LLMHealth(
                provider=self.name,
                status="unhealthy",
                model=self.configured_model,
                details={"base_url": self.base_url, "error": str(exc)},
            )

        models = [
            item.get("name", "")
            for item in data.get("models", [])
            if isinstance(item, dict)
        ]
        configured = self.configured_model
        model_available = any(
            model == configured or model.split(":", 1)[0] == configured
            for model in models
        )
        return LLMHealth(
            provider=self.name,
            status="healthy" if model_available else "degraded",
            model=configured,
            details={
                "base_url": self.base_url,
                "model_available": model_available,
                "available_models": models,
            },
        )

    def _retry_count(self) -> int:
        return max(1, int(getattr(self.settings, "llm_max_retries", 1) or 1))

    async def _post_with_retries(self, client: httpx.AsyncClient, path: str, payload: dict) -> httpx.Response:
        last_error: Exception | None = None
        retryable_statuses = {408, 429, 500, 502, 503, 504}
        for attempt in range(self._retry_count()):
            try:
                response = await client.post(f"{self.base_url}{path}", json=payload)
                if response.status_code not in retryable_statuses:
                    return response
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt == self._retry_count() - 1:
                    break
                await asyncio.sleep(min(0.25 * (2**attempt), 2.0))

        raise ExternalServiceError(
            code=ErrorCode.LLM_TIMEOUT if isinstance(last_error, httpx.TimeoutException) else ErrorCode.LLM_PROVIDER_ERROR,
            message="Ollama LLM service is unavailable",
            user_message="The local LLM container is not ready yet. Please wait for Ollama to finish starting and pulling the model.",
            details={"provider": self.name, "base_url": self.base_url, "model": payload.get("model"), "error": str(last_error)},
        )

    async def generate(
        self,
        prompt: str,
        history: list[Message],
        memories: list[str] | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResult:
        ollama_model = model or self.configured_model

        messages = []
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

        # Prefer Ollama /api/chat, but fall back to /api/generate for older versions.
        payload: dict = {
            "model": ollama_model,
            "messages": messages,
            "stream": False,
        }

        if temperature is not None:
            payload["options"] = {"temperature": temperature}
        if max_tokens is not None:
            payload.setdefault("options", {})["num_predict"] = max_tokens

        async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
            response = await self._post_with_retries(client, "/api/chat", payload)
            if response.status_code in {404, 405}:
                # Fallback: /api/generate expects prompt, not messages.
                prompt = "\n".join(m.get("content", "") for m in messages)
                gen_payload: dict = {
                    "model": ollama_model,
                    "prompt": prompt,
                    "stream": False,
                }
                if temperature is not None:
                    gen_payload["options"] = {"temperature": temperature}
                if max_tokens is not None:
                    gen_payload.setdefault("options", {})["num_predict"] = max_tokens

                response = await self._post_with_retries(client, "/api/generate", gen_payload)
                response.raise_for_status()
                data = response.json()
            else:
                response.raise_for_status()
                data = response.json()


        content = (data.get("message") or {}).get("content")
        if not isinstance(content, str):
            content = data.get("response")
        if not isinstance(content, str):
            content = ""
        if not content.strip():
            raise ExternalServiceError(
                message="Ollama returned an empty response",
                user_message="The local LLM returned an empty answer. Please retry or verify the configured Ollama model.",
                details={"provider": self.name, "model": ollama_model},
            )


        return LLMResult(
            content=content,
            metadata={
                "provider": self.name,
                "model": data.get("model", ollama_model),
                "done": data.get("done"),
                "total_duration": data.get("total_duration"),
            },
        )


def create_llm_provider(settings: Settings):
    provider = settings.llm_provider.lower()
    if provider == "openai":
        return OpenAICompatibleProvider(settings)
    if provider == "ollama":
        return OllamaProvider(settings)
    return LocalAssistantProvider()


async def get_llm_health(settings: Settings) -> LLMHealth:
    provider = create_llm_provider(settings)
    return await provider.health_check()
