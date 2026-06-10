- [x] Implement missing chat endpoints in `services/gateway/src/main.py`
  - [x] `POST /api/v1/chat/completions/stream` SSE stream with `event: token` and final `event: done`
  - [x] `GET /api/v1/chat/sessions` list sessions
  - [x] `POST /api/v1/chat/sessions` create session

- [x] Ensure streaming never abruptly terminates
  - [x] Use async generator + periodic flush
  - [x] Handle exceptions by emitting `event: error`
- [x] Connect streaming to existing local LLM (`LocalAssistantProvider`) in `services/gateway/src/llm.py`
- [x] Ensure UI store types are satisfied (message list updates)
- [x] Run quick smoke test: `curl -N` to stream endpoint + verify `[DONE]`/`event: done`
- [x] Retest frontend chat streaming

