import { useCallback, useEffect, useRef, useState } from 'react'

import { ApiError, getHealth } from '../api'
import type { HealthResponse } from '../api'

/** Connection state of the backend. */
export type ApiStatus = 'idle' | 'checking' | 'online' | 'offline'

/** Value returned by {@link useApiHealth}. */
export interface ApiHealthState {
  readonly status: ApiStatus
  readonly health: HealthResponse | null
  readonly error: ApiError | null
  readonly check: () => void
}

/**
 * Poll `GET /api/health` once on mount and on demand.
 *
 * This is the foundation check for the service layer: it proves the dev-server
 * proxy, the CORS configuration, the error envelope and the typed client all
 * work before any dashboard section depends on them.
 */
export function useApiHealth(): ApiHealthState {
  const [status, setStatus] = useState<ApiStatus>('idle')
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const check = useCallback(() => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setStatus('checking')
    getHealth({ signal: controller.signal })
      .then((response) => {
        if (controller.signal.aborted) {
          return
        }
        setHealth(response)
        setError(null)
        setStatus('online')
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) {
          return
        }
        setHealth(null)
        setError(
          cause instanceof ApiError
            ? cause
            : new ApiError('Unexpected error while checking the API.', {
                status: 0,
                code: null,
                requestId: '',
              }),
        )
        setStatus('offline')
      })
  }, [])

  useEffect(() => {
    check()
    return () => abortRef.current?.abort()
  }, [check])

  return { status, health, error, check }
}