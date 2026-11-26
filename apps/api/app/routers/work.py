"""ATTD, LEAV, TASK, WLOG, files."""
import calendar
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from .. import models as M
from ..config import settings
from ..core import (
    CM,
    VM,
    WK,
    AppError,
    CurrentUser,
    company_cm_ids,
    forbidden,
    get_current_user,
    not_found,
    notify,
    ok,
    require,
    ser,
)
from ..db import get_db, utcnow
from ..domain import (
    absent_days,
    current_employment,
    employment_status,
    is_open_employment,
    is_workday,
    kst_to_utc_naive,
    today_kst,
    utc_naive_to_kst,
)
from ..enums import AttendanceStatus as AT
from ..enums import EmploymentStatus, FilePurpose, HalfDayType, LeaveType, TaskPriority
from ..enums import LeaveStatus as LS
from ..enums import TaskStatus as TS
from ..enums import WorkLogStatus as WS
from ..ratelimit import limiter
from ..schemas import In
from ..storage import download_url, save_upload, verify_sig

router = APIRouter()


def month_range(month: str) -> tuple[date, date]:
    y, m = map(int, month.split("-"))
    return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])


def my_emp(db: Session, user: CurrentUser, active_only: bool = True) -> M.Employment:
    e = current_employment(db, user.id)
    if not e or (active_only and employment_status(e, today_kst()) != EmploymentStatus.ACTIVE):
        raise AppError("NOT_EMPLOYED", "재직 중인 기업이 없거나 아직 출근 시작일 전입니다.")
    return e


def scoped_emps(db: Session, user: CurrentUser, employment_id: int | None = None) -> list[M.Employment]:
    q = db.query(M.Employment)
    if user.role == CM:
        q = q.filter(M.Employment.company_id == user.company_id)
    if employment_id:
        q = q.filter(M.Employment.id == employment_id)
    return q.all()


# ---------------- ATTENDANCE ----------------
def att_out(r: M.AttendanceRecord) -> dict:
    return ser(r)


def approved_leave_for(db: Session, emp_id: int, d: date) -> M.LeaveRequest | None:
    return db.query(M.LeaveRequest).filter(M.LeaveRequest.employment_id == emp_id, M.LeaveRequest.status == LS.APPROVED,
                                           M.LeaveRequest.start_date <= d, M.LeaveRequest.end_date >= d).first()


@router.get("/attendance/today")
def today_summary(user: CurrentUser = Depends(require(WK)), db: Session = Depends(get_db)):
    e = current_employment(db, user.id)
    if not e:
        return ok({"employment": None})
    today = today_kst()
    rec = db.query(M.AttendanceRecord).filter_by(employment_id=e.id, work_date=today).first()
    tasks = db.query(M.Task).filter(M.Task.employment_id == e.id, M.Task.status != TS.CANCELLED).all()
    todays = [t for t in tasks if t.status == TS.IN_PROGRESS or (t.status == TS.ASSIGNED and (t.due_date is None or t.due_date <= today + timedelta(days=1)))]
    done_today = [t for t in tasks if t.completed_at and utc_naive_to_kst(t.completed_at).date() == today]
    wl = db.query(M.WorkLog).filter_by(employment_id=e.id, work_date=today).first()
    c = e.contract
    return ok({"employment": {"id": e.id, "companyName": e.company.name, "status": employment_status(e, today).value},
               "record": att_out(rec) if rec else None, "isWorkday": is_workday(c, today),
               "workStart": c.work_start_time.isoformat("minutes") if c else None, "workEnd": c.work_end_time.isoformat("minutes") if c else None,
               "todoTasks": [ser(t) for t in sorted(todays, key=lambda t: (t.status != TS.IN_PROGRESS, t.due_date or date.max))],
               "completedToday": len(done_today), "workLogStatus": wl.status.value if wl else None})


@router.post("/attendance/check-in")
def check_in(user: CurrentUser = Depends(require(WK)), db: Session = Depends(get_db)):
    e = my_emp(db, user)
    today, now = today_kst(), utcnow()
    rec = db.query(M.AttendanceRecord).filter_by(employment_id=e.id, work_date=today).first()
    if rec and rec.check_in_at:
        raise AppError("ALREADY_CHECKED_IN", "오늘은 이미 출근했습니다.")
    c = e.contract
    leave = approved_leave_for(db, e.id, today)
    half = HalfDayType.AM if leave and leave.leave_type == LeaveType.HALF_DAY_AM else HalfDayType.PM if leave and leave.leave_type == LeaveType.HALF_DAY_PM else None
    expected = kst_to_utc_naive(today, c.work_start_time)
    if half == HalfDayType.AM:
        expected += timedelta(hours=4)
    late = max(0, int((now - expected).total_seconds() // 60))
    rec = rec or M.AttendanceRecord(employment_id=e.id, work_date=today)
    rec.check_in_at, rec.late_minutes, rec.half_day_type = now, late, half
    rec.status = AT.LATE if late > 0 else AT.NORMAL
    rec.leave_request_id = leave.id if leave else None
    db.add(rec)
    if late:
        notify(db, company_cm_ids(db, e.company_id), "ATTENDANCE_LATE", "지각", f"{user.name} {late}분 지각", "/admin/attendance")
    db.commit()
    return ok(att_out(rec))


@router.post("/attendance/check-out")
def check_out(user: CurrentUser = Depends(require(WK)), db: Session = Depends(get_db)):
    e = my_emp(db, user)
    today, now = today_kst(), utcnow()
    rec = db.query(M.AttendanceRecord).filter_by(employment_id=e.id, work_date=today).first()
    if not rec or not rec.check_in_at:
        raise AppError("NOT_CHECKED_IN", "출근 기록이 없습니다.")
    if rec.check_out_at:
        raise AppError("ALREADY_CHECKED_OUT", "오늘은 이미 퇴근했습니다.")
    rec.check_out_at = now
    if rec.half_day_type != HalfDayType.PM:
        early = max(0, int((kst_to_utc_naive(today, e.contract.work_end_time) - now).total_seconds() // 60))
        rec.early_leave_minutes = early
        if early:
            rec.status = AT.LATE_EARLY_LEAVE if rec.status == AT.LATE else AT.EARLY_LEAVE
            notify(db, company_cm_ids(db, e.company_id), "ATTENDANCE_EARLY_LEAVE", "조퇴", f"{user.name} {early}분 조퇴", "/admin/attendance")
    wl = db.query(M.WorkLog).filter_by(employment_id=e.id, work_date=today).first()
    db.commit()
    return ok(att_out(rec) | {"workLogSubmitted": bool(wl and wl.status in (WS.SUBMITTED, WS.CONFIRMED))})


class ReasonsIn(In):
    late_reason: str | None = None
    early_leave_reason: str | None = None


@router.patch("/attendance/{rid}/reason")
def att_reason(rid: int, body: ReasonsIn, user: CurrentUser = Depends(require(WK)), db: Session = Depends(get_db)):
    r = db.get(M.AttendanceRecord, rid)
    if not r or db.get(M.Employment, r.employment_id).worker_id != user.id:
        raise not_found("근태")
    if r.work_date != today_kst():
        raise AppError("PAST_RECORD", "사유는 당일에만 입력할 수 있습니다.")
    r.worker_late_reason, r.worker_early_leave_reason = body.late_reason, body.early_leave_reason
    db.commit()
    return ok(att_out(r))


def month_days(db: Session, e: M.Employment, month: str) -> tuple[list[dict], dict]:
    start, end = month_range(month)
    today = today_kst()
    recs = {r.work_date: r for r in db.query(M.AttendanceRecord).filter(M.AttendanceRecord.employment_id == e.id,
                                                                        M.AttendanceRecord.work_date.between(start, end))}
    leaves = db.query(M.LeaveRequest).filter(M.LeaveRequest.employment_id == e.id, M.LeaveRequest.status == LS.APPROVED,
                                             M.LeaveRequest.start_date <= end, M.LeaveRequest.end_date >= start).all()
    full_leave: dict[date, M.LeaveRequest] = {}
    for lv in leaves:
        if lv.leave_type in (LeaveType.HALF_DAY_AM, LeaveType.HALF_DAY_PM):
            continue
        d = max(lv.start_date, start)
        while d <= min(lv.end_date, end):
            full_leave[d] = lv
            d += timedelta(days=1)
    absents = set(absent_days(e, recs, set(full_leave), start, end, today))
    days, s = [], {"workdays": 0, "attended": 0, "late": 0, "earlyLeave": 0, "absent": 0, "leaveDays": 0.0}
    d = start
    while d <= end:
        r, wd = recs.get(d), is_workday(e.contract, d) and e.start_date <= d and (e.end_date is None or d <= e.end_date)
        status = r.status.value if r else ("ON_LEAVE" if d in full_leave and wd else "ABSENT" if d in absents else None)
        days.append({"date": d.isoformat(), "isWorkday": wd, "status": status, "computed": r is None and status is not None,
                     "record": att_out(r) if r else None, "leaveType": full_leave[d].leave_type.value if d in full_leave else None})
        if wd and d <= today:
            s["workdays"] += 1
        if r and r.check_in_at:
            s["attended"] += 1
        if status in ("LATE", "LATE_EARLY_LEAVE"):
            s["late"] += 1
        if status in ("EARLY_LEAVE", "LATE_EARLY_LEAVE"):
            s["earlyLeave"] += 1
        if status == "ABSENT":
            s["absent"] += 1
        if status == "ON_LEAVE":
            s["leaveDays"] += 1
        if r and r.half_day_type:
            s["leaveDays"] += 0.5
        d += timedelta(days=1)
    return days, s


@router.get("/attendance/me")
def my_attendance(month: str, user: CurrentUser = Depends(require(WK)), db: Session = Depends(get_db)):
    e = current_employment(db, user.id) or db.query(M.Employment).filter_by(worker_id=user.id).order_by(M.Employment.start_date.desc()).first()
    if not e:
        return ok({"days": [], "summary": None})
    days, s = month_days(db, e, month)
    return ok({"days": days, "summary": s})


@router.get("/attendance")
def attendance(month: str, employment_id: int | None = None, user: CurrentUser = Depends(require(CM, VM)), db: Session = Depends(get_db)):
    start, end = month_range(month)
    out = []
    for e in scoped_emps(db, user, employment_id):
        if e.start_date > end or (e.end_date and e.end_date < start):
            continue
        days, s = month_days(db, e, month)
        row = {"employmentId": e.id, "workerName": e.worker.name, "companyName": e.company.name, "summary": s}
        if employment_id:
            row["days"] = days
        out.append(row)
    return ok(out)


class CorrectIn(In):
    employment_id: int
    work_date: date
    check_in: time | None = None
    check_out: time | None = None
    status: AT
    note: str


@router.put("/attendance/correct")
def correct(body: CorrectIn, user: CurrentUser = Depends(require(CM)), db: Session = Depends(get_db)):
    e = db.get(M.Employment, body.employment_id)
    if not e or e.company_id != user.company_id:
        raise forbidden()
    r = db.query(M.AttendanceRecord).filter_by(employment_id=e.id, work_date=body.work_date).first() or M.AttendanceRecord(employment_id=e.id, work_date=body.work_date)
    r.check_in_at = kst_to_utc_naive(body.work_date, body.check_in) if body.check_in else None
    r.check_out_at = kst_to_utc_naive(body.work_date, body.check_out) if body.check_out else None
    r.status, r.corrected_by, r.corrected_at, r.correction_note = body.status, user.id, utcnow(), body.note
    db.add(r)
    notify(db, [e.worker_id], "ATTENDANCE_CORRECTED", "근태 정정", f"{body.work_date} 근태가 정정되었습니다: {body.note}", "/m/attendance")
    db.commit()
    return ok(att_out(r))


def xlsx_response(wb, filename: str) -> StreamingResponse:
    import io
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"})


def fmt_kst(dt: datetime | None) -> str:
    return utc_naive_to_kst(dt).strftime("%H:%M") if dt else ""


@router.get("/attendance/export.xlsx")
def attendance_xlsx(month: str, user: CurrentUser = Depends(require(CM, VM)), db: Session = Depends(get_db)):
    from openpyxl import Workbook
    wb = Workbook()
    ws1, ws2 = wb.active, wb.create_sheet("월 집계")
    ws1.title = "일별"
    ws1.append(["근로자", "기업", "날짜", "근무일", "상태", "출근", "퇴근", "지각(분)", "조퇴(분)", "정정 사유"])
    ws2.append(["근로자", "기업", "근무일수", "출근일", "지각", "조퇴", "결근", "휴가일수"])
    start, end = month_range(month)
    for e in scoped_emps(db, user):
        if e.start_date > end or (e.end_date and e.end_date < start):
            continue
        days, s = month_days(db, e, month)
        for d in days:
            r = d["record"]
            ws1.append([e.worker.name, e.company.name, d["date"], "Y" if d["isWorkday"] else "", d["status"] or "",
                        r["checkInAt"][11:16] if r and r["checkInAt"] else "", r["checkOutAt"][11:16] if r and r["checkOutAt"] else "",
                        r["lateMinutes"] if r else "", r["earlyLeaveMinutes"] if r else "", r["correctionNote"] or "" if r else ""])
        ws2.append([e.worker.name, e.company.name, s["workdays"], s["attended"], s["late"], s["earlyLeave"], s["absent"], s["leaveDays"]])
    return xlsx_response(wb, f"근태_{month}.xlsx")


# ---------------- LEAVES ----------------
def leave_out(lv: M.LeaveRequest) -> dict:
    return ser(lv, workerName=lv.employment.worker.name)


def leave_balance(db: Session, e: M.Employment, year: int) -> dict:
    g = db.query(M.LeaveGrant).filter_by(employment_id=e.id, year=year).first()
    granted = float(g.granted_days) if g else float(e.contract.annual_leave_days or 0) if e.contract else 0.0
    used = sum(float(lv.days) for lv in db.query(M.LeaveRequest).filter(M.LeaveRequest.employment_id == e.id, M.LeaveRequest.status == LS.APPROVED,
               M.LeaveRequest.leave_type.in_([LeaveType.ANNUAL, LeaveType.HALF_DAY_AM, LeaveType.HALF_DAY_PM])) if lv.start_date.year == year)
    return {"year": year, "granted": granted, "used": used, "remaining": granted - used}


@router.get("/leaves/me")
def my_leaves(user: CurrentUser = Depends(require(WK)), db: Session = Depends(get_db)):
    e = current_employment(db, user.id)
    if not e:
        return ok({"balance": None, "requests": []})
    rows = db.query(M.LeaveRequest).filter_by(employment_id=e.id).order_by(M.LeaveRequest.start_date.desc())
    return ok({"balance": leave_balance(db, e, today_kst().year), "requests": [leave_out(lv) for lv in rows]})


class LeaveIn(In):
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: str | None = None


@router.post("/leaves")
def request_leave(body: LeaveIn, user: CurrentUser = Depends(require(WK)), db: Session = Depends(get_db)):
    e = my_emp(db, user, active_only=False)
    half = body.leave_type in (LeaveType.HALF_DAY_AM, LeaveType.HALF_DAY_PM)
    end = body.start_date if half else body.end_date
    if end < body.start_date:
        raise AppError("INVALID_RANGE", "종료일이 시작일보다 빠릅니다.")
    days = Decimal("0.5") if half else Decimal(sum(1 for i in range((end - body.start_date).days + 1) if is_workday(e.contract, body.start_date + timedelta(i))))
    if days == 0:
        raise AppError("NO_WORKDAY", "선택한 기간에 근무일이 없습니다.")
    if body.leave_type in (LeaveType.ANNUAL, LeaveType.HALF_DAY_AM, LeaveType.HALF_DAY_PM) and leave_balance(db, e, body.start_date.year)["remaining"] < float(days):
        raise AppError("INSUFFICIENT_LEAVE", "잔여 연차가 부족합니다.")
    lv = M.LeaveRequest(employment_id=e.id, leave_type=body.leave_type, start_date=body.start_date, end_date=end, days=days, reason=body.reason)
    db.add(lv)
    notify(db, company_cm_ids(db, e.company_id), "LEAVE_REQUESTED", "휴가 신청", f"{user.name} {body.start_date}~{end} ({days}일)", "/admin/leaves")
    db.commit()
    return ok(leave_out(lv))


@router.post("/leaves/{lid}/withdraw")
def withdraw_leave(lid: int, user: CurrentUser = Depends(require(WK)), db: Session = Depends(get_db)):
    lv = db.get(M.LeaveRequest, lid)
    if not lv or lv.employment.worker_id != user.id or lv.status != LS.PENDING:
        raise AppError("INVALID_TRANSITION", "철회할 수 없는 신청입니다.")
    lv.status = LS.WITHDRAWN
    db.commit()
    return ok(leave_out(lv))


@router.get("/leaves")
def leaves(user: CurrentUser = Depends(require(CM, VM)), db: Session = Depends(get_db)):
    ids = [e.id for e in scoped_emps(db, user)]
    rows = db.query(M.LeaveRequest).filter(M.LeaveRequest.employment_id.in_(ids)).order_by(M.LeaveRequest.id.desc())
    today = today_kst()
    balances = [{"employmentId": e.id, "workerName": e.worker.name, **leave_balance(db, e, today.year)} for e in scoped_emps(db, user) if is_open_employment(e, today)]
    return ok({"requests": [leave_out(lv) for lv in rows], "balances": balances})


class ReviewIn(In):
    note: str | None = None


def _get_leave(db: Session, lid: int, user: CurrentUser, status: LS) -> M.LeaveRequest:
    lv = db.get(M.LeaveRequest, lid)
    if not lv or lv.employment.company_id != user.company_id:
        raise not_found("휴가")
    if lv.status != status:
        raise AppError("INVALID_TRANSITION", "현재 상태에서는 처리할 수 없습니다.")
    return lv


@router.post("/leaves/{lid}/approve")
def approve_leave(lid: int, user: CurrentUser = Depends(require(CM)), db: Session = Depends(get_db)):
    lv = _get_leave(db, lid, user, LS.PENDING)
    lv.status, lv.reviewed_by, lv.reviewed_at = LS.APPROVED, user.id, utcnow()
    notify(db, [lv.employment.worker_id], "LEAVE_APPROVED", "휴가 승인", f"{lv.start_date}~{lv.end_date} 휴가가 승인되었습니다.", "/m/more/leaves")
    db.commit()
    return ok(leave_out(lv))


@router.post("/leaves/{lid}/reject")
def reject_leave(lid: int, body: ReviewIn, user: CurrentUser = Depends(require(CM)), db: Session = Depends(get_db)):
    lv = _get_leave(db, lid, user, LS.PENDING)
    lv.status, lv.reviewed_by, lv.reviewed_at, lv.review_note = LS.REJECTED, user.id, utcnow(), body.note
    notify(db, [lv.employment.worker_id], "LEAVE_REJECTED", "휴가 반려", body.note or "", "/m/more/leaves")
    db.commit()
    return ok(leave_out(lv))


@router.post("/leaves/{lid}/cancel")
def cancel_leave(lid: int, body: ReviewIn, user: CurrentUser = Depends(require(CM)), db: Session = Depends(get_db)):
    lv = _get_leave(db, lid, user, LS.APPROVED)
    lv.status, lv.review_note = LS.CANCELLED, body.note
    notify(db, [lv.employment.worker_id], "LEAVE_CANCELLED", "휴가 취소", body.note or "", "/m/more/leaves")
    db.commit()
    return ok(leave_out(lv))


class GrantIn(In):
    employment_id: int
    year: int
    granted_days: Decimal


@router.put("/leave-grants")
def grant(body: GrantIn, user: CurrentUser = Depends(require(CM)), db: Session = Depends(get_db)):
    e = db.get(M.Employment, body.employment_id)
    if not e or e.company_id != user.company_id:
        raise forbidden()
    g = db.query(M.LeaveGrant).filter_by(employment_id=e.id, year=body.year).first() or M.LeaveGrant(employment_id=e.id, year=body.year, created_by=user.id)
    g.granted_days = body.granted_days
    db.add(g)
    db.commit()
    return ok(leave_balance(db, e, body.year))


# ---------------- TASKS ----------------
TASK_FLOW = {TS.ASSIGNED: {TS.IN_PROGRESS, TS.COMPLETED, TS.CANCELLED}, TS.IN_PROGRESS: {TS.COMPLETED, TS.CANCELLED},
             TS.COMPLETED: {TS.IN_PROGRESS}, TS.CANCELLED: set()}


def task_out(t: M.Task, today: date | None = None) -> dict:
    today = today or today_kst()
    return ser(t, workerName=t.employment.worker.name, overdue=bool(t.due_date and t.due_date < today and t.status in (TS.ASSIGNED, TS.IN_PROGRESS)),
               employmentEnded=employment_status(t.employment, today) == EmploymentStatus.RESIGNED)


def _move(t: M.Task, to: TS, user: CurrentUser) -> None:
    if to not in TASK_FLOW[t.status]:
        raise AppError("INVALID_TRANSITION", "현재 상태에서는 처리할 수 없습니다.")
    t.status, t.status_changed_by, t.status_changed_at = to, user.id, utcnow()


def get_task(db: Session, tid: int, user: CurrentUser) -> M.Task:
    t = db.get(M.Task, tid)
    if not t:
        raise not_found("업무")
    if (user.role == CM and t.company_id != user.company_id) or (user.role == WK and t.employment.worker_id != user.id):
        raise forbidden()
    return t


@router.get("/tasks")
def tasks(status: TS | None = None, employment_id: int | None = None, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(M.Task)
    if user.role == WK:
        e = current_employment(db, user.id)
        if not e:
            return ok([])
        q = q.filter(M.Task.employment_id == e.id)
    elif user.role == CM:
        q = q.filter(M.Task.company_id == user.company_id)
    if employment_id:
        q = q.filter(M.Task.employment_id == employment_id)
    if status:
        q = q.filter(M.Task.status == status)
    today = today_kst()
    order = {TaskPriority.HIGH: 0, TaskPriority.NORMAL: 1, TaskPriority.LOW: 2}
    rows = sorted(q.all(), key=lambda t: (t.status in (TS.COMPLETED, TS.CANCELLED), t.due_date or date.max, order[t.priority], -t.id))
    return ok([task_out(t, today) for t in rows])


@router.get("/tasks/{tid}")
def task_detail(tid: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    t = get_task(db, tid, user)
    entries = db.query(M.WorkLogEntry, M.WorkLog.work_date).join(M.WorkLog).filter(M.WorkLogEntry.task_id == t.id).order_by(M.WorkLog.work_date).all()
    return ok(task_out(t) | {"logEntries": [ser(en, workDate=d) for en, d in entries]})


class TaskIn(In):
    employment_id: int
    title: str
    description: str | None = None
    priority: TaskPriority = TaskPriority.NORMAL
    due_date: date | None = None


@router.post("/tasks")
def create_task(body: TaskIn, user: CurrentUser = Depends(require(CM)), db: Session = Depends(get_db)):
    e = db.get(M.Employment, body.employment_id)
    if not e or e.company_id != user.company_id or not is_open_employment(e, today_kst()):
        raise AppError("INVALID_EMPLOYMENT", "배정할 수 없는 근로자입니다.")
    if body.due_date and body.due_date < e.start_date:
        raise AppError("DUE_BEFORE_START", "기한은 출근 시작일 이후여야 합니다.")
    t = M.Task(**body.model_dump(), company_id=e.company_id, assigned_by=user.id)
    db.add(t)
    db.flush()
    notify(db, [e.worker_id], "TASK_ASSIGNED", "새 업무", t.title, f"/m/tasks/{t.id}")
    db.commit()
    return ok(task_out(t))


@router.put("/tasks/{tid}")
def update_task(tid: int, body: TaskIn, user: CurrentUser = Depends(require(CM)), db: Session = Depends(get_db)):
    t = get_task(db, tid, user)
    if t.status in (TS.COMPLETED, TS.CANCELLED):
        raise AppError("TASK_CLOSED", "완료되거나 취소된 업무는 수정할 수 없습니다.")
    t.title, t.description, t.priority, t.due_date = body.title, body.description, body.priority, body.due_date
    notify(db, [t.employment.worker_id], "TASK_UPDATED", "업무 변경", t.title, f"/m/tasks/{t.id}")
    db.commit()
    return ok(task_out(t))


class NoteIn(In):
    note: str | None = None


@router.post("/tasks/{tid}/start")
def start_task(tid: int, user: CurrentUser = Depends(require(WK)), db: Session = Depends(get_db)):
    t = get_task(db, tid, user)
    if t.status != TS.ASSIGNED:
        raise AppError("INVALID_TRANSITION", "배정됨 상태에서만 시작할 수 있습니다.")
    _move(t, TS.IN_PROGRESS, user)
    t.started_at = t.started_at or utcnow()
    db.commit()
    return ok(task_out(t))


@router.post("/tasks/{tid}/complete")
def complete_task(tid: int, body: NoteIn, user: CurrentUser = Depends(require(WK)), db: Session = Depends(get_db)):
    t = get_task(db, tid, user)
    if employment_status(t.employment, today_kst()) == EmploymentStatus.RESIGNED:
        raise AppError("EMPLOYMENT_ENDED", "재직이 종료된 업무입니다.")
    _move(t, TS.COMPLETED, user)
    t.completed_at, t.completion_note = utcnow(), body.note
    notify(db, company_cm_ids(db, t.company_id), "TASK_COMPLETED", "업무 완료", f"{user.name} · {t.title}", f"/admin/tasks/{t.id}")
    db.commit()
    return ok(task_out(t))


@router.post("/tasks/{tid}/cancel")
def cancel_task(tid: int, body: NoteIn, user: CurrentUser = Depends(require(CM)), db: Session = Depends(get_db)):
    t = get_task(db, tid, user)
    _move(t, TS.CANCELLED, user)
    t.cancel_reason = body.note
    notify(db, [t.employment.worker_id], "TASK_CANCELLED", "업무 취소", t.title, f"/m/tasks/{t.id}")
    db.commit()
    return ok(task_out(t))


@router.post("/tasks/{tid}/reopen")
def reopen_task(tid: int, body: NoteIn, user: CurrentUser = Depends(require(CM, WK)), db: Session = Depends(get_db)):
    t = get_task(db, tid, user)
    if user.role == WK and (not t.completed_at or utc_naive_to_kst(t.completed_at).date() != today_kst()):
        raise AppError("REOPEN_NOT_ALLOWED", "완료한 당일에만 되돌릴 수 있습니다.")
    _move(t, TS.IN_PROGRESS, user)
    if user.role == CM:
        notify(db, [t.employment.worker_id], "TASK_REOPENED", "업무 재오픈", f"{t.title}: {body.note or ''}", f"/m/tasks/{t.id}")
    db.commit()
    return ok(task_out(t))


# ---------------- WORK LOGS ----------------
WL_FLOW = {WS.DRAFT: {WS.SUBMITTED}, WS.SUBMITTED: {WS.CONFIRMED, WS.RETURNED, WS.SUBMITTED}, WS.RETURNED: {WS.SUBMITTED}, WS.CONFIRMED: {WS.SUBMITTED}}


def wl_out(w: M.WorkLog) -> dict:
    return ser(w, workerName=w.employment.worker.name, entries=[ser(en) for en in w.entries],
               files=[{"id": f.file.id, "name": f.file.original_name, "size": f.file.size_bytes} for f in w.files])


def recalc_task_minutes(db: Session, task_ids: set[int]) -> None:
    for tid in task_ids:
        total = sum(en.minutes for en in db.query(M.WorkLogEntry).join(M.WorkLog).filter(M.WorkLogEntry.task_id == tid,
                    M.WorkLog.status.in_([WS.SUBMITTED, WS.CONFIRMED, WS.RETURNED])))
        db.get(M.Task, tid).total_minutes = total


def _my_log(db: Session, user: CurrentUser, d: date, create: bool) -> tuple[M.Employment, M.WorkLog | None]:
    e = my_emp(db, user)
    w = db.query(M.WorkLog).filter_by(employment_id=e.id, work_date=d).first()
    if not w and create:
        has_att = db.query(M.AttendanceRecord).filter_by(employment_id=e.id, work_date=d).first()
        if d != today_kst() and not has_att:
            raise AppError("NO_ATTENDANCE", "출근 기록이 있는 날 또는 오늘만 작성할 수 있습니다.")
        w = M.WorkLog(employment_id=e.id, company_id=e.company_id, work_date=d)
        db.add(w)
        db.flush()
    return e, w


@router.get("/work-logs/me")
def my_logs(month: str, user: CurrentUser = Depends(require(WK)), db: Session = Depends(get_db)):
    e = current_employment(db, user.id)
    if not e:
        return ok([])
    start, end = month_range(month)
    logs = {w.work_date: w for w in db.query(M.WorkLog).filter(M.WorkLog.employment_id == e.id, M.WorkLog.work_date.between(start, end))}
    atts = {r.work_date for r in db.query(M.AttendanceRecord).filter(M.AttendanceRecord.employment_id == e.id, M.AttendanceRecord.work_date.between(start, end),
                                                                     M.AttendanceRecord.check_in_at.isnot(None))}
    out, d = [], start
    while d <= end:
        w = logs.get(d)
        out.append({"date": d.isoformat(), "attended": d in atts, "status": w.status.value if w else None, "totalMinutes": w.total_minutes if w else 0})
        d += timedelta(days=1)
    return ok(out)


@router.get("/work-logs/me/{d}")
def my_log(d: date, user: CurrentUser = Depends(require(WK)), db: Session = Depends(get_db)):
    e, w = _my_log(db, user, d, False)
    tasks = db.query(M.Task).filter(M.Task.employment_id == e.id, M.Task.status != TS.CANCELLED).order_by(M.Task.status, M.Task.due_date).all()
    return ok({"log": wl_out(w) if w else None, "tasks": [{"id": t.id, "title": t.title, "status": t.status.value} for t in tasks]})


class EntryIn(In):
    task_id: int | None = None
    title: str
    content: str
    minutes: int


class WorkLogIn(In):
    summary: str | None = None
    issues: str | None = None
    entries: list[EntryIn] = []


@router.put("/work-logs/me/{d}")
def save_log(d: date, body: WorkLogIn, user: CurrentUser = Depends(require(WK)), db: Session = Depends(get_db)):
    e, w = _my_log(db, user, d, True)
    if w.status == WS.CONFIRMED:
        raise AppError("WORK_LOG_ALREADY_CONFIRMED", "확인된 업무일지는 수정할 수 없습니다.")
    valid = {t.id for t in db.query(M.Task).filter(M.Task.employment_id == e.id, M.Task.status != TS.CANCELLED)}
    w.summary, w.issues = body.summary, body.issues
    w.entries.clear()
    db.flush()
    for i, en in enumerate(body.entries):
        if en.task_id and en.task_id not in valid:
            raise AppError("INVALID_TASK", "선택할 수 없는 업무입니다.")
        w.entries.append(M.WorkLogEntry(task_id=en.task_id, title=en.title, content=en.content, minutes=max(0, en.minutes), sort_order=i))
    db.commit()
    return ok(wl_out(w))


@router.post("/work-logs/me/{d}/submit")
def submit_log(d: date, user: CurrentUser = Depends(require(WK)), db: Session = Depends(get_db)):
    e, w = _my_log(db, user, d, False)
    if not w or not w.entries:
        raise AppError("EMPTY_WORK_LOG", "항목을 1개 이상 작성해 주세요.")
    if WS.SUBMITTED not in WL_FLOW[w.status] or w.status == WS.CONFIRMED:
        raise AppError("INVALID_TRANSITION", "제출할 수 없는 상태입니다.")
    now = utcnow()
    w.status, w.submitted_at, w.total_minutes = WS.SUBMITTED, now, sum(en.minutes for en in w.entries)
    w.first_submitted_at = w.first_submitted_at or now
    db.flush()
    recalc_task_minutes(db, {en.task_id for en in w.entries if en.task_id})
    notify(db, company_cm_ids(db, e.company_id), "WORK_LOG_SUBMITTED", "업무일지 제출", f"{user.name} · {d}", f"/admin/work-logs/{w.id}")
    db.commit()
    return ok(wl_out(w))


@router.post("/work-logs/me/{d}/files")
@limiter.limit(settings.rate_limit_upload)
async def upload_log_file(request: Request, d: date, file: UploadFile = File(...), user: CurrentUser = Depends(require(WK)), db: Session = Depends(get_db)):
    e, w = _my_log(db, user, d, True)
    if w.status == WS.CONFIRMED:
        raise AppError("WORK_LOG_ALREADY_CONFIRMED", "확인된 업무일지는 수정할 수 없습니다.")
    f = await save_upload(db, file, FilePurpose.WORK_LOG_ATTACHMENT, user.id)
    w.files.append(M.WorkLogFile(file_id=f.id))
    db.commit()
    return ok(wl_out(w))


@router.delete("/work-logs/me/{d}/files/{fid}")
def delete_log_file(d: date, fid: int, user: CurrentUser = Depends(require(WK)), db: Session = Depends(get_db)):
    e, w = _my_log(db, user, d, False)
    if not w or w.status == WS.CONFIRMED:
        raise AppError("WORK_LOG_ALREADY_CONFIRMED", "삭제할 수 없습니다.")
    w.files = [lf for lf in w.files if lf.file_id != fid]
    db.commit()
    return ok(wl_out(w))


def get_log(db: Session, wid: int, user: CurrentUser) -> M.WorkLog:
    w = db.get(M.WorkLog, wid)
    if not w:
        raise not_found("업무일지")
    if (user.role == CM and w.company_id != user.company_id) or (user.role == WK and w.employment.worker_id != user.id):
        raise forbidden()
    return w


@router.get("/work-logs")
def list_logs(status: WS | None = None, employment_id: int | None = None, month: str | None = None,
              user: CurrentUser = Depends(require(CM, VM)), db: Session = Depends(get_db)):
    q = db.query(M.WorkLog).filter(M.WorkLog.status != WS.DRAFT)
    if user.role == CM:
        q = q.filter(M.WorkLog.company_id == user.company_id)
    if status:
        q = q.filter(M.WorkLog.status == status)
    if employment_id:
        q = q.filter(M.WorkLog.employment_id == employment_id)
    if month:
        q = q.filter(M.WorkLog.work_date.between(*month_range(month)))
    return ok([ser(w, workerName=w.employment.worker.name, companyName=w.employment.company.name, entryCount=len(w.entries))
               for w in q.order_by(M.WorkLog.work_date.desc(), M.WorkLog.id.desc()).limit(300)])


@router.get("/work-logs/missing")
def missing_logs(month: str, user: CurrentUser = Depends(require(CM, VM)), db: Session = Depends(get_db)):
    start, end = month_range(month)
    out = []
    for e in scoped_emps(db, user):
        atts = db.query(M.AttendanceRecord).filter(M.AttendanceRecord.employment_id == e.id, M.AttendanceRecord.work_date.between(start, end),
                                                   M.AttendanceRecord.check_in_at.isnot(None)).all()
        done = {w.work_date for w in db.query(M.WorkLog).filter(M.WorkLog.employment_id == e.id, M.WorkLog.first_submitted_at.isnot(None))}
        miss = sorted(r.work_date.isoformat() for r in atts if r.work_date not in done)
        if miss:
            out.append({"employmentId": e.id, "workerName": e.worker.name, "companyName": e.company.name, "dates": miss})
    return ok(out)


@router.get("/work-logs/stats")
def log_stats(month: str, user: CurrentUser = Depends(require(CM, VM)), db: Session = Depends(get_db)):
    start, end = month_range(month)
    out = []
    for e in scoped_emps(db, user):
        if e.start_date > end or (e.end_date and e.end_date < start):
            continue
        attended = db.query(M.AttendanceRecord).filter(M.AttendanceRecord.employment_id == e.id, M.AttendanceRecord.work_date.between(start, end),
                                                       M.AttendanceRecord.check_in_at.isnot(None)).count()
        logs = db.query(M.WorkLog).filter(M.WorkLog.employment_id == e.id, M.WorkLog.work_date.between(start, end)).all()
        submitted = [w for w in logs if w.first_submitted_at]
        by_task: dict[str, int] = defaultdict(int)
        for w in submitted:
            for en in w.entries:
                by_task[en.title] += en.minutes
        out.append({"employmentId": e.id, "workerName": e.worker.name, "attended": attended, "submitted": len(submitted),
                    "confirmed": sum(1 for w in logs if w.status == WS.CONFIRMED),
                    "submitRate": round(len(submitted) / attended * 100) if attended else 0,
                    "totalMinutes": sum(w.total_minutes for w in submitted),
                    "topTasks": [{"title": k, "minutes": v} for k, v in sorted(by_task.items(), key=lambda x: -x[1])[:5]]})
    return ok(out)


@router.get("/work-logs/export.xlsx")
def logs_xlsx(month: str, user: CurrentUser = Depends(require(CM, VM)), db: Session = Depends(get_db)):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "업무일지"
    ws.append(["근로자", "기업", "근무일", "업무명", "연결 업무", "수행 내용", "소요(분)", "상태", "제출 시각", "확인 시각"])
    q = db.query(M.WorkLog).filter(M.WorkLog.work_date.between(*month_range(month)), M.WorkLog.status != WS.DRAFT)
    if user.role == CM:
        q = q.filter(M.WorkLog.company_id == user.company_id)
    for w in q.order_by(M.WorkLog.work_date):
        for en in w.entries:
            ws.append([w.employment.worker.name, w.employment.company.name, w.work_date.isoformat(), en.title, "Y" if en.task_id else "",
                       en.content, en.minutes, w.status.value, fmt_kst(w.submitted_at), fmt_kst(w.reviewed_at)])
    return xlsx_response(wb, f"업무일지_{month}.xlsx")


@router.get("/work-logs/{wid}")
def log_detail(wid: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(wl_out(get_log(db, wid, user)))


class CommentIn(In):
    comment: str | None = None


def _review(db: Session, wid: int, user: CurrentUser, to: WS, comment: str | None, frm: set[WS]) -> M.WorkLog:
    w = get_log(db, wid, user)
    if w.status not in frm:
        raise AppError("INVALID_TRANSITION", "현재 상태에서는 처리할 수 없습니다.")
    w.status, w.reviewed_by, w.reviewed_at, w.review_comment = to, user.id, utcnow(), comment
    return w


@router.post("/work-logs/{wid}/confirm")
def confirm_log(wid: int, body: CommentIn, user: CurrentUser = Depends(require(CM)), db: Session = Depends(get_db)):
    w = _review(db, wid, user, WS.CONFIRMED, body.comment, {WS.SUBMITTED})
    notify(db, [w.employment.worker_id], "WORK_LOG_CONFIRMED", "업무일지 확인", f"{w.work_date} 업무일지가 확인되었습니다.", f"/m/log?date={w.work_date}")
    db.commit()
    return ok(wl_out(w))


@router.post("/work-logs/{wid}/return")
def return_log(wid: int, body: CommentIn, user: CurrentUser = Depends(require(CM)), db: Session = Depends(get_db)):
    if not body.comment:
        raise AppError("COMMENT_REQUIRED", "보완 요청 사유를 적어 주세요.")
    w = _review(db, wid, user, WS.RETURNED, body.comment, {WS.SUBMITTED})
    notify(db, [w.employment.worker_id], "WORK_LOG_RETURNED", "업무일지 보완 요청", f"{w.work_date}: {body.comment}", f"/m/log?date={w.work_date}")
    db.commit()
    return ok(wl_out(w))


@router.post("/work-logs/{wid}/unconfirm")
def unconfirm_log(wid: int, user: CurrentUser = Depends(require(CM)), db: Session = Depends(get_db)):
    w = _review(db, wid, user, WS.SUBMITTED, None, {WS.CONFIRMED})
    db.commit()
    return ok(wl_out(w))


# ---------------- FILES ----------------
@router.get("/files/{fid}/url")
def file_url(fid: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    f = db.get(M.File, fid)
    if not f:
        raise not_found("파일")
    link = db.query(M.WorkLogFile).filter_by(file_id=fid).first()
    owner = db.query(M.WorkerProfile).filter_by(photo_file_id=fid).first()
    if link:
        get_log(db, link.work_log_id, user)
    elif owner:
        from .hiring import can_view_resume
        if not can_view_resume(db, user, owner.user_id):
            raise forbidden()
    elif user.role == WK and f.uploaded_by != user.id:
        raise forbidden()
    return ok({"url": download_url(f), "name": f.original_name})


@router.get("/files/{fid}/content")
def file_content(fid: int, sig: str, db: Session = Depends(get_db)):
    f = db.get(M.File, fid)
    if not f or not verify_sig(fid, sig):
        raise forbidden("링크가 만료되었습니다.")
    return FileResponse(Path(settings.upload_dir) / f.storage_key, media_type=f.mime_type, filename=f.original_name)
