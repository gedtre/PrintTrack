from datetime import date
from ipaddress import ip_address
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(Input):
    username: str = Field(min_length=1, max_length=80)
    password: Annotated[str, StringConstraints(strip_whitespace=False)] = Field(
        min_length=1, max_length=200
    )


class UserCreate(Login):
    role: Literal["admin", "it", "viewer"]

    @field_validator("password")
    @classmethod
    def password_length(cls, value):
        if len(value) < 12:
            raise ValueError("PASSWORD_TOO_SHORT")
        return value


class UserUpdate(Input):
    role: Literal["admin", "it", "viewer"]
    active: bool


class Language(Input):
    language: Literal["lt", "en"]


class Named(Input):
    name: str = Field(min_length=1, max_length=160)


class RoomInput(Named):
    number: str = Field(min_length=1, max_length=40)
    floor: str = Field(default="1", min_length=1, max_length=40)
    building_id: int = Field(gt=0)
    department_id: int = Field(gt=0)


class ModelInput(Named):
    name: str = Field(min_length=1, max_length=120)
    manufacturer: str = Field(min_length=1, max_length=120)


class PrinterInput(Input):
    model_id: int = Field(gt=0)
    serial_number: str = Field(min_length=1, max_length=120)
    inventory_number: str = Field(min_length=1, max_length=120)
    ip_address: str | None = None
    room_id: int = Field(gt=0)
    status: Literal["active", "repair", "unused"] = "active"
    installation_date: date = Field(default_factory=date.today)
    notes: str = Field(default="", max_length=4000)
    archived: bool = False

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, value):
        return str(ip_address(value)) if value else None


class CartridgeInput(Input):
    code: str = Field(min_length=1, max_length=120)
    manufacturer: str = Field(min_length=1, max_length=120)
    kind: Literal["original", "compatible"] = "compatible"
    color: Literal["black", "cyan", "magenta", "yellow"] = "black"
    minimum_stock: int = Field(default=2, ge=0, le=1000000)
    description: str = Field(default="", max_length=4000)
    notes: str = Field(default="", max_length=4000)


class CompatibilityInput(Input):
    model_id: int = Field(gt=0)
    cartridge_id: int = Field(gt=0)
    verified: bool = False
    evidence: str = Field(default="", max_length=4000)


class TransactionInput(Input):
    cartridge_id: int = Field(gt=0)
    quantity: int = Field(strict=True, ge=-1000000, le=1000000)
    kind: Literal["receive", "issue", "return", "adjustment", "writeoff"]
    printer_id: int | None = Field(default=None, gt=0)
    notes: str = Field(default="", max_length=4000)
    document_reference: str = Field(default="", max_length=160)
    request_id: UUID


class Correction(Input):
    notes: str = Field(min_length=1, max_length=4000)
    request_id: UUID
