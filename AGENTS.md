# AGENTS.md

Instructions for AI coding agents working in this repo.

## Project

`groundedqa`: a document Q&A API (RAG). Users upload documents; the service chunks and embeds them, stores vectors in PostgreSQL (pgvector), and answers questions using only retrieved chunks, with citations. If the context doesn't support an answer, it says so.

Product goal: a self-hostable grounded document Q&A service. It should run with `docker compose up`, be configurable without code changes, and be usable directly or customized per client.

This is a public portfolio project. Use fake or public sample documents only. No employer code or data. Clients' documents are never committed to this repo, and the code must work with any document set.

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

## Data model

- `documents`: id, tenant_id, filename, content_hash, version, created_at
- `chunks`: id, document_id (cascade delete), chunk_index, page, text, embedding (vector)

Re-ingesting an identical file (same content_hash) must not create duplicates. A new version replaces the old chunks.

## Endpoints

- `POST /documents`: upload and index a document
- `GET /documents`: list indexed documents
- `POST /ask`: question in, answer plus sources out
- `GET /health`: health check

## Answer contract

`POST /ask` returns:
- `answer` (string)
- `found` (bool)
- `citations`: list of { document_id, page, passage }

If no chunk meets the relevance threshold, return `found=false` and do not call the LLM.

## Configuration

Provider, model names, top-k, chunk size, and relevance threshold live in config with env overrides. No hard-coded values in service code.

## Decisions

- Citations for Stage 4 include `page` as null for now. Page-level citations are a later stage, requiring a schema migration and an extraction change.
- DRAFT (owner to edit in own words): /ask makes one extra chat call after retrieval to decide whether the chunks contain the answer. Anything other than exactly YES returns found=false, so the check fails closed. The similarity cutoff alone was shown not to separate on-topic from off-topic questions on the test corpus, which is why the check exists. The check adds latency and depends on the local model's judgment. Its accuracy is not yet measured.

## Stages

Mark a stage done only when it works and is tested.

- [x] Stage 1: FastAPI skeleton, Postgres + pgvector via Docker Compose, `/health`
- [x] Stage 2: Ingestion (text extraction, chunking with overlap, embeddings, storage)
- [x] Stage 3: Retrieval endpoint (similarity search returning raw chunks)
- [x] Stage 4: Answer generation with citations and a "not enough context" path (page may be null until page extraction is added)
- [x] Stage 5: Evaluation script (~20 questions with expected sources, reports retrieval hit rate)
- [ ] Stage 6: pytest suite (mocked providers) and GitHub Actions CI
- [ ] Stage 7: Ingestion CLI (`groundedqa ingest <folder>`), idempotent
- [ ] Stage 8: Auth (API key) and tenant-filtered retrieval
- [ ] Stage 9: Config and env overrides for all tunables. Embedding dimension is hard-coded to 1536 in db/init.sql while EMBEDDING_DIM is configurable. Make these consistent, and enforce a match at startup.
- [ ] Stage 10: Packaging (quickstart in README, health and structured request logs). Upstream provider errors return 502 with a generic message and log at ERROR.
- [ ] Stage 11: License file and dependency license check