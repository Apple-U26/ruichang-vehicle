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
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from urllib.parse import quote

from app.routers import auth
from app.config import settings
from app.database import Base, engine, ensure_column, get_db
from app.excel_service import export_workbook, import_workbook
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
    ApprovalRecord
)
from app.schemas import (
    ApprovalIn,
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
    UserCreateIn,
    UserUpdateIn,
    VehicleIn,
)
from app.security import (
    hash_password,
    get_current_user,
    require_roles
)


Base.metadata.create_all(bind=engine)


ensure_column("sys_user", "vehicle_id", "BIGINT NULL")
ensure_column("violation_record", "attachment_url", "VARCHAR(500)")

os.makedirs(settings.upload_dir, exist_ok=True)

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
    StaticFiles(directory=settings.upload_dir),
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
    rows = db.scalars(
        select(User).order_by(User.id.desc())
    ).all()

    return [user_to_dict(row) for row in rows]


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


@app.post("/api/excel/import", tags=["Excel"])
async def excel_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles("ADMIN", "VEHICLE_MANAGER")
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
    user: User = Depends(get_current_user),   # 可根据需要限制权限
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
    path = os.path.join(settings.upload_dir, filename)

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
    rows = db.scalars(
        select(Project).order_by(Project.id.desc())
    ).all()

    return [
        {
            "id": row.id,
            "name": row.name,
            "manager_name": row.manager_name,
            "enabled": row.enabled,
            "remark": row.remark
        }
        for row in rows
    ]


@app.post("/api/projects")
def project_create(
    data: ProjectIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN", "VEHICLE_MANAGER"))
):
    exists = db.scalar(
        select(Project).where(Project.name == data.name)
    )
    if exists:
        raise HTTPException(status_code=400, detail="项目名称已存在")

    row = Project(**data.model_dump())
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
        require_roles("ADMIN", "VEHICLE_MANAGER")
    ),
):
    row = db.get(Project, project_id)

    if not row:
        raise HTTPException(status_code=404, detail="项目不存在")

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
    row.enabled = data.enabled
    row.remark = data.remark
    db.commit()

    return {"message": "项目修改成功"}


@app.delete("/api/projects/{project_id}")
def project_delete(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles("ADMIN", "VEHICLE_MANAGER")
    ),
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

    if user.role == "DRIVER" and user.vehicle_id:
        stmt = stmt.where(Vehicle.id == user.vehicle_id)

    rows = db.scalars(
        stmt.order_by(Vehicle.id.desc())
    ).all()

    return [vehicle_to_dict(row) for row in rows]


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
    user: User = Depends(require_roles("ADMIN", "VEHICLE_MANAGER"))
):
    plate_no = data.plate_no.strip().upper()

    exists = db.scalar(
        select(Vehicle).where(Vehicle.plate_no == plate_no)
    )
    if exists:
        raise HTTPException(status_code=400, detail="车牌号已经存在")

    count = db.scalar(select(func.count(Vehicle.id))) or 0
    vehicle_code = f"CL-{count + 1:06d}"

    row = Vehicle(
        vehicle_code=vehicle_code,
        plate_no=plate_no,
        project_id=data.project_id,
        project_manager=data.project_manager,
        vehicle_manager=data.vehicle_manager,
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
    user: User = Depends(require_roles("ADMIN", "VEHICLE_MANAGER"))
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

    row.plate_no = data.plate_no.strip().upper()
    row.project_id = data.project_id
    row.project_manager = data.project_manager
    row.vehicle_manager = data.vehicle_manager
    row.ownership = data.ownership
    row.status = data.status
    row.vehicle_age = data.vehicle_age
    row.violation_info = data.violation_info
    row.remark = data.remark

    db.commit()

    return {"message": "车辆修改成功"}


@app.delete("/api/vehicles/{vehicle_id}")
def vehicle_delete(
    vehicle_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles("ADMIN", "VEHICLE_MANAGER")
    ),
):
    row = db.get(Vehicle, vehicle_id)

    if not row:
        raise HTTPException(status_code=404, detail="车辆不存在")

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
    db.commit()
    return {"message": "车辆及其业务记录已删除"}


# =========================
# 出车和收车
# =========================

@app.get("/api/mileages")
def mileage_list(
    vehicle_id: int | None = None,
    month: str | None = None,
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

    if user.role == "DRIVER":
        if user.vehicle_id:
            stmt = stmt.where(
                MileageRecord.vehicle_id == user.vehicle_id
            )
        else:
            stmt = stmt.where(MileageRecord.vehicle_id == -1)

    rows = db.execute(
        stmt.order_by(MileageRecord.id.desc())
    ).all()

    return [
        {
            "id": record.id,
            "vehicle_id": record.vehicle_id,
            "plate_no": plate_no,
            "trip_date": record.trip_date,
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
            "status": record.status,
            "abnormal": record.abnormal,
            "abnormal_reason": record.abnormal_reason
        }
        for record, plate_no in rows
    ]


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

    abnormal = False
    reason = None

    if data.out_mileage < vehicle.current_mileage:
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

    vehicle = db.get(Vehicle, row.vehicle_id)

    if data.in_mileage >= vehicle.current_mileage:
        vehicle.current_mileage = data.in_mileage
    else:
        row.abnormal = True
        row.abnormal_reason = "收车里程小于车辆当前里程"

    db.commit()

    return {
        "message": "收车登记成功",
        "distance": float(distance),
        "abnormal": row.abnormal,
        "abnormal_reason": row.abnormal_reason
    }


# =========================
# 维保管理
# =========================

@app.get("/api/maintenances")
def maintenance_list(
    vehicle_id: int | None = None,
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

    if user.role == "DRIVER":
        if user.vehicle_id:
            stmt = stmt.where(
                MaintenanceRecord.vehicle_id == user.vehicle_id
            )
        else:
            stmt = stmt.where(MaintenanceRecord.vehicle_id == -1)

    rows = db.execute(
        stmt.order_by(MaintenanceRecord.id.desc())
    ).all()

    return [
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
        require_roles("ADMIN", "VEHICLE_MANAGER", "DRIVER")
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
        require_roles("ADMIN", "VEHICLE_MANAGER")
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
    user: User = Depends(
        require_roles("ADMIN", "VEHICLE_MANAGER")
    ),
):
    row = db.get(MaintenanceRecord, record_id)

    if not row:
        raise HTTPException(status_code=404, detail="维保记录不存在")

    db.delete(row)
    db.commit()
    return {"message": "维保记录删除成功"}


# =========================
# 违章管理
# =========================

@app.get("/api/violations")
def violation_list(
    vehicle_id: int | None = None,
    status: str | None = None,
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

    if user.role == "DRIVER":
        if user.vehicle_id:
            stmt = stmt.where(
                ViolationRecord.vehicle_id == user.vehicle_id
            )
        else:
            stmt = stmt.where(ViolationRecord.vehicle_id == -1)

    rows = db.execute(
        stmt.order_by(ViolationRecord.id.desc())
    ).all()

    return [
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


@app.post("/api/violations")
def violation_create(
    data: ViolationIn,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles("ADMIN", "VEHICLE_MANAGER", "DRIVER")
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
        require_roles("ADMIN", "VEHICLE_MANAGER")
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
    user: User = Depends(
        require_roles("ADMIN", "VEHICLE_MANAGER")
    ),
):
    row = db.get(ViolationRecord, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="违章记录不存在")

    db.delete(row)
    db.commit()
    return {"message": "违章记录删除成功"}


# =========================
# 油费管理
# =========================

@app.get("/api/fuels")
def fuel_list(
    vehicle_id: int | None = None,
    month: str | None = None,
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

    if user.role == "DRIVER":
        if user.vehicle_id:
            stmt = stmt.where(
                FuelRecord.vehicle_id == user.vehicle_id
            )
        else:
            stmt = stmt.where(FuelRecord.vehicle_id == -1)

    rows = db.execute(
        stmt.order_by(FuelRecord.id.desc())
    ).all()

    return [
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


@app.post("/api/fuels")
def fuel_create(
    data: FuelIn,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles("ADMIN", "VEHICLE_MANAGER", "DRIVER")
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
        require_roles("ADMIN", "VEHICLE_MANAGER")
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
    user: User = Depends(
        require_roles("ADMIN", "VEHICLE_MANAGER")
    ),
):
    row = db.get(FuelRecord, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="油费记录不存在")

    db.delete(row)
    db.commit()
    return {"message": "油费记录删除成功"}


# =========================
# 报销管理
# =========================

@app.get("/api/reimbursements")
def reimbursement_list(
    month: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
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

    if user.role == "DRIVER":
        stmt = stmt.where(Reimbursement.applicant_id == user.id)
        if user.vehicle_id:
            stmt = stmt.where(
                Reimbursement.vehicle_id == user.vehicle_id
            )

    rows = db.execute(
        stmt.order_by(Reimbursement.id.desc())
    ).all()

    return [
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


@app.get("/api/reimbursements/{record_id}")
def reimbursement_detail(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
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
    user: User = Depends(get_current_user)
):
    vehicle = db.get(Vehicle, data.vehicle_id)

    if not vehicle:
        raise HTTPException(status_code=404, detail="车辆不存在")

    ensure_driver_vehicle(user, data.vehicle_id)

    if not data.details:
        raise HTTPException(status_code=400, detail="至少填写一条费用")

    total = sum(
        (detail.amount for detail in data.details),
        Decimal("0")
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

    for detail in data.details:
        db.add(
            ReimbursementDetail(
                reimbursement_id=row.id,
                **detail.model_dump()
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
    user: User = Depends(get_current_user),
):
    row = db.get(Reimbursement, record_id)

    if not row:
        raise HTTPException(status_code=404, detail="报销单不存在")

    ensure_driver_vehicle(user, row.vehicle_id)

    if row.applicant_id != user.id and user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="不能删除他人报销单")

    if row.status not in {"DRAFT", "REJECTED"}:
        raise HTTPException(
            status_code=400,
            detail="只有草稿或已退回的报销单可以删除",
        )

    db.delete(row)
    db.commit()
    return {"message": "报销单删除成功"}


@app.post("/api/reimbursements/{record_id}/submit")
def reimbursement_submit(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
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
    total_mileage = db.scalar(
        select(
            func.coalesce(func.sum(MileageRecord.distance), 0)
        ).where(
            func.date_format(
                MileageRecord.trip_date, "%Y-%m"
            ) == month,
            MileageRecord.status == "CLOSED"
        )
    )

    total_reimbursement = db.scalar(
        select(
            func.coalesce(func.sum(Reimbursement.total_amount), 0)
        ).where(
            Reimbursement.reimbursement_month == month,
            Reimbursement.status == "APPROVED"
        )
    )

    expense_rows = db.execute(
        select(
            ReimbursementDetail.expense_type,
            func.coalesce(
                func.sum(ReimbursementDetail.amount), 0
            )
        )
        .join(
            Reimbursement,
            Reimbursement.id ==
            ReimbursementDetail.reimbursement_id
        )
        .where(
            Reimbursement.reimbursement_month == month,
            Reimbursement.status == "APPROVED"
        )
        .group_by(ReimbursementDetail.expense_type)
    ).all()

    expense_map = {
        expense_type: float(amount)
        for expense_type, amount in expense_rows
    }

    vehicle_count = db.scalar(
        select(func.count(Vehicle.id))
    ) or 0

    active_vehicle_count = db.scalar(
        select(func.count(Vehicle.id)).where(
            Vehicle.status == "ACTIVE"
        )
    ) or 0

    pending_count = db.scalar(
        select(func.count(Reimbursement.id)).where(
            Reimbursement.status.in_(
                ["SUBMITTED", "PROJECT_APPROVED"]
            )
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
