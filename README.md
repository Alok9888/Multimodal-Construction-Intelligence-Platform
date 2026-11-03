# Buildwise — Construction Intelligence

An AI-assisted construction operations workspace for project status, site safety, image analysis, planning, weather-aware decisions, and field questions. This repository contains a React + TypeScript frontend and a FastAPI backend with explicit Pydantic request and response contracts.

## Requirements

- Node.js 20+
- Python 3.11+

## Run locally

In one terminal, start the API:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

In a second terminal, start the web app from the repository root:

```powershell
npm install
npm run dev
```

Open http://localhost:5173. FastAPI docs are available at http://localhost:8000/docs.

## API

- `GET /health` — service health
- `GET /api/projects` — portfolio projects
- `POST /api/projects` — create a project
- `POST /api/assistant/ask` — construction assistant question
- `POST /api/images/analyze` — accept an image for analysis

Set `FRONTEND_ORIGINS` in `backend/.env` to a comma-separated list of allowed frontend origins. The assistant and image endpoints run in demo/receive-only mode until an AI provider and secure project data sources are connected. Do not use demo output as a substitute for professional safety review.

## Free deployment (Render)

The repository includes `render.yaml` for a single free web service that builds the React frontend and serves it from FastAPI on the same origin.

1. Push this repository to a Git provider account.
2. Create a free account at [Render](https://render.com/) and connect that repository.
3. In Render, choose **New → Blueprint**, select the repository, and apply the `render.yaml` blueprint.
4. Wait for the build to finish, then open the generated `onrender.com` URL.

The free web service sleeps after 15 minutes without traffic, so the first visit after idle may take about a minute. Its filesystem is temporary and the current project records are held in memory; they reset after restarts or redeploys. Use a persistent database and storage service before relying on this for real projects.

## Project layout

```text
src/                 React dashboard and responsive styles
backend/app/main.py  FastAPI routes and strict JSON schemas
```
