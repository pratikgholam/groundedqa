from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.db import get_db
from app.models import Chunk, Document
from app.services import embeddings as embeddings_module
from app.services import generation as generation_module

EMBEDDING_DIM = 1536


def _fake_embed(texts, task=None):
    return [[1.0] + [0.0] * (EMBEDDING_DIM - 1) for _ in texts]


def _fake_llm_client(check_content="YES", answer_content="The answer is grounded."):
    client = MagicMock()
    check_mock = MagicMock()
    check_mock.choices[0].message.content = check_content
    answer_mock = MagicMock()
    answer_mock.choices[0].message.content = answer_content
    # First chat call: answerability check; second: answer generation.
    client.chat.completions.create.side_effect = [check_mock, answer_mock]
    return client


def test_ask_returns_grounded_answer(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    llm_client = _fake_llm_client()
    monkeypatch.setattr(generation_module, "_get_chat_client", lambda: llm_client)
    doc = Document(filename="notes.txt", content_hash="abc123", tenant_id="tenant-1")
    db_session.add(doc)
    db_session.flush()
    db_session.add(
        Chunk(
            document_id=doc.id,
            chunk_index=0,
            text="hello world",
            embedding=[1.0] + [0.0] * (EMBEDDING_DIM - 1),
        )
    )
    db_session.commit()

    client = TestClient(app)
    resp = client.post(
        "/ask", json={"question": "hello"}, headers={"X-Tenant-ID": "tenant-1"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body) == {"answer", "found", "citations"}
    assert body["found"] is True
    assert body["answer"] == "The answer is grounded."
    assert len(body["citations"]) == 1
    citation = body["citations"][0]
    assert citation["document_id"] == doc.id
    assert citation["page"] is None
    assert citation["passage"] == "hello world"
    assert llm_client.chat.completions.create.called


def test_ask_empty_question_returns_400(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    client = TestClient(app)
    resp = client.post(
        "/ask",
        json={"question": "   "},
        headers={"X-Tenant-ID": "tenant-1"},
    )
    assert resp.status_code == 400, resp.text


def test_ask_missing_question_returns_422(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    client = TestClient(app)
    resp = client.post(
        "/ask", json={}, headers={"X-Tenant-ID": "tenant-1"}
    )
    assert resp.status_code == 422, resp.text


def test_ask_sql_injection_attempt_safe(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    monkeypatch.setattr(
        generation_module,
        "_get_chat_client",
        lambda: _fake_llm_client("injection-safe answer"),
    )
    doc = Document(filename="notes.txt", content_hash="def456", tenant_id="tenant-1")
    db_session.add(doc)
    db_session.flush()
    db_session.add(
        Chunk(
            document_id=doc.id,
            chunk_index=0,
            text="hello world",
            embedding=[1.0] + [0.0] * (EMBEDDING_DIM - 1),
        )
    )
    db_session.commit()

    client = TestClient(app)
    # SQL-injection-style strings in the question must not break the query
    # or leak data; pgvector cosine_distance receives the embedding vector,
    # never raw SQL, so injection is not possible.
    injection_payloads = [
        "' OR 1=1 --",
        "'; DROP TABLE chunks; --",
        "UNION SELECT * FROM documents",
    ]
    for payload in injection_payloads:
        resp = client.post(
            "/ask",
            json={"question": payload},
            headers={"X-Tenant-ID": "tenant-1"},
        )
        assert resp.status_code in (200, 400), f"{payload!r} -> {resp.status_code}"


def test_ask_very_long_question(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    client = TestClient(app)
    resp = client.post(
        "/ask",
        json={"question": "x" * 10000},
        headers={"X-Tenant-ID": "tenant-1"},
    )
    # Either accepted and answered, or rejected cleanly — never a 500 leak.
    assert resp.status_code in (200, 400, 413, 422), resp.text


def test_ask_non_json_body_returns_422(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    client = TestClient(app)
    resp = client.post(
        "/ask",
        content=b"not json",
        headers={"content-type": "application/json", "X-Tenant-ID": "tenant-1"},
    )
    assert resp.status_code in (400, 422), resp.text
