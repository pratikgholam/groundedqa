# Evaluation (Stage 5) — retrieval hit rate

Run the retrieval hit-rate eval:

    cp .env.example .env                  # set OPENAI_API_KEY
    docker compose up -d db               # Postgres with pgvector must be running
    python eval/run_eval.py

Run the score diagnostic to pick SIMILARITY_CUTOFF from data:

    python eval/run_eval.py --scores

The script ingests eval/corpus through the same ingestion code the API uses,
runs retrieval for each question in eval/questions.json, and prints the hit
rate plus misses. It always exits 0 and deletes the documents it inserts, so
re-running is safe. Unit tests (tests/test_eval.py) need no API key or network.

The corpus is 5 small hand-written documents and 17 scored questions, so the
hit rate shows the pipeline works end to end, not general retrieval quality.

Score diagnostic (last run): scored top-1 scores range 0.4540–0.8635; no-source
top-1 scores range 0.5203–0.6085. The groups overlap, so no cutoff separates
them cleanly; SIMILARITY_CUTOFF stays at 0.3.
