# POST /ask
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import AskIn, AskOut, CitationOut
from app.services import generation
from app.services.retrieval import retrieve

router = APIRouter()


@router.post("/ask", response_model=AskOut)
def ask(
    payload: AskIn,
    db: Session = Depends(get_db),
):
    if not payload.question or not payload.question.strip():
        raise HTTPException(400, "Question is required")
    sources = retrieve(payload.question.strip(), db)
    if not sources:
        return AskOut(answer="", found=False, citations=[])
    answer = generation.generate_answer(payload.question.strip(), sources)
    citations = [
        CitationOut(
            document_id=source["document_id"],
            page=None,
            passage=source["text"],
        )
        for source in sources
    ]
    return AskOut(answer=answer, found=True, citations=citations)
