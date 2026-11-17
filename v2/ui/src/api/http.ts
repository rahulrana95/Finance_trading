import { DEFAULT_ERROR, STOCKS_URL } from '../constants'
import { ApiError, type Api, type Stock } from './types'

/** GET a JSON document from the backend; failures become ApiError with the server's reason. */
export async function getJson<T>(url: string): Promise<T> {
  let response: Response
  try {
    response = await fetch(url, { headers: { Accept: 'application/json' } })
  } catch {
    throw new ApiError('The server did not answer. Check your connection and try again.', 'network')
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: unknown } | null
    throw new ApiError(typeof body?.detail === 'string' ? body.detail : DEFAULT_ERROR, String(response.status))
  }
  return (await response.json()) as T
}

/** The parts of the Api that the backend serves today. */
export const liveStocks: Pick<Api, 'listStocks' | 'getStock'> = {
  listStocks: () => getJson<Stock[]>(STOCKS_URL),
  getStock: (symbol) => getJson<Stock>(`${STOCKS_URL}/${encodeURIComponent(symbol)}`),
}
