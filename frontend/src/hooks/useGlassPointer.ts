import { useCallback, type PointerEvent } from 'react'

// Inclinação máxima do card (graus) quando o mouse está na borda.
const MAX_TILT = 5

/**
 * Faz o vidro reagir ao mouse: grava a posição do cursor e a inclinação em
 * variáveis CSS do próprio elemento (--mx, --my, --rx, --ry). O CSS usa essas
 * variáveis para mover o reflexo de luz e inclinar o card em 3D.
 *
 * Escreve direto no `style` do elemento (sem setState): o mouse dispara dezenas
 * de eventos por segundo e assim o React não precisa re-renderizar o card.
 */
export function useGlassPointer() {
  const onPointerMove = useCallback((e: PointerEvent<HTMLElement>) => {
    const el = e.currentTarget
    const rect = el.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width // 0 (esquerda) a 1 (direita)
    const y = (e.clientY - rect.top) / rect.height // 0 (topo) a 1 (base)

    el.style.setProperty('--mx', `${(x * 100).toFixed(1)}%`)
    el.style.setProperty('--my', `${(y * 100).toFixed(1)}%`)
    el.style.setProperty('--ry', `${((x - 0.5) * 2 * MAX_TILT).toFixed(2)}deg`)
    el.style.setProperty('--rx', `${((0.5 - y) * 2 * MAX_TILT).toFixed(2)}deg`)
  }, [])

  // Ao sair, volta o card para a posição reta (o CSS anima a volta).
  const onPointerLeave = useCallback((e: PointerEvent<HTMLElement>) => {
    const el = e.currentTarget
    el.style.setProperty('--rx', '0deg')
    el.style.setProperty('--ry', '0deg')
  }, [])

  return { onPointerMove, onPointerLeave }
}
