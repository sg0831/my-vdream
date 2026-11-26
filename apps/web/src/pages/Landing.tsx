import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Box, Button, Card, CardContent, Chip, Container, Link, Stack, TextField, Typography } from '@mui/material'
import { errMsg } from '../api'
import { homeOf, useAuth } from '../auth'
import { tokens } from '../theme'

const ROLES = [
  { role: 'WORKER', title: '장애인 근로자', color: tokens.mint[700], desc: ['휴대폰 화면으로 출퇴근·업무·업무일지', '담당자·담당 매니저에게 쪽지'] },
  { role: 'COMPANY_MANAGER', title: '기업 담당자', color: tokens.violet[500], desc: ['업무 배정, 업무일지 확인, 근태 관리', '월간 장애인 고용 리포트'] },
  { role: 'VDREAM_MANAGER', title: '브이드림 매니저', color: tokens.violet[700], desc: ['공고 승인, 채용 진행, 상담보고서', '모든 사용자에게 쪽지·단체 발송'] },
  { role: 'SYSTEM_ADMIN', title: '시스템관리자', color: tokens.navy[800], desc: ['기업·계정·공지 관리', '데모 데이터 초기화'] },
]
const STACK = ['FastAPI', 'SQLAlchemy 2', 'MySQL 8.4', 'React 18', 'TypeScript', 'MUI', 'TanStack Query', 'Docker Compose', 'Caddy', 'AWS EC2 · S3', 'GitHub Actions CI/CD']

export default function Landing() {
  const { me, demo, login } = useAuth()
  const nav = useNavigate()
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState('')
  const [f, setF] = useState({ id: '', pw: '' })
  const enter = async (fn: () => Promise<any>, key: string) => {
    setBusy(key); setErr('')
    try { const u = await fn(); nav(homeOf(u.role)) } catch (e) { setErr(errMsg(e)) } finally { setBusy('') }
  }
  return (
    <Box sx={{ bgcolor: '#FFFFFF', color: tokens.gray[90], minHeight: '100vh' }}>
      <Box component="header" sx={{ bgcolor: tokens.navy[950], color: '#FFFFFF', py: { xs: 6, md: 10 }, position: 'relative', overflow: 'hidden' }}>
        <Box aria-hidden sx={{ position: 'absolute', inset: 0, background: `radial-gradient(600px 300px at 15% 20%, ${tokens.mint[500]}44, transparent), radial-gradient(500px 300px at 85% 70%, ${tokens.violet[500]}66, transparent)` }} />
        <Container sx={{ position: 'relative' }}>
          <Typography sx={{ color: tokens.mint[300], fontWeight: 800, mb: 1 }}>my-vdream · 포트폴리오 프로젝트</Typography>
          <Typography component="h1" sx={{ fontSize: { xs: 30, md: 46 }, fontWeight: 800, lineHeight: 1.25 }}>
            장애인 재택근무,<br /><Box component="span" sx={{ color: tokens.mint[500] }}>채용부터 근태·업무·고용 리포트까지</Box> 한곳에서
          </Typography>
          <Typography sx={{ mt: 2, maxWidth: 680, color: '#E5E7EB', fontSize: 18 }}>
            브이드림의 재택근무 관리 방식을 벤치마킹해 근로자, 기업 담당자, 브이드림 매니저가 같은 정보를 보는 시스템을 만들었습니다.
            아래 버튼을 누르면 비밀번호 없이 각 역할의 화면으로 들어갑니다.
          </Typography>
          {me && <Button sx={{ mt: 3 }} variant="contained" onClick={() => nav(homeOf(me.role))}>{me.name}님 화면으로 돌아가기</Button>}
        </Container>
      </Box>
      <Container component="main" sx={{ py: 5 }}>
        <Typography component="h2" variant="h2" sx={{ mb: 2 }}>역할별로 체험하기</Typography>
        {err && <Alert severity="error" sx={{ mb: 2 }}>{err}</Alert>}
        <Stack direction="row" flexWrap="wrap" gap={2}>
          {ROLES.map((r) => (
            <Card key={r.role} variant="outlined" sx={{ flex: '1 1 230px', borderTop: `6px solid ${r.color}` }}>
              <CardContent>
                <Typography component="h3" sx={{ fontWeight: 800, fontSize: 20, mb: 1 }}>{r.title}</Typography>
                {r.desc.map((d) => <Typography key={d} sx={{ color: tokens.gray[60] }}>· {d}</Typography>)}
                <Button fullWidth variant="contained" sx={{ mt: 2, minHeight: 48, bgcolor: r.color, color: '#FFFFFF', '&:hover': { bgcolor: r.color, filter: 'brightness(1.1)' } }}
                  disabled={!!busy} onClick={() => enter(() => demo(r.role), r.role)}>{busy === r.role ? '들어가는 중…' : `${r.title}로 체험하기`}</Button>
              </CardContent>
            </Card>
          ))}
        </Stack>
        <Typography sx={{ mt: 2, color: tokens.gray[60] }}>근로자 화면은 데스크톱에서 휴대폰 크기로 보여 드립니다. 데이터는 가상 인물이며 시스템관리자가 언제든 초기화할 수 있습니다. 실제 개인정보는 입력하지 마세요.</Typography>

        <Stack direction={{ xs: 'column', md: 'row' }} gap={3} sx={{ mt: 6 }}>
          <Box sx={{ flex: 1 }}>
            <Typography component="h2" variant="h2" sx={{ mb: 1 }}>해결하는 문제</Typography>
            {['재택 근로자의 출퇴근을 메신저로 보고 → 버튼 한 번으로 기록, 지각·조퇴·결근 자동 판정', '업무를 메일로 전달 → 배정·진행·완료를 양쪽 화면에서 추적',
              '업무일지가 흩어짐 → 근무일별 일지 제출과 기업 확인·보완 요청', '공단 제출 증빙 수작업 → 근태·업무일지로 월간 장애인 고용 리포트 자동 생성(월 60시간, 중증 2배수 참고 판정)',
              '연락 창구 혼선 → 자기 기업 담당자·담당 매니저에게만 보낼 수 있는 쪽지'].map((t) => <Typography key={t} sx={{ mb: 0.75 }}>· {t}</Typography>)}
          </Box>
          <Box sx={{ flex: 1 }}>
            <Typography component="h2" variant="h2" sx={{ mb: 1 }}>아키텍처</Typography>
            <Box role="img" aria-label="브라우저의 React 앱이 Caddy를 거쳐 FastAPI로 요청하고, FastAPI는 MySQL과 S3를 사용합니다. GitHub Actions가 main 머지 시 EC2로 배포합니다."
              sx={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr auto 1fr', alignItems: 'center', gap: 1, textAlign: 'center', fontWeight: 700 }}>
              <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: tokens.mint[50], color: tokens.gray[90], border: `2px solid ${tokens.mint[500]}` }}>React SPA<br />/ · /m · /admin</Box><span>→</span>
              <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: tokens.violet[50], color: tokens.violet[700] }}>Caddy<br />HTTPS</Box><span>→</span>
              <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: tokens.violet[50], color: tokens.violet[700] }}>FastAPI<br />MySQL · S3</Box>
            </Box>
            <Typography sx={{ mt: 1, color: tokens.gray[60] }}>main 브랜치에 PR이 머지되면 GitHub Actions가 이미지를 빌드해 GHCR에 올리고 EC2에 자동 배포합니다.</Typography>
            <Stack direction="row" flexWrap="wrap" gap={1} sx={{ mt: 2 }}>{STACK.map((s) => <Chip key={s} label={s} />)}</Stack>
          </Box>
        </Stack>

        <Box sx={{ mt: 6, maxWidth: 420 }}>
          <Typography component="h2" variant="h3" sx={{ mb: 1 }}>아이디로 로그인</Typography>
          <Stack spacing={1.5} component="form" onSubmit={(e) => { e.preventDefault(); enter(() => login(f.id, f.pw), 'login') }}>
            <TextField size="small" label="아이디" value={f.id} onChange={(e) => setF({ ...f, id: e.target.value })} autoComplete="username" />
            <TextField size="small" label="비밀번호" type="password" value={f.pw} onChange={(e) => setF({ ...f, pw: e.target.value })} autoComplete="current-password" />
            <Button type="submit" variant="outlined" disabled={!!busy}>로그인</Button>
          </Stack>
        </Box>
        <Typography sx={{ mt: 6, color: tokens.gray[60] }}>
          브랜드 색은 브이드림·브이매치·브이워크 사이트에서 조사한 값을 사용했으며 로고는 사용하지 않았습니다. 이 사이트는 브이드림과 관련 없는 개인 포트폴리오입니다.
          {' '}<Link href="https://github.com" color="inherit">GitHub</Link>
        </Typography>
      </Container>
    </Box>
  )
}
