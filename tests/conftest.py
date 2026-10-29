# fixtures, mocked providers
import os
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db, init_db
from app.main import app


# Prevent TestClient startup from connecting to a real DB in tests.
@pytest.fixture(autouse=True)
def _noop_init_db(monkeypatch):
    monkeypatch.setattr("app.db.init_db", lambda: None)


# --- no-DB client (for router/service tests that mock providers) ---
def _mock_db():
    yield MagicMock()


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = _mock_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# --- real DB-backed session (for ingestion/end-to-end tests) ---
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/groundedqa_test",
)


@pytest.fixture
def db_session():
    try:
        engine_test = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
        # Only connection failures are skippable; schema bugs must surface.
        with engine_test.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    except OperationalError:
        pytest.skip(f"Test database not available at {TEST_DATABASE_URL}")

    # Reset the schema each test so stale tables/indexes can't mask bugs.
    Base.metadata.drop_all(bind=engine_test)
    Base.metadata.create_all(bind=engine_test)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)
    connection = engine_test.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)

    def override():
        yield session

    app.dependency_overrides[get_db] = override
    try:
        yield session
    finally:
        app.dependency_overrides.clear()
        session.close()
        transaction.rollback()
        connection.close()
        engine_test.dispose()
