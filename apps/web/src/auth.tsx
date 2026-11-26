import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { get, post, TOKEN_KEY } from './api'

export type Me = { id: number; loginId: string; name: string; role: string; companyId: number | null; companyName: string | null; isDemo: boolean;
  phone?: string; email?: string; employment?: { id: number; companyId: number; companyName: string; status: string } | null }
type Ctx = { me: Me | null; loading: boolean; demo: (role: string) => Promise<Me>; login: (id: string, pw: string) => Promise<Me>; logout: () => void; reload: () => Promise<void> }
const AuthCtx = createContext<Ctx>(null!)
export const useAuth = () => useContext(AuthCtx)
export const homeOf = (role: string) => (role === 'WORKER' ? '/m' : role === 'SYSTEM_ADMIN' ? '/system' : '/admin')

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(true)
  const qc = useQueryClient()
  const reload = useCallback(async () => {
    if (!localStorage.getItem(TOKEN_KEY)) { setMe(null); setLoading(false); return }
    try { setMe(await get<Me>('/auth/me')) } catch { setMe(null) } finally { setLoading(false) }
  }, [])
  useEffect(() => { reload() }, [reload])
  const accept = (r: { token: string; user: Me }) => { localStorage.setItem(TOKEN_KEY, r.token); qc.clear(); setMe(r.user); return r.user }
  const demo = async (role: string) => accept(await post('/auth/demo-login', { role }))
  const login = async (loginId: string, password: string) => accept(await post('/auth/login', { loginId, password }))
  const logout = () => { localStorage.removeItem(TOKEN_KEY); qc.clear(); setMe(null) }
  return <AuthCtx.Provider value={{ me, loading, demo, login, logout, reload }}>{children}</AuthCtx.Provider>
}
