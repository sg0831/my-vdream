import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Alert, Badge, Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle, IconButton, Menu, MenuItem,
  Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Tooltip, Typography, useMediaQuery,
} from '@mui/material'
import MailOutlineIcon from '@mui/icons-material/MailOutline'
import NotificationsNoneIcon from '@mui/icons-material/NotificationsNone'
import SwapHorizIcon from '@mui/icons-material/SwapHoriz'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import HomeOutlinedIcon from '@mui/icons-material/HomeOutlined'
import DarkModeOutlinedIcon from '@mui/icons-material/DarkModeOutlined'
import { errMsg, get } from './api'
import { homeOf, useAuth } from './auth'
import { lb, tone, tokens } from './labels-tokens'

export { lb, tone }

export function useQ<T = any>(key: unknown[], url: string, params?: object, opts: object = {}) {
  return useQuery<T>({ queryKey: [...key, params], queryFn: () => get<T>(url, params), ...opts })
}

/** 변경 요청 + 결과를 화면 텍스트로 남기는 훅 (자동 닫힘 토스트 금지, ACCS-008) */
export function useAct() {
  const qc = useQueryClient()
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const m = useMutation({
    mutationFn: async ({ fn }: { fn: () => Promise<any>; done?: string }) => fn(),
    onSuccess: (_d, v) => { qc.invalidateQueries(); if (v.done) setMsg({ ok: true, text: v.done }) },
    onError: (e) => setMsg({ ok: false, text: errMsg(e) }),
  })
  const run = (fn: () => Promise<any>, done?: string) => m.mutateAsync({ fn, done }).catch(() => undefined)
  return { run, busy: m.isPending, msg, setMsg }
}

export function Status({ msg }: { msg: { ok: boolean; text: string } | null }) {
  return (
    <Box role="status" aria-live="polite" sx={{ my: msg ? 1.5 : 0 }}>
      {msg && <Alert severity={msg.ok ? 'success' : 'error'}>{msg.text}</Alert>}
    </Box>
  )
}

export function StatusChip({ value, label }: { value?: string | null; label?: string }) {
  const c = tone(value)
  const s = c === 'default' ? null : tokens.status[c]
  return <Chip component="span" size="small" label={label ?? lb(value)} sx={s ? { bgcolor: s.bg, color: s.text, fontWeight: 700 } : { fontWeight: 700 }} />
}

export function PageTitle({ children, action }: { children: ReactNode; action?: ReactNode }) {
  const ref = useRef<HTMLHeadingElement>(null)
  useEffect(() => { ref.current?.focus() }, [])
  return (
    <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2, gap: 1, flexWrap: 'wrap' }}>
      <Typography variant="h1" component="h1" tabIndex={-1} ref={ref} sx={{ outline: 'none' }}>{children}</Typography>
      {action}
    </Stack>
  )
}

export function Section({ title, children, action }: { title?: string; children: ReactNode; action?: ReactNode }) {
  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardContent>
        {(title || action) && (
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
            {title && <Typography variant="h3" component="h2">{title}</Typography>}
            {action}
          </Stack>
        )}
        {children}
      </CardContent>
    </Card>
  )
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <Card variant="outlined" sx={{ flex: '1 1 150px' }}>
      <CardContent>
        <Typography variant="body2" color="text.secondary">{label}</Typography>
        <Typography sx={{ fontSize: 28, fontWeight: 800 }}>{value}</Typography>
        {hint && <Typography variant="body2" color="text.secondary">{hint}</Typography>}
      </CardContent>
    </Card>
  )
}

export function Loading({ q }: { q: { isLoading: boolean; error: unknown } }) {
  if (q.isLoading) return <Typography role="status">불러오는 중입니다…</Typography>
  if (q.error) return <Alert severity="error">{errMsg(q.error)}</Alert>
  return null
}

export function Empty({ text = '표시할 내용이 없습니다.' }: { text?: string }) {
  return <Typography color="text.secondary" sx={{ py: 2 }}>{text}</Typography>
}

export type Col<T> = { label: string; render: (r: T) => ReactNode; width?: number | string }
export function DataTable<T>({ rows, cols, onRow, caption }: { rows: T[]; cols: Col<T>[]; onRow?: (r: T) => void; caption: string }) {
  if (!rows.length) return <Empty />
  return (
    <TableContainer>
      <Table size="small">
        <caption style={{ position: 'absolute', left: -9999 }}>{caption}</caption>
        <TableHead><TableRow>{cols.map((c) => <TableCell key={c.label} scope="col" sx={{ fontWeight: 700, width: c.width }}>{c.label}</TableCell>)}</TableRow></TableHead>
        <TableBody>
          {rows.map((r, i) => (
            <TableRow key={i} hover={!!onRow} onClick={onRow ? () => onRow(r) : undefined} sx={onRow ? { cursor: 'pointer' } : undefined}
              tabIndex={onRow ? 0 : undefined} onKeyDown={onRow ? (e) => { if (e.key === 'Enter') onRow(r) } : undefined}>
              {cols.map((c) => <TableCell key={c.label}>{c.render(r)}</TableCell>)}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

/** 사유 입력 등 간단한 확인 대화상자 */
export function PromptDialog({ open, title, label, required, onClose, onOk, okText = '확인' }: {
  open: boolean; title: string; label?: string; required?: boolean; onClose: () => void; onOk: (v: string) => void; okText?: string
}) {
  const [v, setV] = useState('')
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>{title}</DialogTitle>
      {label && <DialogContent><TextField autoFocus fullWidth multiline minRows={2} label={label} value={v} onChange={(e) => setV(e.target.value)} sx={{ mt: 1 }} /></DialogContent>}
      <DialogActions>
        <Button onClick={onClose}>닫기</Button>
        <Button variant="contained" disabled={required && !v.trim()} onClick={() => { onOk(v); setV(''); onClose() }}>{okText}</Button>
      </DialogActions>
    </Dialog>
  )
}

/** 미읽음 알림·쪽지 배지. 10초마다 갱신 (NOTI-005, MESG-010) */
export function UnreadBadges({ base }: { base: string }) {
  const nav = useNavigate()
  const q = useQ<{ notifications: number; messages: number }>(['unread'], '/me/unread-counts', undefined, { refetchInterval: 10000, refetchIntervalInBackground: false })
  const n = q.data?.notifications ?? 0
  const m = q.data?.messages ?? 0
  return (
    <Stack direction="row">
      <IconButton aria-label={`쪽지함, 읽지 않은 쪽지 ${m}개`} onClick={() => nav(`${base}/messages`)} color="inherit">
        <Badge badgeContent={m} color="error"><MailOutlineIcon /></Badge>
      </IconButton>
      <IconButton aria-label={`알림, 읽지 않은 알림 ${n}개`} onClick={() => nav(`${base}/notifications`)} color="inherit">
        <Badge badgeContent={n} color="error"><NotificationsNoneIcon /></Badge>
      </IconButton>
    </Stack>
  )
}

const ROLES = [['WORKER', '근로자'], ['COMPANY_MANAGER', '기업 담당자'], ['VDREAM_MANAGER', '브이드림 매니저'], ['SYSTEM_ADMIN', '시스템관리자']]

export function RoleSwitcher({ compact }: { compact?: boolean }) {
  const { me, demo } = useAuth()
  const nav = useNavigate()
  const [el, setEl] = useState<HTMLElement | null>(null)
  if (!me?.isDemo) return null
  return (
    <>
      <Button color="inherit" startIcon={<SwapHorizIcon />} onClick={(e) => setEl(e.currentTarget)} aria-haspopup="menu" size={compact ? 'small' : 'medium'}>
        다른 역할로 보기
      </Button>
      <Menu anchorEl={el} open={!!el} onClose={() => setEl(null)}>
        {ROLES.map(([r, l]) => (
          <MenuItem key={r} selected={me.role === r} onClick={async () => { setEl(null); const u = await demo(r); nav(homeOf(u.role)) }}>{l}</MenuItem>
        ))}
      </Menu>
    </>
  )
}

export function ThemeToggle({ onToggle }: { onToggle: () => void }) {
  return <Tooltip title="밝게/어둡게 전환"><IconButton aria-label="밝은 테마와 어두운 테마 전환" onClick={onToggle} color="inherit"><DarkModeOutlinedIcon /></IconButton></Tooltip>
}

/** 데스크톱에서 근로자 화면을 휴대폰 프레임 안에 보여준다 (DEMO-003, DEMO-004) */
export function PhoneFrame({ children }: { children: ReactNode }) {
  const wide = useMediaQuery('(min-width:600px)')
  const standalone = new URLSearchParams(location.search).get('standalone') === '1' || window.name === 'myvdream_mobile'
  const nav = useNavigate()
  const [blocked, setBlocked] = useState(false)
  const short = useMediaQuery('(max-height:920px)')
  if (!wide || standalone) return <Box sx={{ minHeight: '100dvh' }}>{children}</Box>
  const openPopup = () => {
    const w = window.open('/m?standalone=1', 'myvdream_mobile', 'width=390,height=844,resizable=yes')
    setBlocked(!w)
  }
  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4, p: 2, flexWrap: 'wrap',
      background: `linear-gradient(135deg, ${tokens.mint.gradientStart} 0%, ${tokens.mint[500]} 45%, ${tokens.mint[700]} 100%)` }}>
      <Stack spacing={1.5} sx={{ color: '#FFFFFF', maxWidth: 260 }}>
        <Typography sx={{ fontWeight: 800, fontSize: 22 }}>my-vdream<br />근로자 화면</Typography>
        <Typography sx={{ color: '#FFFFFF', opacity: 0.95 }}>실제 휴대폰에서는 화면 전체로 보입니다. 데스크톱에서는 휴대폰 크기(390×844)로 보여 드립니다.</Typography>
        <Box sx={{ bgcolor: tokens.navy[950], borderRadius: 2, p: 1 }}><RoleSwitcher compact /></Box>
        <Button variant="contained" startIcon={<OpenInNewIcon />} onClick={openPopup} sx={{ bgcolor: tokens.navy[950], color: '#FFFFFF' }}>새 창으로 열기</Button>
        {blocked && <Alert severity="info">팝업이 차단되었습니다. 현재 화면에서 그대로 보셔도 됩니다.</Alert>}
        <Button variant="outlined" startIcon={<HomeOutlinedIcon />} onClick={() => nav('/')} sx={{ color: '#FFFFFF', borderColor: '#FFFFFF' }}>처음 화면으로</Button>
      </Stack>
      <Box sx={{ width: 390 + 24, height: 844 + 24, p: '12px', borderRadius: '48px', bgcolor: tokens.navy[950], boxShadow: '0 30px 80px rgba(12,9,24,.45)',
        transform: short ? 'scale(0.8)' : undefined, transformOrigin: 'center', flexShrink: 0 }}>
        <Box sx={{ width: 390, height: 844, borderRadius: '38px', overflow: 'hidden', position: 'relative', bgcolor: 'background.default', containerType: 'inline-size' }}>
          {children}
        </Box>
      </Box>
      <Card sx={{ maxWidth: 260, bgcolor: 'rgba(255,255,255,0.96)', color: tokens.gray[90] }}>
        <CardContent>
          <Typography sx={{ fontWeight: 800, mb: 1 }}>이 화면에서 해볼 것</Typography>
          <Typography component="ol" sx={{ pl: 2.5, m: 0, '& li': { mb: 0.75 } }}>
            <li>홈에서 <b>출근하기</b>를 누르세요.</li>
            <li>업무 탭에서 업무를 <b>시작·완료</b>하세요.</li>
            <li>일지 탭에서 업무일지를 <b>작성·제출</b>하세요.</li>
            <li>상단 봉투에서 담당자에게 <b>쪽지</b>를 보내 보세요.</li>
          </Typography>
        </CardContent>
      </Card>
    </Box>
  )
}

export function BackLink() {
  const nav = useNavigate()
  return <Button onClick={() => nav(-1)} sx={{ mb: 1, px: 0 }}>← 뒤로</Button>
}

export function errorText(e: unknown) { return errMsg(e) }
