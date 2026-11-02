# Grounded QA

A document Q&A API that answers questions using only your documents and cites the chunks it used. Built with FastAPI, PostgreSQL + pgvector, and Docker.

> Portfolio project. Uses sample documents only. Built with AI-assisted tooling; design decisions and trade-offs are documented below.

## How it works

**Ingest:** `POST /documents` extracts text, splits it into overlapping chunks, embeds each chunk, and stores text and vectors in PostgreSQL (pgvector).

**Ask:** `POST /ask` embeds the question and returns the top-k most similar chunks, each with its source document and a similarity score. The service returns the retrieved chunks; no answer is generated yet.

## API

| Method | Path | Description |
|---|---|---|
| POST | `/documents` | Upload and index a document |
| GET | `/documents` | List indexed documents |
| POST | `/ask` | Ask a question; returns retrieved chunks |
| GET | `/health` | Health check |

## Data model (current schema)

- `documents`: id, filename, created_at
- `chunks`: id, document_id, chunk_index, text, embedding (vector)

## Tech stack

Python, FastAPI, PostgreSQL + pgvector, pytest, Docker Compose.

CI via GitHub Actions is planned (no `.github/workflows` yet).

## Run locally

```bash
cp .env.example .env   # add your provider API key
docker compose up --build
```

API docs at `http://localhost:8000/docs`.

## Tests

```bash
pytest
```

LLM and embedding calls are mocked, so tests need no API key.

## Evaluation

`eval/questions.json` is a placeholder question set and `eval/run.py` is not yet implemented. Evaluation (Stage 5) is planned.

## Design decisions and trade-offs

Fill in with what you actually chose and why:

- **Chunk size and overlap:** _what you tested, what the eval showed_
- **Embedding model / LLM provider:** _choice and reason (cost, quality, local vs hosted)_
- **Top-k and similarity cutoff:** _how you picked them_
- **No orchestration framework:** the provider SDK is called directly to keep the pipeline explicit.

## Limitations

- **pgvector extension:** `init_db` runs `CREATE EXTENSION IF NOT EXISTS vector`, which requires superuser privileges; managed Postgres without extension rights will fail to start.
- **No auth or rate limiting:** anyone who can reach the API can upload and query documents.
- **Embedding/LLM calls go to OpenAI:** an API key is required for real ingestion and answers; tests mock these.
- **Chunking is character-based**, not token-based; results depend on the `CHUNK_SIZE`/`CHUNK_OVERLAP` settings.
- **PDFs must have a text layer:** scanned/image-only PDFs yield no text.
- **No streaming / pagination:** `/documents` returns all documents at once.

## Possible next steps

- _Only list things you'd genuinely do._
