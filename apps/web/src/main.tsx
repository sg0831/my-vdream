import { lazy, StrictMode, Suspense, useEffect, useMemo, useState, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CssBaseline, ThemeProvider, useMediaQuery } from '@mui/material'
import { AuthProvider, homeOf, useAuth } from './auth'
import { makeTheme } from './theme'
import Landing from './pages/Landing'

// 역할 영역별 코드 분할: 랜딩은 바로, 나머지는 들어갈 때 내려받는다
const MobileApp = lazy(() => import('./pages/mobile'))
const AdminApp = lazy(() => import('./pages/admin'))
const SystemApp = lazy(() => import('./pages/system'))

const qc = new QueryClient({ defaultOptions: { queries: { staleTime: 5000, retry: 1, refetchOnWindowFocus: true } } })
const MODE_KEY = 'myvdream.theme'

function RequireRole({ roles, children }: { roles: string[]; children: ReactNode }) {
  const { me, loading } = useAuth()
  if (loading) return null
  if (!me) return <Navigate to="/" replace />
  if (!roles.includes(me.role)) return <Navigate to={homeOf(me.role)} replace />
  return <>{children}</>
}

/** /demo/:role 로 들어오면 해당 역할 데모 계정으로 로그인 후 그 화면으로 보낸다 (이력서 링크용) */
function DemoEntry() {
  const { role } = useParams()
  const { demo } = useAuth()
  const nav = useNavigate()
  const map: Record<string, string> = { worker: 'WORKER', company: 'COMPANY_MANAGER', manager: 'VDREAM_MANAGER', admin: 'SYSTEM_ADMIN' }
  useEffect(() => {
    const r = map[role ?? '']
    if (!r) { nav('/', { replace: true }); return }
    demo(r).then((u) => nav(homeOf(u.role), { replace: true })).catch(() => nav('/', { replace: true }))
  }, [role])  // eslint-disable-line
  return <p role="status" style={{ padding: 24 }}>데모 계정으로 들어가는 중입니다…</p>
}

function Themed() {
  const loc = useLocation()
  const prefersDark = useMediaQuery('(prefers-color-scheme: dark)')
  const [saved, setSaved] = useState<string | null>(() => { try { return localStorage.getItem(MODE_KEY) } catch { return null } })
  const mode = (saved ?? (prefersDark ? 'dark' : 'light')) as 'light' | 'dark'
  const area = loc.pathname.startsWith('/m') ? 'worker' : 'admin'
  const theme = useMemo(() => makeTheme(area, mode), [area, mode])
  const toggle = () => { const n = mode === 'dark' ? 'light' : 'dark'; setSaved(n); try { localStorage.setItem(MODE_KEY, n) } catch { /* ignore */ } }
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Suspense fallback={<p role="status" style={{ padding: 24 }}>불러오는 중입니다…</p>}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/demo/:role" element={<DemoEntry />} />
        <Route path="/m/*" element={<RequireRole roles={['WORKER']}><MobileApp onToggleTheme={toggle} /></RequireRole>} />
        <Route path="/admin/*" element={<RequireRole roles={['COMPANY_MANAGER', 'VDREAM_MANAGER']}><AdminApp onToggleTheme={toggle} /></RequireRole>} />
        <Route path="/system/*" element={<RequireRole roles={['SYSTEM_ADMIN']}><SystemApp onToggleTheme={toggle} /></RequireRole>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </Suspense>
    </ThemeProvider>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <AuthProvider><Themed /></AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
