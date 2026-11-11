import { usePolling } from '../../hooks/usePolling'
import { getTeam } from '../../services/api'
import GlassCard from '../GlassCard'
import Icon from '../Icon'

// Card 4: integrantes e a regra do trabalho (cada um com pelo menos 1 PR).
function TeamCard() {
  const poll = usePolling(getTeam, 60000)

  return (
    <GlassCard title="Integrantes" icon="users" poll={poll} className="area-team">
      {(team) =>
        team.length === 0 ? (
          <p className="empty">Configure TEAM_LOGINS na API.</p>
        ) : (
          <ul className="list">
            {team.map((m) => (
              <li key={m.login} className="row member">
                <img className="avatar" src={m.avatarUrl} alt="" />
                <div className="row-main">
                  <span className="row-title">{m.login}</span>
                  <span className="muted small">
                    {m.prsMerged} PRs · {m.commits} commits
                    {m.prsOpen > 0 && ` · ${m.prsOpen} aberto${m.prsOpen > 1 ? 's' : ''}`}
                  </span>
                </div>
                {m.meetsRequirement ? (
                  <span className="pill tone-success" title="Já tem pelo menos 1 PR mergeado">
                    <Icon name="check" size={13} /> PR
                  </span>
                ) : (
                  <span className="pill tone-queued">sem PR</span>
                )}
              </li>
            ))}
          </ul>
        )
      }
    </GlassCard>
  )
}

export default TeamCard
