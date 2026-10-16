/**
 * Low-level HTTP client for the Weather Analytics Dashboard API.
 *
 * Responsibilities kept deliberately narrow:
 *  - build the URL and issue the request,
 *  - apply a timeout and honour an external `AbortSignal`,
 *  - translate every failure into an {@link ApiError}.
 *
 * It knows nothing about individual endpoints; `weatherApi.ts` owns that.
 */

import { API_TIMEOUT_MS, apiUrl } from './config'
import type { ApiErrorCode, ApiErrorResponse, ErrorDetail } from './types'

/** Status codes the client maps explicitly; anything else becomes `unknown`. */
const KNOWN_ERROR_CODES: readonly ApiErrorCode[] = [
  'invalid_request',
  'location_not_found',
  'upstream_rate_limited',
  'upstream_timeout',
  'upstream_unreachable',
  'upstream_bad_response',
  'processing_error',
  'not_found',
  'method_not_allowed',
  'internal_error',
]

/** HTTP methods this client is allowed to use. */
type HttpMethod = 'GET' | 'POST'

/** Options accepted by {@link request} and {@link post}. */
export interface RequestOptions {
  /** Query parameters; `undefined` values are omitted. */
  readonly params?: Record<string, string | number | undefined> | undefined
  /** Caller-owned cancellation. */
  readonly signal?: AbortSignal | undefined
  /** Override the default timeout, in milliseconds. */
  readonly timeoutMs?: number | undefined
}

/**
 * A failed API call.
 *
 * Carries the backend's machine-readable code alongside the message the user
 * should read, so components can react to `upstream_timeout` without string
 * matching.
 */
export class ApiError extends Error {
  /** HTTP status code, or 0 when the request never reached the server. */
  readonly status: number
  /** Stable code from the API, or `null` when the body was not the standard envelope. */
  readonly code: ApiErrorCode | null
  /** Correlation id, echoed in the `X-Request-ID` response header. */
  readonly requestId: string
  /** Field-level details, present for validation failures. */
  readonly details: readonly ErrorDetail[]

  constructor(
    message: string,
    options: {
      readonly status: number
      readonly code: ApiErrorCode | null
      readonly requestId: string
      readonly details?: readonly ErrorDetail[]
    },
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = options.status
    this.code = options.code
    this.requestId = options.requestId
    this.details = options.details ?? []
  }

  /** Whether retrying the same request could plausibly succeed. */
  get isRetryable(): boolean {
    return (
      this.status === 0 || this.status === 429 || this.status >= 500
    )
  }
}

/** Narrow an unknown value to the API error envelope. */
function isErrorEnvelope(value: unknown): value is ApiErrorResponse {
  if (typeof value !== 'object' || value === null) {
    return false
  }
  const candidate = value as { error?: unknown }
  return typeof candidate.error === 'object' && candidate.error !== null
}

/** Narrow an unknown value to one of the documented error codes. */
function asErrorCode(value: unknown): ApiErrorCode | null {
  return typeof value === 'string' && (KNOWN_ERROR_CODES as readonly string[]).includes(value)
    ? (value as ApiErrorCode)
    : null
}

/** Build the error thrown when the request never produced an HTTP response. */
function transportError(callerAborted: boolean): ApiError {
  return callerAborted
    ? new ApiError('The request was cancelled.', { status: 0, code: null, requestId: '' })
    : new ApiError('Could not reach the weather service. Check your connection.', {
        status: 0,
        code: 'upstream_unreachable',
        requestId: '',
      })
}

/** Build the error thrown when a response arrived but was not the documented envelope. */
function statusError(response: Response, requestId: string): ApiError {
  return new ApiError(`The server returned an unexpected status (HTTP ${response.status}).`, {
    status: response.status,
    code: null,
    requestId,
  })
}

/** Issue one request and decode its JSON body, whatever the method. */
async function send<T>(method: HttpMethod, path: string, options: RequestOptions): Promise<T> {
  const { params, signal, timeoutMs = API_TIMEOUT_MS } = options
  const url = apiUrl(path, params)

  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)
  const abortFromCaller = (): void => controller.abort()
  signal?.addEventListener('abort', abortFromCaller)

  let response: Response
  try {
    response = await fetch(url, {
      method,
      signal: controller.signal,
      headers: { Accept: 'application/json' },
    })
  } catch {
    throw transportError(signal?.aborted === true)
  } finally {
    window.clearTimeout(timeoutId)
    signal?.removeEventListener('abort', abortFromCaller)
  }

  const requestId = response.headers.get('X-Request-ID') ?? ''
  const payload: unknown = await response.json().catch(() => null)

  if (!response.ok) {
    if (!isErrorEnvelope(payload)) {
      throw statusError(response, requestId)
    }
    throw new ApiError(payload.error.message, {
      status: response.status,
      code: asErrorCode(payload.error.code),
      requestId: payload.requestId || requestId,
      details: payload.error.details ?? [],
    })
  }

  return payload as T
}

/** Perform a GET request and decode the JSON body.
 *
 * @throws {ApiError} for any non-2xx response, network failure, timeout,
 * cancellation, or malformed JSON. The thrown error always carries a message
 * suitable for display.
 */
export function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  return send<T>('GET', path, options)
}

/** Perform a POST request and decode the JSON body.
 *
 * Only `POST /api/cache/refresh` exists today, so there is no request-body
 * support; adding it later means extending this signature rather than the
 * endpoints.
 */
export function post<T>(path: string, options: RequestOptions = {}): Promise<T> {
  return send<T>('POST', path, options)
}