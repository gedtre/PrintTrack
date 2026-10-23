import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from app.bootstrap import bootstrap
from app.db import Base, Session, engine
from app.main import app


@pytest.fixture(autouse=True)
def clean_database():
    # Destructive cleanup is deliberately restricted to a dedicated test database.
    if not make_url(str(engine.url)).database.endswith("_test"):
        raise RuntimeError("Tests require a database whose name ends in _test")
    with engine.begin() as connection:
        tables = ", ".join(f'"{table}"' for table in Base.metadata.tables)
        connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    bootstrap()
    yield


@pytest.fixture
def client():
    with TestClient(app, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def logged_in(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "local-test-only-password"},
    )
    assert response.status_code == 200, response.text
    return client


@pytest.fixture
def db():
    with Session() as session:
        yield session
