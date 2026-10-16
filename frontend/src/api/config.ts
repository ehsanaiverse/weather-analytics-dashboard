/**
 * Runtime configuration for the API service layer.
 *
 * All values come from Vite environment variables (`import.meta.env`), which are
 * inlined at build time. Defaults keep the app working with no `.env` file at
 * all: a relative base URL, which the Vite dev server proxies to the backend.
 */

/** Join the configured base URL and a path without doubling slashes. */
function joinUrl(base: string, path: string): string {
  const trimmedBase = base.replace(/\/+$/, '')
  const trimmedPath = path.replace(/^\/+/, '')
  return `${trimmedBase}/${trimmedPath}`
}

/** Base URL of the backend, including the `/api` prefix. */
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? '/api'

/** Timeout applied to every request unless overridden. */
export const API_TIMEOUT_MS: number = Number(import.meta.env.VITE_API_TIMEOUT_MS ?? 20_000)

/** Every route this client knows about, relative to {@link API_BASE_URL}. */
export const API_PATHS = {
  health: '/health',
  config: '/config',
  locationSearch: '/locations/search',
  locationDefault: '/locations/default',
  weather: '/weather',
  chernoff: '/chernoff',
  cacheRefresh: '/cache/refresh',
} as const

/** Build an absolute API URL for a known route. */
export function apiUrl(path: string, params?: Record<string, string | number | undefined>): string {
  const url = joinUrl(API_BASE_URL, path)
  if (!params) {
    return url
  }

  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) {
      search.append(key, String(value))
    }
  }

  const query = search.toString()
  return query.length > 0 ? `${url}?${query}` : url
}