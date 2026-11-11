import { usePolling } from '../../hooks/usePolling'
import { getVersion } from '../../services/api'
import type { VersionState } from '../../types/api'
import type { Tone } from '../../utils/format'
import GlassCard from '../GlassCard'

const STATES: Record<VersionState, { label: string; hint: string; tone: Tone }> = {
  up_to_date: { label: 'Atualizado', hint: 'Produção roda o último commit da main.', tone: 'success' },
  restart_pending: { label: 'Aguardando reinício', hint: 'Imagem nova publicada; o vigia ainda vai trocar o container.', tone: 'queued' },
  building: { label: 'Publicando', hint: 'O pipeline da main está gerando as imagens.', tone: 'running' },
  pipeline_failed: { label: 'Pipeline falhou', hint: 'A produção continua na versão anterior.', tone: 'failure' },
  dev: { label: 'Ambiente dev', hint: 'A API não está rodando de uma imagem do pipeline.', tone: 'neutral' },
}

// Compara SHAs por prefixo (o pipeline usa 7 caracteres; o git pode usar mais).
function sameSha(a: string | null | undefined, b: string | null | undefined): boolean {
  if (!a || !b) return false
  const n = Math.min(a.length, b.length)
  return n >= 7 && a.slice(0, n) === b.slice(0, n)
}

// Card 5: versão rodando × imagens no GHCR × último commit da main.
function VersionCard() {
  const poll = usePolling(getVersion, 15000)

  return (
    <GlassCard title="Versão publicada" icon="box" poll={poll} className="area-version">
      {(v) => {
        const state = STATES[v.state]
        const rows = [
          { name: 'rodando', sha: v.running },
          ...v.images.map((img) => ({ name: img.name, sha: img.publishedSha })),
        ]
        return (
          <>
            <div className={`hero tone-${state.tone}`}>
              <span className="hero-dot" />
              <div className="hero-text">
                <span className="hero-label">{state.label}</span>
                <span className="muted">{state.hint}</span>
              </div>
            </div>
            <ul className="list sha-list">
              <li className="row">
                <span className="muted">main</span>
                <span className="mono sha">{v.mainSha?.slice(0, 7) ?? '—'}</span>
              </li>
              {rows.map((r) => (
                <li key={r.name} className="row">
                  <span className="muted">{r.name}</span>
                  <span className={`mono sha ${sameSha(r.sha, v.mainSha) ? 'is-match' : 'is-diff'}`}>
                    {r.sha?.slice(0, 7) ?? '—'}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )
      }}
    </GlassCard>
  )
}

export default VersionCard
