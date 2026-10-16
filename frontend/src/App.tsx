import type { ReactNode } from 'react'

import {
  APP_SUBTITLE,
  APP_TITLE,
  ATTRIBUTION_TEXT,
  DATA_FRESHNESS_NOTE,
} from './lib/constants'
import { AppShell } from './components/layout/AppShell'
import { DashboardSidebar } from './components/location/DashboardSidebar'
import { CurrentWeatherHero } from './components/current/CurrentWeatherHero'
import { MetricGrid } from './components/current/MetricGrid'
import { DailyForecastSection } from './components/forecast/DailyForecastSection'
import { HourlyForecastSection } from './components/forecast/HourlyForecastSection'
import { ChernoffFacesSection } from './components/chernoff/ChernoffFacesSection'
import {
  ChartSkeleton,
  ErrorState,
  HeroSkeleton,
  WarningBanner,
} from './components/states/DashboardStates'
import { ApiStatusBadge } from './components/api/ApiStatusBadge'
import { useApiHealth } from './hooks/useApiHealth'
import { useDashboard } from './hooks/useDashboard'

/**
 * The weather dashboard with dark-first glassmorphism design.
 *
 * Sticky header with app identity on left and health badge + theme toggle on right.
 * Sidebar + main layout on >= lg breakpoint, single column on mobile.
 */
export function App(): ReactNode {
  const dashboard = useDashboard()
  const api = useApiHealth()
  const { location, weather, hours, setHours, selectLocation, refresh, status, error } = dashboard

  // Silent load for default location bootstrap: only show skeletons if actively loading weather
  const awaitingFirstData = weather === null && status === 'loading'
  const showFatalError = weather === null && error !== null

  return (
    <AppShell
      title={APP_TITLE}
      subtitle={APP_SUBTITLE}
      attribution={ATTRIBUTION_TEXT}
      version="0.2.0"
      headerActions={<ApiStatusBadge state={api} />}
    >
      <p className="sr-only" role="status" aria-live="polite">
        {dashboard.isRefreshing
          ? 'Refreshing weather data'
          : status === 'error' && error !== null
            ? `Weather data could not be loaded: ${error.message}`
            : weather !== null
              ? `Showing weather for ${location?.shortLabel ?? 'the selected location'}`
              : 'Loading weather data'}
      </p>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
        <DashboardSidebar
          location={location}
          onSelect={selectLocation}
          onRefresh={refresh}
          isRefreshing={dashboard.isRefreshing}
          api={api}
        />

        <div className="min-w-0 space-y-6">
          {weather !== null && <WarningBanner messages={weather.warnings} />}

          {showFatalError && error !== null && (
            <ErrorState error={error} onRetry={refresh} />
          )}

          {awaitingFirstData && (
            <div className="space-y-6">
              <HeroSkeleton />
              <ChartSkeleton />
            </div>
          )}

          {weather !== null && location !== null && (
            <>
              {/* Unified Current Weather Card containing hero reading & 2x2 metric pills */}
              <CurrentWeatherHero
                location={location}
                weather={weather}
                now={dashboard.now}
                isRefreshing={dashboard.isRefreshing}
              >
                <MetricGrid current={weather.current} />
              </CurrentWeatherHero>

              <div className="space-y-1 px-1">
                <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                  {DATA_FRESHNESS_NOTE}
                </p>

                {weather.meta.cached && (
                  <p className="text-xs text-sky-600 dark:text-cyan-400/90 font-medium" role="status">
                    Served from cache ({Math.round(weather.meta.cacheAgeSeconds)}s old, TTL{' '}
                    {weather.meta.cacheTtlSeconds}s). Use “Refresh weather data” for the latest model
                    run.
                  </p>
                )}
              </div>

              <HourlyForecastSection
                weather={weather}
                hours={hours}
                onHoursChange={setHours}
                isBusy={dashboard.isBusy}
              />

              <DailyForecastSection weather={weather} />

              <ChernoffFacesSection
                weather={weather}
                latitude={location.latitude}
                longitude={location.longitude}
              />
            </>
          )}
        </div>
      </div>
    </AppShell>
  )
}

export default App