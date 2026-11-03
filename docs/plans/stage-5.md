# Stage 5 plan — retrieval hit-rate evaluation

## Goal
A `eval/run_eval.py` script that reports the retrieval hit rate over ~20 questions with expected sources, using the real embedding provider and the same ingestion/retrieval code the API uses. No code change to `app/` except calling existing functions directly; no change to `db/init.sql` or vector dimension.

## Open questions and resolutions (defaults from the prompt)
1. **Script location** → `eval/run_eval.py`.
2. **"Same ingestion code the API uses"** → reuse the exact service functions the `/documents` router calls: `extract_text` → `chunk_text` → `embed_texts` → store `Chunk` rows via `app.models`, driven by a SQLAlchemy session directly (no TestClient/HTTP reimplementation).
3. **Dimension mismatch guard** → after `init_db()`, read `chunks.embedding` typmod from pg_attribute and compare to `settings.EMBEDDING_DIM`; `SystemExit` with a clear message if they differ. No patching around it; `db/init.sql` untouched.
4. **Unanswerable questions** → `expected_filename: null`; reported separately as "no-source questions", excluded from hit rate; report only whether retrieval returned zero chunks above `SIMILARITY_CUTOFF`.
5. **Config** → all values read from `app.config.settings` (`TOP_K`, `SIMILARITY_CUTOFF`, `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `OPENAI_API_KEY`, `DATABASE_URL`). Nothing hard-coded.
6. **Exit code** → always 0; the script reports numbers, does not pass/fail.
7. **Database hygiene** → ingest into the configured DB, track inserted document IDs, delete them (cascade removes chunks) at the end. Document in `eval/README.md`.
8. **Corpus** → 5 small documents written by me (fictional/general knowledge, no downloads, no client/employer data) in `eval/corpus/`.

## Files to create/change
1. `docs/plans/stage-5.md` (this file)
2. `eval/corpus/*.txt` — 5 sample documents
3. `eval/questions.json` — ~20 entries (`question`, `expected_filename`; 3 with `null`)
4. `eval/run_eval.py` — the evaluation script
5. `eval/README.md` — ≤20 lines, how to run
6. `tests/test_eval.py` — unit tests for pure helpers (load_questions, partition_questions, is_hit, hit_rate); no network

## Verification
- `pytest tests/test_eval.py` (and full suite) passes with no API key.
- `python eval/run_eval.py` runs for real against the local Postgres + OpenAI embedding API; paste actual output. Requires `OPENAI_API_KEY` and a running Postgres with pgvector.

## Deliberately out of scope (Stage 6+)
- pytest suite for the API, GitHub Actions CI, ingestion CLI, auth, packaging.
