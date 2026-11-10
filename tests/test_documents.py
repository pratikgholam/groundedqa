from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.db import get_db
from app.services import embeddings as embeddings_module


def _fake_embed(texts, task=None):
    return [[0.1] * 1536 for _ in texts]


def test_upload_and_list_documents(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)

    client = TestClient(app)

    files = {"file": ("notes.txt", b"hello world " * 50, "text/plain")}
    resp = client.post(
        "/documents",
        files=files,
        headers={"X-Tenant-ID": "tenant-1"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["filename"] == "notes.txt"
    assert data["chunk_count"] == 1
    assert set(data) == {"id", "filename", "created_at", "chunk_count"}

    resp = client.get("/documents", headers={"X-Tenant-ID": "tenant-1"})
    assert resp.status_code == 200, resp.text
    listed = resp.json()
    assert len(listed) == 1
    assert listed[0]["filename"] == "notes.txt"
    assert listed[0]["chunk_count"] == 1


def test_upload_unsupported_type(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    client = TestClient(app)

    files = {"file": ("image.png", b"\x89PNG", "image/png")}
    resp = client.post(
        "/documents", files=files, headers={"X-Tenant-ID": "tenant-1"}
    )
    assert resp.status_code == 415, resp.text


def test_upload_oversized_file_returns_413(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 0)
    client = TestClient(app)

    files = {"file": ("notes.txt", b"hello", "text/plain")}
    resp = client.post(
        "/documents", files=files, headers={"X-Tenant-ID": "tenant-1"}
    )
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
    resp = client.post(
        "/documents", files=files, headers={"X-Tenant-ID": "tenant-1"}
    )
    assert resp.status_code == 500, resp.text
    assert rollback_called == [True]


def test_upload_same_file_twice_no_duplicates(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    client = TestClient(app)

    content = b"hello world " * 50
    resp1 = client.post(
        "/documents",
        files={"file": ("notes.txt", content, "text/plain")},
        headers={"X-Tenant-ID": "tenant-1"},
    )
    assert resp1.status_code == 200, resp1.text
    doc1 = resp1.json()

    # Re-upload identical bytes: same document returned, no duplicate.
    resp2 = client.post(
        "/documents",
        files={"file": ("notes.txt", content, "text/plain")},
        headers={"X-Tenant-ID": "tenant-1"},
    )
    assert resp2.status_code == 200, resp2.text
    doc2 = resp2.json()
    assert doc2["id"] == doc1["id"]
    assert doc2["chunk_count"] == doc1["chunk_count"]

    # Listing still shows one document.
    listed = client.get("/documents", headers={"X-Tenant-ID": "tenant-1"}).json()
    assert len(listed) == 1
    assert listed[0]["id"] == doc1["id"]


def upload_with_content(
    client, filename: str, content: bytes, monkeypatch, tenant_id: str = "tenant-1"
):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    return client.post(
        "/documents",
        files={"file": (filename, content, "text/plain")},
        headers={"X-Tenant-ID": tenant_id},
    )


def test_upload_is_per_tenant(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    client = TestClient(app)

    content = b"hello world " * 50

    # Same content hash, different tenant → separate document (not idempotent
    # across tenants).
    resp1 = upload_with_content(client, "notes.txt", content, monkeypatch, "tenant-1")
    assert resp1.status_code == 200, resp1.text
    resp2 = upload_with_content(client, "notes.txt", content, monkeypatch, "tenant-2")
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["id"] != resp1.json()["id"]

    # Each tenant lists only their own documents.
    listed_1 = client.get(
        "/documents", headers={"X-Tenant-ID": "tenant-1"}
    ).json()
    assert len(listed_1) == 1
    assert listed_1[0]["id"] == resp1.json()["id"]

    listed_2 = client.get(
        "/documents", headers={"X-Tenant-ID": "tenant-2"}
    ).json()
    assert len(listed_2) == 1
    assert listed_2[0]["id"] == resp2.json()["id"]


def test_upload_same_filename_new_content_is_new_version(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    client = TestClient(app)

    resp1 = upload_with_content(client, "notes.txt", b"hello world " * 50, monkeypatch)
    assert resp1.status_code == 200, resp1.text
    doc1 = resp1.json()
    assert doc1["chunk_count"] == 1

    # Same filename, different content → new version, old chunks replaced.
    resp2 = upload_with_content(client, "notes.txt", b"goodbye moon " * 50, monkeypatch)
    assert resp2.status_code == 200, resp2.text
    doc2 = resp2.json()
    assert doc2["id"] == doc1["id"]  # same document record
    assert doc2["chunk_count"] == 1

    # Still only one document row.
    listed = client.get("/documents", headers={"X-Tenant-ID": "tenant-1"}).json()
    assert len(listed) == 1
    assert listed[0]["id"] == doc1["id"]
