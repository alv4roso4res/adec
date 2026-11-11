import type { RunStatus } from '../types/api'

// 145 -> "2m 25s"; 42 -> "42s"; 3725 -> "1h 2m"
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return '—'
  const s = Math.max(0, Math.round(seconds))
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ${s % 60}s`
  return `${Math.floor(m / 60)}h ${m % 60}m`
}

// ISO -> "agora", "há 5 min", "há 3 h", "há 2 d"
export function timeAgo(iso: string | null | undefined, now: number): string {
  if (!iso) return '—'
  const diff = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000))
  if (diff < 45) return 'agora'
  if (diff < 3600) return `há ${Math.round(diff / 60)} min`
  if (diff < 86400) return `há ${Math.round(diff / 3600)} h`
  return `há ${Math.round(diff / 86400)} d`
}

export function firstLine(text: string): string {
  return text.split('\n', 1)[0]
}

// "Merge pull request #6 from owner/feat/x" -> "Merge #6 · feat/x"
export function prettyCommit(message: string): string {
  const line = firstLine(message)
  const merge = /^Merge pull request #(\d+) from [^/]+\/(.+)$/.exec(line)
  return merge ? `Merge #${merge[1]} · ${merge[2]}` : line
}

// Mensagens da API/navegador -> texto curto em português para o card.
export function friendlyError(message: string): string {
  const m = message.toLowerCase()
  if (m.includes('requires authentication') || m.includes('bad credentials')) {
    return 'A API precisa de um GITHUB_TOKEN para ler isto.'
  }
  if (m.includes('rate limit')) return 'Limite de requisições do GitHub atingido.'
  if (m.includes('failed to fetch') || m.includes('networkerror') || m.includes('bad gateway')) {
    return 'API fora do ar. Tentando reconectar…'
  }
  return message
}

export type Tone = 'success' | 'failure' | 'running' | 'queued' | 'neutral'

export const STATUS_META: Record<RunStatus, { label: string; tone: Tone }> = {
  success: { label: 'Sucesso', tone: 'success' },
  failure: { label: 'Falhou', tone: 'failure' },
  in_progress: { label: 'Rodando', tone: 'running' },
  queued: { label: 'Na fila', tone: 'queued' },
  cancelled: { label: 'Cancelado', tone: 'neutral' },
  skipped: { label: 'Pulado', tone: 'neutral' },
}

export function isActive(status: RunStatus | null | undefined): boolean {
  return status === 'in_progress' || status === 'queued'
}
