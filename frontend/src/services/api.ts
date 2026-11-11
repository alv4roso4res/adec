import type {
  CommitItem,
  HealthResponse,
  PipelineCurrent,
  PipelineHistory,
  PullItem,
  TeamMember,
  VersionInfo,
} from '../types/api'

const API_URL = (import.meta.env.VITE_API_URL ?? '/api').replace(/\/+$/, '')

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

// A API responde erros como {"detail": "..."}; usa essa mensagem quando existir.
async function errorMessage(response: Response): Promise<string> {
  const body = await response.text().catch(() => '')
  try {
    const detail = (JSON.parse(body) as { detail?: unknown }).detail
    if (typeof detail === 'string' && detail) return detail
  } catch {
    // corpo não é JSON (ex.: página do nginx enquanto a API reinicia)
  }
  return body || response.statusText || `Erro ${response.status}`
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_URL}${path.startsWith('/') ? path : `/${path}`}`
  const response = await fetch(url, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...init?.headers,
    },
  })

  if (!response.ok) {
    throw new ApiError(response.status, await errorMessage(response))
  }

  return (await response.json()) as T
}

// Um endpoint por card. `signal` cancela a requisição quando o card sai da tela.
type Opts = { signal?: AbortSignal }

export const getHealth = (o?: Opts) => request<HealthResponse>('/health', o)

export const getPipelineCurrent = (o?: Opts) =>
  request<PipelineCurrent>('/pipeline/current', o)

export const getPipelineHistory = (o?: Opts) =>
  request<PipelineHistory>('/pipeline/history?limit=20', o)

export const getPulls = (o?: Opts) => request<PullItem[]>('/pulls', o)

export const getTeam = (o?: Opts) => request<TeamMember[]>('/team', o)

export const getVersion = (o?: Opts) => request<VersionInfo>('/version', o)

export const getCommits = (o?: Opts) => request<CommitItem[]>('/commits?limit=6', o)
