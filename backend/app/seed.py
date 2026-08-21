from sqlalchemy import select

from app.database import (
    Base,
    engine,
    ensure_column,
    SessionLocal,
)
from app.models import Project, User, Vehicle
from app.security import hash_password


def main():
    Base.metadata.create_all(bind=engine)
    ensure_column("sys_user", "vehicle_id", "BIGINT NULL")
    ensure_column("violation_record", "attachment_url", "VARCHAR(500)")
    ensure_column("project_info", "location", "VARCHAR(200)")
    ensure_column("project_info", "manager_user_id", "BIGINT NULL")

    db = SessionLocal()

    try:
        users = [
            ("admin", "系统管理员", "ADMIN"),
            ("vehicle_manager", "车辆负责人", "VEHICLE_MANAGER"),
            ("project_manager", "项目负责人", "PROJECT_MANAGER"),
            ("finance", "财务人员", "FINANCE"),
            ("driver", "驾驶员", "DRIVER"),
        ]

        for username, real_name, role in users:
            exists = db.scalar(
                select(User).where(User.username == username)
            )
            if exists:
                continue
            db.add(
                User(
                    username=username,
                    real_name=real_name,
                    password_hash=hash_password("Admin@123456"),
                    role=role,
                    enabled=True,
                )
            )

        if not db.scalar(select(Project)):
            db.add(
                Project(
                    name="示范项目",
                    manager_name="项目负责人",
                    enabled=True,
                    remark="系统初始化项目",
                )
            )
            db.flush()

        demo_vehicle = None
        if not db.scalar(select(Vehicle)):
            project = db.scalar(select(Project))
            demo_vehicle = Vehicle(
                vehicle_code="CL-000001",
                plate_no="赣A00001",
                project_id=project.id if project else None,
                project_manager="项目负责人",
                vehicle_manager="车辆负责人",
                ownership="COMPANY",
                initial_mileage=0,
                current_mileage=0,
                status="ACTIVE",
            )
            db.add(demo_vehicle)
            db.flush()

        if demo_vehicle is not None:
            driver = db.scalar(
                select(User).where(User.username == "driver")
            )
            if driver is not None and driver.vehicle_id is None:
                driver.vehicle_id = demo_vehicle.id

        db.commit()

        print("初始化完成")
        print("用户名：admin")
        print("演示账号：vehicle_manager / project_manager / finance / driver")
        print("初始密码：Admin@123456")
    finally:
        db.close()


if __name__ == "__main__":
    main()
