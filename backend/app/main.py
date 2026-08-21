import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    UploadFile,
    File,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.orm import Session
from urllib.parse import quote

from app.routers import auth
from app.config import settings
from app.database import (
    Base,
    engine,
    ensure_column,
    ensure_column_type,
    get_db,
    SessionLocal,
)
from app.excel_service import (
    export_vehicle_workbook,
    export_welder_workbook,
    export_workbook,
    import_workbook,
)
from app.models import (
    User,
    Project,
    Vehicle,
    MileageRecord,
    MaintenanceRecord,
    ViolationRecord,
    FuelRecord,
    Reimbursement,
    ReimbursementDetail,
    ApprovalRecord,
    Welder,
    WelderInspection,
)
from app.schemas import (
    ApprovalIn,
    BatchApproveIn,
    BatchDeleteIn,
    ChangePasswordIn,
    LoginIn,
    MileageOutIn,
    MileageCloseIn,
    MaintenanceIn,
    ViolationIn,
    FuelIn,
    ProjectIn,
    ProjectUpdateIn,
    ReimbursementIn,
    RejectIn,
    RepairIn,
    UserCreateIn,
    UserUpdateIn,
    VehicleIn,
    WelderIn,
    WelderInspectionIn,
)
from app.security import (
    hash_password,
    get_current_user,
    get_current_user_query,
    require_roles
)


Base.metadata.create_all(bind=engine)


ensure_column("sys_user", "vehicle_id", "BIGINT NULL")
ensure_column("violation_record", "attachment_url", "VARCHAR(500)")
ensure_column("reimbursement_detail", "source_type", "VARCHAR(30)")
ensure_column("reimbursement_detail", "source_id", "INT NULL")
ensure_column("project_info", "location", "VARCHAR(200)")
ensure_column("project_info", "manager_user_id", "BIGINT NULL")
ensure_column_type("vehicle_mileage", "trip_date", "DATETIME NULL")
ensure_column("vehicle_mileage", "close_time", "DATETIME NULL")

os.makedirs(settings.upload_path, exist_ok=True)

FRONTEND_DIST = (
    Path(__file__).resolve().parent.parent.parent
    / "frontend"
    / "dist"
)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0"
)
app.include_router(auth.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.mount(
    "/uploads",
    StaticFiles(directory=str(settings.upload_path)),
    name="uploads"
)


def vehicle_to_dict(vehicle: Vehicle):
    return {
        "id": vehicle.id,
        "vehicle_code": vehicle.vehicle_code,
        "plate_no": vehicle.plate_no,
        "project_id": vehicle.project_id,
        "project_name": (
            vehicle.project.name if vehicle.project else None
        ),
        "project_manager_name": (
            vehicle.project.manager_name if vehicle.project else None
        ),
        "project_manager": vehicle.project_manager,
        "vehicle_manager": vehicle.vehicle_manager,
        "ownership": vehicle.ownership,
        "initial_mileage": float(vehicle.initial_mileage or 0),
        "current_mileage": float(vehicle.current_mileage or 0),
        "status": vehicle.status,
        "vehicle_age": vehicle.vehicle_age,
        "violation_info": vehicle.violation_info,
        "appearance_url": vehicle.appearance_url,
        "remark": vehicle.remark,
        "created_at": vehicle.created_at,
        "updated_at": vehicle.updated_at,
    }


def user_to_dict(user: User):
    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "role": user.role,
        "enabled": user.enabled,
        "vehicle_id": user.vehicle_id,
        "plate_no": (
            user.vehicle.plate_no if user.vehicle else None
        ),
        "vehicle_code": (
            user.vehicle.vehicle_code if user.vehicle else None
        ),
        "created_at": user.created_at,
    }


def validate_vehicle_binding(
    db: Session,
    role: str,
    vehicle_id: int | None,
    exclude_user_id: int | None = None,
) -> int | None:
    if role != "DRIVER" or vehicle_id is None:
        return None

    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=400, detail="绑定车辆不存在")

    stmt = select(User).where(User.vehicle_id == vehicle_id)
    if exclude_user_id is not None:
        stmt = stmt.where(User.id != exclude_user_id)
    duplicate = db.scalar(stmt)
    if duplicate:
        raise HTTPException(
            status_code=400,
            detail=f"车辆 {vehicle.plate_no} 已经绑定账号",
        )

    return vehicle_id


def ensure_driver_vehicle(
    user: User,
    vehicle_id: int | None = None,
) -> None:
    if user.role != "DRIVER":
        return
    if not user.vehicle_id:
        raise HTTPException(
            status_code=400,
            detail="当前账号未绑定车辆，请联系管理员",
        )
    if vehicle_id is not None and vehicle_id != user.vehicle_id:
        raise HTTPException(
            status_code=403,
            detail="只能操作自己绑定的车辆",
        )


def ensure_not_driver(user: User) -> None:
    if user.role == "DRIVER":
        raise HTTPException(
            status_code=403,
            detail="驾驶员无该模块权限",
        )


def names_similar(name_a: str | None, name_b: str | None) -> bool:
    if not name_a or not name_b:
        return False
    a = name_a.strip()
    b = name_b.strip()
    if a == b:
        return True
    if len(a) != len(b):
        return False
    return sum(1 for x, y in zip(a, b) if x != y) <= 1


def project_owned_by_user(user: User, project: Project | None) -> bool:
    if project is None:
        return False
    if project.manager_user_id and project.manager_user_id == user.id:
        return True
    return names_similar(project.manager_name, user.real_name)


def sync_project_owner_ids(db: Session) -> None:
    users = db.scalars(select(User)).all()
    projects = db.scalars(
        select(Project).where(Project.manager_user_id.is_(None))
    ).all()
    for project in projects:
        if not project.manager_name:
            continue
        for user in users:
            if names_similar(project.manager_name, user.real_name):
                project.manager_user_id = user.id
                break
    db.commit()


sync_project_owner_ids(SessionLocal())


def ensure_vehicle_manageable(
    user: User,
    vehicle_manager_name: str | None,
) -> None:
    if (
        user.role == "VEHICLE_MANAGER"
        and vehicle_manager_name != user.real_name
    ):
        raise HTTPException(
            status_code=403,
            detail="只能编辑自己负责的车辆",
        )


def apply_vehicle_scope(
    user: User,
    stmt,
    join_project: bool = False,
):
    if user.role == "DRIVER":
        if user.vehicle_id:
            return stmt.where(Vehicle.id == user.vehicle_id)
        return stmt.where(Vehicle.id == -1)

    if user.role == "VEHICLE_MANAGER":
        return stmt.where(Vehicle.vehicle_manager == user.real_name)

    if user.role == "PROJECT_MANAGER":
        if join_project:
            stmt = stmt.join(Project, Project.id == Vehicle.project_id)
        return stmt.where(Project.manager_name == user.real_name)

    return stmt


def ensure_reimbursement_source_available(
    db: Session,
    source_type: str,
    source_id: int,
) -> None:
    used = db.scalar(
        select(ReimbursementDetail.id).where(
            ReimbursementDetail.source_type == source_type,
            ReimbursementDetail.source_id == source_id,
        )
    )
    if used:
        label = {
            "FUEL": "油费",
            "MAINTENANCE": "维保",
            "MILEAGE": "里程记录",
        }.get(source_type, "费用")
        raise HTTPException(
            status_code=400,
            detail=f"该{label}记录已被报销单使用，不能重复关联",
        )


@app.get("/api/health")
def health():
    return {"status": "ok", "name": settings.app_name}




@app.get("/api/auth/me", tags=["认证"])
def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "role": user.role,
        "vehicle_id": user.vehicle_id,
        "plate_no": user.vehicle.plate_no if user.vehicle else None,
    }


# =========================
# 用户管理
# =========================

@app.get("/api/users")
def user_list(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    stmt = select(User).order_by(User.id.asc())
    rows = db.scalars(stmt).all()
    items = [user_to_dict(row) for row in rows]
    return items


@app.post("/api/users")
def user_create(
    data: UserCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    exists = db.scalar(
        select(User).where(User.username == data.username)
    )
    if exists:
        raise HTTPException(status_code=400, detail="用户名已存在")

    vehicle_id = validate_vehicle_binding(
        db, data.role, data.vehicle_id
    )

    row = User(
        username=data.username,
        real_name=data.real_name,
        password_hash=hash_password(data.password),
        role=data.role,
        enabled=data.enabled,
        vehicle_id=vehicle_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "id": row.id,
        "message": "用户创建成功",
    }


@app.put("/api/users/{user_id}")
def user_update(
    user_id: int,
    data: UserUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    row = db.get(User, user_id)

    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")

    if row.id == user.id and not data.enabled:
        raise HTTPException(status_code=400, detail="不能停用当前登录账号")

    vehicle_id = validate_vehicle_binding(
        db, data.role, data.vehicle_id, exclude_user_id=user_id
    )

    row.real_name = data.real_name
    row.role = data.role
    row.enabled = data.enabled
    row.vehicle_id = vehicle_id if data.role == "DRIVER" else None
    if data.password:
        row.password_hash = hash_password(data.password)

    db.commit()
    return {"message": "用户修改成功"}


@app.delete("/api/users/{user_id}")
def user_delete(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    row = db.get(User, user_id)

    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")

    if row.role == "ADMIN":
        raise HTTPException(
            status_code=400,
            detail="系统管理员账号无法被删除",
        )

    related = (
        db.scalar(
            select(func.count(Reimbursement.id)).where(
                Reimbursement.applicant_id == user_id
            )
        )
        or 0
    ) + (
        db.scalar(
            select(func.count(ApprovalRecord.id)).where(
                ApprovalRecord.approver_id == user_id
            )
        )
        or 0
    ) + (
        db.scalar(
            select(func.count(MileageRecord.id)).where(
                MileageRecord.created_by == user_id
            )
        )
        or 0
    )

    if related:
        raise HTTPException(
            status_code=400,
            detail="该用户已有业务记录，不能删除，可改为停用",
        )

    db.delete(row)
    db.commit()
    return {"message": "用户删除成功"}


@app.post("/api/excel/import", tags=["Excel"])
async def excel_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            "ADMIN",
            "VEHICLE_MANAGER",
            "PROJECT_MANAGER",
            "FINANCE",
        )
    ),
):
    extension = os.path.splitext(file.filename or "")[1].lower()

    if extension != ".xlsx":
        raise HTTPException(
            status_code=400,
            detail="仅支持 .xlsx 文件",
        )

    content = await file.read()

    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="文件不能超过10MB",
        )

    try:
        result = import_workbook(db, content, user)
        db.commit()
        return result
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@app.get("/api/excel/export", tags=["Excel"])
def excel_export(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_query),
):
    output = export_workbook(db)
    filename = f"车辆里程维保报销台账-{date.today():%Y%m%d}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )


@app.get("/api/excel/export/vehicles", tags=["Excel"])
def excel_export_vehicles(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_query),
):
    output = export_vehicle_workbook(db)
    filename = f"车辆台账-{date.today():%Y%m%d}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )


@app.get("/api/excel/export/welders", tags=["Excel"])
def excel_export_welders(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_query),
):
    output = export_welder_workbook(db)
    filename = f"焊机台账-{date.today():%Y%m%d}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )
@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user)
):
    extension = os.path.splitext(file.filename or "")[1].lower()

    allowed = {
        ".jpg", ".jpeg", ".png", ".pdf",
        ".xlsx", ".xls"
    }

    if extension not in allowed:
        raise HTTPException(status_code=400, detail="不支持该文件类型")

    filename = f"{uuid4().hex}{extension}"
    path = settings.upload_path / filename

    content = await file.read()

    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件不能超过10MB")

    with open(path, "wb") as f:
        f.write(content)

    return {
        "filename": filename,
        "url": f"/uploads/{filename}"
    }


# =========================
# 项目管理
# =========================

@app.get("/api/projects")
def project_list(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    stmt = select(Project)
    rows = db.scalars(stmt.order_by(Project.id.asc())).all()
    items = [
        {
            "id": row.id,
            "name": row.name,
            "manager_name": row.manager_name,
            "manager_user_id": row.manager_user_id,
            "location": row.location,
            "enabled": row.enabled,
            "remark": row.remark
        }
        for row in rows
    ]
    return items


@app.post("/api/projects")
def project_create(
    data: ProjectIn,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles("ADMIN", "PROJECT_MANAGER", "FINANCE")
    )
):
    exists = db.scalar(
        select(Project).where(Project.name == data.name)
    )
    if exists:
        raise HTTPException(status_code=400, detail="项目名称已存在")

    manager_user = None
    if user.role == "PROJECT_MANAGER":
        manager_user = user
    elif data.manager_user_id:
        manager_user = db.get(User, data.manager_user_id)
    elif data.manager_name:
        manager_user = db.scalar(
            select(User).where(User.real_name == data.manager_name)
        )
        if manager_user is None:
            for candidate in db.scalars(select(User)).all():
                if names_similar(data.manager_name, candidate.real_name):
                    manager_user = candidate
                    break

    row = Project(
        **data.model_dump(exclude={"manager_user_id"}),
        manager_user_id=manager_user.id if manager_user else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {"id": row.id, "message": "项目创建成功"}


@app.put("/api/projects/{project_id}")
def project_update(
    project_id: int,
    data: ProjectUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles("ADMIN", "PROJECT_MANAGER", "FINANCE")
    ),
):
    row = db.get(Project, project_id)

    if not row:
        raise HTTPException(status_code=404, detail="项目不存在")

    if user.role == "PROJECT_MANAGER" and not project_owned_by_user(
        user, row
    ):
        raise HTTPException(
            status_code=403,
            detail="只能编辑自己负责的项目",
        )

    duplicate = db.scalar(
        select(Project).where(
            Project.name == data.name,
            Project.id != project_id,
        )
    )
    if duplicate:
        raise HTTPException(status_code=400, detail="项目名称已存在")

    row.name = data.name
    row.manager_name = data.manager_name
    row.location = data.location
    row.enabled = data.enabled
    row.remark = data.remark
    if user.role == "PROJECT_MANAGER":
        row.manager_user_id = user.id
    elif user.role == "ADMIN" and data.manager_user_id is not None:
        if not db.get(User, data.manager_user_id):
            raise HTTPException(status_code=400, detail="负责人账号不存在")
        row.manager_user_id = data.manager_user_id
    db.commit()

    return {"message": "项目修改成功"}


@app.delete("/api/projects/{project_id}")
def project_delete(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    row = db.get(Project, project_id)

    if not row:
        raise HTTPException(status_code=404, detail="项目不存在")

    linked = db.scalar(
        select(func.count(Vehicle.id)).where(
            Vehicle.project_id == project_id
        )
    ) or 0

    if linked:
        row.enabled = False
        db.commit()
        return {
            "message": "项目下仍有车辆，已改为停用"
        }

    db.delete(row)
    db.commit()
    return {"message": "项目删除成功"}


@app.post("/api/projects/batch-delete")
def project_batch_delete(
    data: BatchDeleteIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    deleted = 0
    disabled = 0
    for project_id in data.ids:
        row = db.get(Project, project_id)
        if not row:
            continue
        linked = (
            db.scalar(
                select(func.count(Vehicle.id)).where(
                    Vehicle.project_id == project_id
                )
            )
            or 0
        )
        if linked:
            row.enabled = False
            disabled += 1
        else:
            db.delete(row)
            deleted += 1
    db.commit()
    return {
        "message": f"已删除 {deleted} 个项目，停用 {disabled} 个有车辆的项目",
        "deleted": deleted,
        "disabled": disabled,
    }


# =========================
# 车辆档案
# =========================

@app.get("/api/vehicles")
def vehicle_list(
    keyword: str | None = None,
    project_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    stmt = select(Vehicle)

    if keyword:
        stmt = stmt.where(
            Vehicle.plate_no.like(f"%{keyword}%")
        )

    if project_id:
        stmt = stmt.where(Vehicle.project_id == project_id)

    if status:
        stmt = stmt.where(Vehicle.status == status)

    if user.role in ("DRIVER", "VEHICLE_MANAGER"):
        stmt = apply_vehicle_scope(user, stmt, join_project=False)

    rows = db.scalars(stmt.order_by(Vehicle.id.asc())).all()
    items = [vehicle_to_dict(row) for row in rows]
    return items


@app.get("/api/vehicles/{vehicle_id}")
def vehicle_detail(
    vehicle_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    row = db.get(Vehicle, vehicle_id)

    if not row:
        raise HTTPException(status_code=404, detail="车辆不存在")

    if user.role == "DRIVER" and user.vehicle_id and row.id != user.vehicle_id:
        raise HTTPException(status_code=403, detail="无权查看该车辆")

    return vehicle_to_dict(row)


@app.post("/api/vehicles")
def vehicle_create(
    data: VehicleIn,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            "ADMIN",
            "VEHICLE_MANAGER",
            "PROJECT_MANAGER",
            "FINANCE",
        )
    )
):
    plate_no = data.plate_no.strip().upper()

    exists = db.scalar(
        select(Vehicle).where(Vehicle.plate_no == plate_no)
    )
    if exists:
        raise HTTPException(status_code=400, detail="车牌号已经存在")

    vehicle_manager = (
        user.real_name
        if user.role == "VEHICLE_MANAGER"
        else data.vehicle_manager
    )

    max_id = db.scalar(select(func.max(Vehicle.id))) or 0
    vehicle_code = f"CL-{max_id + 1:06d}"
    while db.scalar(
        select(Vehicle).where(Vehicle.vehicle_code == vehicle_code)
    ):
        max_id += 1
        vehicle_code = f"CL-{max_id + 1:06d}"

    row = Vehicle(
        vehicle_code=vehicle_code,
        plate_no=plate_no,
        project_id=data.project_id,
        project_manager=data.project_manager,
        vehicle_manager=vehicle_manager,
        appearance_url=data.appearance_url,
        ownership=data.ownership,
        initial_mileage=data.initial_mileage,
        current_mileage=data.initial_mileage,
        status=data.status,
        vehicle_age=data.vehicle_age,
        violation_info=data.violation_info,
        remark=data.remark
    )

    db.add(row)
    db.commit()
    db.refresh(row)

    return vehicle_to_dict(row)


@app.put("/api/vehicles/{vehicle_id}")
def vehicle_update(
    vehicle_id: int,
    data: VehicleIn,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            "ADMIN",
            "VEHICLE_MANAGER",
            "PROJECT_MANAGER",
            "FINANCE",
        )
    )
):
    row = db.get(Vehicle, vehicle_id)

    if not row:
        raise HTTPException(status_code=404, detail="车辆不存在")

    duplicate = db.scalar(
        select(Vehicle).where(
            Vehicle.plate_no == data.plate_no.strip().upper(),
            Vehicle.id != vehicle_id
        )
    )
    if duplicate:
        raise HTTPException(status_code=400, detail="车牌号已经存在")

    ensure_vehicle_manageable(user, row.vehicle_manager)

    if user.role == "PROJECT_MANAGER" and not project_owned_by_user(
        user, row.project
    ):
        raise HTTPException(
            status_code=403,
            detail="只能编辑自己项目下的车辆",
        )

    row.plate_no = data.plate_no.strip().upper()
    row.project_id = data.project_id
    row.project_manager = data.project_manager
    row.vehicle_manager = (
        user.real_name
        if user.role == "VEHICLE_MANAGER"
        else data.vehicle_manager
    )
    row.appearance_url = data.appearance_url
    row.ownership = data.ownership
    row.status = data.status
    row.vehicle_age = data.vehicle_age
    row.violation_info = data.violation_info
    row.remark = data.remark
    if user.role == "ADMIN":
        row.initial_mileage = data.initial_mileage

    db.commit()

    return {"message": "车辆修改成功"}


def delete_vehicle_cascade(db: Session, vehicle_id: int) -> bool:
    row = db.get(Vehicle, vehicle_id)
    if not row:
        return False

    reimbursement_ids = select(Reimbursement.id).where(
        Reimbursement.vehicle_id == vehicle_id
    )
    db.execute(
        delete(ApprovalRecord).where(
            ApprovalRecord.reimbursement_id.in_(reimbursement_ids)
        )
    )
    db.execute(
        delete(ReimbursementDetail).where(
            ReimbursementDetail.reimbursement_id.in_(reimbursement_ids)
        )
    )
    db.execute(
        delete(Reimbursement).where(
            Reimbursement.vehicle_id == vehicle_id
        )
    )
    db.execute(
        delete(MaintenanceRecord).where(
            MaintenanceRecord.vehicle_id == vehicle_id
        )
    )
    db.execute(
        delete(MileageRecord).where(
            MileageRecord.vehicle_id == vehicle_id
        )
    )
    db.execute(
        delete(ViolationRecord).where(
            ViolationRecord.vehicle_id == vehicle_id
        )
    )
    db.execute(
        delete(FuelRecord).where(
            FuelRecord.vehicle_id == vehicle_id
        )
    )

    db.delete(row)
    return True


def reset_vehicle_sequence(db: Session) -> None:
    old_ids = db.scalars(
        select(Vehicle.id).order_by(Vehicle.id.asc())
    ).all()
    if not old_ids:
        db.execute(text("ALTER TABLE vehicle_info AUTO_INCREMENT = 1"))
        return

    mapping = {
        old_id: new_id
        for new_id, old_id in enumerate(old_ids, start=1)
    }
    db.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    try:
        for old_id in mapping:
            db.execute(
                text(
                    "UPDATE vehicle_info SET id = id + 1000000 "
                    "WHERE id = :old_id"
                ),
                {"old_id": old_id},
            )
        for old_id, new_id in mapping.items():
            db.execute(
                text(
                    "UPDATE vehicle_info SET id = :new_id, "
                    "vehicle_code = :code "
                    "WHERE id = :old_id + 1000000"
                ),
                {
                    "new_id": new_id,
                    "code": f"CL-{new_id:06d}",
                    "old_id": old_id,
                },
            )
            for table in (
                "vehicle_mileage",
                "maintenance_record",
                "violation_record",
                "fuel_record",
                "reimbursement",
                "sys_user",
            ):
                db.execute(
                    text(
                        f"UPDATE {table} SET vehicle_id = :new_id "
                        "WHERE vehicle_id = :old_id"
                    ),
                    {"new_id": new_id, "old_id": old_id},
                )
    finally:
        db.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    db.execute(
        text(
            f"ALTER TABLE vehicle_info AUTO_INCREMENT = "
            f"{len(mapping) + 1}"
        )
    )


@app.delete("/api/vehicles/{vehicle_id}")
def vehicle_delete(
    vehicle_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    if not delete_vehicle_cascade(db, vehicle_id):
        raise HTTPException(status_code=404, detail="车辆不存在")
    reset_vehicle_sequence(db)
    db.commit()
    return {"message": "车辆及其业务记录已删除"}


@app.post("/api/vehicles/batch-delete")
def vehicle_batch_delete(
    data: BatchDeleteIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    deleted = sum(
        delete_vehicle_cascade(db, vehicle_id)
        for vehicle_id in data.ids
    )
    reset_vehicle_sequence(db)
    db.commit()
    return {"message": f"已删除 {deleted} 辆车", "deleted": deleted}


# =========================
# 出车和收车
# =========================

@app.get("/api/mileages")
def mileage_list(
    vehicle_id: int | None = None,
    month: str | None = None,
    keyword: str | None = None,
    exclude_used: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    stmt = (
        select(MileageRecord, Vehicle.plate_no)
        .join(Vehicle, Vehicle.id == MileageRecord.vehicle_id)
    )

    if vehicle_id:
        stmt = stmt.where(MileageRecord.vehicle_id == vehicle_id)

    if month:
        stmt = stmt.where(
            func.date_format(MileageRecord.trip_date, "%Y-%m") == month
        )

    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                Vehicle.plate_no.like(like),
                MileageRecord.driver_name.like(like),
                MileageRecord.purpose.like(like),
            )
        )

    if exclude_used:
        stmt = stmt.where(
            MileageRecord.id.not_in(
                select(ReimbursementDetail.source_id).where(
                    ReimbursementDetail.source_type == "MILEAGE",
                    ReimbursementDetail.source_id.is_not(None),
                )
            )
        )

    stmt = apply_vehicle_scope(user, stmt, join_project=True)

    rows = db.execute(
        stmt.order_by(MileageRecord.id.asc())
    ).all()
    items = [
        {
            "id": record.id,
            "vehicle_id": record.vehicle_id,
            "plate_no": plate_no,
            "trip_date": record.trip_date,
            "close_time": record.close_time,
            "out_mileage": float(record.out_mileage),
            "in_mileage": (
                float(record.in_mileage)
                if record.in_mileage is not None else None
            ),
            "distance": float(record.distance or 0),
            "driver_name": record.driver_name,
            "departure": record.departure,
            "destination": record.destination,
            "purpose": record.purpose,
            "out_photo": record.out_photo,
            "in_photo": record.in_photo,
            "status": record.status,
            "abnormal": record.abnormal,
            "abnormal_reason": record.abnormal_reason
        }
        for record, plate_no in rows
    ]
    return items


@app.post("/api/mileages/out")
def mileage_out(
    data: MileageOutIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    ensure_driver_vehicle(user, data.vehicle_id)

    vehicle = db.get(Vehicle, data.vehicle_id)

    if not vehicle:
        raise HTTPException(status_code=404, detail="车辆不存在")

    if vehicle.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="车辆当前不可出车")

    unfinished = db.scalar(
        select(MileageRecord).where(
            MileageRecord.vehicle_id == data.vehicle_id,
            MileageRecord.status == "OUT"
        )
    )

    if unfinished:
        raise HTTPException(
            status_code=400,
            detail="该车辆存在未完成的出车记录"
        )

    original_current = vehicle.current_mileage
    abnormal = False
    reason = None

    if data.out_mileage < original_current:
        abnormal = True
        reason = "出车里程小于车辆当前里程"

    row = MileageRecord(
        vehicle_id=data.vehicle_id,
        trip_date=data.trip_date,
        out_mileage=data.out_mileage,
        distance=0,
        driver_name=data.driver_name,
        departure=data.departure,
        destination=data.destination,
        purpose=data.purpose,
        out_photo=data.out_photo,
        status="OUT",
        abnormal=abnormal,
        abnormal_reason=reason,
        remark=data.remark,
        created_by=user.id
    )

    db.add(row)
    vehicle.current_mileage = data.out_mileage
    db.commit()
    db.refresh(row)

    return {
        "id": row.id,
        "abnormal": row.abnormal,
        "message": "出车登记成功"
    }


@app.put("/api/mileages/{record_id}/close")
def mileage_close(
    record_id: int,
    data: MileageCloseIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    row = db.get(MileageRecord, record_id)

    if not row:
        raise HTTPException(status_code=404, detail="里程记录不存在")

    ensure_driver_vehicle(user, row.vehicle_id)

    if row.status == "CLOSED":
        raise HTTPException(status_code=400, detail="该行程已经收车")

    if data.in_mileage < row.out_mileage:
        raise HTTPException(
            status_code=400,
            detail="收车里程不能小于出车里程"
        )

    distance = data.in_mileage - row.out_mileage

    if distance > Decimal("2000"):
        row.abnormal = True
        row.abnormal_reason = "单次行驶里程超过2000公里"

    row.in_mileage = data.in_mileage
    row.distance = distance
    row.in_photo = data.in_photo
    row.status = "CLOSED"
    row.close_time = datetime.now()

    vehicle = db.get(Vehicle, row.vehicle_id)

    if data.in_mileage < vehicle.current_mileage:
        row.abnormal = True
        row.abnormal_reason = "收车里程小于车辆当前里程"
    vehicle.current_mileage = data.in_mileage

    db.commit()

    return {
        "message": "收车登记成功",
        "distance": float(distance),
        "abnormal": row.abnormal,
        "abnormal_reason": row.abnormal_reason
    }


@app.delete("/api/mileages/{record_id}")
def mileage_delete(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    row = db.get(MileageRecord, record_id)

    if not row:
        raise HTTPException(status_code=404, detail="里程记录不存在")

    db.delete(row)
    db.commit()
    return {"message": "里程记录删除成功"}


@app.post("/api/mileages/batch-delete")
def mileage_batch_delete(
    data: BatchDeleteIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    deleted = 0
    for record_id in data.ids:
        row = db.get(MileageRecord, record_id)
        if row:
            db.delete(row)
            deleted += 1
    db.commit()
    return {"message": f"已删除 {deleted} 条里程记录", "deleted": deleted}


# =========================
# 维保管理
# =========================

@app.get("/api/maintenances")
def maintenance_list(
    vehicle_id: int | None = None,
    month: str | None = None,
    exclude_used: bool = False,
    keyword: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    stmt = (
        select(MaintenanceRecord, Vehicle.plate_no)
        .join(Vehicle, Vehicle.id == MaintenanceRecord.vehicle_id)
    )

    if vehicle_id:
        stmt = stmt.where(
            MaintenanceRecord.vehicle_id == vehicle_id
        )

    if month:
        stmt = stmt.where(
            func.date_format(
                MaintenanceRecord.maintenance_date, "%Y-%m"
            )
            == month
        )

    if exclude_used:
        stmt = stmt.where(
            MaintenanceRecord.id.not_in(
                select(ReimbursementDetail.source_id).where(
                    ReimbursementDetail.source_type == "MAINTENANCE",
                    ReimbursementDetail.source_id.is_not(None),
                )
            )
        )

    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                Vehicle.plate_no.like(like),
                MaintenanceRecord.items.like(like),
                MaintenanceRecord.service_provider.like(like),
            )
        )

    stmt = apply_vehicle_scope(user, stmt, join_project=True)

    rows = db.execute(
        stmt.order_by(MaintenanceRecord.id.asc())
    ).all()
    items = [
        {
            "id": row.id,
            "vehicle_id": row.vehicle_id,
            "plate_no": plate_no,
            "maintenance_date": row.maintenance_date,
            "current_mileage": float(row.current_mileage),
            "maintenance_type": row.maintenance_type,
            "items": row.items,
            "amount": float(row.amount),
            "service_provider": row.service_provider,
            "operator_name": row.operator_name,
            "next_mileage": (
                float(row.next_mileage)
                if row.next_mileage is not None else None
            ),
            "next_date": row.next_date,
            "remark": row.remark
        }
        for row, plate_no in rows
    ]


@app.post("/api/maintenances")
def maintenance_create(
    data: MaintenanceIn,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            "ADMIN",
            "VEHICLE_MANAGER",
            "PROJECT_MANAGER",
            "DRIVER",
        )
    )
):
    ensure_driver_vehicle(user, data.vehicle_id)

    vehicle = db.get(Vehicle, data.vehicle_id)

    if not vehicle:
        raise HTTPException(status_code=404, detail="车辆不存在")

    row = MaintenanceRecord(**data.model_dump())
    db.add(row)

    if data.current_mileage > vehicle.current_mileage:
        vehicle.current_mileage = data.current_mileage

    db.commit()
    db.refresh(row)

    return {
        "id": row.id,
        "message": "维保记录保存成功"
    }


@app.put("/api/maintenances/{record_id}")
def maintenance_update(
    record_id: int,
    data: MaintenanceIn,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            "ADMIN",
            "VEHICLE_MANAGER",
            "PROJECT_MANAGER",
        )
    ),
):
    row = db.get(MaintenanceRecord, record_id)

    if not row:
        raise HTTPException(status_code=404, detail="维保记录不存在")

    vehicle = db.get(Vehicle, data.vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="车辆不存在")

    row.vehicle_id = data.vehicle_id
    row.maintenance_date = data.maintenance_date
    row.current_mileage = data.current_mileage
    row.maintenance_type = data.maintenance_type
    row.items = data.items
    row.amount = data.amount
    row.service_provider = data.service_provider
    row.operator_name = data.operator_name
    row.next_mileage = data.next_mileage
    row.next_date = data.next_date
    row.attachment_url = data.attachment_url
    row.remark = data.remark

    if data.current_mileage > vehicle.current_mileage:
        vehicle.current_mileage = data.current_mileage

    db.commit()
    return {"message": "维保记录修改成功"}


@app.delete("/api/maintenances/{record_id}")
def maintenance_delete(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    row = db.get(MaintenanceRecord, record_id)

    if not row:
        raise HTTPException(status_code=404, detail="维保记录不存在")

    db.delete(row)
    db.commit()
    return {"message": "维保记录删除成功"}


@app.post("/api/maintenances/batch-delete")
def maintenance_batch_delete(
    data: BatchDeleteIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    deleted = 0
    for record_id in data.ids:
        row = db.get(MaintenanceRecord, record_id)
        if row:
            db.delete(row)
            deleted += 1
    db.commit()
    return {"message": f"已删除 {deleted} 条维保记录", "deleted": deleted}


# =========================
# 违章管理
# =========================

@app.get("/api/violations")
def violation_list(
    vehicle_id: int | None = None,
    status: str | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(ViolationRecord, Vehicle.plate_no)
        .join(Vehicle, Vehicle.id == ViolationRecord.vehicle_id)
    )

    if vehicle_id:
        stmt = stmt.where(ViolationRecord.vehicle_id == vehicle_id)

    if status:
        stmt = stmt.where(ViolationRecord.status == status)

    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                Vehicle.plate_no.like(like),
                ViolationRecord.violation_type.like(like),
                ViolationRecord.location.like(like),
            )
        )

    stmt = apply_vehicle_scope(user, stmt, join_project=True)

    rows = db.execute(
        stmt.order_by(ViolationRecord.id.asc())
    ).all()
    items = [
        {
            "id": row.id,
            "vehicle_id": row.vehicle_id,
            "plate_no": plate_no,
            "violation_date": row.violation_date,
            "violation_type": row.violation_type,
            "location": row.location,
            "attachment_url": row.attachment_url,
            "points": row.points,
            "fine_amount": float(row.fine_amount),
            "status": row.status,
            "handler_name": row.handler_name,
            "remark": row.remark,
            "created_at": row.created_at,
        }
        for row, plate_no in rows
    ]
    return items


@app.post("/api/violations")
def violation_create(
    data: ViolationIn,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            "ADMIN",
            "VEHICLE_MANAGER",
            "PROJECT_MANAGER",
            "DRIVER",
        )
    ),
):
    ensure_driver_vehicle(user, data.vehicle_id)

    vehicle = db.get(Vehicle, data.vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="车辆不存在")

    row = ViolationRecord(**data.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "id": row.id,
        "message": "违章记录保存成功",
    }


@app.put("/api/violations/{record_id}")
def violation_update(
    record_id: int,
    data: ViolationIn,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            "ADMIN",
            "VEHICLE_MANAGER",
            "PROJECT_MANAGER",
            "FINANCE",
        )
    ),
):
    row = db.get(ViolationRecord, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="违章记录不存在")

    vehicle = db.get(Vehicle, data.vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="车辆不存在")

    row.vehicle_id = data.vehicle_id
    row.violation_date = data.violation_date
    row.violation_type = data.violation_type
    row.location = data.location
    row.attachment_url = data.attachment_url
    row.points = data.points
    row.fine_amount = data.fine_amount
    row.status = data.status
    row.handler_name = data.handler_name
    row.remark = data.remark
    db.commit()

    return {"message": "违章记录修改成功"}


@app.delete("/api/violations/{record_id}")
def violation_delete(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    row = db.get(ViolationRecord, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="违章记录不存在")

    db.delete(row)
    db.commit()
    return {"message": "违章记录删除成功"}


@app.post("/api/violations/batch-delete")
def violation_batch_delete(
    data: BatchDeleteIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    deleted = 0
    for record_id in data.ids:
        row = db.get(ViolationRecord, record_id)
        if row:
            db.delete(row)
            deleted += 1
    db.commit()
    return {"message": f"已删除 {deleted} 条违章记录", "deleted": deleted}


# =========================
# 油费管理
# =========================

@app.get("/api/fuels")
def fuel_list(
    vehicle_id: int | None = None,
    month: str | None = None,
    exclude_used: bool = False,
    keyword: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(FuelRecord, Vehicle.plate_no)
        .join(Vehicle, Vehicle.id == FuelRecord.vehicle_id)
    )

    if vehicle_id:
        stmt = stmt.where(FuelRecord.vehicle_id == vehicle_id)

    if month:
        stmt = stmt.where(
            func.date_format(FuelRecord.fuel_date, "%Y-%m") == month
        )

    if exclude_used:
        stmt = stmt.where(
            FuelRecord.id.not_in(
                select(ReimbursementDetail.source_id).where(
                    ReimbursementDetail.source_type == "FUEL",
                    ReimbursementDetail.source_id.is_not(None),
                )
            )
        )

    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                Vehicle.plate_no.like(like),
                FuelRecord.station.like(like),
                FuelRecord.invoice_no.like(like),
            )
        )

    stmt = apply_vehicle_scope(user, stmt, join_project=True)

    rows = db.execute(
        stmt.order_by(FuelRecord.id.asc())
    ).all()
    items = [
        {
            "id": row.id,
            "vehicle_id": row.vehicle_id,
            "plate_no": plate_no,
            "fuel_date": row.fuel_date,
            "liters": float(row.liters),
            "unit_price": float(row.unit_price),
            "total_amount": float(row.total_amount),
            "mileage": (
                float(row.mileage)
                if row.mileage is not None else None
            ),
            "station": row.station,
            "invoice_no": row.invoice_no,
            "attachment_url": row.attachment_url,
            "remark": row.remark,
            "created_at": row.created_at,
        }
        for row, plate_no in rows
    ]
    return items


@app.post("/api/fuels")
def fuel_create(
    data: FuelIn,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            "ADMIN",
            "VEHICLE_MANAGER",
            "PROJECT_MANAGER",
            "DRIVER",
        )
    ),
):
    ensure_driver_vehicle(user, data.vehicle_id)

    vehicle = db.get(Vehicle, data.vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="车辆不存在")

    total = data.total_amount
    if total <= 0:
        total = data.liters * data.unit_price

    row = FuelRecord(
        **data.model_dump(exclude={"total_amount"}),
        total_amount=total,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "id": row.id,
        "total_amount": float(row.total_amount),
        "message": "油费记录保存成功",
    }


@app.put("/api/fuels/{record_id}")
def fuel_update(
    record_id: int,
    data: FuelIn,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            "ADMIN",
            "VEHICLE_MANAGER",
            "PROJECT_MANAGER",
        )
    ),
):
    row = db.get(FuelRecord, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="油费记录不存在")

    vehicle = db.get(Vehicle, data.vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="车辆不存在")

    total = data.total_amount
    if total <= 0:
        total = data.liters * data.unit_price

    row.vehicle_id = data.vehicle_id
    row.fuel_date = data.fuel_date
    row.liters = data.liters
    row.unit_price = data.unit_price
    row.total_amount = total
    row.mileage = data.mileage
    row.station = data.station
    row.invoice_no = data.invoice_no
    row.attachment_url = data.attachment_url
    row.remark = data.remark
    db.commit()

    return {"message": "油费记录修改成功"}


@app.delete("/api/fuels/{record_id}")
def fuel_delete(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    row = db.get(FuelRecord, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="油费记录不存在")

    db.delete(row)
    db.commit()
    return {"message": "油费记录删除成功"}


@app.post("/api/fuels/batch-delete")
def fuel_batch_delete(
    data: BatchDeleteIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    deleted = 0
    for record_id in data.ids:
        row = db.get(FuelRecord, record_id)
        if row:
            db.delete(row)
            deleted += 1
    db.commit()
    return {"message": f"已删除 {deleted} 条油费记录", "deleted": deleted}


# =========================
# 焊机档案
# =========================

def welder_to_dict(welder: Welder):
    return {
        "id": welder.id,
        "welder_code": welder.welder_code,
        "welder_no": welder.welder_no,
        "location": welder.location,
        "project_id": welder.project_id,
        "project_name": (
            welder.project.name if welder.project else None
        ),
        "project_manager": (
            welder.project.manager_name if welder.project else None
        ),
        "project_location": (
            welder.project.location if welder.project else None
        ),
        "project_enabled": (
            welder.project.enabled if welder.project else True
        ),
        "welder_manager": welder.welder_manager,
        "status": welder.status,
        "remark": welder.remark,
        "created_at": welder.created_at,
        "updated_at": welder.updated_at,
    }


@app.get("/api/welders")
def welder_list(
    keyword: str | None = None,
    project_id: int | None = None,
    status: str | None = None,
    project_manager: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ensure_not_driver(user)
    stmt = select(Welder)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                Welder.welder_code.like(like),
                Welder.welder_no.like(like),
                Welder.location.like(like),
                Welder.welder_manager.like(like),
            )
        )
    if project_id:
        stmt = stmt.where(Welder.project_id == project_id)
    if status:
        stmt = stmt.where(Welder.status == status)
    if project_manager:
        stmt = stmt.join(
            Project,
            Project.id == Welder.project_id,
        ).where(Project.manager_name == project_manager)

    rows = db.scalars(stmt.order_by(Welder.id.asc())).all()
    items = [welder_to_dict(row) for row in rows]
    return items


@app.post("/api/welders")
def welder_create(
    data: WelderIn,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            "ADMIN",
            "VEHICLE_MANAGER",
            "PROJECT_MANAGER",
        )
    ),
):
    welder_code = data.welder_code.strip()
    if not welder_code:
        max_id = db.scalar(select(func.max(Welder.id))) or 0
        welder_code = f"HJ-{max_id + 1:06d}"
        while db.scalar(
            select(Welder).where(Welder.welder_code == welder_code)
        ):
            max_id += 1
            welder_code = f"HJ-{max_id + 1:06d}"

    if db.scalar(
        select(Welder).where(Welder.welder_code == welder_code)
    ):
        raise HTTPException(status_code=400, detail="焊机编码已存在")
    if db.scalar(
        select(Welder).where(Welder.welder_no == data.welder_no)
    ):
        raise HTTPException(status_code=400, detail="焊机编号已存在")

    row = Welder(
        **data.model_dump(exclude={"welder_code"}),
        welder_code=welder_code,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return welder_to_dict(row)


@app.put("/api/welders/{welder_id}")
def welder_update(
    welder_id: int,
    data: WelderIn,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            "ADMIN",
            "VEHICLE_MANAGER",
            "PROJECT_MANAGER",
        )
    ),
):
    row = db.get(Welder, welder_id)
    if not row:
        raise HTTPException(status_code=404, detail="焊机不存在")

    if user.role == "PROJECT_MANAGER" and not project_owned_by_user(
        user, row.project
    ):
        raise HTTPException(
            status_code=403,
            detail="只能编辑自己项目下的焊机",
        )

    if db.scalar(
        select(Welder).where(
            Welder.welder_code == data.welder_code,
            Welder.id != welder_id,
        )
    ):
        raise HTTPException(status_code=400, detail="焊机编码已存在")
    if db.scalar(
        select(Welder).where(
            Welder.welder_no == data.welder_no,
            Welder.id != welder_id,
        )
    ):
        raise HTTPException(status_code=400, detail="焊机编号已存在")

    row.welder_code = data.welder_code
    row.welder_no = data.welder_no
    row.location = data.location
    row.project_id = data.project_id
    row.welder_manager = data.welder_manager
    row.status = data.status
    row.remark = data.remark
    db.commit()
    db.refresh(row)
    return welder_to_dict(row)


def renumber_welders(db: Session) -> None:
    old_ids = db.scalars(
        select(Welder.id).order_by(Welder.id.asc())
    ).all()
    if not old_ids:
        db.execute(text("ALTER TABLE welder_archive AUTO_INCREMENT = 1"))
        return

    mapping = {
        old_id: new_id
        for new_id, old_id in enumerate(old_ids, start=1)
    }
    db.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    try:
        for old_id in mapping:
            db.execute(
                text(
                    "UPDATE welder_archive SET id = id + 1000000 "
                    "WHERE id = :old_id"
                ),
                {"old_id": old_id},
            )
        for old_id, new_id in mapping.items():
            db.execute(
                text(
                    "UPDATE welder_archive SET id = :new_id, "
                    "welder_code = :code "
                    "WHERE id = :old_id + 1000000"
                ),
                {
                    "new_id": new_id,
                    "code": f"HJ-{new_id:06d}",
                    "old_id": old_id,
                },
            )
            db.execute(
                text(
                    "UPDATE welder_inspection SET welder_id = :new_id "
                    "WHERE welder_id = :old_id"
                ),
                {"new_id": new_id, "old_id": old_id},
            )
    finally:
        db.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    db.execute(
        text(
            f"ALTER TABLE welder_archive AUTO_INCREMENT = "
            f"{len(mapping) + 1}"
        )
    )


@app.delete("/api/welders/{welder_id}")
def welder_delete(
    welder_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    row = db.get(Welder, welder_id)
    if not row:
        raise HTTPException(status_code=404, detail="焊机不存在")
    db.delete(row)
    renumber_welders(db)
    db.commit()
    return {"message": "焊机删除成功"}


@app.post("/api/welders/batch-delete")
def welder_batch_delete(
    data: BatchDeleteIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    deleted = 0
    for welder_id in data.ids:
        row = db.get(Welder, welder_id)
        if row:
            db.delete(row)
            deleted += 1
    renumber_welders(db)
    db.commit()
    return {"message": f"已删除 {deleted} 台焊机", "deleted": deleted}


# =========================
# 焊机巡检管理
# =========================

def inspection_to_dict(inspection: WelderInspection):
    return {
        "id": inspection.id,
        "welder_id": inspection.welder_id,
        "welder_no": (
            inspection.welder.welder_no if inspection.welder else None
        ),
        "location": inspection.location,
        "project_name": (
            inspection.welder.project.name
            if inspection.welder and inspection.welder.project
            else None
        ),
        "project_manager": (
            inspection.welder.project.manager_name
            if inspection.welder and inspection.welder.project
            else None
        ),
        "welder_manager": (
            inspection.welder.welder_manager
            if inspection.welder
            else None
        ),
        "inspection_date": inspection.inspection_date,
        "inspection_type": inspection.inspection_type,
        "completed": inspection.completed,
        "attachment_url": inspection.attachment_url,
        "operator_name": inspection.operator_name,
        "device_status": inspection.device_status,
        "remark": inspection.remark,
        "repair_note": inspection.repair_note,
        "created_at": inspection.created_at,
    }


@app.get("/api/welder-inspections")
def inspection_list(
    welder_id: int | None = None,
    month: str | None = None,
    keyword: str | None = None,
    fault: bool | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ensure_not_driver(user)
    stmt = (
        select(WelderInspection)
        .join(Welder, Welder.id == WelderInspection.welder_id)
    )
    if welder_id:
        stmt = stmt.where(WelderInspection.welder_id == welder_id)
    if month:
        stmt = stmt.where(
            func.date_format(
                WelderInspection.inspection_date, "%Y-%m"
            )
            == month
        )
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                Welder.welder_no.like(like),
                WelderInspection.operator_name.like(like),
                WelderInspection.remark.like(like),
                WelderInspection.repair_note.like(like),
            )
        )
    if fault is True:
        stmt = stmt.where(WelderInspection.device_status == "FAULT")
    if fault is False:
        stmt = stmt.where(WelderInspection.device_status == "NORMAL")

    rows = db.scalars(
        stmt.order_by(WelderInspection.id.asc())
    ).all()
    items = [inspection_to_dict(row) for row in rows]
    return items


@app.post("/api/welder-inspections")
def inspection_create(
    data: WelderInspectionIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    welder = db.get(Welder, data.welder_id)
    if not welder:
        raise HTTPException(status_code=404, detail="焊机不存在")

    row = WelderInspection(**data.model_dump())
    db.add(row)
    if data.device_status == "FAULT":
        welder.status = "FAULT"
    db.commit()
    db.refresh(row)
    return inspection_to_dict(row)


@app.put("/api/welder-inspections/{record_id}")
def inspection_update(
    record_id: int,
    data: WelderInspectionIn,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            "ADMIN",
            "VEHICLE_MANAGER",
            "PROJECT_MANAGER",
            "FINANCE",
        )
    ),
):
    row = db.get(WelderInspection, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="巡检单不存在")
    welder = db.get(Welder, data.welder_id)
    if not welder:
        raise HTTPException(status_code=404, detail="焊机不存在")

    row.welder_id = data.welder_id
    row.location = data.location
    row.inspection_date = data.inspection_date
    row.inspection_type = data.inspection_type
    row.completed = data.completed
    row.attachment_url = data.attachment_url
    row.operator_name = data.operator_name
    row.device_status = data.device_status
    row.remark = data.remark
    if data.device_status == "FAULT":
        welder.status = "FAULT"
    db.commit()
    db.refresh(row)
    return inspection_to_dict(row)


@app.post("/api/welder-inspections/{record_id}/repair")
def inspection_repair(
    record_id: int,
    data: RepairIn,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            "ADMIN",
            "VEHICLE_MANAGER",
            "PROJECT_MANAGER",
            "FINANCE",
        )
    ),
):
    row = db.get(WelderInspection, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="巡检单不存在")

    row.repair_note = data.repair_note
    existing = row.remark or ""
    note = f"维修说明：{data.repair_note}"
    row.remark = (
        f"{existing}\n{note}"
        if existing and note not in existing
        else note
        if note not in existing
        else existing
    )
    if row.welder:
        row.welder.status = "ONLINE"
    db.commit()
    return inspection_to_dict(row)


@app.delete("/api/welder-inspections/{record_id}")
def inspection_delete(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    row = db.get(WelderInspection, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="巡检单不存在")
    db.delete(row)
    db.commit()
    return {"message": "巡检单删除成功"}


@app.post("/api/welder-inspections/batch-delete")
def inspection_batch_delete(
    data: BatchDeleteIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    deleted = 0
    for record_id in data.ids:
        row = db.get(WelderInspection, record_id)
        if row:
            db.delete(row)
            deleted += 1
    db.commit()
    return {"message": f"已删除 {deleted} 条巡检单", "deleted": deleted}


# =========================
# 报销管理
# =========================

@app.get("/api/reimbursements")
def reimbursement_list(
    month: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if user.role == "DRIVER":
        raise HTTPException(
            status_code=403,
            detail="驾驶员无报销管理权限",
        )

    stmt = (
        select(Reimbursement, Vehicle.plate_no)
        .join(Vehicle, Vehicle.id == Reimbursement.vehicle_id)
    )

    if month:
        stmt = stmt.where(
            Reimbursement.reimbursement_month == month
        )

    if status:
        stmt = stmt.where(Reimbursement.status == status)

    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                Reimbursement.reimbursement_no.like(like),
                Vehicle.plate_no.like(like),
                Reimbursement.applicant_name.like(like),
            )
        )

    stmt = apply_vehicle_scope(user, stmt, join_project=True)

    rows = db.execute(
        stmt.order_by(Reimbursement.id.asc())
    ).all()
    items = [
        {
            "id": row.id,
            "reimbursement_no": row.reimbursement_no,
            "reimbursement_month": row.reimbursement_month,
            "vehicle_id": row.vehicle_id,
            "plate_no": plate_no,
            "project_id": row.project_id,
            "applicant_id": row.applicant_id,
            "applicant_name": row.applicant_name,
            "total_amount": float(row.total_amount),
            "status": row.status,
            "reject_reason": row.reject_reason,
            "created_at": row.created_at
        }
        for row, plate_no in rows
    ]
    return items


@app.get("/api/reimbursements/{record_id}")
def reimbursement_detail(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == "DRIVER":
        raise HTTPException(
            status_code=403,
            detail="驾驶员无报销管理权限",
        )

    row = db.get(Reimbursement, record_id)

    if not row:
        raise HTTPException(status_code=404, detail="报销单不存在")

    ensure_driver_vehicle(user, row.vehicle_id)

    if (
        user.role == "DRIVER"
        and row.applicant_id != user.id
    ):
        raise HTTPException(status_code=403, detail="无权查看该报销单")

    vehicle = db.get(Vehicle, row.vehicle_id)
    project = db.get(Project, row.project_id) if row.project_id else None

    return {
        "id": row.id,
        "reimbursement_no": row.reimbursement_no,
        "reimbursement_month": row.reimbursement_month,
        "vehicle_id": row.vehicle_id,
        "plate_no": vehicle.plate_no if vehicle else None,
        "project_id": row.project_id,
        "project_name": project.name if project else None,
        "applicant_id": row.applicant_id,
        "applicant_name": row.applicant_name,
        "total_amount": float(row.total_amount),
        "status": row.status,
        "reject_reason": row.reject_reason,
        "remark": row.remark,
        "created_at": row.created_at,
        "submitted_at": row.submitted_at,
        "approved_at": row.approved_at,
        "details": [
            {
                "id": detail.id,
                "expense_type": detail.expense_type,
                "expense_date": detail.expense_date,
                "amount": float(detail.amount),
                "related_mileage": (
                    float(detail.related_mileage)
                    if detail.related_mileage is not None
                    else None
                ),
                "invoice_no": detail.invoice_no,
                "description": detail.description,
                "attachment_url": detail.attachment_url,
                "source_type": detail.source_type,
                "source_id": detail.source_id,
            }
            for detail in row.details
        ],
        "approvals": [
            {
                "id": approval.id,
                "approver_name": approval.approver_name,
                "action": approval.action,
                "opinion": approval.opinion,
                "created_at": approval.created_at,
            }
            for approval in row.approvals
        ],
    }


@app.post("/api/reimbursements")
def reimbursement_create(
    data: ReimbursementIn,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            "ADMIN",
            "VEHICLE_MANAGER",
            "PROJECT_MANAGER",
            "FINANCE",
        )
    ),
):
    vehicle = db.get(Vehicle, data.vehicle_id)

    if not vehicle:
        raise HTTPException(status_code=404, detail="车辆不存在")

    ensure_driver_vehicle(user, data.vehicle_id)

    if not data.details:
        raise HTTPException(status_code=400, detail="至少填写一条费用")

    prepared_details = []
    for detail in data.details:
        if detail.source_type and detail.source_id:
            if detail.source_type == "FUEL":
                source = db.get(FuelRecord, detail.source_id)
                if (
                    source is None
                    or source.vehicle_id != data.vehicle_id
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="关联的油费记录不存在或不属于该车辆",
                    )
                if (
                    source.fuel_date.strftime("%Y-%m")
                    != data.reimbursement_month
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="关联油费记录不在报销月份内",
                    )
                ensure_reimbursement_source_available(
                    db, "FUEL", source.id
                )
                prepared_details.append(
                    {
                        "expense_type": "FUEL",
                        "expense_date": source.fuel_date,
                        "amount": source.total_amount,
                        "related_mileage": source.mileage,
                        "invoice_no": source.invoice_no,
                        "description": (
                            detail.description
                            or f"油费记录 {source.fuel_date}"
                        ),
                        "attachment_url": (
                            source.attachment_url
                            or detail.attachment_url
                        ),
                        "source_type": "FUEL",
                        "source_id": source.id,
                    }
                )
            elif detail.source_type == "MILEAGE":
                source = db.get(MileageRecord, detail.source_id)
                if (
                    source is None
                    or source.vehicle_id != data.vehicle_id
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="关联的里程记录不存在或不属于该车辆",
                    )
                if (
                    source.trip_date.strftime("%Y-%m")
                    != data.reimbursement_month
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="关联里程记录不在报销月份内",
                    )
                if source.status != "CLOSED":
                    raise HTTPException(
                        status_code=400,
                        detail="只有已收车的里程记录可以申报里程补助",
                    )
                ensure_reimbursement_source_available(
                    db, "MILEAGE", source.id
                )
                amount = source.distance * Decimal("0.2")
                prepared_details.append(
                    {
                        "expense_type": "MILEAGE_ALLOWANCE",
                        "expense_date": source.trip_date.date(),
                        "amount": amount,
                        "related_mileage": source.distance,
                        "invoice_no": None,
                        "description": (
                            detail.description
                            or f"里程补助 {source.trip_date}"
                        ),
                        "attachment_url": (
                            ",".join(
                                filter(
                                    None,
                                    [
                                        source.out_photo,
                                        source.in_photo,
                                    ],
                                )
                            )
                            or detail.attachment_url
                        ),
                        "source_type": "MILEAGE",
                        "source_id": source.id,
                    }
                )
            else:
                source = db.get(MaintenanceRecord, detail.source_id)
                if (
                    source is None
                    or source.vehicle_id != data.vehicle_id
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="关联的维保记录不存在或不属于该车辆",
                    )
                if (
                    source.maintenance_date.strftime("%Y-%m")
                    != data.reimbursement_month
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="关联维保记录不在报销月份内",
                    )
                ensure_reimbursement_source_available(
                    db, "MAINTENANCE", source.id
                )
                prepared_details.append(
                    {
                        "expense_type": "MAINTENANCE",
                        "expense_date": source.maintenance_date,
                        "amount": source.amount,
                        "related_mileage": source.current_mileage,
                        "invoice_no": None,
                        "description": (
                            detail.description or source.items
                        ),
                        "attachment_url": (
                            source.attachment_url
                            or detail.attachment_url
                        ),
                        "source_type": "MAINTENANCE",
                        "source_id": source.id,
                    }
                )
        else:
            if detail.amount <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="额外费用金额必须大于0",
                )
            if not detail.attachment_url:
                raise HTTPException(
                    status_code=400,
                    detail="额外费用必须上传图片证明",
                )
            prepared_details.append(detail.model_dump())

    total = sum(
        (Decimal(str(item["amount"])) for item in prepared_details),
        Decimal("0"),
    )

    sequence = db.scalar(
        select(func.count(Reimbursement.id)).where(
            Reimbursement.reimbursement_month ==
            data.reimbursement_month
        )
    ) or 0

    reimbursement_no = (
        f"BX-{data.reimbursement_month.replace('-', '')}-"
        f"{sequence + 1:04d}"
    )

    row = Reimbursement(
        reimbursement_no=reimbursement_no,
        reimbursement_month=data.reimbursement_month,
        vehicle_id=data.vehicle_id,
        project_id=data.project_id,
        applicant_id=user.id,
        applicant_name=user.real_name,
        total_amount=total,
        status="DRAFT",
        remark=data.remark
    )

    db.add(row)
    db.flush()

    for detail in prepared_details:
        db.add(
            ReimbursementDetail(
                reimbursement_id=row.id,
                **detail,
            )
        )

    db.commit()
    db.refresh(row)

    return {
        "id": row.id,
        "reimbursement_no": row.reimbursement_no,
        "total_amount": float(row.total_amount),
        "message": "报销单创建成功"
    }


@app.delete("/api/reimbursements/{record_id}")
def reimbursement_delete(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    row = db.get(Reimbursement, record_id)

    if not row:
        raise HTTPException(status_code=404, detail="报销单不存在")

    db.delete(row)
    db.commit()
    return {"message": "报销单删除成功"}


@app.post("/api/reimbursements/batch-delete")
def reimbursement_batch_delete(
    data: BatchDeleteIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    deleted = 0
    for record_id in data.ids:
        row = db.get(Reimbursement, record_id)
        if row:
            db.delete(row)
            deleted += 1
    db.commit()
    return {"message": f"已删除 {deleted} 张报销单", "deleted": deleted}


@app.post("/api/reimbursements/batch-approve")
def reimbursement_batch_approve(
    data: BatchApproveIn,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles("ADMIN", "PROJECT_MANAGER", "FINANCE")
    ),
):
    approved = 0
    skipped = 0
    for record_id in data.ids:
        row = db.get(Reimbursement, record_id)
        if not row:
            skipped += 1
            continue

        if (
            row.status == "SUBMITTED"
            and user.role in ("ADMIN", "PROJECT_MANAGER")
        ):
            row.status = "PROJECT_APPROVED"
            db.add(
                ApprovalRecord(
                    reimbursement_id=row.id,
                    approver_id=user.id,
                    approver_name=user.real_name,
                    action="PROJECT_APPROVE",
                    opinion=data.opinion,
                )
            )
            approved += 1
        elif (
            row.status == "PROJECT_APPROVED"
            and user.role in ("ADMIN", "FINANCE")
        ):
            row.status = "APPROVED"
            row.approved_at = datetime.now()
            db.add(
                ApprovalRecord(
                    reimbursement_id=row.id,
                    approver_id=user.id,
                    approver_name=user.real_name,
                    action="FINANCE_APPROVE",
                    opinion=data.opinion,
                )
            )
            approved += 1
        else:
            skipped += 1

    db.commit()
    return {
        "message": f"批量审核完成：通过 {approved} 张，跳过 {skipped} 张",
        "approved": approved,
        "skipped": skipped,
    }


@app.post("/api/reimbursements/{record_id}/submit")
def reimbursement_submit(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            "ADMIN",
            "VEHICLE_MANAGER",
            "PROJECT_MANAGER",
            "FINANCE",
        )
    ),
):
    row = db.get(Reimbursement, record_id)

    if not row:
        raise HTTPException(status_code=404, detail="报销单不存在")

    ensure_driver_vehicle(user, row.vehicle_id)

    if row.applicant_id != user.id and user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="不能提交他人报销单")

    if row.status not in {"DRAFT", "REJECTED"}:
        raise HTTPException(status_code=400, detail="当前状态不能提交")

    row.status = "SUBMITTED"
    row.reject_reason = None
    row.submitted_at = datetime.now()

    db.add(
        ApprovalRecord(
            reimbursement_id=row.id,
            approver_id=user.id,
            approver_name=user.real_name,
            action="SUBMIT",
            opinion="提交报销"
        )
    )

    db.commit()

    return {"message": "报销单提交成功"}


@app.post("/api/reimbursements/{record_id}/project-approve")
def project_approve(
    record_id: int,
    data: ApprovalIn,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles("ADMIN", "PROJECT_MANAGER")
    )
):
    row = db.get(Reimbursement, record_id)

    if not row:
        raise HTTPException(status_code=404, detail="报销单不存在")

    if row.status != "SUBMITTED":
        raise HTTPException(status_code=400, detail="报销状态不正确")

    row.status = "PROJECT_APPROVED"

    db.add(
        ApprovalRecord(
            reimbursement_id=row.id,
            approver_id=user.id,
            approver_name=user.real_name,
            action="PROJECT_APPROVE",
            opinion=data.opinion
        )
    )

    db.commit()

    return {"message": "项目审核通过"}


@app.post("/api/reimbursements/{record_id}/finance-approve")
def finance_approve(
    record_id: int,
    data: ApprovalIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN", "FINANCE"))
):
    row = db.get(Reimbursement, record_id)

    if not row:
        raise HTTPException(status_code=404, detail="报销单不存在")

    if row.status != "PROJECT_APPROVED":
        raise HTTPException(status_code=400, detail="报销状态不正确")

    row.status = "APPROVED"
    row.approved_at = datetime.now()

    db.add(
        ApprovalRecord(
            reimbursement_id=row.id,
            approver_id=user.id,
            approver_name=user.real_name,
            action="FINANCE_APPROVE",
            opinion=data.opinion
        )
    )

    db.commit()

    return {"message": "财务审核通过"}


@app.post("/api/reimbursements/{record_id}/reject")
def reimbursement_reject(
    record_id: int,
    data: RejectIn,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            "ADMIN",
            "PROJECT_MANAGER",
            "FINANCE"
        )
    )
):
    row = db.get(Reimbursement, record_id)

    if not row:
        raise HTTPException(status_code=404, detail="报销单不存在")

    if row.status not in {"SUBMITTED", "PROJECT_APPROVED"}:
        raise HTTPException(status_code=400, detail="当前状态不能退回")

    row.status = "REJECTED"
    row.reject_reason = data.reason

    db.add(
        ApprovalRecord(
            reimbursement_id=row.id,
            approver_id=user.id,
            approver_name=user.real_name,
            action="REJECT",
            opinion=data.reason
        )
    )

    db.commit()

    return {"message": "报销单已退回"}


# =========================
# 月度仪表盘
# =========================

@app.get("/api/dashboard")
def dashboard(
    month: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    mileage_stmt = (
        select(
            func.coalesce(func.sum(MileageRecord.distance), 0)
        )
        .select_from(MileageRecord)
        .join(Vehicle, Vehicle.id == MileageRecord.vehicle_id)
        .where(
            func.date_format(
                MileageRecord.trip_date, "%Y-%m"
            ) == month,
            MileageRecord.status == "CLOSED",
        )
    )
    total_mileage = db.scalar(
        apply_vehicle_scope(
            user, mileage_stmt, join_project=True
        )
    )

    reimb_stmt = (
        select(
            func.coalesce(func.sum(Reimbursement.total_amount), 0)
        )
        .select_from(Reimbursement)
        .join(Vehicle, Vehicle.id == Reimbursement.vehicle_id)
        .where(
            Reimbursement.reimbursement_month == month,
            Reimbursement.status == "APPROVED",
        )
    )
    total_reimbursement = db.scalar(
        apply_vehicle_scope(
            user, reimb_stmt, join_project=True
        )
    )

    expense_stmt = (
        select(
            ReimbursementDetail.expense_type,
            func.coalesce(
                func.sum(ReimbursementDetail.amount), 0
            ),
        )
        .select_from(ReimbursementDetail)
        .join(
            Reimbursement,
            Reimbursement.id
            == ReimbursementDetail.reimbursement_id,
        )
        .join(Vehicle, Vehicle.id == Reimbursement.vehicle_id)
        .where(
            Reimbursement.reimbursement_month == month,
            Reimbursement.status == "APPROVED",
        )
        .group_by(ReimbursementDetail.expense_type)
    )
    expense_rows = db.execute(
        apply_vehicle_scope(
            user, expense_stmt, join_project=True
        )
    ).all()

    expense_map = {
        expense_type: float(amount)
        for expense_type, amount in expense_rows
    }

    vehicle_stmt = select(func.count(Vehicle.id))
    vehicle_count = db.scalar(
        apply_vehicle_scope(
            user, vehicle_stmt, join_project=True
        )
    ) or 0

    active_stmt = select(func.count(Vehicle.id)).where(
        Vehicle.status == "ACTIVE"
    )
    active_vehicle_count = db.scalar(
        apply_vehicle_scope(
            user, active_stmt, join_project=True
        )
    ) or 0

    pending_stmt = (
        select(func.count(Reimbursement.id))
        .select_from(Reimbursement)
        .join(Vehicle, Vehicle.id == Reimbursement.vehicle_id)
        .where(
            Reimbursement.status.in_(
                ["SUBMITTED", "PROJECT_APPROVED"]
            )
        )
    )
    pending_count = db.scalar(
        apply_vehicle_scope(
            user, pending_stmt, join_project=True
        )
    ) or 0

    return {
        "month": month,
        "vehicle_count": vehicle_count,
        "active_vehicle_count": active_vehicle_count,
        "total_mileage": float(total_mileage or 0),
        "total_reimbursement": float(total_reimbursement or 0),
        "fuel_amount": expense_map.get("FUEL", 0),
        "maintenance_amount": expense_map.get("MAINTENANCE", 0),
        "toll_amount": expense_map.get("TOLL", 0),
        "parking_amount": expense_map.get("PARKING", 0),
        "other_amount": expense_map.get("OTHER", 0),
        "mileage_allowance_amount": expense_map.get(
            "MILEAGE_ALLOWANCE", 0
        ),
        "pending_reimbursement_count": pending_count
    }


# =========================
# 前端静态资源（生产模式）
# =========================

if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=assets_dir),
            name="assets",
        )

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        if full_path.startswith(("api/", "uploads/")):
            raise HTTPException(status_code=404)

        target = FRONTEND_DIST / full_path
        if full_path and target.is_file():
            return FileResponse(target)

        return FileResponse(FRONTEND_DIST / "index.html")
