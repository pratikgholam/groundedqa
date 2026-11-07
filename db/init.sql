-- Run once when the db container first starts.
-- pgvector extension + the documents/chunks tables.
-- The app also calls Base.metadata.create_all on startup as a safety net
-- (idempotent; it won't recreate existing tables).

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding vector(1536)
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
