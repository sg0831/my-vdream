# my-vdream 기술스펙정의서

| 항목 | 내용 |
|---|---|
| 문서 버전 | v2.0 (포트폴리오 2주 범위, 2026-11-19 작성) |
| 작성일 | 2026-11-19 |
| 관련 문서 | [프로젝트 개요](01-project-overview.md) · [요구기능정의서](02-functional-requirements.md) · [DB 테이블 정의서](03-database-schema.md) · [개발 계획](05-development-plan.md) |

---

## 1. 기술 스택 요약

백엔드는 Python(FastAPI), 프론트엔드는 TypeScript(React) 단일 앱이다. 모바일 앱은 만들지 않는다. 아래 버전은 기준 버전이며 세팅 시점의 최신 안정 버전을 사용한다.

| 영역 | 기술 | 기준 버전 | 비고 |
|---|---|---|---|
| 백엔드 언어 | Python | 3.12 | 타입 힌트, mypy |
| 백엔드 패키지 관리 | uv | 0.5.x | `uv.lock` |
| 백엔드 프레임워크 | FastAPI | 0.115.x | REST API, OpenAPI 자동 생성 |
| ASGI 서버 | uvicorn | - | 운영도 uvicorn 워커 2개 |
| ORM | SQLAlchemy | 2.0.x | 동기 세션, `Mapped[]` 선언형 |
| DB 드라이버 | PyMySQL | - | |
| 마이그레이션 | Alembic | 1.14.x | |
| 데이터베이스 | MySQL | 8.4 | Docker 컨테이너 |
| 검증·설정 | Pydantic v2, pydantic-settings | 2.x | |
| 인증 | PyJWT, bcrypt | - | 액세스 토큰 1개 |
| 엑셀 | openpyxl | 3.1.x | 근태, 업무일지 |
| 파일 저장소 | AWS S3 | - | boto3. 서버가 받아 업로드 |
| 로깅 | 표준 logging (JSON 포매터) | - | |
| 백엔드 테스트 | pytest, httpx | - | 서비스 단위 + API 테스트 |
| 백엔드 린트·포맷 | ruff, mypy | - | |
| 프론트엔드 | React + Vite + TypeScript | React 19, Vite 7, TS 5 | 단일 SPA |
| UI 라이브러리 | MUI (Material UI) | 7.x | 브이드림 브랜드 팔레트(민트·바이올렛) 기반 테마, 라이트·다크 |
| 라우팅 | React Router | 7.x | `/`, `/m/*`, `/admin/*`, `/system/*` |
| 서버 상태 | TanStack Query | 5.x | |
| 폼 | react-hook-form + zod | 7.x / 4.x | |
| HTTP | axios | 1.x | |
| 차트 | Recharts | 2.x | 업무 통계, 상담 점수 추이 |
| API 타입 | openapi-typescript | 7.x | 서버 OpenAPI → `src/api/schema.d.ts` |
| 프론트 테스트 | Vitest, Testing Library | - | 핵심 컴포넌트만 |
| 프론트 린트 | ESLint 9, Prettier 3 | - | |
| 컨테이너 | Docker, Docker Compose | Compose v2 | |
| 리버스 프록시·TLS | Caddy | 2.x | HTTPS 자동 발급, 정적 파일 서빙, `/api` 프록시 |
| 클라우드 | AWS EC2 (t3.small), S3, Route 53 또는 외부 도메인 | - | |
| CI/CD | GitHub Actions + GitHub Container Registry (GHCR) | - | PR마다 CI(린트, 타입, 테스트). main 머지 시 이미지 빌드·푸시 후 EC2 자동 배포 |
| 버전 관리 | Git, GitHub (GitHub Flow) | - | main 보호, feature 브랜치, PR 필수, squash merge |

---

## 2. 시스템 아키텍처

```mermaid
flowchart TB
  subgraph Browser["브라우저"]
    SPA[React SPA<br/>/ · /m · /admin · /system]
  end

  subgraph EC2["AWS EC2 1대 (Docker Compose)"]
    CADDY[Caddy<br/>HTTPS, 정적 파일, /api 프록시]
    API[FastAPI<br/>uvicorn]
    DB[(MySQL 8.4)]
  end

  S3[(AWS S3<br/>업로드 파일)]

  SPA -->|HTTPS| CADDY
  CADDY -->|정적 파일| SPA
  CADDY -->|/api| API
  API --> DB
  API -->|boto3| S3
  API -->|사전 서명 URL| SPA
```

| 원칙 | 내용 |
|---|---|
| 단일 API, 단일 SPA | 하나의 FastAPI와 하나의 React 앱. 역할별 차이는 라우트 가드와 인가 규칙으로 처리 |
| 배포 단위 1개 | `docker compose up -d` 한 번으로 전체 기동. Caddy가 빌드된 프론트 정적 파일을 서빙하고 `/api`를 FastAPI로 넘긴다 |
| 무상태 서버 | JWT. 파일은 S3. 서버 재시작에 영향 없음 |
| 배치 없음 | 스케줄러를 두지 않는다. 날짜에 따라 달라지는 상태(재직 상태, 결근, 공고 마감 예정일 경과)는 서비스 계층이 요청 시점에 계산한다. 데모 초기화는 시스템관리자 버튼으로만 |
| 스키마 원천 | Python 열거형과 Pydantic 스키마가 원천. OpenAPI JSON에서 프론트 타입 생성 |
| 머지가 곧 배포 | main에 머지되면 GitHub Actions가 이미지를 빌드해 GHCR에 올리고 EC2에서 `docker compose pull && up -d`를 실행한다. 사람이 서버에 들어가 배포하지 않는다 |

---

## 3. 저장소 구조

```
my-vdream/
├─ apps/
│  ├─ api/                      # FastAPI
│  │  ├─ app/
│  │  │  ├─ main.py             # 앱 생성, 라우터 등록, CORS, 예외 핸들러
│  │  │  ├─ core/               # config, security(JWT), deps(현재 사용자·역할), errors, responses
│  │  │  ├─ db/                 # engine, session, base, mixins
│  │  │  ├─ enums.py            # 모든 열거형 (원천)
│  │  │  ├─ models/             # SQLAlchemy 모델 (도메인별)
│  │  │  ├─ schemas/            # Pydantic 요청·응답
│  │  │  ├─ routers/            # 도메인별 APIRouter
│  │  │  ├─ services/           # 비즈니스 규칙
│  │  │  ├─ domain/             # 순수 함수: 날짜 파생 계산(employment_status, absent_days, posting_open), 쪽지 대상 규칙(messaging), 고용 인정 판정(recognition)
│  │  │  ├─ reports/            # 월간 장애인 고용 리포트 집계
│  │  │  ├─ excel/              # 근태, 업무일지, 고용 리포트 내보내기
│  │  │  └─ seed/               # 시드 데이터 생성과 데모 초기화 (SA 버튼이 호출)
│  │  ├─ alembic/
│  │  ├─ tests/
│  │  ├─ Dockerfile
│  │  └─ pyproject.toml
│  └─ web/                      # React SPA
│     ├─ src/
│     │  ├─ main.tsx
│     │  ├─ app/                # 라우터, 테마(theme/tokens.ts: 브이드림 팔레트, workerTheme·adminTheme), 인증 컨텍스트, 레이아웃
│     │  ├─ api/                # axios 인스턴스, 생성된 schema.d.ts, 도메인별 쿼리 훅
│     │  ├─ pages/
│     │  │  ├─ landing/         # 랜딩, 역할 체험 버튼
│     │  │  ├─ mobile/          # 근로자 화면 (/m)
│     │  │  ├─ admin/           # CM·VM 화면 (/admin). reports/ 아래 고용 리포트 화면과 인쇄 화면
│     │  │  ├─ messages/        # 쪽지함·쪽지 쓰기 (모바일·관리자 레이아웃 공용 컴포넌트)
│     │  │  └─ system/          # SA 화면 (/system)
│     │  ├─ components/         # PhoneFrame, 큰 버튼, 상태 뱃지, 알림 배지, 역할 전환 바
│     │  └─ lib/                # 날짜(Asia/Seoul), 상태 레이블, 포맷
│     ├─ Dockerfile             # 빌드 후 정적 파일을 Caddy 볼륨으로
│     └─ package.json
├─ deploy/
│  ├─ Caddyfile
│  ├─ docker-compose.yml        # caddy, api, web-build, mysql
│  ├─ docker-compose.dev.yml    # 개발: mysql만 (api, web은 호스트에서 실행)
│  ├─ deploy.sh                 # EC2에서 docker compose pull && up -d (CD가 SSH로 호출)
│  └─ ec2-bootstrap.sh          # 새 EC2에 docker 설치, 저장소 clone, .env 자리
├─ scripts/
│  ├─ export-openapi.py         # OpenAPI JSON 내보내기
│  └─ generate-types.sh         # openapi-typescript 실행
├─ docs/
├─ .github/
│  ├─ workflows/
│  │  ├─ ci.yml                 # PR·push: api 린트·타입·테스트, web 린트·타입·빌드, 타입 생성물 검사
│  │  └─ deploy.yml             # main push: 이미지 빌드 → GHCR 푸시 → EC2 SSH 배포
│  ├─ dependabot.yml            # pip, npm, actions 주간 업데이트 PR
│  └─ PULL_REQUEST_TEMPLATE.md
├─ .env.example
└─ README.md                    # 소개, 아키텍처, 데모 계정, 실행 방법, 확장 계획
```

모노레포 도구(Turborepo, pnpm 워크스페이스)는 쓰지 않는다. `apps/api`와 `apps/web`은 각자의 패키지 매니저(uv, npm)로 독립 관리한다.

---

## 4. 백엔드 (API 서버)

### 4.1 라우터 구성

| 라우터 | 책임 | 관련 요구기능 |
|---|---|---|
| auth | 로그인, 데모 로그인, 내 정보, 비밀번호 변경 | AUTH |
| users | 계정 CRUD(SA) | SYSM |
| companies | 기업 CRUD, 담당 매니저, 매니저용 기업 목록 | SYSM |
| system | 시스템 대시보드, 데모 초기화 | SYSM |
| announcements | 공지 CRUD, 공개 범위 필터 | ANNC |
| notifications | 알림 목록, 읽음, 미읽음 개수 | NOTI |
| files | 업로드(multipart), 다운로드 URL | RESM, WLOG |
| resumes | 프로필, 학력, 경력, 구직 등록 | RESM, REGI |
| job_postings | 공고 CRUD, 승인, 반려, 게시, 마감 | JOBP |
| applications | 지원, 심사, 면접, 합격, 출근일, 취소 | APPL |
| employments | 재직 목록, 계약 조회·수정, 재직 이력 | EMPL |
| resignations | 퇴사 신청, 승인, 반려, 철회, 통보 조회 | RESG |
| attendance | 출퇴근, 사유, 정정, 조회, 집계, 엑셀 | ATTD |
| leaves | 연차 부여, 휴가 신청, 승인, 취소, 잔여 | LEAV |
| tasks | 업무 배정, 상태 전이, 목록, 상세 | TASK |
| work_logs | 작성, 제출, 확인, 보완, 파일, 미제출, 통계, 엑셀 | WLOG |
| counseling | 상담보고서 CRUD, 근로자별 이력 | CNSL |
| messages | 수신 대상 목록, 발송(단체 포함), 받은·보낸 함, 상세·읽음, 답장, 삭제 | MESG |
| reports | 월간 장애인 고용 리포트 데이터 경고, JSON, 엑셀 | EMRP |
| me | 내 미읽음 개수(알림 + 쪽지) | NOTI-005, MESG-010 |
| dashboard | 역할별 대시보드 | DASH |

### 4.2 레이어 규칙

| 레이어 | 역할 | 규칙 |
|---|---|---|
| Router | 요청 수신, 스키마 검증, 인가 의존성 | 비즈니스 로직 금지 |
| Service | 비즈니스 규칙, 트랜잭션, 알림 생성 | `Session`을 주입받아 SQLAlchemy 직접 사용 |
| Schema | Pydantic 요청·응답 | `extra="forbid"`, camelCase alias, `from_attributes=True` |

레이어를 더 나누지 않는다. 2주 범위에서는 Router → Service → 모델 세 단계로 충분하다.

### 4.3 API 규약

| 항목 | 규칙 |
|---|---|
| 기본 경로 | `/api/v1` |
| 리소스 명명 | 복수 명사, kebab-case. 상태 전이는 POST + 동사 하위 경로 (`/approve`, `/check-in`, `/submit`, `/confirm`, `/return`) |
| 성공 응답 | `{ "data": ... }`. 목록은 `{ "data": [...], "meta": { "page", "size", "total" } }` |
| 오류 응답 | `{ "error": { "code": "WORK_LOG_ALREADY_CONFIRMED", "message": "한국어 메시지" } }`. `AppError(code, status, message)`를 전역 핸들러가 변환 |
| 페이지네이션 | `?page=1&size=20` (최대 100) |
| 날짜·시간 | ISO 8601. 일시는 UTC(`Z`), 날짜는 `YYYY-MM-DD`. 클라이언트가 Asia/Seoul로 표시 |
| 필드 명명 | JSON은 camelCase (`alias_generator=to_camel`) |
| 열거형 | `app/enums.py`의 문자열 값 그대로 |
| 문서 | Swagger UI `/api/docs`, OpenAPI JSON `/api/openapi.json`. 운영에서도 노출한다 (포트폴리오에서 API 문서를 보여주는 용도) |

### 4.4 인증

| 항목 | 규칙 |
|---|---|
| 방식 | JWT HS256 액세스 토큰 1개, 유효 24시간. 리프레시 토큰 없음. 만료 시 재로그인(데모 로그인은 버튼 한 번) |
| 저장 | 프론트 `localStorage`. axios 인터셉터가 `Authorization: Bearer` 헤더 부착, 401 시 토큰 삭제 후 랜딩으로 이동 |
| 비밀번호 | bcrypt cost 10 |
| 데모 로그인 | `POST /auth/demo-login { role }`. `is_demo = 1`이고 해당 역할인 계정 중 첫 번째로 토큰 발급. 랜딩 페이지와 역할 전환 바가 사용 |
| 의존성 | `Depends(get_current_user)` → `CurrentUser(id, role, company_id, is_demo)` |

### 4.5 인가

| 계층 | 규칙 |
|---|---|
| 역할 | `Depends(require_roles(...))` |
| 범위 | CM은 `company_id` 일치 검사. VM은 전체. WK는 본인(`worker_id = current_user.id` 또는 본인 재직) |
| 편집 권한 | 근태 정정, 휴가 승인, 업무 배정, 업무일지 확인은 CM만. 공고 승인, 퇴사 승인, 상담보고서는 VM만 |
| 데모 계정 보호 | 비밀번호 변경·비활성화·삭제 요청에서 `is_demo`면 403 `DEMO_ACCOUNT_PROTECTED` |

### 4.6 상태 전이

모듈별 `ALLOWED_TRANSITIONS: dict[Status, set[Status]]`로 정의하고 서비스가 전이 전에 검사한다. 공고, 지원, 업무, 업무일지, 휴가, 퇴사 여섯 개.

### 4.7 파일 업로드와 다운로드

| 항목 | 규칙 |
|---|---|
| 업로드 | `POST /files` multipart. 서버가 MIME과 크기를 검사하고 boto3로 S3에 `put_object`. `files` 행 생성 후 id 반환 |
| 키 | `{purpose}/{yyyy}/{mm}/{uuid}.{ext}` |
| 제한 | 증명사진 JPG·PNG 5MB. 업무일지 산출물 PDF·JPG·PNG·DOCX·XLSX·ZIP 10MB |
| 다운로드 | `GET /files/{id}/url`에서 권한 검사 후 10분 사전 서명 URL 반환 |
| 개발 환경 | `STORAGE_BACKEND=local`이면 `apps/api/uploads/`에 저장하고 `/api/v1/files/{id}/content`로 서빙. S3 없이 개발 가능 |
| 데모 초기화 | S3 객체는 지우지 않는다 (시드 파일 재사용). `files` 테이블만 재생성 |

### 4.8 알림

`NotificationService.notify(user_ids, type, title, body, link_path)`가 행을 만든다. `notify_company_managers(company_id, ...)`가 담당 매니저 라우팅을 처리한다. 푸시 없음. 프론트가 10초마다 `GET /me/unread-counts`를 호출해 알림과 쪽지 미읽음 수를 함께 받는다 (TanStack Query `refetchInterval: 10000`, 창이 비활성이면 중단).

### 4.9 날짜 파생 상태 계산 (배치 대체)

매일 실행되는 배치는 범위 밖이므로, v1.0에서 배치가 갱신하던 값을 요청 시점에 계산한다. 모두 `app/domain/`의 순수 함수로 두고 단위 테스트한다.

| 값 | 계산 | 사용처 |
|---|---|---|
| 재직 상태 | `employment_status(e, today)`: `start_date > today` → PENDING, `end_date is not None and end_date < today` → RESIGNED, 그 외 ACTIVE | 재직 목록·상세 응답, 근태·업무·업무일지 쓰기 권한 검사, 지원 가능 여부 |
| 결근 | `absent_days(employment, contract, records, approved_leaves, from, to)`: 기간 안의 날짜 중 재직 기간에 속하고, 요일이 계약 `work_days`에 있고, `today` 이전이고, 근태 행도 승인 휴가도 없는 날 | 근태 월별 조회·집계·엑셀, 대시보드 |
| 공고 지원 가능 | `posting_open(p, today)`: `status == PUBLISHED and (deadline_date is None or deadline_date >= today)` | 지원 API, 근로자 공고 목록의 "마감 예정일 경과" 표시 |
| 업무 기한 초과 | `due_date < today and status in (ASSIGNED, IN_PROGRESS)` | 업무 목록, 대시보드 |

`today`는 항상 Asia/Seoul 기준 날짜(`today_kst()`)를 인자로 받아 테스트에서 고정할 수 있게 한다.

### 4.9.1 데모 초기화

`POST /system/demo-reset` (SA). 모든 테이블 TRUNCATE 후 `app/seed/`가 실행 시점 기준 상대 날짜로 최근 3개월 데이터를 만든다. 자동 실행은 없다. 버튼은 확인 대화상자를 거치고 완료 후 처리 건수를 보여준다.

### 4.10 엑셀

openpyxl `write_only=True`. 근태(일별 + 월 집계 시트), 업무일지(항목별 + 월 통계 시트), 월간 장애인 고용 리포트(4.13). `StreamingResponse`, 파일명 `{종류}_{기업명}_{YYYYMM}.xlsx` RFC 5987 인코딩.

### 4.11 시드 데이터

`app/seed/`가 결정적(deterministic) 데이터를 만든다. 요구기능정의서 DEMO-006 구성. 날짜는 `today`를 기준으로 상대 계산해 언제 초기화해도 "최근 3개월"이 유지된다. 고용 리포트 판정이 골고루 보이도록 중증 주 40시간(2배수), 경증 주 40시간(1배수), 중증 주 12시간 월 16일 이상 근무(1배수), 경증 주 12시간(제외 가능), 지난달 중순 입사자(확인 필요)를 포함하고, 일부 날짜에 퇴근 미기록과 업무일지 미제출을 넣어 데이터 경고도 보이게 한다. 쪽지는 역할 간 왕복 대화 몇 건과 매니저 단체 발송 1건. 데모 계정 아이디는 `demo.worker`, `demo.company`, `demo.manager`, `demo.admin`이며 비밀번호는 환경 변수 `DEMO_PASSWORD`. README에도 적는다.

### 4.12 쪽지

| 항목 | 규칙 |
|---|---|
| 규칙 함수 | `app/domain/messaging.py`의 `allowed_recipient_ids(sender, today) -> set[int] \| ALL`. 요구기능정의서 부록 A.13을 그대로 코드화한다. 근로자: 재직 상태(계산)가 PENDING·ACTIVE인 재직의 `company_id` → 그 기업의 활성 CM 전원 + `companies.manager_id`. 기업 담당자: 자기 `company_id`의 PENDING·ACTIVE 재직 근로자 + `companies.manager_id`. 매니저: 전체. 그 외: 빈 집합 |
| 대상 목록 API | `GET /messages/recipients?q=` → `allowed_recipient_ids` 결과를 이름·역할·기업명과 함께 반환. 매니저는 `q` 검색 필수(최대 20건). 근로자·기업 담당자는 전체 목록(수십 명 이하)을 그룹(기업 담당자 / 담당 매니저 / 근로자)으로 반환. 담당 매니저가 없으면 `managerMissing: true` |
| 발송 API | `POST /messages { recipientIds?, audience, audienceCompanyId?, title, body, parentMessageId? }`. 서비스가 같은 `allowed_recipient_ids`로 수신자 전부를 검사하고 하나라도 벗어나면 403 `MESSAGE_RECIPIENT_NOT_ALLOWED`. 단체 audience는 VM만, 서버가 수신자를 확장(fan-out)해 `message_recipients`를 일괄 INSERT |
| 함 조회 | `GET /messages/inbox?unreadOnly=&page=`, `GET /messages/sent?page=`. 보낸 함은 `recipient_count`와 `COUNT(read_at)`로 "n명 중 m명 읽음" |
| 상세·읽음 | `GET /messages/{id}`: 수신자면 `read_at`을 채운다(처음 열 때만). 발신자면 수신자별 읽음 시각 목록 포함. 답장 가능 여부 `canReply`를 같은 규칙 함수로 계산해 내려준다 |
| 삭제 | `DELETE /messages/{id}?box=inbox\|sent` → 해당 쪽의 삭제 시각만 기록 |
| 미읽음 수 | `GET /me/unread-counts` → `{ notifications, messages }`. 프론트는 이 요청 하나를 10초마다 호출해 알림 배지와 봉투 배지를 함께 갱신한다 |
| 테스트 | 규칙 함수 단위 테스트: 역할 4종 × 재직 상태 3종 × 담당 매니저 있음/없음/다른 기업. API 테스트: 근로자가 다른 기업 매니저 id로 발송 시 403 |

### 4.13 월간 장애인 고용 리포트

| 항목 | 규칙 |
|---|---|
| 위치 | `app/reports/employment_report.py`(집계), `app/domain/recognition.py`(판정·환산 순수 함수), `app/excel/employment_report.py`(엑셀) |
| API | `GET /reports/employment/warnings?from=YYYY-MM&to=YYYY-MM` (데이터 경고), `GET /reports/employment?from=&to=` (JSON 전체), `GET /reports/employment.xlsx?from=&to=` (엑셀). CM 전용, `company_id`는 토큰에서만 가져온다 |
| 기간 검증 | `from ≤ to`, 최대 12개월, `to ≤ 이번 달`. 이번 달은 `today`까지만 집계하고 `inProgress: true` |
| 대상 | 각 월 `[월초, min(월말, today)]`와 재직 기간 `[start_date, end_date]`가 겹치는 자기 기업 재직 기록. 퇴사자 포함 |
| 쿼리 | 기간 전체를 한 번에 읽는다: 재직·계약·프로필(1회), 근태(기간 범위 1회), 승인 휴가(1회), 업무일지와 항목(1회), 산출물 수(GROUP BY 1회), 완료 업무(1회). 파이썬에서 월·근로자별로 묶어 계산. 12개월 × 수십 명 규모에서 1초 이내 |

계산식 (`app/domain/recognition.py`, 모두 `today`를 인자로 받는 순수 함수):

| 값 | 식 |
|---|---|
| 월 소정근로시간 `H` | `weekly_work_hours × 365 / 7 / 12` (소수 첫째 자리 반올림) |
| 근무일 수 | 그 달 중 재직 기간 안이고 `today` 이하이며 요일이 계약 `work_days`에 있는 날 수 |
| 출근일 수 / 출근율 | 근태 행에 `check_in_at`이 있는 날 수 / 출근일 수 ÷ (근무일 수 − 승인 휴가 일수) |
| 실근로시간 | 출근·퇴근이 모두 있는 날마다 `max(0, 퇴근 − 출근 − 계약 break_minutes)` 합계. 퇴근 미기록일은 제외하고 일수를 따로 센다 |
| 유급 근로일수(추정) | 출근일 수 + 승인된 연차(ANNUAL) 일수. 반차 날은 출근일로 이미 셈 |
| 업무일지 제출률 | `first_submitted_at`이 있는 일지 수 ÷ 출근일 수 |
| 인정 판정 | 장애정도 NULL → NEEDS_REVIEW. 경증: `H ≥ 60` → SINGLE, 아니면 EXCLUDED. 중증: `H ≥ 60` → DOUBLE, `H < 60`이고 유급 근로일수 ≥ 16 → SINGLE, 아니면 EXCLUDED. 단, 월 중 입사·퇴사로 재직일이 그 달 일부이고 유급 근로일수 < 16이면 NEEDS_REVIEW로 덮어쓴다 |
| 인정 인원 추정 | 월별 Σ(DOUBLE → 2, SINGLE → 1, 그 외 0) |
| 시급 환산 | HOURLY: `salary_amount`. MONTHLY: `salary_amount ÷ ((W + 주휴) × 365 / 7 / 12)`, `W`는 주 소정근로시간, 주휴는 `W ≥ 15`이면 `W / 5`, 아니면 0 |
| 최저임금 참고 | 시급 환산 ≥ `MINIMUM_WAGE_HOURLY` → 충족, 미만 → 미달, 계약 급여 누락 → 확인 필요 |

| 항목 | 규칙 |
|---|---|
| 엑셀 | openpyxl. 시트 `요약`(월 × 지표), `근로자별 월간`(근로자 × 월 1행, 부록 A.14의 1~5 항목을 열로), `일자별 근로 기록`(근로자 × 날짜 1행). 첫 행에 기업명·기간·생성 일시, 마지막 행에 참고용 안내 문구. 헤더 고정, 열 너비 지정 |
| 인쇄 화면 | 프론트 `/admin/reports/employment/print?from=&to=`가 같은 JSON으로 렌더링. `@page { size: A4 portrait; margin: 15mm }`, 근로자 × 월마다 `break-before: page`, 머리글·바닥글은 각 페이지 블록 안에 직접 배치. 인쇄 화면은 브랜드 색을 줄이고 흑백 인쇄에서도 읽히게 표 테두리와 굵기로 구분. 상단 "인쇄 / PDF로 저장" 버튼은 `window.print()`, 인쇄 시 숨김 |
| 안내 문구 | "이 문서는 my-vdream의 근태·업무일지 기록으로 생성한 참고 자료입니다. 고용 인정 여부와 인원은 한국장애인고용공단 심사로 확정되며, 유급 근로일수와 임금은 급여대장으로 확인해야 합니다." |
| 테스트 | 판정 함수: 경증 59.9/60시간, 중증 60시간 이상·미만 × 유급 15/16일, 월 중 입사, 장애정보 없음. 환산 함수: 주 40시간 월급(209시간), 주 12시간(주휴 없음). 리포트 API: 다른 기업 CM 403, 13개월 요청 400 |

---

## 5. 데이터베이스

### 5.1 MySQL

| 항목 | 값 |
|---|---|
| 버전 | 8.4 |
| 문자셋 | `utf8mb4`, `utf8mb4_0900_ai_ci` |
| 시간대 | 서버 UTC. 애플리케이션이 Asia/Seoul 변환 (`zoneinfo`) |
| 실행 | EC2 안 Docker 컨테이너, 볼륨 `mysql_data`. RDS는 쓰지 않는다 |

### 5.2 SQLAlchemy 규칙

- `DeclarativeBase` 하나, `Mapped[]` + `mapped_column`. 공통 컬럼은 `PKMixin`, `TimestampMixin`.
- 열거형은 `class XxxStatus(str, enum.Enum)` + `sqlalchemy.Enum(..., native_enum=True, values_callable=lambda e: [m.value for m in e])`.
- 세션은 요청당 하나(`Depends(get_db)`), 서비스가 `db.commit()`으로 경계를 잡는다.
- 소프트 삭제는 각 쿼리에 `deleted_at.is_(None)` 조건을 명시한다 (자동 필터는 두지 않는다. 테이블이 셋뿐).

### 5.3 마이그레이션과 시드

| 환경 | 명령 |
|---|---|
| 개발 | `uv run alembic revision --autogenerate -m "..."` → 검토 → `uv run alembic upgrade head` |
| 운영 | api 컨테이너 엔트리포인트가 `alembic upgrade head` 실행 |
| 시드 | `uv run python -m app.seed` 또는 SA 화면의 데모 초기화 버튼 |

### 5.4 시간대 처리

| 상황 | 규칙 |
|---|---|
| 저장 | UTC naive datetime |
| 업무 날짜 | DATE는 Asia/Seoul 날짜. `today_kst()` 헬퍼 |
| 근태 판정 | 계약 `work_start_time`과 `work_date`를 Asia/Seoul로 결합해 UTC로 변환 후 비교 |
| 근무일 | `date.weekday()`가 계약 `work_days`에 포함되는지 |
| 프론트 | `date-fns` + `date-fns-tz`, Asia/Seoul 고정 |

---

## 6. 프론트엔드 (단일 React 앱)

### 6.1 구성

| 항목 | 내용 |
|---|---|
| 경로 | `/` 랜딩, `/m/*` 근로자, `/admin/*` CM·VM, `/system/*` SA. 로그인 후 역할에 따라 이동 |
| 레이아웃 | `/m`은 `MobileLayout`(하단 탭 5개) + 데스크톱에서 `PhoneFrame` 래핑. `/admin`, `/system`은 `AdminLayout`(좌측 메뉴, 상단 알림 배지, 역할 전환 바) |
| 라우트 가드 | `RequireRole` 컴포넌트. 미로그인 → `/`, 역할 불일치 → 자기 홈 |
| 서버 상태 | TanStack Query. 쿼리 키 `[도메인, 식별자, 필터]`. 미읽음 개수는 `refetchInterval: 10000`, `refetchIntervalInBackground: false` |
| 폼 | react-hook-form + zod |
| HTTP | axios 인스턴스, Bearer 헤더, 401 처리 |
| 타입 | `openapi-typescript`로 생성한 `schema.d.ts`에서 `components["schemas"]["..."]` 사용 |
| 표 | MUI DataGrid Community, 서버 페이지네이션 |
| 차트 | Recharts. 업무별 소요 시간 막대, 상담 점수 추이 선 |
| 테마 | 브이드림 브랜드 팔레트(6.2.1) 기반 `workerTheme`(민트 주색), `adminTheme`(바이올렛 주색). `useMediaQuery('(prefers-color-scheme: dark)')` 기본, 설정에서 고정, `localStorage` |

### 6.2 디자인과 접근성

| 항목 | 규칙 |
|---|---|
| 글자 크기 | 모바일 화면 본문 18px, 제목 24px. 관리자 화면 본문 16px, 표 15px |
| 대비 | 4.5:1 이상. 브랜드 민트 `#2EB6AA` 위 흰 글자는 2.5:1로 미달이므로 라이트모드 버튼 배경은 딥민트 `#0B7A71`, 민트 배경에는 진한 글자. 상세는 6.2.1 |
| 포커스 | 2px 가시 포커스 링 |
| 레이블 | 아이콘 버튼에 `aria-label`, 입력에 `label`, 상태 변경 결과는 `role="status"` 영역에 텍스트 |
| 색상 외 구분 | 상태 뱃지는 텍스트 포함. 기한 초과는 "기한 초과" 텍스트 |
| 토스트 | 자동 닫힘 스낵바를 모바일 화면에서 쓰지 않는다. 결과는 화면 내 텍스트 |
| 반응형 | 관리자 화면은 1280px 기준, 1024px까지 표 가로 스크롤. 모바일 화면은 390px 기준 |

### 6.2.1 브랜드 컬러 체계 (브이드림 사이트 조사 기반)

2026-11-22에 브이드림 세 사이트를 브라우저에서 직접 열어 CSS 변수와 버튼·배경의 계산된 색상 값을 수집했다. 이 프로젝트는 그 색을 그대로 쓰되, 로고와 워드마크는 사용하지 않는다 (브이드림을 사칭하는 인상을 주지 않기 위해 "my-vdream" 텍스트 워드마크와 자체 아이콘만 쓴다).

**조사 결과**

| 사이트 | 역할 | 실제 사용 색 (hex) | 근거 |
|---|---|---|---|
| vdream.co.kr (본사) | 기업·구직자 대상 소개 | 브랜드 바이올렛 `#584C9D` (`--brand`, violet-50), 호버 `#433594` (violet-70), 액센트 민트 `#5DBEB6` (`--accent`, mint-50), CTA 딥민트 `#0B7A71`, 다크 배경 `#0C0918`, 다크 표면 `#150F29`·`#1E1638` | `:root` 토큰 164개. violet·mint·gray 각 11단계와 error `#CE3426`·success `#36B37E`·info `#0B78CB`·pending `#FFAB00` 상태색 |
| v-match.co.kr (브이매치) | 채용 매칭 플랫폼 | 브랜드 민트 `#2EB6AA` (`--brand-primary`), 보조 `#00AFEE`, `#6464F5`, `#935DE9`, 오류 `#E6533E`, 흰 배경, 본문 텍스트 `#151719` | `:root` 토큰 57개. 화면에서 유일하게 쓰인 유채색이 `#2EB6AA` |
| v-work.co.kr (브이워크) | 재택근무 인사관리 플랫폼 | 민트 `#23CDB7` (로그인 버튼, 좌측 그라데이션 패널), 흰 배경 | 로그인 화면 전체에서 유채색은 `#23CDB7` 하나 |

세 사이트를 관통하는 고유 색은 **민트(틸) 계열**이고, 본사 사이트는 여기에 **바이올렛**을 주색으로 더한다. 이 프로젝트가 벤치마킹하는 대상은 브이워크(재택근무 관리)이므로 근로자 화면은 민트를 주색으로, 관리자 화면은 본사처럼 바이올렛 주색 + 민트 액센트로 구성한다.

**팔레트 토큰** (`apps/web/src/app/theme/tokens.ts`. 값은 브이드림 토큰을 그대로 가져오고 변수명만 이 프로젝트 기준)

| 토큰 | 값 | 출처 | 용도 |
|---|---|---|---|
| `mint.500` | `#2EB6AA` | 브이매치 brand-primary | 브랜드 대표색. 아이콘, 테두리, 선택 상태, 칩 배경(진한 글자), 다크모드 주 버튼 |
| `mint.400` | `#5DBEB6` | 본사 mint-50 | 그라데이션, 장식 |
| `mint.300` | `#72C9C1` | 본사 mint-40 | 다크모드 링크·강조 텍스트 |
| `mint.gradientEnd` | `#23CDB7` | 브이워크 | 대비 2.0:1로 텍스트 배경에 부적합. 그라데이션 시작색으로만 |
| `mint.700` | `#0B7A71` | 본사 CTA | 라이트모드 주 버튼 배경(흰 글자), 링크 텍스트 |
| `mint.800` | `#0E877D` | 본사 mint-95 | 주 버튼 호버 |
| `mint.50` | `#D7F4F2` | 본사 mint-5 | 민트 칩·배너 배경 |
| `violet.500` | `#584C9D` | 본사 brand | 관리자 화면 주 버튼, 활성 메뉴, 앱바 |
| `violet.700` | `#433594` | 본사 brand-hover | 관리자 주 버튼 호버 |
| `violet.300` | `#8377C2` | 본사 violet-30 | 다크모드 보조 강조 |
| `violet.200` | `#9C93D1` | 본사 violet-20 | 다크모드 링크·활성 메뉴 텍스트 |
| `violet.50` | `#D6D1F0` | 본사 violet-5 | 바이올렛 칩·배너 배경 |
| `navy.950` | `#0C0918` | 본사 다크 배경 | 랜딩 히어로, 다크모드 배경 |
| `navy.900` | `#150F29` | 본사 다크 표면 | 다크모드 카드 |
| `navy.800` | `#1E1638` | 본사 다크 표면 | 다크모드 앱바·입력 배경 |
| `gray.*` | `#030712` ~ `#F9FAFB` | 본사 gray 11단계 (Tailwind gray와 동일) | 텍스트, 테두리, 표면 |
| `error` | 배경 `#FAEBE9`, 텍스트·아이콘 `#90241B`, 버튼 `#CE3426` | 본사 error-5·70·50 | 오류, 반려, 기한 초과 |
| `success` | 배경 `#EBF7F2`, 텍스트 `#267D58`, 아이콘 `#36B37E` | 본사 success-5·70·50 | 확인됨, 완료, 승인 |
| `warning` | 배경 `#FFF7E6`, 텍스트 `#805600`, 아이콘 `#FFAB00` | 본사 pending-5·80·50 | 승인 대기, 보완 요청, 제출됨 |
| `info` | 배경 `#E6F2FB`(근사), 텍스트 `#085691`, 아이콘 `#0B78CB` | 본사 info-70·50 | 안내, 진행중 |

**MUI 테마 매핑**

| MUI 팔레트 | 라이트 | 다크 | 비고 |
|---|---|---|---|
| `primary` (근로자 `/m`) | main `#0B7A71`, light `#2EB6AA`, dark `#0E877D`, contrastText `#FFFFFF` | main `#2EB6AA`, contrastText `#0C0918` | 라이트에서 `#2EB6AA`에 흰 글자는 2.5:1로 AA 미달이라 버튼 배경은 `#0B7A71`(5.2:1) |
| `primary` (관리자 `/admin`, `/system`) | main `#584C9D`, dark `#433594`, contrastText `#FFFFFF` | main `#9C93D1`, contrastText `#0C0918` | `#584C9D` + 흰 글자 7.15:1 (AAA) |
| `secondary` | 근로자: `#584C9D` / 관리자: `#0B7A71` | 근로자: `#9C93D1` / 관리자: `#2EB6AA` | 서로의 주색을 보조색으로 교차 사용 |
| `background.default` | `#FFFFFF` | `#0C0918` | |
| `background.paper` | `#F6F5FB` (본사 `--ui-bg-alt`) | `#150F29` | |
| `text.primary` | `#111827` | `#F9FAFB` | 본사 gray-90 / gray-5 |
| `text.secondary` | `#4B5563` | `#9CA3AF` | gray-60 / gray-40 (라이트 7.6:1, 다크 7.0:1) |
| `divider` | `#E5E7EB` | `#374151` | |
| `error` / `success` / `warning` / `info` | 위 상태색 | 아이콘색을 main으로, 다크 배경에서는 텍스트색을 밝게 | |

테마는 역할 경로에 따라 두 개(`workerTheme`, `adminTheme`)를 만들고 각각 라이트·다크 모드를 가진다. 네 조합 모두 `tokens.ts` 하나에서 생성한다.

**사용 규칙**

| 규칙 | 내용 |
|---|---|
| 민트는 "브이드림의 색" | 랜딩 히어로 제목 강조, 역할 체험 버튼의 근로자 버튼, 모바일 하단 탭 활성 아이콘, 출근·완료·제출 성공 피드백, 휴대폰 프레임 바깥 배경 그라데이션(`#23CDB7` → `#2EB6AA` → `#0B7A71`, 브이워크 로그인 패널과 같은 방향)에 쓴다 |
| 바이올렛은 "운영·관리의 색" | 관리자 앱바, 좌측 메뉴 활성 항목, 관리자 주 버튼, 브이드림 매니저 역할 뱃지, 랜딩의 관리자 체험 버튼에 쓴다 |
| 텍스트 대비 | 유채색 배경 위 텍스트는 반드시 4.5:1 이상. 민트 배경에는 진한 글자(`#111827`, 7.1:1), 바이올렛 배경에는 흰 글자(7.2:1). `#2EB6AA`, `#23CDB7`, `#5DBEB6`, `#36B37E`, `#FFAB00` 위에 흰 글자 금지 |
| 상태 칩 | 연한 배경 + 진한 텍스트 조합만 사용 (예: 승인 대기 `#FFF7E6` 위 `#805600`). 텍스트 레이블 필수 (색상 외 구분, ACCS-007) |
| 랜딩 | 히어로는 `#0C0918` 배경에 민트·바이올렛 그라데이션 글로우(본사 히어로와 같은 분위기), 본문은 흰 배경. 아키텍처 그림은 민트(클라이언트)·바이올렛(서버)·회색(외부) 세 색만 |
| 차트 | 계열색은 민트 `#2EB6AA`, 바이올렛 `#584C9D`, 그 다음 `#0B78CB`, `#FFAB00` 순. 상담 점수 추이 선은 민트 |
| 그라데이션 | 큰 면(랜딩 히어로, 프레임 배경, 로그인 패널)에만. 버튼·칩에는 단색 |
| 금지 | 브이드림·브이매치·브이워크 로고, 하트 모양 V 심볼, "브이드림" 워드마크 이미지 사용 금지. 색만 가져온다 |


### 6.3 화면 구성 (`/admin`)

| 메뉴 | CM | VM |
|---|---|---|
| 대시보드 | 기업 대시보드 | 브이드림 대시보드 (담당/전체 전환) |
| 기업 | - | 기업 목록 |
| 근로자 | 재직 근로자 목록, 상세 | 구직자 목록, 재직 근로자 목록, 상세(이력서 대리 작성) |
| 채용 | 공고 관리, 지원자 관리 | 공고 작성(즉시 게시), 공고 승인, 지원자 관리 |
| 근로계약 | 조회·수정 | 조회·수정 |
| 퇴사 | 퇴사 통보 조회 | 퇴사 신청 처리 |
| 근태 | 조회, 정정, 엑셀 | 조회, 엑셀 |
| 휴가 | 연차 설정, 승인, 조회 | 조회 |
| 업무 | 배정, 수정, 취소, 재오픈, 목록, 상세 | 목록, 상세 |
| 업무일지 | 확인, 보완 요청, 미제출 현황, 통계, 엑셀 | 조회, 미제출 현황, 통계, 엑셀 |
| 상담 | - | 상담보고서 작성, 조회 |
| 고용 리포트 | 월간 장애인 고용 리포트: 기간 선택, 데이터 경고, 미리보기, 엑셀, 인쇄·PDF | - |
| 쪽지 | 받은·보낸 쪽지함, 쪽지 쓰기(자기 기업 근로자·담당 매니저만) | 받은·보낸 쪽지함, 쪽지 쓰기(개별 검색, 단체 발송) |
| 공지·알림·내 정보 | 공통 | 공통. 상단에 알림 배지와 봉투(쪽지) 배지 |

### 6.4 화면 구성 (`/system`)

| 메뉴 | 내용 |
|---|---|
| 대시보드 | 카운트, 데모 초기화 버튼(확인 대화상자) |
| 기업 관리 | 목록, 등록, 수정, 담당 매니저 지정, 비활성화 |
| 계정 관리 | 역할별 목록, 생성, 수정, 비활성화, 비밀번호 초기화 |
| 공지사항 | 작성, 수정, 삭제 |

---

## 7. 근로자 모바일 화면 (`/m`)

### 7.1 브라우저 크기를 모바일로 강제할 수 있는가 (조사 결과)

**결론: 이미 열려 있는 탭의 크기는 스크립트로 바꿀 수 없다.** 이력서 링크를 클릭해 열린 탭은 그 사람의 브라우저 창 크기 그대로다.

| 방법 | 가능 여부 | 근거와 제약 |
|---|---|---|
| `window.resizeTo()` / `resizeBy()`로 현재 탭 크기 변경 | 불가 | 브라우저는 `window.open()`으로 스크립트가 직접 만든 창만 크기를 바꿀 수 있게 하고, 탭이 여러 개인 창은 바꿀 수 없다 (MDN, Firefox 7 이후 모든 주요 브라우저 공통). 이력서에서 열린 탭은 둘 다 해당하지 않는다 |
| `window.open(url, '_blank', 'width=390,height=844')` 팝업 | 조건부 가능 | 사용자가 버튼을 클릭한 직후에 호출하면 Chrome, Edge, Safari는 지정 크기의 팝업 창을 연다. Firefox는 팝업으로 열되 수정자 키를 누른 클릭 등 일부 상황에서 일반 창으로 열리는 사례가 보고되어 있다. 팝업 차단기가 켜져 있으면 열리지 않는다. 모바일 브라우저는 크기를 무시한다 |
| `<meta name="viewport">` | 무관 | 모바일 기기에서 렌더링 배율만 결정. 데스크톱 창 크기에 영향 없음 |
| CSS로 화면 안에 모바일 크기 영역을 그리기 | 항상 가능 | 창 크기와 무관하게 390px 폭 컨테이너 안에 모바일 레이아웃을 렌더링. 가장 확실하다 |

따라서 **기본 방식은 CSS 휴대폰 프레임**이고, **팝업은 보조 버튼**으로 둔다.

출처: [MDN Window.resizeTo()](https://developer.mozilla.org/docs/Web/API/Window/resizeTo), [MDN Window.resizeBy()](https://developer.mozilla.org/docs/Web/API/Window/resizeBy), [window.open 기능 문자열의 브라우저별 해석 (커뮤니티 정리)](https://arai-a.github.io/window-open-features), [Firefox 팝업 동작 관련 버그 보고](https://bugzilla.mozilla.org/show_bug.cgi?id=2042925)

### 7.2 휴대폰 프레임 구현

| 항목 | 규칙 |
|---|---|
| 조건 | `useMediaQuery('(min-width: 600px)')`가 참이면 `PhoneFrame`으로 감싼다. 거짓(실제 모바일 기기)이면 감싸지 않고 전체 화면 |
| 크기 | 내부 뷰포트 390×844 (iPhone 14 기준). 바깥에 둥근 모서리 테두리, 상단 노치 모양, 그림자. 화면 높이가 900px보다 작으면 `transform: scale()`로 비율 유지하며 축소 |
| 내부 스크롤 | 프레임 내부 `overflow-y: auto`. 하단 탭은 프레임 안에 고정 |
| 바깥 요소 | 프레임 왼쪽 또는 위에 "my-vdream 근로자 화면", 역할 전환 바, "새 창으로 열기", "랜딩으로" 버튼. 오른쪽에 "이 화면에서 해볼 것" 안내 카드 (DEMO-007). 바깥 배경은 브이워크 로그인 패널과 같은 민트 그라데이션(`#23CDB7` → `#0B7A71`), 프레임 테두리는 `#0C0918` |
| 새 창으로 열기 | `window.open('/m?standalone=1', 'myvdream_mobile', 'width=390,height=844,resizable=yes')`. `standalone=1`이면 600px 이상이어도 프레임을 그리지 않는다. 반환값이 null이면 "팝업이 차단되었습니다. 현재 화면에서 그대로 보셔도 됩니다" 표시 |
| 미디어 쿼리 주의 | 프레임 안의 콘텐츠는 실제 뷰포트가 데스크톱이므로 `@media` 쿼리를 쓰지 않고 컨테이너 폭 390px에 맞춘 고정 레이아웃으로 만든다. 필요하면 `@container` 쿼리 사용 |

### 7.3 주요 화면과 동작

| 화면 | 핵심 동작 |
|---|---|
| 홈 | 출근 또는 퇴근 큰 버튼 1개(상태에 따라 전환). 오늘 업무 요약, 다음 할 업무 카드, 업무일지 상태와 바로가기, 미읽음 알림 수, 최신 공지 1건 |
| 업무 | 오늘 할 일, 전체, 완료 탭. 각 건에서 시작, 완료 큰 버튼. 상세에서 내용, 이력, 업무일지에 추가 바로가기 |
| 일지 | 오늘 업무일지 작성(항목 추가, 업무 선택 또는 직접 입력, 수행 내용, 소요 시간 15분 단위 선택, 산출물 첨부, 요약, 특이사항), 제출 버튼. 월별 달력에서 날짜별 상태, 보완 요청 사유 표시 |
| 근태 | 월별 달력. 일별 상태와 시각. 지각·조퇴 사유 입력. 잔여 연차와 휴가 신청 바로가기 |
| 상단 바 | 모든 탭 공통. 오른쪽에 봉투 아이콘(미읽음 쪽지 배지, 쪽지함으로 이동)과 종 아이콘(미읽음 알림 배지). 두 배지는 10초마다 갱신 |
| 쪽지 | 받은·보낸 함 탭, 쪽지 상세, 쓰기 화면. 대상 목록은 "기업 담당자"와 "담당 매니저" 두 묶음만 보이고 각 항목은 큰 선택 버튼. 재직이 없으면 쓰기 버튼 대신 "재직 중인 기업이 생기면 쪽지를 보낼 수 있습니다" 안내 |
| 더보기 | 쪽지, 이력서, 구직 등록, 채용 공고, 지원 현황, 휴가, 근로계약, 퇴사 신청, 공지사항, 알림, 설정(테마), 내 정보 |

### 7.4 접근성 구현 규칙

| 항목 | 규칙 |
|---|---|
| 레이블 | 모든 아이콘 버튼 `aria-label`. 목록 항목은 "n번째 업무, 제목, 우선순위 높음, 기한 내일, 진행중" 형태의 통합 `aria-label` |
| 제목 | 화면마다 `h1` 하나. 라우트 전환 시 `h1`에 포커스 |
| 상태 안내 | 출근 완료, 제출 완료 등은 `role="status"` 영역 텍스트로 알린다 |
| 터치 | 주요 버튼 `minHeight: 56`, 그 외 44 |
| 키보드 | 하단 탭, 달력, 폼 모두 Tab 이동과 Enter 동작 |
| 테스트 | 출시 전 VoiceOver(macOS Safari) 또는 NVDA(Windows Chrome)로 로그인, 출퇴근, 업무 완료, 업무일지 제출, 휴가 신청, 지원 흐름 점검. Lighthouse 접근성 점수 90 이상 |

---

## 8. 클라이언트 타입 생성

`scripts/generate-types.sh`: `uv run python scripts/export-openapi.py > apps/web/openapi.json` → `npx openapi-typescript apps/web/openapi.json -o apps/web/src/api/schema.d.ts`. 생성물은 커밋한다. CI가 재생성 결과의 차이를 검사한다.

---

## 9. 개발 환경과 Docker

### 9.1 로컬 개발

```bash
cp .env.example .env
```

```bash
docker compose -f deploy/docker-compose.dev.yml up -d
```

```bash
cd apps/api && uv sync && uv run alembic upgrade head && uv run python -m app.seed
```

```bash
cd apps/api && uv run uvicorn app.main:app --reload --port 8000
```

```bash
cd apps/web && npm install && npm run dev
```

- API: http://localhost:8000, Swagger: http://localhost:8000/api/docs
- 웹: http://localhost:5173 (Vite 프록시가 `/api`를 8000으로 전달)
- 개발은 `STORAGE_BACKEND=local`로 S3 없이 진행

### 9.2 운영 Docker Compose (`deploy/docker-compose.yml`)

| 서비스 | 이미지 또는 빌드 | 역할 |
|---|---|---|
| caddy | caddy:2 | 80, 443. HTTPS 자동 발급(Let's Encrypt). `/`는 `web_dist` 볼륨의 정적 파일, `/api/*`는 `api:8000`으로 프록시. SPA 폴백 `try_files {path} /index.html` |
| api | `ghcr.io/<owner>/my-vdream-api:latest` (CD가 빌드·푸시) | `alembic upgrade head` 후 `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2` |
| web-build | `ghcr.io/<owner>/my-vdream-web:latest` (CD가 빌드·푸시) | 이미지 안의 `dist/`를 `web_dist` 볼륨에 복사하고 종료 |
| mysql | mysql:8.4 | 볼륨 `mysql_data`. 호스트 포트 미노출 |

Caddyfile:

```
{$DOMAIN} {
  encode gzip
  handle /api/* {
    reverse_proxy api:8000
  }
  handle {
    root * /srv/web
    try_files {path} /index.html
    file_server
  }
}
```

### 9.3 Dockerfile 규칙

| 항목 | 규칙 |
|---|---|
| api | `python:3.12-slim`, uv 설치, `uv sync --frozen --no-dev`, 비root 사용자 |
| web | `node:22-alpine`에서 빌드 후 `dist/`만 담은 `alpine` 이미지. 컨테이너 시작 시 볼륨으로 복사하고 종료 (별도 nginx 이미지 없음) |
| 빌드 위치 | 두 이미지 모두 GitHub Actions에서 빌드한다. EC2(t3.small)에서는 빌드하지 않아 메모리 부족을 피한다 |
| 헬스체크 | api `/api/health`, mysql `mysqladmin ping` |

### 9.4 환경 변수

| 변수 | 예시 | 설명 |
|---|---|---|
| DOMAIN | myvdream.example.com | Caddy HTTPS 도메인 |
| APP_ENV | production | development, production |
| DATABASE_URL | mysql+pymysql://myvdream:pw@mysql:3306/myvdream | |
| MYSQL_ROOT_PASSWORD, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD | | |
| JWT_SECRET | (32자 이상) | |
| JWT_TTL_HOURS | 24 | |
| STORAGE_BACKEND | s3 | 개발은 local |
| S3_BUCKET, S3_REGION | | |
| AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY | | EC2 IAM 역할을 쓰면 생략 |
| DEMO_PASSWORD | | 데모 계정 공통 비밀번호 |
| MINIMUM_WAGE_HOURLY | 10320 | 고용 리포트 최저임금 참고 비교값(원). 2026년 최저시급. 해가 바뀌면 갱신 |
| SEED_ADMIN_LOGIN_ID, SEED_ADMIN_PASSWORD | | 비데모 시스템관리자 |
| CORS_ORIGINS | https://myvdream.example.com | 개발은 http://localhost:5173 |
| VITE_API_BASE_URL | (빈 값) | 같은 도메인이면 비움 |

---

## 10. AWS 배포

### 10.1 구성

| 항목 | 선택 | 이유 |
|---|---|---|
| 컴퓨트 | EC2 t3.small (2 vCPU, 2GB), Ubuntu 24.04, 20GB gp3 | Compose 4개 컨테이너에 충분. 월 약 2~3만원 |
| 네트워크 | 탄력적 IP, 보안 그룹 80·443 전체 허용, 22는 내 IP만 | |
| 도메인 | 저가 도메인 1개 구입 (가비아, Namecheap 등) 후 A 레코드를 탄력적 IP로. Route 53 호스팅 영역은 선택 | IP 주소 링크는 인상이 나쁘고 HTTPS 발급에 도메인이 필요 |
| 파일 | S3 버킷 1개(비공개). EC2에 IAM 역할 부여(해당 버킷 `GetObject`, `PutObject`) | 키 파일을 서버에 두지 않음 |
| DB | EC2 안 MySQL 컨테이너 + 볼륨 | RDS는 비용과 세팅 시간 대비 이점 없음. 데모 데이터는 매일 초기화되므로 백업 불필요 |
| 로그 | `docker compose logs`, json-file 드라이버 용량 제한 | |

### 10.2 절차

1. EC2 생성, 탄력적 IP 연결, 보안 그룹 설정, IAM 역할(S3) 부여.
2. `deploy/ec2-bootstrap.sh`로 Docker, Compose 설치, 저장소 clone(`deploy/` 폴더만 사용), 배포용 SSH 키 쌍 생성.
3. 도메인 A 레코드를 탄력적 IP로 설정하고 전파 확인.
4. GitHub 저장소 Secrets에 `EC2_HOST`, `EC2_USER`, `EC2_SSH_KEY`(개인키), `DOMAIN` 등록. GHCR 패키지는 공개로 두어 EC2에서 로그인 없이 pull.
5. EC2에 `.env` 작성 후 첫 1회만 `deploy/deploy.sh` 수동 실행. Caddy가 인증서를 자동 발급한다.
6. `https://{DOMAIN}/api/health`와 랜딩 페이지 확인, 데모 초기화 1회 실행.
7. 이후 배포는 PR을 main에 머지하면 `deploy.yml`이 자동 수행한다 (11.4). 서버에 직접 들어가는 일은 장애 대응 때만.

### 10.3 운영 점검

| 항목 | 내용 |
|---|---|
| 재시작 | 모든 서비스 `restart: unless-stopped` |
| 모니터링 | 무료 업타임 모니터(UptimeRobot 등)로 `/api/health` 5분 간격 감시. 이력서 제출 기간 동안 다운을 빨리 알기 위함 |
| 비용 | 제출 후 평가 기간이 끝나면 인스턴스 중지 |

---

## 11. Git 브랜치 전략과 CI/CD

혼자 2주 동안 개발하지만, 채용 공고가 CI/CD와 브랜치 활용을 평가 항목으로 적고 있으므로 **팀에서 쓰는 방식 그대로** 운영한다. 커밋 히스토리와 PR 목록, Actions 실행 기록이 그 자체로 포트폴리오다.

### 11.1 브랜치 전략 (GitHub Flow)

| 항목 | 규칙 |
|---|---|
| 모델 | GitHub Flow. 영구 브랜치는 `main` 하나. 모든 작업은 `main`에서 딴 짧은 브랜치에서 하고 PR로 합친다. Git Flow의 `develop`, `release` 브랜치는 두지 않는다 (혼자 개발, 환경 1개) |
| `main` | 항상 배포 가능한 상태. 머지되면 자동으로 운영에 배포된다 (11.4). 직접 push 금지 |
| 작업 브랜치 | `feat/<도메인>-<내용>`, `fix/<내용>`, `chore/<내용>`, `docs/<내용>`. 예: `feat/attendance-check-in`, `fix/work-log-resubmit`. 하루 안에 끝나는 크기로 자른다 (개발 계획의 일차별 작업을 2~4개 브랜치로) |
| 머지 | PR → CI 통과 → Squash merge → 브랜치 자동 삭제. 스쿼시 커밋 메시지는 PR 제목(Conventional Commits) |
| 보호 규칙 | `main`에 Branch protection: PR 필수, CI 상태 검사 필수(`ci / api`, `ci / web`), 직접 push 차단, 리니어 히스토리 강제. 혼자이므로 승인 리뷰 수는 0 |
| 태그 | 마일스톤마다 `v0.1.0`(1차 배포), `v0.5.0`(핵심 흐름), `v1.0.0`(제출). GitHub Release에 변경 요약 |
| 이슈 | 일차별 작업을 GitHub Issues로 만들고 PR 본문에 `Closes #n`. Projects 보드(Todo / In progress / Done)로 진행 상황을 공개 |

### 11.2 커밋과 PR 규칙

| 항목 | 규칙 |
|---|---|
| 커밋 메시지 | Conventional Commits. `feat(api): 출근 체크와 지각 판정`, `fix(web): 휴대폰 프레임 스케일 계산`. 범위는 `api`, `web`, `deploy`, `ci`, `docs` |
| PR 제목 | 커밋 메시지와 같은 형식. 스쿼시 머지 커밋이 된다 |
| PR 템플릿 | 변경 내용, 관련 이슈, 확인 방법(스크린샷·Swagger 경로), 체크리스트(테스트 추가, 타입 생성물 갱신, 문서 갱신) |
| 로컬 훅 | `pre-commit`으로 커밋 전 ruff·mypy(api), eslint·prettier(web) 실행. CI 실패를 미리 막는다 |
| 작은 PR | 변경 300줄 이내 목표. 큰 기능은 API PR과 화면 PR로 나눈다 |

### 11.3 CI 워크플로 (`.github/workflows/ci.yml`)

PR과 `main` push마다 실행. 바뀐 경로에 해당하는 잡만 돈다.

| 잡 | 트리거 경로 | 단계 |
|---|---|---|
| `api` | `apps/api/**`, `.github/**` | `uv sync` (캐시) → `ruff check` → `ruff format --check` → `mypy` → `pytest` (MySQL 서비스 컨테이너 사용) |
| `web` | `apps/web/**`, `.github/**` | `npm ci` (캐시) → `eslint` → `tsc --noEmit` → `vitest run` → `vite build` |
| `types` | `apps/api/**`, `apps/web/src/api/**` | `scripts/generate-types.sh` 실행 후 `git diff --exit-code` (생성물 미갱신 감지) |
| `docker` | `apps/**`, `deploy/**` | 두 Dockerfile `docker build` (푸시 없음). 배포 전에 이미지가 깨지는지 확인 |

```yaml
name: ci
on:
  pull_request:
  push:
    branches: [main]
jobs:
  api:
    runs-on: ubuntu-latest
    services:
      mysql:
        image: mysql:8.4
        env: { MYSQL_ROOT_PASSWORD: test, MYSQL_DATABASE: test }
        ports: ["3306:3306"]
        options: --health-cmd "mysqladmin ping -h localhost" --health-interval 5s --health-retries 10
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with: { enable-cache: true }
      - run: uv sync --frozen
        working-directory: apps/api
      - run: uv run ruff check . && uv run ruff format --check . && uv run mypy app
        working-directory: apps/api
      - run: uv run pytest
        working-directory: apps/api
        env: { DATABASE_URL: mysql+pymysql://root:test@127.0.0.1:3306/test }
  web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm, cache-dependency-path: apps/web/package-lock.json }
      - run: npm ci && npm run lint && npx tsc --noEmit && npm test -- --run && npm run build
        working-directory: apps/web
```

(`types`, `docker` 잡은 같은 파일에 추가. 전체 CI 시간 목표 5분 이내.)

### 11.4 CD 워크플로 (`.github/workflows/deploy.yml`)

`main`에 push(=PR 머지)되면 실행. CI 성공을 기다리지 않고 별도로 돌되, 11.1의 보호 규칙 때문에 CI를 통과한 코드만 `main`에 들어온다.

| 단계 | 내용 |
|---|---|
| 1. 빌드·푸시 | `docker/build-push-action`으로 `apps/api`, `apps/web` 이미지를 빌드해 GHCR에 `latest`와 `sha-<커밋>` 두 태그로 푸시. `GITHUB_TOKEN`으로 로그인하므로 별도 비밀 없음. 레이어 캐시(`cache-from: type=gha`) |
| 2. 배포 | `appleboy/ssh-action`으로 EC2에 접속해 `cd ~/my-vdream && git pull && bash deploy/deploy.sh` 실행. `deploy.sh`는 `docker compose pull && docker compose up -d --remove-orphans && docker image prune -f` |
| 3. 확인 | `curl -fsS https://${DOMAIN}/api/health`가 200이 아니면 잡 실패. 실패 시 GitHub가 메일 알림 |
| 환경 | GitHub Environment `production`에 Secrets를 두고 잡에 `environment: production` 지정. Deployments 탭에 배포 이력이 남는다 |

```yaml
name: deploy
on:
  push:
    branches: [main]
concurrency: { group: deploy, cancel-in-progress: false }
jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    environment: production
    permissions: { contents: read, packages: write }
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with: { registry: ghcr.io, username: ${{ github.actor }}, password: ${{ secrets.GITHUB_TOKEN }} }
      - uses: docker/build-push-action@v6
        with:
          context: apps/api
          push: true
          tags: ghcr.io/${{ github.repository_owner }}/my-vdream-api:latest,ghcr.io/${{ github.repository_owner }}/my-vdream-api:sha-${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - uses: docker/build-push-action@v6
        with:
          context: apps/web
          push: true
          tags: ghcr.io/${{ github.repository_owner }}/my-vdream-web:latest,ghcr.io/${{ github.repository_owner }}/my-vdream-web:sha-${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ${{ secrets.EC2_USER }}
          key: ${{ secrets.EC2_SSH_KEY }}
          script: cd ~/my-vdream && git pull --ff-only && bash deploy/deploy.sh
      - run: curl -fsS https://${{ secrets.DOMAIN }}/api/health
```

롤백: 문제가 생기면 EC2에서 `IMAGE_TAG=sha-<이전 커밋> bash deploy/deploy.sh`로 이전 이미지를 올린다. compose 파일은 `image: ghcr.io/.../my-vdream-api:${IMAGE_TAG:-latest}` 형태로 태그를 변수화한다.

### 11.5 왜 이 구성인가 (다른 선택지와 비교)

| 선택지 | 장점 | 단점 | 판단 |
|---|---|---|---|
| **GitHub Actions → GHCR → SSH 배포 (채택)** | 설정 파일 2개, 추가 비용 0, EC2에서 빌드 안 함, Actions·Packages·Deployments 탭에 이력이 남아 보여주기 좋음 | SSH 키 관리 필요 | 2주 범위에서 가장 적은 설정으로 "진짜 CD" |
| EC2에서 `git pull && docker compose build` | 더 단순 | t3.small에서 React 빌드가 느리고 메모리 부족 가능, 빌드 실패가 운영에 영향 | 1차 배포 전 임시로만 |
| AWS CodePipeline + CodeDeploy | AWS 네이티브 | 설정 항목이 많고 IAM 역할·에이전트 세팅에 하루 이상 | 2주에는 과함 |
| ECS Fargate + ECR | 운영 표준 | 비용과 세팅 시간, 이 규모에 불필요 | 확장 계획에만 기재 |
| EC2에 self-hosted runner | 비밀 없이 로컬 배포 | runner 유지 관리, 보안 | 불필요 |

### 11.6 Dependabot과 유지

`.github/dependabot.yml`로 pip(`apps/api`), npm(`apps/web`), github-actions를 주간 점검한다. 생기는 PR은 CI가 통과하면 머지한다. 2주 동안 Dependabot PR이 몇 개 머지된 기록 자체가 운영 습관을 보여준다.

### 11.7 코드 품질

| 항목 | 규칙 |
|---|---|
| 백엔드 | ruff(린트+포맷), mypy. 서비스 단위 테스트는 상태 전이, 근태 판정, 업무일지 집계, 권한 검사 중심. API 테스트는 로그인 → 핵심 흐름 1개씩 |
| 프론트 | ESLint + Prettier. Vitest는 PhoneFrame, 상태 뱃지, 날짜 유틸 정도 |
| README | 프로젝트 소개, 데모 링크와 계정, 아키텍처 그림, 로컬 실행, 폴더 구조, 설계 문서 링크, **브랜치 전략과 CI/CD 그림**, 확장 계획. CI·Deploy 상태 배지를 상단에 |

---

## 12. 보안

| 영역 | 규칙 |
|---|---|
| 전송 | HTTPS만. Caddy가 HTTP → HTTPS 리다이렉트 |
| 토큰 | 24시간 JWT, `localStorage`. XSS 방어는 React 기본 이스케이프와 외부 HTML 미사용 |
| 비밀번호 | bcrypt. 데모 계정 비밀번호는 README에 공개하되 변경 불가 |
| 입력 | Pydantic `extra="forbid"`. SQLAlchemy 바인딩 |
| CORS | 운영은 같은 도메인이므로 사실상 불필요. 개발 오리진만 허용 |
| 속도 제한 | slowapi로 로그인·데모 로그인 IP당 분당 20회, 파일 업로드 분당 10회 |
| 파일 | 비공개 버킷, 사전 서명 URL, MIME·확장자·크기 검사 |
| 개인정보 | 시드 데이터는 모두 가상 인물. 실제 개인정보 입력 금지 안내를 랜딩에 표시 |
| 비밀 | `.env`는 EC2에만. 저장소에 커밋 금지. 배포용 SSH 키, 호스트, 도메인은 GitHub Environment `production` Secrets에만 둔다. GHCR 푸시는 `GITHUB_TOKEN` |

---

## 13. 비기능 요구사항

| 항목 | 목표 |
|---|---|
| 응답 시간 | 조회 API p95 500ms 이내 (t3.small 기준) |
| 동시 사용자 | 수 명 (평가자) |
| 가용성 | 이력서 제출 후 평가 기간 동안 상시 가동. 업타임 모니터 감시 |
| 브라우저 | 최신 Chrome, Edge, Safari, Firefox. 데스크톱 1280px, 모바일 390px |
| 접근성 | 모바일 화면 Lighthouse 접근성 90 이상, 스크린리더 핵심 흐름 점검 |
| 데이터 | 시스템관리자 버튼으로 데모 초기화. 영구 보존 데이터 없음 |
| 언어 | 한국어 |
