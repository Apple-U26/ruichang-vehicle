from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User


password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token",
    auto_error=False,
)

DbSession = Annotated[Session, Depends(get_db)]
AccessToken = Annotated[str, Depends(oauth2_scheme)]


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_expire_minutes)

    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "iat": now,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm="HS256",
    )


def get_current_user(
    token: AccessToken,
    db: DbSession,
) -> User:
    if not token:
        raise credentials_error()
    return get_user_from_token(token, db)


def get_current_user_query(
    token: str | None = None,
    header_token: str | None = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> User:
    actual_token = token or header_token
    if not actual_token:
        raise credentials_error()
    return get_user_from_token(actual_token, db)


def credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="登录状态已失效",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_user_from_token(token: str, db: Session) -> User:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
        )
        subject = payload.get("sub")
        if subject is None:
            raise credentials_error()

        user_id = int(subject)
    except (InvalidTokenError, TypeError, ValueError) as exc:
        raise credentials_error() from exc

    user = db.get(User, user_id)

    if user is None or not user.enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已停用",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_roles(*roles: str) -> Callable:
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有操作权限",
            )
        return user

    return checker
