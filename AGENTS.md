# AGENTS.md

Instructions for AI coding agents working in this repo.

## Project

`groundedqa`: a document Q&A API (RAG). Users upload documents; the service chunks and embeds them, stores vectors in PostgreSQL (pgvector), and answers questions using only retrieved chunks, with citations. If the context doesn't support an answer, it says so.

This is a public portfolio project. Use fake or public sample documents only. No employer code or data.

## Stack

Python, FastAPI, PostgreSQL + pgvector, pytest, Docker Compose, GitHub Actions.

## Rules

- Call the LLM/embedding provider SDK directly. No LangChain, LlamaIndex, or similar orchestration frameworks.
- No chat UI. This project is the API.
- Work one stage at a time (see below). Don't start the next stage until the current one builds, runs, and has passing tests.
- Verify library versions and APIs against current documentation before using them. Don't rely on memory.
- Tests must not call real LLM or embedding APIs. Mock them. The suite must pass with no API key.
- Never commit secrets. Keep `.env` out of git and maintain `.env.example`.
- Explain non-obvious design choices and trade-offs when making them, so the owner can state them in his own words in the README.
- Prefer small, readable code the owner can explain line by line over clever abstractions.

## README honesty

- The README must not describe anything the code doesn't do.
- Update the README only when the code and tests back the change.
- Leave the evaluation results and design-decision sections for the owner to fill in from real runs and real choices. Don't invent numbers.

## Stages

Mark a stage done only when it works and is tested.

- [ ] Stage 1: FastAPI skeleton, Postgres + pgvector via Docker Compose, `/health`
- [ ] Stage 2: Ingestion (text extraction, chunking with overlap, embeddings, storage)
- [ ] Stage 3: Retrieval endpoint (similarity search returning raw chunks)
- [ ] Stage 4: Answer generation with citations and a "not enough context" path
- [ ] Stage 5: Evaluation script (~20 questions with expected sources, reports retrieval hit rate)
- [ ] Stage 6: pytest suite (mocked providers) and GitHub Actions CI

## Data model

- `documents`: id, filename, created_at
- `chunks`: id, document_id, chunk_index, text, embedding (vector)

## Endpoints

- `POST /documents`: upload and index a document
- `GET /documents`: list indexed documents
- `POST /ask`: question in, answer plus sources out
- `GET /health`: health check
