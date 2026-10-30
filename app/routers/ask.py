# POST /ask
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import AskIn, AskOut
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
    return AskOut(sources=sources)
