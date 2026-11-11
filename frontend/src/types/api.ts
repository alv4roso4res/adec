// Contratos da API (JSON em camelCase). Espelham os schemas em api/src/api/schemas/.

export type RunStatus =
  | 'queued'
  | 'in_progress'
  | 'success'
  | 'failure'
  | 'cancelled'
  | 'skipped'

// GET /api/health
export interface HealthResponse {
  status: string
  version: string
  repository: string
  writeActionsEnabled: boolean
}

// GET /api/pipeline/current (card 1)
export interface PipelineStep {
  name: string
  status: RunStatus
  number: number
}

export interface PipelineJob {
  name: string
  status: RunStatus
  durationSeconds: number | null
  steps: PipelineStep[]
}

export interface PipelineRun {
  id: number
  status: RunStatus
  event: string
  branch: string
  headSha: string
  commitMessage: string
  actor: string
  startedAt: string | null
  durationSeconds: number | null
  htmlUrl: string
}

export interface PipelineCurrent {
  run: PipelineRun | null
  jobs: PipelineJob[]
}

// GET /api/pipeline/history (card 2)
export interface HistoryRun {
  id: number
  status: RunStatus
  event: string
  branch: string
  headSha: string
  durationSeconds: number | null
  createdAt: string
}

export interface HistoryStats {
  total: number
  successRate: number | null
  avgDurationSeconds: number | null
  deploys: number
  byEvent: Record<string, number>
}

export interface PipelineHistory {
  runs: HistoryRun[]
  stats: HistoryStats
}

// GET /api/pulls (card 3)
export type PullBadge =
  | 'draft'
  | 'conflict'
  | 'checks_failed'
  | 'waiting_checks'
  | 'computing'
  | 'needs_approval'
  | 'ready'

export interface PullItem {
  number: number
  title: string
  author: { login: string; avatarUrl: string }
  createdAt: string
  htmlUrl: string
  headSha: string
  checks: { passed: number; failed: number; pending: number }
  approvals: number
  badge: PullBadge
  canApprove: boolean
  canMerge: boolean
}

// GET /api/team (card 4)
export interface TeamMember {
  login: string
  avatarUrl: string
  prsOpen: number
  prsMerged: number
  commits: number
  meetsRequirement: boolean
}

// GET /api/version (card 5)
export type VersionState =
  | 'up_to_date'
  | 'restart_pending'
  | 'building'
  | 'pipeline_failed'
  | 'dev'

export interface VersionInfo {
  running: string
  mainSha: string | null
  images: { name: string; publishedSha: string | null }[]
  state: VersionState
}

// GET /api/commits (card 6)
export interface CommitItem {
  sha: string
  shortSha: string
  message: string
  author: { login: string | null; name: string; avatarUrl: string | null }
  committedAt: string
  htmlUrl: string
  pipelineStatus: RunStatus | null
}
