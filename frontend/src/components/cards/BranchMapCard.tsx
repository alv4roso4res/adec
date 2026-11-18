import { useEffect, useMemo, useRef, useState, type CSSProperties, type RefObject } from 'react'
import { usePolling } from '../../hooks/usePolling'
import { getBranches } from '../../services/api'
import type { BranchMap, MapCommit } from '../../types/api'
import { layoutBranchMap, type LaidOutBranch } from '../../utils/branchLayout'
import { firstLine, timeAgo } from '../../utils/format'
import GlassCard from '../GlassCard'

// Card 7: mapa de branches no estilo mapa de metrô. A main é a linha do meio;
// cada branch sai dela, passa pelos próprios commits (estações) e volta no
// merge. Branch aberta ainda não voltou: termina com a ponta piscando.
// O mapa traz o histórico todo e rola para o lado com a rodinha do mouse
// (começa no mais recente), sem barra de rolagem visível.
function BranchMapCard() {
  const poll = usePolling(getBranches, 30000)

  return (
    <GlassCard title="Mapa de branches" icon="branch" poll={poll} className="area-map">
      {(map, now) => <MetroMap map={map} now={now} />}
    </GlassCard>
  )
}

// Cores das linhas, como num mapa de metrô (a main usa o azul do tema).
const LINE_COLORS = ['#30d158', '#bf5af2', '#ff9f0a', '#ff375f', '#64d2ff', '#ffd60a', '#5e5ce6', '#ff6482']
const MAIN_COLOR = '#0a84ff'
const lineColor = (b: LaidOutBranch) => LINE_COLORS[b.colorIndex % LINE_COLORS.length]

// Medidas do desenho, em px.
const PAD_LEFT = 30
const PAD_TOP = 26 // espaço para as plaquinhas "#PR" das faixas de cima
const PAD_BOTTOM = 32 // plaquinhas das faixas de baixo + linha das datas
const LANE_HEIGHT = 30
const COL_WIDTH = 46 // distância entre estações; o que passar da largura rola
const CURVE = 26
const TAG_GAP = 16 // distância entre a última estação e a plaquinha do nome

type Hover = { kind: 'main' } | { kind: 'branch'; branch: LaidOutBranch } | null

function MetroMap({ map, now }: { map: BranchMap; now: number }) {
  const layout = useMemo(() => layoutBranchMap(map), [map])
  const [hover, setHover] = useState<Hover>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const width = useElementWidth(scrollRef)
  const edges = useScrollEdges(scrollRef)

  // À direita cabem as plaquinhas: a da main e as das branches abertas.
  const tags = [map.defaultBranch, ...map.branches.filter((b) => b.state === 'open').map((b) => b.name)]
  const padRight = TAG_GAP + Math.max(...tags.map(tagWidth)) + 16
  const lastCol = Math.max(1, layout.columns - 1)
  // Se couber, estica para ocupar a largura; se não, rola.
  const colWidth = Math.max(COL_WIDTH, (width - PAD_LEFT - padRight) / lastCol)
  const svgWidth = Math.max(width, PAD_LEFT + lastCol * colWidth + padRight)
  const mainY = PAD_TOP + layout.lanesAbove * LANE_HEIGHT
  const svgHeight = mainY + layout.lanesBelow * LANE_HEIGHT + PAD_BOTTOM

  const x = (col: number) => (col < 0 ? 0 : PAD_LEFT + col * colWidth)
  const y = (lane: number) => mainY + lane * LANE_HEIGHT

  // Só conta depois de medir a largura (antes disso o SVG nem é desenhado).
  useStartAtNewest(scrollRef, width > 0 ? svgWidth : 0)
  useWheelToScroll(scrollRef)
  useDragToScroll(scrollRef)

  if (map.mainline.length === 0) {
    return <p className="empty">Nenhum commit na {map.defaultBranch}.</p>
  }

  const mainStart = x(layout.main[0].col)
  const mainEnd = x(layout.main.at(-1)!.col)
  const hoveredKey = hover?.kind === 'branch' ? hover.branch.key : hover?.kind
  const dim = (key: string) => (hoveredKey && hoveredKey !== key ? 'is-dim' : '')
  const days = dayMarks(layout.main)

  return (
    <div className="metro">
      <div className={`metro-viewport ${edges.left ? 'more-left' : ''} ${edges.right ? 'more-right' : ''}`}>
        <div className="metro-scroll" ref={scrollRef}>
          {width > 0 && (
            <svg
              className="metro-svg"
              width={svgWidth}
              height={svgHeight}
              role="img"
              aria-label={`Mapa de branches: ${map.defaultBranch} e ${map.branches.length} ramificações`}
            >
              <defs>
                <filter id="metro-glow" x="-20%" y="-200%" width="140%" height="500%">
                  <feGaussianBlur stdDeviation="6" />
                </filter>
              </defs>

              {/* Linha do tempo: uma guia tracejada e a data onde o dia muda. */}
              {days.map(({ col, label }) => (
                <g key={col} className="metro-day">
                  <line x1={x(col)} x2={x(col)} y1={8} y2={svgHeight - 20} />
                  <text x={x(col)} y={svgHeight - 7} textAnchor="middle">
                    {label}
                  </text>
                </g>
              ))}

              {/* Brilho difuso da main, por baixo de tudo. */}
              <path className="metro-glow" d={`M ${mainStart} ${mainY} H ${mainEnd}`} filter="url(#metro-glow)" />

              {/* Branches primeiro: a main passa por cima nas junções. */}
              {layout.branches.map((b, i) => {
                const ly = y(b.lane)
                const first = b.stations[0] ? x(b.stations[0].col) : x(b.start) + CURVE
                const last = b.stations.at(-1) ? x(b.stations.at(-1)!.col) : first
                const isOpen = b.end === null
                const d = branchPath(b, x, ly, mainY, last)
                const label = b.line.prNumber ? `#${b.line.prNumber}` : shortName(b.line.name)

                return (
                  // <g> clicável (não <a>): as estações dentro já são links.
                  <g
                    key={b.key}
                    role="link"
                    tabIndex={0}
                    onClick={() => openLink(b.line.htmlUrl)}
                    onKeyDown={(e) => e.key === 'Enter' && openLink(b.line.htmlUrl)}
                    className={`metro-branch ${isOpen ? 'is-open' : ''} ${dim(b.key)}`}
                    style={{ '--c': lineColor(b), '--d': `${0.1 + i * 0.04}s` } as CSSProperties}
                    onMouseEnter={() => setHover({ kind: 'branch', branch: b })}
                    onMouseLeave={() => setHover(null)}
                    onFocus={() => setHover({ kind: 'branch', branch: b })}
                    onBlur={() => setHover(null)}
                    aria-label={`${b.line.name}${b.line.prNumber ? `, PR #${b.line.prNumber}` : ''}`}
                  >
                    {/* Contorno escuro + linha colorida: o visual de mapa de metrô. */}
                    <path className="metro-casing" d={d} />
                    <path className="metro-line" pathLength={1} d={d} />
                    <path className="metro-hit" d={d} />

                    {b.stations.map(({ commit, col }) => (
                      <Station key={commit.sha} commit={commit} cx={x(col)} cy={ly} />
                    ))}
                    {b.stations.length === 0 && <circle className="metro-station is-empty" cx={first} cy={ly} r={5} />}

                    {isOpen ? (
                      <NameTag x={last} y={ly} text={b.line.name} />
                    ) : (
                      <LineBadge x={(first + last) / 2} y={b.lane < 0 ? ly - 16 : ly + 16} text={label} />
                    )}
                  </g>
                )
              })}

              <g
                className={`metro-main ${dim('main')}`}
                style={{ '--c': MAIN_COLOR, '--d': '0s' } as CSSProperties}
                onMouseEnter={() => setHover({ kind: 'main' })}
                onMouseLeave={() => setHover(null)}
              >
                <path className="metro-casing is-main" d={`M ${mainStart} ${mainY} H ${mainEnd}`} />
                <path className="metro-line is-main" pathLength={1} d={`M ${mainStart} ${mainY} H ${mainEnd}`} />
                <path className="metro-hit" d={`M ${mainStart} ${mainY} H ${mainEnd}`} />
                {layout.main.map(({ commit, col, isMerge }, i) => (
                  <Station
                    key={commit.sha}
                    commit={commit}
                    cx={x(col)}
                    cy={mainY}
                    variant={isMerge ? 'interchange' : 'stop'}
                    head={i === layout.main.length - 1}
                  />
                ))}
                <NameTag x={mainEnd} y={mainY} text={map.defaultBranch} />
              </g>
            </svg>
          )}
        </div>

      </div>

      <MetroInfo map={map} hover={hover} now={now} />
    </div>
  )
}

/** Caminho de uma branch: sobe da main, segue na faixa e (se mergeada) desce. */
function branchPath(b: LaidOutBranch, x: (col: number) => number, ly: number, mainY: number, last: number): string {
  const parts: string[] = []
  if (b.start < 0) {
    // Saiu antes do começo do mapa: chega pela borda esquerda.
    parts.push(`M 0 ${ly}`)
  } else {
    const xs = x(b.start)
    parts.push(`M ${xs} ${mainY}`, `C ${xs + CURVE / 2} ${mainY} ${xs + CURVE / 2} ${ly} ${xs + CURVE} ${ly}`)
  }
  parts.push(`H ${last}`)
  if (b.end !== null) {
    const xe = x(b.end)
    parts.push(`H ${xe - CURVE}`, `C ${xe - CURVE / 2} ${ly} ${xe - CURVE / 2} ${mainY} ${xe} ${mainY}`)
  }
  return parts.join(' ')
}

/** Estação: clicar abre o commit; o título mostra SHA e mensagem. */
function Station({
  commit,
  cx,
  cy,
  variant = 'branch',
  head = false,
}: {
  commit: MapCommit
  cx: number
  cy: number
  variant?: 'branch' | 'stop' | 'interchange'
  head?: boolean
}) {
  const r = variant === 'interchange' ? 8 : variant === 'stop' ? 4 : 6
  return (
    <a href={commit.htmlUrl} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>
      {head && <circle className="metro-head-ring" cx={cx} cy={cy} r={r + 4} />}
      <circle className={`metro-station is-${variant}`} cx={cx} cy={cy} r={r}>
        <title>{`${commit.shortSha} · ${firstLine(commit.message)}`}</title>
      </circle>
    </a>
  )
}

/** Plaquinha colorida com o número do PR, em cima (ou embaixo) da faixa. */
function LineBadge({ x, y, text }: { x: number; y: number; text: string }) {
  const w = text.length * 7 + 12
  return (
    <g className="metro-badge">
      <rect x={x - w / 2} y={y - 9} width={w} height={18} rx={9} />
      <text x={x} y={y + 4} textAnchor="middle">
        {text}
      </text>
    </g>
  )
}

/** Largura da plaquinha de um nome (fonte mono de 11px). */
function tagWidth(text: string): number {
  return Math.min(230, text.length * 6.7 + 18)
}

/** Plaquinha com o nome logo depois da ponta da linha (como "master" no exemplo). */
function NameTag({ x, y, text }: { x: number; y: number; text: string }) {
  const w = tagWidth(text)
  const h = 22
  return (
    <g className="metro-tag">
      <path d={`M ${x + 7} ${y} l ${TAG_GAP - 7} -5 v 10 z`} />
      <rect x={x + TAG_GAP} y={y - h / 2} width={w} height={h} rx={7} />
      <text x={x + TAG_GAP + w / 2} y={y + 4} textAnchor="middle">
        {text}
      </text>
    </g>
  )
}

function openLink(url: string) {
  window.open(url, '_blank', 'noopener,noreferrer')
}

function shortName(name: string): string {
  const last = name.split('/').at(-1) ?? name
  return last.length > 10 ? `${last.slice(0, 9)}…` : last
}

const DAY_FORMAT = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short' })

/** Primeira estação da main de cada dia, com a data ("11 de nov."). */
function dayMarks(main: { commit: MapCommit; col: number }[]): { col: number; label: string }[] {
  const marks: { col: number; label: string }[] = []
  let previous = ''
  for (const { commit, col } of main) {
    const label = DAY_FORMAT.format(new Date(commit.committedAt)).replace(' de ', ' ').replace('.', '')
    if (label !== previous) marks.push({ col, label })
    previous = label
  }
  return marks
}

/** Faixa de baixo: resumo do mapa ou detalhes da linha sob o mouse. */
function MetroInfo({ map, hover, now }: { map: BranchMap; hover: Hover; now: number }) {
  const merged = map.branches.filter((b) => b.state === 'merged').length
  const open = map.branches.length - merged

  if (hover?.kind === 'branch') {
    const { line } = hover.branch
    const mergeCommit = map.mainline.find((c) => c.sha === line.mergeSha)
    const last = line.commits.at(-1)
    return (
      <div className="metro-info">
        <i className="metro-dot" style={{ background: lineColor(hover.branch) }} />
        <strong className="metro-info-name">{line.name}</strong>
        <span className={`pill ${line.state === 'open' ? 'tone-queued' : 'tone-success'}`}>
          {line.state === 'open' ? 'aberta' : 'mergeada'}
        </span>
        {line.prNumber && <span className="muted">PR #{line.prNumber}</span>}
        {line.author?.avatarUrl && <img className="avatar tiny" src={line.author.avatarUrl} alt="" />}
        {line.author && <span className="muted">{line.author.login ?? line.author.name}</span>}
        <span className="muted">
          {line.commits.length} {line.commits.length === 1 ? 'commit' : 'commits'}
        </span>
        <span className="muted nowrap">
          {line.state === 'open'
            ? `${line.aheadBy} à frente · ${line.behindBy} atrás da ${map.defaultBranch}`
            : `voltou para a ${map.defaultBranch} ${timeAgo(mergeCommit?.committedAt, now)}`}
        </span>
        {last && <span className="metro-info-msg muted">{firstLine(last.message)}</span>}
      </div>
    )
  }

  if (hover?.kind === 'main') {
    const head = map.mainline.at(-1)!
    return (
      <div className="metro-info">
        <i className="metro-dot" style={{ background: MAIN_COLOR }} />
        <strong className="metro-info-name">{map.defaultBranch}</strong>
        <span className="muted">{map.mainline.length} commits</span>
        <span className="muted nowrap">último {timeAgo(head.committedAt, now)}</span>
        <span className="metro-info-msg muted">{firstLine(head.message)}</span>
      </div>
    )
  }

  return (
    <div className="metro-info">
      <i className="metro-dot" style={{ background: MAIN_COLOR }} />
      <strong className="metro-info-name">{map.defaultBranch}</strong>
      <span className="muted">
        {merged} {merged === 1 ? 'branch mergeada' : 'branches mergeadas'} · {open}{' '}
        {open === 1 ? 'aberta' : 'abertas'}
      </span>
      <span className="metro-info-msg muted">
        Role o mouse sobre o mapa para ver o histórico · passe numa linha para ver detalhes
      </span>
    </div>
  )
}

/** Largura do elemento, atualizada quando a janela muda de tamanho. */
function useElementWidth(ref: RefObject<HTMLElement | null>): number {
  const [width, setWidth] = useState(0)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const observer = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)))
    observer.observe(el)
    return () => observer.disconnect()
  }, [ref])
  return width
}

/** Se ainda há mapa escondido à esquerda e à direita (mostra setas e esmaece a borda). */
function useScrollEdges(ref: RefObject<HTMLElement | null>) {
  const [edges, setEdges] = useState({ left: false, right: false })
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const update = () => {
      const max = el.scrollWidth - el.clientWidth
      const left = el.scrollLeft > 4
      const right = el.scrollLeft < max - 4
      setEdges((cur) => (cur.left === left && cur.right === right ? cur : { left, right }))
    }
    // O ResizeObserver chama uma vez ao começar e de novo quando o SVG muda.
    const observer = new ResizeObserver(update)
    observer.observe(el)
    if (el.firstElementChild) observer.observe(el.firstElementChild)
    const mutations = new MutationObserver(() => {
      if (el.firstElementChild) observer.observe(el.firstElementChild)
      update()
    })
    mutations.observe(el, { childList: true })
    el.addEventListener('scroll', update, { passive: true })
    return () => {
      observer.disconnect()
      mutations.disconnect()
      el.removeEventListener('scroll', update)
    }
  }, [ref])
  return edges
}

/** Na primeira vez que o mapa não cabe, começa mostrando o fim (o mais novo). */
function useStartAtNewest(ref: RefObject<HTMLElement | null>, contentWidth: number) {
  const done = useRef(false)
  useEffect(() => {
    const el = ref.current
    if (!el || done.current || contentWidth === 0) return
    el.scrollLeft = el.scrollWidth
    done.current = true
  }, [ref, contentWidth])
}

/**
 * A rodinha do mouse (para cima/baixo) rola o mapa para os lados. Nas pontas
 * do mapa a rodinha volta a funcionar normalmente.
 */
function useWheelToScroll(ref: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const onWheel = (e: WheelEvent) => {
      // Trackpad rolando de lado já funciona sozinho.
      if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return
      const max = el.scrollWidth - el.clientWidth
      const canScroll = e.deltaY > 0 ? el.scrollLeft < max - 1 : el.scrollLeft > 1
      if (!canScroll) return
      e.preventDefault()
      // deltaMode 1 = linhas (Firefox): converte para pixels.
      el.scrollLeft += e.deltaY * (e.deltaMode === 1 ? 32 : 1)
    }
    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [ref])
}

/**
 * Arrastar com o mouse também rola o mapa para o lado. Só vira arraste depois de
 * mover alguns pixels; nesse caso o clique no fim é cancelado, para não abrir
 * o link da linha onde o arraste começou.
 */
function useDragToScroll(ref: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = ref.current
    if (!el) return
    let startX = 0
    let startLeft = 0
    let pressed = false
    let dragging = false

    const onDown = (e: PointerEvent) => {
      if (e.pointerType !== 'mouse' || e.button !== 0) return
      pressed = true
      dragging = false
      startX = e.clientX
      startLeft = el.scrollLeft
    }
    const onMove = (e: PointerEvent) => {
      if (!pressed) return
      const dx = e.clientX - startX
      if (!dragging && Math.abs(dx) > 5) {
        dragging = true
        el.classList.add('is-dragging')
      }
      if (dragging) el.scrollLeft = startLeft - dx
    }
    const onUp = () => {
      pressed = false
      el.classList.remove('is-dragging')
    }
    const onClick = (e: MouseEvent) => {
      if (!dragging) return
      e.preventDefault()
      e.stopPropagation()
      dragging = false
    }
    // Sem isso o navegador "arrasta" o link (imagem fantasma) em vez de rolar.
    const onDragStart = (e: DragEvent) => e.preventDefault()

    el.addEventListener('pointerdown', onDown)
    window.addEventListener('pointermove', onMove)
    window.addEventListener('pointerup', onUp)
    el.addEventListener('click', onClick, true)
    el.addEventListener('dragstart', onDragStart)
    return () => {
      el.removeEventListener('pointerdown', onDown)
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerup', onUp)
      el.removeEventListener('click', onClick, true)
      el.removeEventListener('dragstart', onDragStart)
    }
  }, [ref])
}

export default BranchMapCard
