import type {
  EndpointAResponse,
  EndpointBResponse,
  EndpointCResponse,
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
    const body = await response.text().catch(() => '')
    throw new ApiError(
      response.status,
      `Erro ${response.status} em ${path}: ${body || response.statusText}`,
    )
  }

  return (await response.json()) as T
}

//endpoints
export function getEndpointA(): Promise<EndpointAResponse> {
  return request<EndpointAResponse>('/endpoint-a')
}
export function getEndpointB(): Promise<EndpointBResponse> {
  return request<EndpointBResponse>('/endpoint-b')
}
export function getEndpointC(): Promise<EndpointCResponse> {
  return request<EndpointCResponse>('/endpoint-c')
}
