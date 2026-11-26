"""AUTH, NOTI, ANNC, SYSM."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models as M
from ..config import settings
from ..core import (
    CM,
    SA,
    VM,
    WK,
    AppError,
    CurrentUser,
    check_pw,
    company_inactive,
    forbidden,
    get_current_user,
    hash_pw,
    make_token,
    not_found,
    ok,
    require,
    ser,
)
from ..db import get_db, utcnow
from ..domain import current_employment, employment_status, today_kst
from ..enums import (
    AnnouncementAudience,
    EmploymentStatus,
    JobPostingStatus,
    JobSeekingStatus,
    OrgStatus,
    UserRole,
    UserStatus,
)
from ..ratelimit import limiter
from ..schemas import In

router = APIRouter()


def user_summary(db: Session, u: M.User) -> dict:
    d = {"id": u.id, "loginId": u.login_id, "name": u.name, "role": u.role.value, "phone": u.phone, "email": u.email,
         "companyId": u.company_id, "companyName": u.company.name if u.company else None, "isDemo": u.is_demo}
    if u.role == WK:
        emp = current_employment(db, u.id)
        d["employment"] = {"id": emp.id, "companyId": emp.company_id, "companyName": emp.company.name,
                           "status": employment_status(emp, today_kst()).value} if emp else None
    return d


# ---------------- AUTH ----------------
class LoginIn(In):
    login_id: str
    password: str


class DemoIn(In):
    role: UserRole


def _issue(db: Session, u: M.User) -> dict:
    u.last_login_at = utcnow()
    db.commit()
    return ok({"token": make_token(u), "user": user_summary(db, u)})


@router.post("/auth/login")
@limiter.limit(settings.rate_limit_login)
def login(request: Request, body: LoginIn, db: Session = Depends(get_db)):
    u = db.query(M.User).filter(M.User.login_id == body.login_id, M.User.deleted_at.is_(None)).first()
    if not u or not check_pw(body.password, u.password_hash):
        raise AppError("INVALID_CREDENTIALS", "아이디 또는 비밀번호가 올바르지 않습니다.", 401)
    if u.status != UserStatus.ACTIVE or company_inactive(u):
        raise AppError("ACCOUNT_INACTIVE", "비활성화된 계정이거나 소속 기업이 비활성 상태입니다.", 403)
    return _issue(db, u)


@router.post("/auth/demo-login")
@limiter.limit(settings.rate_limit_login)
def demo_login(request: Request, body: DemoIn, db: Session = Depends(get_db)):
    u = db.query(M.User).filter(M.User.is_demo.is_(True), M.User.role == body.role, M.User.deleted_at.is_(None)).order_by(M.User.id).first()
    if not u:
        raise not_found("데모 계정")
    return _issue(db, u)


@router.get("/auth/me")
def me(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(user_summary(db, db.get(M.User, user.id)))


class MeIn(In):
    name: str
    phone: str | None = None
    email: str | None = None


@router.patch("/auth/me")
def update_me(body: MeIn, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    u = db.get(M.User, user.id)
    u.name, u.phone, u.email = body.name, body.phone, body.email
    db.commit()
    return ok(user_summary(db, u))


class PwIn(In):
    current_password: str
    new_password: str


@router.post("/auth/password")
def change_pw(body: PwIn, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.is_demo:
        raise AppError("DEMO_ACCOUNT_PROTECTED", "데모 계정의 비밀번호는 바꿀 수 없습니다.", 403)
    u = db.get(M.User, user.id)
    if not check_pw(body.current_password, u.password_hash):
        raise AppError("INVALID_PASSWORD", "현재 비밀번호가 올바르지 않습니다.")
    if len(body.new_password) < 8:
        raise AppError("WEAK_PASSWORD", "비밀번호는 8자 이상이어야 합니다.")
    u.password_hash = hash_pw(body.new_password)
    db.commit()
    return ok(True)


@router.get("/me/unread-counts")
def unread(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(func.count(M.Notification.id)).filter(M.Notification.user_id == user.id, M.Notification.is_read.is_(False)).scalar()
    m = db.query(func.count(M.MessageRecipient.id)).filter(M.MessageRecipient.recipient_id == user.id, M.MessageRecipient.read_at.is_(None),
                                                         M.MessageRecipient.deleted_at.is_(None)).scalar()
    return ok({"notifications": n, "messages": m})


# ---------------- NOTI ----------------
@router.get("/notifications")
def notifications(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(M.Notification).filter(M.Notification.user_id == user.id).order_by(M.Notification.id.desc()).limit(100)
    return ok([ser(r) for r in rows])


@router.post("/notifications/{nid}/read")
def read_noti(nid: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.get(M.Notification, nid)
    if not n or n.user_id != user.id:
        raise not_found("알림")
    n.is_read, n.read_at = True, utcnow()
    db.commit()
    return ok(True)


@router.post("/notifications/read-all")
def read_all(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(M.Notification).filter(M.Notification.user_id == user.id, M.Notification.is_read.is_(False)).update({"is_read": True, "read_at": utcnow()})
    db.commit()
    return ok(True)


# ---------------- ANNC ----------------
AUD = {WK: [AnnouncementAudience.ALL, AnnouncementAudience.WORKER], CM: [AnnouncementAudience.ALL, AnnouncementAudience.COMPANY],
       VM: [AnnouncementAudience.ALL, AnnouncementAudience.VDREAM]}


@router.get("/announcements")
def announcements(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(M.Announcement).filter(M.Announcement.deleted_at.is_(None))
    if user.role != SA:
        q = q.filter(M.Announcement.audience.in_(AUD[user.role]))
    return ok([ser(a) for a in q.order_by(M.Announcement.is_pinned.desc(), M.Announcement.id.desc())])


class AnnIn(In):
    title: str
    content: str
    audience: AnnouncementAudience
    is_pinned: bool = False


@router.post("/announcements")
def create_ann(body: AnnIn, user: CurrentUser = Depends(require(SA)), db: Session = Depends(get_db)):
    a = M.Announcement(**body.model_dump(), author_id=user.id)
    db.add(a)
    db.commit()
    return ok(ser(a))


@router.put("/announcements/{aid}")
def update_ann(aid: int, body: AnnIn, user: CurrentUser = Depends(require(SA)), db: Session = Depends(get_db)):
    a = db.get(M.Announcement, aid)
    if not a:
        raise not_found("공지")
    for k, v in body.model_dump().items():
        setattr(a, k, v)
    db.commit()
    return ok(ser(a))


@router.delete("/announcements/{aid}")
def delete_ann(aid: int, user: CurrentUser = Depends(require(SA)), db: Session = Depends(get_db)):
    a = db.get(M.Announcement, aid)
    if not a:
        raise not_found("공지")
    a.deleted_at = utcnow()
    db.commit()
    return ok(True)


# ---------------- SYSM ----------------
@router.get("/system/dashboard")
def sys_dashboard(user: CurrentUser = Depends(require(SA)), db: Session = Depends(get_db)):
    today = today_kst()
    roles = dict(db.query(M.User.role, func.count(M.User.id)).filter(M.User.deleted_at.is_(None)).group_by(M.User.role).all())
    emps = db.query(M.Employment).all()
    active_ids = [e.id for e in emps if employment_status(e, today) == EmploymentStatus.ACTIVE]
    checked = db.query(func.count(M.AttendanceRecord.id)).filter(M.AttendanceRecord.work_date == today, M.AttendanceRecord.check_in_at.isnot(None)).scalar()
    return ok({
        "companies": db.query(func.count(M.Company.id)).scalar(),
        "users": {r.value: c for r, c in roles.items()},
        "seekers": db.query(func.count(M.WorkerProfile.id)).filter(M.WorkerProfile.job_seeking_status == JobSeekingStatus.SEEKING).scalar(),
        "activeWorkers": len(active_ids),
        "publishedPostings": db.query(func.count(M.JobPosting.id)).filter(M.JobPosting.status == JobPostingStatus.PUBLISHED).scalar(),
        "checkedInToday": checked,
    })


@router.post("/system/demo-reset")
def demo_reset(user: CurrentUser = Depends(require(SA)), db: Session = Depends(get_db)):
    from ..seed import reset_and_seed
    db.close()
    return ok(reset_and_seed())


def company_out(c: M.Company) -> dict:
    return ser(c, managerName=c.manager.name if c.manager else None)


@router.get("/companies")
def companies(mine: bool = False, user: CurrentUser = Depends(require(SA, VM)), db: Session = Depends(get_db)):
    q = db.query(M.Company)
    if mine:
        q = q.filter(M.Company.manager_id == user.id)
    today = today_kst()
    out = []
    for c in q.order_by(M.Company.name):
        n = sum(1 for e in db.query(M.Employment).filter(M.Employment.company_id == c.id) if employment_status(e, today) == EmploymentStatus.ACTIVE)
        out.append(company_out(c) | {"activeWorkers": n})
    return ok(out)


class CompanyIn(In):
    name: str
    business_registration_no: str | None = None
    representative_name: str | None = None
    employment_insurance_no: str | None = None
    industry: str | None = None
    address: str | None = None
    phone: str | None = None
    manager_id: int | None = None
    status: OrgStatus = OrgStatus.ACTIVE


def _check_manager(db: Session, mid: int | None) -> None:
    if mid is not None:
        m = db.get(M.User, mid)
        if not m or m.role != VM or m.status != UserStatus.ACTIVE:
            raise AppError("INVALID_MANAGER", "담당 매니저는 활성 브이드림 매니저여야 합니다.")


@router.post("/companies")
def create_company(body: CompanyIn, user: CurrentUser = Depends(require(SA)), db: Session = Depends(get_db)):
    _check_manager(db, body.manager_id)
    c = M.Company(**body.model_dump())
    db.add(c)
    db.commit()
    return ok(company_out(c))


@router.put("/companies/{cid}")
def update_company(cid: int, body: CompanyIn, user: CurrentUser = Depends(require(SA)), db: Session = Depends(get_db)):
    c = db.get(M.Company, cid)
    if not c:
        raise not_found("기업")
    _check_manager(db, body.manager_id)
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    db.commit()
    return ok(company_out(c))


@router.get("/users")
def users(role: UserRole | None = None, q: str | None = None, user: CurrentUser = Depends(require(SA)), db: Session = Depends(get_db)):
    qq = db.query(M.User).filter(M.User.deleted_at.is_(None))
    if role:
        qq = qq.filter(M.User.role == role)
    if q:
        qq = qq.filter((M.User.name.contains(q)) | (M.User.login_id.contains(q)))
    return ok([ser(u, companyName=u.company.name if u.company else None) for u in qq.order_by(M.User.role, M.User.name)])


class UserIn(In):
    login_id: str
    name: str
    role: UserRole
    password: str | None = None
    phone: str | None = None
    email: str | None = None
    company_id: int | None = None
    status: UserStatus = UserStatus.ACTIVE


@router.post("/users")
def create_user(body: UserIn, user: CurrentUser = Depends(require(SA)), db: Session = Depends(get_db)):
    if body.role == CM and not body.company_id:
        raise AppError("COMPANY_REQUIRED", "기업 담당자는 소속 기업이 필요합니다.")
    if db.query(M.User).filter(M.User.login_id == body.login_id).first():
        raise AppError("LOGIN_ID_TAKEN", "이미 사용 중인 아이디입니다.")
    u = M.User(login_id=body.login_id, name=body.name, role=body.role, phone=body.phone, email=body.email,
               company_id=body.company_id if body.role == CM else None, password_hash=hash_pw(body.password or "changeme123"))
    db.add(u)
    db.flush()
    if body.role == WK:
        db.add(M.WorkerProfile(user_id=u.id))
    db.commit()
    return ok(ser(u))


@router.put("/users/{uid}")
def update_user(uid: int, body: UserIn, user: CurrentUser = Depends(require(SA)), db: Session = Depends(get_db)):
    u = db.get(M.User, uid)
    if not u:
        raise not_found("계정")
    if u.is_demo and body.status != UserStatus.ACTIVE:
        raise AppError("DEMO_ACCOUNT_PROTECTED", "데모 계정은 비활성화할 수 없습니다.", 403)
    u.name, u.phone, u.email, u.status = body.name, body.phone, body.email, body.status
    if u.role == CM and body.company_id:
        u.company_id = body.company_id
    if body.password and not u.is_demo:
        u.password_hash = hash_pw(body.password)
    db.commit()
    return ok(ser(u))


def ensure_company_access(user: CurrentUser, company_id: int) -> None:
    if user.role == CM and user.company_id != company_id:
        raise forbidden()
