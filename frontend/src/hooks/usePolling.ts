import { useEffect, useRef, useState } from 'react'

export interface PollState<T> {
  data: T | undefined
  error: string | null
  // Momento (ms) da última resposta boa; null enquanto não chegou nenhuma.
  updatedAt: number | null
}

type Fetcher<T> = (opts: { signal: AbortSignal }) => Promise<T>

// Intervalo fixo ou calculado a partir do último dado (ex.: mais rápido
// enquanto o pipeline está rodando).
type Interval<T> = number | ((data: T | undefined) => number)

/**
 * Busca `fetcher` agora e de novo a cada `interval` ms, para o card se
 * atualizar sozinho. Se uma busca falha, mantém o último dado bom na tela e
 * só marca o erro. O `fetcher` precisa ser estável (função de módulo).
 */
export function usePolling<T>(fetcher: Fetcher<T>, interval: Interval<T>): PollState<T> {
  const [state, setState] = useState<PollState<T>>({
    data: undefined,
    error: null,
    updatedAt: null,
  })

  const intervalRef = useRef(interval)
  useEffect(() => {
    intervalRef.current = interval
  })

  useEffect(() => {
    let active = true
    let timer: ReturnType<typeof setTimeout> | undefined
    let controller: AbortController | undefined
    let last: T | undefined

    const tick = async () => {
      controller = new AbortController()
      try {
        const data = await fetcher({ signal: controller.signal })
        if (!active) return
        last = data
        setState({ data, error: null, updatedAt: Date.now() })
      } catch (err) {
        if (!active) return
        const message = err instanceof Error ? err.message : String(err)
        setState((prev) => ({ ...prev, error: message }))
      }
      const iv = intervalRef.current
      timer = setTimeout(tick, typeof iv === 'function' ? iv(last) : iv)
    }

    tick()

    return () => {
      active = false
      clearTimeout(timer)
      controller?.abort()
    }
  }, [fetcher])

  return state
}
