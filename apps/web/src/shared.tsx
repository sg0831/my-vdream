import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Box, Button, Checkbox, Chip, FormControlLabel, List, ListItemButton, ListItemText, MenuItem, Stack, Tab, Tabs, TextField, Typography } from '@mui/material'
import { del, post } from './api'
import type { MsgIn } from './api-types'
import { useAuth } from './auth'
import { kst } from './labels'
import { BackLink, Empty, Loading, PageTitle, Section, Status, useAct, useQ } from './ui'

/** 쪽지함 (MESG-005, MESG-006) — 모바일과 관리자 화면 공용 */
export function MessagesPage({ base }: { base: string }) {
  const [tab, setTab] = useState(0)
  const [unread, setUnread] = useState(false)
  const nav = useNavigate()
  const { me } = useAuth()
  const q = useQ<any[]>(['messages', tab, unread], tab === 0 ? '/messages/inbox' : '/messages/sent', tab === 0 ? { unread_only: unread } : undefined)
  return (
    <Box>
      <PageTitle action={me?.role !== 'SYSTEM_ADMIN' && <Button variant="contained" onClick={() => nav(`${base}/messages/new`)}>쪽지 쓰기</Button>}>쪽지</PageTitle>
      <Tabs value={tab} onChange={(_, v) => setTab(v)} aria-label="쪽지함 종류" sx={{ mb: 1 }}><Tab label="받은 쪽지" /><Tab label="보낸 쪽지" /></Tabs>
      {tab === 0 && <FormControlLabel control={<Checkbox checked={unread} onChange={(e) => setUnread(e.target.checked)} />} label="읽지 않은 쪽지만" />}
      <Loading q={q} />
      {q.data && !q.data.length && <Empty text="쪽지가 없습니다." />}
      <List>
        {q.data?.map((m) => (
          <ListItemButton key={m.id} divider onClick={() => nav(`${base}/messages/${m.id}`)}
            aria-label={`${tab === 0 ? `${m.sender.name}님이 보낸` : `${m.recipientCount}명에게 보낸`} 쪽지, ${m.title}${tab === 0 && !m.readAt ? ', 읽지 않음' : ''}`}>
            <ListItemText
              primary={<Stack direction="row" spacing={1} alignItems="center">{tab === 0 && !m.readAt && <Chip size="small" color="error" label="새 쪽지" />}<Typography sx={{ fontWeight: tab === 0 && !m.readAt ? 800 : 500 }}>{m.title}</Typography></Stack>}
              secondary={tab === 0 ? `${m.sender.name} · ${m.sender.roleLabel}${m.sender.companyName ? ` · ${m.sender.companyName}` : ''} · ${kst(m.createdAt)}`
                : `${m.recipientCount}명 중 ${m.readCount}명 읽음 · ${kst(m.createdAt)}`} />
          </ListItemButton>
        ))}
      </List>
    </Box>
  )
}

export function MessageDetail({ base }: { base: string }) {
  const { id } = useParams()
  const nav = useNavigate()
  const q = useQ<any>(['message', id], `/messages/${id}`)
  const a = useAct()
  const m = q.data
  return (
    <Box>
      <BackLink />
      <Loading q={q} />
      {m && (
        <>
          <PageTitle>{m.title}</PageTitle>
          <Typography color="text.secondary" sx={{ mb: 2 }}>{m.sender.name} · {m.sender.roleLabel} · {kst(m.createdAt)}</Typography>
          {m.parent && <Section title="원래 쪽지"><Typography sx={{ fontWeight: 700 }}>{m.parent.title}</Typography><Typography color="text.secondary">{m.parent.body}</Typography></Section>}
          <Typography sx={{ whiteSpace: 'pre-wrap', mb: 3 }}>{m.body}</Typography>
          {m.recipients && (
            <Section title={`받은 사람 ${m.recipients.length}명`}>
              {m.recipients.map((r: any) => <Typography key={r.id}>{r.name} ({r.roleLabel}) — {r.readAt ? `${kst(r.readAt)} 읽음` : '읽지 않음'}</Typography>)}
            </Section>
          )}
          <Stack direction="row" spacing={1}>
            {!m.isSender && (m.canReply
              ? <Button variant="contained" onClick={() => nav(`${base}/messages/new?to=${m.sender.id}&reply=${m.id}&title=${encodeURIComponent('RE: ' + m.title)}`)}>답장</Button>
              : <Typography color="text.secondary" role="note">이 사용자에게는 답장할 수 없습니다.</Typography>)}
            <Button color="error" onClick={() => a.run(() => del(`/messages/${m.id}?box=${m.isSender ? 'sent' : 'inbox'}`)).then(() => nav(`${base}/messages`))}>삭제</Button>
          </Stack>
          <Status msg={a.msg} />
        </>
      )}
    </Box>
  )
}

const AUDIENCES = [['INDIVIDUAL', '개별 선택'], ['COMPANY_MEMBERS', '특정 기업 전체'], ['ALL_WORKERS', '전체 근로자'], ['ALL_COMPANY_MANAGERS', '전체 기업 담당자'], ['ALL_USERS', '전체 사용자']]

/** 쪽지 쓰기. 대상 목록은 서버가 허용한 사람만 내려준다 (MESG-001~004) */
export function MessageCompose({ base }: { base: string }) {
  const sp = new URLSearchParams(location.search)
  const nav = useNavigate()
  const { me } = useAuth()
  const [selected, setSelected] = useState<number[]>(sp.get('to') ? [Number(sp.get('to'))] : [])
  const [search, setSearch] = useState('')
  const [audience, setAudience] = useState('INDIVIDUAL')
  const [companyId, setCompanyId] = useState<number | ''>('')
  const [title, setTitle] = useState(sp.get('title') ?? '')
  const [body, setBody] = useState('')
  const isVM = me?.role === 'VDREAM_MANAGER'
  const r = useQ<any>(['recipients', search], '/messages/recipients', isVM ? { q: search || undefined } : undefined)
  const companies = useQ<any[]>(['companies'], '/companies', undefined, { enabled: isVM })
  const a = useAct()
  const toggle = (id: number) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]))
  const payload: MsgIn = { recipientIds: selected, audience: audience as MsgIn['audience'], audienceCompanyId: companyId || null, title, body, parentMessageId: sp.get('reply') ? Number(sp.get('reply')) : null }
  const send = () => a.run(() => post('/messages', payload), '쪽지를 보냈습니다.')
    .then((res) => { if (res) setTimeout(() => nav(`${base}/messages`), 600) })
  return (
    <Box>
      <BackLink />
      <PageTitle>쪽지 쓰기</PageTitle>
      <Loading q={r} />
      {r.data && !r.data.canSend && <Typography role="note" sx={{ mb: 2 }}>재직 중인 기업이 생기면 쪽지를 보낼 수 있습니다.</Typography>}
      {r.data?.canSend && (
        <Stack spacing={2}>
          {isVM && (
            <TextField select label="받는 대상" value={audience} onChange={(e) => setAudience(e.target.value)}>
              {AUDIENCES.map(([v, l]) => <MenuItem key={v} value={v}>{l}</MenuItem>)}
            </TextField>
          )}
          {audience === 'COMPANY_MEMBERS' && (
            <TextField select label="대상 기업" value={companyId} onChange={(e) => setCompanyId(Number(e.target.value))}>
              {companies.data?.map((c) => <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>)}
            </TextField>
          )}
          {audience === 'INDIVIDUAL' && (
            <Box>
              {isVM && <TextField fullWidth label="이름 또는 아이디로 검색" value={search} onChange={(e) => setSearch(e.target.value)} sx={{ mb: 1 }} />}
              {r.data.managerMissing && <Typography color="text.secondary" role="note">담당 매니저가 지정되지 않았습니다.</Typography>}
              {r.data.groups.map((g: any) => (
                <Box key={g.label} sx={{ mb: 1.5 }} role="group" aria-label={g.label}>
                  <Typography sx={{ fontWeight: 700, mb: 0.5 }}>{g.label}</Typography>
                  <Stack direction="row" flexWrap="wrap" gap={1}>
                    {g.people.map((p: any) => (
                      <Button key={p.id} variant={selected.includes(p.id) ? 'contained' : 'outlined'} aria-pressed={selected.includes(p.id)} onClick={() => toggle(p.id)}>
                        {p.name}{p.companyName && g.label === '검색 결과' ? ` · ${p.companyName}` : ''} · {p.roleLabel}
                      </Button>
                    ))}
                  </Stack>
                </Box>
              ))}
              <Typography color="text.secondary">선택한 사람 {selected.length}명</Typography>
            </Box>
          )}
          <TextField label="제목" value={title} onChange={(e) => setTitle(e.target.value)} inputProps={{ maxLength: 100 }} />
          <TextField label="내용" value={body} onChange={(e) => setBody(e.target.value)} multiline minRows={5} inputProps={{ maxLength: 2000 }} helperText={`${body.length}/2000`} />
          <Button variant="contained" size="large" disabled={a.busy || !title.trim() || !body.trim() || (audience === 'INDIVIDUAL' && !selected.length)} onClick={send}>보내기</Button>
        </Stack>
      )}
      <Status msg={a.msg} />
    </Box>
  )
}

export function NotificationsPage() {
  const q = useQ<any[]>(['notifications'], '/notifications')
  const nav = useNavigate()
  const a = useAct()
  return (
    <Box>
      <PageTitle action={<Button onClick={() => a.run(() => post('/notifications/read-all'), '모두 읽음으로 표시했습니다.')}>모두 읽음</Button>}>알림</PageTitle>
      <Status msg={a.msg} />
      <Loading q={q} />
      {q.data && !q.data.length && <Empty text="알림이 없습니다." />}
      <List>
        {q.data?.map((n) => (
          <ListItemButton key={n.id} divider onClick={async () => { await post(`/notifications/${n.id}/read`); if (n.linkPath) nav(n.linkPath) }}>
            <ListItemText primary={<Typography sx={{ fontWeight: n.isRead ? 500 : 800 }}>{n.isRead ? '' : '● '}{n.title}</Typography>} secondary={`${n.body} · ${kst(n.createdAt)}`} />
          </ListItemButton>
        ))}
      </List>
    </Box>
  )
}

export function NoticesPage() {
  const q = useQ<any[]>(['announcements'], '/announcements')
  const [open, setOpen] = useState<number | null>(null)
  return (
    <Box>
      <PageTitle>공지사항</PageTitle>
      <Loading q={q} />
      {q.data?.map((n) => (
        <Section key={n.id}>
          <Button onClick={() => setOpen(open === n.id ? null : n.id)} aria-expanded={open === n.id} sx={{ justifyContent: 'flex-start', p: 0, textAlign: 'left' }}>
            {n.isPinned && <Chip size="small" label="고정" sx={{ mr: 1 }} />}{n.title}
          </Button>
          {open === n.id && <Typography sx={{ whiteSpace: 'pre-wrap', mt: 1 }}>{n.content}</Typography>}
        </Section>
      ))}
    </Box>
  )
}
