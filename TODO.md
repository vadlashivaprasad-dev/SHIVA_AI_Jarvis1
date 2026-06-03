# TODO - Ollama chat reply + correctness fixes

- [x] Add OllamaProvider to `services/gateway/src/llm.py` (HTTP call to Ollama `/api/chat`).
- [x] Extend `services/gateway/src/config.py` with `ollama_base_url` + `ollama_model` settings.
- [x] Update `create_llm_provider()` routing to support `LLM_PROVIDER=ollama`.
- [x] Verify/adjust SSE formatting in `services/gateway/src/main.py` so frontend parses `token` and `done` correctly.
- [ ] If required, patch `apps/web/src/App.tsx` SSE parsing edge cases.
- [ ] Add quick local run notes (env vars + commands) to README or deliverable summary.


