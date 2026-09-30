"""
AazhiNav AI — FastAPI Backend
Voyage risk prediction server using rule-based engine from fishersafe_engine.py
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import math

# ─────────────────────────────────────────────────────────────
#  Import rule-based functions from fishersafe_engine
#  (only the ones that work without ML model files)
# ─────────────────────────────────────────────────────────────
from fishersafe_engine import (
    calculate_boat_vulnerability,
    calculate_final_risk,
    generate_recommendation,
    find_safer_departure_windows,
    fishersafe_predict,
)

# ─────────────────────────────────────────────────────────────
#  App
# ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="AazhiNav AI — Voyage Risk API",
    description="Rule-based voyage risk prediction engine for fishermen.",
    version="1.0.0",
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Fallback exception handler for unhandled internal errors."""
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred.", "error": str(exc)},
    )

# ─────────────────────────────────────────────────────────────
#  CORS — allow the Vite dev server to call this API
# ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
#  Request / Response Schemas
# ─────────────────────────────────────────────────────────────
class PredictRequest(BaseModel):
    # Voyage details (from user form)
    boat_type: str = Field(default="Small", description="Small, Medium, or Large")
    distance_km: Optional[float] = Field(default=None, ge=0, description="Distance from shore in km")
    departure_time: Optional[str] = Field(default=None, description="HH:MM")
    return_time: Optional[str] = Field(default=None, description="HH:MM")
    crew_size: Optional[int] = Field(default=None, ge=1, description="Number of crew members")

    # Live weather data (fetched by frontend from Open-Meteo)
    wind_speed: Optional[float] = Field(default=None, ge=0, description="Wind speed in km/h")
    wave_height: Optional[float] = Field(default=None, ge=0, description="Wave height in metres")
    temperature: Optional[float] = Field(default=None, description="Temperature in Celsius")

    # GPS (from browser geolocation)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


class RiskFactor(BaseModel):
    name: str
    value: str
    points: int


class PredictResponse(BaseModel):
    # High-level summary
    risk_score: int
    risk_level: str          # "SAFE" | "MODERATE" | "HIGH RISK"
    safety_status: str       # "Safe" | "Unsafe"

    # Sub-risk breakdown
    boat_vulnerability_score: float
    boat_risk: str
    sea_risk: str
    ocean_risk: str
    cyclone_risk: str
    final_risk: str          # "Low" | "Moderate" | "High"

    # Detailed analysis
    risk_factors: list[RiskFactor]
    warnings: list[str]
    recommendation: str
    recommended_time: str
    boat_reasons: list[str]


# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────

def _parse_time_to_minutes(time_str: Optional[str]) -> Optional[int]:
    """Convert 'HH:MM' string to total minutes since midnight."""
    if not time_str:
        return None
    try:
        parts = time_str.split(":")
        if len(parts) != 2:
            return None
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, AttributeError):
        return None


def _calculate_duration_minutes(
    departure_time: Optional[str],
    return_time: Optional[str],
) -> int:
    """Return trip duration in minutes (handles overnight trips)."""
    dep = _parse_time_to_minutes(departure_time)
    ret = _parse_time_to_minutes(return_time)
    if dep is None or ret is None:
        return 0
    if ret < dep:
        ret += 1440  # overnight trip
    return ret - dep


def _map_boat_type_to_length(boat_type: str) -> float:
    """Map frontend boat type string to an approximate length in feet."""
    mapping = {
        "Small": 22.0,
        "Medium": 35.0,
        "Large": 50.0,
    }
    return mapping.get(boat_type, 22.0)


def _map_boat_type_to_engine_hp(boat_type: str) -> float:
    """Map frontend boat type to approximate engine HP."""
    mapping = {
        "Small": 25.0,
        "Medium": 75.0,
        "Large": 150.0,
    }
    return mapping.get(boat_type, 25.0)





# ─────────────────────────────────────────────────────────────
#  Risk score builder (mirrors the frontend calculateRisk logic)
# ─────────────────────────────────────────────────────────────

def _build_risk_score_and_factors(
    req: PredictRequest,
    duration_minutes: int,
) -> tuple[int, list[dict], list[str]]:
    """
    Replicate the frontend's point-based scoring so the API
    returns the same familiar 0-100 score that the UI already
    displays. Returns (score, risk_factors, warnings).
    """
    factors: list[dict] = []
    warnings: list[str] = []
    total = 0

    # ── Distance ─────────────────────────────────────────────
    d = req.distance_km
    if d is not None:
        if d > 50:
            pts = 30
            factors.append({"name": "Distance", "value": "Very High", "points": pts})
            warnings.append("Voyage distance is very far from shore.")
        elif d > 30:
            pts = 20
            factors.append({"name": "Distance", "value": "High", "points": pts})
            warnings.append("Long-distance voyage increases exposure.")
        elif d > 15:
            pts = 10
            factors.append({"name": "Distance", "value": "Moderate", "points": pts})
            warnings.append("Distance from shore is within a moderate range.")
        else:
            pts = 3
            factors.append({"name": "Distance", "value": "Low", "points": pts})
            warnings.append("Distance from shore is within a lower-risk range.")
        total += pts
    else:
        factors.append({"name": "Distance", "value": "Not provided", "points": 0})
        warnings.append("Enter the planned distance from shore.")

    # ── Boat type ─────────────────────────────────────────────
    boat_map = {"Small": (15, "Small boat selected. Extra caution is recommended in rough conditions."),
                "Medium": (8, "Medium boat selected."),
                "Large": (3, "Large boat provides greater stability.")}
    pts, msg = boat_map.get(req.boat_type, (15, "Small boat selected."))
    factors.append({"name": "Boat Type", "value": req.boat_type, "points": pts})
    warnings.append(msg)
    total += pts

    # ── Wind ─────────────────────────────────────────────────
    w = req.wind_speed
    if w is None:
        factors.append({"name": "Wind", "value": "Unavailable", "points": 0})
        warnings.append("Live wind data is currently unavailable.")
    elif w > 40:
        pts = 30
        factors.append({"name": "Wind", "value": "Dangerous", "points": pts})
        warnings.append("Dangerous wind conditions detected.")
        total += pts
    elif w > 30:
        pts = 22
        factors.append({"name": "Wind", "value": "High", "points": pts})
        warnings.append("High wind conditions detected.")
        total += pts
    elif w > 20:
        pts = 12
        factors.append({"name": "Wind", "value": "Moderate", "points": pts})
        warnings.append("Moderate wind conditions detected.")
        total += pts
    else:
        pts = 3
        factors.append({"name": "Wind", "value": "Low", "points": pts})
        warnings.append("Wind conditions are currently low.")
        total += pts

    # ── Waves ─────────────────────────────────────────────────
    wv = req.wave_height
    if wv is None:
        factors.append({"name": "Wave Height", "value": "Unavailable", "points": 0})
        warnings.append("Marine wave data is unavailable at the current location.")
    elif wv > 3:
        pts = 25
        factors.append({"name": "Wave Height", "value": "Dangerous", "points": pts})
        warnings.append("Dangerous wave height detected.")
        total += pts
    elif wv > 2:
        pts = 18
        factors.append({"name": "Wave Height", "value": "High", "points": pts})
        warnings.append("High wave height detected.")
        total += pts
    elif wv > 1:
        pts = 10
        factors.append({"name": "Wave Height", "value": "Moderate", "points": pts})
        warnings.append("Moderate wave conditions detected.")
        total += pts
    else:
        pts = 3
        factors.append({"name": "Wave Height", "value": "Low", "points": pts})
        warnings.append("Wave height is currently low.")
        total += pts

    # ── Crew ─────────────────────────────────────────────────
    c = req.crew_size
    if c is None:
        factors.append({"name": "Crew Size", "value": "Not provided", "points": 0})
        warnings.append("Enter the number of crew members.")
    elif c <= 1:
        pts = 15
        factors.append({"name": "Crew Size", "value": "Very Small", "points": pts})
        warnings.append("Very small crew size detected.")
        total += pts
    elif c <= 3:
        pts = 8
        factors.append({"name": "Crew Size", "value": "Small", "points": pts})
        warnings.append("Crew size is relatively small.")
        total += pts
    else:
        pts = 2
        factors.append({"name": "Crew Size", "value": "Adequate", "points": pts})
        warnings.append("Crew size provides better support.")
        total += pts

    # ── Duration ─────────────────────────────────────────────
    if duration_minutes > 720:
        pts = 15
        factors.append({"name": "Voyage Duration", "value": "Very Long", "points": pts})
        warnings.append("Very long voyage duration detected.")
        total += pts
    elif duration_minutes > 480:
        pts = 10
        factors.append({"name": "Voyage Duration", "value": "Long", "points": pts})
        warnings.append("Long voyage duration detected.")
        total += pts
    elif duration_minutes > 240:
        pts = 5
        factors.append({"name": "Voyage Duration", "value": "Moderate", "points": pts})
        warnings.append("Moderate voyage duration.")
        total += pts
    elif duration_minutes > 0:
        hrs = duration_minutes // 60
        mins = duration_minutes % 60
        pts = 2
        factors.append({"name": "Voyage Duration", "value": f"{hrs}h {mins}m", "points": pts})
        warnings.append("Voyage duration is within a shorter range.")
        total += pts
    else:
        factors.append({"name": "Voyage Duration", "value": "Not provided", "points": 0})

    # ── Departure time (night penalty) ────────────────────────
    if req.departure_time:
        try:
            hour = int(req.departure_time.split(":")[0])
            if hour >= 20 or hour < 5:
                pts = 10
                factors.append({"name": "Departure", "value": "Night", "points": pts})
                warnings.append("Night departure detected. Visibility may be reduced.")
                total += pts
            else:
                pts = 2
                factors.append({"name": "Departure", "value": "Daytime", "points": pts})
                warnings.append("Daytime departure provides better visibility.")
                total += pts
        except (ValueError, IndexError):
            pass

    # ── Temperature ───────────────────────────────────────────
    t = req.temperature
    if t is not None:
        if t > 38:
            total += 5
            warnings.append("High temperature detected. Carry sufficient drinking water.")
        elif t < 18:
            total += 3
            warnings.append("Low temperature detected. Dress appropriately.")

    # ── Missing input penalty ─────────────────────────────────
    missing = []
    if req.distance_km is None:
        missing.append("distance from shore")
    if req.crew_size is None:
        missing.append("crew size")
    if not req.departure_time:
        missing.append("departure time")
    if not req.return_time:
        missing.append("expected return time")

    if missing:
        total = max(total, 20)
        warnings.insert(0, f"Complete the following voyage details: {', '.join(missing)}.")

    score = max(0, min(100, round(total)))
    return score, factors, warnings


# ─────────────────────────────────────────────────────────────
#  Endpoints
# ─────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "AazhiNav AI — Voyage Risk API"}


@app.post("/api/predict", response_model=PredictResponse, tags=["Prediction"])
def predict(req: PredictRequest):
    """
    Main voyage risk prediction endpoint.

    Accepts voyage details + live weather data from the frontend,
    runs rule-based risk analysis using fishersafe_engine functions,
    and returns a structured risk report.
    """

    # ── Duration ─────────────────────────────────────────────
    duration_minutes = _calculate_duration_minutes(req.departure_time, req.return_time)
    trip_hours = duration_minutes / 60 if duration_minutes > 0 else 4.0

    # ── Boat parameters ───────────────────────────────────────
    boat_length = _map_boat_type_to_length(req.boat_type)
    engine_hp = _map_boat_type_to_engine_hp(req.boat_type)
    distance_km = req.distance_km if req.distance_km is not None else 10.0
    crew_size = req.crew_size if req.crew_size is not None else 2

    # ── Stage 2: ML Environment Risks (fishersafe_engine) ──────
    # Using real inputs where possible, dummy values for missing advanced features
    try:
        hour = int(req.departure_time.split(":")[0]) if req.departure_time else 6
    except:
        hour = 6

    # Real inputs
    wind_speed_ms = (req.wind_speed or 15) * 0.277778  # Convert km/h to m/s
    air_temp = req.temperature or 30.0
    sigheight = req.wave_height or 1.0
    
    # Dummy inputs for missing features
    water_temp = air_temp - 1
    pressure = 1013.25
    dewpoint = air_temp - 2
    humidity = 80
    precipitation = 0.0
    cloud_cover = 50
    wind_direction = 180
    wave_direction = 180
    dominant_period = 8
    average_period = 6

    ml_results = fishersafe_predict(
        ocean_windspeed=wind_speed_ms,
        ocean_windgust=wind_speed_ms * 1.3,
        dominant_period=dominant_period,
        average_period=average_period,
        ocean_pressure=pressure,
        air_temp=air_temp,
        water_temp=water_temp,
        ocean_dewpoint=dewpoint,
        ocean_wind_direction=wind_direction,
        wave_direction=wave_direction,
        precipitation=precipitation,
        humidity=humidity,
        cloud_cover=cloud_cover,
        sea_wind_spot_difference=0,
        sigheight=sigheight,
        swellheight=sigheight * 0.8,
        sea_period=average_period,
        swell_direction=wave_direction,
        swell_spot_difference=0,
        day_of_week=1,
        idbeach=1,
        lat=req.latitude or 13.0,
        lon=req.longitude or 80.0,
        distance_to_land=distance_km,
        landfall=0,
        storm_speed=15,
        storm_direction=180,
        boat_length_ft=boat_length,
        engine_hp=engine_hp,
        distance_km=distance_km,
        trip_hours=trip_hours,
        crew_size=crew_size,
        year=2024,
        month=6,
        hour=hour,
        day_of_year=180
    )

    boat_score = ml_results["boat_vulnerability_score"]
    boat_risk = ml_results["boat_risk"]
    boat_reasons = ml_results["boat_reasons"]
    sea_risk = ml_results["sea_risk"]
    ocean_risk = ml_results["ocean_risk"]
    cyclone_risk = ml_results["cyclone_risk"]
    final_risk = ml_results["final_risk"]
    safety_status = ml_results["safety_status"]

    # ── Stage 4: Point-based score + factors ──────────────────
    risk_score, risk_factors, warnings = _build_risk_score_and_factors(
        req, duration_minutes
    )

    # ── Stage 5: Risk level label ─────────────────────────────
    if risk_score >= 70:
        risk_level = "HIGH RISK"
        recommendation = (
            "Departure is not recommended under the current assessed conditions. "
            "Consider delaying the voyage and checking for a safer departure window."
        )
        recommended_time = "Delay recommended"
    elif risk_score >= 40:
        risk_level = "MODERATE"
        recommendation = (
            "Use caution before departure. "
            "Recheck marine conditions and consider delaying if conditions worsen."
        )
        recommended_time = "06:00"
    else:
        risk_level = "SAFE"
        recommendation = (
            "Conditions appear relatively favorable. "
            "Proceed with normal safety precautions and continue monitoring updates."
        )
        recommended_time = req.departure_time or "06:00"

    # ── Override with fishersafe engine's final_risk if stricter ──
    # Escalate risk_level upward if the engine fusion says it's worse
    engine_level_map = {"Low": 0, "Moderate": 1, "High": 2}
    ui_level_map = {"SAFE": 0, "MODERATE": 1, "HIGH RISK": 2}
    reverse_map = {0: "SAFE", 1: "MODERATE", 2: "HIGH RISK"}

    engine_num = engine_level_map.get(final_risk, 0)
    ui_num = ui_level_map.get(risk_level, 0)
    effective_num = max(engine_num, ui_num)
    risk_level = reverse_map[effective_num]

    if effective_num == 2:
        recommendation = (
            "Departure is not recommended under the current assessed conditions. "
            "Consider delaying the voyage and checking for a safer departure window."
        )
        recommended_time = "Delay recommended"
    elif effective_num == 1 and ui_num < 1:
        recommendation = (
            "Use caution before departure. "
            "Recheck marine conditions and consider delaying if conditions worsen."
        )
        recommended_time = "06:00"

    return PredictResponse(
        risk_score=risk_score,
        risk_level=risk_level,
        safety_status=safety_status,
        boat_vulnerability_score=round(boat_score, 2),
        boat_risk=boat_risk,
        sea_risk=sea_risk,
        ocean_risk=ocean_risk,
        cyclone_risk=cyclone_risk,
        final_risk=final_risk,
        risk_factors=[RiskFactor(**f) for f in risk_factors],
        warnings=warnings,
        recommendation=recommendation,
        recommended_time=recommended_time,
        boat_reasons=boat_reasons,
    )
