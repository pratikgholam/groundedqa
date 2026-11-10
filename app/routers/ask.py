# POST /ask
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_tenant_id, rate_limit, verify_api_key
from app.db import get_db
from app.schemas import AskIn, AskOut, CitationOut
from app.services import generation
from app.services.retrieval import retrieve

router = APIRouter()


@router.post(
    "/ask",
    response_model=AskOut,
    dependencies=[Depends(verify_api_key), Depends(rate_limit)],
)
def ask(
    payload: AskIn,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    if not payload.question or not payload.question.strip():
        raise HTTPException(400, "Question is required")
    sources = retrieve(payload.question.strip(), db, tenant_id=tenant_id)
    if not sources:
        return AskOut(answer="", found=False, citations=[])
    if not generation.check_answerable(payload.question.strip(), sources):
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
