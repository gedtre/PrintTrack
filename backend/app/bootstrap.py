"""Explicit instance initialization. Does not reset inventory or passwords."""

from sqlalchemy import select, text
from .auth import passwords
from .config import settings
from .db import Session
from .models import (
    Building,
    Cartridge,
    Compatibility,
    Department,
    InstanceState,
    Printer,
    PrinterModel,
    Room,
    User,
)


def bootstrap():
    with Session() as db:
        # Serializes initialization if multiple app instances start together.
        db.execute(text("SELECT pg_advisory_xact_lock(74512019)"))
        state = db.get(InstanceState, 1)
        if state and state.demo != settings.demo_mode:
            raise RuntimeError(
                "DEMO_MODE cannot change for an existing database. Use a separate database/volume."
            )
        if not state:
            db.add(InstanceState(id=1, demo=settings.demo_mode))
        if not db.scalar(select(User.id).limit(1)):
            if len(settings.admin_password) < 12:
                raise RuntimeError(
                    "ADMIN_PASSWORD must contain at least 12 characters."
                )
            db.add(
                User(
                    username=settings.admin_username,
                    password_hash=passwords.hash(settings.admin_password),
                    role="admin",
                )
            )
        if settings.demo_mode and not db.scalar(select(Department.id).limit(1)):
            building = Building(name="DEMO · Fiktyvus korpusas")
            departments = [Department(name=f"DEMO · Skyrius {i + 1}") for i in range(5)]
            db.add_all([building, *departments])
            db.flush()
            rooms = [
                Room(
                    name=f"DEMO · Kabinetas {i + 1}",
                    number=f"D{i + 101}",
                    floor=str(i // 5 + 1),
                    building_id=building.id,
                    department_id=departments[i % 5].id,
                )
                for i in range(15)
            ]
            models = [
                PrinterModel(manufacturer="DEMO Fictional", name=f"PT-DEMO-{i + 1}")
                for i in range(4)
            ]
            cartridges = [
                Cartridge(
                    code=f"DEMO-T{i + 1:02}",
                    manufacturer="DEMO Fictional",
                    color=["black", "cyan", "magenta", "yellow"][i % 4],
                    minimum_stock=2,
                    description="DEMO · Fiktyvi kasetė, ne realus gaminys",
                )
                for i in range(12)
            ]
            db.add_all([*rooms, *models, *cartridges])
            db.flush()
            db.add_all(
                [
                    Printer(
                        model_id=models[i % 4].id,
                        serial_number=f"DEMO-S{i + 1:03}",
                        inventory_number=f"DEMO-P{i + 1:03}",
                        room_id=rooms[i % 15].id,
                        notes="DEMO · Fiktyvus spausdintuvas",
                    )
                    for i in range(20)
                ]
            )
            db.add_all(
                [
                    Compatibility(
                        model_id=models[i % 4].id,
                        cartridge_id=c.id,
                        verified=False,
                        evidence="DEMO · Fiktyvus ryšys. Reikia patvirtinti demonstravimo metu.",
                    )
                    for i, c in enumerate(cartridges)
                ]
            )
        db.commit()


if __name__ == "__main__":
    bootstrap()
