# POST/GET /documents
import hashlib

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.auth import get_tenant_id, rate_limit, verify_api_key
from app.db import get_db
from app.models import Chunk, Document
from app.schemas import DocumentOut
from app.services import embeddings
from app.services.chunking import chunk_text
from app.services.extraction import extract_text
from app.config import settings

router = APIRouter(
    dependencies=[Depends(verify_api_key), Depends(rate_limit)]
)


@router.post("/documents", response_model=DocumentOut)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024

    # Reject oversized uploads before reading the body (content-length may be
    # absent, so the chunked read below enforces the cap as a backstop).
    content_length = request.headers.get("content-length")
    if content_length is not None and int(content_length) > max_bytes:
        raise HTTPException(413, "File too large")

    # Stream the body in 1 MiB chunks, aborting past the size cap so a huge
    # upload never gets fully held in memory.
    pieces: list[bytes] = []
    total = 0
    while True:
        piece = await file.read(1024 * 1024)
        if not piece:
            break
        total += len(piece)
        if total > max_bytes:
            raise HTTPException(413, "File too large")
        pieces.append(piece)
    content = b"".join(pieces)

    filename = file.filename or "upload"
    content_hash = hashlib.sha256(content).hexdigest()

    # Idempotent: identical content already indexed for this tenant? Return
    # the existing document without creating duplicates or new chunks.
    existing = db.execute(
        select(Document).where(
            Document.content_hash == content_hash,
            Document.tenant_id == tenant_id,
        )
    ).first()
    if existing:
        document = existing[0]
        chunk_count = (
            db.execute(
                select(func.count(Chunk.id)).where(
                    Chunk.document_id == document.id
                )
            )
            .scalar()
            or 0
        )
        return DocumentOut(
            id=document.id,
            filename=document.filename,
            created_at=document.created_at,
            chunk_count=chunk_count,
        )

    try:
        text = extract_text(filename, content)
    except ValueError as exc:
        raise HTTPException(415, str(exc))

    chunks = chunk_text(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
    if not chunks:
        raise HTTPException(400, "No text extracted from document")

    # Embed before touching the database so a provider failure leaves no
    # partial write behind.
    vectors = embeddings.embed_texts(chunks)

    # Same filename + same tenant, different content → new version: replace
    # old chunks. Different tenant with same filename is a separate document.
    existing_by_name = db.execute(
        select(Document).where(
            Document.filename == filename, Document.tenant_id == tenant_id
        )
    ).first()
    if existing_by_name:
        document = existing_by_name[0]
        document.version += 1
        document.content_hash = content_hash
        db.execute(
            delete(Chunk).where(Chunk.document_id == document.id)
        )
    else:
        document = Document(
            filename=filename,
            tenant_id=tenant_id,
            content_hash=content_hash,
            version=1,
        )
        db.add(document)
    db.flush()  # assign document.id

    try:
        db.add_all(
            [
                Chunk(
                    document_id=document.id,
                    chunk_index=index,
                    text=chunk,
                    embedding=vector,
                )
                for index, (chunk, vector) in enumerate(zip(chunks, vectors))
            ]
        )
        db.commit()
        db.refresh(document)
    except Exception:
        db.rollback()
        raise

    return DocumentOut(
        id=document.id,
        filename=document.filename,
        created_at=document.created_at,
        chunk_count=len(chunks),
    )


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db), tenant_id: str = Depends(get_tenant_id)
):
    statement = (
        select(Document, func.count(Chunk.id).label("chunk_count"))
        .outerjoin(Chunk, Chunk.document_id == Document.id)
        .where(Document.tenant_id == tenant_id)
        .group_by(Document.id)
        .order_by(Document.created_at.desc())
    )
    rows = db.execute(statement).all()
    return [
        DocumentOut(
            id=document.id,
            filename=document.filename,
            created_at=document.created_at,
            chunk_count=chunk_count,
        )
        for document, chunk_count in rows
    ]
