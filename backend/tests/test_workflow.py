from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from app.bootstrap import bootstrap
from app.config import settings
from app.main import app
from app.models import (
    AuditLog,
    Cartridge,
    Department,
    InventoryTransaction,
    Printer,
    Room,
)


def transaction(client, kind="receive", quantity=5, **kwargs):
    return client.post(
        "/api/transactions",
        json={
            "kind": kind,
            "quantity": quantity,
            "cartridge_id": 1,
            "request_id": str(uuid4()),
            **kwargs,
        },
    )


def verify(client):
    response = client.post(
        "/api/compatibility",
        json={
            "model_id": 1,
            "cartridge_id": 1,
            "verified": True,
            "evidence": "DEMO fictional test only",
        },
    )
    assert response.status_code == 200, response.text


def stock(client):
    return next(
        c["balance"] for c in client.get("/api/cartridges").json() if c["id"] == 1
    )


def test_end_to_end_persistence_and_reports(logged_in, db):
    client = logged_in
    assert stock(client) == 0
    assert transaction(client).status_code == 201
    denied = transaction(client, "issue", 1, printer_id=1)
    assert denied.status_code == 409
    assert denied.json()["detail"] == "UNVERIFIED_COMPATIBILITY"
    verify(client)
    response = transaction(client, "issue", 2, printer_id=1)
    assert response.status_code == 201, response.text
    assert stock(client) == 3
    history = client.get("/api/transactions?printer_id=1").json()
    assert len(history) == 1 and history[0]["quantity"] == -2
    assert history[0]["department_label"].startswith("DEMO")
    assert client.get("/api/dashboard").json()["issued"] == 2
    report = client.get("/api/reports?report=department&printer_id=1").json()
    assert sum(r["quantity"] for r in report["rows"]) == 2
    # A separate database connection sees the committed ledger.
    assert db.scalar(select(func.sum(InventoryTransaction.quantity))) == 3
    exported = client.get("/api/reports/export?language=lt")
    assert exported.status_code == 200
    assert exported.content.startswith(b"\xef\xbb\xbf")
    assert "Išdavimas" in exported.text
    assert "DEMO-T01" in exported.text
    assert client.get("/api/reports/export?language=en").text.count("Issue") == 1


def test_negative_inventory_and_validation(logged_in):
    verify(logged_in)
    assert (
        transaction(logged_in, "issue", 1, printer_id=1).json()["detail"]
        == "INSUFFICIENT_STOCK"
    )
    for kind, qty in [
        ("receive", 0),
        ("receive", -1),
        ("issue", -1),
        ("receive", 1.5),
        ("receive", True),
    ]:
        assert transaction(logged_in, kind, qty, printer_id=1).status_code == 422
    assert transaction(logged_in, "adjustment", 1).status_code == 422
    assert stock(logged_in) == 0


def test_returns_adjustments_writeoffs_and_compensation(logged_in):
    client = logged_in
    received = transaction(client, quantity=10).json()
    assert transaction(client, "return", 2).status_code == 201
    assert transaction(client, "writeoff", 3).status_code == 201
    assert (
        transaction(client, "adjustment", -1, notes="Count correction").status_code
        == 201
    )
    assert stock(client) == 8
    assert (
        client.post(
            f"/api/transactions/{received['id']}/reverse",
            json={"request_id": str(uuid4()), "notes": "Mistake"},
        ).status_code
        == 409
    )
    verify(client)
    issue = transaction(client, "issue", 1, printer_id=1).json()
    assert (
        client.post(
            f"/api/transactions/{issue['id']}/reverse",
            json={"request_id": str(uuid4()), "notes": "Wrong entry"},
        ).status_code
        == 201
    )
    assert stock(client) == 8
    assert client.get("/api/dashboard").json()["issued"] == 0
    assert client.get("/api/dashboard").json()["popular"][0]["quantity"] == 0
    assert (
        client.post(
            f"/api/transactions/{issue['id']}/reverse",
            json={"request_id": str(uuid4()), "notes": "Twice"},
        ).status_code
        == 409
    )


def test_concurrent_issues_never_go_negative(logged_in):
    verify(logged_in)
    transaction(logged_in, quantity=1)
    cookies = dict(logged_in.cookies)

    def issue(_):
        with TestClient(app) as client:
            client.cookies.update(cookies)
            return transaction(client, "issue", 1, printer_id=1).status_code

    with ThreadPoolExecutor(max_workers=6) as pool:
        outcomes = list(pool.map(issue, range(6)))
    assert outcomes.count(201) == 1
    assert outcomes.count(409) == 5
    assert stock(logged_in) == 0


def test_idempotency(logged_in):
    key = str(uuid4())
    first = transaction(logged_in, request_id=key)
    again = transaction(logged_in, request_id=key)
    assert first.json()["id"] == again.json()["id"]
    assert stock(logged_in) == 5
    assert transaction(logged_in, quantity=3, request_id=key).status_code == 409


def test_concurrent_receive_idempotency(logged_in):
    cookies = dict(logged_in.cookies)
    key = str(uuid4())

    def receive(_):
        with TestClient(app) as client:
            client.cookies.update(cookies)
            return transaction(client, request_id=key).json()["id"]

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert len(set(pool.map(receive, range(4)))) == 1
    assert stock(logged_in) == 5


def test_history_and_audit_cannot_be_changed(logged_in, db):
    transaction(logged_in)
    for statement in [
        "UPDATE inventory_transactions SET quantity=100",
        "DELETE FROM inventory_transactions",
        "DELETE FROM audit_logs",
    ]:
        with pytest.raises(DBAPIError):
            db.execute(text(statement))
            db.commit()
        db.rollback()
    assert stock(logged_in) == 5
    assert db.scalar(select(func.count()).select_from(AuditLog)) > 0


def test_reassignment_preserves_transaction_snapshot(logged_in):
    client = logged_in
    transaction(client)
    verify(client)
    original = transaction(client, "issue", 1, printer_id=1).json()
    printer = client.get("/api/printers").json()[0]
    printer["room_id"] = 2
    printer.pop("id")
    assert client.put("/api/printers/1", json=printer).status_code == 200
    assignments = client.get("/api/printers/1/history").json()
    assert assignments[0]["from_room_id"] == 1 and assignments[0]["to_room_id"] == 2
    history = client.get("/api/transactions?printer_id=1").json()
    assert history[0]["room_label"] == original["room_label"]
    archived = {**printer, "archived": True}
    assert client.put("/api/printers/1", json=archived).status_code == 200
    assert transaction(client, "issue", 1, printer_id=1).status_code == 404
    assert len(client.get("/api/transactions?printer_id=1").json()) == 1


def test_demo_seed_is_explicit_repeatable_and_zero_stock(logged_in, db, monkeypatch):
    bootstrap()
    assert db.scalar(select(func.count()).select_from(Department)) == 5
    assert db.scalar(select(func.count()).select_from(Room)) == 15
    assert db.scalar(select(func.count()).select_from(Printer)) == 20
    assert db.scalar(select(func.count()).select_from(Cartridge)) == 12
    assert db.scalar(select(func.count()).select_from(InventoryTransaction)) == 0
    assert all(not c["verified"] for c in logged_in.get("/api/compatibility").json())
    monkeypatch.setattr(settings, "demo_mode", False)
    with pytest.raises(RuntimeError, match="DEMO_MODE"):
        bootstrap()


def test_unauthorized_roles_and_revocation(client, logged_in):
    with TestClient(app) as anonymous:
        assert anonymous.get("/api/printers").status_code == 401
        assert transaction(anonymous).status_code == 401
    for role in ["viewer", "it"]:
        created = logged_in.post(
            "/api/users",
            json={"username": role, "password": "another-test-password", "role": role},
        )
        assert created.status_code == 201
        with TestClient(app) as reader:
            assert (
                reader.post(
                    "/api/auth/login",
                    json={"username": role, "password": "another-test-password"},
                ).status_code
                == 200
            )
            assert reader.get("/api/printers").status_code == 200
            assert (
                reader.post(
                    "/api/users",
                    json={
                        "username": "x",
                        "password": "another-test-password",
                        "role": "admin",
                    },
                ).status_code
                == 403
            )
            assert transaction(reader).status_code == (403 if role == "viewer" else 201)
            logged_in.put(
                f"/api/users/{created.json()['id']}",
                json={"role": role, "active": False},
            )
            assert reader.get("/api/printers").status_code == 401
    assert (
        logged_in.put(
            "/api/users/1", json={"role": "viewer", "active": True}
        ).status_code
        == 400
    )


def test_login_csrf_language_and_logout(client):
    assert (
        client.post(
            "/api/auth/login", json={"username": "admin", "password": "wrong"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "local-test-only-password"},
            headers={"Origin": "https://attacker.test"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "local-test-only-password"},
        ).status_code
        == 200
    )
    assert client.get("/api/auth/me").json()["language"] == "lt"
    cookie = client.cookies.get("printtrack_session")
    assert (
        client.patch("/api/auth/language", json={"language": "en"}).status_code == 200
    )
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401
    client.cookies.set("printtrack_session", cookie)
    assert client.get("/api/auth/me").status_code == 401
    client.cookies.clear()
    assert (
        client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "local-test-only-password"},
        ).json()["language"]
        == "en"
    )


def test_rate_limit_and_password_not_echoed(client):
    for _ in range(10):
        assert (
            client.post(
                "/api/auth/login", json={"username": "admin", "password": "wrong"}
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/auth/login", json={"username": "admin", "password": "wrong"}
        ).status_code
        == 429
    )
    response = client.post(
        "/api/auth/login", json={"username": "", "password": "secret-never-echo"}
    )
    assert response.status_code == 422 and "secret-never-echo" not in response.text


def test_filters_csv_injection_and_invalid_range(logged_in):
    assert transaction(logged_in, notes='=HYPERLINK("malicious")').status_code == 201
    assert "'=HYPERLINK" in logged_in.get("/api/reports/export").text
    assert (
        logged_in.get("/api/reports?start=2026-10-25&end=2026-10-01").status_code == 422
    )
    assert logged_in.get("/api/reports?report=stock&printer_id=1").status_code == 422
    assert logged_in.get("/api/reports?cartridge_id=999").json()["rows"] == []
    assert len(logged_in.get("/api/reports?report=low").json()["rows"]) == 11


def test_compatibility_validation_and_revocation(logged_in):
    client = logged_in
    assert (
        client.post(
            "/api/compatibility",
            json={"model_id": 1, "cartridge_id": 1, "verified": True},
        ).status_code
        == 422
    )
    verify(client)
    transaction(client)
    assert transaction(client, "issue", 1, printer_id=2).status_code == 409
    assert (
        client.post(
            "/api/compatibility",
            json={
                "model_id": 1,
                "cartridge_id": 1,
                "verified": False,
                "evidence": "Withdrawn",
            },
        ).status_code
        == 200
    )
    assert transaction(client, "issue", 1, printer_id=1).status_code == 409
    assert (
        client.post("/api/departments", json={"name": "New department"}).status_code
        == 201
    )
    assert (
        client.post("/api/departments", json={"name": "New department"}).status_code
        == 409
    )
    assert client.put("/api/printers/999", json={}).status_code == 422


def test_production_bootstrap_does_not_seed_demo(db, monkeypatch):
    from app.db import Base

    tables = ", ".join(f'"{table}"' for table in Base.metadata.tables)
    db.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    db.commit()
    monkeypatch.setattr(settings, "demo_mode", False)
    bootstrap()
    assert db.scalar(select(func.count()).select_from(Department)) == 0
    assert db.scalar(select(func.count()).select_from(Printer)) == 0
    assert db.scalar(select(func.count()).select_from(Cartridge)) == 0
    bootstrap()  # Restart does not duplicate or reset the administrator.
    from app.models import User

    assert db.scalar(select(func.count()).select_from(User)) == 1


def test_password_whitespace_is_preserved(logged_in):
    response = logged_in.post(
        "/api/users",
        json={
            "username": "space-user",
            "password": "  long-test-password  ",
            "role": "viewer",
        },
    )
    assert response.status_code == 201
    with TestClient(app) as client:
        assert (
            client.post(
                "/api/auth/login",
                json={"username": "space-user", "password": "long-test-password"},
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/auth/login",
                json={"username": "space-user", "password": "  long-test-password  "},
            ).status_code
            == 200
        )
