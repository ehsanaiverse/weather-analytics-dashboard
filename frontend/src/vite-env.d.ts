/// <reference types="vite/client" />

/**
 * Typed access to Vite's environment variables.
 *
 * Only `VITE_`-prefixed variables are exposed to the browser, and they are
 * inlined at build time. `.env.example` documents each one; none of them may
 * hold a secret.
 */
interface ImportMetaEnv {
  /** Base URL of the FastAPI backend, including its `/api` prefix. */
  readonly VITE_API_BASE_URL?: string
  /** Target the dev-server proxy forwards `/api` to (build-time only). */
  readonly VITE_API_PROXY_TARGET?: string
  /** Request timeout in milliseconds. */
  readonly VITE_API_TIMEOUT_MS?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}