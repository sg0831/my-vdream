# my-vdream

장애인 재택근무 관리 시스템. 브이드림의 재택근무 관리 방식을 벤치마킹해 **근로자 · 기업 담당자 · 브이드림 매니저 · 시스템관리자**가 채용부터 근태, 업무, 업무일지, 쪽지, 월간 장애인 고용 리포트까지 같은 정보를 보는 웹 서비스입니다. 브이드림 개발자 지원을 위한 2주 포트폴리오 프로젝트입니다.

- 데모: `https://<도메인>` (랜딩의 역할 버튼으로 비밀번호 없이 체험)
- 바로 가기: `/demo/worker` · `/demo/company` · `/demo/manager` · `/demo/admin` (해당 역할로 즉시 로그인)
- 설계 문서: [docs/](docs/) (개요 · 요구기능 · DB · 기술스펙 · 개발 계획)
- 구현 현황과 검증 결과: [docs/06-unimplemented-features.md](docs/06-unimplemented-features.md) (요구기능 163개 전부 구현, Lighthouse 접근성 100)

## 데모 계정

| 역할 | 아이디 | 비고 |
|---|---|---|
| 근로자 | `demo.worker` | 중증 시각장애, (주)하늘데이터 재직 |
| 기업 담당자 | `demo.company` | (주)하늘데이터 |
| 브이드림 매니저 | `demo.manager` | 하늘데이터·누리커머스 담당 |
| 시스템관리자 | `demo.admin` | 데모 데이터 초기화 가능 |

비밀번호는 환경 변수 `DEMO_PASSWORD`(기본 `demo1234!`). 데모 계정은 비밀번호를 바꿀 수 없습니다.

## 주요 기능

- **근로자 모바일 화면** (`/m`): 데스크톱에서는 390×844 휴대폰 프레임 안에, 실제 휴대폰에서는 전체 화면으로 표시. 출퇴근, 업무 시작·완료, 업무일지 작성·제출(산출물 첨부), 휴가, 지원, 쪽지
- **기업 담당자** (`/admin`): 업무 배정, 업무일지 확인·보완 요청, 근태 정정, 휴가 승인, 채용 진행, **월간 장애인 고용 리포트**(공단 기준 월 60시간·중증 2배수·16일 참고 판정, 엑셀, A4 인쇄)
- **브이드림 매니저** (`/admin`): 공고 승인, 채용 진행, 퇴사 승인, 상담보고서(상태 점수 추이), 모든 사용자에게 쪽지·단체 발송
- **쪽지 규칙**: 근로자·기업 담당자는 자기 기업의 담당 매니저에게만 보낼 수 있고, 대상 목록에도 그 매니저만 보입니다. 목록 API와 발송 API가 같은 규칙 함수(`app/domain.py`)를 씁니다
- **배치 없음**: 재직 상태·결근·공고 마감은 저장하지 않고 요청 시 오늘 날짜로 계산
- **브랜드 컬러**: 브이드림·브이매치·브이워크 사이트에서 수집한 민트 `#2EB6AA`·바이올렛 `#584C9D` (로고 미사용)

## 아키텍처

```
Browser (React SPA: / · /m · /admin · /system)
   │ HTTPS
Caddy (자동 TLS, 정적 파일, /api 프록시)
   │
FastAPI (SQLAlchemy 2) ── MySQL 8.4
   └── AWS S3 (업무일지 산출물)
```

| 영역 | 기술 |
|---|---|
| 백엔드 | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, PyJWT, slowapi, openpyxl |
| 프론트엔드 | React 18, TypeScript, Vite 5, MUI 6, TanStack Query, Recharts, Vitest, openapi-typescript |
| 인프라 | Docker Compose, Caddy, AWS EC2·S3, GitHub Actions, GHCR |

## 로컬 실행

```bash
cd apps/api && python3 -m venv .venv && .venv/bin/pip install fastapi "uvicorn[standard]" sqlalchemy pymysql cryptography pydantic-settings pyjwt bcrypt python-multipart openpyxl boto3 slowapi alembic
```

```bash
cd apps/api && .venv/bin/uvicorn app.main:app --reload --port 8000
```

```bash
cd apps/web && npm install && npm run dev
```

- 웹 http://localhost:5173 · API 문서 http://localhost:8000/api/docs
- 기본 DB는 SQLite(`apps/api/dev.db`). 비어 있으면 시작 시 최근 3개월 데모 데이터를 자동 생성합니다.

## 테스트

```bash
cd apps/api && .venv/bin/pip install pytest httpx ruff "moto[server]" && .venv/bin/python -m pytest -q
```

```bash
cd apps/web && npx tsc --noEmit && npx vitest run
```

- 백엔드 16개: 고용 인정 판정 경계값, 시급 환산, 쪽지 권한(다른 기업 매니저에게 보내면 403), 리포트 판정 네 종류, 근로자 하루 흐름, 채용 흐름, 비활성 기업 로그인 차단, 증명사진 권한, 필터, 대시보드
- MySQL로 돌리기: `DATABASE_URL=mysql+pymysql://...` 지정 후 `alembic upgrade head && pytest`
- S3 통합: `moto_server -p 19000` 후 `S3_TEST_ENDPOINT=http://127.0.0.1:19000 pytest tests/test_s3_integration.py`

## 운영 구성을 로컬에서 실행

```bash
cd deploy && docker compose --env-file local.env -f docker-compose.yml -f docker-compose.local.yml up -d --build
```

http://localhost:8088 에서 Caddy·API·웹·MySQL 운영 구성 그대로 확인할 수 있습니다.

## 브랜치 전략과 CI/CD

- **GitHub Flow**: `main` 보호(PR 필수, CI 통과 필수), `feat/*`·`fix/*` 브랜치, squash merge
- **CI** (`.github/workflows/ci.yml`): PR마다 ruff + pytest(SQLite) + S3 통합(moto), MySQL 8.4 서비스에서 Alembic upgrade·check + pytest, OpenAPI 타입 생성물 일치 검사 + tsc + Vitest + 빌드, Docker 이미지 빌드
- **CD** (`.github/workflows/deploy.yml`): `main` 머지 시 API·웹 이미지를 GHCR에 `latest`·`sha-<커밋>`으로 푸시 → SSH로 EC2에서 `deploy/deploy.sh` → 헬스체크
- 롤백: EC2에서 `IMAGE_TAG=sha-<이전 커밋> bash deploy/deploy.sh`

## 배포 (AWS)

1. EC2(t3.small, Ubuntu 24.04) 생성, 탄력적 IP, 보안 그룹 80·443, S3 접근 IAM 역할
2. 도메인 A 레코드를 탄력적 IP로
3. `bash deploy/ec2-bootstrap.sh <저장소 URL>` 후 `.env` 작성
4. GitHub Environment `production`에 `EC2_HOST`, `EC2_USER`, `EC2_SSH_KEY`, `DOMAIN` 등록
5. 첫 배포는 `main`에 머지하거나 Actions에서 deploy 수동 실행

## 확장 계획

전체 설계(v1.0)는 [docs/archive/my-vdream-v1-full-scope](docs/archive/my-vdream-v1-full-scope)에 있습니다. Flutter 앱, 푸시 알림, 근무 확인, 휴게 기록, 설문 양식 빌더, 재직 중 이직 지원과 조건부 퇴사 승인, 근로계약 갱신 이력, 공휴일·휴무일 관리가 포함됩니다.

토큰을 `localStorage`에 두는 것은 데모 단순화를 위한 선택이며, 운영에서는 HttpOnly 쿠키 + 리프레시 토큰 회전(v1.0 설계)으로 바꿉니다.
