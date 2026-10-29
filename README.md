# Grounded QA

A document Q&A API that answers questions using only your documents and cites the chunks it used. Built with FastAPI, PostgreSQL + pgvector, and Docker.

> Portfolio project. Uses sample documents only. Built with AI-assisted tooling; design decisions and trade-offs are documented below.

## How it works

**Ingest:** `POST /documents` extracts text, splits it into overlapping chunks, embeds each chunk, and stores text and vectors in PostgreSQL (pgvector).

**Ask:** `POST /ask` embeds the question, retrieves the top-k most similar chunks, and sends them with the question to an LLM. The answer includes the source chunks. If the retrieved context doesn't support an answer, the service says so instead of guessing.

## API

| Method | Path | Description |
|---|---|---|
| POST | `/documents` | Upload and index a document |
| GET | `/documents` | List indexed documents |
| POST | `/ask` | Ask a question; returns answer and sources |
| GET | `/health` | Health check |

## Data model

- `documents`: id, filename, created_at
- `chunks`: id, document_id, chunk_index, text, embedding (vector)

## Tech stack

Python, FastAPI, PostgreSQL + pgvector, pytest, Docker Compose, GitHub Actions.

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

`eval/` contains a small question set with expected source chunks. Run:

```bash
python -m eval.run
```

Results (fill in from real runs):

| Chunk size / overlap | top-k | Retrieval hit rate |
|---|---|---|
| _TBD_ | _TBD_ | _TBD_ |

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
