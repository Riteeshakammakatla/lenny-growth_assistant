import pytest


async def test_create_session_returns_id(client):
    resp = await client.post("/api/sessions", json={"user_id": "u1"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["session_id"]
    assert body["llm_provider"] in ("ollama", "anthropic")


async def test_chat_requires_existing_session(client):
    resp = await client.post(
        "/api/chat", json={"session_id": "does-not-exist", "message": "hi", "intent": "chat"}
    )
    assert resp.status_code == 404


async def test_chat_round_trip_persists_messages(client):
    session_resp = await client.post("/api/sessions", json={"user_id": "u1"})
    session_id = session_resp.json()["session_id"]

    chat_resp = await client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "How do growth loops work?", "intent": "chat"},
    )
    assert chat_resp.status_code == 200
    body = chat_resp.json()
    assert "growth loops" in body["content"].lower()
    assert body["llm_provider"] == "fake"

    history_resp = await client.get(f"/api/sessions/{session_id}")
    assert history_resp.status_code == 200
    messages = history_resp.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


async def test_two_sessions_have_independent_history(client):
    s1 = (await client.post("/api/sessions", json={"user_id": "u1"})).json()["session_id"]
    s2 = (await client.post("/api/sessions", json={"user_id": "u2"})).json()["session_id"]

    await client.post("/api/chat", json={"session_id": s1, "message": "question A", "intent": "chat"})

    h1 = (await client.get(f"/api/sessions/{s1}")).json()["messages"]
    h2 = (await client.get(f"/api/sessions/{s2}")).json()["messages"]

    assert len(h1) == 2
    assert len(h2) == 0


async def test_artifact_intent_produces_sanitized_html_artifact(client):
    session_id = (await client.post("/api/sessions", json={"user_id": "u1"})).json()["session_id"]
    resp = await client.post(
        "/api/chat",
        json={
            "session_id": session_id,
            "message": "Make a one-pager on activation",
            "intent": "artifact",
            "artifact_format": "html",
        },
    )
    body = resp.json()
    assert body["artifact"]["type"] == "html"
    assert "<script" not in body["artifact"]["content"]


async def test_health_endpoint_reports_status(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "degraded")
    assert "knowledge_base_chunks" in body
