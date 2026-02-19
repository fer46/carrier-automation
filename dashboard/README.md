# Carrier Load Analytics Dashboard

Real-time analytics dashboard for the AI-powered carrier load booking system. Visualizes call outcomes, carrier performance, negotiation metrics, and lane geography.

## Tech Stack

- **React 19** + **TypeScript 5.9**
- **Vite 7** (dev server + bundler)
- **Tailwind CSS 4** (via Vite plugin — no PostCSS config needed)
- **Recharts 3** (area, bar, pie charts)
- **react-simple-maps 3** (interactive US arc map)

## Project Structure

```
src/
├── App.tsx                  # Root component — state, data fetching, tab routing
├── main.tsx                 # Entry point (renders App to #root)
├── api.ts                   # HTTP client (generic fetchAPI<T> wrapper)
├── types.ts                 # TypeScript interfaces (mirrors backend Pydantic models)
├── index.css                # Tailwind CSS imports
├── react-simple-maps.d.ts   # Type declarations for react-simple-maps
└── components/
    ├── Header.tsx            # Sticky top bar — branding, time range toggle, refresh
    ├── KPICard.tsx           # Single metric card (number, percent, duration, dollar formats)
    ├── OperationsTab.tsx     # Conversion funnel, call volume over time, rejection reasons
    ├── NegotiationsTab.tsx   # Savings stats, negotiation outcomes pie, margin distribution
    ├── CarriersTab.tsx       # Lane intelligence, equipment mix, objections, leaderboard
    ├── GeographyTab.tsx      # US arc map, city markers, lane lists, hub rankings
    └── EmptyState.tsx        # Fallback placeholder for empty data
```

## Getting Started

```bash
# Install dependencies
npm install

# Create .env with your API key
echo "VITE_API_KEY=your_api_key_here" > .env

# Start dev server (proxies /api to localhost:8000)
npm run dev
```

The dev server proxies `/api` requests to `localhost:8000`, so make sure the FastAPI backend is running.

## Scripts

| Command           | Description                              |
| ----------------- | ---------------------------------------- |
| `npm run dev`     | Start Vite dev server with HMR           |
| `npm run build`   | Type-check (`tsc -b`) then Vite build    |
| `npm run lint`    | Lint all files with ESLint               |
| `npm run preview` | Preview the production build locally     |

## How It Works

### Data Flow

1. `App.tsx` fetches 5 analytics endpoints in parallel on mount and when the time range changes
2. Each tab component receives its data slice as a nullable prop
3. Auto-refreshes every 5 minutes via polling interval
4. Empty states render gracefully when data is null or arrays are empty

### API Client (`api.ts`)

- Generic `fetchAPI<T>(path, params?)` builds URLs from `window.location.origin`
- Sends `X-API-Key` header from `VITE_API_KEY` env var
- Strips falsy query params to keep URLs clean
- All endpoints live under `/api/analytics/`

### Tabs

| Tab             | Visualizations                                                               |
| --------------- | ---------------------------------------------------------------------------- |
| **Operations**  | Conversion funnel (7 stages), call volume area chart, rejection reasons bars  |
| **Negotiations**| Savings stats cards, outcome donut chart, margin distribution histogram       |
| **Carriers**    | Top requested/actual lanes, equipment donut, objections bars, leaderboard table |
| **Geography**   | Interactive US map with arcs (requested vs booked lanes), city markers, hub lists |

### KPI Hero Row

8 summary cards at the top: Total Calls, Avg Call Duration, Acceptance Rate, Booked Revenue, Gross Margin, Avg Margin %, Rate/Mile, Unique Carriers. Formats include number, percentage, duration (`Xm Ys`), and dollar.

## Production Build

```bash
npm run build
```

Outputs to `dist/`, which the FastAPI backend serves at `/dashboard`. The SPA only mounts if `dashboard/dist/` exists at FastAPI startup — without building first, `/dashboard` returns 404.

## Environment Variables

| Variable       | Description                                     |
| -------------- | ----------------------------------------------- |
| `VITE_API_KEY` | API key sent as `X-API-Key` header on all requests |

Must be prefixed with `VITE_` for Vite to expose it to the client bundle.
