import { useGlassPointer } from '../hooks/useGlassPointer'
import { useNow } from '../hooks/useNow'
import { usePolling } from '../hooks/usePolling'
import { getHealth } from '../services/api'

// Cabeçalho: repositório monitorado, indicador "ao vivo", relógio e versão.
function Header() {
  const now = useNow(1000)
  const { data, error } = usePolling(getHealth, 30000)
  const online = data !== undefined && !error
  const pointer = useGlassPointer()

  return (
    <header className="glass topbar" {...pointer}>
      <div className="brand">
        <span className="brand-mark">A</span>
        <div className="brand-text">
          <span className="brand-name">ADEC</span>
          <span className="muted small">{data?.repository ?? 'painel de CI/CD'}</span>
        </div>
      </div>

      <div className="topbar-right">
        <span className={`live ${online ? '' : 'is-off'}`}>
          <span className="live-dot" />
          {online ? 'Ao vivo' : 'Sem conexão'}
        </span>
        <span className="clock mono">
          {new Date(now).toLocaleTimeString('pt-BR', { hour12: false })}
        </span>
        <span className="pill version mono" title="Versão da API rodando">
          {data?.version ?? '—'}
        </span>
      </div>
    </header>
  )
}

export default Header
