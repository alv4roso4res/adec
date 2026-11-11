import type { ReactNode } from 'react'
import { useGlassPointer } from '../hooks/useGlassPointer'
import { useNow } from '../hooks/useNow'
import type { PollState } from '../hooks/usePolling'
import { friendlyError } from '../utils/format'
import Icon, { type IconName } from './Icon'

interface GlassCardProps<T> {
  title: string
  icon: IconName
  poll: PollState<T>
  className?: string
  // Só é chamado quando já existe dado: o card cuida de carregando/erro.
  children: (data: T, now: number) => ReactNode
}

/**
 * Moldura de vidro comum aos 6 cards: título, indicador de atualização,
 * estados de carregando e erro. Um card com erro não afeta os outros.
 */
function GlassCard<T>({ title, icon, poll, className = '', children }: GlassCardProps<T>) {
  const now = useNow(1000)
  const { data, error, updatedAt } = poll
  const seconds = updatedAt ? Math.max(0, Math.round((now - updatedAt) / 1000)) : null
  const pointer = useGlassPointer()

  return (
    <section className={`glass card interactive ${className}`} {...pointer}>
      <header className="card-header">
        <span className="card-icon">
          <Icon name={icon} size={16} />
        </span>
        <h2 className="card-title">{title}</h2>
        <span className={`card-sync ${error ? 'is-stale' : ''}`}>
          {error && data !== undefined
            ? 'reconectando…'
            : seconds !== null
              ? seconds < 3
                ? 'agora'
                : `${seconds}s`
              : ''}
        </span>
      </header>

      <div className="card-body">
        {data !== undefined ? (
          children(data, now)
        ) : error ? (
          <div className="card-state is-error">
            <Icon name="x" size={22} />
            <p>{friendlyError(error)}</p>
          </div>
        ) : (
          <div className="card-state">
            <span className="skeleton" />
            <span className="skeleton short" />
            <span className="skeleton" />
          </div>
        )}
      </div>
    </section>
  )
}

export default GlassCard
