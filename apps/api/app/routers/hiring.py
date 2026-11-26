"""RESM, REGI, JOBP, APPL, EMPL, RESG."""
from datetime import date, datetime, time
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Request, UploadFile
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
    company_manager_ids,
    forbidden,
    get_current_user,
    not_found,
    notify,
    ok,
    require,
    ser,
)
from ..db import get_db, utcnow
from ..domain import KST, UTC, current_employment, employment_status, is_open_employment, posting_open, today_kst
from ..enums import ApplicationStatus as AS
from ..enums import (
    CareerType,
    ContractType,
    DisabilityDegree,
    DisabilityType,
    EducationStatus,
    EducationType,
    EmploymentStatus,
    FilePurpose,
    Gender,
    InterviewMethod,
    JobField,
    JobSeekingStatus,
    PostingAuthorType,
    SalaryType,
    WorkType,
)
from ..enums import JobPostingStatus as PS
from ..enums import ResignationStatus as RS
from ..ratelimit import limiter
from ..schemas import In
from ..storage import save_upload

router = APIRouter()
FINAL = {AS.DOCUMENT_FAILED, AS.FAILED, AS.HIRED, AS.CANCELLED}


# ---------------- RESUME ----------------
def resume_out(db: Session, u: M.User) -> dict:
    p = u.profile
    edus = db.query(M.Education).filter(M.Education.worker_id == u.id).order_by(M.Education.sort_order, M.Education.start_date)
    cars = db.query(M.Career).filter(M.Career.worker_id == u.id).order_by(M.Career.sort_order, M.Career.start_date)
    emps = db.query(M.Employment).filter(M.Employment.worker_id == u.id).order_by(M.Employment.start_date.desc())
    today = today_kst()
    return {"user": {"id": u.id, "name": u.name, "phone": u.phone, "email": u.email},
            "profile": ser(p) if p else None, "educations": [ser(e) for e in edus], "careers": [ser(c) for c in cars],
            "employmentHistory": [{"id": e.id, "companyName": e.company.name, "startDate": e.start_date.isoformat(),
                                   "endDate": e.end_date.isoformat() if e.end_date else None,
                                   "status": employment_status(e, today).value} for e in emps]}


def can_view_resume(db: Session, user: CurrentUser, worker_id: int) -> bool:
    if user.role == VM or (user.role == WK and user.id == worker_id):
        return True
    if user.role == CM:
        if db.query(M.Employment).filter(M.Employment.worker_id == worker_id, M.Employment.company_id == user.company_id).first():
            return True
        return db.query(M.JobApplication).join(M.JobPosting).filter(M.JobApplication.worker_id == worker_id,
                                                                    M.JobPosting.company_id == user.company_id).first() is not None
    return False


class EduIn(In):
    start_date: date
    end_date: date | None = None
    institution: str
    type: EducationType
    status: EducationStatus
    major: str | None = None


class CareerIn(In):
    start_date: date
    end_date: date | None = None
    institution: str
    employment_type: CareerType
    duties: str | None = None
    position: str | None = None


class ResumeIn(In):
    name: str
    phone: str | None = None
    email: str | None = None
    birth_date: date | None = None
    gender: Gender | None = None
    address: str | None = None
    disability_type: DisabilityType | None = None
    disability_type_secondary: DisabilityType | None = None
    disability_degree: DisabilityDegree | None = None
    assistive_devices: str | None = None
    has_pc: bool | None = None
    has_internet: bool | None = None
    software_skills: str | None = None
    work_environment_note: str | None = None
    desired_job_fields: list[JobField] = []
    skills: str | None = None
    introduction: str | None = None
    educations: list[EduIn] = []
    careers: list[CareerIn] = []


def save_resume(db: Session, u: M.User, body: ResumeIn) -> None:
    u.name, u.phone, u.email = body.name, body.phone, body.email
    p = u.profile or M.WorkerProfile(user_id=u.id)
    db.add(p)
    data = body.model_dump(exclude={"name", "phone", "email", "educations", "careers", "desired_job_fields"})
    for k, v in data.items():
        setattr(p, k, v)
    p.desired_job_fields = ",".join(f.value for f in body.desired_job_fields) or None
    db.query(M.Education).filter(M.Education.worker_id == u.id).delete()
    db.query(M.Career).filter(M.Career.worker_id == u.id).delete()
    for i, e in enumerate(body.educations):
        db.add(M.Education(worker_id=u.id, sort_order=i, **e.model_dump()))
    for i, c in enumerate(body.careers):
        db.add(M.Career(worker_id=u.id, sort_order=i, **c.model_dump()))
    db.commit()


@router.get("/resumes/{worker_id}")
def get_resume(worker_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if not can_view_resume(db, user, worker_id):
        raise forbidden()
    u = db.get(M.User, worker_id)
    if not u or u.role != WK:
        raise not_found("근로자")
    return ok(resume_out(db, u))


@router.put("/resumes/{worker_id}")
def put_resume(worker_id: int, body: ResumeIn, user: CurrentUser = Depends(require(WK, VM)), db: Session = Depends(get_db)):
    if user.role == WK and user.id != worker_id:
        raise forbidden()
    u = db.get(M.User, worker_id)
    if not u or u.role != WK:
        raise not_found("근로자")
    save_resume(db, u, body)
    return ok(resume_out(db, u))


@router.post("/resumes/{worker_id}/photo")
@limiter.limit(settings.rate_limit_upload)
async def upload_photo(request: Request, worker_id: int, file: UploadFile = File(...), user: CurrentUser = Depends(require(WK, VM)), db: Session = Depends(get_db)):
    if user.role == WK and user.id != worker_id:
        raise forbidden()
    p = db.query(M.WorkerProfile).filter(M.WorkerProfile.user_id == worker_id).first()
    if not p:
        raise not_found("이력서")
    f = await save_upload(db, file, FilePurpose.PROFILE_PHOTO, user.id)
    p.photo_file_id = f.id
    db.commit()
    return ok(ser(p))


class SeekIn(In):
    seeking: bool


def set_seeking(db: Session, worker_id: int, seeking: bool, actor: CurrentUser) -> M.WorkerProfile:
    p = db.query(M.WorkerProfile).filter(M.WorkerProfile.user_id == worker_id).first()
    if not p:
        raise not_found("이력서")
    if seeking:
        if current_employment(db, worker_id):
            raise AppError("EMPLOYED", "재직 중에는 구직 등록을 할 수 없습니다.")
        if not p.disability_type or not p.birth_date:
            raise AppError("RESUME_INCOMPLETE", "기본정보와 장애정보를 먼저 작성해 주세요.")
    else:
        active = db.query(M.JobApplication).filter(M.JobApplication.worker_id == worker_id, M.JobApplication.status.notin_(FINAL)).count()
        if active:
            raise AppError("ACTIVE_APPLICATION", "진행 중인 지원이 있어 구직 등록을 해제할 수 없습니다.")
    p.job_seeking_status = JobSeekingStatus.SEEKING if seeking else JobSeekingStatus.NOT_SEEKING
    p.job_seeking_changed_at = utcnow()
    if seeking:
        name = db.get(M.User, worker_id).name
        if actor.role == WK:
            notify(db, [u.id for u in db.query(M.User).filter(M.User.role == VM)], "JOB_SEEKING_REGISTERED", "구직 등록", f"{name}님이 구직 등록했습니다.", f"/admin/workers/{worker_id}")
        else:
            notify(db, [worker_id], "JOB_SEEKING_REGISTERED_BY_MANAGER", "구직 등록 완료", "브이드림 매니저가 구직 등록을 해 주었습니다.", "/m/more/resume")
    db.commit()
    return p


@router.post("/resumes/{worker_id}/job-seeking")
def job_seeking(worker_id: int, body: SeekIn, user: CurrentUser = Depends(require(WK, VM)), db: Session = Depends(get_db)):
    if user.role == WK and user.id != worker_id:
        raise forbidden()
    return ok(ser(set_seeking(db, worker_id, body.seeking, user)))


@router.get("/seekers")
def seekers(job_field: JobField | None = None, q: str | None = None, user: CurrentUser = Depends(require(VM)), db: Session = Depends(get_db)):
    qq = db.query(M.WorkerProfile).join(M.User).filter(M.WorkerProfile.job_seeking_status == JobSeekingStatus.SEEKING)
    if q:
        qq = qq.filter(M.User.name.contains(q))
    out = []
    for p in qq:
        if job_field and job_field.value not in (p.desired_job_fields or ""):
            continue
        out.append(ser(p, name=p.user.name))
    return ok(out)


@router.get("/workers")
def workers(user: CurrentUser = Depends(require(VM)), db: Session = Depends(get_db)):
    today = today_kst()
    out = []
    for u in db.query(M.User).filter(M.User.role == WK, M.User.deleted_at.is_(None)).order_by(M.User.name):
        emp = current_employment(db, u.id, today)
        out.append({"id": u.id, "name": u.name, "jobSeekingStatus": u.profile.job_seeking_status.value if u.profile else None,
                    "disabilityType": u.profile.disability_type.value if u.profile and u.profile.disability_type else None,
                    "disabilityDegree": u.profile.disability_degree.value if u.profile and u.profile.disability_degree else None,
                    "companyName": emp.company.name if emp else None, "employmentStatus": employment_status(emp, today).value if emp else None})
    return ok(out)


# ---------------- POSTINGS ----------------
class PostingIn(In):
    company_id: int | None = None
    title: str
    job_field: JobField
    main_duties: str
    work_type: WorkType = WorkType.REMOTE
    work_location: str | None = None
    work_days: str = "MON,TUE,WED,THU,FRI"
    work_start_time: time
    work_end_time: time
    weekly_work_hours: Decimal
    salary_type: SalaryType
    salary_amount: int
    benefits: str | None = None
    equipment_support: str | None = None
    requirements: str | None = None
    expected_start_date: date
    contract_type: ContractType
    expected_end_date: date | None = None
    headcount: int = 1
    description: str | None = None
    deadline_date: date | None = None


def posting_out(db: Session, p: M.JobPosting, user: CurrentUser | None = None) -> dict:
    extra = {"companyName": p.company.name, "managerName": p.company.manager.name if p.company.manager else None,
             "applicantCount": db.query(M.JobApplication).filter(M.JobApplication.job_posting_id == p.id, M.JobApplication.status != AS.CANCELLED).count(),
             "isOpen": posting_open(p, today_kst())}
    if user and user.role == WK:
        a = db.query(M.JobApplication).filter(M.JobApplication.job_posting_id == p.id, M.JobApplication.worker_id == user.id).first()
        extra["myApplication"] = {"id": a.id, "status": a.status.value} if a else None
    return ser(p, **extra)


def get_posting(db: Session, pid: int, user: CurrentUser) -> M.JobPosting:
    p = db.get(M.JobPosting, pid)
    if not p:
        raise not_found("공고")
    if user.role == CM and p.company_id != user.company_id:
        raise forbidden()
    if user.role == WK and p.status not in (PS.PUBLISHED, PS.CLOSED):
        raise not_found("공고")
    return p


@router.get("/job-postings")
def list_postings(status: PS | None = None, company_id: int | None = None, mine: bool = False, job_field: JobField | None = None, author_type: PostingAuthorType | None = None,
                  work_type: WorkType | None = None, q: str | None = None,
                  user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    qq = db.query(M.JobPosting).join(M.Company)
    if user.role == WK:
        qq = qq.filter(M.JobPosting.status == PS.PUBLISHED)
    elif user.role == CM:
        qq = qq.filter(M.JobPosting.company_id == user.company_id)
    elif user.role == VM and mine:
        qq = qq.filter(M.Company.manager_id == user.id)
    if status and user.role != WK:
        qq = qq.filter(M.JobPosting.status == status)
    if company_id:
        qq = qq.filter(M.JobPosting.company_id == company_id)
    if author_type and user.role != WK:
        qq = qq.filter(M.JobPosting.author_type == author_type)
    if job_field:
        qq = qq.filter(M.JobPosting.job_field == job_field)
    if work_type:
        qq = qq.filter(M.JobPosting.work_type == work_type)
    if q:
        qq = qq.filter(M.JobPosting.title.contains(q) | M.Company.name.contains(q))
    return ok([posting_out(db, p, user) for p in qq.order_by(M.JobPosting.id.desc())])


@router.get("/job-postings/{pid}")
def posting_detail(pid: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(posting_out(db, get_posting(db, pid, user), user))


@router.post("/job-postings")
def create_posting(body: PostingIn, user: CurrentUser = Depends(require(CM, VM)), db: Session = Depends(get_db)):
    cid = user.company_id if user.role == CM else body.company_id
    if not cid or not db.get(M.Company, cid):
        raise AppError("COMPANY_REQUIRED", "기업을 선택해 주세요.")
    p = M.JobPosting(**body.model_dump(exclude={"company_id"}), company_id=cid, created_by=user.id,
                     author_type=PostingAuthorType.COMPANY if user.role == CM else PostingAuthorType.VDREAM)
    db.add(p)
    db.commit()
    return ok(posting_out(db, p))


@router.put("/job-postings/{pid}")
def update_posting(pid: int, body: PostingIn, user: CurrentUser = Depends(require(CM, VM)), db: Session = Depends(get_db)):
    p = get_posting(db, pid, user)
    if p.status in (PS.DRAFT, PS.REJECTED):
        for k, v in body.model_dump(exclude={"company_id"}).items():
            setattr(p, k, v)
    elif p.status == PS.PUBLISHED:
        p.deadline_date, p.headcount = body.deadline_date, body.headcount
    else:
        raise AppError("POSTING_NOT_EDITABLE", "이 상태의 공고는 수정할 수 없습니다.")
    db.commit()
    return ok(posting_out(db, p))


@router.delete("/job-postings/{pid}")
def delete_posting(pid: int, user: CurrentUser = Depends(require(CM, VM)), db: Session = Depends(get_db)):
    p = get_posting(db, pid, user)
    if p.status not in (PS.DRAFT, PS.REJECTED):
        raise AppError("POSTING_NOT_DELETABLE", "작성중 또는 반려 상태만 삭제할 수 있습니다.")
    db.delete(p)
    db.commit()
    return ok(True)


def _transition(p: M.JobPosting, allowed: set[PS], to: PS) -> None:
    if p.status not in allowed:
        raise AppError("INVALID_TRANSITION", "현재 상태에서는 처리할 수 없습니다.")
    p.status = to


@router.post("/job-postings/{pid}/submit")
def submit_posting(pid: int, user: CurrentUser = Depends(require(CM)), db: Session = Depends(get_db)):
    p = get_posting(db, pid, user)
    _transition(p, {PS.DRAFT, PS.REJECTED}, PS.PENDING_APPROVAL)
    notify(db, company_manager_ids(db, p.company_id), "POSTING_APPROVAL_REQUESTED", "공고 승인 요청", f"[{p.company.name}] {p.title}", f"/admin/postings/{p.id}")
    db.commit()
    return ok(posting_out(db, p))


@router.post("/job-postings/{pid}/approve")
def approve_posting(pid: int, user: CurrentUser = Depends(require(VM)), db: Session = Depends(get_db)):
    p = get_posting(db, pid, user)
    _transition(p, {PS.PENDING_APPROVAL}, PS.PUBLISHED)
    p.approved_by, p.approved_at = user.id, utcnow()
    notify(db, company_cm_ids(db, p.company_id), "POSTING_APPROVED", "공고 승인", f"{p.title} 공고가 게시되었습니다.", f"/admin/postings/{p.id}")
    db.commit()
    return ok(posting_out(db, p))


@router.post("/job-postings/{pid}/publish")
def publish_posting(pid: int, user: CurrentUser = Depends(require(VM)), db: Session = Depends(get_db)):
    p = get_posting(db, pid, user)
    if p.author_type != PostingAuthorType.VDREAM:
        raise AppError("INVALID_TRANSITION", "기업 작성 공고는 승인 절차를 거쳐야 합니다.")
    _transition(p, {PS.DRAFT}, PS.PUBLISHED)
    p.approved_by, p.approved_at = user.id, utcnow()
    notify(db, company_cm_ids(db, p.company_id), "POSTING_PUBLISHED", "공고 게시", f"브이드림이 {p.title} 공고를 게시했습니다.", f"/admin/postings/{p.id}")
    db.commit()
    return ok(posting_out(db, p))


class ReasonIn(In):
    reason: str | None = None


@router.post("/job-postings/{pid}/reject")
def reject_posting(pid: int, body: ReasonIn, user: CurrentUser = Depends(require(VM)), db: Session = Depends(get_db)):
    p = get_posting(db, pid, user)
    _transition(p, {PS.PENDING_APPROVAL}, PS.REJECTED)
    p.reject_reason = body.reason
    notify(db, company_cm_ids(db, p.company_id), "POSTING_REJECTED", "공고 반려", f"{p.title}: {body.reason or ''}", f"/admin/postings/{p.id}")
    db.commit()
    return ok(posting_out(db, p))


@router.post("/job-postings/{pid}/close")
def close_posting(pid: int, user: CurrentUser = Depends(require(CM, VM)), db: Session = Depends(get_db)):
    p = get_posting(db, pid, user)
    _transition(p, {PS.PUBLISHED}, PS.CLOSED)
    p.closed_at = utcnow()
    db.commit()
    return ok(posting_out(db, p))


# ---------------- APPLICATIONS ----------------
def app_out(db: Session, a: M.JobApplication) -> dict:
    p = a.worker.profile
    return ser(a, postingTitle=a.posting.title, companyName=a.posting.company.name, workerName=a.worker.name,
               disabilityType=p.disability_type.value if p and p.disability_type else None,
               disabilityDegree=p.disability_degree.value if p and p.disability_degree else None)


class ApplyIn(In):
    register_seeking: bool = False


@router.post("/job-postings/{pid}/apply")
def apply(pid: int, body: ApplyIn, user: CurrentUser = Depends(require(WK)), db: Session = Depends(get_db)):
    p = get_posting(db, pid, user)
    if not posting_open(p, today_kst()):
        raise AppError("POSTING_NOT_OPEN", "지원할 수 없는 공고입니다.")
    if current_employment(db, user.id):
        raise AppError("EMPLOYED", "재직 중에는 지원할 수 없습니다.")
    prof = db.query(M.WorkerProfile).filter(M.WorkerProfile.user_id == user.id).first()
    if prof.job_seeking_status != JobSeekingStatus.SEEKING:
        if not body.register_seeking:
            raise AppError("NOT_SEEKING", "구직 등록이 필요합니다.", 409)
        set_seeking(db, user.id, True, user)
    if db.query(M.JobApplication).filter(M.JobApplication.job_posting_id == pid, M.JobApplication.worker_id == user.id).first():
        raise AppError("ALREADY_APPLIED", "이미 지원한 공고입니다.")
    a = M.JobApplication(job_posting_id=pid, worker_id=user.id)
    db.add(a)
    notify(db, company_cm_ids(db, p.company_id) + company_manager_ids(db, p.company_id), "APPLICATION_RECEIVED", "새 지원",
           f"{user.name}님이 {p.title}에 지원했습니다.", f"/admin/postings/{p.id}")
    db.commit()
    return ok(app_out(db, a))


@router.get("/applications/me")
def my_apps(user: CurrentUser = Depends(require(WK)), db: Session = Depends(get_db)):
    rows = db.query(M.JobApplication).filter(M.JobApplication.worker_id == user.id).order_by(M.JobApplication.id.desc())
    return ok([app_out(db, a) for a in rows])


@router.post("/applications/{aid}/cancel")
def cancel_app(aid: int, user: CurrentUser = Depends(require(WK)), db: Session = Depends(get_db)):
    a = db.get(M.JobApplication, aid)
    if not a or a.worker_id != user.id:
        raise not_found("지원")
    if a.status not in (AS.APPLIED, AS.DOCUMENT_PASSED, AS.INTERVIEW_SCHEDULED):
        raise AppError("INVALID_TRANSITION", "최종 결과가 나온 지원은 취소할 수 없습니다.")
    a.status, a.cancelled_at = AS.CANCELLED, utcnow()
    notify(db, company_cm_ids(db, a.posting.company_id) + company_manager_ids(db, a.posting.company_id), "APPLICATION_CANCELLED", "지원 취소",
           f"{a.worker.name}님이 {a.posting.title} 지원을 취소했습니다.")
    db.commit()
    return ok(app_out(db, a))


def get_app(db: Session, aid: int, user: CurrentUser) -> M.JobApplication:
    a = db.get(M.JobApplication, aid)
    if not a:
        raise not_found("지원")
    if user.role == CM and a.posting.company_id != user.company_id:
        raise forbidden()
    return a


@router.get("/job-postings/{pid}/applications")
def posting_apps(pid: int, user: CurrentUser = Depends(require(CM, VM)), db: Session = Depends(get_db)):
    get_posting(db, pid, user)
    rows = db.query(M.JobApplication).filter(M.JobApplication.job_posting_id == pid).order_by(M.JobApplication.id)
    return ok([app_out(db, a) for a in rows])


@router.get("/applications/{aid}")
def app_detail(aid: int, user: CurrentUser = Depends(require(CM, VM)), db: Session = Depends(get_db)):
    a = get_app(db, aid, user)
    return ok(app_out(db, a) | {"resume": resume_out(db, a.worker)})


def _progress(db: Session, a: M.JobApplication, user: CurrentUser, frm: set[AS], to: AS, title: str, body: str) -> None:
    if a.status not in frm:
        raise AppError("INVALID_TRANSITION", "현재 단계에서는 처리할 수 없습니다.")
    a.status, a.last_updated_by = to, user.id
    other = company_manager_ids(db, a.posting.company_id) if user.role == CM else company_cm_ids(db, a.posting.company_id)
    notify(db, [a.worker_id], "APPLICATION_" + to.value, title, body, "/m/more/applications")
    notify(db, other, "APPLICATION_" + to.value, title, f"{a.worker.name} · {body}", f"/admin/postings/{a.job_posting_id}")


class PassIn(In):
    passed: bool


@router.post("/applications/{aid}/document")
def document_result(aid: int, body: PassIn, user: CurrentUser = Depends(require(CM, VM)), db: Session = Depends(get_db)):
    a = get_app(db, aid, user)
    to = AS.DOCUMENT_PASSED if body.passed else AS.DOCUMENT_FAILED
    _progress(db, a, user, {AS.APPLIED}, to, "서류심사 결과", f"{a.posting.title}: {'서류 합격' if body.passed else '서류 불합격'}")
    a.document_result_at = utcnow()
    db.commit()
    return ok(app_out(db, a))


class InterviewIn(In):
    interview_at: datetime
    interview_method: InterviewMethod
    interview_location: str | None = None
    interview_note: str | None = None


@router.post("/applications/{aid}/interview")
def interview(aid: int, body: InterviewIn, user: CurrentUser = Depends(require(CM, VM)), db: Session = Depends(get_db)):
    a = get_app(db, aid, user)
    _progress(db, a, user, {AS.DOCUMENT_PASSED, AS.INTERVIEW_SCHEDULED}, AS.INTERVIEW_SCHEDULED, "면접 일정 안내", f"{a.posting.title} 면접 일정이 정해졌습니다.")
    at = body.interview_at
    a.interview_at = (at if at.tzinfo else at.replace(tzinfo=KST)).astimezone(UTC).replace(tzinfo=None)
    a.interview_method, a.interview_location, a.interview_note = body.interview_method, body.interview_location, body.interview_note
    db.commit()
    return ok(app_out(db, a))


@router.post("/applications/{aid}/final")
def final_result(aid: int, body: PassIn, user: CurrentUser = Depends(require(CM, VM)), db: Session = Depends(get_db)):
    a = get_app(db, aid, user)
    _progress(db, a, user, {AS.INTERVIEW_SCHEDULED}, AS.PASSED if body.passed else AS.FAILED, "최종 결과", f"{a.posting.title}: {'최종 합격' if body.passed else '불합격'}")
    a.final_result_at = utcnow()
    db.commit()
    return ok(app_out(db, a))


class HireIn(In):
    start_date: date


@router.post("/applications/{aid}/hire")
def hire(aid: int, body: HireIn, user: CurrentUser = Depends(require(CM, VM)), db: Session = Depends(get_db)):
    a = get_app(db, aid, user)
    p, today = a.posting, today_kst()
    if a.status == AS.HIRED and a.employment_id:  # 출근일 변경
        e = db.get(M.Employment, a.employment_id)
        if employment_status(e, today) != EmploymentStatus.PENDING:
            raise AppError("ALREADY_STARTED", "이미 출근이 시작되어 변경할 수 없습니다.")
        e.start_date = e.contract.start_date = a.start_date = body.start_date
        db.commit()
        return ok(app_out(db, a))
    if a.status != AS.PASSED:
        raise AppError("INVALID_TRANSITION", "최종 합격자만 출근일을 정할 수 있습니다.")
    if current_employment(db, a.worker_id, today):
        raise AppError("EMPLOYED", "이미 재직 중인 근로자입니다.")
    e = M.Employment(worker_id=a.worker_id, company_id=p.company_id, job_application_id=a.id, start_date=body.start_date)
    db.add(e)
    db.flush()
    db.add(M.EmploymentContract(employment_id=e.id, contract_type=p.contract_type, start_date=body.start_date, end_date=p.expected_end_date,
                                work_type=p.work_type, work_location=p.work_location or "자택", job_description=p.main_duties[:500],
                                work_days=p.work_days, work_start_time=p.work_start_time, work_end_time=p.work_end_time,
                                weekly_work_hours=p.weekly_work_hours, annual_leave_days=Decimal(15), salary_type=p.salary_type,
                                salary_amount=p.salary_amount, equipment_support=p.equipment_support, updated_by=user.id))
    a.status, a.start_date, a.employment_id, a.last_updated_by = AS.HIRED, body.start_date, e.id, user.id
    prof = db.query(M.WorkerProfile).filter(M.WorkerProfile.user_id == a.worker_id).first()
    prof.job_seeking_status, prof.job_seeking_changed_at = JobSeekingStatus.NOT_SEEKING, utcnow()  # REGI-004
    notify(db, [a.worker_id], "HIRED", "출근 시작일 확정", f"{p.company.name} 출근 시작일은 {body.start_date}입니다.", "/m/more/contract")
    other = company_manager_ids(db, p.company_id) if user.role == CM else company_cm_ids(db, p.company_id)
    notify(db, other, "HIRED", "출근 시작일 확정", f"{a.worker.name} · {body.start_date}", f"/admin/employments/{e.id}")
    db.commit()
    return ok(app_out(db, a))


# ---------------- EMPLOYMENTS & CONTRACTS ----------------
def emp_out(e: M.Employment, today: date) -> dict:
    p = e.worker.profile
    return ser(e, status=employment_status(e, today).value, workerName=e.worker.name, companyName=e.company.name,
               managerName=e.company.manager.name if e.company.manager else None,
               disabilityType=p.disability_type.value if p and p.disability_type else None,
               disabilityDegree=p.disability_degree.value if p and p.disability_degree else None,
               contract=ser(e.contract) if e.contract else None)


def get_emp(db: Session, eid: int, user: CurrentUser) -> M.Employment:
    e = db.get(M.Employment, eid)
    if not e:
        raise not_found("재직")
    if (user.role == CM and e.company_id != user.company_id) or (user.role == WK and e.worker_id != user.id):
        raise forbidden()
    return e


@router.get("/employments")
def list_emps(company_id: int | None = None, mine: bool = False, include_resigned: bool = False,
              user: CurrentUser = Depends(require(CM, VM)), db: Session = Depends(get_db)):
    q = db.query(M.Employment).join(M.Company)
    if user.role == CM:
        q = q.filter(M.Employment.company_id == user.company_id)
    elif company_id:
        q = q.filter(M.Employment.company_id == company_id)
    if user.role == VM and mine:
        q = q.filter(M.Company.manager_id == user.id)
    today = today_kst()
    rows = [emp_out(e, today) for e in q.order_by(M.Employment.start_date.desc())]
    return ok([r for r in rows if include_resigned or r["status"] != "RESIGNED"])


@router.get("/employments/me")
def my_emps(user: CurrentUser = Depends(require(WK)), db: Session = Depends(get_db)):
    today = today_kst()
    return ok([emp_out(e, today) for e in db.query(M.Employment).filter(M.Employment.worker_id == user.id).order_by(M.Employment.start_date.desc())])


@router.get("/employments/{eid}")
def emp_detail(eid: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(emp_out(get_emp(db, eid, user), today_kst()))


class ContractIn(In):
    contract_type: ContractType
    start_date: date
    end_date: date | None = None
    work_type: WorkType
    work_location: str
    job_description: str
    work_days: str
    work_start_time: time
    work_end_time: time
    break_minutes: int = 60
    weekly_work_hours: Decimal
    annual_leave_days: Decimal | None = None
    salary_type: SalaryType
    salary_amount: int
    insurance_employment: bool = True
    insurance_accident: bool = True
    insurance_pension: bool = True
    insurance_health: bool = True
    equipment_support: str | None = None
    note: str | None = None


@router.put("/employments/{eid}/contract")
def update_contract(eid: int, body: ContractIn, user: CurrentUser = Depends(require(CM, VM)), db: Session = Depends(get_db)):
    e = get_emp(db, eid, user)
    c = e.contract or M.EmploymentContract(employment_id=e.id)
    db.add(c)
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    c.updated_by = user.id
    db.commit()
    return ok(emp_out(e, today_kst()))


# ---------------- RESIGNATIONS ----------------
def resg_out(r: M.ResignationRequest) -> dict:
    return ser(r, workerName=r.worker.name, companyName=r.employment.company.name)


class ResgIn(In):
    planned_date: date
    reason: str


@router.post("/resignations")
def request_resign(body: ResgIn, user: CurrentUser = Depends(require(WK)), db: Session = Depends(get_db)):
    e = current_employment(db, user.id)
    if not e:
        raise AppError("NOT_EMPLOYED", "재직 중인 기업이 없습니다.")
    if db.query(M.ResignationRequest).filter(M.ResignationRequest.employment_id == e.id, M.ResignationRequest.status == RS.PENDING).first():
        raise AppError("ALREADY_REQUESTED", "이미 처리 대기 중인 퇴사 신청이 있습니다.")
    r = M.ResignationRequest(employment_id=e.id, worker_id=user.id, planned_date=body.planned_date, reason=body.reason)
    db.add(r)
    notify(db, company_manager_ids(db, e.company_id), "RESIGNATION_REQUESTED", "퇴사 신청", f"{user.name} ({e.company.name}) 퇴사 예정일 {body.planned_date}", "/admin/resignations")
    db.commit()
    return ok(resg_out(r))


@router.get("/resignations")
def list_resign(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(M.ResignationRequest).join(M.Employment)
    if user.role == WK:
        q = q.filter(M.ResignationRequest.worker_id == user.id)
    elif user.role == CM:
        q = q.filter(M.Employment.company_id == user.company_id, M.ResignationRequest.status == RS.APPROVED)
    elif user.role != VM:
        raise forbidden()
    return ok([resg_out(r) for r in q.order_by(M.ResignationRequest.id.desc())])


def _get_resg(db: Session, rid: int) -> M.ResignationRequest:
    r = db.get(M.ResignationRequest, rid)
    if not r:
        raise not_found("퇴사 신청")
    if r.status != RS.PENDING:
        raise AppError("INVALID_TRANSITION", "이미 처리된 신청입니다.")
    return r


@router.post("/resignations/{rid}/withdraw")
def withdraw_resign(rid: int, user: CurrentUser = Depends(require(WK)), db: Session = Depends(get_db)):
    r = _get_resg(db, rid)
    if r.worker_id != user.id:
        raise forbidden()
    r.status = RS.WITHDRAWN
    db.commit()
    return ok(resg_out(r))


class ResgReviewIn(In):
    confirmed_date: date | None = None
    note: str | None = None


@router.post("/resignations/{rid}/approve")
def approve_resign(rid: int, body: ResgReviewIn, user: CurrentUser = Depends(require(VM)), db: Session = Depends(get_db)):
    r = _get_resg(db, rid)
    r.status, r.reviewed_by, r.reviewed_at, r.review_note = RS.APPROVED, user.id, utcnow(), body.note
    r.confirmed_date = body.confirmed_date or r.planned_date
    r.employment.end_date = r.confirmed_date
    notify(db, [r.worker_id], "RESIGNATION_APPROVED", "퇴사 승인", f"퇴사일이 {r.confirmed_date}로 확정되었습니다.", "/m/more/resign")
    notify(db, company_cm_ids(db, r.employment.company_id), "RESIGNATION_APPROVED", "퇴사 통보", f"{r.worker.name} 퇴사일 {r.confirmed_date} · {r.reason}", "/admin/resignations")
    db.commit()
    return ok(resg_out(r))


@router.post("/resignations/{rid}/reject")
def reject_resign(rid: int, body: ResgReviewIn, user: CurrentUser = Depends(require(VM)), db: Session = Depends(get_db)):
    r = _get_resg(db, rid)
    r.status, r.reviewed_by, r.reviewed_at, r.review_note = RS.REJECTED, user.id, utcnow(), body.note
    notify(db, [r.worker_id], "RESIGNATION_REJECTED", "퇴사 반려", body.note or "", "/m/more/resign")
    db.commit()
    return ok(resg_out(r))


def is_writable_employment(e: M.Employment) -> bool:
    return is_open_employment(e, today_kst())
