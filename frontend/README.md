# Weather Analytics Dashboard — Frontend

React + Vite + TypeScript client for the FastAPI backend in this repository.

This folder currently holds the **foundation**: the toolchain, theming, page
shell and a typed API service layer. The dashboard sections (search, current
conditions, charts, Chernoff Faces) are built on top of it in later phases.

---

## Requirements

| Tool | Version | Why this range |
| --- | --- | --- |
| Node.js | **18.x** (or 20/22) | The machine this project was verified on runs Node 18.19.1. Vite 7+ and Tailwind 4 both require Node 20+, so both are pinned below. |
| npm | 9+ | Ships with Node 18. |

Pinned versions (see `package.json`):

- `vite@^6.4` — the last major with Node 18 in its `engines` field
- `@vitejs/plugin-react@^4.7` — peer range covers Vite 6
- `tailwindcss@^3.4` — Tailwind 4's native `@tailwindcss/oxide` binding fails on Node 18
- `typescript@~5.9` — stable compiler line with the ESLint/Vite tooling

## Getting started

```bash
npm install
cp .env.example .env.local     # optional; defaults work as-is
npm run dev                    # http://localhost:5173
```

The API is reached through the same origin: `vite.config.ts` proxies `/api` to
`http://127.0.0.1:8000`, so the browser never makes a cross-origin request and
CORS stays out of the way during development.

## npm scripts

| Script | What it does |
| --- | --- |
| `npm run dev` | Dev server with hot reload on port 5173 (proxies `/api`) |
| `npm run build` | Type-checks with `tsc -b`, then builds to `dist/` |
| `npm run preview` | Serves the production build on port 4173 (proxies `/api`) |
| `npm run lint` | ESLint 9 flat config over the whole project |
| `npm run typecheck` | `tsc -b` in strict mode, no emit |
| `npm run test` | Vitest, single run (52 tests: normalisation, feature mapping, formatters) |
| `npm run test:watch` | Vitest in watch mode |

## Environment variables

Only `VITE_`-prefixed variables reach the browser, and they are **inlined at build
time** — changing one requires restarting `npm run dev` or rebuilding. Never put a
secret in one; this project has no credentials because Open-Meteo needs no API
key. See `.env.example`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `/api` | Base URL of the backend, including the `/api` prefix |
| `VITE_API_PROXY_TARGET` | `http://127.0.0.1:8000` | Where the dev/preview server forwards `/api` |
| `VITE_API_TIMEOUT_MS` | `20000` | Request timeout |

## Project structure

```
src/
├── main.tsx                  # Entry point: StrictMode + ThemeProvider
├── App.tsx                   # Dashboard composition
├── index.css                 # Tailwind layers + theme tokens (light/dark)
├── vite-env.d.ts             # Typed import.meta.env
├── api/
│   ├── types.ts              # Types mirroring app/api/schemas.py 1:1
│   ├── config.ts             # Base URL, timeout, route table
│   ├── client.ts             # fetch wrapper -> ApiError
│   ├── weatherApi.ts         # One function per backend endpoint
│   └── index.ts              # Public surface of the layer
├── components/
│   ├── chernoff/             # FaceSvg, ChernoffFacesSection, ChernoffLegend
│   ├── charts/               # ChartCard, WeatherCharts (Recharts)
│   ├── current/              # CurrentWeatherHero, MetricGrid
│   ├── forecast/             # HourlyForecastSection, DailyForecastSection
│   ├── location/             # LocationSearch, DashboardSidebar
│   ├── layout/               # AppShell, AppHeader, AppFooter
│   ├── states/               # Skeletons, EmptyState, ErrorState, WarningBanner
│   ├── theme/ThemeToggle.tsx
│   ├── ui/                   # Card, Button
│   └── api/ApiStatusBadge.tsx
├── hooks/                    # useDashboard, useWeatherData, useChernoffFaces,
│                             # useLocationSearch, useApiHealth, useChartTheme,
│                             # useDebouncedValue, useTheme
├── lib/
│   ├── chernoff.ts           # Normalisation + face geometry (port of Python)
│   ├── chernoff.test.ts      # 36 tests, including parity with the Python port
│   ├── format.ts             # Number/time formatting
│   ├── format.test.ts        # 16 tests
│   ├── constants.ts          # Titles and the CC BY 4.0 attribution
│   └── cn.ts                 # Class-name joiner
└── providers/                # ThemeProvider, theme-context
```

## Chernoff Faces

The feature has two renderers, so the encoding rules live in two files that must
agree:

| | Python | TypeScript |
| --- | --- | --- |
| Normalisation + geometry | `app/utils/chernoff.py` | `src/lib/chernoff.ts` |
| Renderer | `app/components/chernoff.py` (Plotly shapes) | `src/components/chernoff/FaceSvg.tsx` (SVG) |

The **feature mapping is unchanged** from the original implementation:

| Facial feature | Hourly variable | Daily variable |
| --- | --- | --- |
| face width | Temperature | Daily maximum temperature |
| eye size | Relative humidity | Mean relative humidity |
| eyebrow angle | Wind speed | Maximum wind speed |
| mouth curvature | Precipitation probability | Max precipitation probability |
| nose length | Apparent temperature | Max apparent temperature |

Two safeguards keep the ports honest:

- `src/lib/chernoff.test.ts` pins the *behaviour* against reference output
  generated from the Python module: geometry for four specs, the emitted SVG
  paths, monotonicity of every feature, and the "everything stays inside the head"
  invariant.
- `tests/api/test_chernoff_geometry_sync.py` parses `src/lib/chernoff.ts` and
  asserts every shared constant and range still equals the Python value. Change
  one side and both suites fail.

The split of responsibility is deliberate: the **backend** performs the min-max
scaling - relative to exactly the faces it returns, with a median fill for missing
values and a neutral midpoint for constant ones - and this side only maps
`spec` to geometry. That is why changing the face count issues a request to
`/api/chernoff` instead of slicing client-side.

## Theming

Tailwind runs with `darkMode: 'class'`. Colours are CSS variables holding bare
RGB channels (`--color-surface: 255 255 255`), so utilities keep their alpha
channel (`bg-surface/80`) and both themes share one class name. `ThemeProvider`
toggles `dark` on `<html>`, updates `color-scheme` and persists the choice;
`index.html` applies the stored theme in an inline script to avoid a flash. With
no stored preference the app follows `prefers-color-scheme` live, and the header
control can return to that "system" mode.

## Connecting to the backend

The frontend is independent of Streamlit: it never imports Python and talks only
to the HTTP API.

```bash
# terminal 1 - the API
cd ..
uvicorn app.main:app --reload --port 8000

# terminal 2 - this frontend
npm run dev
```

The header badge calls `GET /api/health`, so it turns green once the backend is
up and shows the exact reason when it is not.

## Current status

Working today: location search, current-conditions hero, five KPI cards,
hourly and daily Recharts charts, Chernoff Faces, refresh, light/dark themes,
responsive layout from phone to desktop, and loading/empty/error states.

Vitest covers the pure logic (52 tests). Component rendering is verified against
live API responses during development rather than in unit tests, because the
charts need a DOM to measure.