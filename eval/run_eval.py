"""Retrieval hit-rate evaluation for groundedqa (Stage 5).

Ingests every file in eval/corpus through the same ingestion code the API
uses (extract_text -> chunk_text -> embed_texts -> store Chunk rows), then,
for each question in eval/questions.json, runs retrieval with the configured
TOP_K and reports the hit rate.

Exit code is always 0: this script reports numbers, it does not pass or fail
on them.

Prerequisites:
  * Postgres with pgvector running at settings.DATABASE_URL
  * EMBEDDING_API_KEY set (the eval calls the real embedding provider)

With --scores, instead of the hit-rate report it prints a per-question
diagnostic: each question's group (scored / no-source), expected filename,
top-1 similarity score, and the filename of the top-1 chunk, plus summary
stats (min / max / mean) per group. This is used to pick SIMILARITY_CUTOFF
from data, not from a round number.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from pathlib import Path

# Allow `python eval/run_eval.py` from the repo root: put the repo root on
# sys.path so the `app` package is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.db import SessionLocal, init_db
from app.models import Chunk, Document
from app.services import embeddings
from app.services import generation
from app.services.chunking import chunk_text
from app.services.extraction import extract_text
from app.services.retrieval import retrieve
from sqlalchemy import text as sql_text

BASE_DIR = Path(__file__).resolve().parent
CORPUS_DIR = BASE_DIR / "corpus"
QUESTIONS_PATH = BASE_DIR / "questions.json"


def load_questions(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def partition_questions(questions: list[dict]):
    """Split questions into (scored, no_source).

    Scored questions have an expected_filename; no_source questions have
    expected_filename set to null and are excluded from the hit rate.
    """
    scored = [q for q in questions if q.get("expected_filename") is not None]
    no_source = [q for q in questions if q.get("expected_filename") is None]
    return scored, no_source


def top1_score(question: str, db, top_k: int) -> tuple[float | None, str | None]:
    """Return (top-1 similarity score, top-1 filename) for a question.

    Runs retrieval with similarity_cutoff=0.0 so the top-1 score is visible
    even when it falls below the configured cutoff (needed to pick a cutoff
    from data). Returns (None, None) when there are no chunks at all.
    """
    results = retrieve(question, db, top_k=top_k, similarity_cutoff=0.0)
    if not results:
        return None, None
    return results[0]["score"], results[0]["document"]


def group_stats(scores: list[float | None]) -> dict[str, float | None]:
    valid = [s for s in scores if s is not None]
    if not valid:
        return {"min": None, "max": None, "mean": None, "count": 0}
    return {
        "min": round(min(valid), 4),
        "max": round(max(valid), 4),
        "mean": round(statistics.mean(valid), 4),
        "count": len(valid),
    }


def print_score_report(questions: list[dict], db, top_k: int) -> None:
    """Print per-question top-1 scores and per-group summary stats."""
    scored, no_source = partition_questions(questions)

    print(f"Per-question top-1 similarity scores (top_k={top_k}, cutoff=0.0):")
    print(f"{'Group':<10} {'Expected':<24} {'Top-1 score':<12} {'Top-1 file':<24} Question")
    print("-" * 100)

    scored_scores: list[float | None] = []
    no_source_scores: list[float | None] = []

    def row(group: str, q: dict, expected: str | None) -> None:
        score, filename = top1_score(q["question"], db, top_k)
        score_str = f"{score:.4f}" if score is not None else "(none)"
        file_str = filename or "(none)"
        print(
            f"{group:<10} {str(expected):<24} {score_str:<12} {file_str:<24} {q['question']}"
        )
        if group == "scored":
            scored_scores.append(score)
        else:
            no_source_scores.append(score)

    for q in scored:
        row("scored", q, q.get("expected_filename"))
    for q in no_source:
        row("no-source", q, None)

    print()
    print("Group stats (top-1 score):")
    print(f"  scored:   {group_stats(scored_scores)}")
    print(f"  no-source: {group_stats(no_source_scores)}")


def run_answerability(questions: list[dict], db, top_k: int, cutoff: float) -> None:
    """Run the full /ask pipeline for all questions and report found-rates.

    For each question: retrieve chunks, apply similarity cutoff, run the
    answerability check on the retrieved chunks, then (if answerable) generate
    an answer. Reports found-rate for scored questions and reject-rate
    (found=false) for no-source questions.
    """
    scored, no_source = partition_questions(questions)

    def evaluate(q: dict, expected_found: bool) -> dict:
        results = retrieve(q["question"], db, top_k=top_k, similarity_cutoff=cutoff)
        if not results:
            return {
                "question": q["question"],
                "expected_found": expected_found,
                "actual_found": False,
                "check_reply": "(none - below cutoff or no chunks)",
            }
        answerable = generation.check_answerable(q["question"], results)
        return {
            "question": q["question"],
            "expected_found": expected_found,
            "actual_found": answerable,
            "check_reply": str(answerable),
        }

    scored_results = [evaluate(q, True) for q in scored]
    no_source_results = [evaluate(q, False) for q in no_source]

    scored_found = sum(1 for r in scored_results if r["actual_found"])
    no_source_rejected = sum(1 for r in no_source_results if not r["actual_found"])

    scored_found_rate = hit_rate_percent(scored_found, len(scored_results))
    no_source_reject_rate = hit_rate_percent(
        no_source_rejected, len(no_source_results)
    )

    print("GroundedQA answerability evaluation")
    print(f"Embedding model: {settings.EMBEDDING_MODEL} (dim {settings.EMBEDDING_DIM})")
    print(f"Chat model: {settings.CHAT_MODEL}")
    print(f"Top-k: {top_k}, similarity cutoff: {cutoff}")
    print()
    print(f"Total questions: {len(questions)}")
    print(f"Scored questions: {len(scored_results)}")
    print(f"Scored found-rate: {scored_found_rate:.1f}% ({scored_found}/{len(scored_results)})")
    print(f"No-source questions: {len(no_source_results)}")
    print(
        f"No-source reject-rate: {no_source_reject_rate:.1f}% "
        f"({no_source_rejected}/{len(no_source_results)})"
    )
    print()

    misses = [
        r
        for r in scored_results + no_source_results
        if r["actual_found"] != r["expected_found"]
    ]
    if misses:
        print("Misses:")
        for m in misses:
            expected = "found=true" if m["expected_found"] else "found=false"
            actual = "found=true" if m["actual_found"] else "found=false"
            print(f'  Q: {m["question"]}')
            print(f'    expected: {expected}')
            print(f'    actual: {actual}')
            print(f'    check reply: {m["check_reply"]}')
    else:
        print("Misses: none")


def is_hit(expected_filename: str | None, returned_filenames: list[str]) -> bool:
    """True when the expected document is among the returned filenames."""
    if expected_filename is None:
        return False
    return expected_filename in returned_filenames


def hit_rate_percent(hits: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(hits / total * 100, 1)


def _db_vector_dimension(db) -> int | None:
    row = db.execute(
        sql_text(
            "SELECT atttypmod FROM pg_attribute "
            "WHERE attrelid = 'chunks'::regclass AND attname = 'embedding'"
        )
    ).first()
    return row[0] if row else None


def ensure_dimension_matches(db) -> None:
    """Fail clearly if the configured dimension differs from the DB schema.

    db/init.sql fixes chunks.embedding at a fixed dimension while EMBEDDING_DIM is
    configurable; they must match. This is enforced here instead of patching
    around a mismatch (the real fix is Stage 9).
    """
    actual = _db_vector_dimension(db)
    if actual is None:
        raise SystemExit(
            "could not read the chunks.embedding dimension from the database; "
            "make sure pgvector and the chunks table exist"
        )
    if actual != settings.EMBEDDING_DIM:
        raise SystemExit(
            "embedding dimension mismatch: "
            f"EMBEDDING_DIM={settings.EMBEDDING_DIM} but the database stores "
            f"chunks.embedding as vector({actual}); "
            "reconcile EMBEDDING_DIM with the schema (Stage 9) before running the eval"
        )


def ingest_corpus(db):
    """Ingest eval/corpus using the API's ingestion code.

    Returns a list of (filename, document_id, chunk_count). The caller owns
    cleanup (delete the inserted documents).
    """
    inserted = []
    for path in sorted(CORPUS_DIR.iterdir()):
        if not path.is_file():
            continue
        content = path.read_bytes()
        text = extract_text(path.name, content)
        chunks = chunk_text(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
        if not chunks:
            inserted.append((path.name, None, 0))
            continue
        vectors = embeddings.embed_texts(chunks)
        content_hash = hashlib.sha256(content).hexdigest()
        document = Document(
            filename=path.name,
            tenant_id="tenant-1",
            content_hash=content_hash,
            version=1,
        )
        db.add(document)
        db.flush()
        db.add_all(
            [
                Chunk(
                    document_id=document.id,
                    chunk_index=index,
                    text=chunk,
                    embedding=vector,
                )
                for index, (chunk, vector) in enumerate(zip(chunks, vectors))
            ]
        )
        db.commit()
        inserted.append((path.name, document.id, len(chunks)))
    return inserted


def cleanup_documents(db, document_ids) -> None:
    for doc_id in document_ids:
        if doc_id is None:
            continue
        db.execute(sql_text("DELETE FROM documents WHERE id = :id"), {"id": doc_id})
    db.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="GroundedQA retrieval evaluation")
    parser.add_argument(
        "--scores",
        action="store_true",
        help="Print per-question top-1 similarity diagnostic and group stats, "
        "then exit (no hit-rate report).",
    )
    parser.add_argument(
        "--answerability",
        action="store_true",
        help="Run the full /ask pipeline (retrieval, cutoff, answerability "
        "check, generation) for all questions and report found-rates.",
    )
    args = parser.parse_args()

    if not settings.EMBEDDING_API_KEY:
        raise SystemExit(
            "EMBEDDING_API_KEY is not set; the eval calls the real embedding provider. "
            "Copy .env.example to .env and add your key (or use the Ollama default)."
        )

    init_db()  # pgvector extension + tables (idempotent)

    db = SessionLocal()
    try:
        ensure_dimension_matches(db)

        questions = load_questions(QUESTIONS_PATH)

        inserted = ingest_corpus(db)
        try:
            if args.scores:
                print_score_report(questions, db, settings.TOP_K)
                return 0

            if args.answerability:
                run_answerability(questions, db, settings.TOP_K, settings.SIMILARITY_CUTOFF)
                return 0

            scored, no_source = partition_questions(questions)
            top_k = settings.TOP_K
            cutoff = settings.SIMILARITY_CUTOFF

            misses = []
            hits = 0
            for q in scored:
                results = retrieve(
                    q["question"], db, top_k=top_k, similarity_cutoff=cutoff
                )
                returned = [r["document"] for r in results]
                if is_hit(q.get("expected_filename"), returned):
                    hits += 1
                else:
                    misses.append(
                        {
                            "question": q["question"],
                            "expected": q.get("expected_filename"),
                            "returned": returned,
                        }
                    )

            no_source_results = []
            for q in no_source:
                results = retrieve(
                    q["question"], db, top_k=top_k, similarity_cutoff=cutoff
                )
                no_source_results.append(
                    {
                        "question": q["question"],
                        "returned_zero_chunks": len(results) == 0,
                        "returned_count": len(results),
                    }
                )
        finally:
            cleanup_documents(db, [doc_id for _, doc_id, _ in inserted])

        total_scored = len(scored)
        rate = hit_rate_percent(hits, total_scored)

        print("GroundedQA retrieval evaluation")
        print(f"Corpus documents: {len(inserted)} in {CORPUS_DIR.name}")
        print(
            f"Embedding model: {settings.EMBEDDING_MODEL} (dim {settings.EMBEDDING_DIM})"
        )
        print(f"Top-k: {top_k}, similarity cutoff: {cutoff}")
        print(f"Hit rule: expected document within top {top_k} chunks, matched by filename")
        print()
        print(f"Total questions: {len(questions)}")
        print(f"No-source questions (expected_filename null): {len(no_source)}")
        print(f"Scored questions: {total_scored}")
        print(f"Hits: {hits}")
        print(f"Hit rate: {rate:.1f}%")
        print()
        if misses:
            print("Misses:")
            for m in misses:
                returned = ", ".join(m["returned"]) if m["returned"] else "(none)"
                print(f'  Q: {m["question"]}')
                print(f'    expected: {m["expected"]}')
                print(f'    returned: {returned}')
        else:
            print("Misses: none")
        print()
        print("No-source questions:")
        for ns in no_source_results:
            if ns["returned_zero_chunks"]:
                status = "zero chunks (expected)"
            else:
                status = f'{ns["returned_count"]} chunks (unexpected)'
            print(f'  Q: {ns["question"]} -> {status}')
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
