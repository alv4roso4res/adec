import { usePolling } from '../../hooks/usePolling'
import { getPipelineHistory } from '../../services/api'
import { STATUS_META, formatDuration } from '../../utils/format'
import GlassCard from '../GlassCard'

// Card 2: barrinhas dos últimos runs (altura = duração, cor = resultado).
function HistoryCard() {
  const poll = usePolling(getPipelineHistory, 15000)

  return (
    <GlassCard title="Últimos runs" icon="chart" poll={poll} className="area-history">
      {({ runs, stats }) => {
        // A API manda do mais novo para o mais antigo; o gráfico lê da esquerda.
        const ordered = [...runs].reverse()
        const max = Math.max(1, ...ordered.map((r) => r.durationSeconds ?? 0))
        const rate = stats.successRate == null ? '—' : `${Math.round(stats.successRate * 100)}%`

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

            {ordered.length === 0 ? (
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

            <div className="legend muted">
              <span><i className="dot is-push" /> push na main</span>
              <span><i className="dot" /> pull request</span>
            </div>
          </>
        )
      }}
    </GlassCard>
  )
}

export default HistoryCard
