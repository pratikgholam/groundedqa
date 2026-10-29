from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.db import get_db
from app.services import embeddings as embeddings_module


def _fake_embed(texts):
    return [[0.1] * 1536 for _ in texts]


def test_upload_and_list_documents(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)

    client = TestClient(app)

    files = {"file": ("notes.txt", b"hello world " * 50, "text/plain")}
    resp = client.post("/documents", files=files)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["filename"] == "notes.txt"
    assert data["chunk_count"] == 1
    assert set(data) == {"id", "filename", "created_at", "chunk_count"}

    resp = client.get("/documents")
    assert resp.status_code == 200, resp.text
    listed = resp.json()
    assert len(listed) == 1
    assert listed[0]["filename"] == "notes.txt"
    assert listed[0]["chunk_count"] == 1


def test_upload_unsupported_type(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    client = TestClient(app)

    files = {"file": ("image.png", b"\x89PNG", "image/png")}
    resp = client.post("/documents", files=files)
    assert resp.status_code == 415, resp.text


def test_upload_oversized_file_returns_413(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 0)
    client = TestClient(app)

    files = {"file": ("notes.txt", b"hello", "text/plain")}
    resp = client.post("/documents", files=files)
    assert resp.status_code == 413, resp.text


def test_upload_commit_failure_rolls_back(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    rollback_called = []

    def boom(*args, **kwargs):
        raise Exception("db write failed")

    monkeypatch.setattr(db_session, "commit", boom)
    monkeypatch.setattr(
        db_session, "rollback", lambda *a, **k: rollback_called.append(True)
    )

    client = TestClient(app, raise_server_exceptions=False)
    files = {"file": ("notes.txt", b"hello world", "text/plain")}
    resp = client.post("/documents", files=files)
    assert resp.status_code == 500, resp.text
    assert rollback_called == [True]
