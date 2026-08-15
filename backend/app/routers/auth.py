from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import ChangePasswordIn, LoginIn
from app.security import (
    create_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["认证"])


def authenticate_user(
    db: Session,
    username: str,
    password: str,
) -> User:
    user = db.scalar(
        select(User).where(User.username == username)
    )

    if (
        user is None
        or not user.enabled
        or not verify_password(password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def build_access_token(user: User) -> str:
    return create_token(user)


@router.post("/login")
def login(
    payload: LoginIn,
    db: Session = Depends(get_db),
):
    user = authenticate_user(
        db=db,
        username=payload.username,
        password=payload.password,
    )
    access_token = build_access_token(user)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "role": user.role,
            "vehicle_id": user.vehicle_id,
            "plate_no": (
                user.vehicle.plate_no if user.vehicle else None
            ),
        },
    }


@router.post("/token")
def swagger_token_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(
        db=db,
        username=form_data.username,
        password=form_data.password,
    )

    return {
        "access_token": build_access_token(user),
        "token_type": "bearer",
    }


@router.post("/change-password")
def change_password(
    payload: ChangePasswordIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(
            status_code=400,
            detail="原密码不正确",
        )

    if payload.old_password == payload.new_password:
        raise HTTPException(
            status_code=400,
            detail="新密码不能与原密码相同",
        )

    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "密码修改成功"}




