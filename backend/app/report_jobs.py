"""Bounded report jobs: one low-priority child process, private expiring files."""

import json
import logging
import multiprocessing
import os
import re
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from app.config import settings

TTL_SECONDS = 6 * 60 * 60
JOB_TIMEOUT = 150
MAX_STORAGE_BYTES = 512 * 1024 * 1024
_guard = threading.Lock()
_active_owners = set()
_children = {}
_pending_jobs = {}
_pool = None


def root_path():
    root = Path(os.environ.get('MILEAGE_REPORT_DIR') or settings.upload_path.resolve().parent / '.mileage-reports')
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root.resolve()


def write_state(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    temporary.replace(path)


def read_state(job_id):
    if not re.fullmatch(r'[a-f0-9]{32}', job_id):
        raise HTTPException(status_code=404, detail='导出任务不存在')
    try:
        job = json.loads((root_path() / job_id / 'state.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise HTTPException(status_code=404, detail='导出任务不存在或已过期')
    if time.time() - job['created_at'] > TTL_SECONDS:
        raise HTTPException(status_code=410, detail='导出文件已过期，请重新生成')
    return job


def cleanup(root):
    for directory in root.iterdir():
        if not directory.is_dir() or directory.is_symlink() or not re.fullmatch(r'[a-f0-9]{32}', directory.name):
            continue
        try:
            data = json.loads((directory / 'state.json').read_text(encoding='utf-8'))
            if time.time() - data['created_at'] > TTL_SECONDS:
                shutil.rmtree(directory)
        except (OSError, ValueError, KeyError):
            continue


def worker(job_dir, rows, params, upload_path):
    state_path = Path(job_dir) / 'state.json'
    job = json.loads(state_path.read_text(encoding='utf-8'))
    lock_file = None
    try:
        if os.name == 'posix':
            import fcntl
            import resource
            os.nice(8)
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
            lock_file = (Path(job_dir).parent / 'worker.lock').open('a')
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        job.update(status='running', progress=1)
        write_state(state_path, job)
        from app.mileage_report import build_workbook

        def progress(value):
            job['progress'] = value
            write_state(state_path, job)

        temporary = Path(job_dir) / 'report.partial.xlsx'
        stats = build_workbook(rows, params, upload_path, temporary, progress)
        if temporary.stat().st_size > 64 * 1024 * 1024:
            raise ValueError('导出文件超过64MB，请缩小范围或选择代表照片')
        temporary.replace(Path(job_dir) / 'report.xlsx')
        job.update(status='ready', progress=100, stats=stats, bytes=(Path(job_dir) / 'report.xlsx').stat().st_size)
        write_state(state_path, job)
    except Exception as exc:
        logging.getLogger(__name__).exception('Mileage report generation failed')
        message = str(exc) if isinstance(exc, ValueError) else '生成失败，请缩小范围或选择不附照片后重试'
        job.update(status='failed', message=message, progress=0)
        write_state(state_path, job)
    finally:
        if lock_file:
            lock_file.close()


def supervise(job_id, rows, params, upload_path, root):
    directory = root / job_id
    state_path = directory / 'state.json'
    owner = json.loads(state_path.read_text(encoding='utf-8'))['owner_id']
    process = multiprocessing.get_context('spawn').Process(target=worker, args=(str(directory), rows, params, str(upload_path)), daemon=True)
    try:
        with _guard:
            _children[job_id] = process
        process.start()
        process.join(JOB_TIMEOUT)
        if process.is_alive():
            process.terminate()
            process.join(5)
        job = json.loads(state_path.read_text(encoding='utf-8'))
        if job['status'] not in {'ready', 'failed'}:
            job.update(status='failed', message='生成超时或任务已中断，请缩小范围后重新生成', progress=0)
            write_state(state_path, job)
    except Exception:
        logging.getLogger(__name__).exception('Mileage report process failed')
        job = json.loads(state_path.read_text(encoding='utf-8'))
        job.update(status='failed', message='任务未能完成，请重新生成', progress=0)
        write_state(state_path, job)
    finally:
        with _guard:
            _active_owners.discard(owner)
            _children.pop(job_id, None)
            _pending_jobs.pop(job_id, None)


def create_job(user, rows, filters):
    global _pool
    root = root_path()
    with _guard:
        cleanup(root)
        if user.id in _active_owners:
            raise HTTPException(status_code=429, detail='您已有报表正在生成，请等待完成')
        if len(_active_owners) >= 2:
            raise HTTPException(status_code=429, detail='报表生成队列繁忙，请稍后重试')
        size = sum(path.stat().st_size for path in root.glob('*/*') if path.is_file())
        if size >= MAX_STORAGE_BYTES or shutil.disk_usage(root).free < 128 * 1024 * 1024:
            raise HTTPException(status_code=429, detail='导出存储暂时繁忙，请稍后重试')
        if _pool is None:
            _pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='mileage-report-supervisor')
        job_id = uuid4().hex
        directory = root / job_id
        directory.mkdir(mode=0o700)
        params = filters.model_dump(mode='json')
        job = {'id': job_id, 'owner_id': user.id, 'created_at': time.time(), 'status': 'queued', 'progress': 0,
            'vehicle_ids': sorted({row['vehicle_id'] for row in rows}), 'params': params,
            'filename': f"里程报告-{filters.date_from:%Y%m%d}-{filters.date_to:%Y%m%d}.xlsx"}
        write_state(directory / 'state.json', job)
        _active_owners.add(user.id)
        _pending_jobs[job_id] = (user.id, root)
        try:
            _pool.submit(supervise, job_id, rows, params, settings.upload_path.resolve(), root)
        except Exception:
            _active_owners.discard(user.id)
            _pending_jobs.pop(job_id, None)
            job.update(status='failed', message='任务未能启动，请重试')
            write_state(directory / 'state.json', job)
            raise HTTPException(status_code=503, detail='任务未能启动，请重试')
    return job


def shutdown():
    global _pool
    with _guard:
        pool, _pool = _pool, None
        children = list(_children.values())
        pending = dict(_pending_jobs)
    for process in children:
        if process.pid and process.is_alive():
            process.terminate()
    if pool:
        pool.shutdown(wait=True, cancel_futures=True)
    for job_id, (owner, root) in pending.items():
        path = root / job_id / 'state.json'
        try:
            job = json.loads(path.read_text(encoding='utf-8'))
            if job['status'] not in {'ready', 'failed'}:
                job.update(status='failed', message='服务更新中，任务已中断，请重新生成', progress=0)
                write_state(path, job)
        except (OSError, ValueError):
            pass
        with _guard:
            _active_owners.discard(owner)
            _pending_jobs.pop(job_id, None)
