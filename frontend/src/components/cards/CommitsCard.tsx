import { usePolling } from '../../hooks/usePolling'
import { getCommits } from '../../services/api'
import { prettyCommit, timeAgo } from '../../utils/format'
import GlassCard from '../GlassCard'
import StatusIcon from '../StatusIcon'

// Card 6: últimos commits da main com o resultado do pipeline de cada um.
// A lista rola para baixo (barra de rolagem escondida) para ver os mais antigos.
function CommitsCard() {
  const poll = usePolling(getCommits, 15000)

  return (
    <GlassCard title="Commits da main" icon="commit" poll={poll} className="area-commits">
      {(commits, now) =>
        commits.length === 0 ? (
          <p className="empty">Nenhum commit.</p>
        ) : (
          <ul className="list timeline scroll-hidden">
            {commits.map((c) => (
              <li key={c.sha} className="row commit">
                <StatusIcon status={c.pipelineStatus} size={18} />
                <a className="sha mono" href={c.htmlUrl} target="_blank" rel="noreferrer">
                  {c.shortSha}
                </a>
                <span className="row-title" title={c.message}>
                  {prettyCommit(c.message)}
                </span>
                {c.author.avatarUrl && (
                  <img className="avatar tiny" src={c.author.avatarUrl} alt="" title={c.author.login ?? c.author.name} />
                )}
                <span className="muted small nowrap row-time">{timeAgo(c.committedAt, now)}</span>
              </li>
            ))}
          </ul>
        )
      }
    </GlassCard>
  )
}

export default CommitsCard
