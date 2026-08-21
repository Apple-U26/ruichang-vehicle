from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordIn(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    manager_name: str | None = Field(default=None, max_length=50)
    manager_user_id: int | None = Field(default=None, gt=0)
    location: str | None = Field(default=None, max_length=200)
    remark: str | None = None


class ProjectUpdateIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    manager_name: str | None = Field(default=None, max_length=50)
    manager_user_id: int | None = Field(default=None, gt=0)
    location: str | None = Field(default=None, max_length=200)
    enabled: bool = True
    remark: str | None = None


class UserCreateIn(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    real_name: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    role: Literal[
        "ADMIN",
        "VEHICLE_MANAGER",
        "PROJECT_MANAGER",
        "FINANCE",
        "DRIVER",
    ] = "DRIVER"
    enabled: bool = True
    vehicle_id: int | None = Field(default=None, gt=0)


class UserUpdateIn(BaseModel):
    real_name: str = Field(min_length=1, max_length=50)
    role: Literal[
        "ADMIN",
        "VEHICLE_MANAGER",
        "PROJECT_MANAGER",
        "FINANCE",
        "DRIVER",
    ] = "DRIVER"
    enabled: bool = True
    password: str | None = Field(default=None, min_length=6, max_length=128)
    vehicle_id: int | None = Field(default=None, gt=0)


class VehicleIn(BaseModel):
    plate_no: str = Field(min_length=1, max_length=30)
    project_id: int | None = Field(default=None, gt=0)
    project_manager: str | None = Field(default=None, max_length=50)
    vehicle_manager: str | None = Field(default=None, max_length=50)
    appearance_url: str | None = Field(default=None, max_length=500)
    ownership: Literal["COMPANY", "RENTAL", "TEMPORARY", "OTHER"] = "COMPANY"
    initial_mileage: Decimal = Field(default=Decimal("0"), ge=0)
    status: Literal["ACTIVE", "MAINTENANCE", "DISABLED", "RETURNED"] = "ACTIVE"
    vehicle_age: int | None = Field(default=None, ge=0)
    violation_info: str | None = None
    remark: str | None = None


class MileageOutIn(BaseModel):
    vehicle_id: int = Field(gt=0)
    trip_date: datetime
    out_mileage: Decimal = Field(ge=0)
    driver_name: str | None = Field(default=None, max_length=50)
    departure: str | None = Field(default=None, max_length=100)
    destination: str | None = Field(default=None, max_length=100)
    purpose: str | None = Field(default=None, max_length=255)
    out_photo: str = Field(min_length=1, max_length=500)
    remark: str | None = None


class MileageCloseIn(BaseModel):
    in_mileage: Decimal = Field(ge=0)
    in_photo: str = Field(min_length=1, max_length=500)


class MaintenanceIn(BaseModel):
    vehicle_id: int = Field(gt=0)
    maintenance_date: date
    current_mileage: Decimal = Field(ge=0)
    maintenance_type: Literal[
        "MAINTENANCE",
        "REPAIR",
        "INSPECTION",
        "INSURANCE",
    ]
    items: str = Field(min_length=1)
    amount: Decimal = Field(ge=0)
    service_provider: str | None = Field(default=None, max_length=100)
    operator_name: str | None = Field(default=None, max_length=50)
    next_mileage: Decimal | None = Field(default=None, ge=0)
    next_date: date | None = None
    attachment_url: str = Field(min_length=1, max_length=500)
    remark: str | None = None


class ViolationIn(BaseModel):
    vehicle_id: int = Field(gt=0)
    violation_date: date
    violation_type: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=200)
    attachment_url: str = Field(min_length=1, max_length=500)
    points: int | None = Field(default=None, ge=0, le=12)
    fine_amount: Decimal = Field(default=Decimal("0"), ge=0)
    status: Literal["UNPROCESSED", "PROCESSED"] = "UNPROCESSED"
    handler_name: str | None = Field(default=None, max_length=50)
    remark: str | None = None


class FuelIn(BaseModel):
    vehicle_id: int = Field(gt=0)
    fuel_date: date
    liters: Decimal = Field(default=Decimal("0"), ge=0)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0)
    total_amount: Decimal = Field(default=Decimal("0"), ge=0)
    mileage: Decimal | None = Field(default=None, ge=0)
    station: str | None = Field(default=None, max_length=200)
    invoice_no: str | None = Field(default=None, max_length=100)
    attachment_url: str = Field(min_length=1, max_length=500)
    remark: str | None = None


class WelderIn(BaseModel):
    welder_code: str = Field(default="", max_length=30)
    welder_no: str = Field(min_length=1, max_length=50)
    location: str | None = Field(default=None, max_length=100)
    project_id: int | None = Field(default=None, gt=0)
    welder_manager: str | None = Field(default=None, max_length=50)
    status: Literal["ONLINE", "OFFLINE", "FAULT"] = "ONLINE"
    remark: str | None = None


class WelderInspectionIn(BaseModel):
    welder_id: int = Field(gt=0)
    location: str | None = Field(default=None, max_length=100)
    inspection_date: datetime
    inspection_type: Literal["MONTHLY", "WEEKLY", "DAILY"]
    completed: bool = False
    attachment_url: str | None = Field(default=None, max_length=500)
    operator_name: str | None = Field(default=None, max_length=50)
    device_status: Literal["NORMAL", "FAULT"]
    remark: str | None = None


class RepairIn(BaseModel):
    repair_note: str = Field(min_length=1, max_length=500)


class ReimbursementDetailIn(BaseModel):
    expense_type: Literal[
        "FUEL",
        "MAINTENANCE",
        "TOLL",
        "PARKING",
        "OTHER",
        "MILEAGE_ALLOWANCE",
    ]
    expense_date: date
    amount: Decimal = Field(default=Decimal("0"), ge=0)
    related_mileage: Decimal | None = Field(default=None, ge=0)
    invoice_no: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    attachment_url: str | None = Field(default=None, max_length=500)
    source_type: Literal["FUEL", "MAINTENANCE", "MILEAGE"] | None = None
    source_id: int | None = Field(default=None, gt=0)


class ReimbursementIn(BaseModel):
    reimbursement_month: str = Field(pattern=r"^\d{4}-\d{2}$")
    vehicle_id: int = Field(gt=0)
    project_id: int | None = Field(default=None, gt=0)
    remark: str | None = None
    details: list[ReimbursementDetailIn] = Field(min_length=1)

    @field_validator("reimbursement_month")
    @classmethod
    def validate_reimbursement_month(cls, value: str) -> str:
        year_text, month_text = value.split("-")
        year = int(year_text)
        month = int(month_text)

        if year < 2000 or month < 1 or month > 12:
            raise ValueError("报销月份必须是有效的 YYYY-MM")

        return value


class ApprovalIn(BaseModel):
    opinion: str | None = Field(default=None, max_length=500)


class RejectIn(BaseModel):
    reason: str = Field(min_length=2, max_length=500)


class BatchDeleteIn(BaseModel):
    ids: list[int] = Field(min_length=1)


class BatchApproveIn(BaseModel):
    ids: list[int] = Field(min_length=1)
    opinion: str | None = Field(default=None, max_length=500)
