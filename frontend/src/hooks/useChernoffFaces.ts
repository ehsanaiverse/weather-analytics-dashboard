import { useEffect, useRef, useState } from 'react'

import { ApiError, getChernoffFaces } from '../api'
import type { Chernoff, ChernoffSource, ChernoffSourceKey } from '../api'

/** Parameters for {@link useChernoffFaces}. */
export interface ChernoffQuery {
  readonly latitude: number
  readonly longitude: number
  readonly source: ChernoffSourceKey
  readonly count: number
}

/** Value returned by {@link useChernoffFaces}. */
export interface ChernoffState {
  readonly data: ChernoffSource | null
  readonly isBusy: boolean
  readonly error: ApiError | null
}

/** Coerce any thrown value into an {@link ApiError}. */
function toApiError(cause: unknown): ApiError {
  return cause instanceof ApiError
    ? cause
    : new ApiError('Could not prepare the Chernoff faces.', { status: 0, code: null, requestId: '' })
}

/** Cache key for one prepared set of faces. */
function keyOf(query: ChernoffQuery): string {
  return `${query.latitude},${query.longitude},${query.source},${query.count}`
}

/** Whether the faces embedded in the forecast response are the ones requested. */
function seedMatches(seed: ChernoffSource | null, query: ChernoffQuery | null): boolean {
  return (
    seed !== null &&
    query !== null &&
    seed.source === query.source &&
    seed.requestedCount === query.count
  )
}

/**
 * Load the prepared faces for one source and count.
 *
 * The forecast response already embeds faces at the default count, so `seed` is
 * used **synchronously** when it matches the requested source and count: the
 * first paint already shows faces instead of flashing an empty state. Any other
 * combination is fetched from `GET /api/chernoff` and kept in a small
 * keyed cache, so switching back and forth does not refetch.
 *
 * Normalisation happens on the server, relative to exactly the faces it returns,
 * which is why a different count needs a different request rather than a
 * client-side slice.
 */
export function useChernoffFaces(
  query: ChernoffQuery | null,
  seed: ChernoffSource | null,
): ChernoffState {
  const [fetched, setFetched] = useState<{ key: string; source: ChernoffSource } | null>(null)
  const [pendingKey, setPendingKey] = useState<string | null>(null)
  const [error, setError] = useState<ApiError | null>(null)

  const key = query === null ? null : keyOf(query)
  const useSeed = seedMatches(seed, query)

  // Derive during render rather than in an effect: no extra paint, and it works
  // for the very first frame the section is mounted.
  const data = useSeed ? seed : (fetched !== null && fetched.key === key ? fetched.source : null)

  const requestIdRef = useRef(0)
  const controllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (query === null || key === null || useSeed) {
      return
    }
    // Already have this exact set from an earlier visit.
    if (fetched !== null && fetched.key === key) {
      return
    }

    const requestId = requestIdRef.current + 1
    requestIdRef.current = requestId
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller

    // Keep the previous faces on screen while the new ones are prepared, so the
    // grid never blanks out when the count changes.
    setPendingKey(key)
    setError(null)

    getChernoffFaces({ ...query, signal: controller.signal })
      .then((response: Chernoff) => {
        if (requestId !== requestIdRef.current || controller.signal.aborted) {
          return
        }
        const source = response.sources[query.source] ?? null
        if (source !== null) {
          setFetched({ key, source })
        }
        setError(null)
        setPendingKey(null)
      })
      .catch((cause: unknown) => {
        if (requestId !== requestIdRef.current || controller.signal.aborted) {
          return
        }
        setError(toApiError(cause))
        setPendingKey(null)
      })
  }, [query, key, useSeed, fetched])

  useEffect(() => {
    return () => {
      controllerRef.current?.abort()
    }
  }, [])

  return { data, isBusy: pendingKey === key, error }
}