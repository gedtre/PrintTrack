"""Preview-first, atomic room CSV import. Never guesses building or floor."""

import csv
import io
from collections import Counter
from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session as DBSession
from .auth import editor, fail
from .db import get_db
from .models import AuditLog, Building, Department, Room
from .schemas import Input

router = APIRouter(prefix="/api/room-import")
HEADERS = {
    "importuoti",
    "numeris",
    "pavadinimas",
    "padalinys",
    "pastatas",
    "aukstas",
    "tipas_saltinyje",
    "vieta_nuo",
    "saltinis",
    "pastaba",
}


class ImportInput(Input):
    csv_text: str = Field(min_length=1, max_length=1000000)
    default_building_id: int | None = Field(default=None, gt=0)
    default_floor: str = Field(default="", max_length=40)


def plan_import(data, db):
    source = data.csv_text.lstrip("\ufeff")
    if "\ufffd" in source or "\x00" in source:
        fail("IMPORT_FORMAT", 422)
    header = source.splitlines()[0] if source.splitlines() else ""
    delimiter = ";" if header.count(";") >= header.count(",") else ","
    reader = csv.DictReader(
        io.StringIO(source, newline=""), delimiter=delimiter, strict=True
    )
    try:
        fields = reader.fieldnames
    except csv.Error:
        fail("IMPORT_FORMAT", 422)
    if (
        not fields
        or len(set(fields)) != len(fields)
        or not {"numeris", "padalinys"}.issubset(fields)
        or not set(fields).issubset(HEADERS)
    ):
        fail("IMPORT_FORMAT", 422)
    buildings = {b.name: b for b in db.scalars(select(Building))}
    default_building = next(
        (b for b in buildings.values() if b.id == data.default_building_id), None
    )
    if data.default_building_id and not default_building:
        fail("IMPORT_BUILDING", 422)
    departments = {d.id: d.name for d in db.scalars(select(Department))}
    existing = {(r.building_id, r.number): r for r in db.scalars(select(Room))}
    rows = []
    try:
        for index, record in enumerate(reader, 2):
            if len(rows) >= 500:
                fail("IMPORT_LIMIT", 422)
            if None in record or any(value is None for value in record.values()):
                fail("IMPORT_FORMAT", 422)
            record = {key: value.strip() for key, value in record.items()}
            number = record.get("numeris", "")
            name = record.get("pavadinimas", "") or (
                f"Kabinetas {number}" if number else ""
            )
            building_name = record.get("pastatas", "")
            building = (
                buildings.get(building_name) if building_name else default_building
            )
            row = {
                "line": index,
                "number": number,
                "name": name,
                "department": record.get("padalinys", ""),
                "building": building.name if building else building_name,
                "building_id": building.id if building else None,
                "floor": record.get("aukstas", "") or data.default_floor,
                "source": record.get("saltinis", ""),
                "status": "ready",
                "issues": [],
            }
            flag = record.get("importuoti", "taip").casefold()
            if flag in ("ne", "no", "0"):
                row["status"] = "skipped"
                rows.append(row)
                continue
            if flag not in ("taip", "yes", "1"):
                row["issues"].append("FLAG")
            for key, code in [
                ("number", "NUMBER"),
                ("department", "DEPARTMENT"),
                ("building", "BUILDING"),
                ("floor", "FLOOR"),
            ]:
                if not row[key]:
                    row["issues"].append(code)
            if building_name and not building:
                row["issues"].append("UNKNOWN_BUILDING")
            if (
                len(number) > 40
                or len(name) > 160
                or len(row["department"]) > 160
                or len(row["floor"]) > 40
            ):
                row["issues"].append("LENGTH")
            rows.append(row)
    except csv.Error:
        fail("IMPORT_FORMAT", 422)
    if not rows:
        fail("IMPORT_FORMAT", 422)
    identities = Counter(
        (r["building_id"], r["number"])
        for r in rows
        if r["status"] != "skipped" and r["building_id"] and r["number"]
    )
    for row in rows:
        if row["status"] == "skipped":
            continue
        key = (row["building_id"], row["number"])
        if identities[key] > 1:
            row["issues"].append("DUPLICATE_NUMBER")
        prior = existing.get(key)
        if prior:
            if (prior.name, departments[prior.department_id], prior.floor) == (
                row["name"],
                row["department"],
                row["floor"],
            ):
                row["status"] = "existing"
            else:
                row["issues"].append("EXISTING_CONFLICT")
        if row["issues"]:
            row["status"] = "error"
    counts = {
        status: sum(r["status"] == status for r in rows)
        for status in ("ready", "existing", "skipped", "error")
    }
    new_departments = sorted(
        {r["department"] for r in rows if r["status"] == "ready"}
        - set(departments.values())
    )
    return {
        "rows": rows,
        "counts": counts,
        "valid": counts["error"] == 0,
        "new_departments": new_departments,
    }


@router.post("/preview")
def preview(data: ImportInput, db: DBSession = Depends(get_db), user=Depends(editor)):
    return plan_import(data, db)


@router.post("/commit")
def commit(data: ImportInput, db: DBSession = Depends(get_db), user=Depends(editor)):
    # Serializes concurrent imports; normal catalog writes remain protected by unique constraints.
    db.execute(text("SELECT pg_advisory_xact_lock(74512020)"))
    plan = plan_import(data, db)
    if not plan["valid"]:
        fail("IMPORT_INVALID", 422)
    departments = {d.name: d for d in db.scalars(select(Department))}
    for name in plan["new_departments"]:
        department = Department(name=name)
        db.add(department)
        db.flush()
        departments[name] = department
        db.add(
            AuditLog(
                user_id=user.id,
                action="import",
                entity="departments",
                entity_id=department.id,
            )
        )
    for row in plan["rows"]:
        if row["status"] != "ready":
            continue
        room = Room(
            number=row["number"],
            name=row["name"],
            building_id=row["building_id"],
            floor=row["floor"],
            department_id=departments[row["department"]].id,
        )
        db.add(room)
        db.flush()
        db.add(
            AuditLog(
                user_id=user.id,
                action="import",
                entity="rooms",
                entity_id=room.id,
                detail=f"CSV line {row['line']}; source: {row['source']}",
            )
        )
    db.commit()
    return {
        "created": plan["counts"]["ready"],
        "existing": plan["counts"]["existing"],
        "skipped": plan["counts"]["skipped"],
    }
