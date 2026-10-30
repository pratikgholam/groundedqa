# Graph Report - groundedqa  (2026-10-30)

## Corpus Check
- Corpus is ~3,406 words - fits in a single context window. You may not need a graph.

## Summary
- 201 nodes · 342 edges · 17 communities (10 shown, 7 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 52 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Core app & config
- Models & retrieval
- Tech stack & rules
- RAG pipeline & stages
- Docker Compose db
- Documents & chunking
- Text extraction
- Ask & health APIs
- Embeddings & docs
- Docker Compose app
- GET /documents endpoint
- License & copyright

## God Nodes (most connected - your core abstractions)
1. `groundedqa project` - 21 edges
2. `Document` - 15 edges
3. `Chunk` - 15 edges
4. `retrieve()` - 13 edges
5. `extract_text()` - 12 edges
6. `upload_document()` - 11 edges
7. `chunk_text()` - 10 edges
8. `get_db()` - 7 edges
9. `_fake_embed()` - 7 edges
10. `ask()` - 6 edges

## Surprising Connections (you probably didn't know these)
- `test_chunking_empty_and_whitespace()` --calls--> `chunk_text()`  [EXTRACTED]
  tests/test_chunking.py → app/services/chunking.py
- `test_chunking_exact_size()` --calls--> `chunk_text()`  [EXTRACTED]
  tests/test_chunking.py → app/services/chunking.py
- `test_chunking_invalid_args()` --calls--> `chunk_text()`  [EXTRACTED]
  tests/test_chunking.py → app/services/chunking.py
- `test_chunking_shorter_than_size()` --calls--> `chunk_text()`  [EXTRACTED]
  tests/test_chunking.py → app/services/chunking.py
- `test_chunking_splits_with_overlap()` --calls--> `chunk_text()`  [EXTRACTED]
  tests/test_chunking.py → app/services/chunking.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **GroundedQA tech stack** — agents_python, agents_fastapi, agents_postgresql_pgvector, agents_pytest, agents_docker_compose, agents_github_actions [INFERRED 0.85]
- **Document ingestion flow** — agents_post_documents_endpoint, agents_documents_table, agents_chunks_table [INFERRED 0.80]
- **GroundedQA API endpoints** — agents_post_documents_endpoint, agents_get_documents_endpoint, agents_post_ask_endpoint, agents_get_health_endpoint [EXTRACTED 1.00]

## Communities (17 total, 7 thin omitted)

### Community 0 - "Core app & config"
Cohesion: 0.12
Nodes (9): Settings, get_db(), init_db(), lifespan(), root(), client(), db_session(), _mock_db() (+1 more)

### Community 1 - "Models & retrieval"
Cohesion: 0.17
Nodes (16): Chunk, Document, retrieve(), _fake_embed(), test_ask_empty_question_returns_400(), test_ask_missing_question_returns_422(), test_ask_non_json_body_returns_422(), test_ask_returns_raw_sources() (+8 more)

### Community 2 - "Tech stack & rules"
Cohesion: 0.09
Nodes (20): Docker Compose, FastAPI, GitHub Actions, groundedqa project, PostgreSQL + pgvector, pytest, Python, Grounded QA project (+12 more)

### Community 3 - "RAG pipeline & stages"
Cohesion: 0.12
Nodes (18): chunks table, documents table, GET /health endpoint, POST /ask endpoint, POST /documents endpoint, Document Q&A RAG pipeline, Stage 1: FastAPI skeleton, Postgres + pgvector, /health, Stage 2: Ingestion (+10 more)

### Community 4 - "Docker Compose db"
Cohesion: 0.12
Nodes (16): environment, healthcheck, image, ports, volumes, POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER (+8 more)

### Community 5 - "Documents & chunking"
Cohesion: 0.17
Nodes (8): list_documents(), upload_document(), chunk_text(), test_chunking_empty_and_whitespace(), test_chunking_exact_size(), test_chunking_invalid_args(), test_chunking_shorter_than_size(), test_chunking_splits_with_overlap()

### Community 6 - "Text extraction"
Cohesion: 0.23
Nodes (8): extract_text(), test_md(), test_pdf_corrupt_raises_valueerror(), test_pdf_via_mocked_reader(), extract_text(), test_txt(), test_txt_non_utf8_raises_valueerror(), test_unsupported_type_raises()

### Community 7 - "Ask & health APIs"
Cohesion: 0.18
Nodes (7): ask(), health(), AskIn, AskOut, ChunkOut, DocumentOut, HealthOut

### Community 8 - "Embeddings & docs"
Cohesion: 0.24
Nodes (8): embed_text(), embed_texts(), _get_client(), _fake_embed(), test_upload_and_list_documents(), test_upload_commit_failure_rolls_back(), test_upload_oversized_file_returns_413(), test_upload_unsupported_type()

### Community 9 - "Docker Compose app"
Cohesion: 0.18
Nodes (11): build, depends_on, environment, ports, condition, db, CHAT_MODEL, DATABASE_URL (+3 more)

## Knowledge Gaps
- **20 isolated node(s):** `GET /documents endpoint`, `Stage 6: pytest suite and GitHub Actions CI`, `Python`, `Docker Compose`, `GitHub Actions` (+15 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 83 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `extract_text()` connect `Text extraction` to `Core app & config`, `Documents & chunking`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `Document` (e.g. with `list_documents()` and `upload_document()`) actually correct?**
  _`Document` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `GET /documents endpoint`, `Stage 6: pytest suite and GitHub Actions CI`, `Python` to the rest of the system?**
  _20 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Core app & config` be split into smaller, more focused modules?**
  _Cohesion score 0.12043010752688173 - nodes in this community are weakly interconnected._
- **Why does `upload_document()` connect `Documents & chunking` to `Core app & config`, `Models & retrieval`, `Text extraction`, `Ask & health APIs`, `Embeddings & docs`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `Chunk` (e.g. with `list_documents()` and `upload_document()`) actually correct?**
  _`Chunk` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `Tech stack & rules` be split into smaller, more focused modules?**
  _Cohesion score 0.09230769230769231 - nodes in this community are weakly interconnected._