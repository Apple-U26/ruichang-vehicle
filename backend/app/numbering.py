"""Allocate reimbursement display numbers without counting existing rows."""

from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Reimbursement


def provisional_reimbursement_no() -> str:
    return f"TMP-{uuid4().hex}"


def assign_reimbursement_no(db: Session, row: Reimbursement) -> None:
    # The database allocates the ID, including for concurrent inserts. Keep the
    # existing display format and tolerate legacy/imported numbers on collision.
    db.flush()
    prefix = f"BX-{row.reimbursement_month.replace('-', '')}-"
    for offset in range(1000):
        try:
            with db.begin_nested():
                row.reimbursement_no = f"{prefix}{row.id + offset:04d}"
                db.flush()
            return
        except IntegrityError:
            continue
    raise HTTPException(status_code=409, detail="报销编号分配冲突，请稍后重试")
