# Jarvis Profile And Preferences

ShivaAI Jarvis now has a persisted local profile layer. The profile captures communication style,
response detail, preferred name, and focus domains, then injects those preferences into chat context
before the LLM provider is called.

## Implemented Scope

- SQLite-backed `assistant_profiles` table with a default `local` profile.
- `GET /api/v1/profile` to read saved preferences.
- `PATCH /api/v1/profile` to update communication style, detail, domains, and custom preferences.
- Chat context injection through a system message before provider generation.
- Local provider metadata marks `profile_applied` when the saved profile is used.
- Frontend profile editor in the right workspace panel.
- Smoke test coverage for profile persistence and chat application.

## API Reference

### Read Profile

```http
GET /api/v1/profile
```

### Update Profile

```http
PATCH /api/v1/profile
Content-Type: application/json

{
  "preferred_name": "Keerthi",
  "communication_style": "technical",
  "response_detail": "brief",
  "domains": ["coding", "automation"],
  "preferences": {
    "updates": "concise"
  }
}
```

Supported communication styles are `concise`, `balanced`, `warm`, and `technical`.
Supported response detail levels are `brief`, `balanced`, and `detailed`.

## Next Integration Points

- Scope profiles per authenticated user once public chat mode is disabled.
- Learn preference updates automatically from repeated feedback.
- Expose domain-specific toggles for trading, coding, teaching, and prediction modules.
- Use profile preferences in agent planning and capability selection.
