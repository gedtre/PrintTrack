from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from app.main import app
from app.models import AuditLog, Department, Room


def payload(text, **kwargs):
    return {"csv_text": text, **kwargs}


VALID = "importuoti;numeris;pavadinimas;padalinys;pastatas;aukstas\ntaip;OCR-001;;OCR Skyrius;;\n"


def test_preview_requires_real_metadata_and_never_writes(logged_in, db):
    before = db.scalar(select(func.count()).select_from(Room))
    result = logged_in.post("/api/room-import/preview", json=payload(VALID)).json()
    assert not result["valid"]
    assert set(result["rows"][0]["issues"]) == {"BUILDING", "FLOOR"}
    assert db.scalar(select(func.count()).select_from(Room)) == before
    assert not db.scalar(select(Department.id).where(Department.name == "OCR Skyrius"))


def test_commit_is_atomic_repeatable_and_audited(logged_in, db):
    invalid = VALID + "taip;;Name;Must Not Be Created;;\n"
    options = {"default_building_id": 1, "default_floor": "2"}
    assert (
        logged_in.post(
            "/api/room-import/commit", json=payload(invalid, **options)
        ).status_code
        == 422
    )
    assert not db.scalar(
        select(Department.id).where(
            Department.name.in_(["OCR Skyrius", "Must Not Be Created"])
        )
    )
    result = logged_in.post(
        "/api/room-import/preview", json=payload(VALID, **options)
    ).json()
    assert result["valid"] and result["counts"]["ready"] == 1
    assert result["rows"][0]["name"] == "Kabinetas OCR-001"
    result = logged_in.post("/api/room-import/commit", json=payload(VALID, **options))
    assert result.status_code == 200 and result.json()["created"] == 1
    repeated = logged_in.post(
        "/api/room-import/commit", json=payload(VALID, **options)
    ).json()
    assert repeated == {"created": 0, "existing": 1, "skipped": 0}
    room = db.scalar(select(Room).where(Room.number == "OCR-001"))
    assert room.floor == "2"
    assert db.scalar(
        select(AuditLog.id).where(
            AuditLog.entity == "rooms",
            AuditLog.entity_id == room.id,
            AuditLog.action == "import",
        )
    )


def test_skips_unconfirmed_rows_and_preserves_number_variants(logged_in):
    text = "\ufeffimportuoti;numeris;pavadinimas;padalinys;pastatas;aukstas;tipas_saltinyje\nne;1;Registratūra;OCR;;;Registratūra\ntaip;001.;;OCR;;;Kabinetas\ntaip;001;;OCR;;;Kabinetas\ntaip;202(II lygis);;OCR;;;Kabinetas\n"
    data = payload(text, default_building_id=1, default_floor="Patikrintas aukštas")
    plan = logged_in.post("/api/room-import/preview", json=data).json()
    assert plan["counts"] == {"ready": 3, "existing": 0, "skipped": 1, "error": 0}
    assert plan["rows"][-1]["floor"] == "Patikrintas aukštas"
    assert logged_in.post("/api/room-import/commit", json=data).json()["created"] == 3
    numbers = [row["number"] for row in logged_in.get("/api/rooms").json()]
    assert "001." in numbers and "001" in numbers and "202(II lygis)" in numbers


def test_duplicate_numbers_block_import_and_existing_conflicts_are_not_overwritten(
    logged_in, db
):
    data = payload(
        VALID + "taip;OCR-001;Other;Other Department;;\n",
        default_building_id=1,
        default_floor="1",
    )
    plan = logged_in.post("/api/room-import/preview", json=data).json()
    assert plan["counts"]["error"] == 2
    assert all("DUPLICATE_NUMBER" in r["issues"] for r in plan["rows"])
    assert logged_in.post("/api/room-import/commit", json=data).status_code == 422
    valid = payload(VALID, default_building_id=1, default_floor="1")
    assert logged_in.post("/api/room-import/commit", json=valid).status_code == 200
    changed = payload(
        VALID.replace("OCR Skyrius", "Different Department"),
        default_building_id=1,
        default_floor="1",
    )
    assert logged_in.post("/api/room-import/commit", json=changed).status_code == 422
    assert not db.scalar(
        select(Department.id).where(Department.name == "Different Department")
    )


def test_explicit_building_and_floor_override_only_blank_cells(logged_in):
    other = logged_in.post("/api/buildings", json={"name": "OCR Building"}).json()
    text = "numeris,padalinys,pastatas,aukstas\nOCR-A,OCR,OCR Building,5\nOCR-A,OCR,,\n"
    plan = logged_in.post(
        "/api/room-import/preview",
        json=payload(text, default_building_id=1, default_floor="2"),
    ).json()
    assert plan["valid"]
    assert (
        plan["rows"][0]["building_id"] == other["id"]
        and plan["rows"][0]["floor"] == "5"
    )
    assert plan["rows"][1]["building_id"] == 1 and plan["rows"][1]["floor"] == "2"


def test_invalid_file_is_rejected_with_safe_codes(logged_in):
    for text in [
        "hello",
        "numeris;numeris;padalinys\n1;1;x",
        "numeris;padalinys;typo\n1;X;a",
        "numeris;padalinys\n1;x;extra",
        '"unclosed',
        "numeris;padalinys\n1;\ufffd",
        "numeris;padalinys\n1;\x00",
    ]:
        result = logged_in.post("/api/room-import/preview", json=payload(text))
        assert result.status_code == 422, (text, result.text)
        assert result.json()["detail"] == "IMPORT_FORMAT"
    assert (
        logged_in.post(
            "/api/room-import/preview", json=payload(VALID, default_building_id=999)
        ).json()["detail"]
        == "IMPORT_BUILDING"
    )
    too_many = "numeris;padalinys\n" + "".join(f"{i};OCR\n" for i in range(501))
    assert (
        logged_in.post("/api/room-import/preview", json=payload(too_many)).json()[
            "detail"
        ]
        == "IMPORT_LIMIT"
    )


def test_viewers_and_anonymous_cannot_import(logged_in):
    with TestClient(app) as anonymous:
        assert (
            anonymous.post("/api/room-import/preview", json=payload(VALID)).status_code
            == 401
        )
    logged_in.post(
        "/api/users",
        json={
            "username": "ocr-viewer",
            "password": "test-viewer-password",
            "role": "viewer",
        },
    )
    with TestClient(app) as viewer:
        assert (
            viewer.post(
                "/api/auth/login",
                json={"username": "ocr-viewer", "password": "test-viewer-password"},
            ).status_code
            == 200
        )
        for path in ["preview", "commit"]:
            assert (
                viewer.post(f"/api/room-import/{path}", json=payload(VALID)).status_code
                == 403
            )


def test_concurrent_repeated_import_creates_one_room(logged_in, db):
    cookies = dict(logged_in.cookies)

    def run(_):
        with TestClient(app) as client:
            client.cookies.update(cookies)
            response = client.post(
                "/api/room-import/commit",
                json=payload(VALID, default_building_id=1, default_floor="1"),
            )
            assert response.status_code == 200
            return response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, range(2)))
    assert sum(r["created"] for r in results) == 1
    assert (
        db.scalar(
            select(func.count()).select_from(Room).where(Room.number == "OCR-001")
        )
        == 1
    )
