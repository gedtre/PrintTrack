from datetime import date, datetime, timezone
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20))
    language: Mapped[str] = mapped_column(String(2), default="lt")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (
        CheckConstraint("role IN ('admin','it','viewer')"),
        CheckConstraint("language IN ('lt','en')"),
    )


class SessionToken(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    expires: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)


class Building(Base):
    __tablename__ = "buildings"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)


class Room(Base):
    __tablename__ = "rooms"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    number: Mapped[str] = mapped_column(String(40))
    floor: Mapped[str] = mapped_column(String(40), default="1")
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"), index=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    __table_args__ = (UniqueConstraint("building_id", "number"),)


class PrinterModel(Base):
    __tablename__ = "printer_models"
    id: Mapped[int] = mapped_column(primary_key=True)
    manufacturer: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(120))
    __table_args__ = (UniqueConstraint("manufacturer", "name"),)


class Printer(Base):
    __tablename__ = "printers"
    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("printer_models.id"), index=True)
    serial_number: Mapped[str] = mapped_column(String(120), unique=True)
    inventory_number: Mapped[str] = mapped_column(String(120), unique=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    installation_date: Mapped[date] = mapped_column(Date, default=date.today)
    notes: Mapped[str] = mapped_column(Text, default="")
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (CheckConstraint("status IN ('active','repair','unused')"),)


class Cartridge(Base):
    __tablename__ = "toner_cartridges"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(120), unique=True)
    manufacturer: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(20), default="compatible")
    color: Mapped[str] = mapped_column(String(20), default="black")
    description: Mapped[str] = mapped_column(Text, default="")
    minimum_stock: Mapped[int] = mapped_column(Integer, default=2)
    notes: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (
        CheckConstraint("minimum_stock >= 0"),
        CheckConstraint("kind IN ('original','compatible')"),
        CheckConstraint("color IN ('black','cyan','magenta','yellow')"),
    )


class Compatibility(Base):
    __tablename__ = "printer_toner_compatibility"
    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("printer_models.id"), index=True)
    cartridge_id: Mapped[int] = mapped_column(
        ForeignKey("toner_cartridges.id"), index=True
    )
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (UniqueConstraint("model_id", "cartridge_id"),)


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, index=True
    )
    cartridge_id: Mapped[int] = mapped_column(
        ForeignKey("toner_cartridges.id"), index=True
    )
    quantity: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(20))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    printer_id: Mapped[int | None] = mapped_column(
        ForeignKey("printers.id"), index=True
    )
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"))
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id"), index=True
    )
    cartridge_code: Mapped[str] = mapped_column(String(120))
    printer_label: Mapped[str] = mapped_column(String(260), default="")
    room_label: Mapped[str] = mapped_column(String(220), default="")
    department_label: Mapped[str] = mapped_column(String(160), default="")
    user_label: Mapped[str] = mapped_column(String(80))
    notes: Mapped[str] = mapped_column(Text, default="")
    document_reference: Mapped[str] = mapped_column(String(160), default="")
    correction_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("inventory_transactions.id"), unique=True
    )
    request_id: Mapped[str] = mapped_column(String(36), unique=True)
    __table_args__ = (
        CheckConstraint(
            "(kind IN ('receive','return') AND quantity > 0) OR (kind IN ('issue','writeoff') AND quantity < 0) OR (kind = 'adjustment' AND quantity <> 0)"
        ),
    )


class Assignment(Base):
    __tablename__ = "printer_assignment_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    printer_id: Mapped[int] = mapped_column(ForeignKey("printers.id"), index=True)
    from_room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"))
    to_room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    from_label: Mapped[str] = mapped_column(String(220), default="")
    to_label: Mapped[str] = mapped_column(String(220))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80))
    entity: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[int] = mapped_column(Integer)
    detail: Mapped[str] = mapped_column(Text, default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class InstanceState(Base):
    __tablename__ = "instance_state"
    id: Mapped[int] = mapped_column(primary_key=True)
    demo: Mapped[bool] = mapped_column(Boolean)
