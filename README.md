# Grounded QA

A document Q&A API that answers questions using only your documents and cites the chunks it used. Built with FastAPI, PostgreSQL + pgvector, and Docker.

> Portfolio project. Uses sample documents only. Built with AI-assisted tooling; design decisions and trade-offs are documented below.

## How it works

**Ingest:** `POST /documents` extracts text, splits it into overlapping chunks, embeds each chunk, and stores text and vectors in PostgreSQL (pgvector).

**Ask:** `POST /ask` embeds the question and retrieves the top-k most similar chunks from PostgreSQL (pgvector). When no chunk meets `SIMILARITY_CUTOFF`, it returns `found=false` with no LLM call. Otherwise it runs an answerability check: one extra chat call that must reply exactly `YES` (case and whitespace insensitive) for the chunks to be considered to contain the answer. If the check fails, it returns `found=false`. If the check passes, it generates an answer using only the retrieved chunks and returns `found=true` with citations; each citation's `page` is `null` for now.

## API

| Method | Path | Description |
|---|---|---|
| POST | `/documents` | Upload and index a document |
| GET | `/documents` | List indexed documents |
| POST | `/ask` | Ask a question; returns answer, found, and citations |
| GET | `/health` | Health check |

## Error behavior

Upstream provider (embedding/LLM) failures return HTTP 502 with a generic message (`"Upstream model provider unavailable. Try again later."`) and are logged at `ERROR`. Provider exception messages are never returned to the client or included in the log message.

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

## Configuration

Settings are loaded from environment (via `.env`) with these defaults:

| Variable | Default |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/groundedqa` |
| `OPENAI_API_KEY` | `""` |
| `EMBEDDING_BASE_URL` | `http://localhost:11434/v1` |
| `EMBEDDING_API_KEY` | `"ollama"` |
| `EMBEDDING_MODEL` | `nomic-embed-text` |
| `CHAT_BASE_URL` | `http://localhost:11434/v1` |
| `CHAT_API_KEY` | `"ollama"` |
| `CHAT_MODEL` | `lfm3-qa:latest` |
| `EMBEDDING_DIM` | `768` |
| `CHUNK_SIZE` | `800` |
| `CHUNK_OVERLAP` | `100` |
| `TOP_K` | `5` |
| `SIMILARITY_CUTOFF` | `0.3` |
| `MAX_UPLOAD_MB` | `10` |
| `LOG_LEVEL` | `INFO` |

Defaults use the local Ollama provider (`nomic-embed-text` for embeddings,
`lfm3-qa:latest` for chat). OpenAI users must set `EMBEDDING_BASE_URL`,
`EMBEDDING_MODEL`, `EMBEDDING_DIM`, `EMBEDDING_API_KEY`, `CHAT_BASE_URL`,
`CHAT_MODEL`, and `CHAT_API_KEY`; `EMBEDDING_DIM` must match the DB column
(`vector(768)` for `nomic-embed-text`; `vector(1536)` for
`text-embedding-3-small`).

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

- **pgvector extension:** `init_db` runs `CREATE EXTENSION IF NOT EXISTS vector`, which requires superuser privileges; managed Postgres without extension rights will fail to start.
- **No auth or rate limiting:** anyone who can reach the API can upload and query documents.
- **Embedding/LLM calls go to the configured provider:** defaults to local
  Ollama (`nomic-embed-text`); an API key is not required for Ollama. Tests
  mock providers, so the suite needs no API key.
- **Chunking is character-based**, not token-based; results depend on the `CHUNK_SIZE`/`CHUNK_OVERLAP` settings.
- **`found=true` is not a support guarantee:** it only means retrieved chunks passed `SIMILARITY_CUTOFF`; the model is not required to confirm support, so it may still answer from weak context.
- **The similarity cutoff does not reliably separate on-topic from off-topic questions** on the current 5-document test corpus. As a result, `found=false` may not trigger for off-topic questions.
- **The answerability check depends on the chat model's judgment.** Its accuracy has not been measured.
- **With the local chat model, `/ask` is slow.** Latency depends on the hardware and the model.
- **Page citations are not implemented:** every citation's `page` is `null`; page-level citations require a schema migration and extraction change (planned).
- **Embedding dimension mismatch:** `db/init.sql` fixes the vector column at `vector(768)`, while `EMBEDDING_DIM` is configurable; they must match for storage to work.
- **PDFs must have a text layer:** scanned/image-only PDFs yield no text.
- **No streaming / pagination:** `/documents` returns all documents at once.

## Possible next steps

- _Only list things you'd genuinely do._
