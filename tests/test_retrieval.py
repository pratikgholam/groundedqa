import pytest

from app.models import Chunk, Document
from app.services import embeddings as embeddings_module
from app.services.retrieval import retrieve

EMBEDDING_DIM = 1536


def _fake_embed(texts):
    return [[1.0] + [0.0] * (EMBEDDING_DIM - 1) for _ in texts]


def test_retrieve_orders_by_similarity(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    doc = Document(filename="doc.txt")
    db_session.add(doc)
    db_session.flush()
    # identical to query -> similarity 1.0
    db_session.add(
        Chunk(
            document_id=doc.id,
            chunk_index=0,
            text="exact match",
            embedding=[1.0] + [0.0] * (EMBEDDING_DIM - 1),
        )
    )
    # orthogonal to query -> similarity 0.0
    db_session.add(
        Chunk(
            document_id=doc.id,
            chunk_index=1,
            text="orthogonal",
            embedding=[0.0, 1.0] + [0.0] * (EMBEDDING_DIM - 2),
        )
    )
    db_session.commit()

    results = retrieve("query", db_session, similarity_cutoff=0.0)
    assert len(results) == 2
    assert results[0]["text"] == "exact match"
    assert results[1]["text"] == "orthogonal"
    assert results[0]["document"] == "doc.txt"
    assert results[0]["score"] > results[1]["score"]


def test_retrieve_filters_by_similarity_cutoff(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    doc = Document(filename="doc.txt")
    db_session.add(doc)
    db_session.flush()
    db_session.add(
        Chunk(
            document_id=doc.id,
            chunk_index=0,
            text="exact",
            embedding=[1.0] + [0.0] * (EMBEDDING_DIM - 1),
        )
    )
    db_session.add(
        Chunk(
            document_id=doc.id,
            chunk_index=1,
            text="orthogonal",
            embedding=[0.0, 1.0] + [0.0] * (EMBEDDING_DIM - 2),
        )
    )
    db_session.commit()

    results = retrieve("query", db_session, similarity_cutoff=0.5)
    assert len(results) == 1
    assert results[0]["text"] == "exact"


def test_retrieve_limits_to_top_k(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    doc = Document(filename="doc.txt")
    db_session.add(doc)
    db_session.flush()
    for index in range(5):
        db_session.add(
            Chunk(
                document_id=doc.id,
                chunk_index=index,
                text=f"chunk {index}",
                embedding=[1.0] + [0.0] * (EMBEDDING_DIM - 1),
            )
        )
    db_session.commit()

    results = retrieve("query", db_session, top_k=2)
    assert len(results) == 2


def test_retrieve_empty_when_no_chunks(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)
    assert retrieve("query", db_session) == []


def test_retrieve_rolls_back_on_db_error(db_session, monkeypatch):
    monkeypatch.setattr(embeddings_module, "embed_texts", _fake_embed)

    def boom(*args, **kwargs):
        raise Exception("db query failed")

    rollback_called = []
    db_session.execute = boom
    db_session.rollback = lambda *a, **k: rollback_called.append(True)

    with pytest.raises(Exception, match="db query failed"):
        retrieve("query", db_session)

    assert rollback_called == [True]
