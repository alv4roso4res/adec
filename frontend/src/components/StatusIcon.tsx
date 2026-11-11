import type { RunStatus } from '../types/api'
import { STATUS_META } from '../utils/format'
import Icon from './Icon'

interface StatusIconProps {
  status: RunStatus | null
  size?: number
}

// Bolinha colorida com o símbolo do estado (✓, ✕, relógio, girando...).
function StatusIcon({ status, size = 18 }: StatusIconProps) {
  const tone = status ? STATUS_META[status].tone : 'neutral'
  const inner = Math.round(size * 0.62)

  return (
    <span
      className={`status-icon tone-${tone}`}
      style={{ width: size, height: size }}
      title={status ? STATUS_META[status].label : 'Sem pipeline'}
    >
      {status === 'success' && <Icon name="check" size={inner} />}
      {status === 'failure' && <Icon name="x" size={inner} />}
      {status === 'queued' && <Icon name="clock" size={inner} />}
      {status === 'in_progress' && <span className="spinner" />}
      {(status === 'cancelled' || status === 'skipped' || status === null) && (
        <Icon name="minus" size={inner} />
      )}
    </span>
  )
}

export default StatusIcon
