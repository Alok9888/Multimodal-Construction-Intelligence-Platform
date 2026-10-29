from __future__ import annotations

import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from .schemas import AnalysisRequest, DailyAssistanceRequest, Health, ValuationRequest
from .services import analyze, daily_assistance, estimate, value
from .settings import settings
from .storage import get_record, initialize_storage, list_records, save_record

@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.ai_mode == "live" and not settings.openai_api_key:
        raise RuntimeError("AI_MODE=live requires OPENAI_API_KEY")
    initialize_storage()
    yield

app = FastAPI(title="BuildSight API", version="0.2.0", description="Multimodal construction intelligence platform", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_credentials=False,
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}

@app.get("/api/health", response_model=Health)
async def health():
    return Health(status="ok", ai_mode=settings.ai_mode, model=settings.openai_model, storage="sqlite+files")

def parse_request(raw: str) -> AnalysisRequest:
    try:
        return AnalysisRequest.model_validate_json(raw)
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid project information") from exc

async def read_image(image: UploadFile | None) -> tuple[bytes | None, str]:
    if image is None:
        return None, "image/jpeg"
    if image.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Use a JPEG, PNG, or WebP image")
    content = await image.read(MAX_IMAGE_BYTES + 1)
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be 10 MB or smaller")
    if not content:
        raise HTTPException(status_code=422, detail="Image file is empty")
    return content, image.content_type

@app.post("/api/analyze")
async def analyze_site(project: str = Form("{}"), description: str = Form(""), image: UploadFile | None = File(None)):
    try:
        data = AnalysisRequest(description=description, project=json.loads(project))
    except (ValidationError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail="Invalid project information") from exc
    image_bytes, mime = await read_image(image)
    try:
        result = await analyze(data, image_bytes, mime)
        record_id = save_record("site_analysis", result.model_dump(), image_bytes, mime if image_bytes else None)
        return {**result.model_dump(), "record_id": record_id}
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Analysis provider failed; check server configuration") from exc

@app.post("/api/estimate")
async def create_estimate(request: AnalysisRequest):
    try:
        result = await estimate(request)
        record_id = save_record("project_plan", result.model_dump())
        return {**result.model_dump(), "record_id": record_id}
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Planning provider failed; check server configuration") from exc

@app.post("/api/valuation")
async def create_valuation(request: ValuationRequest):
    result = await value(request)
    record_id = save_record("property_valuation", result.model_dump())
    return {**result.model_dump(), "record_id": record_id}

@app.post("/api/daily-assistance")
async def create_daily_assistance(request: DailyAssistanceRequest):
    try:
        result = await daily_assistance(request)
        record_id = save_record("daily_assistance", result.model_dump())
        return {**result.model_dump(), "record_id": record_id}
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Daily advisory provider failed; check server configuration") from exc

@app.get("/api/records")
async def records(limit: int = 20):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    return list_records(limit)

@app.get("/api/records/{record_id}")
async def record(record_id: str):
    result = get_record(record_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return result
