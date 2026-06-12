import httpx
import pytest

from services.gateway.src.config import Settings
from services.gateway.src.llm import OllamaProvider


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.request = httpx.Request("POST", "http://ollama.test")

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "fake http error",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )


class FakeAsyncClient:
    calls: list[tuple[str, dict]]

    def __init__(self, *args, **kwargs):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url: str, json: dict):
        self.calls.append((url, json))
        if url.endswith("/api/chat"):
            return FakeResponse(404, {"error": "not found"})
        return FakeResponse(
            200,
            {
                "model": json["model"],
                "response": "Generated through legacy Ollama endpoint",
                "done": True,
            },
        )


@pytest.mark.asyncio
async def test_ollama_provider_uses_generate_response_fallback(monkeypatch):
    fake_client = FakeAsyncClient()
    monkeypatch.setattr(
        "services.gateway.src.llm.httpx.AsyncClient",
        lambda *args, **kwargs: fake_client,
    )
    provider = OllamaProvider(
        Settings(
            llm_provider="ollama",
            llm_max_retries=1,
            ollama_base_url="http://ollama.test",
            ollama_model="llama3",
        )
    )

    result = await provider.generate(
        prompt="Hello",
        history=[],
    )

    assert result.content == "Generated through legacy Ollama endpoint"
    assert result.metadata["provider"] == "ollama"
    assert [url.rsplit("/", 1)[-1] for url, _ in fake_client.calls] == ["chat", "generate"]
