# request/response models (Pydantic)
from datetime import datetime
from pydantic import BaseModel, Field

from app.config import settings


class HealthOut(BaseModel):
    status: str
    database: str


class DocumentOut(BaseModel):
    id: int
    filename: str
    created_at: datetime
    chunk_count: int


class CitationOut(BaseModel):
    document_id: int
    page: int | None = None
    passage: str


class AskIn(BaseModel):
    question: str = Field(max_length=settings.MAX_QUESTION_LENGTH)


class AskOut(BaseModel):
    answer: str
    found: bool
    citations: list[CitationOut]
