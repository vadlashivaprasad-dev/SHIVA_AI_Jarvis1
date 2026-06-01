# Self-Learning Feedback Capture

ShivaAI Jarvis now includes the first self-learning data path: lightweight response feedback.
The system can collect positive, negative, and correction signals against assistant messages so
future evaluation, preference learning, and fine-tuning jobs have structured training data.

## Implemented Scope

- SQLite-backed `feedback_entries` table.
- `POST /api/v1/feedback` for response-quality signals.
- `GET /api/v1/feedback` for recent feedback review and filtering.
- `GET /api/v1/feedback/summary` for aggregate signal counts by rating and category.
- Frontend feedback controls on assistant messages.
- Frontend feedback summary panel.
- Smoke test coverage for feedback creation, listing, and aggregation.

## API Reference

### Capture Feedback

```http
POST /api/v1/feedback
Content-Type: application/json

{
  "rating": "positive",
  "category": "response_quality",
  "conversation_id": "conversation-id",
  "message_id": "assistant-message-id",
  "comment": "Helpful and concise"
}
```

Supported ratings are `positive`, `negative`, and `correction`.

### List Feedback

```http
GET /api/v1/feedback?conversation_id=conversation-id&rating=positive&limit=20
```

Filters are optional. Results are newest first.

### Summarize Feedback

```http
GET /api/v1/feedback/summary?conversation_id=conversation-id
```

Returns total feedback count plus counts grouped by rating and category. The conversation filter is
optional.

## Next Integration Points

- Aggregate feedback by model/provider to score response quality.
- Feed approved correction examples into the future self-learning pipeline.
- Tie feedback to authenticated users once public chat mode is disabled.
