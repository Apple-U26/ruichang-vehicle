from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    String,
    Integer,
    Date,
    DateTime,
    Numeric,
    ForeignKey,
    Text,
    Boolean
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "sys_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    real_name: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # ADMIN、VEHICLE_MANAGER、PROJECT_MANAGER、FINANCE、DRIVER
    role: Mapped[str] = mapped_column(String(30), default="DRIVER")

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now
    )

    vehicle_id: Mapped[int | None] = mapped_column(
        ForeignKey("vehicle_info.id"), index=True
    )

    vehicle: Mapped["Vehicle | None"] = relationship(
        back_populates="accounts"
    )


class Project(Base):
    __tablename__ = "project_info"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    manager_name: Mapped[str | None] = mapped_column(String(50))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    remark: Mapped[str | None] = mapped_column(Text)

    vehicles: Mapped[list["Vehicle"]] = relationship(
        back_populates="project"
    )


class Vehicle(Base):
    __tablename__ = "vehicle_info"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_code: Mapped[str] = mapped_column(
        String(30), unique=True, index=True
    )
    plate_no: Mapped[str] = mapped_column(
        String(30), unique=True, index=True, nullable=False
    )

    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("project_info.id")
    )

    project_manager: Mapped[str | None] = mapped_column(String(50))
    vehicle_manager: Mapped[str | None] = mapped_column(String(50))

    # COMPANY、RENTAL、TEMPORARY、OTHER
    ownership: Mapped[str] = mapped_column(String(30), default="COMPANY")

    initial_mileage: Mapped[Decimal] = mapped_column(
        Numeric(12, 1), default=0
    )
    current_mileage: Mapped[Decimal] = mapped_column(
        Numeric(12, 1), default=0
    )

    # ACTIVE、MAINTENANCE、DISABLED、RETURNED
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")

    vehicle_age: Mapped[int | None] = mapped_column(Integer)
    violation_info: Mapped[str | None] = mapped_column(Text)
    appearance_url: Mapped[str | None] = mapped_column(String(500))
    remark: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    project: Mapped["Project | None"] = relationship(
        back_populates="vehicles"
    )
    mileages: Mapped[list["MileageRecord"]] = relationship(
        back_populates="vehicle"
    )
    maintenances: Mapped[list["MaintenanceRecord"]] = relationship(
        back_populates="vehicle"
    )
    reimbursements: Mapped[list["Reimbursement"]] = relationship(
        back_populates="vehicle"
    )
    violations: Mapped[list["ViolationRecord"]] = relationship(
        back_populates="vehicle",
        cascade="all, delete-orphan",
    )
    fuels: Mapped[list["FuelRecord"]] = relationship(
        back_populates="vehicle",
        cascade="all, delete-orphan",
    )
    accounts: Mapped[list["User"]] = relationship(
        back_populates="vehicle"
    )


class MileageRecord(Base):
    __tablename__ = "vehicle_mileage"

    id: Mapped[int] = mapped_column(primary_key=True)

    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicle_info.id"), index=True
    )
    trip_date: Mapped[date] = mapped_column(Date, index=True)

    out_mileage: Mapped[Decimal] = mapped_column(Numeric(12, 1))
    in_mileage: Mapped[Decimal | None] = mapped_column(Numeric(12, 1))
    distance: Mapped[Decimal] = mapped_column(Numeric(12, 1), default=0)

    driver_name: Mapped[str | None] = mapped_column(String(50))
    departure: Mapped[str | None] = mapped_column(String(100))
    destination: Mapped[str | None] = mapped_column(String(100))
    purpose: Mapped[str | None] = mapped_column(String(255))

    out_photo: Mapped[str | None] = mapped_column(String(500))
    in_photo: Mapped[str | None] = mapped_column(String(500))

    # OUT、CLOSED
    status: Mapped[str] = mapped_column(String(20), default="OUT")

    abnormal: Mapped[bool] = mapped_column(Boolean, default=False)
    abnormal_reason: Mapped[str | None] = mapped_column(String(255))
    remark: Mapped[str | None] = mapped_column(Text)

    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("sys_user.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now
    )

    vehicle: Mapped["Vehicle"] = relationship(
        back_populates="mileages"
    )


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_record"

    id: Mapped[int] = mapped_column(primary_key=True)

    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicle_info.id"), index=True
    )
    maintenance_date: Mapped[date] = mapped_column(Date, index=True)
    current_mileage: Mapped[Decimal] = mapped_column(Numeric(12, 1))

    # MAINTENANCE、REPAIR、INSPECTION、INSURANCE
    maintenance_type: Mapped[str] = mapped_column(String(30))

    items: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    service_provider: Mapped[str | None] = mapped_column(String(100))
    operator_name: Mapped[str | None] = mapped_column(String(50))

    next_mileage: Mapped[Decimal | None] = mapped_column(Numeric(12, 1))
    next_date: Mapped[date | None] = mapped_column(Date)

    attachment_url: Mapped[str | None] = mapped_column(String(500))
    remark: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now
    )

    vehicle: Mapped["Vehicle"] = relationship(
        back_populates="maintenances"
    )


class ViolationRecord(Base):
    __tablename__ = "violation_record"

    id: Mapped[int] = mapped_column(primary_key=True)

    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicle_info.id"), index=True
    )
    violation_date: Mapped[date] = mapped_column(Date, index=True)
    violation_type: Mapped[str | None] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(200))
    attachment_url: Mapped[str | None] = mapped_column(String(500))
    points: Mapped[int | None] = mapped_column(Integer)
    fine_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=0
    )

    # UNPROCESSED、PROCESSED
    status: Mapped[str] = mapped_column(
        String(30), default="UNPROCESSED"
    )
    handler_name: Mapped[str | None] = mapped_column(String(50))
    remark: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now
    )

    vehicle: Mapped["Vehicle"] = relationship(
        back_populates="violations"
    )


class FuelRecord(Base):
    __tablename__ = "fuel_record"

    id: Mapped[int] = mapped_column(primary_key=True)

    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicle_info.id"), index=True
    )
    fuel_date: Mapped[date] = mapped_column(Date, index=True)
    liters: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=0
    )
    mileage: Mapped[Decimal | None] = mapped_column(Numeric(12, 1))
    station: Mapped[str | None] = mapped_column(String(200))
    invoice_no: Mapped[str | None] = mapped_column(String(100))
    attachment_url: Mapped[str | None] = mapped_column(String(500))
    remark: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now
    )

    vehicle: Mapped["Vehicle"] = relationship(
        back_populates="fuels"
    )


class Reimbursement(Base):
    __tablename__ = "reimbursement"

    id: Mapped[int] = mapped_column(primary_key=True)
    reimbursement_no: Mapped[str] = mapped_column(
        String(40), unique=True, index=True
    )
    reimbursement_month: Mapped[str] = mapped_column(
        String(7), index=True
    )

    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicle_info.id"), index=True
    )
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("project_info.id")
    )

    applicant_id: Mapped[int] = mapped_column(
        ForeignKey("sys_user.id")
    )
    applicant_name: Mapped[str] = mapped_column(String(50))

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=0
    )

    # DRAFT、SUBMITTED、PROJECT_APPROVED、APPROVED、REJECTED
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")

    reject_reason: Mapped[str | None] = mapped_column(String(500))
    remark: Mapped[str | None] = mapped_column(Text)

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now
    )

    vehicle: Mapped["Vehicle"] = relationship(
        back_populates="reimbursements"
    )
    details: Mapped[list["ReimbursementDetail"]] = relationship(
        back_populates="reimbursement",
        cascade="all, delete-orphan",
    )
    approvals: Mapped[list["ApprovalRecord"]] = relationship(
        back_populates="reimbursement",
        cascade="all, delete-orphan",
    )


class ReimbursementDetail(Base):
    __tablename__ = "reimbursement_detail"

    id: Mapped[int] = mapped_column(primary_key=True)
    reimbursement_id: Mapped[int] = mapped_column(
        ForeignKey("reimbursement.id"), index=True
    )

    # FUEL、MAINTENANCE、TOLL、PARKING、OTHER
    expense_type: Mapped[str] = mapped_column(String(30))
    expense_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    related_mileage: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 1)
    )
    invoice_no: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(500))
    attachment_url: Mapped[str | None] = mapped_column(String(500))

    reimbursement: Mapped["Reimbursement"] = relationship(
        back_populates="details"
    )


class ApprovalRecord(Base):
    __tablename__ = "approval_record"

    id: Mapped[int] = mapped_column(primary_key=True)
    reimbursement_id: Mapped[int] = mapped_column(
        ForeignKey("reimbursement.id"), index=True
    )
    approver_id: Mapped[int] = mapped_column(ForeignKey("sys_user.id"))
    approver_name: Mapped[str] = mapped_column(String(50))

    action: Mapped[str] = mapped_column(String(30))
    opinion: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now
    )

    reimbursement: Mapped["Reimbursement"] = relationship(
        back_populates="approvals"
    )
