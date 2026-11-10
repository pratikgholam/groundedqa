# DB connection/session setup
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Ensure pgvector extension and tables exist (idempotent).

    Also validates that the configured EMBEDDING_DIM matches the actual
    chunks.embedding column dimension in the database. Raises RuntimeError
    with a clear message when they differ, so the mismatch is caught at
    startup instead of failing on first ingestion.
    """
    with engine.begin() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception as exc:
            raise RuntimeError(
                "pgvector extension is required but could not be created. "
                "Ensure the database user has privileges to create extensions "
                "(typically superuser) and that pgvector is installed."
            ) from exc

    Base.metadata.create_all(bind=engine)

    _validate_embedding_dimension()


def _validate_embedding_dimension() -> None:
    """Ensure the chunks.embedding column dimension matches EMBEDDING_DIM.

    db/init.sql now creates the column unconstrained (`embedding vector`)
    so the dimension is derived from the EMBEDDING_DIM setting. On first
    startup we set the column to vector(EMBEDDING_DIM). On later startups we
    verify the existing dimension still matches and fail fast if it does not.
    """
    expected_dim = settings.EMBEDDING_DIM
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT atttypmod FROM pg_attribute "
                "WHERE attrelid = 'chunks'::regclass AND attname = 'embedding'"
            )
        ).first()
    if row is None:
        raise RuntimeError(
            "could not read chunks.embedding dimension from the database; "
            "make sure the chunks table exists before starting the app"
        )
    actual_dim = row[0]
    if actual_dim == -1:
        # Unconstrained column: set it to the configured dimension.
        with engine.begin() as conn:
            conn.execute(
                text(
                    f"ALTER TABLE chunks ALTER COLUMN embedding "
                    f"TYPE vector({expected_dim})"
                )
            )
        return
    if actual_dim != expected_dim:
        raise RuntimeError(
            f"embedding dimension mismatch: EMBEDDING_DIM={expected_dim} but "
            f"database stores chunks.embedding as vector({actual_dim}); "
            "reconcile EMBEDDING_DIM with the database schema before starting"
        )
