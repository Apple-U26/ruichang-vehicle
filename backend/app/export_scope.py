"""Apply the same resource boundary to every sheet in a workbook export."""

from contextlib import contextmanager

from fastapi import HTTPException
from sqlalchemy import event, select
from sqlalchemy.orm import with_loader_criteria

from app.access import apply_vehicle_scope, project_owner_filter
from app.models import (
    FuelRecord, MaintenanceRecord, MileageRecord, Project,
    Reimbursement, ReimbursementDetail, Vehicle, ViolationRecord,
    Welder, WelderInspection,
)


@contextmanager
def export_scope(db, user):
    if user.role == "DRIVER":
        raise HTTPException(status_code=403, detail="驾驶员无台账导出权限")
    if user.role in {"ADMIN", "FINANCE"}:
        yield
        return

    vehicle_ids = list(db.scalars(apply_vehicle_scope(user, select(Vehicle.id))))
    reimbursement_ids = list(db.scalars(
        select(Reimbursement.id).where(Reimbursement.vehicle_id.in_(vehicle_ids))
    ))
    welder_stmt = select(Welder.id)
    if user.role == "PROJECT_MANAGER":
        welder_stmt = welder_stmt.where(
            Welder.project_id.in_(select(Project.id).where(project_owner_filter(user)))
        )
    welder_ids = list(db.scalars(welder_stmt))
    criteria = [with_loader_criteria(Vehicle, Vehicle.id.in_(vehicle_ids), include_aliases=True)]
    for model in (MileageRecord, MaintenanceRecord, ViolationRecord, FuelRecord, Reimbursement):
        criteria.append(with_loader_criteria(model, model.vehicle_id.in_(vehicle_ids), include_aliases=True))
    criteria.extend([
        with_loader_criteria(ReimbursementDetail, ReimbursementDetail.reimbursement_id.in_(reimbursement_ids), include_aliases=True),
        with_loader_criteria(Welder, Welder.id.in_(welder_ids), include_aliases=True),
        with_loader_criteria(WelderInspection, WelderInspection.welder_id.in_(welder_ids), include_aliases=True),
    ])

    def scope_statement(state):
        if state.is_select:
            state.statement = state.statement.options(*criteria)

    event.listen(db, "do_orm_execute", scope_statement)
    try:
        yield
    finally:
        event.remove(db, "do_orm_execute", scope_statement)
