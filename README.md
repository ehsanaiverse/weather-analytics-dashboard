```text

▄   ▄▗▄▄▄▖  ▄  ▗▄▄▄▖▗▖ ▗▖▗▄▄▄▖▗▄▄▖        ▄  ▗▄ ▗▖  ▄  ▗▖   ▄▖ ▗▄▗▄▄▄▖ ▄▄▄   ▄▄  ▗▄▖      ▗▄▄    ▄   ▗▄▖ ▗▖ ▗▖▗▄▄▖  ▗▄▖   ▄  ▗▄▄▖ ▗▄▄  
█   █▐▛▀▀▘ ▐█▌ ▝▀█▀▘▐▌ ▐▌▐▛▀▀▘▐▛▀▜▌      ▐█▌ ▐█ ▐▌ ▐█▌ ▐▌   ▐▙ ▟▌▝▀█▀▘ ▀█▀  █▀▀▌▗▛▀▜      ▐▛▀█  ▐█▌ ▗▛▀▜ ▐▌ ▐▌▐▛▀▜▌ █▀█  ▐█▌ ▐▛▀▜▌▐▛▀█ 
▜▖█▗▛▐▌    ▐█▌   █  ▐▌ ▐▌▐▌   ▐▌ ▐▌      ▐█▌ ▐▛▌▐▌ ▐█▌ ▐▌    █▄█   █    █  ▐▛   ▐▙        ▐▌ ▐▌ ▐█▌ ▐▙   ▐▌ ▐▌▐▌ ▐▌▐▌ ▐▌ ▐█▌ ▐▌ ▐▌▐▌ ▐▌
▐▌█▐▌▐███  █ █   █  ▐███▌▐███ ▐███       █ █ ▐▌█▐▌ █ █ ▐▌    ▝█▘   █    █  ▐▌    ▜█▙      ▐▌ ▐▌ █ █  ▜█▙ ▐███▌▐███ ▐▌ ▐▌ █ █ ▐███ ▐▌ ▐▌
▐█▀█▌▐▌    ███   █  ▐▌ ▐▌▐▌   ▐▌▝█▖      ███ ▐▌▐▟▌ ███ ▐▌     █    █    █  ▐▙      ▜▌     ▐▌ ▐▌ ███    ▜▌▐▌ ▐▌▐▌ ▐▌▐▌ ▐▌ ███ ▐▌▝█▖▐▌ ▐▌
▐█ █▌▐▙▄▄▖▗█ █▖  █  ▐▌ ▐▌▐▙▄▄▖▐▌ ▐▌     ▗█ █▖▐▌ █▌▗█ █▖▐▙▄▄▖  █    █   ▄█▄  █▄▄▌▐▄▄▟▘     ▐▙▄█ ▗█ █▖▐▄▄▟▘▐▌ ▐▌▐▙▄▟▌ █▄█ ▗█ █▖▐▌ ▐▌▐▙▄█ 
▝▀ ▀▘▝▀▀▀▘▝▘ ▝▘  ▀  ▝▘ ▝▘▝▀▀▀▘▝▘ ▝▀     ▝▘ ▝▘▝▘ ▀▘▝▘ ▝▘▝▀▀▀▘  ▀    ▀   ▀▀▀   ▀▀  ▀▀▘      ▝▀▀  ▝▘ ▝▘ ▀▀▘ ▝▘ ▝▘▝▀▀▀  ▝▀▘ ▝▘ ▝▘▝▘ ▝▀▝▀▀  
```

# Real-Time Weather Analytics Dashboard

An interactive weather dashboard that turns the free
[**Open-Meteo**](https://open-meteo.com/) APIs into a clean, fast analytics UI.
Search any city in the world, inspect current conditions as KPI cards, and explore
hourly and seven-day forecasts through interactive charts and a multivariate
**Chernoff Faces** view.

This repository ships **three cooperating layers** built on one shared Python core:

- **Python core** (`app/services/`, `app/utils/`) — HTTP access, validation, pandas
  reshaping, WMO code translation, timezone handling and Chernoff encoding.
- **FastAPI backend** (`app/main.py`, `app/api/`) — a thin HTTP shell that exposes
  the core as a documented JSON API.
- **React + Vite + TypeScript frontend** (`frontend/`) — the interactive UI that
  consumes that API.

Because the Python core is the single source of truth, the data cannot drift
between consumers — the API layer only reshapes the core's output into response
models, it never re-implements the logic.

This is an educational and portfolio project. It needs **no API key**, **no
database**, and **no paid services** — zero friction to run.

> **On "real-time":** the values shown are the *nearest 15-minute interval* from
> Open-Meteo's forecast-model blend, **not** a reading from a physical weather
> station. Responses are cached (10 minutes for weather, 1 hour for geocoding) and
> every response carries the UTC retrieval timestamp plus explicit cache metadata,
> so the freshness is always visible rather than implied. The UI labels this
> directly instead of claiming live observations.

---

## Table of contents

- [Features](#features)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Repository structure](#repository-structure)
- [Installation & setup](#installation--setup)
- [Running the FastAPI backend](#running-the-fastapi-backend)
- [Running the frontend](#running-the-frontend)
- [REST API reference](#rest-api-reference)
- [Configuration](#configuration)
- [Caching and data freshness](#caching-and-data-freshness)
- [Upstream API usage](#upstream-api-usage)
- [Running the tests](#running-the-tests)
- [Design decisions and data handling](#design-decisions-and-data-handling)
- [Error handling](#error-handling)
- [Attribution and licensing](#attribution-and-licensing)
- [Troubleshooting](#troubleshooting)
- [Author](#author)

---

## Features

### Current conditions

- A **hero card** with a large condition emoji, the temperature (with a
  smaller "feels like" value underneath), the location name and the local clock.
- A **2×2 grid of KPI pills**: humidity, wind speed, precipitation and the
  condition label, each with an icon and an explanatory tooltip.
- Coordinates, elevation and the location's UTC offset.
- Weather condition resolved from the WMO code to human-readable text plus an
  emoji icon.
- Warm/cool visual accents when the temperature or humidity crosses a threshold.

### Location search

- Free-text search of any city worldwide through the Open-Meteo **Geocoding API**.
- **Debounced** (300 ms) and **cancellable** — one request per quiet period, and a
  slow response for `"Londo"` can never overwrite the newer result for `"London"`.
- A keyboard-navigable combobox (`↑`/`↓`/`Enter`/`Escape`) with an accessible
  listbox of matches, so ambiguous names can be disambiguated.
- Blank queries, unknown places and transport failures produce clear,
  non-technical messages.
- Defaults to **Abbottabad, Pakistan**, served from the backend so no client
  hardcodes coordinates and the first render costs no geocoding request.

### Hourly forecast

- Selectable window of **12, 24 or 48 hours**.
- Two views: a scrollable row of **hour cards** (time, condition emoji,
  temperature, precipitation-probability bar) and an interactive **temperature
  line chart**.
- Window boundaries are derived from the response's own reference time and shown
  in the location's local time.

### Daily forecast

- A **seven-day outlook** as glass rows, each with the day label, condition emoji
  and text, a low→high temperature range bar (blue → orange), and a
  precipitation-probability chip.
- Honest labelling: daily figures are whole-day model output, not measurements.

### Data visualisation

Interactive **Recharts** charts with a shared "glass" tooltip and theme-aware
axes:

| Chart | Type | Question it answers |
| --- | --- | --- |
| Hourly temperature forecast | Line with active dot | How does the temperature evolve hour by hour? |
| Hourly relative humidity | Filled area | Is the air getting drier or more humid? |
| Chance of precipitation | Bar | When should I expect rain? |
| Seven-day temperature range | Grouped bar | How wide is the day-to-day temperature swing? |

### Chernoff Faces

A multivariate view that encodes **five weather variables per record** into a
face, so many periods can be compared at a glance. Each face is **one real
forecast record**.

| Facial feature | Hourly variable | Daily variable | Higher value looks like |
| --- | --- | --- | --- |
| face width | Temperature (°C) | Daily maximum temperature (°C) | wider |
| eye size | Relative humidity (%) | Mean relative humidity (%) | larger eyes |
| eyebrow angle | Wind speed (km/h) | Maximum wind speed (km/h) | steeper, more angled brows |
| mouth curvature | Precipitation probability (%) | Max precipitation probability (%) | flatter, then a deeper curve |
| nose length | Apparent temperature (°C) | Max apparent temperature (°C) | longer nose |

- **Hourly or daily** source, and **4, 6, 8 or 12** faces, both selectable.
- Normalisation is performed on the **backend**, min–max scaled to `0–1` across
  exactly the faces returned in that response. The same temperature can therefore
  look warm in one view and cool in another — that is the point of the
  comparison. A different face count is a different request, not a client-side
  slice.
- Constant-valued variables normalise to a neutral midpoint, and missing values
  are drawn using the median of the available values *for geometry only* — the
  `values` always show what the provider actually returned.
- Each face is drawn as **inline SVG** (`FaceSvg.tsx`) with a hover/focus tooltip
  showing the exact reported values, plus a legend explaining the mapping, so the
  encoding is never a black box.
- The geometry rules are ported to `frontend/src/lib/chernoff.ts` and kept in sync
  by two safeguards: the Vitest suite pins the behaviour against reference output
  from the Python module, and `tests/api/test_chernoff_geometry_sync.py` parses
  the TypeScript file and fails if any shared constant drifts.

### Experience & polish

- **Dark-first glassmorphism** design with a subtle CSS aurora background.
- **Light/dark/system** theme toggle; the stored theme is applied before first
  paint to avoid a flash.
- Responsive layout from phone to desktop, with a sticky header and sidebar.
- Loading skeletons, empty states, error banners and data-quality warning banners.
- An **API status badge** in the header that polls `GET /api/health` and turns
  green once the backend answers.
- Accessible by construction: ARIA roles, live regions, a skip link and full
  keyboard support.

---

## Architecture

The layering rule is simple: **a module may only import from the layer above it.**

```
frontend/  (React + Vite + TypeScript — talks HTTP only, imports no Python)
    │  GET /api/health | /config | /locations/default | /locations/search
    │  GET /api/weather | /chernoff          POST /api/cache/refresh
    ▼
app/main.py  (FastAPI: CORS, correlation ids, error envelope, static mount)
    │
    ├── app/api/routers      endpoints, declared sync so requests never block the event loop
    ├── app/api/transformers services/pandas -> Pydantic models (NaN -> null)
    ├── app/api/deps         query validation + cached service access
    ├── app/api/cache        thread-safe TTL caches (no framework imports)
    │
    └── app/utils            pure functions: payloads -> DataFrames, WMO codes,
        │                    timezones, Chernoff encoding  (no framework imports)
        └── app/services      Open-Meteo access
                └── app/services/http_client   the only module that performs HTTP
```

Consequences worth noting:

- The **Python core is shared and framework-free.** `app/utils` never imports
  FastAPI, so the processing layer is fully testable without a running server.
- `http_client.get_json` is the **single point** where timeouts, status codes and
  JSON validation live, so the two services cannot drift apart.
- Domain objects (`Location`, `WeatherBundle`, `CurrentConditions`) are frozen
  dataclasses — hashable, immutable and cheap to cache.
- The `app/api` layer **never re-implements** fetching or processing; it only
  validates input, calls the core, and reshapes the result into response models.
- The Python and TypeScript halves never import each other: the frontend talks to
  the API over HTTP only, and `frontend/` is excluded from Python tooling (Ruff)
  while `app/` is excluded from the frontend tooling (ESLint).

---

## Technology stack

| Tool | Version | Purpose |
| --- | --- | --- |
| Python | ≥ 3.11 | Runtime for the core and the API |
| FastAPI | ≥ 0.115 | REST backend |
| Uvicorn | ≥ 0.30 | ASGI server |
| Pydantic | ≥ 2 (via FastAPI) | Query validation and response models |
| Requests | ≥ 2.31 | HTTP transport to Open-Meteo |
| Pandas | ≥ 2.0 | Payload validation and reshaping |
| Node.js | ≥ 18 | Runtime for the frontend toolchain |
| React | ≥ 19 | Frontend UI library |
| Vite | ≥ 6.4 | Frontend dev server and bundler |
| TypeScript | ~5.9 | Frontend types, strict mode |
| Tailwind CSS | ≥ 3.4 | Utility styling, light/dark themes |
| Recharts | ≥ 3.10 | Interactive charts |
| Lucide React | ≥ 1.50 | Icon set |
| Pytest | ≥ 7.4 | Python test suite |
| Vitest | ≥ 3.2 | Frontend unit tests |
| ESLint | ≥ 9.20 | Frontend linting |
| Ruff | ≥ 0.5 (dev) | Python linting and formatting |

No OpenAI, no paid API, no database, no Docker, no authentication.

---

## Repository structure

```
weather-analytics-dashboard/
├── app/                          # Python core + FastAPI backend
│   ├── __init__.py
│   ├── config.py                 # Endpoints, variables, TTLs, palette, default location
│   ├── main.py                   # FastAPI app factory (CORS, request ids, error envelope, static mount)
│   ├── services/                 # Open-Meteo access (framework-free)
│   │   ├── __init__.py
│   │   ├── exceptions.py         # Typed, user-facing error hierarchy
│   │   ├── http_client.py        # The only module that performs HTTP
│   │   ├── geocoding_service.py  # City search -> Location objects
│   │   └── weather_service.py    # Forecast fetch -> WeatherBundle
│   ├── utils/                    # Pure transformations (no framework imports)
│   │   ├── __init__.py
│   │   ├── data_processing.py    # API payloads -> Pandas DataFrames + CurrentConditions
│   │   ├── weather_codes.py      # WMO 4677 code -> label + emoji
│   │   ├── time_utils.py         # Timezone resolution + local-time formatting
│   │   └── chernoff.py           # Chernoff normalisation + geometry (UI-free)
│   └── api/                      # REST layer (no Streamlit/Plotly imports)
│       ├── __init__.py
│       ├── settings.py           # Environment-driven configuration
│       ├── cache.py              # Thread-safe TTL caches with single flight
│       ├── schemas.py            # Pydantic response models (camelCase wire format)
│       ├── errors.py             # One error envelope + exception mapping
│       ├── deps.py               # Query validation, cached service access
│       ├── transformers.py       # Services/pandas -> API models
│       └── routers/
│           ├── health.py         # /health, /config
│           ├── locations.py      # /locations/default, /locations/search
│           ├── weather.py        # /weather, /chernoff
│           └── cache.py          # /cache/refresh
├── tests/                        # Offline pytest suite (never touches the network)
│   ├── __init__.py
│   ├── conftest.py               # Fixtures, payload builders, network guard
│   ├── test_weather_codes.py     # WMO mapping, including unknown codes
│   ├── test_data_processing.py   # Hourly/daily shaping and missing data
│   ├── test_weather_service.py   # API parsing, HTTP failures, timeouts
│   ├── test_geocoding_service.py # Search, ambiguity, invalid input
│   ├── test_chernoff.py          # Normalisation, feature mapping, geometry
│   └── api/                      # FastAPI endpoint tests (fully offline)
│       ├── conftest.py
│       ├── test_health.py
│       ├── test_locations.py
│       ├── test_weather.py
│       ├── test_chernoff.py
│       ├── test_chernoff_geometry_sync.py   # Python <-> TypeScript constant parity
│       ├── test_cache.py
│       └── test_settings.py
├── frontend/                     # React + Vite + TypeScript client
│   ├── package.json  vite.config.ts  vitest.config.ts  eslint.config.js
│   ├── tailwind.config.js  postcss.config.js  tsconfig*.json  index.html
│   ├── .env.example              # VITE_* variables (no credentials)
│   ├── README.md
│   └── src/
│       ├── main.tsx  App.tsx  index.css  vite-env.d.ts
│       ├── api/                  # types.ts, client.ts, weatherApi.ts, config.ts, index.ts
│       ├── components/           # chernoff, charts, current, forecast, location,
│       │                         # layout, states, theme, ui, api
│       ├── hooks/                # useDashboard, useWeatherData, useChernoffFaces,
│       │                         # useLocationSearch, useApiHealth, useChartTheme,
│       │                         # useDebouncedValue, useTheme
│       ├── lib/                  # chernoff.ts(+test), format.ts(+test), constants.ts, cn.ts
│       └── providers/            # ThemeProvider, theme-context
├── requirements.txt              # Runtime dependencies
├── requirements-dev.txt          # Runtime + test dependencies
├── pyproject.toml                # Project metadata and Ruff configuration
├── pytest.ini                    # Pytest configuration
├── .gitignore
└── README.md
```

---

## Installation & setup

**Python 3.11 or newer** and **Node.js 18 or newer** are required. Start with the
Python backend.

### 1. Create a virtual environment and install dependencies

From the project root:

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt    # runtime only
# or, including the test/lint tooling:
pip install -r requirements-dev.txt
```

Verify the environment:

```bash
python --version                   # expect 3.11+
python -c "import fastapi, pandas, requests; print('dependencies OK')"
```

### 2. Set up the frontend

```bash
cd frontend
npm install
```

That is all the setup — there is no `.env` to create, because the defaults work
and there are no credentials.

---

## Running the FastAPI backend

Start the backend first; the frontend talks to it.

```bash
# development server with auto-reload
uvicorn app.main:app --reload --port 8000

# or, without the extra dependency:
python -m uvicorn app.main:app --port 8000
```

Then open:

- <http://127.0.0.1:8000/api/docs> — interactive Swagger UI
- <http://127.0.0.1:8000/api/openapi.json> — the OpenAPI schema

Quick check:

```bash
curl http://127.0.0.1:8000/api/health
curl "http://127.0.0.1:8000/api/locations/search?q=London"
curl "http://127.0.0.1:8000/api/weather?latitude=34.1463&longitude=73.2117"
```

> Run Uvicorn from the **project root** so the `app/` package is importable.
> `app/main.py` also supports `python -m app.main` for a local dev run.

When `frontend/dist` exists, the API serves the built frontend automatically at
`/` (see `SERVE_FRONTEND`), so production can run as a **single process**.

---

## Running the frontend

The React client lives in `frontend/`. With the backend running:

```bash
# terminal 1 - the API on :8000
uvicorn app.main:app --reload --port 8000

# terminal 2 - the frontend dev server on :5173
cd frontend
npm install        # first time only
npm run dev
```

Open <http://localhost:5173>. The Vite dev server **proxies `/api`** to the
backend, so requests stay same-origin and CORS never gets in the way during
development. The header badge turns green once the backend answers.

| Script | Purpose |
| --- | --- |
| `npm run dev` | Dev server with hot reload (port 5173) |
| `npm run build` | `tsc -b` then a production build into `frontend/dist` |
| `npm run preview` | Serve the production build (port 4173) |
| `npm run lint` | ESLint 9 flat config |
| `npm run typecheck` | Strict TypeScript check, no emit |
| `npm run test` | Vitest suite (normalisation, feature mapping, formatters) |

See [`frontend/README.md`](frontend/README.md) for toolchain details and
conventions.

---

## REST API reference

The backend is a thin HTTP shell over the shared Python core. Every route is
mounted under the `/api` prefix.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness, cache state and the public upstream endpoints |
| `GET` | `/api/config` | Static contract: hour windows, forecast limits, face counts, units |
| `GET` | `/api/locations/default` | The built-in default location, so a client never hardcodes coordinates |
| `GET` | `/api/locations/search` | City search through the Geocoding API (cached 1 h) |
| `GET` | `/api/weather` | Current + hourly window + 7-day outlook + Chernoff faces |
| `GET` | `/api/chernoff` | Chernoff faces for one source only |
| `POST` | `/api/cache/refresh` | Drop cached data so the next request refetches |

### Query parameters

| Endpoint | Parameter | Default | Accepted |
| --- | --- | --- | --- |
| `/api/locations/search` | `q` | required | 1–120 characters |
| | `count` | 10 | 1–10 |
| `/api/weather` | `latitude`, `longitude` | required | -90..90, -180..180 |
| | `hours` | 24 | `12`, `24`, `48` |
| | `forecast_days` | 7 | 1–16 (Open-Meteo limit) |
| | `chernoff_count` | 6 | `4`, `6`, `8`, `12` |
| `/api/chernoff` | `latitude`, `longitude` | required | as above |
| | `source` | required | `hourly`, `daily` |
| | `count` | 6 | `4`, `6`, `8`, `12` |
| `/api/cache/refresh` | `scope` | `weather` | `weather`, `geocoding`, `all` |

### Example: `GET /api/weather`

```jsonc
{
  "meta":    { "latitude": 34.13, "longitude": 73.22, "timezone": "Asia/Karachi",
               "timezoneAbbreviation": "GMT+5", "utcOffsetSeconds": 18000,
               "elevationM": 1241, "retrievedAt": "2026-10-02T17:42:10Z",
               "forecastDays": 7, "cached": false, "cacheAgeSeconds": 0,
               "cacheTtlSeconds": 600,
               "units": { "temperature": "°C", "windSpeed": "km/h", "precipitation": "mm" },
               "provider": { "name": "Open-Meteo", "url": "...", "license": "CC BY 4.0" } },
  "current": { "observedAt": "2026-10-02T22:30:00", "temperatureC": 19.3, "feelsLikeC": 18.6,
               "humidityPct": 50, "windSpeedKmh": 2.8, "precipitationMm": 0,
               "weatherCode": 0, "condition": { "label": "Clear sky", "icon": "☀️", "isKnown": true },
               "hasMeasurements": true },
  "hourly":  [{ "time": "2026-10-02T22:00:00", "label": "Fri 22:00", "temperatureC": 19.4,
                "humidityPct": 51, "precipitationProbabilityPct": 0,
                "windSpeedKmh": 2.6, "apparentTemperatureC": 18.7 }],
  "daily":   [{ "date": "2026-10-02T00:00:00", "label": "Fri 02 Oct",
                "condition": { "label": "Clear sky", "icon": "☀️", "isKnown": true },
                "temperatureMaxC": 26.5, "temperatureMinC": 18.9,
                "precipitationProbabilityMaxPct": 2, "precipitationTotalMm": 0,
                "windSpeedMaxKmh": 11.6, "apparentTemperatureMaxC": 27.4, "humidityMeanPct": 57 }],
  "summary": { "hours": 24, "hoursCount": 24, "daysCount": 7,
               "windowStart": "2026-10-02T22:00:00", "windowEnd": "2026-10-03T21:00:00",
               "missingHourlyCount": 0, "missingDailyCount": 0 },
  "chernoff": { "sources": { "hourly": { "faces": [ /* spec values in 0..1 */ ], "features": [] },
                             "daily":  { "faces": [], "features": [] } }, "note": "..." },
  "warnings": []
}
```

### Conventions a client can rely on

- **JSON keys are camelCase**; Python attributes stay snake_case.
- **A missing measurement is `null`, never `0` and never a bare `NaN`** (which is
  not valid JSON and would break `JSON.parse`).
- **Timestamps in `hourly[].time` and `daily[].date` are naive local strings**,
  because the upstream request uses `timezone=auto`. Only `meta.retrievedAt` is
  UTC. The `label` fields are pre-rendered so a client never has to redo timezone
  arithmetic.
- **Chernoff `spec` values are always in `[0, 1]`**, scaled across the faces in the
  same response; a constant or entirely missing variable is `neutralValue`.
- Every response carries an **`X-Request-ID`** header, echoed in error bodies.

### Configuration

The API reads its settings from the environment; every variable is optional.

| Variable | Default | Purpose |
| --- | --- | --- |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated allowed origins for the Vite dev server |
| `WEATHER_CACHE_TTL_SECONDS` | `600` | Forecast cache lifetime |
| `GEOCODING_CACHE_TTL_SECONDS` | `3600` | Geocoding cache lifetime |
| `LOG_LEVEL` | `INFO` | Root log level for the API process |
| `SERVE_FRONTEND` | `true` | Serve `frontend/dist` at `/` when it exists |
| `FRONTEND_DIST` | `frontend/dist` | Path to the built frontend |

There is no authentication and no credential is read, stored or returned: the
upstream provider needs no API key.

The frontend reads Vite environment variables; copy `frontend/.env.example` to
`frontend/.env.local` to change anything:

| Variable | Default | Purpose |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `/api` | Backend base URL, including the `/api` prefix |
| `VITE_API_PROXY_TARGET` | `http://127.0.0.1:8000` | Where the dev server forwards `/api` |
| `VITE_API_TIMEOUT_MS` | `20000` | Request timeout |

Only `VITE_`-prefixed variables reach the browser and they are inlined at build
time, so changing one means restarting `npm run dev` or rebuilding. Nothing secret
belongs in them: this project has no credentials.

---

## Caching and data freshness

Caching lives in `app/api/cache.py`, **not** inside the services, which keeps the
service layer free of framework imports and easy to test.

| Data | Cache | TTL | Cleared by |
| --- | --- | --- | --- |
| Geocoding results | `geocoding` | 1 hour | expiry, a different search term, or `POST /api/cache/refresh?scope=geocoding` |
| Weather responses | `weather` | 10 minutes | expiry, the refresh button, or `POST /api/cache/refresh` |

Key behaviours:

- The **Refresh weather data** button in the frontend calls
  `POST /api/cache/refresh` and then refetches. Clearing the cache **does not
  guarantee new data** — if the provider has not published a newer model run, you
  get the same numbers. The retrieval timestamp is always shown, so this is
  visible rather than implied.
- The hourly window is derived from the response's **own** `current.time` rather
  than the browser clock, keeping the window stable while a cached response is
  reused.
- **Only the upstream fetch is cached.** Windowing, reshaping and Chernoff
  normalisation run per request, so asking for 48 hours instead of 24 reuses the
  same cached forecast instead of fetching a second one.
- **Concurrent requests for one uncached key share a single upstream call**
  (single flight), and a failed fetch is never cached.
- Every response reports whether it was cached and how old the entry is
  (`meta.cached`, `meta.cacheAgeSeconds`).
- Caching keeps the app well inside Open-Meteo's free-tier limits.

---

## Upstream API usage

Both endpoints are free for non-commercial use and need **no API key**.

### 1. Geocoding — resolve a city name to coordinates

```
GET https://geocoding-api.open-meteo.com/v1/search
    ?name=Abbottabad
    &count=10
    &language=en
    &format=json
```

### 2. Forecast — current conditions, hourly and daily data

```
GET https://api.open-meteo.com/v1/forecast
    ?latitude=34.1463
    &longitude=73.21168
    &current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m
    &hourly=temperature_2m,relative_humidity_2m,precipitation_probability,wind_speed_10m,apparent_temperature
    &daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,wind_speed_10m_max,apparent_temperature_max,relative_humidity_2m_mean
    &temperature_unit=celsius
    &wind_speed_unit=kmh
    &precipitation_unit=mm
    &timezone=auto
    &forecast_days=7
```

Notes on the request design:

- **Only the variables the dashboard renders are requested**, keeping payloads
  small and requests inside the free tier's fair-use limits. `wind_speed_10m`,
  `apparent_temperature` and the daily equivalents back the Chernoff features;
  they are extra fields on these same two requests, not extra calls.
- `timezone=auto` makes the API return timestamps already expressed in the
  location's local time.
- Units are pinned server-side (°C, km/h, mm) so no client-side conversion is
  needed.
- `forecast_days=7` yields 168 hourly points, comfortably more than the largest
  selectable window of 48 hours.
- Every request sends a 15-second timeout, a descriptive `User-Agent`, and checks
  the status code and JSON shape.

---

## Running the tests

A single command runs the whole Python suite:

```bash
pytest
```

With verbose output, or just one test file:

```bash
pytest -v
pytest tests/test_data_processing.py
```

To include the lint check (optional, needs `ruff`):

```bash
pip install ruff
ruff check .
```

The frontend has its own checks:

```bash
cd frontend
npm run lint
npm run typecheck
npm run test
```

**The Python tests never touch the network.** `tests/conftest.py` replaces
`requests.get` with a recording stub and blocks real socket connections, so a
missing mock fails loudly instead of silently calling Open-Meteo.

Coverage includes:

- **Weather codes** — every WMO code, all condition families, unknown codes,
  `None`/`NaN`/strings/booleans/fractional values.
- **Hourly processing** — window sizing (12/24/48), window start derived from the
  API's own reference time, sorting, invalid-timestamp dropping with values kept
  aligned, `NaN` never zero-filled, length mismatches, empty datasets.
- **Daily processing** — sorting, labels, condition mapping, missing codes,
  invalid dates, empty datasets.
- **API response parsing** — full envelope, units, timezone metadata, only the
  declared variables requested, custom forecast lengths, optional-field defaults.
- **HTTP failures** — timeouts, connection errors, HTTP 429, other non-2xx
  statuses, invalid JSON, non-object JSON roots, error-flagged 200 bodies.
- **Geocoding** — multiple matches, empty and `None` queries, no-match responses,
  malformed result entries, transport failures.
- **REST API** — endpoint contracts, query validation, `null` (never `0`, never
  `NaN`) handling, camelCase wire format, the single error envelope, upstream
  failure mapping (404/429/502/504), CORS for the Vite dev server, TTL cache
  behaviour including single-flight and cache-key policy, the refresh endpoint,
  OpenAPI accuracy and the Chernoff specs (all normalised into `[0, 1]`).
- **Cross-language parity** — the Chernoff geometry constants in
  `frontend/src/lib/chernoff.ts` are checked against the Python module.

---

## Design decisions and data handling

**Missing values are never replaced with zero.** A missing measurement stays
`NaN`, so charts draw a gap. Zero is a real temperature; a gap means "not
reported". Over HTTP the same value becomes JSON `null`, and the
`summary.missingHourlyCount` / `summary.missingDailyCount` counters plus the
`warnings` array tell the client what to disclose.

**Unparseable timestamps drop the whole row.** The API returns parallel arrays.
When a timestamp cannot be parsed, the corresponding values are removed with it,
so a single bad entry can never shift every later measurement.

**Unusable datasets return empty frames, not exceptions.** If a block has no valid
timestamps, the builder returns an empty DataFrame with the correct columns and
the UI shows an empty state. The rest of the dashboard keeps working.

**Unknown weather codes degrade gracefully.** A code outside the WMO table becomes
`Unknown weather code (123)`; a missing code becomes `No data available`. Neither
raises.

**Empty search queries fail before any request.** The provider is never called
with a blank name.

**Synchronous endpoints on purpose.** The service layer uses blocking `requests`;
FastAPI runs `def` endpoints in a worker thread pool, so those calls never stall
the event loop.

---

## Error handling

Each failure mode maps to a typed exception in `app/services/exceptions.py` and a
short, friendly message. Stack traces are never shown to users; details go to the
logs instead.

| Situation | Exception | What the user sees |
| --- | --- | --- |
| Blank search | `EmptyQueryError` | "Enter a city name to search for." |
| City not found | `LocationNotFoundError` | "No location found for “X”. Try a different spelling…" |
| No connectivity / DNS failure | `NetworkRequestError` | "Could not reach the weather service. Check your internet connection." |
| Slow provider | `APITimeoutError` | "The weather service did not respond within 15 seconds." |
| Rate limited (HTTP 429) | `APIRateLimitError` | "The weather service is receiving too many requests…" |
| Server or client HTTP error | `APIResponseError` | "The weather service returned an unexpected status (HTTP 500)." |
| Malformed / non-object JSON | `APIResponseError` | "The weather service returned a malformed response." |
| Missing or unexpected fields | `APIResponseError` | "The weather service returned an incomplete response." |
| Invalid timestamps | logged, row dropped | Values render as gaps |
| Empty forecast dataset | empty DataFrame | "The weather service did not return … data…" |

Over HTTP the same exceptions are mapped to status codes in `app/api/errors.py`
and rendered through **one envelope**, so a client only needs one error path:

```json
{
  "error": { "code": "upstream_timeout",
             "message": "The weather service did not respond within 15 seconds.",
             "details": [] },
  "requestId": "f0066a34d530",
  "path": "/api/weather",
  "timestamp": "2026-10-02T17:56:01Z"
}
```

| Code | Status |
| --- | --- |
| `invalid_request` | 400 |
| `location_not_found` | 404 |
| `not_found` / `method_not_allowed` | 404 / 405 |
| `upstream_rate_limited` | 429 (with `Retry-After`) |
| `processing_error` / `internal_error` | 500 |
| `upstream_unreachable` / `upstream_bad_response` | 502 |
| `upstream_timeout` | 504 |

---

## Attribution and licensing

**Weather data by [Open-Meteo](https://open-meteo.com/)**, licensed under
**CC BY 4.0**. Geocoding data is provided by the Open-Meteo Geocoding API.

- [Open-Meteo Terms of Use](https://open-meteo.com/en/terms)
- [Open-Meteo Licence (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)
- [Forecast API documentation](https://open-meteo.com/en/docs)
- [Geocoding API documentation](https://open-meteo.com/en/docs/geocoding-api)

The free, non-commercial API is intended for personal and educational use. If you
deploy this project commercially, review the Open-Meteo terms and consider their
paid plans. This project itself is released under the **MIT licence**.

Attribution is rendered in the dashboard footer, as the CC BY 4.0 licence
requires. Please keep it if you reuse this code.

---

## Troubleshooting

**`uvicorn: command not found`**
The virtual environment is not active, or dependencies were not installed. Run
`source .venv/bin/activate` then `pip install -r requirements.txt`.

**`ModuleNotFoundError: No module named 'app'`**
Run Uvicorn from the project root so the `app/` package is importable:
`uvicorn app.main:app --port 8000` from inside `weather-analytics-dashboard/`.

**"Could not reach the weather service"**
Check connectivity to `https://api.open-meteo.com`. A corporate proxy may require
configuration. Behind a proxy, set `HTTPS_PROXY` before starting the server;
Requests honours it automatically.

**The numbers do not change after refreshing**
Expected. Refreshing clears the local cache, but Open-Meteo may not have published
a newer model run. The retrieval timestamp updates either way.

**`AttributeError` or a stale schema after editing the routers**
Restart the server. `--reload` watches Python files, but `app/main.py` builds the
OpenAPI schema once per process.

**A frontend request is blocked by CORS**
The allowed origins default to the Vite dev server (ports 5173). For another
origin, start the API with
`CORS_ORIGINS="http://localhost:4173" uvicorn app.main:app --port 8000`. During
development, the Vite proxy (`/api` → `http://127.0.0.1:8000`) avoids CORS
entirely because the browser sees a single origin.

**`npm run dev` fails with "Unsupported engine" or Tailwind cannot find a native binding**
Both mean Node is older than the toolchain expects. This repository pins `vite@6`
and `tailwindcss@3.4` precisely because they still support Node 18; upgrading
those two packages means upgrading Node to 20.19+ or 22 first.

**The frontend shows "API offline"**
Start the backend (`uvicorn app.main:app --port 8000`) — the badge reflects
`GET /api/health`. If the backend runs elsewhere, set `VITE_API_PROXY_TARGET` for
the dev proxy or set `VITE_API_BASE_URL` to its full URL (and add that origin to
`CORS_ORIGINS`).

**Dates or times in the UI are shifted by a few hours**
Forecast timestamps arrive as naive local strings for the *queried* location. Do
not pass them to `new Date()`; use the API's pre-rendered `label` field or
`formatLocalTime()` in `frontend/src/lib/format.ts` with `meta.utcOffsetSeconds`.

**`GET /api/weather` answers 400 `invalid_request` with `hours` in the message**
Only the windows in `HOURLY_PERIOD_CHOICES` (12, 24, 48) are accepted, and
`chernoff_count` must be one of 4, 6, 8, 12.

---

## Author

Built and maintained by **Ehsan**.

- **GitHub:** [github.com/ehsanaiverse](https://github.com/ehsanaiverse)
- **LinkedIn:** [linkedin.com/in/ehsanaiverse](https://linkedin.com/in/ehsanaiverse)
- **Twitter / X:** [x.com/ehsanaiverse](https://x.com/ehsanaiverse)

---

Built as an educational project. Weather data by
[Open-Meteo](https://open-meteo.com/) (CC BY 4.0).
