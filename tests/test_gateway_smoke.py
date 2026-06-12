import os
from pathlib import Path
from uuid import uuid4

scratch_dir = Path("tests/.tmp")
scratch_dir.mkdir(exist_ok=True)
os.environ["DATABASE_PATH"] = str(scratch_dir / f"gateway-test-{uuid4()}.db")

from fastapi.testclient import TestClient

from services.gateway.src.main import app
from services.gateway.src.schemas import Conversation, Message
from services.gateway.src.storage import ChatRepository


client = TestClient(app)


def test_health_endpoint_is_available():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_readiness_and_llm_status_endpoints_are_available():
    readiness_response = client.get("/ready")

    assert readiness_response.status_code == 200
    readiness = readiness_response.json()
    assert readiness["status"] in {"ready", "degraded"}
    assert readiness["checks"]["database"]["status"] == "healthy"
    assert readiness["checks"]["llm"]["provider"] == "local"

    llm_response = client.get("/api/v1/llm/status")

    assert llm_response.status_code == 200
    llm = llm_response.json()
    assert llm["provider"] == "local"
    assert llm["status"] == "healthy"


def test_auth_signup_login_me_and_admin_user_listing():
    email = f"admin-{uuid4()}@example.com"
    signup_response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": "strong-password",
            "full_name": "Admin User",
            "role": "admin",
        },
    )

    assert signup_response.status_code == 201
    token = signup_response.json()["access_token"]

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "strong-password"},
    )

    assert login_response.status_code == 200
    assert login_response.json()["user"]["email"] == email

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["role"] == "admin"

    users_response = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert users_response.status_code == 200
    assert any(user["email"] == email for user in users_response.json())


def test_chat_development_flow():
    session_response = client.post(
        "/api/v1/chat/sessions",
        json={"title": "Smoke test"},
    )
    conversation_id = session_response.json()["id"]

    message_response = client.post(
        "/api/v1/chat/completions",
        json={"conversation_id": conversation_id, "content": "Hello"},
    )

    assert message_response.status_code == 200
    assert message_response.json()["role"] == "assistant"
    assert message_response.json()["metadata"]["provider"] == "local"


def test_chat_history_can_be_loaded():
    session_response = client.post(
        "/api/v1/chat/sessions",
        json={"title": "History test", "system_prompt": "Be concise"},
    )
    conversation_id = session_response.json()["id"]

    client.post(
        "/api/v1/chat/completions",
        json={"conversation_id": conversation_id, "content": "Remember this"},
    )

    history_response = client.get(f"/api/v1/chat/sessions/{conversation_id}")

    assert history_response.status_code == 200
    assert history_response.json()["message_count"] == 2
    assert [message["role"] for message in history_response.json()["messages"]] == [
        "user",
        "assistant",
    ]


def test_memory_crud_and_search():
    create_response = client.post(
        "/api/v1/memory",
        json={
            "content": "Keerthi prefers concise implementation updates",
            "category": "preference",
            "source": "manual",
        },
    )

    assert create_response.status_code == 201
    memory_id = create_response.json()["id"]

    search_response = client.get("/api/v1/memory", params={"query": "concise updates"})

    assert search_response.status_code == 200
    assert any(memory["id"] == memory_id for memory in search_response.json())

    delete_response = client.delete(f"/api/v1/memory/{memory_id}")

    assert delete_response.status_code == 204


def test_document_ingestion_search_and_memory_seed():
    content = (
        "ShivaAI Jarvis should ingest project documents into searchable chunks.\n\n"
        "The knowledge layer supports retrieval augmented generation by preserving source text."
    )
    create_response = client.post(
        "/api/v1/documents",
        json={
            "title": "Knowledge test",
            "content": content,
            "source": "test-suite",
            "tags": ["rag", "docs"],
            "add_to_memory": True,
        },
    )

    assert create_response.status_code == 201
    document = create_response.json()
    assert document["chunk_count"] >= 1
    assert document["tags"] == ["rag", "docs"]

    list_response = client.get("/api/v1/documents")

    assert list_response.status_code == 200
    assert any(item["id"] == document["id"] for item in list_response.json())

    detail_response = client.get(f"/api/v1/documents/{document['id']}")

    assert detail_response.status_code == 200
    assert detail_response.json()["chunks"][0]["document_id"] == document["id"]

    search_response = client.get(
        "/api/v1/documents/search",
        params={"query": "retrieval generation"},
    )

    assert search_response.status_code == 200
    assert any(chunk["document_id"] == document["id"] for chunk in search_response.json())

    memory_response = client.get(
        "/api/v1/memory",
        params={"query": "retrieval generation", "category": "knowledge"},
    )

    assert memory_response.status_code == 200
    assert any("Knowledge test" in memory["content"] for memory in memory_response.json())


def test_feedback_capture_and_listing():
    session_response = client.post(
        "/api/v1/chat/sessions",
        json={"title": "Feedback test"},
    )
    conversation_id = session_response.json()["id"]
    message_response = client.post(
        "/api/v1/chat/completions",
        json={"conversation_id": conversation_id, "content": "Give me a short answer"},
    )
    message_id = message_response.json()["id"]

    feedback_response = client.post(
        "/api/v1/feedback",
        json={
            "rating": "positive",
            "category": "response_quality",
            "conversation_id": conversation_id,
            "message_id": message_id,
            "comment": "Helpful and concise",
        },
    )

    assert feedback_response.status_code == 201
    assert feedback_response.json()["rating"] == "positive"

    list_response = client.get(
        "/api/v1/feedback",
        params={"conversation_id": conversation_id, "rating": "positive"},
    )

    assert list_response.status_code == 200
    assert any(item["message_id"] == message_id for item in list_response.json())

    summary_response = client.get(
        "/api/v1/feedback/summary",
        params={"conversation_id": conversation_id},
    )

    assert summary_response.status_code == 200
    assert summary_response.json()["total"] == 1
    assert summary_response.json()["by_rating"]["positive"] == 1
    assert summary_response.json()["by_category"]["response_quality"] == 1


def test_profile_preferences_are_saved_and_applied_to_chat():
    update_response = client.patch(
        "/api/v1/profile",
        json={
            "preferred_name": "Keerthi",
            "communication_style": "technical",
            "response_detail": "brief",
            "domains": ["coding", "automation"],
            "preferences": {"updates": "concise"},
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["communication_style"] == "technical"
    assert update_response.json()["domains"] == ["coding", "automation"]

    profile_response = client.get("/api/v1/profile")

    assert profile_response.status_code == 200
    assert profile_response.json()["preferred_name"] == "Keerthi"

    session_response = client.post(
        "/api/v1/chat/sessions",
        json={"title": "Profile test"},
    )
    conversation_id = session_response.json()["id"]
    message_response = client.post(
        "/api/v1/chat/completions",
        json={"conversation_id": conversation_id, "content": "Use my style"},
    )

    assert message_response.status_code == 200
    assert message_response.json()["metadata"]["profile_applied"] is True


def test_capability_registry_crud_and_dry_run():
    list_response = client.get("/api/v1/capabilities")

    assert list_response.status_code == 200
    assert any(item["name"] == "kernel.capability_registry" for item in list_response.json())

    capability_name = f"custom.test.{uuid4()}"
    create_response = client.post(
        "/api/v1/capabilities",
        json={
            "name": capability_name,
            "description": "Temporary capability for smoke testing",
            "category": "custom",
            "permissions": ["custom:invoke"],
            "metadata": {"core_feature": "governance"},
        },
    )

    assert create_response.status_code == 201
    capability_id = create_response.json()["id"]

    invoke_response = client.post(
        f"/api/v1/capabilities/{capability_id}/invoke",
        json={"dry_run": True, "input": {"sample": "value"}},
    )

    assert invoke_response.status_code == 200
    assert invoke_response.json()["invocation_id"]
    assert invoke_response.json()["status"] == "dry_run"
    assert invoke_response.json()["output"]["input_keys"] == ["sample"]

    patch_response = client.patch(
        f"/api/v1/capabilities/{capability_id}",
        json={"status": "disabled"},
    )

    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "disabled"

    blocked_response = client.post(
        f"/api/v1/capabilities/{capability_id}/invoke",
        json={"dry_run": True},
    )

    assert blocked_response.status_code == 409

    delete_response = client.delete(f"/api/v1/capabilities/{capability_id}")

    assert delete_response.status_code == 204


def test_builtin_capability_executors_and_invocation_history():
    memory_response = client.post(
        "/api/v1/memory",
        json={
            "content": "Planner execution should preserve audit history",
            "category": "semantic",
            "source": "test",
        },
    )

    assert memory_response.status_code == 201

    planner_response = client.post(
        "/api/v1/capabilities/agent.planner/invoke",
        json={
            "dry_run": False,
            "input": {
                "objective": "Implement pending Jarvis features",
                "constraints": ["keep changes scoped"],
            },
        },
    )

    assert planner_response.status_code == 200
    assert planner_response.json()["status"] == "completed"
    assert planner_response.json()["output"]["steps"]

    memory_search_response = client.post(
        "/api/v1/capabilities/memory.semantic_search/invoke",
        json={"dry_run": False, "input": {"query": "audit history", "limit": 3}},
    )

    assert memory_search_response.status_code == 200
    assert memory_search_response.json()["status"] == "completed"
    assert memory_search_response.json()["output"]["count"] >= 1

    registry_response = client.post(
        "/api/v1/capabilities/kernel.capability_registry/invoke",
        json={"dry_run": False, "input": {"query": "planner"}},
    )

    assert registry_response.status_code == 200
    assert registry_response.json()["output"]["count"] >= 1

    history_response = client.get("/api/v1/capabilities/invocations", params={"limit": 5})

    assert history_response.status_code == 200
    invocation_names = {item["capability_name"] for item in history_response.json()}
    assert "agent.planner" in invocation_names
    assert "memory.semantic_search" in invocation_names


def test_core_feature_status_endpoint():
    response = client.get("/api/v1/features")

    assert response.status_code == 200
    feature_ids = {feature["id"] for feature in response.json()}
    assert {"chat", "memory", "orchestration", "governance", "workflow", "decision"} <= feature_ids


def test_enterprise_overview_summarizes_operational_posture():
    response = client.get("/api/v1/enterprise/overview")

    assert response.status_code == 200
    overview = response.json()
    assert overview["posture"] in {"ready", "watch", "attention"}
    assert 0 <= overview["readiness_score"] <= 100
    assert overview["llm"]["provider"] == "local"
    assert overview["metrics"]["capabilities"] >= 1
    assert overview["governance"]["total_modules"] >= overview["governance"]["enabled_modules"]
    assert overview["risks"]
    assert overview["next_actions"]


def test_module_settings_can_disable_and_enable_domain_features():
    settings_response = client.get("/api/v1/settings/modules")

    assert settings_response.status_code == 200
    assert any(setting["id"] == "domain_intelligence" for setting in settings_response.json())

    disable_response = client.patch(
        "/api/v1/settings/modules/domain_intelligence",
        json={"enabled": False},
    )

    assert disable_response.status_code == 200
    assert disable_response.json()["enabled"] is False

    features_response = client.get("/api/v1/features")
    disabled_feature = next(
        feature for feature in features_response.json()
        if feature["id"] == "domain_intelligence"
    )
    assert disabled_feature["status"] == "disabled"

    blocked_response = client.post(
        "/api/v1/vision/analyze",
        json={"description": "dashboard screen"},
    )

    assert blocked_response.status_code == 403

    enable_response = client.patch(
        "/api/v1/settings/modules/domain_intelligence",
        json={"enabled": True},
    )

    assert enable_response.status_code == 200
    assert enable_response.json()["enabled"] is True

    allowed_response = client.post(
        "/api/v1/vision/analyze",
        json={"description": "dashboard screen"},
    )

    assert allowed_response.status_code == 200


def test_workflow_engine_foundation_create_run_and_history():
    workflow_name = f"Release checklist {uuid4()}"
    create_response = client.post(
        "/api/v1/workflows",
        json={
            "name": workflow_name,
            "trigger": "manual",
            "steps": ["Collect scope", "Run tests", "Prepare release notes"],
            "conditions": ["tests pass"],
            "schedule": "manual",
            "external_actions": ["notify release channel"],
            "metadata": {"owner": "test-suite"},
        },
    )

    assert create_response.status_code == 201
    workflow = create_response.json()
    assert workflow["status"] == "enabled"
    assert workflow["steps"] == ["Collect scope", "Run tests", "Prepare release notes"]

    list_response = client.get("/api/v1/workflows", params={"query": "release checklist"})

    assert list_response.status_code == 200
    assert any(item["id"] == workflow["id"] for item in list_response.json())

    run_response = client.post(
        f"/api/v1/workflows/{workflow['id']}/run",
        json={"dry_run": False, "input": {"version": "0.1.0"}},
    )

    assert run_response.status_code == 200
    run = run_response.json()
    assert run["status"] == "completed"
    assert run["output"]["step_count"] == 3
    assert run["output"]["steps"][0]["status"] == "completed"
    assert run["output"]["verification"]["verdict"] == "pass"
    assert run["output"]["external_actions"][0]["status"] == "simulated"

    history_response = client.get(
        "/api/v1/workflows/runs",
        params={"workflow_id": workflow["id"]},
    )

    assert history_response.status_code == 200
    assert history_response.json()[0]["id"] == run["id"]

    verification_response = client.get(
        "/api/v1/workflows/verification",
        params={"workflow_id": workflow["id"]},
    )

    assert verification_response.status_code == 200
    assert verification_response.json()[0]["verdict"] == "pass"


def test_decision_intelligence_and_reflection_foundations():
    decision_response = client.post(
        "/api/v1/decisions/evaluate",
        json={
            "decision": "Ship workflow MVP",
            "options": ["Ship local deterministic engine", "Wait for full LangGraph"],
            "risks": ["Limited automation depth"],
            "expected_impact": "High product clarity",
            "estimated_effort": "small",
        },
    )

    assert decision_response.status_code == 200
    decision = decision_response.json()
    assert decision["recommendation"] == "Ship local deterministic engine"
    assert 0 <= decision["risk_score"] <= 100
    assert decision["impact_score"] >= 70
    assert decision["rationale"]

    reflection_response = client.post(
        "/api/v1/reflection/review",
        json={
            "content": "Implement workflow support for local planning.",
            "criteria": ["clarity", "verification"],
        },
    )

    assert reflection_response.status_code == 200
    reflection = reflection_response.json()
    assert reflection["quality_score"] < 92
    assert reflection["improvements"]
    assert "Reflection improvements" in reflection["revised_content"]


def test_architecture_feature_endpoints_are_available():
    voice_response = client.post(
        "/api/v1/voice/transcribe",
        json={"audio_text": "Jarvis this is Keerthi checking the voice loop", "speaker_hint": "Keerthi"},
    )

    assert voice_response.status_code == 200
    assert voice_response.json()["speaker"] == "Keerthi"
    assert voice_response.json()["wake_word_detected"] is True

    synthesis_response = client.post(
        "/api/v1/voice/synthesize",
        json={"text": "Voice synthesis ready"},
    )

    assert synthesis_response.status_code == 200
    assert synthesis_response.json()["format"] == "browser-speech"

    decision_response = client.post(
        "/api/v1/decisions/evaluate",
        json={
            "decision": "Execute guarded action",
            "risks": ["security impact", "production change", "customer impact"],
            "policy_gates": ["human_approval", "security_review"],
        },
    )

    assert decision_response.status_code == 200
    assert decision_response.json()["policy_verdict"] == "requires_review"
    assert decision_response.json()["explainability"]["blocked_gates"]

    graph_response = client.post(
        "/api/v1/skill-graphs/run",
        params={"dry_run": False},
        json={
            "name": "Research to action",
            "objective": "Plan and verify a feature",
            "nodes": ["agent.planner", "reflection.review"],
            "edges": [{"from": "agent.planner", "to": "reflection.review"}],
        },
    )

    assert graph_response.status_code == 200
    assert graph_response.json()["status"] == "completed"
    assert graph_response.json()["ordered_nodes"] == ["agent.planner", "reflection.review"]

    fact_response = client.post(
        "/api/v1/world/facts",
        json={
            "subject": "Keerthi",
            "relation": "prefers",
            "object": "implementation-first updates",
            "confidence": 90,
        },
    )

    assert fact_response.status_code == 201
    twin_response = client.get("/api/v1/world/digital-twin")

    assert twin_response.status_code == 200
    assert any(fact["subject"] == "Keerthi" for fact in twin_response.json()["known_facts"])

    connectors_response = client.get("/api/v1/connectors")

    assert connectors_response.status_code == 200
    providers = {connector["provider"] for connector in connectors_response.json()}
    assert {"Jira", "Salesforce", "Slack", "Teams", "Confluence", "ServiceNow", "SharePoint"} <= providers

    sync_response = client.post(
        "/api/v1/connectors/jira/sync",
        json={"query": "release blockers", "dry_run": False},
    )

    assert sync_response.status_code == 200
    assert sync_response.json()["status"] == "completed"

    search_response = client.get(
        "/api/v1/connectors/jira/search",
        params={"query": "release blockers"},
    )

    assert search_response.status_code == 200
    assert search_response.json()["results"][0]["source"] == "Jira"

    evolution_response = client.post(
        "/api/v1/capabilities/evolve",
        json={
            "objective": "Summarize connector risks",
            "observed_gap": "Need a repeatable connector risk review capability",
            "category": "connector",
        },
    )

    assert evolution_response.status_code == 201
    assert evolution_response.json()["proposed_capability"]["category"] == "connector"
    assert evolution_response.json()["verification_plan"]

    meeting_response = client.post(
        "/api/v1/meetings/analyze",
        json={
            "title": "Planning",
            "transcript": "We need an action to assign UI verification. Follow up with tests.",
        },
    )

    assert meeting_response.status_code == 200
    assert meeting_response.json()["action_items"]
    assert meeting_response.json()["jira_stories"]

    vision_response = client.post(
        "/api/v1/vision/analyze",
        json={"description": "A dashboard screen shows an error chart"},
    )

    assert vision_response.status_code == 200
    assert "dashboard" in vision_response.json()["objects"]
    assert "error" in vision_response.json()["risk_flags"]

    trading_response = client.post(
        "/api/v1/trading/analyze",
        json={"symbol": "AAPL", "strategy": "momentum", "risk_tolerance": "low"},
    )

    assert trading_response.status_code == 200
    assert trading_response.json()["approval_required"] is True
    assert trading_response.json()["symbol"] == "AAPL"

    robotics_response = client.post(
        "/api/v1/robotics/readiness",
        json={"task": "Move item across workspace", "environment": "lab"},
    )

    assert robotics_response.status_code == 200
    assert robotics_response.json()["blockers"]


def test_streaming_chat_endpoint_returns_sse_events():
    session_response = client.post(
        "/api/v1/chat/sessions",
        json={"title": "Streaming test"},
    )
    conversation_id = session_response.json()["id"]

    with client.stream(
        "POST",
        "/api/v1/chat/completions/stream",
        json={"conversation_id": conversation_id, "content": "Stream this"},
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert "event: token" in body
    assert "event: done" in body


def test_sqlite_repository_persists_conversation():
    database_path = scratch_dir / f"gateway-{uuid4()}.db"
    first_repository = ChatRepository(str(database_path))
    conversation = Conversation(
        id="conversation-1",
        title="Persistent chat",
        created_at="2026-05-31T00:00:00+00:00",
        updated_at="2026-05-31T00:00:00+00:00",
    )
    first_repository.create_conversation(conversation)
    first_repository.add_messages(
        conversation.id,
        [
            Message(
                id="message-1",
                conversation_id=conversation.id,
                role="user",
                content="Persist me",
                created_at="2026-05-31T00:00:01+00:00",
            )
        ],
        updated_at="2026-05-31T00:00:01+00:00",
    )

    second_repository = ChatRepository(str(database_path))
    restored = second_repository.get_conversation(conversation.id)

    assert restored is not None
    assert restored.message_count == 1
    assert restored.messages[0].content == "Persist me"
