# FastAPI app, router registration
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.routers import documents, health, ask


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Grounded QA", lifespan=lifespan)

app.include_router(health.router)
app.include_router(documents.router)
app.include_router(ask.router)


@app.get("/")
def root():
    return {"message": "Grounded QA API. See /docs"}
