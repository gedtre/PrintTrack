import json
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from .auth import current_user, editor, fail
from .db import get_db
from .inventory import balance, row_json
from .models import (
    Assignment,
    AuditLog,
    Building,
    Cartridge,
    Compatibility,
    Department,
    Printer,
    PrinterModel,
    Room,
    now,
)
from .schemas import (
    CartridgeInput,
    CompatibilityInput,
    ModelInput,
    Named,
    PrinterInput,
    RoomInput,
)

router = APIRouter(prefix="/api")
CATALOG = {
    "departments": (Department, Named),
    "buildings": (Building, Named),
    "rooms": (Room, RoomInput),
    "models": (PrinterModel, ModelInput),
    "printers": (Printer, PrinterInput),
    "cartridges": (Cartridge, CartridgeInput),
}


def require(db, model, identifier):
    obj = db.get(model, identifier)
    if not obj:
        fail("NOT_FOUND", 404)
    return obj


def validate_links(db, resource, data):
    if resource == "rooms":
        require(db, Building, data.building_id)
        require(db, Department, data.department_id)
    if resource == "printers":
        require(db, PrinterModel, data.model_id)
        require(db, Room, data.room_id)


def room_label(db, identifier):
    if identifier is None:
        return ""
    room = require(db, Room, identifier)
    return f"{room.number} · {room.name}"


def register(resource, model, schema):
    def list_items(db: DBSession = Depends(get_db), user=Depends(current_user)):
        items = [row_json(obj) for obj in db.scalars(select(model).order_by(model.id))]
        if resource == "cartridges":
            for item in items:
                item["balance"] = balance(db, item["id"])
        return items

    def save(data, db, user, identifier=None):
        validate_links(db, resource, data)
        obj = (
            db.scalar(select(model).where(model.id == identifier).with_for_update())
            if identifier
            else model()
        )
        if obj is None:
            fail("NOT_FOUND", 404)
        before = row_json(obj) if identifier else {}
        old_room = obj.room_id if resource == "printers" and identifier else None
        for key, value in data.model_dump().items():
            setattr(obj, key, value)
        db.add(obj)
        db.flush()
        if resource == "printers" and (not identifier or old_room != obj.room_id):
            db.add(
                Assignment(
                    printer_id=obj.id,
                    from_room_id=old_room,
                    to_room_id=obj.room_id,
                    from_label=room_label(db, old_room),
                    to_label=room_label(db, obj.room_id),
                    user_id=user.id,
                )
            )
        db.add(
            AuditLog(
                user_id=user.id,
                action="update" if identifier else "create",
                entity=resource,
                entity_id=obj.id,
                detail=json.dumps(
                    {"before": before, "after": row_json(obj)},
                    default=str,
                    ensure_ascii=False,
                ),
            )
        )
        db.commit()
        return row_json(obj)

    def create(data, db: DBSession = Depends(get_db), user=Depends(editor)):
        return save(data, db, user)

    def update(
        identifier: int, data, db: DBSession = Depends(get_db), user=Depends(editor)
    ):
        return save(data, db, user, identifier)

    create.__annotations__["data"] = schema
    update.__annotations__["data"] = schema
    router.add_api_route(
        f"/{resource}", list_items, methods=["GET"], name=f"list_{resource}"
    )
    router.add_api_route(
        f"/{resource}",
        create,
        methods=["POST"],
        status_code=201,
        name=f"create_{resource}",
    )
    router.add_api_route(
        f"/{resource}/{{identifier}}",
        update,
        methods=["PUT"],
        name=f"update_{resource}",
    )


for resource, (model, schema) in CATALOG.items():
    register(resource, model, schema)


@router.get("/compatibility")
def compatibility(db: DBSession = Depends(get_db), user=Depends(current_user)):
    return [
        row_json(obj)
        for obj in db.scalars(select(Compatibility).order_by(Compatibility.id))
    ]


@router.post("/compatibility")
def set_compatibility(
    data: CompatibilityInput, db: DBSession = Depends(get_db), user=Depends(editor)
):
    # Same cartridge lock as issue/reverse serializes verification changes with issuing.
    db.scalar(
        select(Cartridge).where(Cartridge.id == data.cartridge_id).with_for_update()
    )
    require(db, Cartridge, data.cartridge_id)
    require(db, PrinterModel, data.model_id)
    if data.verified and not data.evidence:
        fail("REASON_REQUIRED", 422)
    obj = db.scalar(
        select(Compatibility).where(
            Compatibility.model_id == data.model_id,
            Compatibility.cartridge_id == data.cartridge_id,
        )
    )
    if not obj:
        obj = Compatibility(model_id=data.model_id, cartridge_id=data.cartridge_id)
        db.add(obj)
    obj.verified = data.verified
    obj.verified_by = user.id if data.verified else None
    obj.verified_at = now() if data.verified else None
    obj.evidence = data.evidence
    db.flush()
    db.add(
        AuditLog(
            user_id=user.id,
            action="verify" if data.verified else "unverify",
            entity="compatibility",
            entity_id=obj.id,
            detail=data.evidence,
        )
    )
    db.commit()
    return row_json(obj)


@router.get("/printers/{printer_id}/history")
def printer_history(
    printer_id: int, db: DBSession = Depends(get_db), user=Depends(current_user)
):
    require(db, Printer, printer_id)
    return [
        row_json(obj)
        for obj in db.scalars(
            select(Assignment)
            .where(Assignment.printer_id == printer_id)
            .order_by(Assignment.id.desc())
        )
    ]
