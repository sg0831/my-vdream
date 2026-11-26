"""Deterministic demo seed. Dates are relative to today (KST), covering the last 3 months."""
import hashlib
from datetime import date, time, timedelta
from decimal import Decimal

from . import models as M
from .config import settings
from .core import hash_pw
from .db import Base, SessionLocal, engine
from .domain import is_workday, kst_to_utc_naive, today_kst
from .enums import (
    AnnouncementAudience,
    CareerType,
    ContractType,
    CounselingMethod,
    EducationStatus,
    EducationType,
    Gender,
    InterviewMethod,
    JobSeekingStatus,
    LeaveStatus,
    LeaveType,
    MessageAudience,
    PostingAuthorType,
    SalaryType,
    TaskPriority,
    WorkType,
)
from .enums import ApplicationStatus as AS
from .enums import AttendanceStatus as AT
from .enums import DisabilityDegree as DD
from .enums import DisabilityType as DT
from .enums import JobField as JF
from .enums import JobPostingStatus as PS
from .enums import TaskStatus as TS
from .enums import UserRole as R
from .enums import WorkLogStatus as WS


def rnd(*key) -> float:
    h = hashlib.md5("|".join(map(str, key)).encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def month_start(d: date, back: int) -> date:
    y, m = d.year, d.month - back
    while m <= 0:
        y, m = y - 1, m + 12
    return date(y, m, 1)


TASKS = {
    JF.DATA_LABELING: ["이미지 객체 라벨링 1차", "음성 전사 데이터 검수", "상품 이미지 분류", "라벨링 가이드 피드백 정리", "OCR 결과 교정", "AI 학습 데이터 품질 점검"],
    JF.DOCUMENT_ENTRY: ["계약서 스캔본 전산 입력", "거래처 정보 엑셀 정리", "설문 응답 코딩", "영수증 데이터 입력", "고객 명부 중복 정리", "월간 자료 색인 작업"],
    JF.CONTENT_MONITORING: ["커뮤니티 게시글 검수", "상품 리뷰 분류", "신고 게시물 1차 검토", "금칙어 목록 업데이트", "검수 결과 주간 리포트", "이미지 유해성 검토"],
    JF.DESIGN: ["SNS 카드뉴스 제작", "이벤트 배너 시안", "상세페이지 썸네일", "아이콘 세트 정리", "브랜드 템플릿 수정", "뉴스레터 헤더 이미지"],
    JF.CONTENT_WRITING: ["블로그 원고 작성", "상품 설명 문구", "보도자료 초안 교정", "SNS 캡션 작성", "FAQ 문서 정리", "뉴스레터 본문"],
}


def clear_all_tables() -> None:
    """데모 초기화: 스키마는 그대로 두고 모든 행을 지운다 (DB 정의서 공통 규칙). 운영 스키마는 Alembic이 관리."""
    Base.metadata.create_all(engine)  # 없을 때만 생성 (SQLite 개발·테스트)
    tables = list(Base.metadata.tables)
    with engine.begin() as c:
        if engine.dialect.name == "mysql":
            c.exec_driver_sql("SET FOREIGN_KEY_CHECKS=0")
            for t in tables:
                c.exec_driver_sql(f"TRUNCATE TABLE `{t}`")
            c.exec_driver_sql("SET FOREIGN_KEY_CHECKS=1")
        else:
            c.exec_driver_sql("PRAGMA foreign_keys=OFF")
            for t in tables:
                c.exec_driver_sql(f'DELETE FROM "{t}"')


def reset_and_seed() -> dict:
    from . import models  # noqa: F401
    clear_all_tables()
    db = SessionLocal()
    today = today_kst()
    start = month_start(today, 2)
    pw = hash_pw(settings.demo_password)

    def user(login, name, role, company=None, demo=False, phone=None):
        u = M.User(login_id=login, name=name, role=role, company_id=company.id if company else None, is_demo=demo, password_hash=pw,
                   phone=phone, email=f"{login}@example.com")
        db.add(u)
        db.flush()
        if role == R.WORKER:
            db.add(M.WorkerProfile(user_id=u.id))
            db.flush()
        return u

    admin = user("demo.admin", "관리자", R.SYSTEM_ADMIN, demo=True)
    vm1 = user("demo.manager", "송유나", R.VDREAM_MANAGER, demo=True, phone="010-2100-1001")
    vm2 = user("vm.oh", "오세훈", R.VDREAM_MANAGER, phone="010-2100-1002")
    c1 = M.Company(name="(주)하늘데이터", business_registration_no="214-81-12345", representative_name="한상민", employment_insurance_no="21481123450",
                   industry="AI 데이터 서비스", address="서울시 강남구 테헤란로 100", phone="02-555-1000", manager_id=vm1.id)
    c2 = M.Company(name="(주)누리커머스", business_registration_no="120-86-54321", representative_name="박나래", employment_insurance_no="12086543210",
                   industry="온라인 쇼핑몰", address="경기도 성남시 판교역로 50", phone="031-700-2000", manager_id=vm1.id)
    c3 = M.Company(name="(주)바른리서치", business_registration_no="105-87-11111", representative_name="이도윤", employment_insurance_no="10587111110",
                   industry="시장 조사", address="서울시 마포구 월드컵로 20", phone="02-333-3000", manager_id=vm2.id)
    db.add_all([c1, c2, c3])
    db.flush()
    cm1 = user("demo.company", "이수진", R.COMPANY_MANAGER, c1, demo=True, phone="010-3100-2001")
    cm2 = user("cm.kang", "강태호", R.COMPANY_MANAGER, c2)
    user("cm.moon", "문예린", R.COMPANY_MANAGER, c3)

    # name, login, company, degree, type, field, weekly, days, start, end, months_employed
    W = [
        ("김민지", "demo.worker", c1, DD.SEVERE, DT.VISUAL, JF.DATA_LABELING, 40, "MON,TUE,WED,THU,FRI", time(9), time(18), 8, "스크린리더(NVDA), 점자정보단말기"),
        ("이준호", "wk.lee", c1, DD.MILD, DT.PHYSICAL, JF.DOCUMENT_ENTRY, 40, "MON,TUE,WED,THU,FRI", time(9), time(18), 14, "높낮이 조절 책상"),
        ("박서연", "wk.park", c1, DD.SEVERE, DT.HEARING, JF.DESIGN, 12.5, "MON,TUE,WED,THU,FRI", time(10), time(12, 30), 6, "보청기"),
        ("정우진", "wk.jung", c1, DD.MILD, DT.BRAIN_LESION, JF.CONTENT_MONITORING, 12, "MON,WED,FRI", time(10), time(14), 10, None),
        ("최하늘", "wk.choi", c1, DD.MILD, DT.MENTAL, JF.CONTENT_WRITING, 40, "MON,TUE,WED,THU,FRI", time(9), time(18), 0, None),
        ("한지수", "wk.han", c2, DD.SEVERE, DT.PHYSICAL, JF.CONTENT_MONITORING, 40, "MON,TUE,WED,THU,FRI", time(9), time(18), 5, "전동휠체어"),
    ]
    emps = []
    for i, (name, login, comp, deg, dtype, field, weekly, days, st, et, months, devices) in enumerate(W):
        u = user(login, name, R.WORKER, demo=login == "demo.worker", phone=f"010-4{i}00-30{i:02d}")
        p = u.profile
        p.birth_date, p.gender = date(1988 + i * 2, (i % 12) + 1, 10 + i), [Gender.FEMALE, Gender.MALE][i % 2]
        p.address, p.disability_type, p.disability_degree, p.assistive_devices = "서울시", dtype, deg, devices
        p.has_pc, p.has_internet, p.software_skills = True, True, "엑셀, 한글, 구글 문서"
        p.desired_job_fields, p.skills, p.introduction = field.value, "꼼꼼한 검수, 문서 정리", f"{name}입니다. 재택으로 꾸준히 일하고 싶습니다."
        db.add(M.Education(worker_id=u.id, start_date=date(2007 + i, 3, 1), end_date=date(2011 + i, 2, 20), institution="한빛대학교",
                           type=EducationType.UNIVERSITY, status=EducationStatus.GRADUATED, major="경영학"))
        db.add(M.Career(worker_id=u.id, start_date=date(2015, 3, 1), end_date=date(2017, 12, 31), institution="(주)가나상사",
                        employment_type=CareerType.EMPLOYEE, duties="사무 보조", position="사원"))
        sd = month_start(today, 1) + timedelta(days=14) if months == 0 else month_start(today, months)
        e = M.Employment(worker_id=u.id, company_id=comp.id, start_date=sd)
        db.add(e)
        db.flush()
        db.add(M.EmploymentContract(employment_id=e.id, contract_type=ContractType.INDEFINITE, start_date=sd, work_type=WorkType.REMOTE,
                                    work_location="자택", job_description=f"{field.value} 재택 업무", work_days=days, work_start_time=st, work_end_time=et,
                                    break_minutes=60 if weekly >= 40 else 0, weekly_work_hours=Decimal(str(weekly)), annual_leave_days=Decimal(15),
                                    salary_type=SalaryType.MONTHLY if weekly >= 40 else SalaryType.HOURLY,
                                    salary_amount=2_200_000 if weekly >= 40 else 10_500, equipment_support="노트북 대여"))
        db.flush()
        db.refresh(e)
        emps.append((e, u, field))
    seekers = []
    for j, (name, login, dtype, field) in enumerate([("윤가은", "wk.yoon", DT.AUTISM, JF.DATA_LABELING), ("장도현", "wk.jang", DT.VISUAL, JF.DOCUMENT_ENTRY), ("서지훈", "wk.seo", DT.HEARING, JF.CONTENT_MONITORING)]):
        u = user(login, name, R.WORKER, phone=f"010-5{j}00-4000")
        p = u.profile
        p.birth_date, p.gender, p.disability_type, p.disability_degree = date(1996 + j, 5, 5), Gender.MALE, dtype, DD.SEVERE if j else DD.MILD
        p.desired_job_fields, p.job_seeking_status, p.has_pc, p.has_internet = field.value, JobSeekingStatus.SEEKING, True, True
        p.introduction = "데이터 작업에 관심이 많습니다."
        seekers.append(u)
    db.flush()

    # tasks
    task_map: dict[int, list[M.Task]] = {}
    for idx, (e, u, field) in enumerate(emps):
        titles, ts = TASKS[field], []
        for k, title in enumerate(titles):
            st_ = TS.COMPLETED if k < 3 else TS.IN_PROGRESS if k == 3 else TS.ASSIGNED
            due = today - timedelta(days=40 - k * 12) if k < 3 else today + timedelta(days=k - 3) if k != 5 else today - timedelta(days=2)
            t = M.Task(employment_id=e.id, company_id=e.company_id, title=title, description=f"{title} 관련 작업입니다. 가이드 문서를 참고해 주세요.",
                       priority=[TaskPriority.NORMAL, TaskPriority.HIGH, TaskPriority.LOW][k % 3], due_date=max(due, e.start_date), status=st_,
                       assigned_by=cm1.id if e.company_id == c1.id else cm2.id)
            if st_ == TS.COMPLETED:
                t.started_at = kst_to_utc_naive(max(due, e.start_date) - timedelta(days=3), time(10))
                t.completed_at = kst_to_utc_naive(max(due, e.start_date), time(16))
            if st_ == TS.IN_PROGRESS:
                t.started_at = kst_to_utc_naive(today - timedelta(days=2), time(10))
            db.add(t)
            ts.append(t)
        db.flush()
        task_map[e.id] = ts

    # attendance, leaves, work logs (last 3 months)
    counts = {"attendance": 0, "workLogs": 0}
    for idx, (e, u, field) in enumerate(emps):
        c, d = e.contract, max(start, e.start_date)
        ts = task_map[e.id]
        returned_done = False
        while d <= today:
            if not is_workday(c, d):
                d += timedelta(days=1)
                continue
            r = rnd(idx, d)
            if d == today:
                if u.login_id != "demo.worker" and r < 0.8:
                    db.add(M.AttendanceRecord(employment_id=e.id, work_date=d, status=AT.NORMAL, check_in_at=kst_to_utc_naive(d, c.work_start_time) - timedelta(minutes=5)))
                break
            if r < 0.03:  # absent (computed, no row)
                d += timedelta(days=1)
                continue
            if r < 0.07:  # approved annual leave
                lv = M.LeaveRequest(employment_id=e.id, leave_type=LeaveType.ANNUAL, start_date=d, end_date=d, days=Decimal(1), reason="개인 사유",
                                    status=LeaveStatus.APPROVED, reviewed_by=cm1.id, reviewed_at=kst_to_utc_naive(d - timedelta(days=3), time(10)))
                db.add(lv)
                d += timedelta(days=1)
                continue
            late = int(5 + rnd("late", idx, d) * 25) if r > 0.95 else 0
            early = int(20 + rnd("early", idx, d) * 40) if 0.92 < r <= 0.95 else 0
            cin = kst_to_utc_naive(d, c.work_start_time) + timedelta(minutes=late if late else -int(rnd("in", idx, d) * 10))
            cout = kst_to_utc_naive(d, c.work_end_time) + timedelta(minutes=-early if early else int(rnd("out", idx, d) * 15))
            missing_out = idx == 1 and d.month == month_start(today, 1).month and d.day in (6, 7)
            status = AT.LATE if late else AT.EARLY_LEAVE if early else AT.NORMAL
            db.add(M.AttendanceRecord(employment_id=e.id, work_date=d, check_in_at=cin, check_out_at=None if missing_out else cout,
                                      status=status, late_minutes=late, early_leave_minutes=early,
                                      worker_late_reason="병원 진료 후 출근" if late else None))
            counts["attendance"] += 1
            if rnd("nolog", idx, d) < 0.04:  # attended but no work log (warning)
                d += timedelta(days=1)
                continue
            age = (today - d).days
            st_ = WS.CONFIRMED if age > 6 else WS.SUBMITTED
            if not returned_done and age in (3, 4, 5) and idx in (0, 1):
                st_, returned_done = WS.RETURNED, True
            total_min = max(60, int((cout - cin).total_seconds() // 60) - c.break_minutes)
            picks = [ts[int(rnd("t1", idx, d) * 4)], ts[3 + int(rnd("t2", idx, d) * 3)]]
            first = int(total_min * 0.6 // 15 * 15)
            entries = [M.WorkLogEntry(task_id=picks[0].id, title=picks[0].title, content=f"{picks[0].title} 진행. 분량의 일부를 처리했습니다.", minutes=first, sort_order=0),
                       M.WorkLogEntry(task_id=picks[1].id, title=picks[1].title, content=f"{picks[1].title} 검토 및 정리.", minutes=total_min - first, sort_order=1)]
            sub = kst_to_utc_naive(d, c.work_end_time) - timedelta(minutes=10)
            w = M.WorkLog(employment_id=e.id, company_id=e.company_id, work_date=d, status=st_, summary=f"{picks[0].title} 위주로 작업",
                          issues="특이사항 없음" if r < 0.8 else "작업 가이드 문의 필요", total_minutes=total_min, submitted_at=sub, first_submitted_at=sub,
                          reviewed_by=cm1.id if st_ != WS.SUBMITTED else None, reviewed_at=sub + timedelta(hours=16) if st_ != WS.SUBMITTED else None,
                          review_comment="수행 내용을 조금 더 구체적으로 적어 주세요." if st_ == WS.RETURNED else None)
            w.entries = entries
            db.add(w)
            counts["workLogs"] += 1
            d += timedelta(days=1)
    db.flush()
    for e, u, field in emps:
        for t in task_map[e.id]:
            t.total_minutes = sum(en.minutes for en in db.query(M.WorkLogEntry).filter(M.WorkLogEntry.task_id == t.id))
    # pending leaves, resignation
    e0, e3 = emps[0][0], emps[3][0]
    db.add(M.LeaveRequest(employment_id=e0.id, leave_type=LeaveType.HALF_DAY_PM, start_date=today + timedelta(days=5), end_date=today + timedelta(days=5),
                          days=Decimal("0.5"), reason="병원 정기 검진"))
    db.add(M.LeaveRequest(employment_id=emps[1][0].id, leave_type=LeaveType.ANNUAL, start_date=today + timedelta(days=8), end_date=today + timedelta(days=9),
                          days=Decimal(2), reason="가족 행사"))
    db.add(M.ResignationRequest(employment_id=e3.id, worker_id=e3.worker_id, planned_date=today + timedelta(days=30), reason="학업 병행을 위해"))

    # postings & applications
    def posting(comp, title, field, status, author, creator, hours=40):
        p = M.JobPosting(company_id=comp.id, title=title, job_field=field, main_duties=f"{title} 업무를 재택으로 수행합니다.", work_type=WorkType.REMOTE,
                         work_days="MON,TUE,WED,THU,FRI", work_start_time=time(9), work_end_time=time(18) if hours == 40 else time(13),
                         weekly_work_hours=Decimal(hours), salary_type=SalaryType.MONTHLY, salary_amount=2_250_000 if hours == 40 else 1_100_000,
                         benefits="4대보험, 장비 지원, 명절 선물", equipment_support="노트북·모니터 대여", requirements="엑셀 기본 활용 가능자",
                         expected_start_date=today + timedelta(days=21), contract_type=ContractType.INDEFINITE, headcount=2,
                         description="장애인 재택근무 직무입니다. 근무 시간 조정 가능합니다.", deadline_date=today + timedelta(days=14), status=status,
                         author_type=author, created_by=creator.id,
                         approved_by=vm1.id if status in (PS.PUBLISHED, PS.CLOSED) else None,
                         reject_reason="급여 조건을 최저임금 기준에 맞게 확인해 주세요." if status == PS.REJECTED else None)
        if status in (PS.PUBLISHED, PS.CLOSED):
            p.approved_at = kst_to_utc_naive(today - timedelta(days=10), time(10))
        db.add(p)
        db.flush()
        return p
    p1 = posting(c1, "AI 학습 데이터 라벨러 (재택)", JF.DATA_LABELING, PS.PUBLISHED, PostingAuthorType.COMPANY, cm1)
    p2 = posting(c1, "문서 전산화 담당 (재택, 주 20시간)", JF.DOCUMENT_ENTRY, PS.PUBLISHED, PostingAuthorType.VDREAM, vm1, 20)
    p3 = posting(c2, "상품 리뷰 모니터링 (재택)", JF.CONTENT_MONITORING, PS.PUBLISHED, PostingAuthorType.COMPANY, cm2)
    posting(c1, "카드뉴스 디자이너 (재택)", JF.DESIGN, PS.PENDING_APPROVAL, PostingAuthorType.COMPANY, cm1)
    posting(c1, "블로그 원고 작성자", JF.CONTENT_WRITING, PS.DRAFT, PostingAuthorType.COMPANY, cm1)
    p6 = posting(c2, "고객 채팅 상담원", JF.CUSTOMER_SUPPORT, PS.REJECTED, PostingAuthorType.COMPANY, cm2)
    p7 = posting(c1, "콘텐츠 작성 보조 (재택)", JF.CONTENT_WRITING, PS.CLOSED, PostingAuthorType.COMPANY, cm1)
    del p6
    s1, s2, s3 = seekers
    apps = [(p1, s1, AS.APPLIED), (p2, s1, AS.DOCUMENT_PASSED), (p3, s1, AS.INTERVIEW_SCHEDULED), (p1, s2, AS.DOCUMENT_FAILED),
            (p2, s2, AS.PASSED), (p3, s2, AS.APPLIED), (p7, s1, AS.FAILED), (p7, s2, AS.CANCELLED), (p3, s3, AS.DOCUMENT_PASSED)]
    for p, w, st_ in apps:
        a = M.JobApplication(job_posting_id=p.id, worker_id=w.id, status=st_, applied_at=kst_to_utc_naive(today - timedelta(days=7), time(11)))
        if st_ == AS.INTERVIEW_SCHEDULED:
            a.interview_at, a.interview_method = kst_to_utc_naive(today + timedelta(days=3), time(14)), InterviewMethod.VIDEO
            a.interview_location, a.interview_note = "https://meet.example.com/vdream-interview", "브이드림 매니저가 함께 참석합니다."
        db.add(a)
    choi = emps[4]
    db.flush()
    a = M.JobApplication(job_posting_id=p7.id, worker_id=choi[1].id, status=AS.HIRED, start_date=choi[0].start_date, employment_id=choi[0].id,
                         applied_at=kst_to_utc_naive(choi[0].start_date - timedelta(days=30), time(10)))
    db.add(a)
    db.flush()
    choi[0].job_application_id = a.id

    # counseling
    topics = ["입사 후 적응 상담", "업무량과 컨디션 점검", "근무 환경(보조기기) 점검"]
    for idx, (e, u, field) in enumerate(emps):
        for k in range(3):
            when = today - timedelta(days=75 - k * 30)
            if when < e.start_date:
                continue
            db.add(M.CounselingReport(worker_id=u.id, employment_id=e.id, company_id=e.company_id,
                                      method=[CounselingMethod.PHONE, CounselingMethod.VIDEO, CounselingMethod.CHAT][k], counseled_at=kst_to_utc_naive(when, time(15)),
                                      topic=topics[k], content="업무 진행 상황과 컨디션을 확인했습니다. 근무 시간 배분에 대한 어려움을 이야기했습니다.",
                                      condition_score=min(5, 2 + k + idx % 2), follow_up="2주 뒤 재확인", author_id=vm1.id if e.company_id != c3.id else vm2.id))

    # messages
    def msg(sender, recips, title, body, days_ago, read=True, audience=MessageAudience.INDIVIDUAL, company=None, parent=None):
        m = M.Message(sender_id=sender.id, title=title, body=body, audience=audience, audience_company_id=company.id if company else None,
                      parent_message_id=parent.id if parent else None, recipient_count=len(recips),
                      created_at=kst_to_utc_naive(today - timedelta(days=days_ago), time(10)))
        m.recipients = [M.MessageRecipient(recipient_id=r.id, read_at=m.created_at + timedelta(hours=1) if read else None) for r in recips]
        db.add(m)
        db.flush()
        return m
    wk = emps[0][1]
    m1 = msg(wk, [cm1], "라벨링 가이드 문의", "새로 받은 객체 라벨링 가이드에서 겹친 물체 처리 기준이 궁금합니다.", 3)
    msg(cm1, [wk], "RE: 라벨링 가이드 문의", "겹친 경우에는 앞쪽 물체만 전체 박스로 표시해 주세요. 가이드 2.3절도 업데이트했습니다.", 2, read=False, parent=m1)
    msg(cm1, [vm1], "신규 채용 일정 상의", "다음 달 라벨러 2명 추가 채용을 계획 중입니다. 공고 일정 상의 부탁드립니다.", 4)
    msg(vm1, [cm1] + [e.worker for e, _, _ in emps if e.company_id == c1.id], "[브이드림] 12월 근무 안내", "연말 공휴일 근무 일정을 확인해 주세요. 궁금한 점은 쪽지로 남겨 주세요.",
        1, read=False, audience=MessageAudience.COMPANY_MEMBERS, company=c1)
    msg(vm1, [wk], "상담 일정 안내", "이번 주 금요일 오후 3시에 화상 상담을 진행하려고 합니다. 괜찮으신지 답장 부탁드려요.", 0, read=False)

    # announcements & notifications
    db.add_all([
        M.Announcement(title="my-vdream 데모에 오신 것을 환영합니다", content="역할별 데모 계정으로 기능을 둘러보세요. 데이터는 시스템관리자가 초기화할 수 있습니다.",
                       audience=AnnouncementAudience.ALL, is_pinned=True, author_id=admin.id),
        M.Announcement(title="업무일지 작성 요령", content="수행한 업무를 항목별로 나누고 소요 시간을 적어 주세요.", audience=AnnouncementAudience.WORKER, author_id=admin.id),
        M.Announcement(title="월간 장애인 고용 리포트 기능 안내", content="고용 리포트 메뉴에서 공단 제출용 증빙 자료를 만들 수 있습니다.", audience=AnnouncementAudience.COMPANY, author_id=admin.id),
        M.Announcement(title="담당 기업 배정 변경", content="12월부터 일부 기업의 담당 매니저가 변경됩니다.", audience=AnnouncementAudience.VDREAM, author_id=admin.id),
    ])
    for uid, title, body, link in [(wk.id, "새 업무", "AI 학습 데이터 품질 점검", "/m/tasks"), (wk.id, "업무일지 확인", "업무일지가 확인되었습니다.", "/m/log"),
                                   (cm1.id, "업무일지 제출", "김민지 · 업무일지 제출", "/admin/work-logs"), (cm1.id, "휴가 신청", "김민지 오후 반차 신청", "/admin/leaves"),
                                   (vm1.id, "퇴사 신청", "정우진 퇴사 신청", "/admin/resignations"), (vm1.id, "공고 승인 요청", "카드뉴스 디자이너 (재택)", "/admin/postings")]:
        db.add(M.Notification(user_id=uid, type="SEED", title=title, body=body, link_path=link))
    db.commit()
    result = {"users": db.query(M.User).count(), "employments": len(emps), **counts}
    db.close()
    return result
