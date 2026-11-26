import { useEffect, useState, type ReactNode } from 'react'
import { Link as RLink, Outlet, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom'
import {
  Alert, AppBar, Box, Button, Checkbox, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Drawer, FormControlLabel, List, ListItemButton,
  ListItemText, MenuItem, Stack, Tab, Tabs, TextField, Toolbar, Typography,
} from '@mui/material'
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, del, download, openFile, post, put } from '../../api'
import { useAuth } from '../../auth'
import { hm, kst, L, lb, ym, ymd } from '../../labels'
import { tokens } from '../../theme'
import { MessageCompose, MessageDetail, MessagesPage, NoticesPage, NotificationsPage } from '../../shared'
import { BackLink, DataTable, Empty, Loading, PageTitle, PromptDialog, Section, Stat, Status, StatusChip, ThemeToggle, UnreadBadges, RoleSwitcher, useAct, useQ } from '../../ui'
import { MyInfo, ResumeEditor } from '../mobile'

type Menu = [string, string][]
const CM_MENU: Menu = [['', '대시보드'], ['workers', '근로자'], ['postings', '채용'], ['attendance', '근태'], ['leaves', '휴가'], ['tasks', '업무'],
  ['work-logs', '업무일지'], ['reports/employment', '고용 리포트'], ['resignations', '퇴사 통보'], ['messages', '쪽지'], ['notices', '공지사항'], ['me', '내 정보']]
const VM_MENU: Menu = [['', '대시보드'], ['companies', '기업'], ['workers', '근로자'], ['seekers', '구직자'], ['postings', '채용'], ['attendance', '근태'],
  ['leaves', '휴가'], ['tasks', '업무'], ['work-logs', '업무일지'], ['counseling', '상담'], ['resignations', '퇴사 신청'], ['messages', '쪽지'], ['notices', '공지사항'], ['me', '내 정보']]
export const SA_MENU: Menu = [['', '대시보드'], ['companies', '기업 관리'], ['users', '계정 관리'], ['announcements', '공지사항'], ['me', '내 정보']]

export function AdminLayout({ base, menu, onToggleTheme }: { base: string; menu: Menu; onToggleTheme: () => void }) {
  const { me } = useAuth()
  const loc = useLocation()
  const W = 220
  const active = (p: string) => (p === '' ? loc.pathname === base : loc.pathname.startsWith(`${base}/${p}`))
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar position="fixed" sx={{ zIndex: 1201, bgcolor: tokens.navy[950] }} elevation={0}>
        <Toolbar>
          <Typography component={RLink} to="/" sx={{ fontWeight: 800, color: tokens.mint[500], textDecoration: 'none', mr: 2 }}>my-vdream</Typography>
          <Typography sx={{ flex: 1, color: '#FFFFFF' }}>{lb(me?.role)} · {me?.name}{me?.companyName ? ` · ${me.companyName}` : ''}</Typography>
          <Box sx={{ color: '#FFFFFF', display: 'flex', alignItems: 'center' }}><RoleSwitcher /><ThemeToggle onToggle={onToggleTheme} />{me?.role !== 'SYSTEM_ADMIN' && <UnreadBadges base={base} />}</Box>
        </Toolbar>
      </AppBar>
      <Drawer variant="permanent" sx={{ width: W, '& .MuiDrawer-paper': { width: W, boxSizing: 'border-box' } }}>
        <Toolbar />
        <List component="nav" aria-label="관리 메뉴">
          {menu.map(([p, l]) => (
            <ListItemButton key={p} component={RLink} to={p ? `${base}/${p}` : base} selected={active(p)} aria-current={active(p) ? 'page' : undefined}
              sx={{ '&.Mui-selected': { bgcolor: 'primary.main', color: 'primary.contrastText', '&:hover': { bgcolor: 'primary.dark' } } }}>
              <ListItemText primary={l} />
            </ListItemButton>
          ))}
        </List>
      </Drawer>
      <Box component="main" sx={{ flex: 1, p: 3, minWidth: 0 }}><Toolbar /><GuideCard role={me?.role} /><Outlet /></Box>
    </Box>
  )
}

const GUIDES: Record<string, string[]> = {
  COMPANY_MANAGER: ['업무 메뉴에서 근로자에게 업무를 배정해 보세요.', '업무일지 메뉴에서 제출된 일지를 확인하거나 보완을 요청해 보세요.', '고용 리포트에서 공단 제출용 월간 리포트를 만들고 엑셀·PDF로 받아 보세요.'],
  VDREAM_MANAGER: ['채용 메뉴에서 승인 대기 공고를 승인해 보세요.', '상담 메뉴에서 상담보고서를 쓰고 근로자 상세에서 점수 추이를 보세요.', '쪽지에서 "특정 기업 전체"로 단체 쪽지를 보내 보세요.'],
  SYSTEM_ADMIN: ['기업 관리에서 담당 매니저를 바꿔 보세요.', '계정 관리에서 새 계정을 만들어 보세요.', '대시보드의 데모 데이터 초기화로 처음 상태로 되돌릴 수 있습니다.'],
}

/** 역할별 둘러보기 안내 (DEMO-007). 닫으면 기기에 기억한다 */
function GuideCard({ role }: { role?: string }) {
  const key = `myvdream.guide.${role}`
  const [hidden, setHidden] = useState(() => { try { return localStorage.getItem(key) === '1' } catch { return false } })
  if (!role || hidden || !GUIDES[role]) return null
  return (
    <Alert severity="info" sx={{ mb: 2 }} onClose={() => { setHidden(true); try { localStorage.setItem(key, '1') } catch { /* ignore */ } }}>
      <b>이 화면에서 해볼 것</b>
      <Box component="ol" sx={{ m: 0, pl: 2.5 }}>{GUIDES[role].map((g) => <li key={g}>{g}</li>)}</Box>
    </Alert>
  )
}

function MonthPicker({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return <TextField size="small" type="month" label="월" value={value} onChange={(e) => onChange(e.target.value)} InputLabelProps={{ shrink: true }} />
}

// ---------------- Dashboard ----------------
function Dashboard() {
  const { me } = useAuth()
  const nav = useNavigate()
  const isVM = me?.role === 'VDREAM_MANAGER'
  const [all, setAll] = useState(false)
  const q = useQ<any>(['dash', all], '/dashboard', { all_companies: all })
  const d = q.data
  const prev = (() => { const t = new Date(); t.setMonth(t.getMonth() - 1); return ym(t) })()
  return (
    <Box>
      <PageTitle action={isVM && <FormControlLabel control={<Checkbox checked={all} onChange={(e) => setAll(e.target.checked)} />} label="전체 기업 보기" />}>
        {isVM ? (all ? '브이드림 전체 현황' : '내 담당 기업 현황') : `${me?.companyName} 현황`}
      </PageTitle>
      <Loading q={q} />
      {d && (
        <>
          <Stack direction="row" flexWrap="wrap" gap={2} sx={{ mb: 2 }}>
            <Stat label="재직 근로자" value={d.activeWorkers} />
            <Stat label="아직 출근 전" value={d.notCheckedIn} />
            <Stat label="진행 중 업무" value={d.tasksInProgress} hint={`기한 초과 ${d.tasksOverdue}건`} />
            <Stat label="확인 대기 업무일지" value={d.workLogsToConfirm} />
            <Stat label="이번 주 업무일지 미제출" value={d.workLogsMissingThisWeek} />
            {isVM ? (<>
              <Stat label="승인 대기 공고" value={d.postingsPending} /><Stat label="승인 대기 퇴사 신청" value={d.resignationsPending} />
              <Stat label="구직중 근로자" value={d.seekers} /><Stat label="이번 달 상담" value={d.counselingThisMonth} />
            </>) : (<>
              <Stat label="승인 대기 휴가" value={d.leavesPending} /><Stat label="게시 중 공고" value={d.openPostings} />
            </>)}
          </Stack>
          {!isVM && d.lastMonthReport && (
            <Alert severity={d.lastMonthReport.warnings ? 'warning' : 'success'} sx={{ mb: 2 }} action={<Button onClick={() => nav(`/admin/reports/employment?from=${d.lastMonthReport.month}&to=${d.lastMonthReport.month}`)}>리포트 열기</Button>}>
              지난달({d.lastMonthReport.month}) 고용 리포트: 장애인 근로자 {d.lastMonthReport.workers}명, 고용 인정 인원 추정 <b>{d.lastMonthReport.recognizedCount}명</b>, 데이터 경고 {d.lastMonthReport.warnings}건
            </Alert>
          )}
          {isVM && !!d.byCompany?.length && (
            <Section title="기업별 재직 근로자">
              <DataTable caption="기업별 재직 근로자" rows={d.byCompany} cols={[{ label: '기업', render: (r: any) => r.companyName }, { label: '재직 근로자', render: (r: any) => `${r.activeWorkers}명` }]} />
            </Section>
          )}
          <Section title="오늘 근무 현황">
            <DataTable caption="오늘 근무 현황" rows={d.today} onRow={(r: any) => nav(`/admin/workers/${r.employmentId}`)} cols={[
              { label: '근로자', render: (r: any) => r.workerName }, { label: '기업', render: (r: any) => r.companyName },
              { label: '상태', render: (r: any) => <Chip size="small" label={r.state} /> }, { label: '근태', render: (r: any) => r.status ? <StatusChip value={r.status} /> : '-' }]} />
          </Section>
        </>
      )}
    </Box>
  )
}

// ---------------- Workers / Employments ----------------
function Workers() {
  const { me } = useAuth()
  const nav = useNavigate()
  const isVM = me?.role === 'VDREAM_MANAGER'
  const [mine, setMine] = useState(isVM)
  const [resigned, setResigned] = useState(false)
  const q = useQ<any[]>(['emps', mine, resigned], '/employments', { mine, include_resigned: resigned })
  return (
    <Box>
      <PageTitle>재직 근로자</PageTitle>
      <Stack direction="row" sx={{ mb: 1 }}>
        {isVM && <FormControlLabel control={<Checkbox checked={mine} onChange={(e) => setMine(e.target.checked)} />} label="내 담당 기업만" />}
        <FormControlLabel control={<Checkbox checked={resigned} onChange={(e) => setResigned(e.target.checked)} />} label="퇴사자 포함" />
      </Stack>
      <Loading q={q} />
      {q.data && <DataTable caption="재직 근로자 목록" rows={q.data} onRow={(r: any) => nav(`/admin/workers/${r.id}`)} cols={[
        { label: '이름', render: (r: any) => r.workerName }, { label: '기업', render: (r: any) => r.companyName },
        { label: '장애', render: (r: any) => `${lb(r.disabilityType)} · ${lb(r.disabilityDegree)}` },
        { label: '입사일', render: (r: any) => r.startDate }, { label: '퇴사일', render: (r: any) => r.endDate ?? '-' },
        { label: '주 소정', render: (r: any) => r.contract ? `${r.contract.weeklyWorkHours}h` : '-' },
        { label: '상태', render: (r: any) => <StatusChip value={r.status} /> }]} />}
    </Box>
  )
}

function WorkerDetail() {
  const { id } = useParams()
  const { me } = useAuth()
  const isVM = me?.role === 'VDREAM_MANAGER'
  const q = useQ<any>(['emp', id], `/employments/${id}`)
  const att = useQ<any[]>(['att-one', id], '/attendance', { month: ym(), employment_id: id })
  const stats = useQ<any[]>(['wl-stats', ym()], '/work-logs/stats', { month: ym() })
  const [tab, setTab] = useState(0)
  const e = q.data
  const s = att.data?.[0]?.summary
  const st = stats.data?.find((x) => String(x.employmentId) === id)
  const tasks = useQ<any[]>(['tasks-emp', id], '/tasks', { employment_id: id })
  const leaves = useQ<any>(['leaves'], '/leaves')
  const lb2 = leaves.data?.balances?.find((b: any) => String(b.employmentId) === id)
  const tk = tasks.data ?? []
  return (
    <Box>
      <BackLink />
      <Loading q={q} />
      {e && (
        <>
          <PageTitle>{e.workerName} <Typography component="span" color="text.secondary">{e.companyName} · {lb(e.disabilityType)} {lb(e.disabilityDegree)}</Typography></PageTitle>
          <Stack direction="row" flexWrap="wrap" gap={2} sx={{ mb: 2 }}>
            <Stat label="재직 상태" value={lb(e.status)} hint={`${e.startDate} ~ ${e.endDate ?? ''}`} />
            {s && <Stat label="이번 달 출근" value={`${s.attended}일`} hint={`지각 ${s.late} · 결근 ${s.absent}`} />}
            {st && <Stat label="이번 달 업무일지 제출률" value={`${st.submitRate}%`} hint={hm(st.totalMinutes)} />}
            <Stat label="업무" value={`진행 ${tk.filter((t) => t.status === 'IN_PROGRESS').length}건`} hint={`완료 ${tk.filter((t) => t.status === 'COMPLETED').length} · 기한 초과 ${tk.filter((t) => t.overdue).length}`} />
            {lb2 && <Stat label={`${lb2.year}년 연차`} value={`잔여 ${lb2.remaining}일`} hint={`부여 ${lb2.granted} · 사용 ${lb2.used}`} />}
          </Stack>
          <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
            <Tab label="근로계약" /><Tab label="이력서" />{isVM && <Tab label="상담 이력" />}
          </Tabs>
          {tab === 0 && <ContractForm emp={e} />}
          {tab === 1 && (isVM ? <ResumeEditor workerId={e.workerId} compact /> : <ResumeView workerId={e.workerId} />)}
          {tab === 2 && isVM && <CounselingList workerId={e.workerId} />}
        </>
      )}
    </Box>
  )
}

function ResumeView({ workerId }: { workerId: number }) {
  const q = useQ<any>(['resume', workerId], `/resumes/${workerId}`)
  const r = q.data
  if (!r) return <Loading q={q} />
  const p = r.profile ?? {}
  return (
    <Section title="이력서">
      {[['이름', r.user.name], ['생년월일', p.birthDate], ['장애', `${lb(p.disabilityType)} ${lb(p.disabilityDegree)}`], ['보조기기', p.assistiveDevices],
        ['재택 환경', `PC ${p.hasPc ? '있음' : '없음'} · 인터넷 ${p.hasInternet ? '가능' : '불가'} · ${p.softwareSkills ?? ''}`],
        ['희망 직무', (p.desiredJobFields ?? '').split(',').map((x: string) => L[x] ?? x).join(', ')], ['보유 기술', p.skills], ['자기소개', p.introduction]]
        .map(([k, v]) => <Typography key={k}><b>{k}</b> {v || '-'}</Typography>)}
      <Typography sx={{ mt: 1, fontWeight: 700 }}>학력</Typography>
      {r.educations.map((x: any) => <Typography key={x.id}>{x.institution} {lb(x.type)} {x.major ?? ''} ({lb(x.status)})</Typography>)}
      <Typography sx={{ mt: 1, fontWeight: 700 }}>경력</Typography>
      {r.careers.map((x: any) => <Typography key={x.id}>{x.institution} · {x.duties} ({x.startDate}~{x.endDate ?? ''})</Typography>)}
    </Section>
  )
}

function ContractForm({ emp }: { emp: any }) {
  const a = useAct()
  const [f, setF] = useState<any>(emp.contract ?? {})
  const set = (k: string) => (e: any) => setF({ ...f, [k]: e.target.value })
  const fields: [string, string, string?][] = [['startDate', '계약 시작일', 'date'], ['endDate', '계약 종료일', 'date'], ['workLocation', '근무 장소'], ['jobDescription', '업무 내용'],
    ['workDays', '근무 요일 (MON,TUE,...)'], ['workStartTime', '소정 근로 시작', 'time'], ['workEndTime', '소정 근로 종료', 'time'], ['breakMinutes', '휴게(분)', 'number'],
    ['weeklyWorkHours', '주 소정근로시간', 'number'], ['annualLeaveDays', '연차 부여일수', 'number'], ['salaryAmount', '급여(원)', 'number'], ['equipmentSupport', '지원 장비'], ['note', '비고']]
  return (
    <Section title="근로계약 (재직당 1건)">
      <Stack direction="row" flexWrap="wrap" gap={2}>
        <TextField select label="계약 형태" value={f.contractType ?? ''} onChange={set('contractType')} sx={{ minWidth: 180 }}>{['FIXED_TERM', 'INDEFINITE'].map((x) => <MenuItem key={x} value={x}>{L[x]}</MenuItem>)}</TextField>
        <TextField select label="근무 형태" value={f.workType ?? ''} onChange={set('workType')} sx={{ minWidth: 140 }}>{['REMOTE', 'HYBRID'].map((x) => <MenuItem key={x} value={x}>{L[x]}</MenuItem>)}</TextField>
        <TextField select label="급여 형태" value={f.salaryType ?? ''} onChange={set('salaryType')} sx={{ minWidth: 140 }}>{['MONTHLY', 'HOURLY'].map((x) => <MenuItem key={x} value={x}>{L[x]}</MenuItem>)}</TextField>
        {fields.map(([k, l, t]) => <TextField key={k} label={l} type={t ?? 'text'} value={f[k] ?? ''} onChange={set(k)} InputLabelProps={{ shrink: true }} sx={{ minWidth: 200 }} />)}
      </Stack>
      <Button variant="contained" sx={{ mt: 2 }} onClick={() => a.run(() => put(`/employments/${emp.id}/contract`, {
        contractType: f.contractType, startDate: f.startDate, endDate: f.endDate || null, workType: f.workType, workLocation: f.workLocation, jobDescription: f.jobDescription,
        workDays: f.workDays, workStartTime: f.workStartTime, workEndTime: f.workEndTime, breakMinutes: Number(f.breakMinutes), weeklyWorkHours: Number(f.weeklyWorkHours),
        annualLeaveDays: f.annualLeaveDays === '' ? null : Number(f.annualLeaveDays), salaryType: f.salaryType, salaryAmount: Number(f.salaryAmount),
        equipmentSupport: f.equipmentSupport, note: f.note,
      }), '근로계약을 저장했습니다.')}>저장</Button>
      <Status msg={a.msg} />
    </Section>
  )
}

function Seekers() {
  const [field, setField] = useState('')
  const [dtype, setDtype] = useState('')
  const [name, setName] = useState('')
  const q0 = useQ<any[]>(['seekers', field, name], '/seekers', { job_field: field || undefined, q: name || undefined })
  const q = { ...q0, data: q0.data?.filter((r) => !dtype || r.disabilityType === dtype) }
  const w = useQ<any[]>(['all-workers'], '/workers')
  const a = useAct()
  return (
    <Box>
      <PageTitle>구직자</PageTitle>
      <Stack direction="row" gap={2} sx={{ mb: 2 }} flexWrap="wrap">
        <TextField size="small" select label="희망 직무" value={field} onChange={(e) => setField(e.target.value)} sx={{ minWidth: 160 }}><MenuItem value="">전체</MenuItem>{FIELDS.map((x) => <MenuItem key={x} value={x}>{L[x]}</MenuItem>)}</TextField>
        <TextField size="small" select label="장애유형" value={dtype} onChange={(e) => setDtype(e.target.value)} sx={{ minWidth: 140 }}><MenuItem value="">전체</MenuItem>{['PHYSICAL', 'BRAIN_LESION', 'VISUAL', 'HEARING', 'SPEECH', 'INTELLECTUAL', 'AUTISM', 'MENTAL'].map((x) => <MenuItem key={x} value={x}>{L[x]}</MenuItem>)}</TextField>
        <TextField size="small" label="이름 검색" value={name} onChange={(e) => setName(e.target.value)} />
      </Stack>
      <Loading q={q0} />
      {q.data && <DataTable caption="구직중 근로자" rows={q.data} cols={[{ label: '이름', render: (r: any) => r.name }, { label: '장애', render: (r: any) => `${lb(r.disabilityType)} ${lb(r.disabilityDegree)}` },
        { label: '희망 직무', render: (r: any) => (r.desiredJobFields ?? '').split(',').map((x: string) => L[x] ?? x).join(', ') }, { label: '자기소개', render: (r: any) => r.introduction }]} />}
      <Section title="전체 근로자 (대리 구직 등록)">
        {w.data && <DataTable caption="전체 근로자" rows={w.data} cols={[{ label: '이름', render: (r: any) => r.name }, { label: '재직', render: (r: any) => r.companyName ?? '-' },
          { label: '구직', render: (r: any) => <StatusChip value={r.jobSeekingStatus} /> },
          { label: '', render: (r: any) => !r.companyName && r.jobSeekingStatus !== 'SEEKING' && <Button size="small" onClick={() => a.run(() => post(`/resumes/${r.id}/job-seeking`, { seeking: true }), `${r.name}님을 구직 등록했습니다.`)}>구직 등록</Button> }]} />}
        <Status msg={a.msg} />
      </Section>
    </Box>
  )
}

function Companies() {
  const [mine, setMine] = useState(true)
  const q = useQ<any[]>(['companies', mine], '/companies', { mine })
  return (
    <Box>
      <PageTitle>기업</PageTitle>
      <FormControlLabel control={<Checkbox checked={mine} onChange={(e) => setMine(e.target.checked)} />} label="내 담당 기업만" />
      <Loading q={q} />
      {q.data && <DataTable caption="기업 목록" rows={q.data} cols={[{ label: '기업명', render: (r: any) => r.name }, { label: '업종', render: (r: any) => r.industry },
        { label: '담당 매니저', render: (r: any) => r.managerName ?? '미지정' }, { label: '재직 근로자', render: (r: any) => r.activeWorkers }]} />}
    </Box>
  )
}

// ---------------- Postings ----------------
const FIELDS = ['DATA_LABELING', 'DOCUMENT_ENTRY', 'CONTENT_MONITORING', 'DESIGN', 'VIDEO_EDITING', 'CONTENT_WRITING', 'CUSTOMER_SUPPORT', 'RESEARCH', 'OTHER']

function Postings() {
  const { me } = useAuth()
  const nav = useNavigate()
  const isVM = me?.role === 'VDREAM_MANAGER'
  const [status, setStatus] = useState('')
  const [mine, setMine] = useState(false)
  const [company, setCompany] = useState('')
  const [author, setAuthor] = useState('')
  const companies = useQ<any[]>(['companies-all'], '/companies', undefined, { enabled: isVM })
  const q = useQ<any[]>(['postings', status, mine, company, author], '/job-postings', { status: status || undefined, mine: mine || undefined, company_id: company || undefined, author_type: author || undefined })
  return (
    <Box>
      <PageTitle action={<Button variant="contained" onClick={() => nav('/admin/postings/new')}>공고 작성</Button>}>채용 공고</PageTitle>
      <TextField select size="small" label="상태" value={status} onChange={(e) => setStatus(e.target.value)} sx={{ mb: 2, minWidth: 160 }}>
        <MenuItem value="">전체</MenuItem>{['DRAFT', 'PENDING_APPROVAL', 'REJECTED', 'PUBLISHED', 'CLOSED'].map((x) => <MenuItem key={x} value={x}>{L[x]}</MenuItem>)}
      </TextField>
      {isVM && <>
        <TextField select size="small" label="기업" value={company} onChange={(e) => setCompany(e.target.value)} sx={{ mb: 2, ml: 2, minWidth: 160 }}><MenuItem value="">전체</MenuItem>{companies.data?.map((c) => <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>)}</TextField>
        <TextField select size="small" label="작성자" value={author} onChange={(e) => setAuthor(e.target.value)} sx={{ mb: 2, ml: 2, minWidth: 120 }}><MenuItem value="">전체</MenuItem><MenuItem value="COMPANY">기업</MenuItem><MenuItem value="VDREAM">브이드림</MenuItem></TextField>
        <FormControlLabel sx={{ ml: 1 }} control={<Checkbox checked={mine} onChange={(e) => setMine(e.target.checked)} />} label="내 담당 기업만" />
      </>}
      <Loading q={q} />
      {q.data && <DataTable caption="공고 목록" rows={q.data} onRow={(r: any) => nav(`/admin/postings/${r.id}`)} cols={[
        { label: '제목', render: (r: any) => r.title }, ...(me?.role === 'VDREAM_MANAGER' ? [{ label: '기업', render: (r: any) => r.companyName }] : []),
        { label: '직무', render: (r: any) => lb(r.jobField) }, { label: '작성', render: (r: any) => lb(r.authorType) },
        { label: '지원자', render: (r: any) => r.applicantCount }, { label: '마감 예정', render: (r: any) => r.deadlineDate ?? '-' },
        { label: '상태', render: (r: any) => <StatusChip value={r.status} /> }]} />}
    </Box>
  )
}

const EMPTY_POSTING = { title: '', jobField: 'DATA_LABELING', mainDuties: '', workType: 'REMOTE', workLocation: '', workDays: 'MON,TUE,WED,THU,FRI', workStartTime: '09:00', workEndTime: '18:00',
  weeklyWorkHours: 40, salaryType: 'MONTHLY', salaryAmount: 2200000, benefits: '', equipmentSupport: '', requirements: '', expectedStartDate: ymd(), contractType: 'INDEFINITE',
  headcount: 1, description: '', deadlineDate: '' }

function PostingForm() {
  const { id } = useParams()
  const { me } = useAuth()
  const nav = useNavigate()
  const isVM = me?.role === 'VDREAM_MANAGER'
  const existing = useQ<any>(['posting', id], `/job-postings/${id}`, undefined, { enabled: !!id })
  const companies = useQ<any[]>(['companies-all'], '/companies', undefined, { enabled: isVM })
  const [f, setF] = useState<any>({ ...EMPTY_POSTING, companyId: '' })
  const a = useAct()
  useEffect(() => { if (existing.data) setF({ ...existing.data }) }, [existing.data])
  const set = (k: string) => (e: any) => setF({ ...f, [k]: e.target.value })
  const save = () => {
    const body: any = { companyId: f.companyId || null }
    Object.keys(EMPTY_POSTING).forEach((k) => { body[k] = f[k] === '' ? null : f[k] })
    body.weeklyWorkHours = Number(f.weeklyWorkHours); body.salaryAmount = Number(f.salaryAmount); body.headcount = Number(f.headcount)
    return a.run(() => (id ? put(`/job-postings/${id}`, body) : post('/job-postings', body)), '저장했습니다.').then((r) => r && nav(`/admin/postings/${r.id}`))
  }
  return (
    <Box>
      <BackLink />
      <PageTitle>{id ? '공고 수정' : '공고 작성'}</PageTitle>
      <Stack spacing={2} sx={{ maxWidth: 720 }}>
        {isVM && !id && <TextField select label="기업" value={f.companyId} onChange={set('companyId')}>{companies.data?.map((c) => <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>)}</TextField>}
        <TextField label="제목" value={f.title} onChange={set('title')} />
        <TextField select label="직무 분야" value={f.jobField} onChange={set('jobField')}>{FIELDS.map((x) => <MenuItem key={x} value={x}>{L[x]}</MenuItem>)}</TextField>
        <TextField label="주요 업무 내용" multiline minRows={3} value={f.mainDuties} onChange={set('mainDuties')} />
        <Stack direction="row" gap={2} flexWrap="wrap">
          <TextField select label="근무 형태" value={f.workType} onChange={set('workType')} sx={{ minWidth: 140 }}>{['REMOTE', 'HYBRID'].map((x) => <MenuItem key={x} value={x}>{L[x]}</MenuItem>)}</TextField>
          {f.workType === 'HYBRID' && <TextField label="출근 장소" value={f.workLocation ?? ''} onChange={set('workLocation')} />}
          <TextField label="근무 요일" value={f.workDays} onChange={set('workDays')} />
          <TextField type="time" label="시작" value={f.workStartTime} onChange={set('workStartTime')} InputLabelProps={{ shrink: true }} />
          <TextField type="time" label="종료" value={f.workEndTime} onChange={set('workEndTime')} InputLabelProps={{ shrink: true }} />
          <TextField type="number" label="주 소정근로시간" value={f.weeklyWorkHours} onChange={set('weeklyWorkHours')} />
        </Stack>
        <Stack direction="row" gap={2} flexWrap="wrap">
          <TextField select label="급여 형태" value={f.salaryType} onChange={set('salaryType')} sx={{ minWidth: 140 }}>{['MONTHLY', 'HOURLY'].map((x) => <MenuItem key={x} value={x}>{L[x]}</MenuItem>)}</TextField>
          <TextField type="number" label="급여(원)" value={f.salaryAmount} onChange={set('salaryAmount')} />
          <TextField select label="계약 형태" value={f.contractType} onChange={set('contractType')} sx={{ minWidth: 180 }}>{['FIXED_TERM', 'INDEFINITE'].map((x) => <MenuItem key={x} value={x}>{L[x]}</MenuItem>)}</TextField>
          <TextField type="number" label="모집 인원" value={f.headcount} onChange={set('headcount')} />
        </Stack>
        <Stack direction="row" gap={2}>
          <TextField type="date" label="근무 시작 예정일" value={f.expectedStartDate ?? ''} onChange={set('expectedStartDate')} InputLabelProps={{ shrink: true }} />
          <TextField type="date" label="마감 예정일" value={f.deadlineDate ?? ''} onChange={set('deadlineDate')} InputLabelProps={{ shrink: true }} />
        </Stack>
        <TextField label="지원 장비" value={f.equipmentSupport ?? ''} onChange={set('equipmentSupport')} />
        <TextField label="복리후생" value={f.benefits ?? ''} onChange={set('benefits')} />
        <TextField label="필요 역량·우대 사항" value={f.requirements ?? ''} onChange={set('requirements')} />
        <TextField label="상세 설명" multiline minRows={3} value={f.description ?? ''} onChange={set('description')} />
        <Button variant="contained" onClick={save} disabled={a.busy}>저장 (작성중)</Button>
        <Status msg={a.msg} />
      </Stack>
    </Box>
  )
}

function PostingDetail() {
  const { id } = useParams()
  const { me } = useAuth()
  const nav = useNavigate()
  const isVM = me?.role === 'VDREAM_MANAGER'
  const q = useQ<any>(['posting', id], `/job-postings/${id}`)
  const apps = useQ<any[]>(['posting-apps', id], `/job-postings/${id}/applications`)
  const a = useAct()
  const [reject, setReject] = useState(false)
  const p = q.data
  const act = (path: string, done: string, body?: object) => a.run(() => post(`/job-postings/${id}/${path}`, body), done)
  return (
    <Box>
      <BackLink />
      <Loading q={q} />
      {p && (
        <>
          <PageTitle action={<StatusChip value={p.status} />}>{p.title}</PageTitle>
          <Typography color="text.secondary" sx={{ mb: 2 }}>{p.companyName} · {lb(p.jobField)} · {lb(p.workType)} · 주 {p.weeklyWorkHours}시간 · {lb(p.salaryType)} {p.salaryAmount.toLocaleString()}원 · 작성 {lb(p.authorType)}</Typography>
          {p.rejectReason && p.status === 'REJECTED' && <Alert severity="warning" sx={{ mb: 2 }}>반려 사유: {p.rejectReason}</Alert>}
          <Stack direction="row" gap={1} flexWrap="wrap" sx={{ mb: 2 }}>
            {['DRAFT', 'REJECTED', 'PUBLISHED'].includes(p.status) && <Button variant="outlined" onClick={() => nav(`/admin/postings/${id}/edit`)}>수정</Button>}
            {!isVM && ['DRAFT', 'REJECTED'].includes(p.status) && <Button variant="contained" onClick={() => act('submit', '승인을 요청했습니다.')}>승인 요청</Button>}
            {isVM && p.status === 'PENDING_APPROVAL' && <><Button variant="contained" onClick={() => act('approve', '승인했습니다. 게시되었습니다.')}>승인</Button><Button color="error" onClick={() => setReject(true)}>반려</Button></>}
            {isVM && p.status === 'DRAFT' && p.authorType === 'VDREAM' && <Button variant="contained" onClick={() => act('publish', '게시했습니다.')}>즉시 게시</Button>}
            {p.status === 'PUBLISHED' && <Button onClick={() => act('close', '마감했습니다.')}>마감</Button>}
            {['DRAFT', 'REJECTED'].includes(p.status) && <Button color="error" onClick={() => a.run(() => del(`/job-postings/${id}`)).then(() => nav('/admin/postings'))}>삭제</Button>}
          </Stack>
          <Status msg={a.msg} />
          <Section title={`지원자 ${apps.data?.length ?? 0}명`}>
            {apps.data && <DataTable caption="지원자" rows={apps.data} cols={[
              { label: '이름', render: (r: any) => r.workerName }, { label: '장애', render: (r: any) => `${lb(r.disabilityType)} ${lb(r.disabilityDegree)}` },
              { label: '지원일', render: (r: any) => kst(r.appliedAt) }, { label: '상태', render: (r: any) => <StatusChip value={r.status} /> },
              { label: '진행', render: (r: any) => <ApplicationActions app={r} /> }]} />}
          </Section>
        </>
      )}
      <PromptDialog open={reject} title="공고 반려" label="반려 사유" required onClose={() => setReject(false)} onOk={(v) => act('reject', '반려했습니다.', { reason: v })} okText="반려" />
    </Box>
  )
}

function ApplicationActions({ app }: { app: any }) {
  const a = useAct()
  const [iv, setIv] = useState(false)
  const [hire, setHire] = useState(false)
  const [f, setF] = useState({ interviewAt: '', interviewMethod: 'VIDEO', interviewLocation: '', interviewNote: '' })
  const [start, setStart] = useState(ymd())
  const go = (p: string, body: object, done: string) => a.run(() => post(`/applications/${app.id}/${p}`, body), done)
  return (
    <Stack direction="row" gap={0.5} flexWrap="wrap" alignItems="center">
      <Button size="small" component={RLink} to={`/admin/resume/${app.workerId}`}>이력서</Button>
      {app.status === 'APPLIED' && <><Button size="small" onClick={() => go('document', { passed: true }, '서류 합격 처리했습니다.')}>서류 합격</Button><Button size="small" color="error" onClick={() => go('document', { passed: false }, '서류 불합격 처리했습니다.')}>불합격</Button></>}
      {['DOCUMENT_PASSED', 'INTERVIEW_SCHEDULED'].includes(app.status) && <Button size="small" onClick={() => setIv(true)}>면접 일정</Button>}
      {app.status === 'INTERVIEW_SCHEDULED' && <><Button size="small" onClick={() => go('final', { passed: true }, '최종 합격 처리했습니다.')}>최종 합격</Button><Button size="small" color="error" onClick={() => go('final', { passed: false }, '불합격 처리했습니다.')}>불합격</Button></>}
      {(app.status === 'PASSED' || app.status === 'HIRED') && <Button size="small" variant="contained" onClick={() => setHire(true)}>{app.status === 'HIRED' ? '출근일 변경' : '출근일 확정'}</Button>}
      {a.msg && <Typography variant="body2" role="status" color={a.msg.ok ? 'success.main' : 'error.main'}>{a.msg.text}</Typography>}
      <Dialog open={iv} onClose={() => setIv(false)}>
        <DialogTitle>면접 일정</DialogTitle>
        <DialogContent><Stack spacing={2} sx={{ mt: 1 }}>
          <TextField type="datetime-local" label="일시" value={f.interviewAt} onChange={(e) => setF({ ...f, interviewAt: e.target.value })} InputLabelProps={{ shrink: true }} />
          <TextField select label="방식" value={f.interviewMethod} onChange={(e) => setF({ ...f, interviewMethod: e.target.value })}>{['VIDEO', 'VISIT'].map((x) => <MenuItem key={x} value={x}>{L[x]}</MenuItem>)}</TextField>
          <TextField label="장소 또는 화상 링크" value={f.interviewLocation} onChange={(e) => setF({ ...f, interviewLocation: e.target.value })} />
          <TextField label="안내 사항" value={f.interviewNote} onChange={(e) => setF({ ...f, interviewNote: e.target.value })} />
        </Stack></DialogContent>
        <DialogActions><Button onClick={() => setIv(false)}>닫기</Button><Button variant="contained" disabled={!f.interviewAt} onClick={() => { setIv(false); go('interview', f, '면접 일정을 안내했습니다.') }}>저장</Button></DialogActions>
      </Dialog>
      <Dialog open={hire} onClose={() => setHire(false)}>
        <DialogTitle>출근 시작일</DialogTitle>
        <DialogContent><TextField type="date" value={start} onChange={(e) => setStart(e.target.value)} sx={{ mt: 1 }} /><Typography variant="body2" sx={{ mt: 1 }}>확정하면 재직 기록과 근로계약이 만들어지고 구직 등록이 해제됩니다.</Typography></DialogContent>
        <DialogActions><Button onClick={() => setHire(false)}>닫기</Button><Button variant="contained" onClick={() => { setHire(false); go('hire', { startDate: start }, '출근 시작일을 확정했습니다.') }}>확정</Button></DialogActions>
      </Dialog>
    </Stack>
  )
}

function ResumePage() {
  const { id } = useParams()
  return <Box><BackLink /><PageTitle>지원자 이력서</PageTitle><ResumeView workerId={Number(id)} /></Box>
}

// ---------------- Attendance ----------------
function Attendance() {
  const { me } = useAuth()
  const [month, setMonth] = useState(ym())
  const [emp, setEmp] = useState<number | null>(null)
  const q = useQ<any[]>(['att', month], '/attendance', { month })
  const detail = useQ<any[]>(['att-detail', month, emp], '/attendance', { month, employment_id: emp }, { enabled: !!emp })
  const [fix, setFix] = useState<any>(null)
  const a = useAct()
  return (
    <Box>
      <PageTitle action={<Button variant="outlined" onClick={() => download('/attendance/export.xlsx', { month }, `근태_${month}.xlsx`)}>엑셀 내려받기</Button>}>근태</PageTitle>
      <MonthPicker value={month} onChange={setMonth} />
      <Loading q={q} />
      {q.data && <Box sx={{ mt: 2 }}><DataTable caption="월별 근태 집계" rows={q.data} onRow={(r: any) => setEmp(r.employmentId)} cols={[
        { label: '근로자', render: (r: any) => r.workerName }, { label: '기업', render: (r: any) => r.companyName }, { label: '근무일', render: (r: any) => r.summary.workdays },
        { label: '출근', render: (r: any) => r.summary.attended }, { label: '지각', render: (r: any) => r.summary.late }, { label: '조퇴', render: (r: any) => r.summary.earlyLeave },
        { label: '결근', render: (r: any) => r.summary.absent }, { label: '휴가', render: (r: any) => r.summary.leaveDays }]} /></Box>}
      {emp && detail.data?.[0] && (
        <Section title={`${detail.data[0].workerName} 일별 근태`}>
          <DataTable caption="일별 근태" rows={detail.data[0].days.filter((d: any) => d.isWorkday || d.record)} cols={[
            { label: '날짜', render: (d: any) => d.date }, { label: '상태', render: (d: any) => d.status ? <StatusChip value={d.status} label={`${lb(d.status)}${d.computed ? ' (계산)' : ''}`} /> : '-' },
            { label: '출근', render: (d: any) => kst(d.record?.checkInAt, false) }, { label: '퇴근', render: (d: any) => kst(d.record?.checkOutAt, false) },
            { label: '사유·정정', render: (d: any) => d.record?.correctionNote ?? d.record?.workerLateReason ?? '' },
            { label: '', render: (d: any) => me?.role === 'COMPANY_MANAGER' && <Button size="small" onClick={() => setFix({ date: d.date, status: d.status ?? 'NORMAL', checkIn: '', checkOut: '', note: '' })}>정정</Button> }]} />
        </Section>
      )}
      <Status msg={a.msg} />
      <Dialog open={!!fix} onClose={() => setFix(null)}>
        <DialogTitle>{fix?.date} 근태 정정</DialogTitle>
        <DialogContent><Stack spacing={2} sx={{ mt: 1 }}>
          <TextField type="time" label="출근" value={fix?.checkIn ?? ''} onChange={(e) => setFix({ ...fix, checkIn: e.target.value })} InputLabelProps={{ shrink: true }} />
          <TextField type="time" label="퇴근" value={fix?.checkOut ?? ''} onChange={(e) => setFix({ ...fix, checkOut: e.target.value })} InputLabelProps={{ shrink: true }} />
          <TextField select label="상태" value={fix?.status ?? ''} onChange={(e) => setFix({ ...fix, status: e.target.value })}>{['NORMAL', 'LATE', 'EARLY_LEAVE', 'LATE_EARLY_LEAVE', 'ABSENT', 'ON_LEAVE'].map((x) => <MenuItem key={x} value={x}>{L[x]}</MenuItem>)}</TextField>
          <TextField label="정정 사유" value={fix?.note ?? ''} onChange={(e) => setFix({ ...fix, note: e.target.value })} />
        </Stack></DialogContent>
        <DialogActions><Button onClick={() => setFix(null)}>닫기</Button><Button variant="contained" disabled={!fix?.note} onClick={() => {
          const b = { employmentId: emp, workDate: fix.date, checkIn: fix.checkIn || null, checkOut: fix.checkOut || null, status: fix.status, note: fix.note }
          setFix(null); a.run(() => put('/attendance/correct', b), '근태를 정정했습니다.')
        }}>저장</Button></DialogActions>
      </Dialog>
    </Box>
  )
}

function Leaves() {
  const { me } = useAuth()
  const isCM = me?.role === 'COMPANY_MANAGER'
  const q = useQ<any>(['leaves'], '/leaves')
  const a = useAct()
  const [rej, setRej] = useState<number | null>(null)
  return (
    <Box>
      <PageTitle>휴가</PageTitle>
      <Status msg={a.msg} />
      <Loading q={q} />
      {q.data && (
        <>
          <Section title="휴가 신청">
            <DataTable caption="휴가 신청" rows={q.data.requests} cols={[{ label: '근로자', render: (r: any) => r.workerName }, { label: '종류', render: (r: any) => lb(r.leaveType) },
              { label: '기간', render: (r: any) => `${r.startDate}${r.endDate !== r.startDate ? ` ~ ${r.endDate}` : ''}` }, { label: '일수', render: (r: any) => r.days },
              { label: '사유', render: (r: any) => r.reason }, { label: '상태', render: (r: any) => <StatusChip value={r.status} /> },
              { label: '', render: (r: any) => isCM && (r.status === 'PENDING' ? <><Button size="small" onClick={() => a.run(() => post(`/leaves/${r.id}/approve`), '승인했습니다.')}>승인</Button><Button size="small" color="error" onClick={() => setRej(r.id)}>반려</Button></>
                : r.status === 'APPROVED' ? <Button size="small" onClick={() => a.run(() => post(`/leaves/${r.id}/cancel`, {}), '승인을 취소했습니다.')}>승인 취소</Button> : null) }]} />
          </Section>
          <Section title="연차 현황">
            <DataTable caption="연차 현황" rows={q.data.balances} cols={[{ label: '근로자', render: (r: any) => r.workerName }, { label: '부여', render: (r: any) => r.granted },
              { label: '사용', render: (r: any) => r.used }, { label: '잔여', render: (r: any) => r.remaining },
              { label: '', render: (r: any) => isCM && <Button size="small" onClick={() => { const v = prompt('부여 연차일수', String(r.granted)); if (v) a.run(() => put('/leave-grants', { employmentId: r.employmentId, year: r.year, grantedDays: Number(v) }), '연차를 저장했습니다.') }}>부여일수 수정</Button> }]} />
          </Section>
        </>
      )}
      <PromptDialog open={!!rej} title="휴가 반려" label="반려 사유" onClose={() => setRej(null)} onOk={(v) => a.run(() => post(`/leaves/${rej}/reject`, { note: v }), '반려했습니다.')} okText="반려" />
    </Box>
  )
}

// ---------------- Tasks ----------------
function Tasks() {
  const { me } = useAuth()
  const isCM = me?.role === 'COMPANY_MANAGER'
  const nav = useNavigate()
  const [status, setStatus] = useState('')
  const q = useQ<any[]>(['tasks-admin', status], '/tasks', { status: status || undefined })
  const emps = useQ<any[]>(['emps-active'], '/employments', undefined, { enabled: isCM })
  const a = useAct()
  const [open, setOpen] = useState(false)
  const [f, setF] = useState({ employmentId: '', title: '', description: '', priority: 'NORMAL', dueDate: '' })
  return (
    <Box>
      <PageTitle action={isCM && <Button variant="contained" onClick={() => setOpen(true)}>업무 배정</Button>}>업무</PageTitle>
      <TextField select size="small" label="상태" value={status} onChange={(e) => setStatus(e.target.value)} sx={{ mb: 2, minWidth: 140 }}>
        <MenuItem value="">전체</MenuItem>{['ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'].map((x) => <MenuItem key={x} value={x}>{L[x]}</MenuItem>)}
      </TextField>
      <Status msg={a.msg} />
      <Loading q={q} />
      {q.data && <DataTable caption="업무 목록" rows={q.data} onRow={(r: any) => nav(`/admin/tasks/${r.id}`)} cols={[
        { label: '업무', render: (r: any) => r.title }, { label: '근로자', render: (r: any) => r.workerName }, { label: '우선순위', render: (r: any) => lb(r.priority) },
        { label: '기한', render: (r: any) => <>{r.dueDate ?? '-'} {r.overdue && <StatusChip value="ABSENT" label="기한 초과" />}</> },
        { label: '누적', render: (r: any) => hm(r.totalMinutes) }, { label: '상태', render: (r: any) => <><StatusChip value={r.status} />{r.employmentEnded && <Chip size="small" label="재직 종료" sx={{ ml: 0.5 }} />}</> }]} />}
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth>
        <DialogTitle>업무 배정</DialogTitle>
        <DialogContent><Stack spacing={2} sx={{ mt: 1 }}>
          <TextField select label="근로자" value={f.employmentId} onChange={(e) => setF({ ...f, employmentId: e.target.value })}>{emps.data?.map((e) => <MenuItem key={e.id} value={e.id}>{e.workerName} ({lb(e.status)})</MenuItem>)}</TextField>
          <TextField label="제목" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} />
          <TextField label="내용" multiline minRows={3} value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} />
          <TextField select label="우선순위" value={f.priority} onChange={(e) => setF({ ...f, priority: e.target.value })}>{['LOW', 'NORMAL', 'HIGH'].map((x) => <MenuItem key={x} value={x}>{L[x] ?? '보통'}</MenuItem>)}</TextField>
          <TextField type="date" label="기한" value={f.dueDate} onChange={(e) => setF({ ...f, dueDate: e.target.value })} InputLabelProps={{ shrink: true }} />
        </Stack></DialogContent>
        <DialogActions><Button onClick={() => setOpen(false)}>닫기</Button><Button variant="contained" disabled={!f.employmentId || !f.title} onClick={() => {
          setOpen(false); a.run(() => post('/tasks', { ...f, employmentId: Number(f.employmentId), dueDate: f.dueDate || null }), '업무를 배정했습니다.')
        }}>배정</Button></DialogActions>
      </Dialog>
    </Box>
  )
}

function TaskDetail() {
  const { id } = useParams()
  const { me } = useAuth()
  const isCM = me?.role === 'COMPANY_MANAGER'
  const q = useQ<any>(['task', id], `/tasks/${id}`)
  const a = useAct()
  const [dlg, setDlg] = useState<'cancel' | 'reopen' | null>(null)
  const [edit, setEdit] = useState<any>(null)
  const t = q.data
  return (
    <Box>
      <BackLink />
      <Loading q={q} />
      {t && (
        <>
          <PageTitle action={<StatusChip value={t.status} />}>{t.title}</PageTitle>
          <Typography color="text.secondary">{t.workerName} · 우선순위 {lb(t.priority)} · 기한 {t.dueDate ?? '없음'} · 누적 {hm(t.totalMinutes)}</Typography>
          <Typography sx={{ whiteSpace: 'pre-wrap', my: 2 }}>{t.description}</Typography>
          {t.completionNote && <Alert severity="success">완료 메모: {t.completionNote}</Alert>}
          {isCM && <Stack direction="row" gap={1} sx={{ my: 2 }}>
            {t.status !== 'COMPLETED' && t.status !== 'CANCELLED' && <Button variant="outlined" onClick={() => setEdit({ title: t.title, description: t.description ?? '', priority: t.priority, dueDate: t.dueDate ?? '' })}>수정</Button>}
            {t.status !== 'COMPLETED' && t.status !== 'CANCELLED' && <Button color="error" onClick={() => setDlg('cancel')}>취소</Button>}
            {t.status === 'COMPLETED' && <Button onClick={() => setDlg('reopen')}>재오픈</Button>}
          </Stack>}
          <Status msg={a.msg} />
          <Section title="업무일지 기록">{t.logEntries.length ? t.logEntries.map((e: any) => <Typography key={e.id}>{e.workDate} · {hm(e.minutes)} · {e.content}</Typography>) : <Empty />}</Section>
        </>
      )}
      <Dialog open={!!edit} onClose={() => setEdit(null)} fullWidth>
        <DialogTitle>업무 수정</DialogTitle>
        <DialogContent>{edit && <Stack spacing={2} sx={{ mt: 1 }}>
          <TextField label="제목" value={edit.title} onChange={(e) => setEdit({ ...edit, title: e.target.value })} />
          <TextField label="내용" multiline minRows={3} value={edit.description} onChange={(e) => setEdit({ ...edit, description: e.target.value })} />
          <TextField select label="우선순위" value={edit.priority} onChange={(e) => setEdit({ ...edit, priority: e.target.value })}>{[['LOW', '낮음'], ['NORMAL', '보통'], ['HIGH', '높음']].map(([v, l]) => <MenuItem key={v} value={v}>{l}</MenuItem>)}</TextField>
          <TextField type="date" label="기한" value={edit.dueDate} onChange={(e) => setEdit({ ...edit, dueDate: e.target.value })} InputLabelProps={{ shrink: true }} />
        </Stack>}</DialogContent>
        <DialogActions><Button onClick={() => setEdit(null)}>닫기</Button><Button variant="contained" disabled={!edit?.title} onClick={() => {
          const b = { employmentId: t.employmentId, ...edit, dueDate: edit.dueDate || null }; setEdit(null); a.run(() => put(`/tasks/${id}`, b), '업무를 수정했습니다. 근로자에게 알렸어요.')
        }}>저장</Button></DialogActions>
      </Dialog>
      <PromptDialog open={!!dlg} title={dlg === 'cancel' ? '업무 취소' : '업무 재오픈'} label="사유" onClose={() => setDlg(null)} onOk={(v) => a.run(() => post(`/tasks/${id}/${dlg}`, { note: v }), dlg === 'cancel' ? '취소했습니다.' : '재오픈했습니다.')} />
    </Box>
  )
}

// ---------------- Work logs ----------------
function WorkLogs() {
  const nav = useNavigate()
  const [month, setMonth] = useState(ym())
  const [status, setStatus] = useState('SUBMITTED')
  const [tab, setTab] = useState(0)
  const q = useQ<any[]>(['wl', month, status], '/work-logs', { month, status: status || undefined })
  const stats = useQ<any[]>(['wl-stats', month], '/work-logs/stats', { month })
  const missing = useQ<any[]>(['wl-missing', month], '/work-logs/missing', { month })
  return (
    <Box>
      <PageTitle action={<Button variant="outlined" onClick={() => download('/work-logs/export.xlsx', { month }, `업무일지_${month}.xlsx`)}>엑셀 내려받기</Button>}>업무일지</PageTitle>
      <Stack direction="row" gap={2} sx={{ mb: 2 }}>
        <MonthPicker value={month} onChange={setMonth} />
        {tab === 0 && <TextField select size="small" label="상태" value={status} onChange={(e) => setStatus(e.target.value)} sx={{ minWidth: 140 }}>
          <MenuItem value="">전체</MenuItem>{['SUBMITTED', 'CONFIRMED', 'RETURNED'].map((x) => <MenuItem key={x} value={x}>{L[x]}</MenuItem>)}</TextField>}
      </Stack>
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}><Tab label="목록" /><Tab label="월별 통계" /><Tab label={`미제출 (${missing.data?.reduce((s, m) => s + m.dates.length, 0) ?? 0})`} /></Tabs>
      {tab === 0 && <><Loading q={q} />{q.data && <DataTable caption="업무일지 목록" rows={q.data} onRow={(r: any) => nav(`/admin/work-logs/${r.id}`)} cols={[
        { label: '근무일', render: (r: any) => r.workDate }, { label: '근로자', render: (r: any) => r.workerName }, { label: '항목', render: (r: any) => r.entryCount },
        { label: '소요', render: (r: any) => hm(r.totalMinutes) }, { label: '요약', render: (r: any) => r.summary }, { label: '상태', render: (r: any) => <StatusChip value={r.status} /> }]} />}</>}
      {tab === 1 && stats.data && (
        <>
          <Box sx={{ height: 260, mb: 2 }} role="img" aria-label="근로자별 업무일지 제출률 막대 그래프">
            <ResponsiveContainer><BarChart data={stats.data}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="workerName" /><YAxis unit="%" /><Tooltip />
              <Bar dataKey="submitRate" name="제출률(%)" fill={tokens.mint[500]} /></BarChart></ResponsiveContainer>
          </Box>
          <DataTable caption="월별 업무 통계" rows={stats.data} cols={[{ label: '근로자', render: (r: any) => r.workerName }, { label: '출근일', render: (r: any) => r.attended },
            { label: '제출', render: (r: any) => r.submitted }, { label: '확인', render: (r: any) => r.confirmed }, { label: '제출률', render: (r: any) => `${r.submitRate}%` },
            { label: '총 소요', render: (r: any) => hm(r.totalMinutes) }, { label: '업무 상위 5', render: (r: any) => r.topTasks.map((t: any) => `${t.title}(${hm(t.minutes)})`).join(', ') }]} />
        </>
      )}
      {tab === 2 && missing.data && <DataTable caption="업무일지 미제출" rows={missing.data} cols={[{ label: '근로자', render: (r: any) => r.workerName }, { label: '미제출 날짜', render: (r: any) => r.dates.join(', ') }]} />}
    </Box>
  )
}

function WorkLogDetail() {
  const { id } = useParams()
  const { me } = useAuth()
  const isCM = me?.role === 'COMPANY_MANAGER'
  const q = useQ<any>(['wl-one', id], `/work-logs/${id}`)
  const a = useAct()
  const [comment, setComment] = useState('')
  const w = q.data
  return (
    <Box>
      <BackLink />
      <Loading q={q} />
      {w && (
        <>
          <PageTitle action={<StatusChip value={w.status} />}>{w.workerName} · {w.workDate} 업무일지</PageTitle>
          <Typography sx={{ mb: 1 }}><b>요약</b> {w.summary}</Typography>
          <Typography sx={{ mb: 2 }}><b>특이사항</b> {w.issues ?? '-'}</Typography>
          <DataTable caption="업무일지 항목" rows={w.entries} cols={[{ label: '업무', render: (e: any) => <>{e.title}{e.taskId && <Chip size="small" label="배정 업무" sx={{ ml: 1 }} />}</> },
            { label: '수행 내용', render: (e: any) => e.content }, { label: '소요', render: (e: any) => hm(e.minutes) }]} />
          <Typography sx={{ mt: 1 }}>합계 {hm(w.totalMinutes)} · 제출 {kst(w.submittedAt)}</Typography>
          {!!w.files.length && <Section title="산출물">{w.files.map((f: any) => <Button key={f.id} onClick={() => openFile(f.id)}>{f.name}</Button>)}</Section>}
          {w.reviewComment && <Alert severity="info" sx={{ my: 2 }}>검토 의견: {w.reviewComment}</Alert>}
          {isCM && w.status === 'SUBMITTED' && (
            <Stack spacing={1.5} sx={{ maxWidth: 560, mt: 2 }}>
              <TextField label="의견 (보완 요청 시 필수)" multiline value={comment} onChange={(e) => setComment(e.target.value)} />
              <Stack direction="row" gap={1}>
                <Button variant="contained" onClick={() => a.run(() => post(`/work-logs/${id}/confirm`, { comment }), '확인했습니다.')}>확인</Button>
                <Button color="warning" variant="outlined" disabled={!comment} onClick={() => a.run(() => post(`/work-logs/${id}/return`, { comment }), '보완을 요청했습니다.')}>보완 요청</Button>
              </Stack>
            </Stack>
          )}
          {isCM && w.status === 'CONFIRMED' && <Button sx={{ mt: 2 }} onClick={() => a.run(() => post(`/work-logs/${id}/unconfirm`), '확인을 취소했습니다.')}>확인 취소</Button>}
          <Status msg={a.msg} />
        </>
      )}
    </Box>
  )
}

// ---------------- Counseling (VM) ----------------
function CounselingList({ workerId }: { workerId?: number }) {
  const [company, setCompany] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const companies = useQ<any[]>(['companies-all'], '/companies', undefined, { enabled: !workerId })
  const q = useQ<any[]>(['cnsl', workerId, company, from, to], '/counseling', { worker_id: workerId, company_id: company || undefined, from: from || undefined, to: to || undefined })
  const workers = useQ<any[]>(['all-workers'], '/workers')
  const a = useAct()
  const [open, setOpen] = useState(false)
  const blank = { workerId: workerId ?? '', method: 'PHONE', counseledAt: `${ymd()}T15:00`, topic: '', content: '', conditionScore: 3, followUp: '' }
  const [f, setF] = useState<any>(blank)
  const startEdit = (r: any) => { setF({ id: r.id, workerId: r.workerId, method: r.method, counseledAt: kstLocal(r.counseledAt), topic: r.topic, content: r.content, conditionScore: r.conditionScore, followUp: r.followUp ?? '' }); setOpen(true) }
  const chart = [...(q.data ?? [])].reverse().map((r) => ({ date: r.counseledAt.slice(5, 10), score: r.conditionScore }))
  return (
    <Box>
      {!workerId && <PageTitle action={<Button variant="contained" onClick={() => setOpen(true)}>상담보고서 작성</Button>}>상담보고서</PageTitle>}
      {workerId && <Button variant="contained" sx={{ mb: 2 }} onClick={() => { setF(blank); setOpen(true) }}>상담보고서 작성</Button>}
      {!workerId && (
        <Stack direction="row" gap={2} sx={{ mb: 2 }} flexWrap="wrap">
          <TextField size="small" select label="기업" value={company} onChange={(e) => setCompany(e.target.value)} sx={{ minWidth: 160 }}><MenuItem value="">전체</MenuItem>{companies.data?.map((c) => <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>)}</TextField>
          <TextField size="small" type="date" label="시작일" value={from} onChange={(e) => setFrom(e.target.value)} InputLabelProps={{ shrink: true }} />
          <TextField size="small" type="date" label="종료일" value={to} onChange={(e) => setTo(e.target.value)} InputLabelProps={{ shrink: true }} />
        </Stack>
      )}
      {workerId && chart.length > 1 && (
        <Box sx={{ height: 200, mb: 2 }} role="img" aria-label={`상태 점수 추이: ${chart.map((c) => `${c.date} ${c.score}점`).join(', ')}`}>
          <ResponsiveContainer><LineChart data={chart}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="date" /><YAxis domain={[1, 5]} /><Tooltip />
            <Line dataKey="score" name="상태 점수" stroke={tokens.mint[500]} strokeWidth={3} /></LineChart></ResponsiveContainer>
        </Box>
      )}
      <Status msg={a.msg} />
      <Loading q={q} />
      {q.data && <DataTable caption="상담보고서" rows={q.data} cols={[{ label: '일시', render: (r: any) => kst(r.counseledAt) }, { label: '근로자', render: (r: any) => r.workerName },
        { label: '기업', render: (r: any) => r.companyName ?? '-' }, { label: '방식', render: (r: any) => lb(r.method) }, { label: '주제', render: (r: any) => r.topic },
        { label: '점수', render: (r: any) => `${r.conditionScore}/5` }, { label: '내용', render: (r: any) => r.content }, { label: '후속 조치', render: (r: any) => r.followUp },
        { label: '', render: (r: any) => <><Button size="small" onClick={() => startEdit(r)}>수정</Button><Button size="small" color="error" onClick={() => { if (confirm('이 상담보고서를 삭제할까요?')) a.run(() => del(`/counseling/${r.id}`), '삭제했습니다.') }}>삭제</Button></> }]} />}
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth>
        <DialogTitle>{f.id ? '상담보고서 수정' : '상담보고서 작성'}</DialogTitle>
        <DialogContent><Stack spacing={2} sx={{ mt: 1 }}>
          {!workerId && !f.id && <TextField select label="근로자" value={f.workerId} onChange={(e) => setF({ ...f, workerId: e.target.value })}>{workers.data?.map((w) => <MenuItem key={w.id} value={w.id}>{w.name}{w.companyName ? ` (${w.companyName})` : ''}</MenuItem>)}</TextField>}
          <TextField type="datetime-local" label="상담 일시" value={f.counseledAt} onChange={(e) => setF({ ...f, counseledAt: e.target.value })} InputLabelProps={{ shrink: true }} />
          <TextField select label="방식" value={f.method} onChange={(e) => setF({ ...f, method: e.target.value })}>{['PHONE', 'VIDEO', 'VISIT', 'CHAT'].map((x) => <MenuItem key={x} value={x}>{L[x]}</MenuItem>)}</TextField>
          <TextField label="주제" value={f.topic} onChange={(e) => setF({ ...f, topic: e.target.value })} />
          <TextField label="내용" multiline minRows={3} value={f.content} onChange={(e) => setF({ ...f, content: e.target.value })} />
          <TextField select label="근로자 상태 점수" value={f.conditionScore} onChange={(e) => setF({ ...f, conditionScore: Number(e.target.value) })}>{[1, 2, 3, 4, 5].map((x) => <MenuItem key={x} value={x}>{x}점</MenuItem>)}</TextField>
          <TextField label="후속 조치" value={f.followUp} onChange={(e) => setF({ ...f, followUp: e.target.value })} />
        </Stack></DialogContent>
        <DialogActions><Button onClick={() => setOpen(false)}>닫기</Button><Button variant="contained" disabled={!f.workerId || !f.topic || !f.content} onClick={() => {
          setOpen(false)
          const b = { workerId: Number(f.workerId), method: f.method, counseledAt: f.counseledAt, topic: f.topic, content: f.content, conditionScore: f.conditionScore, followUp: f.followUp }
          a.run(() => (f.id ? put(`/counseling/${f.id}`, b) : post('/counseling', b)), '상담보고서를 저장했습니다.')
        }}>저장</Button></DialogActions>
      </Dialog>
    </Box>
  )
}

// ---------------- Resignations ----------------
function Resignations() {
  const { me } = useAuth()
  const isVM = me?.role === 'VDREAM_MANAGER'
  const q = useQ<any[]>(['resignations'], '/resignations')
  const a = useAct()
  const [rej, setRej] = useState<number | null>(null)
  const [appr, setAppr] = useState<{ id: number; date: string; note: string } | null>(null)
  return (
    <Box>
      <PageTitle>{isVM ? '퇴사 신청' : '퇴사 통보'}</PageTitle>
      <Dialog open={!!appr} onClose={() => setAppr(null)}>
        <DialogTitle>퇴사 승인</DialogTitle>
        <DialogContent><Stack spacing={2} sx={{ mt: 1 }}>
          <TextField type="date" label="확정 퇴사일" value={appr?.date ?? ''} onChange={(e) => setAppr(appr && { ...appr, date: e.target.value })} InputLabelProps={{ shrink: true }} helperText="근로자와 협의해 조정할 수 있습니다." />
          <TextField label="메모 (선택)" value={appr?.note ?? ''} onChange={(e) => setAppr(appr && { ...appr, note: e.target.value })} />
        </Stack></DialogContent>
        <DialogActions><Button onClick={() => setAppr(null)}>닫기</Button><Button variant="contained" onClick={() => {
          const v = appr!; setAppr(null); a.run(() => post(`/resignations/${v.id}/approve`, { confirmedDate: v.date, note: v.note || null }), '퇴사를 승인했습니다. 기업에 통보했어요.')
        }}>승인</Button></DialogActions>
      </Dialog>
      <Status msg={a.msg} />
      <Loading q={q} />
      {q.data && <DataTable caption="퇴사 신청" rows={q.data} cols={[{ label: '근로자', render: (r: any) => r.workerName }, { label: '기업', render: (r: any) => r.companyName },
        { label: '예정일', render: (r: any) => r.plannedDate }, { label: '확정일', render: (r: any) => r.confirmedDate ?? '-' }, { label: '사유', render: (r: any) => r.reason },
        { label: '상태', render: (r: any) => <StatusChip value={r.status} /> },
        { label: '', render: (r: any) => isVM && r.status === 'PENDING' && <><Button size="small" onClick={() => setAppr({ id: r.id, date: r.plannedDate, note: '' })}>승인</Button><Button size="small" color="error" onClick={() => setRej(r.id)}>반려</Button></> }]} />}
      <PromptDialog open={!!rej} title="퇴사 반려" label="사유" onClose={() => setRej(null)} onOk={(v) => a.run(() => post(`/resignations/${rej}/reject`, { note: v }), '반려했습니다.')} okText="반려" />
    </Box>
  )
}

// ---------------- Employment report (CM) ----------------
const kstLocal = (iso: string) => new Date(new Date(iso).getTime() + 9 * 3600e3).toISOString().slice(0, 16)

const REC_COLOR: Record<string, string> = { DOUBLE: 'success', SINGLE: 'success', EXCLUDED: 'error', NEEDS_REVIEW: 'warning' }

function defaultFrom() { const t = new Date(); t.setMonth(t.getMonth() - 2); return ym(t) }

function Report() {
  const sp = new URLSearchParams(useLocation().search)
  const nav = useNavigate()
  const [from, setFrom] = useState(sp.get('from') ?? defaultFrom())
  const [to, setTo] = useState(sp.get('to') ?? ym())
  const [go, setGo] = useState(!!sp.get('from'))
  const params = { from, to }
  const warn = useQ<any[]>(['rep-warn', from, to], '/reports/employment/warnings', params, { enabled: go })
  const rep = useQ<any>(['rep', from, to], '/reports/employment', params, { enabled: go })
  const r = rep.data
  return (
    <Box>
      <PageTitle>월간 장애인 고용 리포트</PageTitle>
      <Typography color="text.secondary" sx={{ mb: 2 }}>근태와 업무일지로 장애인 근로자의 월별 근로 실적을 정리합니다. 한국장애인고용공단 제출 증빙용 참고 자료입니다.</Typography>
      <Stack direction="row" gap={2} alignItems="center" sx={{ mb: 2 }} flexWrap="wrap">
        <MonthPicker value={from} onChange={(v) => { setFrom(v); setGo(false) }} />
        <Typography>~</Typography>
        <MonthPicker value={to} onChange={(v) => { setTo(v); setGo(false) }} />
        <Button variant="contained" onClick={() => setGo(true)}>리포트 만들기</Button>
        {r && <>
          <Button variant="outlined" onClick={() => download('/reports/employment.xlsx', params, '장애인고용리포트.xlsx')}>엑셀 내려받기</Button>
          <Button variant="outlined" onClick={() => nav(`/admin/reports/employment/print?from=${from}&to=${to}`)}>인쇄 / PDF</Button>
        </>}
      </Stack>
      <Loading q={rep} />
      {warn.data && !!warn.data.length && (
        <Section title={`데이터 경고 ${warn.data.length}건`}>
          <Typography color="text.secondary" sx={{ mb: 1 }}>증빙이 약한 부분입니다. 고친 뒤 리포트를 다시 만들면 반영됩니다.</Typography>
          <Box sx={{ maxHeight: 200, overflowY: 'auto' }}>
            {warn.data.map((w, i) => <Stack key={i} direction="row" alignItems="center" gap={1}><Typography>{w.month} · {w.worker} · {w.text}</Typography><Button size="small" onClick={() => nav(w.link)}>고치러 가기</Button></Stack>)}
          </Box>
        </Section>
      )}
      {r && r.months.map((m: any) => (
        <Section key={m.month} title={`${m.month}${m.inProgress ? ' (오늘까지 집계, 진행 중)' : ''}`}>
          <Stack direction="row" gap={2} flexWrap="wrap" sx={{ mb: 2 }}>
            <Stat label="재직 장애인" value={m.summary.workers} hint={`중증 ${m.summary.severe} · 경증 ${m.summary.mild}`} />
            <Stat label="고용 인정 인원 추정" value={`${m.summary.recognizedCount}명`} hint={`제외 가능 ${m.summary.excluded} · 확인 필요 ${m.summary.needsReview}`} />
            <Stat label="평균 출근율" value={`${m.summary.avgAttendanceRate}%`} />
            <Stat label="평균 업무일지 제출률" value={`${m.summary.avgSubmitRate}%`} />
            <Stat label="총 실근로시간" value={hm(m.summary.totalWorkMinutes)} />
          </Stack>
          <DataTable caption={`${m.month} 근로자별 리포트`} rows={m.workers} cols={[
            { label: '근로자', render: (w: any) => w.person.name }, { label: '장애정도', render: (w: any) => lb(w.person.disabilityDegree) },
            { label: '월 소정', render: (w: any) => w.conditions ? `${w.conditions.monthlyHours}h` : '-' }, { label: '출근/근무일', render: (w: any) => `${w.attendance.attended}/${w.attendance.workdays}` },
            { label: '유급 근로일', render: (w: any) => w.attendance.paidDays }, { label: '실근로', render: (w: any) => hm(w.attendance.workMinutes) },
            { label: '일지 제출률', render: (w: any) => `${w.work.submitRate}%` }, { label: '최저임금', render: (w: any) => w.conditions?.wageCheck ?? '-' },
            { label: '인정 판정', render: (w: any) => <Chip size="small" color={REC_COLOR[w.recognition.result] as any} label={lb(w.recognition.result)} /> },
            { label: '근거', render: (w: any) => w.recognition.reason }]} />
        </Section>
      ))}
      {r && <Alert severity="info">{r.disclaimer}</Alert>}
    </Box>
  )
}

const P = { border: '1px solid #333', padding: '4px 6px', fontSize: 11 } as const

/** A4 인쇄 화면 (EMRP-009). 흑백 인쇄 가독성을 위해 브랜드 색을 줄인다. */
function ReportPrint() {
  const sp = new URLSearchParams(useLocation().search)
  const q = useQ<any>(['rep', sp.get('from'), sp.get('to')], '/reports/employment', { from: sp.get('from'), to: sp.get('to') })
  const r = q.data
  if (!r) return <Box sx={{ p: 3 }}><Loading q={q} /></Box>
  const head = (title: string) => (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', borderBottom: '2px solid #000', mb: 1, pb: 0.5, fontSize: 11 }}>
      <span>{r.company.name} · {r.from} ~ {r.to}</span><b>{title}</b>
    </Box>
  )
  const foot = <Box sx={{ mt: 2, pt: 0.5, borderTop: '1px solid #999', fontSize: 9, color: '#333' }}>생성 {r.generatedAt} · my-vdream · {r.disclaimer}</Box>
  const tbl = (rows: [string, ReactNode][]) => <table style={{ borderCollapse: 'collapse', width: '100%', marginBottom: 8 }}><tbody>{rows.map(([k, v]) => <tr key={k}><th style={{ ...P, width: 140, background: '#eee', textAlign: 'left' }}>{k}</th><td style={P}>{v}</td></tr>)}</tbody></table>
  return (
    <Box sx={{ bgcolor: '#fff', color: '#000', minHeight: '100vh', '@media print': { '.no-print': { display: 'none' } }, '& .page': { width: '180mm', mx: 'auto', p: 2, breakAfter: 'page' } }}>
      <style>{'@page { size: A4 portrait; margin: 15mm } @media print { body { background: #fff } }'}</style>
      <Box className="no-print" sx={{ p: 2, textAlign: 'center' }}><Button variant="contained" onClick={() => window.print()}>인쇄 / PDF로 저장</Button> <Button onClick={() => history.back()}>돌아가기</Button></Box>
      <Box className="page">
        {head('표지 · 요약')}
        <h1 style={{ fontSize: 20 }}>월간 장애인 고용 리포트</h1>
        {tbl([['기업명', r.company.name], ['사업자등록번호', r.company.businessRegistrationNo], ['고용보험 사업장관리번호', r.company.employmentInsuranceNo], ['대표자', r.company.representativeName],
          ['업종', r.company.industry], ['주소', r.company.address], ['기업 담당자', r.company.companyManager], ['브이드림 담당 매니저', r.company.vdreamManager], ['대상 기간', `${r.from} ~ ${r.to}`]])}
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <caption style={{ textAlign: 'left', fontWeight: 700, fontSize: 12 }}>월별 요약</caption>
          <thead><tr>{['월', '재직 장애인', '중증', '경증', '인정 인원 추정', '제외 가능', '확인 필요', '평균 출근율', '평균 제출률', '총 실근로'].map((h) => <th key={h} scope="col" style={{ ...P, background: '#eee' }}>{h}</th>)}</tr></thead>
          <tbody>{r.months.map((m: any) => <tr key={m.month}>{[m.month + (m.inProgress ? '*' : ''), m.summary.workers, m.summary.severe, m.summary.mild, m.summary.recognizedCount, m.summary.excluded, m.summary.needsReview,
            `${m.summary.avgAttendanceRate}%`, `${m.summary.avgSubmitRate}%`, hm(m.summary.totalWorkMinutes)].map((v, i) => <td key={i} style={P}>{v}</td>)}</tr>)}</tbody>
        </table>
        {foot}
      </Box>
      {r.months.flatMap((m: any) => m.workers.map((w: any) => (
        <Box className="page" key={`${m.month}-${w.employmentId}`}>
          {head(`${w.person.name} · ${m.month}`)}
          <h2 style={{ fontSize: 15 }}>1. 인적사항</h2>
          {tbl([['이름', w.person.name], ['생년월일', w.person.birthDate], ['장애유형', `${lb(w.person.disabilityType)}${w.person.disabilityTypeSecondary ? ` / ${lb(w.person.disabilityTypeSecondary)}` : ''}`],
            ['장애정도', lb(w.person.disabilityDegree)], ['재직 기간', `${w.person.startDate} ~ ${w.person.endDate ?? ''}`]])}
          <h2 style={{ fontSize: 15 }}>2. 근로조건</h2>
          {w.conditions ? tbl([['계약', `${lb(w.conditions.contractType)} (${w.conditions.contractStart} ~ ${w.conditions.contractEnd ?? '정함 없음'})`], ['근무 형태·장소', `${lb(w.conditions.workType)} · ${w.conditions.workLocation}`],
            ['근무 요일·시간', `${w.conditions.workDays} ${w.conditions.workTime} (휴게 ${w.conditions.breakMinutes}분)`], ['소정근로시간', `주 ${w.conditions.weeklyHours}시간 · 월 ${w.conditions.monthlyHours}시간`],
            ['급여', `${lb(w.conditions.salaryType)} ${w.conditions.salaryAmount.toLocaleString()}원 · 시급 환산 ${w.conditions.hourlyWage.toLocaleString()}원 · 최저임금(${w.conditions.minimumWage.toLocaleString()}원) ${w.conditions.wageCheck}`],
            ['4대보험', Object.entries(w.conditions.insurance).filter(([, v]) => v).map(([k]) => ({ employment: '고용', accident: '산재', pension: '연금', health: '건강' } as any)[k]).join(', ')]]) : <p>근로계약 정보 없음</p>}
          <h2 style={{ fontSize: 15 }}>3. 근태 실적</h2>
          {tbl([['근무일 / 출근일', `${w.attendance.workdays}일 / ${w.attendance.attended}일 (출근율 ${w.attendance.attendanceRate}%)`], ['지각 / 조퇴 / 결근', `${w.attendance.late} / ${w.attendance.earlyLeave} / ${w.attendance.absent}일`],
            ['휴가', `${w.attendance.leaveDays}일 ${Object.entries(w.attendance.leaveByType).map(([k, v]) => `${lb(k)} ${v}`).join(', ')}`], ['유급 근로일수(추정)', `${w.attendance.paidDays}일 (급여대장으로 확정)`],
            ['총 실근로시간', `${hm(w.attendance.workMinutes)} (퇴근 미기록 ${w.attendance.missingCheckOutDays}일 제외)`], ['담당자 정정', `${w.attendance.correctedCount}건`]])}
          <h2 style={{ fontSize: 15 }}>4. 업무 실적</h2>
          {tbl([['업무일지 제출', `${w.work.submittedDays}일 (제출률 ${w.work.submitRate}%) · 확인 ${w.work.confirmedDays}일 · 보완 요청 ${w.work.returnedCount}회`],
            ['기록 시간', hm(w.work.loggedMinutes)], ['완료 업무 / 산출물', `${w.work.completedTasks}건 / ${w.work.fileCount}개`],
            ['주요 업무', w.work.topTasks.map((t: any) => `${t.title} ${hm(t.minutes)}`).join(' · ') || '-']])}
          <h2 style={{ fontSize: 15 }}>5. 고용 인정 참고</h2>
          {tbl([['판정', lb(w.recognition.result)], ['근거', w.recognition.reason]])}
          <h2 style={{ fontSize: 15 }}>6. 확인</h2>
          {tbl([['기업 담당자', `${r.company.companyManager ?? ''}            (서명)`], ['브이드림 담당 매니저', r.company.vdreamManager ?? '']])}
          <h2 style={{ fontSize: 15, breakBefore: 'page' }}>부록. 일자별 근로 기록</h2>
          <table style={{ borderCollapse: 'collapse', width: '100%' }}>
            <thead><tr>{['날짜', '요일', '근태', '출근', '퇴근', '실근로', '업무일지', '업무 항목'].map((h) => <th key={h} scope="col" style={{ ...P, background: '#eee' }}>{h}</th>)}</tr></thead>
            <tbody>{w.daily.filter((d: any) => d.isWorkday || d.checkIn).map((d: any) => <tr key={d.date}>{[d.date.slice(5), d.weekday, lb(d.status), d.checkIn ?? '', d.checkOut ?? '',
              d.workMinutes != null ? hm(d.workMinutes) : '', d.workLogStatus ? lb(d.workLogStatus) : '', d.workLogItems.join(', ')].map((v, i) => <td key={i} style={P}>{v}</td>)}</tr>)}</tbody>
          </table>
          {foot}
        </Box>
      )))}
    </Box>
  )
}

export default function AdminApp({ onToggleTheme }: { onToggleTheme: () => void }) {
  const { me } = useAuth()
  const menu = me?.role === 'VDREAM_MANAGER' ? VM_MENU : CM_MENU
  return (
    <Routes>
      <Route path="reports/employment/print" element={<ReportPrint />} />
      <Route element={<AdminLayout base="/admin" menu={menu} onToggleTheme={onToggleTheme} />}>
        <Route index element={<Dashboard />} />
        <Route path="workers" element={<Workers />} />
        <Route path="workers/:id" element={<WorkerDetail />} />
        <Route path="employments/:id" element={<WorkerDetail />} />
        <Route path="seekers" element={<Seekers />} />
        <Route path="companies" element={<Companies />} />
        <Route path="resume/:id" element={<ResumePage />} />
        <Route path="postings" element={<Postings />} />
        <Route path="postings/new" element={<PostingForm />} />
        <Route path="postings/:id" element={<PostingDetail />} />
        <Route path="postings/:id/edit" element={<PostingForm />} />
        <Route path="attendance" element={<Attendance />} />
        <Route path="leaves" element={<Leaves />} />
        <Route path="tasks" element={<Tasks />} />
        <Route path="tasks/:id" element={<TaskDetail />} />
        <Route path="work-logs" element={<WorkLogs />} />
        <Route path="work-logs/:id" element={<WorkLogDetail />} />
        <Route path="counseling" element={<CounselingList />} />
        <Route path="resignations" element={<Resignations />} />
        <Route path="reports/employment" element={<Report />} />
        <Route path="messages" element={<MessagesPage base="/admin" />} />
        <Route path="messages/new" element={<MessageCompose base="/admin" />} />
        <Route path="messages/:id" element={<MessageDetail base="/admin" />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="notices" element={<NoticesPage />} />
        <Route path="me" element={<MyInfo />} />
      </Route>
    </Routes>
  )
}
