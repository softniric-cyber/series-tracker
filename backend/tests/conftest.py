"""Fixtures de test. Las pruebas de integración usan Postgres (docker-compose en
local, servicio `postgres` en CI). Se recrea el esquema en cada test para aislarlos.
"""

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401  — puebla Base.metadata
from app.core.db import Base, get_db
from app.main import app

TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://series:series@localhost:5432/series_tracker"
)

_engine = create_engine(TEST_DATABASE_URL)
_TestingSession = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    Base.metadata.drop_all(_engine)
    Base.metadata.create_all(_engine)
    session = _TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(_engine)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    Base.metadata.drop_all(_engine)
    Base.metadata.create_all(_engine)

    def _override_get_db() -> Generator[Session, None, None]:
        session = _TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(_engine)
