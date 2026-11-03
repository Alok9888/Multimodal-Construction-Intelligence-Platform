from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Buildwise Construction Intelligence"
    api_prefix: str = "/api"
    frontend_origins: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


class ProjectStatus(str, Enum):
    on_track = "on_track"
    needs_attention = "needs_attention"
    at_risk = "at_risk"


class Project(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    location: str
    progress: int = Field(ge=0, le=100)
    health: ProjectStatus
    stage: str
    due_date: str
    budget_usd: int = Field(ge=0)


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=120)
    location: str = Field(min_length=2, max_length=120)
    budget_usd: int = Field(default=0, ge=0)


class AssistantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=2, max_length=2000)
    project_name: str | None = Field(default=None, max_length=120)


class AssistantResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str
    category: Literal["Site assistant"] = "Site assistant"
    confidence: float = Field(ge=0, le=1)
    mode: Literal["demo", "ai"] = "demo"


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    timestamp: datetime


class ImageAnalysisResponse(BaseModel):
    filename: str
    content_type: str
    bytes_received: int
    status: Literal["received"] = "received"
    message: str


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
origins = [origin.strip() for origin in settings.frontend_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

_projects: list[Project] = [
    Project(id="northstar", name="Northstar Residences", location="Austin, TX", progress=68, health=ProjectStatus.on_track, stage="Structure", due_date="2026-10-01", budget_usd=4_800_000),
    Project(id="civic-arts", name="Civic Arts Pavilion", location="Portland, OR", progress=42, health=ProjectStatus.needs_attention, stage="Foundation", due_date="2027-01-15", budget_usd=2_100_000),
    Project(id="meridian", name="Meridian Office Park", location="Denver, CO", progress=86, health=ProjectStatus.on_track, stage="Finishing", due_date="2026-08-30", budget_usd=6_200_000),
]


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name, timestamp=datetime.now(timezone.utc))


@app.get(f"{settings.api_prefix}/projects", response_model=list[Project], tags=["projects"])
async def list_projects() -> list[Project]:
    return _projects


@app.post(f"{settings.api_prefix}/projects", response_model=Project, status_code=201, tags=["projects"])
async def create_project(payload: ProjectCreate) -> Project:
    project = Project(
        id=f"project-{len(_projects) + 1}", name=payload.name, location=payload.location,
        progress=0, health=ProjectStatus.on_track, stage="Planning", due_date="TBD",
        budget_usd=payload.budget_usd,
    )
    _projects.append(project)
    return project


@app.post(f"{settings.api_prefix}/assistant/ask", response_model=AssistantResponse, tags=["assistant"])
async def ask_assistant(payload: AssistantRequest) -> AssistantResponse:
    project_context = f" for {payload.project_name}" if payload.project_name else ""
    answer = (
        f"I’ve noted your question{project_context}: {payload.question} "
        "Connect an AI provider to get an answer grounded in your project documents, site imagery, "
        "schedule, and current conditions. For now, verify recommendations against approved plans "
        "and your site safety lead."
    )
    return AssistantResponse(answer=answer, confidence=0.35)


@app.post(f"{settings.api_prefix}/images/analyze", response_model=ImageAnalysisResponse, tags=["images"])
async def receive_image(file: UploadFile = File(...)) -> ImageAnalysisResponse:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Upload must be an image.")
    contents = await file.read(12 * 1024 * 1024 + 1)
    if len(contents) > 12 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be 12 MB or smaller.")
    if not contents:
        raise HTTPException(status_code=400, detail="Image file is empty.")
    return ImageAnalysisResponse(
        filename=file.filename or "upload",
        content_type=file.content_type,
        bytes_received=len(contents),
        message="Image received. Configure a vision model to enable site safety and defect analysis.",
    )


frontend_dist = Path(__file__).resolve().parents[2] / "dist"
if frontend_dist.is_dir():
    assets = frontend_dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="frontend-assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def frontend(path: str) -> FileResponse:
        candidate = (frontend_dist / path).resolve()
        if candidate.is_relative_to(frontend_dist.resolve()) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(frontend_dist / "index.html")
