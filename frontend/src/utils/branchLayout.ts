import type { BranchLine, BranchMap, MapCommit } from '../types/api'

/**
 * Layout do mapa de branches (card 7), sem nada de desenho: só decide a
 * coluna de cada commit e a faixa (lane) de cada branch.
 *
 * - Coluna: ordem no tempo. Um commit sempre fica depois do pai, e entre os
 *   que estão livres vai primeiro o mais antigo (ordenação topológica).
 * - Lane: 0 é a main; -1, 1, -2, 2... são as faixas acima e abaixo dela. Cada
 *   branch fica na primeira faixa livre no trecho em que existe, então só
 *   branches que se cruzam no tempo vão para faixas diferentes.
 */

export interface LaidOutBranch {
  key: string
  line: BranchLine
  lane: number
  // Coluna onde sai da main (-1 = antes do começo do mapa).
  start: number
  // Coluna onde volta para a main; null se ainda está aberta.
  end: number | null
  stations: { commit: MapCommit; col: number }[]
  colorIndex: number
}

export interface BranchLayout {
  columns: number
  main: { commit: MapCommit; col: number; isMerge: boolean }[]
  branches: LaidOutBranch[]
  lanesAbove: number
  lanesBelow: number
}

// Ordem de tentativa das faixas: acima, abaixo, mais acima, mais abaixo...
const LANE_ORDER = [-1, 1, -2, 2, -3, 3, -4, 4]

export function layoutBranchMap(map: BranchMap): BranchLayout {
  const mainShas = new Set(map.mainline.map((c) => c.sha))
  const mergeShas = new Set(map.branches.map((b) => b.mergeSha).filter(Boolean))
  const col = topologicalColumns(map)

  const sorted = map.branches
    .map((line, index) => {
      const start = line.forkSha && mainShas.has(line.forkSha) ? col.get(line.forkSha)! : -1
      const end = line.mergeSha && mainShas.has(line.mergeSha) ? col.get(line.mergeSha)! : null
      const stations = line.commits.map((commit) => ({ commit, col: col.get(commit.sha)! }))
      return { key: `${line.name}:${line.mergeSha ?? 'open'}`, line, start, end, stations, colorIndex: index }
    })
    .sort((a, b) => a.start - b.start || (a.end ?? Infinity) - (b.end ?? Infinity))

  // Onde termina o último trecho ocupado de cada faixa.
  const laneEnd = new Map<number, number>()
  const branches: LaidOutBranch[] = sorted.map((b) => {
    // Aberta ocupa a faixa até o fim do mapa (ainda vai voltar).
    const occupiedUntil = b.end ?? Infinity
    const lane = LANE_ORDER.find((l) => (laneEnd.get(l) ?? -Infinity) <= b.start) ?? LANE_ORDER.at(-1)!
    laneEnd.set(lane, occupiedUntil)
    return { ...b, lane }
  })

  return {
    columns: col.size,
    main: map.mainline.map((commit) => ({
      commit,
      col: col.get(commit.sha)!,
      isMerge: mergeShas.has(commit.sha),
    })),
    branches,
    lanesAbove: Math.max(0, ...branches.map((b) => -b.lane)),
    lanesBelow: Math.max(0, ...branches.map((b) => b.lane)),
  }
}

/** Coluna de cada commit: pais antes dos filhos, depois o mais antigo primeiro. */
function topologicalColumns(map: BranchMap): Map<string, number> {
  const date = new Map<string, number>()
  const next = new Map<string, string[]>()
  const pending = new Map<string, number>()

  const node = (c: MapCommit) => {
    if (!date.has(c.sha)) {
      date.set(c.sha, new Date(c.committedAt).getTime())
      next.set(c.sha, [])
      pending.set(c.sha, 0)
    }
  }
  const edge = (from: string | null | undefined, to: string | null | undefined) => {
    if (!from || !to || !date.has(from) || !date.has(to)) return
    next.get(from)!.push(to)
    pending.set(to, pending.get(to)! + 1)
  }

  map.mainline.forEach(node)
  map.branches.forEach((b) => b.commits.forEach(node))

  map.mainline.forEach((c, i) => edge(map.mainline[i - 1]?.sha, c.sha))
  for (const b of map.branches) {
    const shas = b.commits.map((c) => c.sha)
    edge(b.forkSha, shas[0])
    shas.forEach((sha, i) => edge(shas[i - 1], sha))
    edge(shas.at(-1), b.mergeSha)
  }

  const col = new Map<string, number>()
  const ready = [...pending].filter(([, n]) => n === 0).map(([sha]) => sha)
  while (ready.length) {
    ready.sort((a, b) => date.get(a)! - date.get(b)!)
    const sha = ready.shift()!
    col.set(sha, col.size)
    for (const to of next.get(sha)!) {
      pending.set(to, pending.get(to)! - 1)
      if (pending.get(to) === 0) ready.push(to)
    }
  }
  // Ciclo não deveria existir; se existir, o que sobrou vai para o fim.
  for (const sha of date.keys()) if (!col.has(sha)) col.set(sha, col.size)
  return col
}
