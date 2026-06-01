# TODO - Production readiness for gateway

## Plan (approved)
1. Add production-grade logging + request correlation (request_id) using structlog.
2. Add centralized exception handler to return consistent JSON errors.
3. Add SSE hardening: correct headers + keep-alive comments.
4. Add basic request validation guards (e.g., chat content length, max_tokens bounds) without changing existing API behavior.
5. Add safe LLM error mapping (502/504) when OpenAI provider fails.
6. Ensure tests still pass and run `pytest`.

## Progress
- [x] Implement logging + request_id middleware.
- [ ] Add exception handlers.
- [x] Harden SSE.
- [x] Add structured request logging.

- [ ] Add validation guards.
- [x] Improve LLM error handling.

- [ ] Run `pytest`.

