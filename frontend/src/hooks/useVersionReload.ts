import { useEffect, useRef } from 'react'
import { usePolling } from './usePolling'

interface VersionFile {
  version: string
}

// Função de módulo (estável), como o usePolling exige.
async function fetchVersionFile({ signal }: { signal: AbortSignal }): Promise<VersionFile> {
  const res = await fetch('/version.json', { cache: 'no-store', signal })
  if (!res.ok) throw new Error(`version.json: ${res.status}`)
  return (await res.json()) as VersionFile
}

/**
 * Consulta /version.json a cada 5 s. Se a versão mudar em relação à que a
 * página carregou, recarrega. `offline` fica true enquanto a consulta falha
 * (ex.: container sendo recriado) depois de já ter funcionado uma vez.
 */
export function useVersionReload(): { offline: boolean } {
  const { data, error } = usePolling(fetchVersionFile, 5000)
  const initial = useRef<string | null>(null)

  useEffect(() => {
    if (!data) return
    if (initial.current === null) {
      initial.current = data.version
    } else if (data.version !== initial.current) {
      window.location.reload()
    }
  }, [data])

  return { offline: error !== null && data !== undefined }
}