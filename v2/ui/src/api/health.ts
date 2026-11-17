export interface Health {
  status: string
  service: string
  version: string
  time: string
}

/** Asks the backend whether it is up. Returns null when there is no backend or it is unhealthy. */
export async function fetchHealth(): Promise<Health | null> {
  try {
    const response = await fetch('/api/health')
    if (!response.ok) return null
    const body = (await response.json()) as Health
    return body.status === 'ok' ? body : null
  } catch {
    return null
  }
}
