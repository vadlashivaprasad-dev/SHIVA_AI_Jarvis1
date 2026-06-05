# TODO - SQLAlchemy DB utilities hardening

- [x] Inspect and update `services/gateway/src/db.py`:
  - [ ] Replace lru_cache singletons with class-based engine manager
  - [ ] Add `dispose()` / `shutdown_db_engine()` for cleanup
  - [ ] Add early `database_url` validation + clear errors
  - [ ] Add SQLite `timeout` and keep thread-safety config
  - [ ] Add safe logging (mask credentials)
  - [ ] Keep backward-compatible public APIs (`get_db_engine`, `get_session_local`, `get_db_session`)
- [x] Wire shutdown hook in `services/gateway/src/main.py` to call `shutdown_db_engine()`
- [x] Verify test suite (`pytest`) passes
- [x] DB engine shutdown wired on FastAPI shutdown





