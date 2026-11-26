"""Security, request dependencies, errors, serialization."""
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, Header
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from . import models as M
from .config import settings
from .db import get_db
from .enums import UserRole, UserStatus


def company_inactive(u: M.User) -> bool:
    """SYSM-002: 비활성 기업의 담당자는 로그인할 수 없다."""
    from .enums import OrgStatus
    return u.role == UserRole.COMPANY_MANAGER and u.company is not None and u.company.status != OrgStatus.ACTIVE


class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code, self.message, self.status = code, message, status


def not_found(what: str = "대상") -> AppError:
    return AppError("NOT_FOUND", f"{what}을(를) 찾을 수 없습니다.", 404)


def forbidden(msg: str = "권한이 없습니다.") -> AppError:
    return AppError("FORBIDDEN", msg, 403)


def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(10)).decode()


def check_pw(pw: str, h: str) -> bool:
    return bcrypt.checkpw(pw.encode(), h.encode())


def make_token(user: M.User) -> str:
    exp = datetime.now(UTC) + timedelta(hours=settings.jwt_ttl_hours)
    return jwt.encode({"sub": str(user.id), "role": user.role.value, "exp": exp}, settings.jwt_secret, algorithm="HS256")


@dataclass
class CurrentUser:
    id: int
    role: UserRole
    company_id: int | None
    is_demo: bool
    name: str


def get_current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError("UNAUTHORIZED", "로그인이 필요합니다.", 401)
    try:
        payload = jwt.decode(authorization[7:], settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise AppError("UNAUTHORIZED", "로그인이 만료되었습니다. 다시 로그인해 주세요.", 401) from None
    u = db.get(M.User, int(payload["sub"]))
    if not u or u.deleted_at or u.status != UserStatus.ACTIVE or company_inactive(u):
        raise AppError("UNAUTHORIZED", "사용할 수 없는 계정입니다.", 401)
    return CurrentUser(u.id, u.role, u.company_id, u.is_demo, u.name)


def require(*roles: UserRole):
    def dep(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise forbidden()
        return user
    return dep


WK, CM, VM, SA = UserRole.WORKER, UserRole.COMPANY_MANAGER, UserRole.VDREAM_MANAGER, UserRole.SYSTEM_ADMIN


def _camel(s: str) -> str:
    head, *tail = s.split("_")
    return head + "".join(t.title() for t in tail)


def val(v: Any) -> Any:
    if isinstance(v, datetime):
        return v.isoformat() + "Z"
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, Enum):
        return v.value
    if hasattr(v, "isoformat"):  # time
        return v.isoformat(timespec="minutes")
    return v


def ser(obj: Any, exclude: tuple[str, ...] = ("password_hash",), **extra: Any) -> dict[str, Any]:
    if obj is None:
        return None  # type: ignore[return-value]
    out = {_camel(c.key): val(getattr(obj, c.key)) for c in inspect(obj).mapper.column_attrs if c.key not in exclude}
    out.update({k: val(v) for k, v in extra.items()})
    return out


def ok(data: Any = None, **meta: Any) -> dict[str, Any]:
    return {"data": data, "meta": meta} if meta else {"data": data}


def page_params(page: int = 1, size: int = 20) -> tuple[int, int]:
    return max(page, 1), min(max(size, 1), 100)


def notify(db: Session, user_ids: list[int] | set[int], type_: str, title: str, body: str, link: str | None = None) -> None:
    for uid in set(user_ids):
        db.add(M.Notification(user_id=uid, type=type_, title=title, body=body, link_path=link))


def company_manager_ids(db: Session, company_id: int) -> list[int]:
    """담당 매니저가 있으면 그 사람, 없으면 모든 활성 VM (NOTI-002)."""
    c = db.get(M.Company, company_id)
    if c and c.manager_id:
        return [c.manager_id]
    return [u.id for u in db.query(M.User).filter(M.User.role == VM, M.User.status == UserStatus.ACTIVE, M.User.deleted_at.is_(None))]


def company_cm_ids(db: Session, company_id: int) -> list[int]:
    return [u.id for u in db.query(M.User).filter(M.User.company_id == company_id, M.User.role == CM, M.User.deleted_at.is_(None))]
