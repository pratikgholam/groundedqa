# Grounded QA

A document Q&A API that answers questions using only your documents and cites the chunks it used. Built with FastAPI, PostgreSQL + pgvector, and Docker.

> Portfolio project. Uses sample documents only. Built with AI-assisted tooling; design decisions and trade-offs are documented below.

## How it works

**Ingest:** `POST /documents` extracts text, splits it into overlapping chunks, embeds each chunk, and stores text and vectors in PostgreSQL (pgvector).

**Ask:** `POST /ask` embeds the question and retrieves the top-k most similar chunks from PostgreSQL (pgvector). When no chunk meets `SIMILARITY_CUTOFF`, it returns `found=false` with no LLM call. Otherwise it runs an answerability check: one extra chat call that must reply exactly `YES` (case and whitespace insensitive) for the chunks to be considered to contain the answer. If the check fails, it returns `found=false`. If the check passes, it generates an answer using only the retrieved chunks and returns `found=true` with citations; each citation's `page` is `null` for now.

## API

| Method | Path | Auth required | Description |
|---|---|---|---|
| POST | `/documents` | Yes (X-API-Key) | Upload and index a document |
| GET | `/documents` | Yes (X-API-Key) | List indexed documents |
| POST | `/ask` | Yes (X-API-Key) | Ask a question; returns answer, found, and citations |
| GET | `/health` | No | Health check |

## Error behavior

Upstream provider (embedding/LLM) failures return HTTP 502 with a generic message (`"Upstream model provider unavailable. Try again later."`) and are logged at `ERROR`. Provider exception messages are never returned to the client or included in the log message.

## Security

All mutating and read endpoints (`/documents`, `/ask`) require an `X-API-Key`
header matching the configured `API_KEY`. `/health` is unauthenticated for
uptime checks. When `API_KEY` is empty (the default), authentication is
disabled — suitable only for local/dev use.

Requests are rate-limited per client IP (`RATE_LIMIT_REQUESTS` per
`RATE_LIMIT_WINDOW` seconds). Responses include security headers:
`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
`Referrer-Policy: no-referrer`, and a restrictive `Content-Security-Policy`.

The Docker image runs as a non-root user (`groundedqa`).

## Data model (current schema)

- `documents`: id, filename, content_hash, version, created_at
- `chunks`: id, document_id, chunk_index, text, embedding (vector)

`content_hash` (SHA-256 of the file bytes) makes re-ingestion idempotent:
uploading the same file twice returns the existing document without creating
duplicates. Uploading the same filename with different content bumps `version`
and replaces the old chunks.

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

## Configuration

Settings are loaded from environment (via `.env`) with these defaults:

| Variable | Default |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/groundedqa` |
| `OPENAI_API_KEY` | `""` |
| `EMBEDDING_BASE_URL` | `https://api.openai.com/v1` |
| `EMBEDDING_API_KEY` | `""` (falls back to `OPENAI_API_KEY`) |
| `EMBEDDING_MODEL` | `text-embedding-3-small` |
| `CHAT_BASE_URL` | `https://api.openai.com/v1` |
| `CHAT_API_KEY` | `""` (falls back to `OPENAI_API_KEY`) |
| `CHAT_MODEL` | `gpt-4o-mini` |
| `EMBEDDING_DIM` | `1536` |
| `CHUNK_SIZE` | `800` |
| `CHUNK_OVERLAP` | `100` |
| `TOP_K` | `5` |
| `SIMILARITY_CUTOFF` | `0.3` |
| `MAX_UPLOAD_MB` | `10` |
| `LOG_LEVEL` | `INFO` |
| `API_KEY` | `""` (auth disabled when empty) |
| `RATE_LIMIT_REQUESTS` | `60` |
| `RATE_LIMIT_WINDOW` | `60` |
| `MAX_QUESTION_LENGTH` | `4000` |

Defaults use OpenAI (`text-embedding-3-small` for embeddings,
`gpt-4o-mini` for chat). To use another OpenAI-compatible provider, override
`EMBEDDING_BASE_URL`, `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `EMBEDDING_API_KEY`,
`CHAT_BASE_URL`, `CHAT_MODEL`, and `CHAT_API_KEY`; `EMBEDDING_DIM` must match
the DB column (`vector(1536)` for `text-embedding-3-small`).

## Evaluation

`eval/run_eval.py` reports the retrieval hit rate over the questions in
`eval/questions.json` against the corpus in `eval/corpus/`. Run
`python eval/run_eval.py --scores` to pick `SIMILARITY_CUTOFF` from data, or
`python eval/run_eval.py --answerability` to run the full /ask pipeline
(retrieval, cutoff, answerability check, generation). No hit-rate or
answerability number is published here; see `eval/README.md` for how to run it.

## Design decisions and trade-offs

Fill in with what you actually chose and why:

- **Chunk size and overlap:** _what you tested, what the eval showed_
- **Embedding model / LLM provider:** _choice and reason (cost, quality, local vs hosted)_
- **Top-k and similarity cutoff:** _how you picked them_
- **No orchestration framework:** the provider SDK is called directly to keep the pipeline explicit.

## Limitations

- **pgvector extension:** `init_db` runs `CREATE EXTENSION IF NOT EXISTS vector`, which requires superuser privileges; managed Postgres without extension rights will fail to start. Startup now fails fast with a clear error instead of failing on first ingestion.
- **Auth is single-key:** one `API_KEY` controls access to all endpoints; there is no per-client key rotation or tenant isolation (planned for Stage 8).
- **Rate limiting is in-memory:** the limiter is per-process and not shared across workers or restart-safe.
- **Embedding/LLM calls go to the configured provider:** defaults to OpenAI
  (`text-embedding-3-small` for embeddings, `gpt-4o-mini` for chat); an API key
  is required for real ingestion and answers. Tests mock providers, so the
  suite needs no API key.
- **Chunking is character-based**, not token-based; results depend on the `CHUNK_SIZE`/`CHUNK_OVERLAP` settings.
- **`found=true` is not a support guarantee:** it only means retrieved chunks passed `SIMILARITY_CUTOFF`; the model is not required to confirm support, so it may still answer from weak context.
- **The similarity cutoff does not reliably separate on-topic from off-topic questions** on the current 5-document test corpus. As a result, `found=false` may not trigger for off-topic questions.
- **The answerability check depends on the chat model's judgment.** Its accuracy has not been measured.
- **With the local chat model, `/ask` is slow.** Latency depends on the hardware and the model.
- **Page citations are not implemented:** every citation's `page` is `null`; page-level citations require a schema migration and extraction change (planned).
- **Embedding dimension derives from `EMBEDDING_DIM`:** `db/init.sql` no longer hard-codes the vector dimension; `init_db()` sets `chunks.embedding` to `vector(EMBEDDING_DIM)` on first startup and verifies the match on every start. If you override `EMBEDDING_DIM` on an existing database, the app refuses to start rather than risk silently storing mismatched vectors.
- **PDFs must have a text layer:** scanned/image-only PDFs yield no text.
- **No streaming / pagination:** `/documents` returns all documents at once.

## Possible next steps

- _Only list things you'd genuinely do._
