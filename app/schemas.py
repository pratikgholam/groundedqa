# request/response models (Pydantic)
from datetime import datetime
from pydantic import BaseModel


class HealthOut(BaseModel):
    status: str
    database: str


class DocumentOut(BaseModel):
    id: int
    filename: str
    created_at: datetime
    chunk_count: int


class ChunkOut(BaseModel):
    document: str
    text: str
    score: float


class AskIn(BaseModel):
    question: str


class AskOut(BaseModel):
    sources: list[ChunkOut]
