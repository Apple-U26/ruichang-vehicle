"""Shared resource checks for lists and direct record operations."""

from fastapi import HTTPException
from sqlalchemy import or_, select

from app.models import Project, User, Vehicle


def project_owner_filter(user: User):
    return or_(
        Project.manager_user_id == user.id,
        (Project.manager_user_id.is_(None))
        & (Project.manager_name == user.real_name),
    )


def project_owned_by_user(user: User, project: Project | None) -> bool:
    if project is None:
        return False
    if project.manager_user_id is not None:
        return project.manager_user_id == user.id
    return bool(user.real_name and project.manager_name == user.real_name)


def apply_vehicle_scope(user: User, stmt, join_project: bool = False):
    if user.role == "DRIVER":
        return stmt.where(Vehicle.id == (user.vehicle_id or -1))
    if user.role == "VEHICLE_MANAGER":
        return stmt.where(Vehicle.vehicle_manager == user.real_name)
    if user.role == "PROJECT_MANAGER":
        return stmt.where(
            Vehicle.project_id.in_(
                select(Project.id).where(project_owner_filter(user))
            )
        )
    if user.role not in {"ADMIN", "FINANCE"}:
        raise HTTPException(status_code=403, detail="没有操作权限")
    return stmt


def ensure_vehicle_access(user: User, vehicle: Vehicle | None) -> None:
    if vehicle is None:
        raise HTTPException(status_code=404, detail="车辆不存在")
    allowed = user.role in {"ADMIN", "FINANCE"}
    if user.role == "DRIVER":
        allowed = bool(user.vehicle_id and vehicle.id == user.vehicle_id)
    elif user.role == "VEHICLE_MANAGER":
        allowed = vehicle.vehicle_manager == user.real_name
    elif user.role == "PROJECT_MANAGER":
        allowed = project_owned_by_user(user, vehicle.project)
    if not allowed:
        raise HTTPException(status_code=403, detail="无权操作该车辆的数据")


def ensure_project_access(user: User, project: Project | None) -> None:
    if user.role == "PROJECT_MANAGER" and not project_owned_by_user(user, project):
        raise HTTPException(status_code=403, detail="只能操作自己负责的项目")
