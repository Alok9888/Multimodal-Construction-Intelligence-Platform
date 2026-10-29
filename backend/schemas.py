from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class ProjectInfo(BaseModel):
    project_type: str = Field(default="residential", max_length=80)
    area_sqft: float = Field(default=1200, gt=0, le=1_000_000)
    location: str = Field(default="", max_length=200)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    floors: int = Field(default=1, ge=1, le=200)
    notes: str = Field(default="", max_length=3000)


class AnalysisRequest(BaseModel):
    description: str = Field(default="", max_length=5000)
    project: ProjectInfo = Field(default_factory=ProjectInfo)


class Finding(BaseModel):
    category: Literal["safety_hazard", "ppe", "crack", "other"]
    title: str
    severity: Literal["low", "medium", "high", "critical"]
    confidence: float = Field(ge=0, le=1)
    probable_cause: str
    recommended_action: str


class SiteAnalysis(BaseModel):
    summary: str
    image_quality: Literal["usable", "limited", "insufficient"]
    findings: list[Finding]
    limitations: list[str]


class Material(BaseModel):
    name: str
    quantity: float
    unit: str
    estimated_cost: float


class Task(BaseModel):
    name: str
    duration_days: int = Field(ge=1)
    depends_on: list[str] = Field(default_factory=list)


class PlanEstimate(BaseModel):
    assumptions: list[str]
    materials: list[Material]
    total_estimated_cost: float
    currency: str
    schedule: list[Task]
    visualization_prompt: str


class Valuation(BaseModel):
    estimated_value: float
    currency: str
    confidence: Literal["low", "medium", "high"]
    assumptions: list[str]
    factors: list[str]


class ComparableSale(BaseModel):
    address: str = Field(max_length=200)
    sale_price: float = Field(gt=0)
    area_sqft: float = Field(gt=0)
    sale_date: str = Field(max_length=40)


class ValuationRequest(AnalysisRequest):
    comparable_sales: list[ComparableSale] = Field(default_factory=list, max_length=30)


class WeatherContext(BaseModel):
    condition: str = Field(default="", max_length=100)
    temperature_c: float | None = Field(default=None, ge=-80, le=65)
    wind_kph: float | None = Field(default=None, ge=0, le=400)
    precipitation_mm: float | None = Field(default=None, ge=0, le=1000)
    observed_at: str = Field(default="", max_length=40)


class DailyAssistanceRequest(AnalysisRequest):
    weather: WeatherContext = Field(default_factory=WeatherContext)


class DailyAssistance(BaseModel):
    weather_summary: str
    work_recommendation: str
    safety_checks: list[str]
    weather_source: str
    limitations: list[str]


class StoredRecord(BaseModel):
    id: str
    kind: str
    created_at: str
    result: dict
    image_available: bool


class Health(BaseModel):
    status: str
    ai_mode: str
    model: str
    storage: str
