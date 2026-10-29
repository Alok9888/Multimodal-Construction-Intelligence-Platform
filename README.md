# BuildSight

A construction-site intelligence demo with a React/Vite web app, FastAPI application/API layer, multimodal AI service, and SQLite plus local-file storage. It accepts site photos, notes, structured project details, and weather observations; it generates typed safety/crack findings, planning allowances, a comparable-sales-based value indication, and a daily site advisory.

## Requirements

- Python 3.9 or newer
- Node.js 20 or newer (Vite 5)
- An OpenAI API key for live multimodal analysis; the app runs without one in clearly labeled demo mode

## Local development

In PowerShell, from the project root:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and set OPENAI_API_KEY; set AI_MODE=live to enable provider calls.
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
npm install
npm run dev
```

Open http://localhost:5173. API docs are at http://127.0.0.1:8000/docs. The frontend proxies `/api` requests to the local backend.

## Configuration

Copy `.env.example` to `.env`. Keep the API key only in `.env` or a deployment secret manager; `.env` is ignored by git. `AI_MODE=mock` provides conservative, labeled placeholders for local demonstrations. `AI_MODE=live` enables the OpenAI multimodal endpoint using `OPENAI_API_KEY` and `OPENAI_MODEL` (default `gpt-4o-mini`); startup fails clearly if live mode has no key. Restart the server after changing settings.

## API

- `GET /api/health`: readiness and configured mode
- `POST /api/analyze`: multipart fields `project` (JSON), `description`, optional `image` (JPEG/PNG/WebP, max 10 MB). Response follows `SiteAnalysis`.
- `POST /api/estimate`: JSON `{ "description": "...", "project": { ... } }`. Response follows `PlanEstimate`.
- `POST /api/valuation`: JSON with `project` plus optional `comparable_sales` entries (`address`, `sale_price`, `area_sqft`, `sale_date`). Without supplied comps, no numeric market indication is returned.
- `POST /api/daily-assistance`: JSON `{ "project": {...}, "weather": {"condition":"...", "temperature_c": 20, "wind_kph": 10, "precipitation_mm": 0} }`. Weather observations are supplied by the user; the app does not retrieve a live forecast.
- `GET /api/records?limit=20` and `GET /api/records/{id}`: retrieve persisted output history.

## Architecture

```text
React web app (src/)
  ├── submits text, image, project details and optional weather observations
  └── renders typed JSON responses and recent saved outputs
              │ /api (Vite dev proxy)
FastAPI API + application logic (backend/main.py)
  ├── multimodal AI service (backend/services.py; OpenAI vision-capable chat model)
  │     ├── construction safety + PPE findings
  │     ├── structural crack findings
  │     ├── project materials/cost/schedule + visualization prompt
  │     ├── property indication from user-provided comparable sales
  │     └── daily site/weather advisory from supplied observations
  └── storage adapter (backend/storage.py)
        ├── SQLite records in data/buildsight.sqlite3
        └── uploaded images in data/files/
```

Each successful generated result is stored with a UUID, type, timestamp, and JSON result; analysis images are saved as files. `STORAGE_DIR` can point to a persistent mounted volume in deployment. The database and image directory are ignored by git. For production, replace local SQLite/files with managed durable storage if deploying across multiple instances, define retention/deletion rules, and add authentication/access controls before exposing record retrieval.

## Scope and limitations

This is a development/demo baseline, not a construction decision system. Image observations can miss hazards or defects; crack cause/severity and PPE compliance require qualified on-site verification. The mock mode does not analyze images. Sample cost rates are illustrative placeholders, not a quote. Scheduling is an initial allowance, not a critical-path plan. Architectural visualization currently returns a prompt; no image-generation provider is connected. The value indication is a simple average of comparable price per area supplied by the user; it does not verify sales or adjust for condition, date, or location. Daily weather advice is based only on user-supplied observations and is not a live forecast. Before deployment, add authentication, rate limits, retention/deletion controls, audit logging, provider-specific privacy review, monitoring, and validated market/weather data sources.
