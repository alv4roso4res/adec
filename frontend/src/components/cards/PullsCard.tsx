import { usePolling } from '../../hooks/usePolling'
import { getPulls } from '../../services/api'
import type { PullBadge } from '../../types/api'
import { type Tone, timeAgo } from '../../utils/format'
import GlassCard from '../GlassCard'
import Icon from '../Icon'

const BADGES: Record<PullBadge, { label: string; tone: Tone }> = {
  ready: { label: 'Pronto', tone: 'success' },
  needs_approval: { label: 'Precisa de aprovação', tone: 'queued' },
  waiting_checks: { label: 'Aguardando checks', tone: 'running' },
  computing: { label: 'Calculando', tone: 'neutral' },
  checks_failed: { label: 'Testes falharam', tone: 'failure' },
  conflict: { label: 'Conflito', tone: 'failure' },
  draft: { label: 'Rascunho', tone: 'neutral' },
}

// Card 3: PRs abertos com o estado de cada um.
function PullsCard() {
  const poll = usePolling(getPulls, 10000)

  return (
    <GlassCard title="Pull requests abertos" icon="pull" poll={poll} className="area-pulls">
      {(pulls, now) =>
        pulls.length === 0 ? (
          <div className="empty big">
            <Icon name="pull" size={34} />
            <p>Nenhum PR aberto</p>
            <span className="muted">Abra um PR e o pipeline aparece aqui.</span>
          </div>
        ) : (
          <ul className="list">
            {pulls.map((pr) => {
              const badge = BADGES[pr.badge]
              return (
                <li key={pr.number} className="row pull">
                  <img className="avatar" src={pr.author.avatarUrl} alt="" />
                  <div className="row-main">
                    <a className="row-title" href={pr.htmlUrl} target="_blank" rel="noreferrer">
                      <span className="muted mono">#{pr.number}</span> {pr.title}
                    </a>
                    <span className="muted small">
                      {pr.author.login} · {timeAgo(pr.createdAt, now)} · ✓ {pr.checks.passed}
                      {pr.checks.failed > 0 && ` · ✕ ${pr.checks.failed}`}
                      {pr.checks.pending > 0 && ` · ⋯ ${pr.checks.pending}`} ·{' '}
                      {pr.approvals} aprovaç{pr.approvals === 1 ? 'ão' : 'ões'}
                    </span>
                  </div>
                  <span className={`pill tone-${badge.tone}`}>{badge.label}</span>
                </li>
              )
            })}
          </ul>
        )
      }
    </GlassCard>
  )
}

export default PullsCard
