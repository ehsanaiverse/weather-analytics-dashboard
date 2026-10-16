import { Loader2, MapPin, Search, X } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import type { ReactNode } from 'react'

import type { Location } from '../../api'
import { MIN_QUERY_LENGTH, useLocationSearch } from '../../hooks/useLocationSearch'
import { cn } from '../../lib/cn'

/** Props for {@link LocationSearch}. */
export interface LocationSearchProps {
  readonly selected: Location | null
  readonly onSelect: (location: Location) => void
}

/**
 * City search: pill shape input with glowing cyan focus ring, dropdown list with hover highlight.
 */
export function LocationSearch({ selected, onSelect }: LocationSearchProps): ReactNode {
  const { query, setQuery, clear, results, status, error, belowMinimumLength, noMatches } =
    useLocationSearch()
  const [isOpen, setIsOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)

  const inputId = useId()
  const listboxId = `${inputId}-listbox`
  const containerRef = useRef<HTMLDivElement>(null)

  // Close when focus or a click moves outside the widget.
  useEffect(() => {
    if (!isOpen) {
      return
    }
    const onPointerDown = (event: MouseEvent): void => {
      if (containerRef.current !== null && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', onPointerDown)
    return () => document.removeEventListener('mousedown', onPointerDown)
  }, [isOpen])

  useEffect(() => {
    setActiveIndex(-1)
  }, [results])

  const showResults = isOpen && (status === 'searching' || results.length > 0 || noMatches)

  const choose = (location: Location): void => {
    onSelect(location)
    clear()
    setIsOpen(false)
  }

  const onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>): void => {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setIsOpen(true)
      setActiveIndex((current) => Math.min(current + 1, results.length - 1))
      return
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex((current) => Math.max(current - 1, -1))
      return
    }
    if (event.key === 'Enter') {
      if (activeIndex >= 0 && activeIndex < results.length) {
        event.preventDefault()
        const match = results[activeIndex]
        if (match !== undefined) {
          choose(match)
        }
      }
      return
    }
    if (event.key === 'Escape') {
      setIsOpen(false)
      setActiveIndex(-1)
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <label
        htmlFor={inputId}
        className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400"
      >
        Search Location
      </label>

      <div className="relative">
        <Search
          className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-sky-500 dark:text-cyan-400"
          aria-hidden="true"
        />
        <input
          id={inputId}
          type="search"
          role="combobox"
          autoComplete="off"
          aria-expanded={showResults}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-activedescendant={
            activeIndex >= 0 ? `${listboxId}-option-${activeIndex}` : undefined
          }
          placeholder="Search city (e.g. London, Tokyo)..."
          value={query}
          onChange={(event) => {
            setQuery(event.target.value)
            setIsOpen(true)
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={onKeyDown}
          className="h-11 w-full rounded-full border border-slate-200/90 bg-white/70 pl-10 pr-10 text-sm text-slate-900 placeholder:text-slate-400 backdrop-blur-md transition-all focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400/40 focus:shadow-[0_0_18px_rgba(34,211,238,0.25)] dark:border-white/10 dark:bg-white/5 dark:text-white dark:placeholder:text-slate-500"
        />
        {status === 'searching' && (
          <Loader2
            className="absolute right-3.5 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-cyan-400"
            aria-hidden="true"
          />
        )}
        {query !== '' && status !== 'searching' && (
          <button
            type="button"
            onClick={() => {
              clear()
              setIsOpen(false)
            }}
            aria-label="Clear search"
            className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-1 text-slate-400 hover:text-slate-600 dark:hover:text-white transition-colors"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        )}
      </div>

      <ul
        id={listboxId}
        role="listbox"
        aria-label="Matching locations"
        hidden={!showResults}
        className={cn(
          'surface-card absolute z-30 mt-2 max-h-72 w-full overflow-auto rounded-2xl p-1.5 shadow-2xl backdrop-blur-xl',
          'border border-slate-200/80 bg-white/95 dark:border-white/15 dark:bg-slate-900/90',
        )}
      >
        {status === 'searching' && results.length === 0 && (
          <li className="px-3 py-2 text-sm text-slate-400" role="presentation">
            Searching locations…
          </li>
        )}

        {noMatches && (
          <li className="px-3 py-2 text-sm text-slate-400" role="presentation">
            No location found for “{query.trim()}”.
          </li>
        )}

        {belowMinimumLength && (
          <li className="px-3 py-2 text-sm text-slate-400" role="presentation">
            Type at least {MIN_QUERY_LENGTH} characters.
          </li>
        )}

        {status === 'error' && error !== null && (
          <li className="px-3 py-2 text-sm text-rose-500 dark:text-rose-400" role="presentation">
            {error.message}
          </li>
        )}

        {results.map((location, index) => (
          <li
            key={`${location.latitude},${location.longitude},${location.name}`}
            id={`${listboxId}-option-${index}`}
            role="option"
            aria-selected={index === activeIndex}
            onMouseEnter={() => setActiveIndex(index)}
            onMouseDown={(event) => {
              event.preventDefault()
              choose(location)
            }}
            className={cn(
              'flex cursor-pointer items-start gap-2.5 rounded-xl px-3 py-2.5 text-sm transition-all',
              index === activeIndex
                ? 'bg-sky-500/15 border border-sky-400/30 text-sky-950 dark:bg-cyan-500/15 dark:border-cyan-400/30 dark:text-white'
                : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-white/10',
            )}
          >
            <MapPin
              className="mt-0.5 h-4 w-4 shrink-0 text-sky-500 dark:text-cyan-400"
              aria-hidden="true"
            />
            <span className="min-w-0">
              <span className="block truncate font-semibold text-slate-900 dark:text-white">
                {location.name}
              </span>
              <span className="block truncate text-xs text-slate-500 dark:text-slate-400">
                {[location.admin1, location.country].filter(Boolean).join(', ') || '—'}
                {location.timezone !== null && ` · ${location.timezone}`}
              </span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}