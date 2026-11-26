"""CNSL, MESG, EMRP, DASH."""
from collections import defaultdict
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models as M
from ..config import settings
from ..core import CM, SA, VM, WK, AppError, CurrentUser, forbidden, get_current_user, not_found, ok, require, ser
from ..db import get_db, utcnow
from ..domain import (
    ALL,
    KST,
    UTC,
    allowed_recipient_ids,
    can_send,
    employment_status,
    hourly_wage,
    is_open_employment,
    is_workday,
    monthly_scheduled_hours,
    recognition,
    today_kst,
    utc_naive_to_kst,
)
from ..enums import (
    CounselingMethod,
    EmploymentStatus,
    JobPostingStatus,
    JobSeekingStatus,
    LeaveStatus,
    LeaveType,
    ResignationStatus,
    TaskStatus,
    UserStatus,
)
from ..enums import MessageAudience as MA
from ..enums import RecognitionResult as RR
from ..enums import WorkLogStatus as WS
from ..schemas import In
from .work import month_days, month_range, xlsx_response

router = APIRouter()

# ---------------- COUNSELING (VM only) ----------------
class CnslIn(In):
    worker_id: int
    method: CounselingMethod
    counseled_at: datetime
    topic: str
    content: str
    condition_score: int
    follow_up: str | None = None


def _utc(dt: datetime) -> datetime:
    return (dt if dt.tzinfo else dt.replace(tzinfo=KST)).astimezone(UTC).replace(tzinfo=None)


def cnsl_out(db: Session, r: M.CounselingReport) -> dict:
    return ser(r, workerName=db.get(M.User, r.worker_id).name, authorName=db.get(M.User, r.author_id).name,
               companyName=db.get(M.Company, r.company_id).name if r.company_id else None)


@router.get("/counseling")
def list_cnsl(worker_id: int | None = None, company_id: int | None = None, frm: date | None = Query(default=None, alias="from"), to: date | None = None,
              user: CurrentUser = Depends(require(VM)), db: Session = Depends(get_db)):
    q = db.query(M.CounselingReport).filter(M.CounselingReport.deleted_at.is_(None))
    if worker_id:
        q = q.filter(M.CounselingReport.worker_id == worker_id)
    if company_id:
        q = q.filter(M.CounselingReport.company_id == company_id)
    if frm:
        q = q.filter(M.CounselingReport.counseled_at >= datetime.combine(frm, datetime.min.time()))
    if to:
        q = q.filter(M.CounselingReport.counseled_at < datetime.combine(to + timedelta(days=1), datetime.min.time()))
    return ok([cnsl_out(db, r) for r in q.order_by(M.CounselingReport.counseled_at.desc())])


@router.post("/counseling")
def create_cnsl(body: CnslIn, user: CurrentUser = Depends(require(VM)), db: Session = Depends(get_db)):
    if not 1 <= body.condition_score <= 5:
        raise AppError("INVALID_SCORE", "상태 점수는 1~5입니다.")
    from ..domain import current_employment
    e = current_employment(db, body.worker_id)
    r = M.CounselingReport(**body.model_dump(exclude={"counseled_at"}), counseled_at=_utc(body.counseled_at), author_id=user.id,
                           employment_id=e.id if e else None, company_id=e.company_id if e else None)
    db.add(r)
    db.commit()
    return ok(cnsl_out(db, r))


@router.put("/counseling/{rid}")
def update_cnsl(rid: int, body: CnslIn, user: CurrentUser = Depends(require(VM)), db: Session = Depends(get_db)):
    r = db.get(M.CounselingReport, rid)
    if not r or r.deleted_at:
        raise not_found("상담보고서")
    for k, v in body.model_dump(exclude={"counseled_at", "worker_id"}).items():
        setattr(r, k, v)
    r.counseled_at, r.updated_by = _utc(body.counseled_at), user.id
    db.commit()
    return ok(cnsl_out(db, r))


@router.delete("/counseling/{rid}")
def delete_cnsl(rid: int, user: CurrentUser = Depends(require(VM)), db: Session = Depends(get_db)):
    r = db.get(M.CounselingReport, rid)
    if not r:
        raise not_found("상담보고서")
    r.deleted_at = utcnow()
    db.commit()
    return ok(True)


# ---------------- MESSAGES ----------------
ROLE_LABEL = {WK: "근로자", CM: "기업 담당자", VM: "브이드림 매니저", SA: "시스템관리자"}


def person(u: M.User) -> dict:
    return {"id": u.id, "name": u.name, "role": u.role.value, "roleLabel": ROLE_LABEL[u.role], "companyName": u.company.name if u.company else None}


@router.get("/messages/recipients")
def recipients(q: str | None = None, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    me = db.get(M.User, user.id)
    allowed = allowed_recipient_ids(db, me, today_kst())
    base = db.query(M.User).filter(M.User.status == UserStatus.ACTIVE, M.User.deleted_at.is_(None), M.User.id != user.id)
    if allowed == ALL:
        if not q:
            return ok({"groups": [], "searchRequired": True, "canSend": True, "managerMissing": False})
        rows = base.filter(M.User.name.contains(q) | M.User.login_id.contains(q)).order_by(M.User.name).limit(20).all()
        return ok({"groups": [{"label": "검색 결과", "people": [person(u) for u in rows]}], "searchRequired": True, "canSend": True, "managerMissing": False})
    rows = base.filter(M.User.id.in_(allowed)).order_by(M.User.name).all() if allowed else []
    groups = defaultdict(list)
    for u in rows:
        groups[u.role].append(person(u))
    order = [(CM, "기업 담당자"), (VM, "담당 매니저"), (WK, "근로자")]
    manager_missing = user.role in (WK, CM) and bool(allowed) and not groups.get(VM)
    if user.role == CM and not groups.get(VM):
        manager_missing = True
    return ok({"groups": [{"label": lbl, "people": groups[r]} for r, lbl in order if groups.get(r)],
               "searchRequired": False, "canSend": bool(allowed), "managerMissing": manager_missing})


class MsgIn(In):
    recipient_ids: list[int] = []
    audience: MA = MA.INDIVIDUAL
    audience_company_id: int | None = None
    title: str
    body: str
    parent_message_id: int | None = None


def expand_audience(db: Session, body: MsgIn) -> set[int]:
    base = db.query(M.User).filter(M.User.status == UserStatus.ACTIVE, M.User.deleted_at.is_(None))
    if body.audience == MA.ALL_WORKERS:
        return {u.id for u in base.filter(M.User.role == WK)}
    if body.audience == MA.ALL_COMPANY_MANAGERS:
        return {u.id for u in base.filter(M.User.role == CM)}
    if body.audience == MA.ALL_USERS:
        return {u.id for u in base}
    if body.audience == MA.COMPANY_MEMBERS:
        if not body.audience_company_id:
            raise AppError("COMPANY_REQUIRED", "대상 기업을 선택해 주세요.")
        today = today_kst()
        ids = {u.id for u in base.filter(M.User.company_id == body.audience_company_id, M.User.role == CM)}
        ids |= {e.worker_id for e in db.query(M.Employment).filter_by(company_id=body.audience_company_id) if is_open_employment(e, today)}
        return ids
    return set(body.recipient_ids)


@router.post("/messages")
def send(body: MsgIn, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.title.strip() or not body.body.strip() or len(body.title) > 100 or len(body.body) > 2000:
        raise AppError("INVALID_MESSAGE", "제목(100자)과 본문(2,000자)을 확인해 주세요.")
    if body.audience != MA.INDIVIDUAL and user.role != VM:
        raise forbidden("단체 발송은 브이드림 매니저만 할 수 있습니다.")
    me = db.get(M.User, user.id)
    allowed = allowed_recipient_ids(db, me, today_kst())
    ids = expand_audience(db, body) - {user.id}
    if not ids:
        raise AppError("NO_RECIPIENT", "받는 사람을 선택해 주세요.")
    if any(not can_send(allowed, rid) for rid in ids):  # MESG-003
        raise AppError("MESSAGE_RECIPIENT_NOT_ALLOWED", "쪽지를 보낼 수 없는 사용자가 포함되어 있습니다.", 403)
    m = M.Message(sender_id=user.id, title=body.title.strip(), body=body.body, audience=body.audience,
                  audience_company_id=body.audience_company_id, parent_message_id=body.parent_message_id, recipient_count=len(ids))
    m.recipients = [M.MessageRecipient(recipient_id=rid) for rid in ids]
    db.add(m)
    db.commit()
    return ok({"id": m.id, "recipientCount": len(ids)})


def msg_row(m: M.Message, read: datetime | None = None) -> dict:
    return {"id": m.id, "title": m.title, "createdAt": m.created_at.isoformat() + "Z", "sender": person(m.sender),
            "audience": m.audience.value, "recipientCount": m.recipient_count, "readAt": read.isoformat() + "Z" if read else None}


@router.get("/messages/inbox")
def inbox(unread_only: bool = False, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(M.MessageRecipient).filter(M.MessageRecipient.recipient_id == user.id, M.MessageRecipient.deleted_at.is_(None))
    if unread_only:
        q = q.filter(M.MessageRecipient.read_at.is_(None))
    return ok([msg_row(r.message, r.read_at) for r in q.order_by(M.MessageRecipient.id.desc()).limit(200)])


@router.get("/messages/sent")
def sent(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(M.Message).filter(M.Message.sender_id == user.id, M.Message.sender_deleted_at.is_(None)).order_by(M.Message.id.desc()).limit(200)
    return ok([msg_row(m) | {"readCount": sum(1 for r in m.recipients if r.read_at)} for m in rows])


@router.get("/messages/{mid}")
def message(mid: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.get(M.Message, mid)
    if not m:
        raise not_found("쪽지")
    mine = next((r for r in m.recipients if r.recipient_id == user.id), None)
    if m.sender_id != user.id and not mine:
        raise not_found("쪽지")
    if mine and not mine.read_at:
        mine.read_at = utcnow()
        db.commit()
    me = db.get(M.User, user.id)
    can_reply = bool(mine) and can_send(allowed_recipient_ids(db, me, today_kst()), m.sender_id)
    parent = db.get(M.Message, m.parent_message_id) if m.parent_message_id else None
    out = msg_row(m, mine.read_at if mine else None) | {"body": m.body, "canReply": can_reply, "isSender": m.sender_id == user.id,
                                                        "parent": {"title": parent.title, "body": parent.body[:200]} if parent else None}
    if m.sender_id == user.id:
        out["recipients"] = [person(r.recipient) | {"readAt": r.read_at.isoformat() + "Z" if r.read_at else None} for r in m.recipients]
    return ok(out)


@router.delete("/messages/{mid}")
def delete_message(mid: int, box: str, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.get(M.Message, mid)
    if not m:
        raise not_found("쪽지")
    if box == "sent" and m.sender_id == user.id:
        m.sender_deleted_at = utcnow()
    else:
        r = next((r for r in m.recipients if r.recipient_id == user.id), None)
        if not r:
            raise not_found("쪽지")
        r.deleted_at = utcnow()
    db.commit()
    return ok(True)


# ---------------- EMPLOYMENT REPORT (CM only) ----------------
DISCLAIMER = ("이 문서는 my-vdream의 근태·업무일지 기록으로 생성한 참고 자료입니다. 고용 인정 여부와 인원은 한국장애인고용공단 심사로 확정되며, "
              "유급 근로일수와 임금은 급여대장으로 확인해야 합니다.")


def months_between(frm: str, to: str) -> list[str]:
    y, m = map(int, frm.split("-"))
    ty, tm = map(int, to.split("-"))
    out = []
    while (y, m) <= (ty, tm):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def validate_period(frm: str, to: str) -> list[str]:
    try:
        months = months_between(frm, to)
    except ValueError:
        raise AppError("INVALID_PERIOD", "기간 형식은 YYYY-MM입니다.") from None
    if not months:
        raise AppError("INVALID_PERIOD", "시작 월이 종료 월보다 늦습니다.")
    if len(months) > 12:
        raise AppError("PERIOD_TOO_LONG", "최대 12개월까지 조회할 수 있습니다.")
    if to > today_kst().strftime("%Y-%m"):
        raise AppError("FUTURE_PERIOD", "종료 월은 이번 달까지입니다.")
    return months


def worker_month(db: Session, e: M.Employment, month: str, today: date) -> dict | None:
    start, end = month_range(month)
    if e.start_date > end or (e.end_date and e.end_date < start) or start > today:
        return None
    c, p, u = e.contract, e.worker.profile, e.worker
    days, s = month_days(db, e, month)
    recs = {r.work_date: r for r in db.query(M.AttendanceRecord).filter(M.AttendanceRecord.employment_id == e.id,
                                                                        M.AttendanceRecord.work_date.between(start, end))}
    work_minutes, missing_out = 0, []
    for d, r in recs.items():
        if r.check_in_at and r.check_out_at:
            work_minutes += max(0, int((r.check_out_at - r.check_in_at).total_seconds() // 60) - (c.break_minutes if c else 0))
        elif r.check_in_at and d < today:
            missing_out.append(d.isoformat())
    leaves = db.query(M.LeaveRequest).filter(M.LeaveRequest.employment_id == e.id, M.LeaveRequest.status == LeaveStatus.APPROVED,
                                             M.LeaveRequest.start_date <= end, M.LeaveRequest.end_date >= start).all()
    leave_by_type: dict[str, float] = defaultdict(float)
    annual_days = 0
    for lv in leaves:
        d = max(lv.start_date, start)
        while d <= min(lv.end_date, end, today):
            if is_workday(c, d):
                n = 0.5 if lv.leave_type in (LeaveType.HALF_DAY_AM, LeaveType.HALF_DAY_PM) else 1
                leave_by_type[lv.leave_type.value] += n
                if lv.leave_type == LeaveType.ANNUAL:
                    annual_days += 1
            d += timedelta(days=1)
    paid_days = s["attended"] + annual_days
    logs = db.query(M.WorkLog).filter(M.WorkLog.employment_id == e.id, M.WorkLog.work_date.between(start, end)).all()
    submitted = [w for w in logs if w.first_submitted_at]
    by_task: dict[str, int] = defaultdict(int)
    for w in submitted:
        for en in w.entries:
            by_task[en.title] += en.minutes
    submitted_dates = {w.work_date for w in submitted}
    no_log = sorted(d.isoformat() for d, r in recs.items() if r.check_in_at and d not in submitted_dates and d < today)
    unconfirmed = sorted(w.work_date.isoformat() for w in logs if w.status in (WS.SUBMITTED, WS.RETURNED))
    files = sum(len(w.files) for w in logs)
    completed = db.query(M.Task).filter(M.Task.employment_id == e.id, M.Task.status == TaskStatus.COMPLETED).all()
    completed_n = sum(1 for t in completed if t.completed_at and start <= utc_naive_to_kst(t.completed_at).date() <= end)
    weekly = float(c.weekly_work_hours) if c else 0.0
    mh = monthly_scheduled_hours(weekly)
    partial = e.start_date > start or bool(e.end_date and e.end_date < end)
    result, reason = recognition(p.disability_degree if p else None, mh, paid_days, partial) if c else (RR.NEEDS_REVIEW, "근로계약 정보 없음")
    hw = hourly_wage(c.salary_type, c.salary_amount, weekly) if c else 0
    wage = "확인 필요" if not c or not c.salary_amount else ("충족" if hw >= settings.minimum_wage_hourly else "미달")
    attend_base = s["workdays"] - s["leaveDays"]
    log_by_date = {w.work_date: w for w in logs}
    daily = []
    for d in days:
        dd = date.fromisoformat(d["date"])
        r, w = recs.get(dd), log_by_date.get(dd)
        wm = max(0, int((r.check_out_at - r.check_in_at).total_seconds() // 60) - (c.break_minutes if c else 0)) if r and r.check_in_at and r.check_out_at else None
        daily.append({"date": d["date"], "weekday": "월화수목금토일"[dd.weekday()], "isWorkday": d["isWorkday"], "status": d["status"],
                      "checkIn": utc_naive_to_kst(r.check_in_at).strftime("%H:%M") if r and r.check_in_at else None,
                      "checkOut": utc_naive_to_kst(r.check_out_at).strftime("%H:%M") if r and r.check_out_at else None,
                      "workMinutes": wm, "leaveType": d["leaveType"], "workLogStatus": w.status.value if w else None,
                      "workLogItems": [f"{en.title}({en.minutes}분)" for en in w.entries] if w else [],
                      "workLogMinutes": w.total_minutes if w and w.first_submitted_at else 0})
    return {
        "employmentId": e.id, "month": month, "inProgress": end >= today,
        "person": {"name": u.name, "birthDate": p.birth_date.isoformat() if p and p.birth_date else None,
                   "disabilityType": p.disability_type.value if p and p.disability_type else None,
                   "disabilityTypeSecondary": p.disability_type_secondary.value if p and p.disability_type_secondary else None,
                   "disabilityDegree": p.disability_degree.value if p and p.disability_degree else None,
                   "startDate": e.start_date.isoformat(), "endDate": e.end_date.isoformat() if e.end_date else None,
                   "status": employment_status(e, today).value},
        "conditions": ({"contractType": c.contract_type.value, "contractStart": c.start_date.isoformat(), "contractEnd": c.end_date.isoformat() if c.end_date else None,
                        "workType": c.work_type.value, "workLocation": c.work_location, "jobDescription": c.job_description, "workDays": c.work_days,
                        "workTime": f"{c.work_start_time:%H:%M}~{c.work_end_time:%H:%M}", "breakMinutes": c.break_minutes, "weeklyHours": weekly,
                        "monthlyHours": mh, "salaryType": c.salary_type.value, "salaryAmount": c.salary_amount, "hourlyWage": hw,
                        "minimumWage": settings.minimum_wage_hourly, "wageCheck": wage,
                        "insurance": {"employment": c.insurance_employment, "accident": c.insurance_accident, "pension": c.insurance_pension, "health": c.insurance_health}}
                       if c else None),
        "attendance": {**s, "attendanceRate": round(s["attended"] / attend_base * 100) if attend_base > 0 else 0, "leaveByType": dict(leave_by_type),
                       "paidDays": paid_days, "workMinutes": work_minutes, "missingCheckOutDays": len(missing_out),
                       "correctedCount": sum(1 for r in recs.values() if r.corrected_by)},
        "work": {"submittedDays": len(submitted), "submitRate": round(len(submitted) / s["attended"] * 100) if s["attended"] else 0,
                 "confirmedDays": sum(1 for w in logs if w.status == WS.CONFIRMED), "returnedCount": sum(1 for w in logs if w.status == WS.RETURNED),
                 "loggedMinutes": sum(w.total_minutes for w in submitted), "completedTasks": completed_n, "fileCount": files,
                 "topTasks": [{"title": k, "minutes": v} for k, v in sorted(by_task.items(), key=lambda x: -x[1])[:5]],
                 "summaries": [f"{w.work_date.isoformat()} {w.summary}" for w in sorted(submitted, key=lambda w: w.work_date) if w.summary][:31]},
        "recognition": {"result": result.value, "reason": reason},
        "warnings": {"noDisability": not (p and p.disability_degree), "noContract": c is None, "missingCheckOut": missing_out,
                     "noWorkLog": no_log, "unconfirmedWorkLog": unconfirmed},
        "daily": daily,
    }


def build_report(db: Session, company_id: int, months: list[str]) -> dict:
    today = today_kst()
    c = db.get(M.Company, company_id)
    emps = db.query(M.Employment).filter_by(company_id=company_id).order_by(M.Employment.start_date).all()
    cm = db.query(M.User).filter_by(company_id=company_id, role=CM).first()
    out_months = []
    for mo in months:
        rows = [r for e in emps if (r := worker_month(db, e, mo, today))]
        rec = [r["recognition"]["result"] for r in rows]
        out_months.append({"month": mo, "inProgress": any(r["inProgress"] for r in rows) or month_range(mo)[1] >= today, "workers": rows, "summary": {
            "workers": len(rows),
            "severe": sum(1 for r in rows if r["person"]["disabilityDegree"] == "SEVERE"),
            "mild": sum(1 for r in rows if r["person"]["disabilityDegree"] == "MILD"),
            "recognizedCount": sum(2 if x == "DOUBLE" else 1 if x == "SINGLE" else 0 for x in rec),
            "excluded": rec.count("EXCLUDED"), "needsReview": rec.count("NEEDS_REVIEW"),
            "avgAttendanceRate": round(sum(r["attendance"]["attendanceRate"] for r in rows) / len(rows)) if rows else 0,
            "avgSubmitRate": round(sum(r["work"]["submitRate"] for r in rows) / len(rows)) if rows else 0,
            "totalWorkMinutes": sum(r["attendance"]["workMinutes"] for r in rows)}})
    return {"company": {"name": c.name, "businessRegistrationNo": c.business_registration_no, "employmentInsuranceNo": c.employment_insurance_no,
                        "representativeName": c.representative_name, "industry": c.industry, "address": c.address,
                        "companyManager": cm.name if cm else None, "vdreamManager": c.manager.name if c.manager else None},
            "from": months[0], "to": months[-1], "generatedAt": datetime.now(KST).strftime("%Y-%m-%d %H:%M"), "disclaimer": DISCLAIMER,
            "months": out_months}


@router.get("/reports/employment")
def employment_report(frm: str = Query(alias="from"), to: str = Query(), user: CurrentUser = Depends(require(CM)), db: Session = Depends(get_db)):
    return ok(build_report(db, user.company_id, validate_period(frm, to)))


@router.get("/reports/employment/warnings")
def report_warnings(frm: str = Query(alias="from"), to: str = Query(), user: CurrentUser = Depends(require(CM)), db: Session = Depends(get_db)):
    rep = build_report(db, user.company_id, validate_period(frm, to))
    items = []
    for mo in rep["months"]:
        for w in mo["workers"]:
            name, wr = w["person"]["name"], w["warnings"]
            if wr["noDisability"]:
                items.append({"type": "NO_DISABILITY", "worker": name, "month": mo["month"], "text": "장애정보 미입력", "link": "/admin/workers"})
            if wr["noContract"]:
                items.append({"type": "NO_CONTRACT", "worker": name, "month": mo["month"], "text": "근로계약 정보 없음", "link": f"/admin/employments/{w['employmentId']}"})
            for d in wr["missingCheckOut"]:
                items.append({"type": "MISSING_CHECKOUT", "worker": name, "month": mo["month"], "text": f"{d} 퇴근 미기록", "link": "/admin/attendance"})
            for d in wr["noWorkLog"]:
                items.append({"type": "NO_WORK_LOG", "worker": name, "month": mo["month"], "text": f"{d} 출근했으나 업무일지 미제출", "link": "/admin/work-logs"})
            for d in wr["unconfirmedWorkLog"]:
                items.append({"type": "UNCONFIRMED_WORK_LOG", "worker": name, "month": mo["month"], "text": f"{d} 업무일지 미확인", "link": "/admin/work-logs"})
    return ok(items)


LABEL = {"DOUBLE": "인정(2배수)", "SINGLE": "인정(1배수)", "EXCLUDED": "제외 가능", "NEEDS_REVIEW": "확인 필요", "SEVERE": "중증", "MILD": "경증"}


@router.get("/reports/employment.xlsx")
def employment_xlsx(frm: str = Query(alias="from"), to: str = Query(), user: CurrentUser = Depends(require(CM)), db: Session = Depends(get_db)):
    from openpyxl import Workbook
    from openpyxl.styles import Font
    rep = build_report(db, user.company_id, validate_period(frm, to))
    co = rep["company"]
    wb = Workbook()
    s1 = wb.active
    s1.title = "요약"
    head = [f"월간 장애인 고용 리포트 · {co['name']} · {rep['from']} ~ {rep['to']} · 생성 {rep['generatedAt']}"]
    s1.append(head)
    s1.append([f"사업자등록번호 {co['businessRegistrationNo'] or '-'} / 고용보험 사업장관리번호 {co['employmentInsuranceNo'] or '-'} / 대표자 {co['representativeName'] or '-'}"])
    s1.append([])
    s1.append(["월", "재직 장애인", "중증", "경증", "인정 인원 추정", "제외 가능", "확인 필요", "평균 출근율(%)", "평균 업무일지 제출률(%)", "총 실근로시간(h)"])
    for mo in rep["months"]:
        sm = mo["summary"]
        s1.append([mo["month"] + (" (진행 중)" if mo["inProgress"] else ""), sm["workers"], sm["severe"], sm["mild"], sm["recognizedCount"],
                   sm["excluded"], sm["needsReview"], sm["avgAttendanceRate"], sm["avgSubmitRate"], round(sm["totalWorkMinutes"] / 60, 1)])
    s1.append([])
    s1.append([rep["disclaimer"]])
    s1["A1"].font = Font(bold=True, size=13)
    s2 = wb.create_sheet("근로자별 월간")
    s2.append(["월", "이름", "생년월일", "주 장애유형", "장애정도", "입사일", "퇴사일", "근무 형태", "주 소정(h)", "월 소정(h)", "급여 형태", "급여",
               "시급 환산", "최저임금", "근무일", "출근일", "출근율(%)", "지각", "조퇴", "결근", "휴가일", "유급 근로일(추정)", "실근로(h)",
               "업무일지 제출일", "제출률(%)", "확인일", "보완 요청", "기록 시간(h)", "완료 업무", "산출물", "인정 판정", "판정 근거"])
    s3 = wb.create_sheet("일자별 근로 기록")
    s3.append(["월", "이름", "날짜", "요일", "근무일", "근태", "출근", "퇴근", "실근로(분)", "휴가", "업무일지", "업무 항목", "업무일지 시간(분)"])
    for mo in rep["months"]:
        for w in mo["workers"]:
            pp, cc, a, wk = w["person"], w["conditions"] or {}, w["attendance"], w["work"]
            s2.append([mo["month"], pp["name"], pp["birthDate"], pp["disabilityType"], LABEL.get(pp["disabilityDegree"], ""), pp["startDate"], pp["endDate"],
                       cc.get("workType"), cc.get("weeklyHours"), cc.get("monthlyHours"), cc.get("salaryType"), cc.get("salaryAmount"), cc.get("hourlyWage"),
                       cc.get("wageCheck"), a["workdays"], a["attended"], a["attendanceRate"], a["late"], a["earlyLeave"], a["absent"], a["leaveDays"],
                       a["paidDays"], round(a["workMinutes"] / 60, 1), wk["submittedDays"], wk["submitRate"], wk["confirmedDays"], wk["returnedCount"],
                       round(wk["loggedMinutes"] / 60, 1), wk["completedTasks"], wk["fileCount"], LABEL[w["recognition"]["result"]], w["recognition"]["reason"]])
            for d in w["daily"]:
                s3.append([mo["month"], pp["name"], d["date"], d["weekday"], "Y" if d["isWorkday"] else "", d["status"] or "", d["checkIn"] or "",
                           d["checkOut"] or "", d["workMinutes"] or "", d["leaveType"] or "", d["workLogStatus"] or "", ", ".join(d["workLogItems"]),
                           d["workLogMinutes"] or ""])
    for ws in (s2, s3):
        ws.freeze_panes = "C2"
        for cell in ws[1]:
            cell.font = Font(bold=True)
    return xlsx_response(wb, f"장애인고용리포트_{co['name']}_{rep['from'].replace('-', '')}-{rep['to'].replace('-', '')}.xlsx")


# ---------------- DASHBOARD ----------------
@router.get("/dashboard")
def dashboard(all_companies: bool = False, user: CurrentUser = Depends(require(CM, VM)), db: Session = Depends(get_db)):
    today = today_kst()
    week_start = today - timedelta(days=today.weekday())
    emps_q = db.query(M.Employment).join(M.Company)
    if user.role == CM:
        emps_q = emps_q.filter(M.Employment.company_id == user.company_id)
    elif not all_companies:
        emps_q = emps_q.filter(M.Company.manager_id == user.id)
    emps = [e for e in emps_q if employment_status(e, today) == EmploymentStatus.ACTIVE]
    eids = [e.id for e in emps]
    today_recs = {r.employment_id: r for r in db.query(M.AttendanceRecord).filter(M.AttendanceRecord.work_date == today, M.AttendanceRecord.employment_id.in_(eids))}
    people = [{"employmentId": e.id, "workerName": e.worker.name, "companyName": e.company.name,
               "state": ("퇴근" if today_recs[e.id].check_out_at else "근무 중") if e.id in today_recs and today_recs[e.id].check_in_at else ("휴무" if not is_workday(e.contract, today) else "출근 전"),
               "status": today_recs[e.id].status.value if e.id in today_recs else None} for e in emps]
    missing = 0
    for e in emps:
        atts = {r.work_date for r in db.query(M.AttendanceRecord).filter(M.AttendanceRecord.employment_id == e.id, M.AttendanceRecord.work_date.between(week_start, today - timedelta(days=1)), M.AttendanceRecord.check_in_at.isnot(None))}
        done = {w.work_date for w in db.query(M.WorkLog).filter(M.WorkLog.employment_id == e.id, M.WorkLog.work_date >= week_start, M.WorkLog.first_submitted_at.isnot(None))}
        missing += len(atts - done)
    data = {"today": people, "activeWorkers": len(emps), "notCheckedIn": sum(1 for p in people if p["state"] == "출근 전"),
            "tasksInProgress": db.query(M.Task).filter(M.Task.employment_id.in_(eids), M.Task.status == TaskStatus.IN_PROGRESS).count(),
            "tasksOverdue": db.query(M.Task).filter(M.Task.employment_id.in_(eids), M.Task.status.in_([TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS]), M.Task.due_date < today).count(),
            "workLogsToConfirm": db.query(M.WorkLog).filter(M.WorkLog.employment_id.in_(eids), M.WorkLog.status == WS.SUBMITTED).count(),
            "workLogsMissingThisWeek": missing}
    if user.role == CM:
        first = today.replace(day=1)
        prev = (first - timedelta(days=1)).strftime("%Y-%m")
        rep = build_report(db, user.company_id, [prev])["months"][0]
        warns = sum(len(w["warnings"]["missingCheckOut"]) + len(w["warnings"]["noWorkLog"]) + len(w["warnings"]["unconfirmedWorkLog"])
                    + int(w["warnings"]["noDisability"]) + int(w["warnings"]["noContract"]) for w in rep["workers"])
        data["lastMonthReport"] = {"month": prev, "recognizedCount": rep["summary"]["recognizedCount"], "workers": rep["summary"]["workers"], "warnings": warns}
    else:
        by_company: dict[str, int] = defaultdict(int)
        for e in emps:
            by_company[e.company.name] += 1
        data["byCompany"] = [{"companyName": k, "activeWorkers": v} for k, v in sorted(by_company.items())]
    if user.role == CM:
        data |= {"leavesPending": db.query(M.LeaveRequest).filter(M.LeaveRequest.employment_id.in_(eids), M.LeaveRequest.status == LeaveStatus.PENDING).count(),
                 "openPostings": db.query(M.JobPosting).filter(M.JobPosting.company_id == user.company_id, M.JobPosting.status == JobPostingStatus.PUBLISHED).count()}
    else:
        data |= {"postingsPending": db.query(M.JobPosting).filter(M.JobPosting.status == JobPostingStatus.PENDING_APPROVAL).count(),
                 "resignationsPending": db.query(M.ResignationRequest).filter(M.ResignationRequest.status == ResignationStatus.PENDING).count(),
                 "seekers": db.query(M.WorkerProfile).filter(M.WorkerProfile.job_seeking_status == JobSeekingStatus.SEEKING).count(),
                 "counselingThisMonth": db.query(M.CounselingReport).filter(M.CounselingReport.deleted_at.is_(None), M.CounselingReport.counseled_at >= datetime(today.year, today.month, 1)).count()}
    return ok(data)
