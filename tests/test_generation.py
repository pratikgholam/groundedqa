# ask refusal / grounding behavior (LLM and embeddings mocked)
import logging
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.db import get_db
from app.models import Chunk, Document
from app.services import embeddings as embeddings_module
from app.services import generation as generation_module
from app.services.errors import UpstreamProviderError

EMBEDDING_DIM = 1536


def formatted_records(records):
    fmt = logging.Formatter()
    return [fmt.format(r) for r in records]


def _fake_embed(texts, task=None):
    return [[1.0] + [0.0] * (EMBEDDING_DIM - 1) for _ in texts]


def _fake_llm_client(check_content="YES", answer_content="The answer is grounded.", exc=None, embed_exc=None):
    client = MagicMock()
    if exc is not None:
        client.chat.completions.create.side_effect = exc
    else:
        check_mock = MagicMock()
        check_mock.choices[0].message.content = check_content
        answer_mock = MagicMock()
        answer_mock.choices[0].message.content = answer_content
        # First chat call: answerability check; second: answer generation.
        client.chat.completions.create.side_effect = [check_mock, answer_mock]
    if embed_exc is not None:
        client.embeddings.create.side_effect = embed_exc
    return client


def _mock_chat(monkeypatch, client):
    monkeypatch.setattr(generation_module, "_get_client", lambda: client)
    monkeypatch.setattr(generation_module, "_get_chat_client", lambda: client)


def test_ask_grounded_answer_with_citations(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    llm_client = _fake_llm_client()
    _mock_chat(monkeypatch, llm_client)

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
    assert set(body) == {"answer", "found", "citations"}
    assert body["found"] is True
    assert body["answer"] == "The answer is grounded."
    assert len(body["citations"]) == 1
    citation = body["citations"][0]
    assert citation["document_id"] == doc.id
    assert citation["page"] is None
    assert citation["passage"] == "hello world"
    assert llm_client.chat.completions.create.called


def test_ask_answerable_check_no_skips_generation(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    llm_client = _fake_llm_client(check_content="NO")
    _mock_chat(monkeypatch, llm_client)

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
    assert body["found"] is False
    assert body["answer"] == ""
    assert body["citations"] == []
    # Answerability check was called; generation was not (only 1 chat call).
    assert llm_client.chat.completions.create.call_count == 1


def test_ask_answerable_check_whitespace_is_yes(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    llm_client = _fake_llm_client(check_content="yes ")
    _mock_chat(monkeypatch, llm_client)

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
    assert body["found"] is True
    assert body["answer"] == "The answer is grounded."


def test_ask_answerable_check_prose_is_no(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    llm_client = _fake_llm_client(check_content="The passages do not say")
    _mock_chat(monkeypatch, llm_client)

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
    assert body["found"] is False
    assert body["answer"] == ""
    assert body["citations"] == []


def test_ask_refusal_when_no_chunks(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    llm_client = _fake_llm_client("unused")
    _mock_chat(monkeypatch, llm_client)

    client = TestClient(app)
    resp = client.post("/ask", json={"question": "hello"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["found"] is False
    assert body["answer"] == ""
    assert body["citations"] == []
    assert not llm_client.chat.completions.create.called


def test_ask_refusal_when_all_chunks_below_threshold(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    llm_client = _fake_llm_client("unused")
    _mock_chat(monkeypatch, llm_client)

    doc = Document(filename="notes.txt")
    db_session.add(doc)
    db_session.flush()
    # orthogonal to query embedding -> similarity 0 < SIMILARITY_CUTOFF (0.3)
    db_session.add(
        Chunk(
            document_id=doc.id,
            chunk_index=0,
            text="unrelated",
            embedding=[0.0, 1.0] + [0.0] * (EMBEDDING_DIM - 2),
        )
    )
    db_session.commit()

    client = TestClient(app)
    resp = client.post("/ask", json={"question": "hello"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["found"] is False
    assert body["answer"] == ""
    assert body["citations"] == []
    assert not llm_client.chat.completions.create.called


def test_ask_chat_failure_returns_502(db_session, monkeypatch, caplog):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    sdk_exc = Exception("SECRET-TEST-MARKER")
    monkeypatch.setattr(
        generation_module,
        "_get_chat_client",
        lambda: _fake_llm_client(exc=sdk_exc),
    )

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

    caplog.set_level(logging.ERROR, logger="app.services.generation")
    client = TestClient(app)
    resp = client.post("/ask", json={"question": "hello"})
    assert resp.status_code == 502, resp.text
    body = resp.json()
    assert body == {"detail": "Upstream model provider unavailable. Try again later."}
    assert "SECRET-TEST-MARKER" not in resp.text
    assert "hello world" not in resp.text

    error_records = [
        r
        for r in caplog.records
        if r.levelname == "ERROR" and r.name == "app.services.generation"
    ]
    assert len(error_records) == 1
    assert error_records[0].operation == "chat"
    assert error_records[0].exc_type == "Exception"
    assert "hello world" not in error_records[0].getMessage()
    assert "SECRET-TEST-MARKER" not in error_records[0].getMessage()
    assert "SECRET-TEST-MARKER" not in "".join(formatted_records(error_records))


def test_ask_embedding_failure_returns_502(db_session, monkeypatch, caplog):
    sdk_exc = Exception("SECRET-TEST-MARKER")
    monkeypatch.setattr(
        embeddings_module,
        "_get_client",
        lambda: _fake_llm_client(embed_exc=sdk_exc),
    )

    caplog.set_level(logging.ERROR, logger="app.services.embeddings")
    client = TestClient(app)
    resp = client.post("/ask", json={"question": "hello"})
    assert resp.status_code == 502, resp.text
    body = resp.json()
    assert body == {"detail": "Upstream model provider unavailable. Try again later."}
    assert "SECRET-TEST-MARKER" not in resp.text

    error_records = [
        r
        for r in caplog.records
        if r.levelname == "ERROR" and r.name == "app.services.embeddings"
    ]
    assert len(error_records) == 1
    assert error_records[0].operation == "embeddings"
    assert error_records[0].exc_type == "Exception"
    assert "SECRET-TEST-MARKER" not in error_records[0].getMessage()
    assert "SECRET-TEST-MARKER" not in "".join(formatted_records(error_records))


def test_documents_embedding_failure_returns_502_no_partial_write(
    db_session, monkeypatch, caplog
):
    def boom(*args, **kwargs):
        raise UpstreamProviderError("embeddings", Exception("SECRET-TEST-MARKER"))

    monkeypatch.setattr(embeddings_module, "embed_texts", boom)

    caplog.set_level(logging.ERROR, logger="app.main")
    client = TestClient(app)
    files = {"file": ("notes.txt", b"hello world", "text/plain")}
    resp = client.post("/documents", files=files)
    assert resp.status_code == 502, resp.text
    body = resp.json()
    assert body == {"detail": "Upstream model provider unavailable. Try again later."}
    assert "SECRET-TEST-MARKER" not in resp.text

    docs = db_session.execute(select(Document)).scalars().all()
    assert len(docs) == 0

    error_records = [
        r for r in caplog.records if r.levelname == "ERROR" and r.name == "app.main"
    ]
    assert len(error_records) == 1
    assert error_records[0].operation == "embeddings"
    assert error_records[0].exc_type == "Exception"
    assert "SECRET-TEST-MARKER" not in error_records[0].getMessage()
    assert "SECRET-TEST-MARKER" not in "".join(formatted_records(error_records))
