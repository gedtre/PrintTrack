import json
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession
from .auth import editor, fail
from .db import get_db
from .models import (
    AuditLog,
    Cartridge,
    Compatibility,
    Department,
    InventoryTransaction as Tx,
    Printer,
    Room,
    now,
)
from .schemas import Correction, TransactionInput

router = APIRouter(prefix="/api")


def balance(db, cartridge_id):
    return db.scalar(
        select(func.coalesce(func.sum(Tx.quantity), 0)).where(
            Tx.cartridge_id == cartridge_id
        )
    )


def row_json(obj):
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}


def existing_request(db, request_id, user_id):
    existing = db.scalar(select(Tx).where(Tx.request_id == str(request_id)))
    if existing and existing.user_id != user_id:
        fail("REQUEST_CONFLICT", 409)
    return existing


@router.post("/transactions", status_code=201)
def transact(
    data: TransactionInput, db: DBSession = Depends(get_db), user=Depends(editor)
):
    # Every balance mutation locks the stable parent row before calculating SUM.
    # Under PostgreSQL READ COMMITTED, each SUM sees preceding committed writes.
    cartridge = db.scalar(
        select(Cartridge).where(Cartridge.id == data.cartridge_id).with_for_update()
    )
    if not cartridge:
        fail("NOT_FOUND", 404)
    previous = existing_request(db, data.request_id, user.id)
    if previous:
        expected_quantity = (
            -data.quantity if data.kind in ("issue", "writeoff") else data.quantity
        )
        if (
            previous.cartridge_id,
            previous.kind,
            previous.quantity,
            previous.printer_id,
            previous.notes,
            previous.document_reference,
        ) != (
            data.cartridge_id,
            data.kind,
            expected_quantity,
            data.printer_id,
            data.notes,
            data.document_reference,
        ):
            fail("REQUEST_CONFLICT", 409)
        return row_json(previous)
    if data.quantity == 0 or (data.kind != "adjustment" and data.quantity < 0):
        fail("INVALID_INPUT", 422)
    if data.kind == "adjustment" and not data.notes:
        fail("REASON_REQUIRED", 422)
    quantity = -data.quantity if data.kind in ("issue", "writeoff") else data.quantity
    printer = None
    if data.printer_id:
        printer = db.scalar(
            select(Printer).where(Printer.id == data.printer_id).with_for_update()
        )
        if not printer or printer.archived:
            fail("NOT_FOUND", 404)
    if data.kind == "issue":
        if not printer:
            fail("PRINTER_REQUIRED", 422)
        if printer.status != "active":
            fail("PRINTER_INACTIVE", 409)
        compatible = db.scalar(
            select(Compatibility)
            .where(
                Compatibility.model_id == printer.model_id,
                Compatibility.cartridge_id == cartridge.id,
            )
            .with_for_update()
        )
        if not compatible or not compatible.verified:
            fail("UNVERIFIED_COMPATIBILITY", 409)
    if balance(db, cartridge.id) + quantity < 0:
        fail("INSUFFICIENT_STOCK", 409)
    room = db.get(Room, printer.room_id) if printer else None
    department = db.get(Department, room.department_id) if room else None
    tx = Tx(
        cartridge_id=cartridge.id,
        quantity=quantity,
        kind=data.kind,
        user_id=user.id,
        printer_id=printer.id if printer else None,
        room_id=room.id if room else None,
        department_id=department.id if department else None,
        cartridge_code=cartridge.code,
        printer_label=printer.inventory_number if printer else "",
        room_label=f"{room.number} · {room.name}" if room else "",
        department_label=department.name if department else "",
        user_label=user.username,
        notes=data.notes,
        document_reference=data.document_reference,
        request_id=str(data.request_id),
    )
    db.add(tx)
    db.flush()
    db.add(
        AuditLog(
            user_id=user.id,
            action="stock",
            entity="inventory_transactions",
            entity_id=tx.id,
            detail=json.dumps({"quantity": quantity}),
        )
    )
    db.commit()
    return row_json(tx)


@router.post("/transactions/{transaction_id}/reverse", status_code=201)
def reverse(
    transaction_id: int,
    data: Correction,
    db: DBSession = Depends(get_db),
    user=Depends(editor),
):
    original = db.get(Tx, transaction_id)
    if not original:
        fail("NOT_FOUND", 404)
    db.scalar(
        select(Cartridge).where(Cartridge.id == original.cartridge_id).with_for_update()
    )
    previous = existing_request(db, data.request_id, user.id)
    if previous:
        if previous.correction_of_id != original.id or previous.notes != data.notes:
            fail("REQUEST_CONFLICT", 409)
        return row_json(previous)
    if original.correction_of_id or db.scalar(
        select(Tx.id).where(Tx.correction_of_id == original.id)
    ):
        fail("ALREADY_REVERSED", 409)
    if balance(db, original.cartridge_id) - original.quantity < 0:
        fail("INSUFFICIENT_STOCK", 409)
    fields = {
        key: value
        for key, value in row_json(original).items()
        if key
        not in (
            "id",
            "occurred_at",
            "quantity",
            "kind",
            "user_id",
            "user_label",
            "notes",
            "request_id",
            "correction_of_id",
        )
    }
    tx = Tx(
        **fields,
        quantity=-original.quantity,
        kind="adjustment",
        user_id=user.id,
        user_label=user.username,
        notes=data.notes,
        request_id=str(data.request_id),
        correction_of_id=original.id,
        occurred_at=now(),
    )
    db.add(tx)
    db.flush()
    db.add(
        AuditLog(
            user_id=user.id,
            action="reverse",
            entity="inventory_transactions",
            entity_id=tx.id,
        )
    )
    db.commit()
    return row_json(tx)
