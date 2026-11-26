"""Pure domain rules: date-derived states (no batch), messaging rules, employment recognition."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from . import models as M
from .enums import (
    DisabilityDegree,
    EmploymentStatus,
    JobPostingStatus,
    RecognitionResult,
    SalaryType,
    UserRole,
    UserStatus,
)

KST = ZoneInfo("Asia/Seoul")
UTC = ZoneInfo("UTC")
DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def today_kst() -> date:
    return datetime.now(KST).date()


def kst_to_utc_naive(d: date, t) -> datetime:
    return datetime.combine(d, t, tzinfo=KST).astimezone(UTC).replace(tzinfo=None)


def utc_naive_to_kst(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC).astimezone(KST)


# ---------- 날짜 파생 상태 (기술스펙 4.9) ----------
def employment_status(e: M.Employment, today: date) -> EmploymentStatus:
    if e.start_date > today:
        return EmploymentStatus.PENDING
    if e.end_date is not None and e.end_date < today:
        return EmploymentStatus.RESIGNED
    return EmploymentStatus.ACTIVE


def is_open_employment(e: M.Employment, today: date) -> bool:
    return employment_status(e, today) in (EmploymentStatus.PENDING, EmploymentStatus.ACTIVE)


def current_employment(db: Session, worker_id: int, today: date | None = None) -> M.Employment | None:
    today = today or today_kst()
    for e in db.query(M.Employment).filter(M.Employment.worker_id == worker_id).order_by(M.Employment.start_date.desc()):
        if is_open_employment(e, today):
            return e
    return None


def is_workday(contract: M.EmploymentContract | None, d: date) -> bool:
    return bool(contract) and DAYS[d.weekday()] in contract.work_days.split(",")


def absent_days(e: M.Employment, records: dict[date, M.AttendanceRecord], leave_days: set[date], start: date, end: date, today: date) -> list[date]:
    """출근 기록·승인 휴가가 없는 과거 근무일 (ATTD-005, 저장하지 않음)."""
    out, d = [], max(start, e.start_date)
    last = min(end, today - timedelta(days=1), e.end_date or end)
    while d <= last:
        if is_workday(e.contract, d) and d not in records and d not in leave_days:
            out.append(d)
        d += timedelta(days=1)
    return out


def posting_open(p: M.JobPosting, today: date) -> bool:
    return p.status == JobPostingStatus.PUBLISHED and (p.deadline_date is None or p.deadline_date >= today)


# ---------- 쪽지 대상 규칙 (요구기능 부록 A.13) ----------
ALL = "ALL"


def allowed_recipient_ids(db: Session, sender: M.User, today: date) -> set[int] | str:
    if sender.role == UserRole.VDREAM_MANAGER:
        return ALL
    if sender.role == UserRole.WORKER:
        emp = current_employment(db, sender.id, today)
        if not emp:
            return set()
        ids = {u.id for u in db.query(M.User).filter(M.User.company_id == emp.company_id, M.User.role == UserRole.COMPANY_MANAGER,
                                                      M.User.status == UserStatus.ACTIVE, M.User.deleted_at.is_(None))}
        if emp.company.manager_id:
            ids.add(emp.company.manager_id)
        return ids
    if sender.role == UserRole.COMPANY_MANAGER and sender.company_id:
        ids = {e.worker_id for e in db.query(M.Employment).filter(M.Employment.company_id == sender.company_id) if is_open_employment(e, today)}
        c = db.get(M.Company, sender.company_id)
        if c and c.manager_id:
            ids.add(c.manager_id)
        return ids
    return set()


def can_send(allowed: set[int] | str, recipient_id: int) -> bool:
    return allowed == ALL or recipient_id in allowed  # type: ignore[operator]


# ---------- 고용 인정 참고 판정 (기술스펙 4.13) ----------
def monthly_scheduled_hours(weekly: float) -> float:
    return round(weekly * 365 / 7 / 12, 1)


def hourly_wage(salary_type: SalaryType, amount: int, weekly: float) -> float:
    if salary_type == SalaryType.HOURLY:
        return float(amount)
    weekly_holiday = weekly / 5 if weekly >= 15 else 0
    paid_hours = round((weekly + weekly_holiday) * 365 / 7 / 12)  # 주 40시간 → 209시간
    return round(amount / paid_hours, 0) if paid_hours else 0.0


def recognition(degree: DisabilityDegree | None, monthly_hours: float, paid_days: int, partial_month: bool) -> tuple[RecognitionResult, str]:
    if degree is None:
        return RecognitionResult.NEEDS_REVIEW, "장애정도 미입력"
    if partial_month and paid_days < 16:
        return RecognitionResult.NEEDS_REVIEW, f"월 중 입사·퇴사, 유급 근로일수 {paid_days}일 < 16일"
    label = "중증" if degree == DisabilityDegree.SEVERE else "경증"
    if monthly_hours >= 60:
        if degree == DisabilityDegree.SEVERE:
            return RecognitionResult.DOUBLE, f"{label}, 월 소정근로시간 {monthly_hours}시간 ≥ 60시간 (2배수)"
        return RecognitionResult.SINGLE, f"{label}, 월 소정근로시간 {monthly_hours}시간 ≥ 60시간"
    if degree == DisabilityDegree.SEVERE and paid_days >= 16:
        return RecognitionResult.SINGLE, f"{label}, 월 {monthly_hours}시간 < 60시간이나 유급 근로일수 {paid_days}일 ≥ 16일"
    return RecognitionResult.EXCLUDED, f"{label}, 월 소정근로시간 {monthly_hours}시간 < 60시간"
