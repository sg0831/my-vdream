"""SQLAlchemy models. Mirrors docs/03-database-schema.md (23 tables)."""
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, Time, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import enums as E
from .db import ID, PK, Base, Timestamps, utcnow


def En(cls):  # noqa: N802
    return SAEnum(cls, native_enum=True, values_callable=lambda e: [m.value for m in e], length=40)


def FK(target: str, ondelete: str = "RESTRICT", nullable: bool = True):  # noqa: N802
    return mapped_column(ID, ForeignKey(target, ondelete=ondelete), nullable=nullable, index=True)


class User(PK, Timestamps, Base):
    __tablename__ = "users"
    login_id: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[E.UserRole] = mapped_column(En(E.UserRole), index=True)
    name: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(100))
    # users ↔ companies 순환 참조: 이쪽을 use_alter로 두어 MySQL drop/create 순서를 풀어준다
    company_id: Mapped[int | None] = mapped_column(ID, ForeignKey("companies.id", use_alter=True, name="fk_users_company_id"), index=True)
    status: Mapped[E.UserStatus] = mapped_column(En(E.UserStatus), default=E.UserStatus.ACTIVE)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
    company: Mapped["Company | None"] = relationship(foreign_keys=[company_id])
    profile: Mapped["WorkerProfile | None"] = relationship(back_populates="user", uselist=False)


class Notification(PK, Base):
    __tablename__ = "notifications"
    user_id: Mapped[int] = FK("users.id", "CASCADE", False)
    type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(String(1000))
    link_path: Mapped[str | None] = mapped_column(String(200))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Announcement(PK, Timestamps, Base):
    __tablename__ = "announcements"
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    audience: Mapped[E.AnnouncementAudience] = mapped_column(En(E.AnnouncementAudience))
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    author_id: Mapped[int] = FK("users.id", nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)


class File(PK, Base):
    __tablename__ = "files"
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    original_name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    purpose: Mapped[E.FilePurpose] = mapped_column(En(E.FilePurpose))
    uploaded_by: Mapped[int] = FK("users.id", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Company(PK, Timestamps, Base):
    __tablename__ = "companies"
    name: Mapped[str] = mapped_column(String(100), index=True)
    business_registration_no: Mapped[str | None] = mapped_column(String(20))
    representative_name: Mapped[str | None] = mapped_column(String(50))
    employment_insurance_no: Mapped[str | None] = mapped_column(String(20))
    industry: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(String(300))
    phone: Mapped[str | None] = mapped_column(String(20))
    manager_id: Mapped[int | None] = FK("users.id")
    status: Mapped[E.OrgStatus] = mapped_column(En(E.OrgStatus), default=E.OrgStatus.ACTIVE)
    manager: Mapped["User | None"] = relationship(foreign_keys=[manager_id])


class WorkerProfile(PK, Timestamps, Base):
    __tablename__ = "worker_profiles"
    user_id: Mapped[int] = mapped_column(ID, ForeignKey("users.id"), unique=True)
    birth_date: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[E.Gender | None] = mapped_column(En(E.Gender))
    photo_file_id: Mapped[int | None] = FK("files.id")
    address: Mapped[str | None] = mapped_column(String(300))
    disability_type: Mapped[E.DisabilityType | None] = mapped_column(En(E.DisabilityType))
    disability_type_secondary: Mapped[E.DisabilityType | None] = mapped_column(En(E.DisabilityType))
    disability_degree: Mapped[E.DisabilityDegree | None] = mapped_column(En(E.DisabilityDegree))
    assistive_devices: Mapped[str | None] = mapped_column(String(300))
    has_pc: Mapped[bool | None] = mapped_column(Boolean)
    has_internet: Mapped[bool | None] = mapped_column(Boolean)
    software_skills: Mapped[str | None] = mapped_column(String(500))
    work_environment_note: Mapped[str | None] = mapped_column(String(500))
    desired_job_fields: Mapped[str | None] = mapped_column(String(200))
    skills: Mapped[str | None] = mapped_column(String(1000))
    introduction: Mapped[str | None] = mapped_column(Text)
    job_seeking_status: Mapped[E.JobSeekingStatus] = mapped_column(En(E.JobSeekingStatus), default=E.JobSeekingStatus.NOT_SEEKING, index=True)
    job_seeking_changed_at: Mapped[datetime | None] = mapped_column(DateTime)
    user: Mapped[User] = relationship(back_populates="profile")


class Education(PK, Timestamps, Base):
    __tablename__ = "educations"
    worker_id: Mapped[int] = FK("users.id", "CASCADE", False)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    institution: Mapped[str] = mapped_column(String(100))
    type: Mapped[E.EducationType] = mapped_column(En(E.EducationType))
    status: Mapped[E.EducationStatus] = mapped_column(En(E.EducationStatus))
    major: Mapped[str | None] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Career(PK, Timestamps, Base):
    __tablename__ = "careers"
    worker_id: Mapped[int] = FK("users.id", "CASCADE", False)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    institution: Mapped[str] = mapped_column(String(100))
    employment_type: Mapped[E.CareerType] = mapped_column(En(E.CareerType))
    duties: Mapped[str | None] = mapped_column(String(500))
    position: Mapped[str | None] = mapped_column(String(50))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class JobPosting(PK, Timestamps, Base):
    __tablename__ = "job_postings"
    company_id: Mapped[int] = FK("companies.id", nullable=False)
    title: Mapped[str] = mapped_column(String(200))
    job_field: Mapped[E.JobField] = mapped_column(En(E.JobField), index=True)
    main_duties: Mapped[str] = mapped_column(Text)
    work_type: Mapped[E.WorkType] = mapped_column(En(E.WorkType), default=E.WorkType.REMOTE)
    work_location: Mapped[str | None] = mapped_column(String(300))
    work_days: Mapped[str] = mapped_column(String(32))
    work_start_time: Mapped[time] = mapped_column(Time)
    work_end_time: Mapped[time] = mapped_column(Time)
    weekly_work_hours: Mapped[Decimal] = mapped_column(Numeric(4, 1))
    salary_type: Mapped[E.SalaryType] = mapped_column(En(E.SalaryType))
    salary_amount: Mapped[int] = mapped_column(Integer)
    benefits: Mapped[str | None] = mapped_column(Text)
    equipment_support: Mapped[str | None] = mapped_column(String(500))
    requirements: Mapped[str | None] = mapped_column(Text)
    expected_start_date: Mapped[date] = mapped_column(Date)
    contract_type: Mapped[E.ContractType] = mapped_column(En(E.ContractType))
    expected_end_date: Mapped[date | None] = mapped_column(Date)
    headcount: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str | None] = mapped_column(Text)
    deadline_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[E.JobPostingStatus] = mapped_column(En(E.JobPostingStatus), default=E.JobPostingStatus.DRAFT)
    author_type: Mapped[E.PostingAuthorType] = mapped_column(En(E.PostingAuthorType))
    reject_reason: Mapped[str | None] = mapped_column(String(500))
    approved_by: Mapped[int | None] = FK("users.id")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_by: Mapped[int] = FK("users.id", nullable=False)
    company: Mapped[Company] = relationship()


class JobApplication(PK, Timestamps, Base):
    __tablename__ = "job_applications"
    __table_args__ = (UniqueConstraint("job_posting_id", "worker_id"),)
    job_posting_id: Mapped[int] = FK("job_postings.id", nullable=False)
    worker_id: Mapped[int] = FK("users.id", nullable=False)
    status: Mapped[E.ApplicationStatus] = mapped_column(En(E.ApplicationStatus), default=E.ApplicationStatus.APPLIED)
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    document_result_at: Mapped[datetime | None] = mapped_column(DateTime)
    interview_at: Mapped[datetime | None] = mapped_column(DateTime)
    interview_method: Mapped[E.InterviewMethod | None] = mapped_column(En(E.InterviewMethod))
    interview_location: Mapped[str | None] = mapped_column(String(500))
    interview_note: Mapped[str | None] = mapped_column(String(500))
    final_result_at: Mapped[datetime | None] = mapped_column(DateTime)
    start_date: Mapped[date | None] = mapped_column(Date)
    employment_id: Mapped[int | None] = mapped_column(ID, ForeignKey("employments.id", use_alter=True, name="fk_job_applications_employment_id"), unique=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_updated_by: Mapped[int | None] = FK("users.id")
    posting: Mapped[JobPosting] = relationship()
    worker: Mapped[User] = relationship(foreign_keys=[worker_id])


class ResignationRequest(PK, Timestamps, Base):
    __tablename__ = "resignation_requests"
    employment_id: Mapped[int] = FK("employments.id", nullable=False)
    worker_id: Mapped[int] = FK("users.id", nullable=False)
    planned_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(String(1000))
    status: Mapped[E.ResignationStatus] = mapped_column(En(E.ResignationStatus), default=E.ResignationStatus.PENDING)
    confirmed_date: Mapped[date | None] = mapped_column(Date)
    reviewed_by: Mapped[int | None] = FK("users.id")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    review_note: Mapped[str | None] = mapped_column(String(500))
    employment: Mapped["Employment"] = relationship()
    worker: Mapped[User] = relationship(foreign_keys=[worker_id])


class Employment(PK, Timestamps, Base):
    __tablename__ = "employments"
    worker_id: Mapped[int] = FK("users.id", nullable=False)
    company_id: Mapped[int] = FK("companies.id", nullable=False)
    job_application_id: Mapped[int | None] = mapped_column(ID, ForeignKey("job_applications.id"), unique=True)
    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date | None] = mapped_column(Date)
    worker: Mapped[User] = relationship(foreign_keys=[worker_id])
    company: Mapped[Company] = relationship()
    contract: Mapped["EmploymentContract | None"] = relationship(back_populates="employment", uselist=False)


class EmploymentContract(PK, Timestamps, Base):
    __tablename__ = "employment_contracts"
    employment_id: Mapped[int] = mapped_column(ID, ForeignKey("employments.id"), unique=True)
    contract_type: Mapped[E.ContractType] = mapped_column(En(E.ContractType))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    work_type: Mapped[E.WorkType] = mapped_column(En(E.WorkType), default=E.WorkType.REMOTE)
    work_location: Mapped[str] = mapped_column(String(300))
    job_description: Mapped[str] = mapped_column(String(500))
    work_days: Mapped[str] = mapped_column(String(32))
    work_start_time: Mapped[time] = mapped_column(Time)
    work_end_time: Mapped[time] = mapped_column(Time)
    break_minutes: Mapped[int] = mapped_column(Integer, default=60)
    weekly_work_hours: Mapped[Decimal] = mapped_column(Numeric(4, 1))
    annual_leave_days: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    salary_type: Mapped[E.SalaryType] = mapped_column(En(E.SalaryType))
    salary_amount: Mapped[int] = mapped_column(Integer)
    insurance_employment: Mapped[bool] = mapped_column(Boolean, default=True)
    insurance_accident: Mapped[bool] = mapped_column(Boolean, default=True)
    insurance_pension: Mapped[bool] = mapped_column(Boolean, default=True)
    insurance_health: Mapped[bool] = mapped_column(Boolean, default=True)
    equipment_support: Mapped[str | None] = mapped_column(String(500))
    note: Mapped[str | None] = mapped_column(String(1000))
    updated_by: Mapped[int | None] = FK("users.id")
    employment: Mapped[Employment] = relationship(back_populates="contract")


class AttendanceRecord(PK, Timestamps, Base):
    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("employment_id", "work_date"),)
    employment_id: Mapped[int] = FK("employments.id", nullable=False)
    work_date: Mapped[date] = mapped_column(Date, index=True)
    check_in_at: Mapped[datetime | None] = mapped_column(DateTime)
    check_out_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[E.AttendanceStatus] = mapped_column(En(E.AttendanceStatus))
    half_day_type: Mapped[E.HalfDayType | None] = mapped_column(En(E.HalfDayType))
    late_minutes: Mapped[int] = mapped_column(Integer, default=0)
    early_leave_minutes: Mapped[int] = mapped_column(Integer, default=0)
    worker_late_reason: Mapped[str | None] = mapped_column(String(500))
    worker_early_leave_reason: Mapped[str | None] = mapped_column(String(500))
    leave_request_id: Mapped[int | None] = FK("leave_requests.id")
    corrected_by: Mapped[int | None] = FK("users.id")
    corrected_at: Mapped[datetime | None] = mapped_column(DateTime)
    correction_note: Mapped[str | None] = mapped_column(String(500))


class LeaveGrant(PK, Timestamps, Base):
    __tablename__ = "leave_grants"
    __table_args__ = (UniqueConstraint("employment_id", "year"),)
    employment_id: Mapped[int] = FK("employments.id", nullable=False)
    year: Mapped[int] = mapped_column(Integer)
    granted_days: Mapped[Decimal] = mapped_column(Numeric(4, 1))
    created_by: Mapped[int] = FK("users.id", nullable=False)


class LeaveRequest(PK, Timestamps, Base):
    __tablename__ = "leave_requests"
    employment_id: Mapped[int] = FK("employments.id", nullable=False)
    leave_type: Mapped[E.LeaveType] = mapped_column(En(E.LeaveType))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    days: Mapped[Decimal] = mapped_column(Numeric(4, 1))
    reason: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[E.LeaveStatus] = mapped_column(En(E.LeaveStatus), default=E.LeaveStatus.PENDING)
    reviewed_by: Mapped[int | None] = FK("users.id")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    review_note: Mapped[str | None] = mapped_column(String(500))
    employment: Mapped[Employment] = relationship()


class Task(PK, Timestamps, Base):
    __tablename__ = "tasks"
    employment_id: Mapped[int] = FK("employments.id", nullable=False)
    company_id: Mapped[int] = FK("companies.id", nullable=False)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[E.TaskPriority] = mapped_column(En(E.TaskPriority), default=E.TaskPriority.NORMAL)
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[E.TaskStatus] = mapped_column(En(E.TaskStatus), default=E.TaskStatus.ASSIGNED)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    completion_note: Mapped[str | None] = mapped_column(String(1000))
    cancel_reason: Mapped[str | None] = mapped_column(String(500))
    total_minutes: Mapped[int] = mapped_column(Integer, default=0)
    status_changed_by: Mapped[int | None] = FK("users.id")
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime)
    assigned_by: Mapped[int] = FK("users.id", nullable=False)
    employment: Mapped[Employment] = relationship()


class WorkLog(PK, Timestamps, Base):
    __tablename__ = "work_logs"
    __table_args__ = (UniqueConstraint("employment_id", "work_date"),)
    employment_id: Mapped[int] = FK("employments.id", nullable=False)
    company_id: Mapped[int] = FK("companies.id", nullable=False)
    work_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[E.WorkLogStatus] = mapped_column(En(E.WorkLogStatus), default=E.WorkLogStatus.DRAFT)
    summary: Mapped[str | None] = mapped_column(String(1000))
    issues: Mapped[str | None] = mapped_column(String(1000))
    total_minutes: Mapped[int] = mapped_column(Integer, default=0)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    first_submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    reviewed_by: Mapped[int | None] = FK("users.id")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    review_comment: Mapped[str | None] = mapped_column(String(1000))
    employment: Mapped[Employment] = relationship()
    entries: Mapped[list["WorkLogEntry"]] = relationship(cascade="all, delete-orphan", order_by="WorkLogEntry.sort_order")
    files: Mapped[list["WorkLogFile"]] = relationship(cascade="all, delete-orphan")


class WorkLogEntry(PK, Timestamps, Base):
    __tablename__ = "work_log_entries"
    work_log_id: Mapped[int] = FK("work_logs.id", "CASCADE", False)
    task_id: Mapped[int | None] = FK("tasks.id")
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    minutes: Mapped[int] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class WorkLogFile(PK, Base):
    __tablename__ = "work_log_files"
    __table_args__ = (UniqueConstraint("work_log_id", "file_id"),)
    work_log_id: Mapped[int] = FK("work_logs.id", "CASCADE", False)
    file_id: Mapped[int] = FK("files.id", nullable=False)
    file: Mapped[File] = relationship()


class CounselingReport(PK, Timestamps, Base):
    __tablename__ = "counseling_reports"
    worker_id: Mapped[int] = FK("users.id", nullable=False)
    employment_id: Mapped[int | None] = FK("employments.id")
    company_id: Mapped[int | None] = FK("companies.id")
    method: Mapped[E.CounselingMethod] = mapped_column(En(E.CounselingMethod))
    counseled_at: Mapped[datetime] = mapped_column(DateTime)
    topic: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    condition_score: Mapped[int] = mapped_column(Integer)
    follow_up: Mapped[str | None] = mapped_column(String(1000))
    author_id: Mapped[int] = FK("users.id", nullable=False)
    updated_by: Mapped[int | None] = FK("users.id")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)


class Message(PK, Base):
    __tablename__ = "messages"
    sender_id: Mapped[int] = FK("users.id", nullable=False)
    title: Mapped[str] = mapped_column(String(100))
    body: Mapped[str] = mapped_column(Text)
    audience: Mapped[E.MessageAudience] = mapped_column(En(E.MessageAudience), default=E.MessageAudience.INDIVIDUAL)
    audience_company_id: Mapped[int | None] = FK("companies.id")
    parent_message_id: Mapped[int | None] = FK("messages.id")
    recipient_count: Mapped[int] = mapped_column(Integer, default=0)
    sender_deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    sender: Mapped[User] = relationship(foreign_keys=[sender_id])
    recipients: Mapped[list["MessageRecipient"]] = relationship(cascade="all, delete-orphan")


class MessageRecipient(PK, Base):
    __tablename__ = "message_recipients"
    __table_args__ = (UniqueConstraint("message_id", "recipient_id"),)
    message_id: Mapped[int] = FK("messages.id", "CASCADE", False)
    recipient_id: Mapped[int] = FK("users.id", nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    message: Mapped[Message] = relationship(back_populates="recipients")
    recipient: Mapped[User] = relationship()
