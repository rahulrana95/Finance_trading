import { DEFAULT_ERROR, IDEAS_URL, RUN_POLL_MS, RUN_POLL_TRIES, RUNS_URL, SCREEN_POLL_TRIES, SCREENS_URL, STOCKS_URL } from '../constants'
import { sleep as realSleep, type Sleep } from '../lib/sleep'
import { ApiError, type Api, type RecFilter, type Recommendation, type Run, type ScreenState, type Stock } from './types'

/** Send a request and read the JSON answer; failures become ApiError with the server's reason. */
async function request<T>(url: string, init: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(url, { ...init, headers: { Accept: 'application/json', ...init.headers } })
  } catch {
    throw new ApiError('The server did not answer. Check your connection and try again.', 'network')
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: unknown } | null
    throw new ApiError(typeof body?.detail === 'string' ? body.detail : DEFAULT_ERROR, String(response.status))
  }
  return (await response.json()) as T
}

export const getJson = <T>(url: string): Promise<T> => request<T>(url, {})

export const postJson = <T>(url: string, body: unknown): Promise<T> =>
  request<T>(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

/** The parts of the Api that the backend serves today. */
export const liveStocks: Pick<Api, 'listStocks' | 'getStock'> = {
  listStocks: () => getJson<Stock[]>(STOCKS_URL),
  getStock: (symbol) => getJson<Stock>(`${STOCKS_URL}/${encodeURIComponent(symbol)}`),
}

/** Only the filters that narrow the list are sent. */
export function ideasQuery(filter: RecFilter = {}): string {
  const params = new URLSearchParams()
  if (filter.instrumentType && filter.instrumentType !== 'any') params.set('instrumentType', filter.instrumentType)
  if (filter.status && filter.status !== 'any') params.set('status', filter.status)
  if (filter.minZone) params.set('minZone', String(filter.minZone))
  if (filter.minScore) params.set('minScore', String(filter.minScore))
  const query = params.toString()
  return query ? `?${query}` : ''
}

/** The server finishes work in the background, so ask again until it is done or tries run out. */
export async function waitUntil<T>(get: () => Promise<T>, done: (value: T) => boolean, sleep: Sleep = realSleep, tries: number = RUN_POLL_TRIES): Promise<T> {
  let value = await get()
  for (let i = 1; i < tries && !done(value); i++) {
    await sleep(RUN_POLL_MS)
    value = await get()
  }
  return value
}

export const waitForRun = (id: string, get: (id: string) => Promise<Run>, sleep: Sleep = realSleep, tries: number = RUN_POLL_TRIES): Promise<Run> =>
  waitUntil(() => get(id), (run) => run.status !== 'running', sleep, tries)

const getRun = (id: string): Promise<Run> => getJson<Run>(`${RUNS_URL}/${encodeURIComponent(id)}`)

export const liveAlgo: Pick<Api, 'listRuns' | 'startRun' | 'listRecommendations'> = {
  listRuns: () => getJson<Run[]>(RUNS_URL),
  startRun: async (kind) => {
    const started = await postJson<Run>(RUNS_URL, { kind })
    return started.status === 'running' ? waitForRun(started.id, getRun) : started
  },
  listRecommendations: (filter) => getJson<Recommendation[]>(IDEAS_URL + ideasQuery(filter)),
}

const latestScreen = (): Promise<ScreenState> => getJson<ScreenState>(`${SCREENS_URL}/latest`)

export const liveScreen: Pick<Api, 'getScreen' | 'startScreen'> = {
  getScreen: latestScreen,
  startScreen: async () => {
    const started = await postJson<ScreenState>(SCREENS_URL, {})
    return started.running ? waitUntil(latestScreen, (state) => !state.running, realSleep, SCREEN_POLL_TRIES) : started
  },
}
