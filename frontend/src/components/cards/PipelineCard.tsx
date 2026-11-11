import { usePolling } from '../../hooks/usePolling'
import { getPipelineCurrent } from '../../services/api'
import type { PipelineCurrent } from '../../types/api'
import { STATUS_META, formatDuration, isActive, prettyCommit, timeAgo } from '../../utils/format'
import GlassCard from '../GlassCard'
import Icon from '../Icon'
import StatusIcon from '../StatusIcon'

// Rodando: atualiza a cada 4s para acompanhar as etapas. Parado: a cada 20s.
const interval = (d?: PipelineCurrent) => (isActive(d?.run?.status) ? 4000 : 20000)

// Card 1: último run do workflow na main, com os jobs e as etapas.
function PipelineCard() {
  const poll = usePolling(getPipelineCurrent, interval)

  return (
    <GlassCard title="Status da main" icon="activity" poll={poll} className="area-pipeline">
      {({ run, jobs }, now) => {
        if (!run) {
          return <p className="empty">Nenhum pipeline rodou na main ainda.</p>
        }

        const meta = STATUS_META[run.status]
        // Em andamento o cronômetro conta ao vivo a partir do início.
        const elapsed =
          isActive(run.status) && run.startedAt
            ? (now - new Date(run.startedAt).getTime()) / 1000
            : run.durationSeconds

        return (
          <>
            <div className={`hero tone-${meta.tone}`}>
              <StatusIcon status={run.status} size={46} />
              <div className="hero-text">
                <span className="hero-label">{meta.label}</span>
                <span className="muted">
                  {run.event} · {run.branch} · {timeAgo(run.startedAt, now)}
                </span>
              </div>
              <span className="hero-timer mono">{formatDuration(elapsed)}</span>
            </div>

            <p className="commit-line" title={run.commitMessage}>
              {prettyCommit(run.commitMessage)}
              <span className="muted"> · {run.actor}</span>
            </p>

            <ul className="jobs">
              {jobs.map((job) => (
                <li key={job.name} className="job">
                  <div className="job-head">
                    <StatusIcon status={job.status} size={18} />
                    <span className="job-name mono">{job.name}</span>
                    <span className="muted mono">{formatDuration(job.durationSeconds)}</span>
                  </div>
                  {/* Uma faixa por etapa: dá para ver o job avançando. */}
                  <div className="steps">
                    {job.steps.map((step) => (
                      <span
                        key={step.number}
                        className={`step tone-${STATUS_META[step.status].tone}`}
                        title={`${step.number}. ${step.name} — ${STATUS_META[step.status].label}`}
                      />
                    ))}
                  </div>
                </li>
              ))}
            </ul>

            <a className="card-link" href={run.htmlUrl} target="_blank" rel="noreferrer">
              Ver no GitHub Actions <Icon name="external" size={13} />
            </a>
          </>
        )
      }}
    </GlassCard>
  )
}

export default PipelineCard
