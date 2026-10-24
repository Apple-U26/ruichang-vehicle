from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import report_jobs
from app.access import apply_vehicle_scope
from app.database import get_db
from app.mileage_report import ReportRequest, collect_rows
from app.models import MileageRecord, User, Vehicle
from app.security import require_roles

router = APIRouter(prefix='/api/mileage-reports', tags=['里程报告'])
allowed = require_roles('ADMIN', 'FINANCE', 'PROJECT_MANAGER', 'VEHICLE_MANAGER')


@router.get('/options')
def options(db: Session = Depends(get_db), user: User = Depends(allowed)):
    vehicles = db.execute(apply_vehicle_scope(user, select(Vehicle.id, Vehicle.plate_no)).order_by(Vehicle.plate_no)).all()
    names = db.scalars(apply_vehicle_scope(user, select(MileageRecord.driver_name).join(Vehicle, Vehicle.id == MileageRecord.vehicle_id))).all()
    return {'vehicles': [{'id': row.id, 'plate_no': row.plate_no} for row in vehicles],
        'drivers': sorted({name.strip() for name in names if name and name.strip()})}


def checked_job(job_id, db, user):
    job = report_jobs.read_state(job_id)
    if job['owner_id'] != user.id:
        raise HTTPException(status_code=404, detail='导出任务不存在')
    visible = set(db.scalars(apply_vehicle_scope(user, select(Vehicle.id)).where(Vehicle.id.in_(job['vehicle_ids']))))
    if not set(job['vehicle_ids']).issubset(visible):
        raise HTTPException(status_code=403, detail='负责范围已变化，请重新生成报表')
    return job


@router.post('')
def create(filters: ReportRequest, db: Session = Depends(get_db), user: User = Depends(allowed)):
    rows = collect_rows(db, user, filters)
    job = report_jobs.create_job(user, rows, filters)
    return {'id': job['id'], 'status': job['status'], 'records': len(rows), 'expires_in': report_jobs.TTL_SECONDS}


@router.get('/{job_id}')
def status(job_id: str, db: Session = Depends(get_db), user: User = Depends(allowed)):
    job = checked_job(job_id, db, user)
    return {key: job[key] for key in ['id', 'status', 'progress', 'filename', 'created_at', 'message', 'stats', 'bytes'] if key in job}


@router.get('/{job_id}/download')
def download(job_id: str, db: Session = Depends(get_db), user: User = Depends(allowed)):
    job = checked_job(job_id, db, user)
    if job['status'] != 'ready':
        raise HTTPException(status_code=409, detail='报表尚未生成完成')
    path = report_jobs.root_path() / job_id / 'report.xlsx'
    if not path.is_file():
        raise HTTPException(status_code=410, detail='导出文件已过期，请重新生成')
    return FileResponse(path, filename=job['filename'], media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Cache-Control': 'private, no-store'})


@router.on_event('shutdown')
def stop_jobs():
    report_jobs.shutdown()
