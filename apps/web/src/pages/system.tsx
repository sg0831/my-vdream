import { useState } from 'react'
import { Route, Routes } from 'react-router-dom'
import { Box, Button, Checkbox, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, MenuItem, Stack, TextField } from '@mui/material'
import { del, post, put } from '../api'
import { L, lb } from '../labels'
import { DataTable, Loading, PageTitle, Stat, Status, StatusChip, useAct, useQ } from '../ui'
import { AdminLayout, SA_MENU } from './admin'
import { MyInfo } from './mobile'

function SysDashboard() {
  const q = useQ<any>(['sysdash'], '/system/dashboard')
  const a = useAct()
  const [confirm, setConfirm] = useState(false)
  const d = q.data
  return (
    <Box>
      <PageTitle action={<Button color="error" variant="outlined" onClick={() => setConfirm(true)}>데모 데이터 초기화</Button>}>시스템 현황</PageTitle>
      <Status msg={a.msg} />
      <Loading q={q} />
      {d && (
        <Stack direction="row" flexWrap="wrap" gap={2}>
          <Stat label="기업" value={d.companies} />
          {Object.entries(d.users).map(([k, v]) => <Stat key={k} label={`${lb(k)} 계정`} value={v as number} />)}
          <Stat label="구직중 근로자" value={d.seekers} /><Stat label="재직 근로자" value={d.activeWorkers} />
          <Stat label="게시 중 공고" value={d.publishedPostings} /><Stat label="오늘 출근" value={d.checkedInToday} />
        </Stack>
      )}
      <Dialog open={confirm} onClose={() => setConfirm(false)}>
        <DialogTitle>모든 데이터를 시드 상태로 되돌릴까요?</DialogTitle>
        <DialogContent>체험하며 바뀐 데이터가 모두 지워지고 최근 3개월 데모 데이터가 다시 만들어집니다. 다시 로그인해야 합니다.</DialogContent>
        <DialogActions><Button onClick={() => setConfirm(false)}>취소</Button><Button color="error" variant="contained" onClick={async () => {
          setConfirm(false); const r = await a.run(() => post('/system/demo-reset'), '초기화했습니다.'); if (r) setTimeout(() => { location.href = '/' }, 1200)
        }}>초기화</Button></DialogActions>
      </Dialog>
    </Box>
  )
}

const EMPTY_CO = { name: '', businessRegistrationNo: '', representativeName: '', employmentInsuranceNo: '', industry: '', address: '', phone: '', managerId: '', status: 'ACTIVE' }

function SysCompanies() {
  const q = useQ<any[]>(['companies-sa'], '/companies')
  const vms = useQ<any[]>(['users', 'VDREAM_MANAGER'], '/users', { role: 'VDREAM_MANAGER' })
  const a = useAct()
  const [f, setF] = useState<any>(null)
  const save = () => {
    const body = { ...f, managerId: f.managerId || null }
    delete body.id; delete body.managerName; delete body.activeWorkers; delete body.createdAt; delete body.updatedAt
    setF(null)
    return a.run(() => (f.id ? put(`/companies/${f.id}`, body) : post('/companies', body)), '저장했습니다.')
  }
  return (
    <Box>
      <PageTitle action={<Button variant="contained" onClick={() => setF({ ...EMPTY_CO })}>기업 등록</Button>}>기업 관리</PageTitle>
      <Status msg={a.msg} />
      <Loading q={q} />
      {q.data && <DataTable caption="기업" rows={q.data} onRow={(r: any) => setF({ ...r, managerId: r.managerId ?? '' })} cols={[
        { label: '기업명', render: (r: any) => r.name }, { label: '사업자번호', render: (r: any) => r.businessRegistrationNo }, { label: '담당 매니저', render: (r: any) => r.managerName ?? '미지정' },
        { label: '재직', render: (r: any) => r.activeWorkers }, { label: '상태', render: (r: any) => <StatusChip value={r.status} label={r.status === 'ACTIVE' ? '활성' : '비활성'} /> }]} />}
      <Dialog open={!!f} onClose={() => setF(null)} fullWidth>
        <DialogTitle>{f?.id ? '기업 수정' : '기업 등록'}</DialogTitle>
        <DialogContent><Stack spacing={2} sx={{ mt: 1 }}>
          {f && [['name', '기업명'], ['businessRegistrationNo', '사업자등록번호'], ['representativeName', '대표자명'], ['employmentInsuranceNo', '고용보험 사업장관리번호'], ['industry', '업종'], ['address', '주소'], ['phone', '대표 전화']]
            .map(([k, l]) => <TextField key={k} label={l} value={f[k] ?? ''} onChange={(e) => setF({ ...f, [k]: e.target.value })} />)}
          {f && <TextField select label="담당 매니저" value={f.managerId} onChange={(e) => setF({ ...f, managerId: e.target.value })}><MenuItem value="">미지정</MenuItem>{vms.data?.map((v) => <MenuItem key={v.id} value={v.id}>{v.name}</MenuItem>)}</TextField>}
          {f && <TextField select label="상태" value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}><MenuItem value="ACTIVE">활성</MenuItem><MenuItem value="INACTIVE">비활성</MenuItem></TextField>}
        </Stack></DialogContent>
        <DialogActions><Button onClick={() => setF(null)}>닫기</Button><Button variant="contained" disabled={!f?.name} onClick={save}>저장</Button></DialogActions>
      </Dialog>
    </Box>
  )
}

function SysUsers() {
  const [role, setRole] = useState('')
  const [kw, setKw] = useState('')
  const q = useQ<any[]>(['users', role, kw], '/users', { role: role || undefined, q: kw || undefined })
  const cos = useQ<any[]>(['companies-sa'], '/companies')
  const a = useAct()
  const [f, setF] = useState<any>(null)
  const save = () => {
    const b = { loginId: f.loginId, name: f.name, role: f.role, password: f.password || null, phone: f.phone || null, email: f.email || null, companyId: f.companyId || null, status: f.status }
    setF(null)
    return a.run(() => (f.id ? put(`/users/${f.id}`, b) : post('/users', b)), '저장했습니다.')
  }
  return (
    <Box>
      <PageTitle action={<Button variant="contained" onClick={() => setF({ loginId: '', name: '', role: 'WORKER', password: '', companyId: '', status: 'ACTIVE' })}>계정 생성</Button>}>계정 관리</PageTitle>
      <TextField select size="small" label="역할" value={role} onChange={(e) => setRole(e.target.value)} sx={{ mb: 2, minWidth: 180 }}>
        <MenuItem value="">전체</MenuItem>{['WORKER', 'COMPANY_MANAGER', 'VDREAM_MANAGER', 'SYSTEM_ADMIN'].map((x) => <MenuItem key={x} value={x}>{L[x]}</MenuItem>)}
      </TextField>
      <TextField size="small" label="이름·아이디 검색" value={kw} onChange={(e) => setKw(e.target.value)} sx={{ mb: 2, ml: 2 }} />
      <Status msg={a.msg} />
      <Loading q={q} />
      {q.data && <DataTable caption="계정" rows={q.data} onRow={(r: any) => setF({ ...r, password: '', companyId: r.companyId ?? '' })} cols={[
        { label: '아이디', render: (r: any) => r.loginId }, { label: '이름', render: (r: any) => r.name }, { label: '역할', render: (r: any) => lb(r.role) },
        { label: '소속', render: (r: any) => r.companyName ?? '-' }, { label: '데모', render: (r: any) => (r.isDemo ? '데모' : '') },
        { label: '상태', render: (r: any) => <StatusChip value={r.status} label={r.status === 'ACTIVE' ? '활성' : '비활성'} /> }]} />}
      <Dialog open={!!f} onClose={() => setF(null)} fullWidth>
        <DialogTitle>{f?.id ? '계정 수정' : '계정 생성'}</DialogTitle>
        <DialogContent><Stack spacing={2} sx={{ mt: 1 }}>
          {f && <>
            <TextField label="아이디" value={f.loginId} disabled={!!f.id} onChange={(e) => setF({ ...f, loginId: e.target.value })} />
            <TextField label="이름" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
            <TextField select label="역할" value={f.role} disabled={!!f.id} onChange={(e) => setF({ ...f, role: e.target.value })}>{['WORKER', 'COMPANY_MANAGER', 'VDREAM_MANAGER', 'SYSTEM_ADMIN'].map((x) => <MenuItem key={x} value={x}>{L[x]}</MenuItem>)}</TextField>
            {f.role === 'COMPANY_MANAGER' && <TextField select label="소속 기업" value={f.companyId} onChange={(e) => setF({ ...f, companyId: e.target.value })}>{cos.data?.map((c) => <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>)}</TextField>}
            <TextField label={f.id ? '새 비밀번호 (초기화할 때만)' : '초기 비밀번호'} type="password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} disabled={f.isDemo} />
            <FormControlLabel control={<Checkbox checked={f.status === 'ACTIVE'} disabled={f.isDemo} onChange={(e) => setF({ ...f, status: e.target.checked ? 'ACTIVE' : 'INACTIVE' })} />} label="활성" />
          </>}
        </Stack></DialogContent>
        <DialogActions><Button onClick={() => setF(null)}>닫기</Button><Button variant="contained" disabled={!f?.loginId || !f?.name} onClick={save}>저장</Button></DialogActions>
      </Dialog>
    </Box>
  )
}

function SysAnnouncements() {
  const q = useQ<any[]>(['announcements'], '/announcements')
  const a = useAct()
  const [f, setF] = useState<any>(null)
  const save = () => { const b = { title: f.title, content: f.content, audience: f.audience, isPinned: f.isPinned }; setF(null); return a.run(() => (f.id ? put(`/announcements/${f.id}`, b) : post('/announcements', b)), '저장했습니다.') }
  return (
    <Box>
      <PageTitle action={<Button variant="contained" onClick={() => setF({ title: '', content: '', audience: 'ALL', isPinned: false })}>공지 작성</Button>}>공지사항</PageTitle>
      <Status msg={a.msg} />
      <Loading q={q} />
      {q.data && <DataTable caption="공지" rows={q.data} onRow={(r: any) => setF(r)} cols={[{ label: '제목', render: (r: any) => r.title }, { label: '공개 범위', render: (r: any) => lb(r.audience) },
        { label: '고정', render: (r: any) => (r.isPinned ? '고정' : '') }, { label: '', render: (r: any) => <Button size="small" color="error" onClick={(e) => { e.stopPropagation(); a.run(() => del(`/announcements/${r.id}`), '삭제했습니다.') }}>삭제</Button> }]} />}
      <Dialog open={!!f} onClose={() => setF(null)} fullWidth>
        <DialogTitle>공지</DialogTitle>
        <DialogContent><Stack spacing={2} sx={{ mt: 1 }}>
          {f && <>
            <TextField label="제목" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} />
            <TextField label="본문" multiline minRows={4} value={f.content} onChange={(e) => setF({ ...f, content: e.target.value })} />
            <TextField select label="공개 범위" value={f.audience} onChange={(e) => setF({ ...f, audience: e.target.value })}>{['ALL', 'VDREAM', 'COMPANY', 'WORKER'].map((x) => <MenuItem key={x} value={x}>{x === 'ALL' ? '모두' : x === 'WORKER' ? '근로자' : L[x]}</MenuItem>)}</TextField>
            <FormControlLabel control={<Checkbox checked={f.isPinned} onChange={(e) => setF({ ...f, isPinned: e.target.checked })} />} label="상단 고정" />
          </>}
        </Stack></DialogContent>
        <DialogActions><Button onClick={() => setF(null)}>닫기</Button><Button variant="contained" disabled={!f?.title} onClick={save}>저장</Button></DialogActions>
      </Dialog>
    </Box>
  )
}

export default function SystemApp({ onToggleTheme }: { onToggleTheme: () => void }) {
  return (
    <Routes>
      <Route element={<AdminLayout base="/system" menu={SA_MENU} onToggleTheme={onToggleTheme} />}>
        <Route index element={<SysDashboard />} />
        <Route path="companies" element={<SysCompanies />} />
        <Route path="users" element={<SysUsers />} />
        <Route path="announcements" element={<SysAnnouncements />} />
        <Route path="me" element={<MyInfo />} />
      </Route>
    </Routes>
  )
}
