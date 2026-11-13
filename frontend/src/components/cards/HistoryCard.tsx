import { useState } from 'react'
import { usePolling } from '../../hooks/usePolling'
import { getPipelineHistory } from '../../services/api'
import { STATUS_META, formatDuration, timeAgo } from '../../utils/format'
import GlassCard from '../GlassCard'
import StatusIcon from '../StatusIcon'

// Filtros da legenda: cada botão mostra só os runs daquele tipo de evento.
type EventFilter = 'push' | 'pull_request'

const FILTERS: { value: EventFilter; label: string; empty: string }[] = [
  { value: 'push', label: 'push na main', empty: 'Nenhum push na main.' },
  { value: 'pull_request', label: 'pull request', empty: 'Nenhum run de pull request.' },
]

// Card 2: barrinhas dos últimos runs (altura = duração, cor = resultado).
// Clicar na legenda troca o gráfico pela lista dos runs daquele tipo.
function HistoryCard() {
  const poll = usePolling(getPipelineHistory, 15000)
  const [filter, setFilter] = useState<EventFilter | null>(null)

  // Clicar no filtro ativo volta para o gráfico.
  const toggle = (value: EventFilter) => setFilter((cur) => (cur === value ? null : value))

  return (
    <GlassCard title="Últimos runs" icon="chart" poll={poll} className="area-history">
      {({ runs, stats }, now) => {
        // A API manda do mais novo para o mais antigo; o gráfico lê da esquerda.
        const ordered = [...runs].reverse()
        const max = Math.max(1, ...ordered.map((r) => r.durationSeconds ?? 0))
        const rate = stats.successRate == null ? '—' : `${Math.round(stats.successRate * 100)}%`
        const active = FILTERS.find((f) => f.value === filter)
        const filtered = runs.filter((r) => r.event === filter)

        return (
          <>
            <div className="stats">
              <div className="stat">
                <span className="stat-value">{rate}</span>
                <span className="muted">sucesso</span>
              </div>
              <div className="stat">
                <span className="stat-value">{formatDuration(stats.avgDurationSeconds)}</span>
                <span className="muted">média</span>
              </div>
              <div className="stat">
                <span className="stat-value">{stats.deploys}</span>
                <span className="muted">deploys</span>
              </div>
            </div>

            {active ? (
              filtered.length === 0 ? (
                <p className="empty">{active.empty}</p>
              ) : (
                // Lista com rolagem (barra escondida), do mais novo para o mais antigo.
                <ul className="list scroll-hidden">
                  {filtered.map((run) => (
                    <li key={run.id} className="row run">
                      <StatusIcon status={run.status} size={18} />
                      <span className="row-title" title={`${run.branch} · ${STATUS_META[run.status].label}`}>
                        {run.branch}
                      </span>
                      <span className="sha mono">{run.headSha.slice(0, 7)}</span>
                      <span className="muted small nowrap run-duration">
                        {formatDuration(run.durationSeconds)}
                      </span>
                      <span className="muted small nowrap row-time">{timeAgo(run.createdAt, now)}</span>
                    </li>
                  ))}
                </ul>
              )
            ) : ordered.length === 0 ? (
              <p className="empty">Nenhum run ainda.</p>
            ) : (
              <div className="bars">
                {ordered.map((run) => {
                  const meta = STATUS_META[run.status]
                  const height = Math.max(8, ((run.durationSeconds ?? 0) / max) * 100)
                  return (
                    <span
                      key={run.id}
                      className={`bar tone-${meta.tone} ${run.event === 'push' ? 'is-push' : ''}`}
                      style={{ height: `${height}%` }}
                      title={`${run.branch} · ${run.event} · ${meta.label} · ${formatDuration(run.durationSeconds)}`}
                    />
                  )
                })}
              </div>
            )}

            <div className="legend" role="group" aria-label="Filtrar runs por evento">
              {FILTERS.map((f) => (
                <button
                  key={f.value}
                  type="button"
                  className={`legend-item ${filter === f.value ? 'is-active' : ''}`}
                  aria-pressed={filter === f.value}
                  title={filter === f.value ? 'Voltar para o gráfico' : `Ver os runs de ${f.label}`}
                  onClick={() => toggle(f.value)}
                >
                  <i className={`dot ${f.value === 'push' ? 'is-push' : ''}`} />
                  {f.label}
                  <span className="legend-count">{stats.byEvent[f.value] ?? 0}</span>
                </button>
              ))}
            </div>
          </>
        )
      }}
    </GlassCard>
  )
}

export default HistoryCard
