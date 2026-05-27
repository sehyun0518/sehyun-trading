const BASE = import.meta.env.VITE_API_URL ?? ''

function getToken(): string {
  return localStorage.getItem('auth_token') ?? ''
}

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function handleUnauthorized(status: number) {
  if (status === 401) {
    localStorage.removeItem('auth_token')
    window.location.href = '/login'
  }
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { headers: authHeaders() })
  handleUnauthorized(res.status)
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`)
  return res.json()
}

async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(body),
  })
  handleUnauthorized(res.status)
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`)
  return res.json()
}

export interface Holding {
  ticker: string; name: string; quantity: number; avg_price: number
  current_price: number; eval_amount: number
  eval_pl: number; eval_pl_pct: number
  stop_loss: number; take_profit: number; updated_at: string
}
export interface PortfolioSummary {
  total_eval: number; cash: number; total: number
  cash_ratio: number; position_count: number
  total_pl: number; total_pl_pct: number
}
export interface PortfolioResponse {
  mode: string; holdings: Holding[]; summary: PortfolioSummary
}

export interface Candidate {
  ticker: string; name: string; market: string | null
  market_cap_b: number | null; close: number; ma20: number
  ma20_diff_pct: number | null; rsi: number; volume_ratio: number
  foreign_net_5d: number; checks: Record<string, boolean>
  entry_price: number; stop_loss: number; take_profit: number
}
export interface CandidatesResponse {
  run_date: string; candidates: Candidate[]; warnings: unknown[]
}

export interface ReportMeta {
  date: string; candidates_count: number; file_path: string
}
export interface ReportDetail {
  date: string; content: string
  candidates: unknown[]; warnings: unknown[]
}

export interface UserInfo {
  id: number; email: string
  has_paper_creds: boolean; has_real_creds: boolean
  kis_paper_account: string | null; kis_real_account: string | null
}

export interface Order {
  id: number; user_id: number; ticker: string; name: string
  side: string; qty: number; price: number
  executed_at: string; kis_order_no: string
}

export type RankType = 'volume' | 'trading_value' | 'change_rate' | 'market_cap'
export interface RankItem {
  rank: number; ticker: string; name: string
  current_price: number; change_pct: number
  volume: number; trading_value: number; market_cap?: number
}
export interface RankingResponse { type: RankType; items: RankItem[] }

export interface CandidateSnapshot {
  id: number
  run_date: string
  ticker: string
  name: string
  source: string
  indicators: Record<string, number | string | null>
  entry_checks: Record<string, boolean>
  entry_price: number | null
  stop_loss: number | null
  take_profit: number | null
  created_at: string
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(body),
  })
  handleUnauthorized(res.status)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `API ${path} → ${res.status}`)
  }
  return res.json()
}

export const api = {
  portfolio:      () => get<PortfolioResponse>('/api/portfolio'),
  candidates:     () => get<CandidatesResponse>('/api/candidates'),
  reports:        () => get<ReportMeta[]>('/api/reports'),
  reportDetail:   (d: string) => get<ReportDetail>(`/api/reports/${d}`),
  setMode:        (mode: 'paper' | 'real') => put<{ mode: string }>('/api/mode', { mode }),
  me:             () => get<UserInfo>('/api/auth/me'),
  updateSettings: (body: Record<string, string>) => put<{ ok: boolean }>('/api/auth/settings', body),
  placeOrder:     (body: { ticker: string; name: string; side: string; qty: number }) =>
                    post<{ order_no: string; ticker: string; qty: number; side: string; price: number }>('/api/orders', body),
  orders:         () => get<Order[]>('/api/orders'),
  marketRanking:  (type: RankType) => get<RankingResponse>(`/api/market/ranking?type=${type}`),
  strategySnapshots: () => get<CandidateSnapshot[]>('/api/strategy/snapshots'),
}
