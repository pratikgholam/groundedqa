# pgvector similarity search
from sqlalchemy import select

from app.config import settings
from app.models import Chunk, Document
from app.services import embeddings


def retrieve(
    query_text: str,
    db,
    top_k: int | None = None,
    similarity_cutoff: float | None = None,
) -> list[dict]:
    """Return the top-k chunks most similar to `query_text`.

    Embeds the question, runs a pgvector cosine-distance search ordered by
    ascending distance, and returns matching chunks with their source document
    filename and cosine-similarity score. Chunks below `similarity_cutoff` are
    dropped. Cosine similarity = 1 - cosine distance.
    """
    if top_k is None:
        top_k = settings.TOP_K
    if similarity_cutoff is None:
        similarity_cutoff = settings.SIMILARITY_CUTOFF

    query_embedding = embeddings.embed_text(query_text)

    distance = Chunk.embedding.cosine_distance(query_embedding)
    statement = (
        select(Chunk, Document.filename, distance.label("distance"))
        .join(Document, Chunk.document_id == Document.id)
        .order_by(distance.asc())
        .limit(top_k)
    )
    try:
        rows = db.execute(statement).all()
    except Exception:
        db.rollback()
        raise

    results = []
    for chunk, filename, distance_value in rows:
        score = 1 - distance_value
        if score < similarity_cutoff:
            continue
        results.append(
            {
                "document": filename,
                "text": chunk.text,
                "score": score,
            }
        )
    return results
