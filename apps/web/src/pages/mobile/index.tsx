import { useEffect, useState } from 'react'
import { Outlet, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom'
import {
  Alert, AppBar, BottomNavigation, BottomNavigationAction, Box, Button, Card, CardActionArea, CardContent, Checkbox, Chip, Dialog, DialogActions,
  DialogContent, DialogTitle, FormControlLabel, IconButton, List, ListItemButton, ListItemText, MenuItem, Stack, TextField, Toolbar, Typography,
} from '@mui/material'
import HomeIcon from '@mui/icons-material/Home'
import ChecklistIcon from '@mui/icons-material/Checklist'
import EditNoteIcon from '@mui/icons-material/EditNote'
import EventAvailableIcon from '@mui/icons-material/EventAvailable'
import MenuIcon from '@mui/icons-material/Menu'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import { api, del, errMsg, get, openFile, post, put } from '../../api'
import { useAuth } from '../../auth'
import { hm, kst, L, lb, ym, ymd } from '../../labels'
import type { LeaveIn } from '../../api-types'
import { MessageCompose, MessageDetail, MessagesPage, NoticesPage, NotificationsPage } from '../../shared'
import { BackLink, Empty, Loading, PageTitle, PhoneFrame, Section, Status, StatusChip, ThemeToggle, UnreadBadges, useAct, useQ } from '../../ui'

const TABS = [['/m', '홈', <HomeIcon />], ['/m/tasks', '업무', <ChecklistIcon />], ['/m/log', '일지', <EditNoteIcon />],
  ['/m/attendance', '근태', <EventAvailableIcon />], ['/m/more', '더보기', <MenuIcon />]] as const
const BIG = { minHeight: 56, fontSize: 18 }

function MobileLayout({ onToggleTheme }: { onToggleTheme: () => void }) {
  const loc = useLocation()
  const nav = useNavigate()
  const cur = [...TABS].reverse().find(([p]) => loc.pathname === p || (p !== '/m' && loc.pathname.startsWith(p)))?.[0] ?? '/m'
  return (
    <PhoneFrame>
      <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 'inherit' }}>
        <AppBar position="static" color="primary" elevation={0}>
          <Toolbar sx={{ minHeight: 56 }}>
            <Typography sx={{ flex: 1, fontWeight: 800 }}>my-vdream</Typography>
            <ThemeToggle onToggle={onToggleTheme} />
            <UnreadBadges base="/m" />
          </Toolbar>
        </AppBar>
        <Box component="main" sx={{ flex: 1, overflowY: 'auto', p: 2, pb: 3 }}><Outlet /></Box>
        <BottomNavigation component="nav" aria-label="주요 메뉴" showLabels value={cur} onChange={(_, v) => nav(v)}
          sx={{ borderTop: 1, borderColor: 'divider', height: 64, flexShrink: 0 }}>
          {TABS.map(([p, l, i]) => <BottomNavigationAction key={p} value={p} label={l} icon={i} sx={{ minWidth: 0, '& .MuiBottomNavigationAction-label': { fontSize: 14 } }} />)}
        </BottomNavigation>
      </Box>
    </PhoneFrame>
  )
}

function Home() {
  const { me } = useAuth()
  const nav = useNavigate()
  const q = useQ<any>(['today'], '/attendance/today')
  const ann = useQ<any[]>(['announcements'], '/announcements')
  const a = useAct()
  const [reason, setReason] = useState<'late' | 'early' | null>(null)
  const d = q.data
  const rec = d?.record
  const act = async (kind: 'in' | 'out') => {
    const r = await a.run(() => post(`/attendance/check-${kind}`), kind === 'in' ? '출근했습니다. 오늘도 힘내세요.' : '퇴근했습니다. 수고하셨습니다.')
    if (r?.lateMinutes > 0 && kind === 'in') setReason('late')
    if (r?.earlyLeaveMinutes > 0 && kind === 'out') setReason('early')
    if (kind === 'out' && r && !r.workLogSubmitted) a.setMsg({ ok: true, text: '퇴근했습니다. 오늘 업무일지를 아직 제출하지 않았어요. 일지 탭에서 제출해 주세요.' })
  }
  return (
    <Box>
      <PageTitle>{me?.name}님, 안녕하세요</PageTitle>
      <Loading q={q} />
      {d && !d.employment && <Alert severity="info">재직 중인 기업이 없습니다. 더보기 → 채용 공고에서 지원해 보세요.</Alert>}
      {d?.employment && (
        <>
          <Typography color="text.secondary" sx={{ mb: 2 }}>{d.employment.companyName} · 근무 {d.workStart}~{d.workEnd}</Typography>
          {d.employment.status === 'PENDING' ? <Alert severity="info">아직 출근 시작일 전입니다.</Alert> : !rec?.checkInAt ? (
            <Button fullWidth variant="contained" size="large" sx={{ ...BIG, minHeight: 72, fontSize: 22 }} disabled={a.busy} onClick={() => act('in')}>출근하기</Button>
          ) : !rec.checkOutAt ? (
            <Button fullWidth variant="contained" color="secondary" size="large" sx={{ ...BIG, minHeight: 72, fontSize: 22 }} disabled={a.busy} onClick={() => act('out')}>퇴근하기</Button>
          ) : <Alert severity="success">오늘 근무를 마쳤습니다.</Alert>}
          {rec?.checkInAt && (
            <Typography sx={{ mt: 1 }} role="note">출근 {kst(rec.checkInAt, false)}{rec.checkOutAt ? ` · 퇴근 ${kst(rec.checkOutAt, false)}` : ''} · <StatusChip value={rec.status} /></Typography>
          )}
          <Status msg={a.msg} />
          <Section title="오늘 할 일" action={<Button onClick={() => nav('/m/tasks')}>전체 보기</Button>}>
            {d.todoTasks.length ? d.todoTasks.slice(0, 3).map((t: any) => (
              <Card key={t.id} variant="outlined" sx={{ mb: 1 }}>
                <CardActionArea onClick={() => nav(`/m/tasks/${t.id}`)} aria-label={`업무 ${t.title}, ${lb(t.status)}, 우선순위 ${lb(t.priority)}${t.overdue ? ', 기한 초과' : ''}`}>
                  <CardContent sx={{ py: 1.5 }}>
                    <Typography sx={{ fontWeight: 700 }}>{t.title}</Typography>
                    <Stack direction="row" spacing={1} sx={{ mt: 0.5 }}><StatusChip value={t.status} />{t.priority === 'HIGH' && <Chip size="small" label="우선순위 높음" />}{t.overdue && <StatusChip value="ABSENT" label="기한 초과" />}</Stack>
                  </CardContent>
                </CardActionArea>
              </Card>
            )) : <Empty text="오늘 할 업무가 없습니다." />}
            <Typography color="text.secondary">오늘 완료 {d.completedToday}건</Typography>
          </Section>
          <Section title="오늘 업무일지">
            <Stack direction="row" alignItems="center" justifyContent="space-between">
              {d.workLogStatus ? <StatusChip value={d.workLogStatus} /> : <Typography>아직 작성하지 않았습니다.</Typography>}
              <Button variant="outlined" onClick={() => nav('/m/log')}>업무일지 쓰기</Button>
            </Stack>
          </Section>
        </>
      )}
      {ann.data?.[0] && <Section title="공지"><Button onClick={() => nav('/m/more/notices')} sx={{ p: 0, textAlign: 'left' }}>{ann.data[0].title}</Button></Section>}
      <ReasonDialog kind={reason} recordId={rec?.id} onClose={() => setReason(null)} />
    </Box>
  )
}

function ReasonDialog({ kind, recordId, onClose }: { kind: 'late' | 'early' | null; recordId?: number; onClose: () => void }) {
  const [v, setV] = useState('')
  const a = useAct()
  return (
    <Dialog open={!!kind} onClose={onClose} fullWidth>
      <DialogTitle>{kind === 'late' ? '지각 사유' : '조퇴 사유'}를 남길 수 있어요</DialogTitle>
      <DialogContent><TextField autoFocus fullWidth multiline label="사유 (선택)" value={v} onChange={(e) => setV(e.target.value)} sx={{ mt: 1 }} /></DialogContent>
      <DialogActions>
        <Button onClick={onClose}>나중에</Button>
        <Button variant="contained" onClick={async () => { await a.run(() => api.patch(`/attendance/${recordId}/reason`, kind === 'late' ? { lateReason: v } : { earlyLeaveReason: v })); onClose() }}>저장</Button>
      </DialogActions>
    </Dialog>
  )
}

function Tasks() {
  const [tab, setTab] = useState<'todo' | 'all' | 'done'>('todo')
  const q = useQ<any[]>(['tasks'], '/tasks')
  const nav = useNavigate()
  const today = ymd()
  const rows = (q.data ?? []).filter((t) => tab === 'all' ? t.status !== 'CANCELLED' : tab === 'done' ? t.status === 'COMPLETED'
    : t.status === 'IN_PROGRESS' || (t.status === 'ASSIGNED' && (!t.dueDate || t.dueDate <= today)))
  return (
    <Box>
      <PageTitle>업무</PageTitle>
      <Stack direction="row" spacing={1} sx={{ mb: 2 }} role="group" aria-label="업무 보기">
        {([['todo', '오늘 할 일'], ['all', '전체'], ['done', '완료']] as const).map(([k, l]) => (
          <Button key={k} variant={tab === k ? 'contained' : 'outlined'} aria-pressed={tab === k} onClick={() => setTab(k)}>{l}</Button>
        ))}
      </Stack>
      <Loading q={q} />
      {q.data && !rows.length && <Empty text="해당하는 업무가 없습니다." />}
      {rows.map((t, i) => (
        <Card key={t.id} variant="outlined" sx={{ mb: 1 }}>
          <CardActionArea onClick={() => nav(`/m/tasks/${t.id}`)}
            aria-label={`${i + 1}번째 업무, ${t.title}, 우선순위 ${lb(t.priority)}, ${t.dueDate ? `기한 ${t.dueDate}` : '기한 없음'}, ${lb(t.status)}${t.overdue ? ', 기한 초과' : ''}`}>
            <CardContent sx={{ py: 1.5 }}>
              <Typography sx={{ fontWeight: 700 }}>{t.title}</Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 0.5 }} alignItems="center">
                <StatusChip value={t.status} />{t.priority === 'HIGH' && <Chip size="small" label="높음" />}
                {t.overdue && <StatusChip value="ABSENT" label="기한 초과" />}
                <Typography variant="body2" color="text.secondary">{t.dueDate ? `기한 ${t.dueDate.slice(5)}` : ''}</Typography>
              </Stack>
            </CardContent>
          </CardActionArea>
        </Card>
      ))}
    </Box>
  )
}

function TaskDetail() {
  const { id } = useParams()
  const q = useQ<any>(['task', id], `/tasks/${id}`)
  const a = useAct()
  const nav = useNavigate()
  const [note, setNote] = useState('')
  const t = q.data
  return (
    <Box>
      <BackLink />
      <Loading q={q} />
      {t && (
        <>
          <PageTitle>{t.title}</PageTitle>
          <Stack direction="row" spacing={1} sx={{ mb: 2 }}><StatusChip value={t.status} /><Chip size="small" label={`우선순위 ${lb(t.priority)}`} />{t.overdue && <StatusChip value="ABSENT" label="기한 초과" />}</Stack>
          <Typography sx={{ whiteSpace: 'pre-wrap', mb: 2 }}>{t.description || '내용 없음'}</Typography>
          <Typography color="text.secondary">기한 {t.dueDate ?? '없음'} · 누적 기록 {hm(t.totalMinutes)}</Typography>
          {t.employmentEnded && <Alert severity="info" sx={{ mt: 1 }}>재직이 종료된 업무입니다.</Alert>}
          <Stack spacing={1.5} sx={{ mt: 3 }}>
            {t.status === 'ASSIGNED' && <Button variant="contained" sx={BIG} onClick={() => a.run(() => post(`/tasks/${t.id}/start`), '업무를 시작했습니다.')}>시작하기</Button>}
            {['ASSIGNED', 'IN_PROGRESS'].includes(t.status) && !t.employmentEnded && (
              <>
                <TextField label="완료 메모 (선택)" value={note} onChange={(e) => setNote(e.target.value)} />
                <Button variant="contained" color="success" sx={BIG} onClick={() => a.run(() => post(`/tasks/${t.id}/complete`, { note }), '업무를 완료했습니다. 담당자에게 알렸어요.')}>완료하기</Button>
              </>
            )}
            {t.status === 'COMPLETED' && <Button onClick={() => a.run(() => post(`/tasks/${t.id}/reopen`, {}), '진행중으로 되돌렸습니다.')}>완료 되돌리기 (당일만)</Button>}
            <Button variant="outlined" onClick={() => nav(`/m/log?task=${t.id}`)}>업무일지에 추가</Button>
          </Stack>
          <Status msg={a.msg} />
          {!!t.logEntries?.length && (
            <Section title="업무일지 기록">
              {t.logEntries.map((e: any) => <Typography key={e.id}>{e.workDate} · {hm(e.minutes)} · {e.content}</Typography>)}
            </Section>
          )}
        </>
      )}
    </Box>
  )
}

type Entry = { taskId: number | null; title: string; content: string; minutes: number }

function WorkLog() {
  const sp = new URLSearchParams(useLocation().search)
  const [date, setDate] = useState(sp.get('date') ?? ymd())
  const [month, setMonth] = useState(ym())
  const q = useQ<any>(['worklog', date], `/work-logs/me/${date}`, undefined, { retry: false })
  const cal = useQ<any[]>(['worklog-cal', month], '/work-logs/me', { month })
  const a = useAct()
  const [summary, setSummary] = useState('')
  const [issues, setIssues] = useState('')
  const [entries, setEntries] = useState<Entry[]>([])
  const log = q.data?.log
  const tasks: any[] = q.data?.tasks ?? []
  useEffect(() => {
    if (!q.data) return
    setSummary(log?.summary ?? ''); setIssues(log?.issues ?? '')
    const base: Entry[] = log?.entries?.map((e: any) => ({ taskId: e.taskId, title: e.title, content: e.content, minutes: e.minutes })) ?? []
    const pre = Number(sp.get('task'))
    if (pre && !base.some((e) => e.taskId === pre)) {
      const t = tasks.find((x) => x.id === pre)
      if (t) base.push({ taskId: t.id, title: t.title, content: '', minutes: 60 })
    }
    setEntries(base)
  }, [q.data])  // eslint-disable-line
  const locked = log?.status === 'CONFIRMED'
  const total = entries.reduce((s, e) => s + (e.minutes || 0), 0)
  const save = () => a.run(() => put(`/work-logs/me/${date}`, { summary, issues, entries }), '임시저장했습니다.')
  const submit = async () => { if (await save() !== undefined) await a.run(() => post(`/work-logs/me/${date}/submit`), '업무일지를 제출했습니다. 담당자에게 알렸어요.') }
  const upload = async (f: File | undefined) => {
    if (!f) return
    const fd = new FormData(); fd.append('file', f)
    await a.run(() => api.post(`/work-logs/me/${date}/files`, fd), '파일을 첨부했습니다.')
  }
  const set = (i: number, patch: Partial<Entry>) => setEntries((es) => es.map((e, j) => (j === i ? { ...e, ...patch } : e)))
  return (
    <Box>
      <PageTitle>업무일지</PageTitle>
      <TextField type="date" label="날짜" value={date} onChange={(e) => setDate(e.target.value)} InputLabelProps={{ shrink: true }} sx={{ mb: 2 }} fullWidth />
      {q.error ? <Alert severity="info">{errMsg(q.error)}</Alert> : <Loading q={q} />}
      {q.data && (
        <>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
            <Typography>상태</Typography>{log ? <StatusChip value={log.status} /> : <Chip size="small" label="미작성" />}
            <Typography color="text.secondary">합계 {hm(total)}</Typography>
          </Stack>
          {log?.status === 'RETURNED' && <Alert severity="warning" sx={{ mb: 1 }}>보완 요청: {log.reviewComment}</Alert>}
          {log?.status === 'CONFIRMED' && log.reviewComment && <Alert severity="success" sx={{ mb: 1 }}>담당자 의견: {log.reviewComment}</Alert>}
          {entries.map((e, i) => (
            <Section key={i} title={`항목 ${i + 1}`} action={!locked && <IconButton aria-label={`항목 ${i + 1} 삭제`} onClick={() => setEntries(entries.filter((_, j) => j !== i))}><DeleteOutlineIcon /></IconButton>}>
              <Stack spacing={1.5}>
                <TextField select label="배정된 업무" value={e.taskId ?? ''} disabled={locked}
                  onChange={(ev) => { const t = tasks.find((x) => x.id === Number(ev.target.value)); set(i, t ? { taskId: t.id, title: t.title } : { taskId: null }) }}>
                  <MenuItem value="">직접 입력</MenuItem>
                  {tasks.map((t) => <MenuItem key={t.id} value={t.id}>{t.title}</MenuItem>)}
                </TextField>
                {!e.taskId && <TextField label="업무명" value={e.title} disabled={locked} onChange={(ev) => set(i, { title: ev.target.value })} />}
                <TextField label="수행 내용" multiline minRows={2} value={e.content} disabled={locked} onChange={(ev) => set(i, { content: ev.target.value })} />
                <TextField select label="소요 시간" value={e.minutes} disabled={locked} onChange={(ev) => set(i, { minutes: Number(ev.target.value) })}>
                  {Array.from({ length: 32 }, (_, k) => (k + 1) * 15).map((m) => <MenuItem key={m} value={m}>{hm(m)}</MenuItem>)}
                </TextField>
              </Stack>
            </Section>
          ))}
          {!locked && <Button fullWidth variant="outlined" sx={{ mb: 2 }} onClick={() => setEntries([...entries, { taskId: null, title: '', content: '', minutes: 60 }])}>항목 추가</Button>}
          <TextField fullWidth label="하루 요약" value={summary} disabled={locked} onChange={(e) => setSummary(e.target.value)} sx={{ mb: 1.5 }} />
          <TextField fullWidth label="특이사항·건의" value={issues} disabled={locked} onChange={(e) => setIssues(e.target.value)} sx={{ mb: 2 }} />
          <Section title="산출물 파일">
            {log?.files?.map((f: any) => (
              <Stack key={f.id} direction="row" alignItems="center">
                <Button onClick={() => openFile(f.id)}>{f.name}</Button>
                {!locked && <IconButton aria-label={`${f.name} 삭제`} onClick={() => a.run(() => del(`/work-logs/me/${date}/files/${f.id}`))}><DeleteOutlineIcon /></IconButton>}
              </Stack>
            ))}
            {!locked && <Button component="label" variant="outlined">파일 첨부<input hidden type="file" onChange={(e) => upload(e.target.files?.[0])} /></Button>}
          </Section>
          {!locked && (
            <Stack spacing={1.5}>
              <Button variant="outlined" sx={BIG} disabled={a.busy} onClick={save}>임시저장</Button>
              <Button variant="contained" sx={BIG} disabled={a.busy || !entries.length || entries.some((e) => !e.title || !e.content)} onClick={submit}>
                {log?.status === 'SUBMITTED' || log?.status === 'RETURNED' ? '다시 제출하기' : '제출하기'}
              </Button>
            </Stack>
          )}
          <Status msg={a.msg} />
        </>
      )}
      <Section title="월별 기록">
        <TextField type="month" label="월" value={month} onChange={(e) => setMonth(e.target.value)} InputLabelProps={{ shrink: true }} sx={{ mb: 1 }} />
        <List dense>
          {cal.data?.filter((d) => d.attended || d.status).map((d) => (
            <ListItemButton key={d.date} onClick={() => setDate(d.date)} selected={d.date === date}>
              <ListItemText primary={<Stack direction="row" spacing={1} alignItems="center"><span>{d.date.slice(5)}</span>{d.status ? <StatusChip value={d.status} /> : <Chip size="small" label="미작성" />}</Stack>} secondary={d.totalMinutes ? hm(d.totalMinutes) : undefined} />
            </ListItemButton>
          ))}
        </List>
      </Section>
    </Box>
  )
}

function Attendance() {
  const [month, setMonth] = useState(ym())
  const q = useQ<any>(['my-att', month], '/attendance/me', { month })
  const s = q.data?.summary
  return (
    <Box>
      <PageTitle>근태</PageTitle>
      <TextField type="month" label="월" value={month} onChange={(e) => setMonth(e.target.value)} InputLabelProps={{ shrink: true }} sx={{ mb: 2 }} fullWidth />
      <Loading q={q} />
      {s && <Typography sx={{ mb: 1 }}>출근 {s.attended}일 · 지각 {s.late} · 조퇴 {s.earlyLeave} · 결근 {s.absent} · 휴가 {s.leaveDays}일</Typography>}
      <List dense>
        {q.data?.days?.filter((d: any) => d.isWorkday || d.record).map((d: any) => (
          <ListItemText key={d.date} sx={{ py: 0.5, borderBottom: 1, borderColor: 'divider' }}
            primary={<Stack direction="row" spacing={1} alignItems="center"><b>{d.date.slice(5)}</b>{d.status ? <StatusChip value={d.status} /> : <Typography color="text.secondary">-</Typography>}</Stack>}
            secondary={d.record?.checkInAt ? `출근 ${kst(d.record.checkInAt, false)} · 퇴근 ${kst(d.record.checkOutAt, false)}` : d.leaveType ? lb(d.leaveType) : undefined} />
        ))}
      </List>
    </Box>
  )
}

const MORE = [['messages', '쪽지'], ['notifications', '알림'], ['resume', '이력서·구직 등록'], ['jobs', '채용 공고'], ['applications', '지원 현황'],
  ['leaves', '휴가'], ['contract', '근로계약'], ['resign', '퇴사 신청'], ['notices', '공지사항'], ['me', '내 정보']]

function More() {
  const nav = useNavigate()
  const { logout } = useAuth()
  return (
    <Box>
      <PageTitle>더보기</PageTitle>
      <List>{MORE.map(([p, l]) => <ListItemButton key={p} divider onClick={() => nav(`/m/more/${p}`)} sx={{ minHeight: 56 }}><ListItemText primary={l} /></ListItemButton>)}</List>
      <Button fullWidth sx={{ mt: 2 }} onClick={() => { logout(); nav('/') }}>로그아웃</Button>
    </Box>
  )
}

const FIELDS = ['DATA_LABELING', 'DOCUMENT_ENTRY', 'CONTENT_MONITORING', 'DESIGN', 'VIDEO_EDITING', 'CONTENT_WRITING', 'CUSTOMER_SUPPORT', 'RESEARCH', 'OTHER']
const DTYPES = ['PHYSICAL', 'BRAIN_LESION', 'VISUAL', 'HEARING', 'SPEECH', 'FACIAL', 'KIDNEY', 'HEART', 'LIVER', 'RESPIRATORY', 'OSTOMY', 'EPILEPSY', 'INTELLECTUAL', 'AUTISM', 'MENTAL']

export function ResumeEditor({ workerId, compact }: { workerId: number; compact?: boolean }) {
  const q = useQ<any>(['resume', workerId], `/resumes/${workerId}`)
  const a = useAct()
  const [f, setF] = useState<any>(null)
  useEffect(() => {
    if (!q.data) return
    const p = q.data.profile ?? {}
    setF({ ...q.data.user, ...p, desiredJobFields: p.desiredJobFields ? p.desiredJobFields.split(',') : [], educations: q.data.educations, careers: q.data.careers })
  }, [q.data])
  if (!f) return <Loading q={q} />
  const set = (k: string) => (e: any) => setF({ ...f, [k]: e.target.value === '' ? null : e.target.value })
  const save = () => a.run(() => put(`/resumes/${workerId}`, {
    name: f.name, phone: f.phone, email: f.email, birthDate: f.birthDate, gender: f.gender, address: f.address, disabilityType: f.disabilityType,
    disabilityTypeSecondary: f.disabilityTypeSecondary, disabilityDegree: f.disabilityDegree, assistiveDevices: f.assistiveDevices, hasPc: f.hasPc, hasInternet: f.hasInternet,
    softwareSkills: f.softwareSkills, workEnvironmentNote: f.workEnvironmentNote, desiredJobFields: f.desiredJobFields, skills: f.skills, introduction: f.introduction,
    educations: f.educations.filter((e: any) => e.institution && e.startDate).map((e: any) => ({ startDate: e.startDate, endDate: e.endDate || null, institution: e.institution, type: e.type, status: e.status, major: e.major })),
    careers: f.careers.filter((c: any) => c.institution && c.startDate).map((c: any) => ({ startDate: c.startDate, endDate: c.endDate || null, institution: c.institution, employmentType: c.employmentType, duties: c.duties, position: c.position })),
  }), '이력서를 저장했습니다.')
  const sel = (k: string, opts: string[], label: string) => (
    <TextField select label={label} value={f[k] ?? ''} onChange={set(k)}><MenuItem value="">선택 안 함</MenuItem>{opts.map((o) => <MenuItem key={o} value={o}>{L[o]}</MenuItem>)}</TextField>
  )
  return (
    <Stack spacing={1.5}>
      <Typography variant="h3" component="h2">기본정보</Typography>
      <TextField label="이름" value={f.name ?? ''} onChange={set('name')} />
      <TextField type="date" label="생년월일" value={f.birthDate ?? ''} onChange={set('birthDate')} InputLabelProps={{ shrink: true }} />
      {sel('gender', ['MALE', 'FEMALE'], '성별')}
      <TextField label="휴대폰번호" value={f.phone ?? ''} onChange={set('phone')} />
      <TextField label="이메일" type="email" value={f.email ?? ''} onChange={set('email')} />
      <TextField label="거주지" value={f.address ?? ''} onChange={set('address')} />
      <PhotoField workerId={workerId} fileId={q.data?.profile?.photoFileId} />
      <Typography variant="h3" component="h2">장애정보</Typography>
      {sel('disabilityType', DTYPES, '주 장애유형')}
      {sel('disabilityTypeSecondary', DTYPES, '부 장애유형')}
      {sel('disabilityDegree', ['SEVERE', 'MILD'], '장애정도')}
      <TextField label="사용 보조기기" value={f.assistiveDevices ?? ''} onChange={set('assistiveDevices')} />
      <Typography variant="h3" component="h2">재택근무 환경</Typography>
      <FormControlLabel control={<Checkbox checked={!!f.hasPc} onChange={(e) => setF({ ...f, hasPc: e.target.checked })} />} label="PC 보유" />
      <FormControlLabel control={<Checkbox checked={!!f.hasInternet} onChange={(e) => setF({ ...f, hasInternet: e.target.checked })} />} label="인터넷 사용 가능" />
      <TextField label="사용 가능 소프트웨어" value={f.softwareSkills ?? ''} onChange={set('softwareSkills')} />
      <TextField label="근무 환경 메모" value={f.workEnvironmentNote ?? ''} onChange={set('workEnvironmentNote')} />
      <Typography variant="h3" component="h2">희망 직무</Typography>
      <Stack direction="row" flexWrap="wrap" gap={1}>
        {FIELDS.map((x) => { const on = f.desiredJobFields.includes(x); return <Button key={x} size="small" variant={on ? 'contained' : 'outlined'} aria-pressed={on} onClick={() => setF({ ...f, desiredJobFields: on ? f.desiredJobFields.filter((y: string) => y !== x) : [...f.desiredJobFields, x] })}>{L[x]}</Button> })}
      </Stack>
      <TextField label="보유 기술" value={f.skills ?? ''} onChange={set('skills')} />
      <TextField label="자기소개" multiline minRows={3} value={f.introduction ?? ''} onChange={set('introduction')} />
      <RowsEditor title="학력" rows={f.educations} onChange={(v) => setF({ ...f, educations: v })}
        blank={{ startDate: '', endDate: '', institution: '', type: 'HIGH', status: 'GRADUATED', major: '' }}
        fields={[['institution', '기관명'], ['type', '구분', ['ELEMENTARY', 'MIDDLE', 'HIGH', 'UNIVERSITY', 'GRADUATE', 'VOCATIONAL']], ['status', '상태', ['ENROLLED', 'GRADUATED', 'DROPPED_OUT', 'COMPLETED']],
          ['major', '전공·과정'], ['startDate', '시작일', 'date'], ['endDate', '종료일', 'date']]} />
      <RowsEditor title="경력" rows={f.careers} onChange={(v) => setF({ ...f, careers: v })}
        blank={{ startDate: '', endDate: '', institution: '', employmentType: 'EMPLOYEE', duties: '', position: '' }}
        fields={[['institution', '기관명'], ['employmentType', '근무형태', ['INTERN', 'TRAINEE', 'EMPLOYEE']], ['duties', '담당업무'], ['position', '직급'],
          ['startDate', '시작일', 'date'], ['endDate', '종료일', 'date']]} />
      {compact && null}
      <Button variant="contained" sx={BIG} onClick={save} disabled={a.busy}>저장</Button>
      <Status msg={a.msg} />
    </Stack>
  )
}

type FieldDef = [string, string, (string[] | 'date')?]

/** 학력·경력처럼 여러 행을 추가·수정·삭제하는 편집기 (RESM-006, RESM-007) */
function RowsEditor({ title, rows, onChange, blank, fields }: { title: string; rows: any[]; onChange: (v: any[]) => void; blank: any; fields: FieldDef[] }) {
  const set = (i: number, k: string, v: string) => onChange(rows.map((r, j) => (j === i ? { ...r, [k]: v } : r)))
  return (
    <Box>
      <Typography variant="h3" component="h2" sx={{ mb: 1 }}>{title}</Typography>
      {rows.map((r, i) => (
        <Card key={i} variant="outlined" sx={{ mb: 1 }}>
          <CardContent>
            <Stack spacing={1.25}>
              {fields.map(([k, l, t]) => Array.isArray(t)
                ? <TextField key={k} select size="small" label={l} value={r[k] ?? ''} onChange={(e) => set(i, k, e.target.value)}>{t.map((o) => <MenuItem key={o} value={o}>{L[o]}</MenuItem>)}</TextField>
                : <TextField key={k} size="small" label={l} type={t === 'date' ? 'date' : 'text'} value={r[k] ?? ''} onChange={(e) => set(i, k, e.target.value)} InputLabelProps={t === 'date' ? { shrink: true } : undefined} />)}
              <Button color="error" onClick={() => onChange(rows.filter((_, j) => j !== i))} aria-label={`${title} ${i + 1}번째 삭제`}>삭제</Button>
            </Stack>
          </CardContent>
        </Card>
      ))}
      <Button variant="outlined" onClick={() => onChange([...rows, { ...blank }])}>{title} 추가</Button>
    </Box>
  )
}

/** 증명사진 업로드 (RESM-005). JPG·PNG 5MB */
function PhotoField({ workerId, fileId }: { workerId: number; fileId?: number | null }) {
  const a = useAct()
  const [src, setSrc] = useState<string | null>(null)
  useEffect(() => { if (fileId) get<{ url: string }>(`/files/${fileId}/url`).then((r) => setSrc(r.url)).catch(() => setSrc(null)) }, [fileId])
  const upload = (f?: File) => {
    if (!f) return
    const fd = new FormData(); fd.append('file', f)
    a.run(() => api.post(`/resumes/${workerId}/photo`, fd), '증명사진을 올렸습니다.')
  }
  return (
    <Stack direction="row" spacing={2} alignItems="center">
      <Box sx={{ width: 72, height: 96, borderRadius: 1, bgcolor: 'action.hover', overflow: 'hidden', flexShrink: 0 }}>
        {src ? <img src={src} alt="증명사진" style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : <Typography variant="body2" sx={{ p: 1 }}>사진 없음</Typography>}
      </Box>
      <Box>
        <Button component="label" variant="outlined">증명사진 선택<input hidden type="file" accept="image/jpeg,image/png" onChange={(e) => upload(e.target.files?.[0])} /></Button>
        <Typography variant="body2" color="text.secondary">JPG·PNG, 5MB 이하</Typography>
        <Status msg={a.msg} />
      </Box>
    </Stack>
  )
}

function Resume() {
  const { me, reload } = useAuth()
  const q = useQ<any>(['resume', me!.id], `/resumes/${me!.id}`)
  const a = useAct()
  const seeking = q.data?.profile?.jobSeekingStatus === 'SEEKING'
  return (
    <Box>
      <BackLink />
      <PageTitle>이력서</PageTitle>
      <Section title="구직 등록">
        <Typography sx={{ mb: 1 }}>현재 상태: <StatusChip value={q.data?.profile?.jobSeekingStatus} /></Typography>
        <Button variant={seeking ? 'outlined' : 'contained'} onClick={() => a.run(() => post(`/resumes/${me!.id}/job-seeking`, { seeking: !seeking }), seeking ? '구직 등록을 해제했습니다.' : '구직 등록했습니다. 브이드림 매니저에게 알렸어요.').then(reload)}>
          {seeking ? '구직 등록 해제' : '구직 등록하기'}
        </Button>
        <Status msg={a.msg} />
      </Section>
      <ResumeEditor workerId={me!.id} />
      {!!q.data?.employmentHistory?.length && <Section title="재직 이력">{q.data.employmentHistory.map((h: any) => <Typography key={h.id}>{h.companyName} · {h.startDate} ~ {h.endDate ?? ''} <StatusChip value={h.status} /></Typography>)}</Section>}
    </Box>
  )
}

function Jobs() {
  const [field, setField] = useState('')
  const [workType, setWorkType] = useState('')
  const [kw, setKw] = useState('')
  const q = useQ<any[]>(['jobs', field, workType, kw], '/job-postings', { job_field: field || undefined, work_type: workType || undefined, q: kw || undefined })
  const nav = useNavigate()
  return (
    <Box>
      <BackLink />
      <PageTitle>채용 공고</PageTitle>
      <TextField select fullWidth label="직무 분야" value={field} onChange={(e) => setField(e.target.value)} sx={{ mb: 2 }}>
        <MenuItem value="">전체</MenuItem>{FIELDS.map((x) => <MenuItem key={x} value={x}>{L[x]}</MenuItem>)}
      </TextField>
      <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
        <TextField select label="근무 형태" value={workType} onChange={(e) => setWorkType(e.target.value)} sx={{ minWidth: 120 }}>
          <MenuItem value="">전체</MenuItem><MenuItem value="REMOTE">재택</MenuItem><MenuItem value="HYBRID">혼합</MenuItem>
        </TextField>
        <TextField label="기업명·제목 검색" value={kw} onChange={(e) => setKw(e.target.value)} fullWidth />
      </Stack>
      <Loading q={q} />
      {q.data && !q.data.length && <Empty text="조건에 맞는 공고가 없습니다." />}
      {q.data?.map((p) => (
        <Card key={p.id} variant="outlined" sx={{ mb: 1 }}>
          <CardActionArea onClick={() => nav(`/m/more/jobs/${p.id}`)}>
            <CardContent>
              <Typography sx={{ fontWeight: 700 }}>{p.title}</Typography>
              <Typography color="text.secondary">{p.companyName} · {lb(p.jobField)} · {lb(p.workType)} · 주 {p.weeklyWorkHours}시간</Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 0.5 }}>{p.myApplication && <StatusChip value={p.myApplication.status} />}{!p.isOpen && <Chip size="small" label="마감 예정일 경과" />}</Stack>
            </CardContent>
          </CardActionArea>
        </Card>
      ))}
    </Box>
  )
}

function JobDetail() {
  const { id } = useParams()
  const q = useQ<any>(['job', id], `/job-postings/${id}`)
  const { reload } = useAuth()
  const a = useAct()
  const [ask, setAsk] = useState(false)
  const p = q.data
  const apply = async (registerSeeking: boolean) => {
    try { await post(`/job-postings/${id}/apply`, { registerSeeking }); a.setMsg({ ok: true, text: '지원했습니다. 결과는 알림으로 알려 드려요.' }); q.refetch(); reload() }
    catch (e: any) { if (e?.response?.data?.error?.code === 'NOT_SEEKING') setAsk(true); else a.setMsg({ ok: false, text: errMsg(e) }) }
  }
  return (
    <Box>
      <BackLink />
      <Loading q={q} />
      {p && (
        <>
          <PageTitle>{p.title}</PageTitle>
          <Typography color="text.secondary" sx={{ mb: 2 }}>{p.companyName}</Typography>
          {[['직무', lb(p.jobField)], ['근무 형태', lb(p.workType)], ['근무 시간', `${p.workDays} ${p.workStartTime}~${p.workEndTime}`], ['주 소정근로시간', `${p.weeklyWorkHours}시간`],
            ['급여', `${lb(p.salaryType)} ${p.salaryAmount.toLocaleString()}원`], ['지원 장비', p.equipmentSupport], ['복리후생', p.benefits], ['근무 시작 예정일', p.expectedStartDate], ['마감 예정일', p.deadlineDate]]
            .map(([k, v]) => <Typography key={k}><b>{k}</b> {v ?? '-'}</Typography>)}
          <Typography sx={{ whiteSpace: 'pre-wrap', my: 2 }}>{p.mainDuties}{'\n'}{p.description}</Typography>
          {p.myApplication ? <Alert severity="info">지원 상태: {lb(p.myApplication.status)}</Alert>
            : <Button fullWidth variant="contained" sx={BIG} disabled={!p.isOpen} onClick={() => apply(false)}>지원하기 (이력서가 기업에 공개됩니다)</Button>}
          <Status msg={a.msg} />
        </>
      )}
      <Dialog open={ask} onClose={() => setAsk(false)}>
        <DialogTitle>구직 등록이 필요해요</DialogTitle>
        <DialogContent>구직 등록을 하고 바로 지원할까요?</DialogContent>
        <DialogActions><Button onClick={() => setAsk(false)}>취소</Button><Button variant="contained" onClick={() => { setAsk(false); apply(true) }}>등록하고 지원</Button></DialogActions>
      </Dialog>
    </Box>
  )
}

function Applications() {
  const q = useQ<any[]>(['my-apps'], '/applications/me')
  const a = useAct()
  return (
    <Box>
      <BackLink />
      <PageTitle>지원 현황</PageTitle>
      <Loading q={q} />
      {q.data && !q.data.length && <Empty text="지원한 공고가 없습니다." />}
      {q.data?.map((x) => (
        <Section key={x.id} title={x.postingTitle}>
          <Typography>{x.companyName} · <StatusChip value={x.status} /></Typography>
          {x.interviewAt && <Typography>면접 {kst(x.interviewAt)} · {lb(x.interviewMethod)} · {x.interviewLocation}</Typography>}
          {x.startDate && <Typography>출근 시작일 {x.startDate}</Typography>}
          {['APPLIED', 'DOCUMENT_PASSED', 'INTERVIEW_SCHEDULED'].includes(x.status) && <Button color="error" onClick={() => a.run(() => post(`/applications/${x.id}/cancel`), '지원을 취소했습니다.')}>지원 취소</Button>}
        </Section>
      ))}
      <Status msg={a.msg} />
    </Box>
  )
}

function Leaves() {
  const q = useQ<any>(['my-leaves'], '/leaves/me')
  const a = useAct()
  const [f, setF] = useState<LeaveIn & { endDate: string }>({ leaveType: 'ANNUAL', startDate: ymd(), endDate: ymd(), reason: '' })
  const b = q.data?.balance
  return (
    <Box>
      <BackLink />
      <PageTitle>휴가</PageTitle>
      {b && <Typography sx={{ mb: 2 }}>{b.year}년 연차 부여 {b.granted}일 · 사용 {b.used}일 · <b>잔여 {b.remaining}일</b></Typography>}
      <Section title="휴가 신청">
        <Stack spacing={1.5}>
          <TextField select label="종류" value={f.leaveType} onChange={(e) => setF({ ...f, leaveType: e.target.value as LeaveIn['leaveType'] })}>
            {['ANNUAL', 'HALF_DAY_AM', 'HALF_DAY_PM', 'SICK', 'OTHER'].map((x) => <MenuItem key={x} value={x}>{L[x]}</MenuItem>)}
          </TextField>
          <TextField type="date" label="시작일" value={f.startDate} onChange={(e) => setF({ ...f, startDate: e.target.value })} InputLabelProps={{ shrink: true }} />
          {!f.leaveType.startsWith('HALF') && <TextField type="date" label="종료일" value={f.endDate} onChange={(e) => setF({ ...f, endDate: e.target.value })} InputLabelProps={{ shrink: true }} />}
          <TextField label="사유" value={f.reason} onChange={(e) => setF({ ...f, reason: e.target.value })} />
          <Button variant="contained" sx={BIG} onClick={() => a.run(() => post('/leaves', { ...f, endDate: f.leaveType.startsWith('HALF') ? f.startDate : f.endDate }), '휴가를 신청했습니다.')}>신청하기</Button>
          <Status msg={a.msg} />
        </Stack>
      </Section>
      <Loading q={q} />
      {q.data?.requests?.map((r: any) => (
        <Typography key={r.id} sx={{ py: 0.5 }}>{lb(r.leaveType)} {r.startDate}{r.endDate !== r.startDate ? `~${r.endDate}` : ''} ({r.days}일) <StatusChip value={r.status} />
          {r.status === 'PENDING' && <Button size="small" onClick={() => a.run(() => post(`/leaves/${r.id}/withdraw`), '신청을 철회했습니다.')}>철회</Button>}</Typography>
      ))}
    </Box>
  )
}

function Contract() {
  const q = useQ<any[]>(['my-emps'], '/employments/me')
  return (
    <Box>
      <BackLink />
      <PageTitle>근로계약</PageTitle>
      <Loading q={q} />
      {q.data && !q.data.length && <Empty text="근로계약이 없습니다." />}
      {q.data?.map((e) => (
        <Section key={e.id} title={`${e.companyName} (${lb(e.status)})`}>
          {e.contract && [['계약 기간', `${e.contract.startDate} ~ ${e.contract.endDate ?? '정함 없음'}`], ['근무 형태', `${lb(e.contract.workType)} · ${e.contract.workLocation}`],
            ['근무 시간', `${e.contract.workDays} ${e.contract.workStartTime}~${e.contract.workEndTime} (휴게 ${e.contract.breakMinutes}분)`], ['주 소정근로시간', `${e.contract.weeklyWorkHours}시간`],
            ['급여', `${lb(e.contract.salaryType)} ${e.contract.salaryAmount.toLocaleString()}원`], ['연차', `${e.contract.annualLeaveDays ?? '-'}일`], ['지원 장비', e.contract.equipmentSupport]]
            .map(([k, v]) => <Typography key={k}><b>{k}</b> {v ?? '-'}</Typography>)}
        </Section>
      ))}
    </Box>
  )
}

function Resign() {
  const q = useQ<any[]>(['my-resign'], '/resignations')
  const a = useAct()
  const [f, setF] = useState({ plannedDate: '', reason: '' })
  const [confirm, setConfirm] = useState(false)
  return (
    <Box>
      <BackLink />
      <PageTitle>퇴사 신청</PageTitle>
      <Typography sx={{ mb: 2 }}>퇴사 전에 담당 매니저와 먼저 이야기해 주세요. 신청하면 담당 매니저에게 알림이 갑니다.</Typography>
      <Stack spacing={1.5}>
        <TextField type="date" label="퇴사 예정일" value={f.plannedDate} onChange={(e) => setF({ ...f, plannedDate: e.target.value })} InputLabelProps={{ shrink: true }} />
        <TextField label="사유" multiline value={f.reason} onChange={(e) => setF({ ...f, reason: e.target.value })} />
        <Button variant="contained" color="error" sx={BIG} disabled={!f.plannedDate || !f.reason} onClick={() => setConfirm(true)}>퇴사 신청하기</Button>
      </Stack>
      <Status msg={a.msg} />
      {q.data?.map((r) => (
        <Typography key={r.id} sx={{ mt: 1 }}>{r.plannedDate} · {r.reason} <StatusChip value={r.status} />
          {r.status === 'PENDING' && <Button size="small" onClick={() => a.run(() => post(`/resignations/${r.id}/withdraw`), '신청을 철회했습니다.')}>철회</Button>}</Typography>
      ))}
      <Dialog open={confirm} onClose={() => setConfirm(false)}>
        <DialogTitle>퇴사를 신청할까요?</DialogTitle>
        <DialogActions><Button onClick={() => setConfirm(false)}>취소</Button><Button color="error" variant="contained" onClick={() => { setConfirm(false); a.run(() => post('/resignations', f), '퇴사를 신청했습니다.') }}>신청</Button></DialogActions>
      </Dialog>
    </Box>
  )
}

/** 비밀번호 변경 (AUTH-003) */
function PasswordForm() {
  const a = useAct()
  const [p, setP] = useState({ currentPassword: '', newPassword: '', confirm: '' })
  const mismatch = !!p.confirm && p.newPassword !== p.confirm
  return (
    <Stack spacing={1.5} component="form" onSubmit={(e) => { e.preventDefault(); a.run(() => post('/auth/password', { currentPassword: p.currentPassword, newPassword: p.newPassword }), '비밀번호를 바꿨습니다.').then(() => setP({ currentPassword: '', newPassword: '', confirm: '' })) }}>
      <Typography variant="h3" component="h2">비밀번호 변경</Typography>
      <TextField type="password" label="현재 비밀번호" autoComplete="current-password" value={p.currentPassword} onChange={(e) => setP({ ...p, currentPassword: e.target.value })} />
      <TextField type="password" label="새 비밀번호 (8자 이상)" autoComplete="new-password" value={p.newPassword} onChange={(e) => setP({ ...p, newPassword: e.target.value })} />
      <TextField type="password" label="새 비밀번호 확인" autoComplete="new-password" value={p.confirm} error={mismatch} helperText={mismatch ? '새 비밀번호와 다릅니다.' : ' '} onChange={(e) => setP({ ...p, confirm: e.target.value })} />
      <Button type="submit" variant="outlined" disabled={!p.currentPassword || p.newPassword.length < 8 || mismatch}>비밀번호 바꾸기</Button>
      <Status msg={a.msg} />
    </Stack>
  )
}

export function MyInfo() {
  const { me, reload, logout } = useAuth()
  const nav = useNavigate()
  const a = useAct()
  const [f, setF] = useState({ name: me?.name ?? '', phone: me?.phone ?? '', email: me?.email ?? '' })
  return (
    <Box>
      <PageTitle>내 정보</PageTitle>
      <Stack spacing={1.5}>
        <Typography>아이디 {me?.loginId} · {lb(me?.role)}{me?.companyName ? ` · ${me.companyName}` : ''}</Typography>
        <TextField label="이름" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
        <TextField label="휴대폰번호" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} />
        <TextField label="이메일" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />
        <Button variant="contained" onClick={() => a.run(() => api.patch('/auth/me', f), '저장했습니다.').then(reload)}>저장</Button>
        {me?.isDemo ? <Typography color="text.secondary">데모 계정은 비밀번호를 바꿀 수 없습니다.</Typography> : <PasswordForm />}
        <Button onClick={() => { logout(); nav('/') }}>로그아웃</Button>
      </Stack>
      <Status msg={a.msg} />
    </Box>
  )
}

export default function MobileApp({ onToggleTheme }: { onToggleTheme: () => void }) {
  return (
    <Routes>
      <Route element={<MobileLayout onToggleTheme={onToggleTheme} />}>
        <Route index element={<Home />} />
        <Route path="tasks" element={<Tasks />} />
        <Route path="tasks/:id" element={<TaskDetail />} />
        <Route path="log" element={<WorkLog />} />
        <Route path="attendance" element={<Attendance />} />
        <Route path="more" element={<More />} />
        <Route path="messages" element={<MessagesPage base="/m" />} />
        <Route path="messages/new" element={<MessageCompose base="/m" />} />
        <Route path="messages/:id" element={<MessageDetail base="/m" />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="more/messages" element={<MessagesPage base="/m" />} />
        <Route path="more/notifications" element={<NotificationsPage />} />
        <Route path="more/resume" element={<Resume />} />
        <Route path="more/jobs" element={<Jobs />} />
        <Route path="more/jobs/:id" element={<JobDetail />} />
        <Route path="more/applications" element={<Applications />} />
        <Route path="more/leaves" element={<Leaves />} />
        <Route path="more/contract" element={<Contract />} />
        <Route path="more/resign" element={<Resign />} />
        <Route path="more/notices" element={<NoticesPage />} />
        <Route path="more/me" element={<MyInfo />} />
      </Route>
    </Routes>
  )
}
