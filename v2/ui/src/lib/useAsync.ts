import { useCallback, useEffect, useState } from 'react'

export interface AsyncState<T> {
  data: T | undefined
  error: string | undefined
  loading: boolean
  reload: () => void
}

/** Loads data when the component mounts and whenever `deps` change. */
export function useAsync<T>(load: () => Promise<T>, deps: readonly unknown[]): AsyncState<T> {
  const [data, setData] = useState<T>()
  const [error, setError] = useState<string>()
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)
  useEffect(() => {
    let live = true
    setLoading(true)
    load()
      .then((value) => live && (setData(value), setError(undefined)))
      .catch((e: unknown) => live && setError(e instanceof Error ? e.message : 'Something went wrong.'))
      .finally(() => live && setLoading(false))
    return () => {
      live = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])
  const reload = useCallback(() => setTick((t) => t + 1), [])
  return { data, error, loading, reload }
}
