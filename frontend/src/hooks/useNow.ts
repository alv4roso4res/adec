import { useEffect, useState } from 'react'

// Relógio que re-renderiza a cada `ms`: mantém "há 3 min" e cronômetros vivos.
export function useNow(ms = 1000): number {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), ms)
    return () => clearInterval(id)
  }, [ms])

  return now
}
