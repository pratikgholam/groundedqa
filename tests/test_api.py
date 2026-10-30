from fastapi.testclient import TestClient

from app.main import app
from app.db import get_db
from app.models import Chunk, Document
from app.services import embeddings as embeddings_module

EMBEDDING_DIM = 1536


def _fake_embed(texts):
    return [[1.0] + [0.0] * (EMBEDDING_DIM - 1) for _ in texts]


def test_ask_returns_raw_sources(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    doc = Document(filename="notes.txt")
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
    resp = client.post("/ask", json={"question": "hello"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body) == {"sources"}
    assert len(body["sources"]) == 1
    source = body["sources"][0]
    assert source["document"] == "notes.txt"
    assert source["text"] == "hello world"
    assert "score" in source


def test_ask_empty_question_returns_400(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    client = TestClient(app)
    resp = client.post("/ask", json={"question": "   "})
    assert resp.status_code == 400, resp.text


def test_ask_missing_question_returns_422(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    client = TestClient(app)
    resp = client.post("/ask", json={})
    assert resp.status_code == 422, resp.text


def test_ask_sql_injection_attempt_safe(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    doc = Document(filename="notes.txt")
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
        resp = client.post("/ask", json={"question": payload})
        assert resp.status_code in (200, 400), f"{payload!r} -> {resp.status_code}"


def test_ask_very_long_question(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    client = TestClient(app)
    resp = client.post("/ask", json={"question": "x" * 10000})
    # Either accepted and answered, or rejected cleanly — never a 500 leak.
    assert resp.status_code in (200, 400, 413, 422), resp.text


def test_ask_non_json_body_returns_422(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    client = TestClient(app)
    resp = client.post(
        "/ask", content=b"not json", headers={"content-type": "application/json"}
    )
    assert resp.status_code in (400, 422), resp.text
