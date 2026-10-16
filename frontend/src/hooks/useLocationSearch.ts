import { useCallback, useEffect, useRef, useState } from 'react'

import { ApiError, searchLocations } from '../api'
import type { Location } from '../api'
import { useDebouncedValue } from './useDebouncedValue'

/** Shortest query worth sending; one letter matches most of the world. */
export const MIN_QUERY_LENGTH = 2

/** Idle, loading, done or failed - used to drive the results list. */
export type SearchStatus = 'idle' | 'searching' | 'success' | 'error'

/** Value returned by {@link useLocationSearch}. */
export interface LocationSearchState {
  readonly query: string
  readonly setQuery: (value: string) => void
  readonly clear: () => void
  readonly results: readonly Location[]
  readonly status: SearchStatus
  readonly error: ApiError | null
  /** Whether the current query is too short to search for. */
  readonly belowMinimumLength: boolean
  /** Whether the provider has no match for the current query. */
  readonly noMatches: boolean
}

/**
 * Debounced, cancellable location search.
 *
 * Two guards keep results trustworthy:
 *
 * 1. **Debouncing** - one request per quiet period, not per keystroke.
 * 2. **Sequencing** - every request carries an id, and a response whose id is no
 *    longer the newest is discarded. Combined with an `AbortController`, a slow
 *    response for "Londo" can never overwrite the newer result for "London".
 */
export function useLocationSearch(delayMs = 300): LocationSearchState {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<readonly Location[]>([])
  const [status, setStatus] = useState<SearchStatus>('idle')
  const [error, setError] = useState<ApiError | null>(null)

  const debouncedQuery = useDebouncedValue(query, delayMs)
  const requestIdRef = useRef(0)
  const controllerRef = useRef<AbortController | null>(null)
  const trimmed = debouncedQuery.trim()
  const readyToSearch = trimmed.length >= MIN_QUERY_LENGTH

  useEffect(() => {
    if (!readyToSearch) {
      controllerRef.current?.abort()
      requestIdRef.current += 1
      setResults([])
      setError(null)
      setStatus('idle')
      return
    }

    const requestId = requestIdRef.current + 1
    requestIdRef.current = requestId
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller

    setStatus('searching')

    searchLocations(trimmed, { signal: controller.signal })
      .then((response) => {
        // A newer request has been issued: this response is stale, drop it.
        if (requestId !== requestIdRef.current || controller.signal.aborted) {
          return
        }
        setResults(response.results)
        setError(null)
        setStatus('success')
      })
      .catch((cause: unknown) => {
        if (requestId !== requestIdRef.current || controller.signal.aborted) {
          return
        }
        const apiError =
          cause instanceof ApiError
            ? cause
            : new ApiError('The location search failed unexpectedly.', {
                status: 0,
                code: null,
                requestId: '',
              })
        if (apiError.status === 0 && apiError.message.startsWith('The request was cancelled')) {
          return
        }
        setResults([])
        setError(apiError)
        setStatus('error')
      })
  }, [trimmed, readyToSearch])

  useEffect(() => {
    return () => {
      controllerRef.current?.abort()
    }
  }, [])

  const clear = useCallback(() => {
    requestIdRef.current += 1
    setQuery('')
    setResults([])
    setError(null)
    setStatus('idle')
  }, [])

  return {
    query,
    setQuery,
    clear,
    results,
    status,
    error,
    belowMinimumLength: query.trim().length > 0 && query.trim().length < MIN_QUERY_LENGTH,
    noMatches: status === 'success' && results.length === 0 && readyToSearch,
  }
}