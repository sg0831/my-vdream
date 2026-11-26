import axios from 'axios'

export const TOKEN_KEY = 'myvdream.token'
export const api = axios.create({ baseURL: (import.meta.env.VITE_API_BASE_URL || '') + '/api/v1' })

api.interceptors.request.use((c) => {
  const t = localStorage.getItem(TOKEN_KEY)
  if (t) c.headers.Authorization = `Bearer ${t}`
  return c
})
api.interceptors.response.use((r) => r, (e) => {
  if (e.response?.status === 401 && !e.config.url?.includes('/auth/')) {
    localStorage.removeItem(TOKEN_KEY)
    if (location.pathname !== '/') location.href = '/'
  }
  return Promise.reject(e)
})

export async function get<T = any>(url: string, params?: object): Promise<T> {
  return (await api.get(url, { params })).data.data
}
export async function post<T = any>(url: string, body?: object): Promise<T> {
  return (await api.post(url, body ?? {})).data.data
}
export async function put<T = any>(url: string, body?: object): Promise<T> {
  return (await api.put(url, body ?? {})).data.data
}
export async function del<T = any>(url: string): Promise<T> {
  return (await api.delete(url)).data.data
}
export function errMsg(e: any): string {
  return e?.response?.data?.error?.message ?? '요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.'
}
export async function download(url: string, params: object, fallbackName: string) {
  const r = await api.get(url, { params, responseType: 'blob' })
  const cd: string = r.headers['content-disposition'] || ''
  const name = decodeURIComponent(cd.split("filename*=UTF-8''")[1] || fallbackName)
  const a = document.createElement('a')
  a.href = URL.createObjectURL(r.data)
  a.download = name
  a.click()
  URL.revokeObjectURL(a.href)
}
export async function openFile(id: number) {
  const r = await get<{ url: string }>(`/files/${id}/url`)
  window.open(r.url, '_blank')
}
