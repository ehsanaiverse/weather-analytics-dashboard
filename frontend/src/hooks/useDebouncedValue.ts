import { useEffect, useState } from 'react'

/**
 * Return `value` only after it has stopped changing for `delayMs`.
 *
 * Used by the location search so a burst of keystrokes produces one API request
 * instead of one per character.
 *
 * @param value - The value that changes rapidly (e.g. the search input).
 * @param delayMs - Quiet period required before the value is published.
 */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState<T>(value)

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebounced(value)
    }, delayMs)
    return () => {
      window.clearTimeout(timer)
    }
  }, [value, delayMs])

  return debounced
}