# Grounded QA

A document Q&A API that answers questions using only your documents and cites the chunks it used. Built with FastAPI, PostgreSQL + pgvector, and Docker.

> Portfolio project. Uses sample documents only. Built with AI-assisted tooling; design decisions and trade-offs are documented below.

## Status

Tick these only when the code and tests back them up.

- [ ] Stage 1: FastAPI skeleton, Postgres + pgvector via Docker Compose, health check
- [ ] Stage 2: Ingestion (text extraction, chunking, embeddings, storage)
- [ ] Stage 3: Retrieval endpoint (similarity search)
- [ ] Stage 4: Answer generation with citations and a "not enough context" path
- [ ] Stage 5: Evaluation script (retrieval hit rate)
- [ ] Stage 6: pytest suite (LLM/embedding calls mocked) and GitHub Actions CI

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

- _List real ones as you find them (e.g., scanned PDFs, large files, no auth)._

## Possible next steps

- _Only list things you'd genuinely do._
