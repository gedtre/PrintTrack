import csv
import io
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession
from .auth import current_user, fail
from .db import get_db
from .inventory import row_json
from .models import (
    AuditLog,
    Cartridge,
    InventoryTransaction as Tx,
    Printer,
    Room,
    Department,
)

router = APIRouter(prefix="/api")
Report = Literal["history", "stock", "low", "monthly", "printer", "department"]


def boundary(day):
    return datetime.combine(day, time.min, ZoneInfo("Europe/Vilnius")).astimezone(
        timezone.utc
    )


def tx_query(
    start=None, end=None, department_id=None, printer_id=None, cartridge_id=None
):
    query = select(Tx)
    if start and end and start > end:
        fail("INVALID_INPUT", 422)
    if start:
        query = query.where(Tx.occurred_at >= boundary(start))
    if end:
        query = query.where(Tx.occurred_at < boundary(end + timedelta(days=1)))
    for field, value in [
        ("department_id", department_id),
        ("printer_id", printer_id),
        ("cartridge_id", cartridge_id),
    ]:
        if value:
            query = query.where(getattr(Tx, field) == value)
    return query


def stock_rows(db, cartridge_id=None):
    sums = (
        select(Tx.cartridge_id, func.sum(Tx.quantity).label("balance"))
        .group_by(Tx.cartridge_id)
        .subquery()
    )
    query = (
        select(Cartridge, func.coalesce(sums.c.balance, 0))
        .outerjoin(sums, Cartridge.id == sums.c.cartridge_id)
        .order_by(Cartridge.code)
    )
    if cartridge_id:
        query = query.where(Cartridge.id == cartridge_id)
    return [
        dict(id=c.id, code=c.code, balance=n, minimum_stock=c.minimum_stock)
        for c, n in db.execute(query)
    ]


def report_rows(db, report, start, end, department_id, printer_id, cartridge_id):
    if report in ("stock", "low"):
        # Current central stock has no department/printer/date attribution.
        if start or end or department_id or printer_id:
            fail("STOCK_FILTERS", 422)
        rows = stock_rows(db, cartridge_id)
        if report == "low":
            rows = [r for r in rows if r["balance"] <= r["minimum_stock"]]
        return ["code", "balance", "minimum_stock"], rows
    transactions = list(
        db.scalars(
            tx_query(start, end, department_id, printer_id, cartridge_id).order_by(
                Tx.occurred_at.desc(), Tx.id.desc()
            )
        )
    )
    if report == "history":
        return [
            "id",
            "occurred_at",
            "cartridge_code",
            "kind",
            "quantity",
            "user_label",
            "printer_label",
            "room_label",
            "department_label",
            "notes",
            "document_reference",
            "correction_of_id",
        ], [row_json(tx) for tx in transactions]
    # Compensating entries reverse consumption as well as balances.
    corrections = {
        t.correction_of_id: t
        for t in db.scalars(select(Tx).where(Tx.correction_of_id.is_not(None)))
    }
    result = {}
    for tx in transactions:
        if tx.kind != "issue":
            continue
        corrected = corrections.get(tx.id)
        # A report as-of an end date excludes later corrections.
        quantity = -tx.quantity
        if corrected and (
            not end or corrected.occurred_at < boundary(end + timedelta(days=1))
        ):
            quantity -= corrected.quantity
        if report == "monthly":
            label = tx.occurred_at.astimezone(ZoneInfo("Europe/Vilnius")).strftime(
                "%Y-%m"
            )
        elif report == "cartridge":
            label = tx.cartridge_code
        elif report == "printer":
            label = tx.printer_label
        else:
            label = tx.department_label
        result[label] = result.get(label, 0) + quantity
    return ["label", "quantity"], [
        dict(label=k, quantity=v) for k, v in sorted(result.items())
    ]


@router.get("/transactions")
def transactions(
    start: date | None = None,
    end: date | None = None,
    department_id: int | None = None,
    printer_id: int | None = None,
    cartridge_id: int | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: DBSession = Depends(get_db),
    user=Depends(current_user),
):
    return [
        row_json(tx)
        for tx in db.scalars(
            tx_query(start, end, department_id, printer_id, cartridge_id)
            .order_by(Tx.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ]


@router.get("/reports")
def reports(
    report: Report = "history",
    start: date | None = None,
    end: date | None = None,
    department_id: int | None = None,
    printer_id: int | None = None,
    cartridge_id: int | None = None,
    db: DBSession = Depends(get_db),
    user=Depends(current_user),
):
    columns, rows = report_rows(
        db, report, start, end, department_id, printer_id, cartridge_id
    )
    return {"columns": columns, "rows": rows}


CSV_HEADERS = {
    "lt": {
        "id": "ID",
        "occurred_at": "Data ir laikas",
        "cartridge_code": "Kasetė",
        "kind": "Operacija",
        "quantity": "Kiekis",
        "user_label": "Naudotojas",
        "printer_label": "Spausdintuvas",
        "room_label": "Kabinetas",
        "department_label": "Skyrius",
        "notes": "Pastabos",
        "document_reference": "Dokumentas",
        "correction_of_id": "Atšaukta operacija",
        "code": "Kasetė",
        "balance": "Likutis",
        "minimum_stock": "Minimalus likutis",
        "label": "Grupė",
    },
    "en": {
        "id": "ID",
        "occurred_at": "Date and time",
        "cartridge_code": "Cartridge",
        "kind": "Operation",
        "quantity": "Quantity",
        "user_label": "User",
        "printer_label": "Printer",
        "room_label": "Room",
        "department_label": "Department",
        "notes": "Notes",
        "document_reference": "Document",
        "correction_of_id": "Reversed transaction",
        "code": "Cartridge",
        "balance": "Balance",
        "minimum_stock": "Minimum stock",
        "label": "Group",
    },
}
KINDS = {
    "lt": dict(
        receive="Gavimas",
        issue="Išdavimas",
        return_="Grąžinimas",
        adjustment="Koregavimas",
        writeoff="Nurašymas",
    ),
    "en": dict(
        receive="Receive",
        issue="Issue",
        return_="Return",
        adjustment="Adjustment",
        writeoff="Write-off",
    ),
}


def safe_cell(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.astimezone(ZoneInfo("Europe/Vilnius")).isoformat()
    if isinstance(value, str) and value.lstrip().startswith(
        ("=", "+", "-", "@", "\t", "\r", "\n")
    ):
        return "'" + value
    return value


@router.get("/reports/export")
def export(
    report: Report = "history",
    start: date | None = None,
    end: date | None = None,
    department_id: int | None = None,
    printer_id: int | None = None,
    cartridge_id: int | None = None,
    language: Literal["lt", "en"] = "lt",
    db: DBSession = Depends(get_db),
    user=Depends(current_user),
):
    columns, rows = report_rows(
        db, report, start, end, department_id, printer_id, cartridge_id
    )
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=";")
    writer.writerow([CSV_HEADERS[language][c] for c in columns])
    for row in rows:
        row = dict(row)
        if "kind" in row:
            row["kind"] = KINDS[language].get(
                "return_" if row["kind"] == "return" else row["kind"]
            )
        writer.writerow([safe_cell(row.get(c)) for c in columns])
    return Response(
        "\ufeff" + stream.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="printtrack-{report}.csv"'
        },
    )


@router.get("/dashboard")
def dashboard(db: DBSession = Depends(get_db), user=Depends(current_user)):
    stock = stock_rows(db)
    month_start = datetime.now(ZoneInfo("Europe/Vilnius")).date().replace(day=1)
    _, monthly = report_rows(db, "monthly", None, None, None, None, None)
    _, popular = report_rows(db, "cartridge", None, None, None, None, None)
    _, departments = report_rows(db, "department", None, None, None, None, None)
    _, issued = report_rows(db, "monthly", month_start, None, None, None, None)
    return {
        "total": db.scalar(
            select(func.count()).select_from(Printer).where(~Printer.archived)
        ),
        "active": db.scalar(
            select(func.count())
            .select_from(Printer)
            .where(~Printer.archived, Printer.status == "active")
        ),
        "stock": sum(r["balance"] for r in stock),
        "types": len(stock),
        "low": len([r for r in stock if r["balance"] <= r["minimum_stock"]]),
        "issued": sum(r["quantity"] for r in issued),
        "monthly": monthly,
        "departments": departments,
        "low_stock": [r for r in stock if r["balance"] <= r["minimum_stock"]],
        "attention": [
            row_json(p)
            for p in db.scalars(
                select(Printer).where(~Printer.archived, Printer.status != "active")
            )
        ],
        "distribution": [
            dict(label=name, quantity=count)
            for name, count in db.execute(
                select(Department.name, func.count(Printer.id))
                .join(Room, Room.department_id == Department.id)
                .join(Printer, Printer.room_id == Room.id)
                .where(~Printer.archived)
                .group_by(Department.name)
            )
        ],
        "popular": sorted(popular, key=lambda item: item["quantity"], reverse=True)[
            :10
        ],
        "recent": [
            row_json(tx)
            for tx in db.scalars(select(Tx).order_by(Tx.id.desc()).limit(8))
        ],
    }


@router.get("/audit")
def audit(
    limit: int = Query(100, ge=1, le=1000),
    db: DBSession = Depends(get_db),
    user=Depends(current_user),
):
    return [
        row_json(obj)
        for obj in db.scalars(
            select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
        )
    ]
