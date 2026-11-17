// Session storage can be blocked (private windows, embedded previews), so every call is guarded.
export function readJson<T>(key: string, storage: Storage = sessionStorage): T | null {
  try {
    const raw = storage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : null
  } catch {
    return null
  }
}

export function writeJson(key: string, value: unknown, storage: Storage = sessionStorage): void {
  try {
    storage.setItem(key, JSON.stringify(value))
  } catch {
    /* the value then lasts only until reload */
  }
}

export function remove(key: string, storage: Storage = sessionStorage): void {
  try {
    storage.removeItem(key)
  } catch {
    /* nothing to clear */
  }
}
