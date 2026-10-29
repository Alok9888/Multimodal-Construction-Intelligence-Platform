from __future__ import annotations

import base64
import json
from openai import AsyncOpenAI
from .schemas import (AnalysisRequest, DailyAssistance, DailyAssistanceRequest,
                      PlanEstimate, SiteAnalysis, Valuation, ValuationRequest)
from .settings import settings

client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None


def _mock_analysis(data: AnalysisRequest, has_image: bool) -> SiteAnalysis:
    # Deliberately conservative: the demo does not claim that a site is safe.
    limitations = ["Demo mode uses a rules-based placeholder, not image understanding.",
                   "Have a qualified site professional verify all observations."]
    if not has_image:
        limitations.insert(0, "No image was supplied; visual findings cannot be assessed.")
    return SiteAnalysis(summary="Demo assessment only. Provide a configured AI provider for site-specific analysis.",
        image_quality="insufficient" if not has_image else "limited", findings=[], limitations=limitations)


async def analyze(data: AnalysisRequest, image: bytes | None, mime_type: str) -> SiteAnalysis:
    if settings.ai_mode == "mock" or client is None:
        return _mock_analysis(data, image is not None)
    prompt = ("Analyze the provided construction-site information. Identify visible hazards, PPE issues, "
      "and visible cracks only. Classify each finding as safety_hazard, ppe, crack, or other; give severity, "
      "confidence, likely causes, and practical corrective actions. "
      "Never certify structural safety. If the image is missing, blurry, or insufficient, state that and "
      "do not infer unseen conditions. Return the requested schema. Project: " + data.project.model_dump_json() +
      " Description: " + data.description)
    content: list[dict] = [{"type": "text", "text": prompt}]
    if image:
        encoded = base64.b64encode(image).decode("ascii")
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}})
    response = await client.beta.chat.completions.parse(model=settings.openai_model,
      messages=[{"role": "user", "content": content}], response_format=SiteAnalysis)
    result = response.choices[0].message.parsed
    if not result:
        raise ValueError("AI provider returned an empty response")
    return result


async def estimate(data: AnalysisRequest) -> PlanEstimate:
    p = data.project
    if settings.ai_mode != "mock" and client:
        prompt = ("Create a rough early-stage construction materials, cost, task schedule, and architectural "
          "visualization prompt from these project details. Make assumptions explicit; estimates are not bids. "
          "Return the requested schema. Project: " + p.model_dump_json() + " Notes: " + data.description)
        response = await client.beta.chat.completions.parse(model=settings.openai_model,
          messages=[{"role": "user", "content": prompt}], response_format=PlanEstimate)
        result = response.choices[0].message.parsed
        if not result:
            raise ValueError("AI provider returned an empty response")
        return result
    area = p.area_sqft
    cost = round(area * 145, 2)
    return PlanEstimate(assumptions=["Illustrative demo rates only; location, design, finishes, and site conditions are not priced."],
      materials=[{"name":"Concrete (allowance)","quantity":round(area*0.08,1),"unit":"cubic yd","estimated_cost":round(cost*.22,2)},
        {"name":"Structural framing (allowance)","quantity":round(area*1.4,1),"unit":"sq ft","estimated_cost":round(cost*.3,2)},
        {"name":"Finishes and services (allowance)","quantity":area,"unit":"sq ft","estimated_cost":round(cost*.48,2)}],
      total_estimated_cost=cost, currency=p.currency.upper(),
      schedule=[{"name":"Design and permits","duration_days":30},{"name":"Site preparation and foundation","duration_days":25,"depends_on":["Design and permits"]},
        {"name":"Structure and enclosure","duration_days":60,"depends_on":["Site preparation and foundation"]},
        {"name":"Services and finishes","duration_days":50,"depends_on":["Structure and enclosure"]}],
      visualization_prompt=f"Architectural concept visualization of a {p.floors}-floor {p.project_type} building, approximately {area:g} sq ft, contextualized for {p.location or 'the project site'}.")


async def value(data: ValuationRequest) -> Valuation:
    # Derive a transparent area-based indication only from supplied comparable sales.
    if not data.comparable_sales:
        return Valuation(estimated_value=0, currency=data.project.currency.upper(), confidence="low",
          assumptions=["No local comparable-sale data or verified property condition was supplied.",
            "A numeric market value requires current location-specific evidence."],
          factors=["Location", "Comparable sales", "Condition", "Permitted area", "Market date"])
    valid = [sale for sale in data.comparable_sales if sale.area_sqft > 0]
    rates = [sale.sale_price / sale.area_sqft for sale in valid]
    indication = round(sum(rates) / len(rates) * data.project.area_sqft, 2)
    return Valuation(estimated_value=indication, currency=data.project.currency.upper(),
      confidence="medium" if len(valid) >= 3 else "low",
      assumptions=["Indication applies the simple mean of supplied comparable sale price per sq ft to the subject area.",
        "No adjustments were made for condition, date, location differences, tenure, or permitted area."],
      factors=[f"{len(valid)} user-supplied comparable sale(s)", "Subject area", "Location: " + (data.project.location or "not supplied")])


async def daily_assistance(data: DailyAssistanceRequest) -> DailyAssistance:
    weather = data.weather
    has_weather = bool(weather.condition or weather.temperature_c is not None or weather.wind_kph is not None
                       or weather.precipitation_mm is not None)
    if settings.ai_mode != "mock" and client:
        prompt = ("Generate a daily construction site work and safety advisory from the supplied project and "
          "weather context. If weather measurements are absent, say so and give only general checks. Do not "
          "claim a live forecast. Avoid legal or engineering certification. Return the requested schema. Project: "
          + data.project.model_dump_json() + " Weather: " + weather.model_dump_json() + " Notes: " + data.description)
        response = await client.beta.chat.completions.parse(model=settings.openai_model,
          messages=[{"role": "user", "content": prompt}], response_format=DailyAssistance)
        result = response.choices[0].message.parsed
        if not result:
            raise ValueError("AI provider returned an empty response")
        return result
    if not has_weather:
        return DailyAssistance(weather_summary="Weather observations were not provided.",
          work_recommendation="Check a local, current forecast before scheduling weather-sensitive work.",
          safety_checks=["Run the daily toolbox talk and site walk.", "Confirm PPE and access controls.",
                         "Reassess lifting, work-at-height, and excavation conditions."],
          weather_source="No weather source connected; no live forecast was requested.",
          limitations=["Demo mode does not retrieve live weather or analyze current site conditions."])
    return DailyAssistance(weather_summary=f"Provided conditions: {weather.condition or 'unspecified'}; "
      f"{weather.temperature_c if weather.temperature_c is not None else 'temperature unavailable'} °C; "
      f"wind {weather.wind_kph if weather.wind_kph is not None else 'unavailable'} km/h; "
      f"precipitation {weather.precipitation_mm if weather.precipitation_mm is not None else 'unavailable'} mm.",
      work_recommendation="Review these observations with the site supervisor and pause exposed or weather-sensitive tasks if conditions exceed the site plan limits.",
      safety_checks=["Confirm footing, access routes, and temporary works after rain.",
                     "Secure loose materials and reassess lifting in high winds.",
                     "Adjust heat, cold, and hydration controls to measured conditions."],
      weather_source="User-supplied weather observations; not independently verified.",
      limitations=["This is not a live forecast or a substitute for the approved site safety plan."])
