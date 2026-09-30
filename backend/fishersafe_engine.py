import numpy as np
import pandas as pd
import joblib
import os
import warnings
warnings.filterwarnings('ignore') # Ignore sklearn version warnings for now

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ML_DIR = os.path.join(os.path.dirname(BASE_DIR), "ml")

def _load_model_safe(filename):
    try:
        return joblib.load(os.path.join(ML_DIR, filename))
    except Exception as e:
        print(f"Warning: Failed to load {filename}: {e}")
        return None

ocean_model = _load_model_safe("ocenography final.pkl")
cyclone_model = _load_model_safe("final cyclone file.pkl")
sea_pipeline = _load_model_safe("seaforecast final.pkl")

RISK_TO_NUMBER = {"Low":0, "Moderate":1, "High":2}
NUMBER_TO_RISK = {0:"Low", 1:"Moderate", 2:"High"}

def risk_to_number(risk):
    return RISK_TO_NUMBER[risk]


def number_to_risk(value):
    return NUMBER_TO_RISK[value]


def ocean_wave_to_risk(wave_height):

    if wave_height < 1.0:
        return "Low"

    elif wave_height < 2.0:
        return "Moderate"

    else:
        return "High"


def standardize_sea_risk(prediction):

    prediction = str(prediction)

    if prediction in ["Low", "Moderate", "High"]:
        return prediction

    else:
        raise ValueError(
            "Unknown Sea Forecast prediction: " + prediction
        )


def standardize_cyclone_risk(prediction):

    cyclone_mapping = {
        0: "Low",
        1: "Moderate",
        2: "High"
    }

    prediction = int(prediction)

    return cyclone_mapping[prediction]


def calculate_boat_vulnerability(
    boat_length_ft,
    engine_hp,
    distance_km,
    trip_hours,
    crew_size
):
    score = 0
    reasons = []

    # Boat length
    if boat_length_ft != -1:
        if boat_length_ft < 28:
            score += 15
            reasons.append("Smaller boat size")
        elif boat_length_ft < 40:
            score += 10
        else:
            score += 5
    else:
        score += 10

    # Engine power
    if engine_hp < 34:
        score += 15
        reasons.append("Low engine power")
    elif engine_hp < 119:
        score += 10
    else:
        score += 5

    # Distance from shore
    if distance_km > 70:
        score += 25
        reasons.append("Long distance from shore")
    elif distance_km > 34:
        score += 15
    else:
        score += 5

    # Trip duration
    if trip_hours > 14:
        score += 25
        reasons.append("Long trip duration")
    elif trip_hours > 8:
        score += 15
    else:
        score += 5

    # Crew size
    if crew_size <= 3:
        score += 10
        reasons.append("Small crew size")
    elif crew_size <= 5:
        score += 5

    # Convert to percentage
    vulnerability_score = round((score / 90) * 100, 2)

    if vulnerability_score < 35:
        level = "Low"
    elif vulnerability_score < 65:
        level = "Moderate"
    else:
        level = "High"

    return vulnerability_score, level, reasons


def calculate_final_risk(
    sea_risk,
    ocean_risk,
    cyclone_risk,
    boat_risk
):

    risks = {
        "Sea Forecast": risk_to_number(sea_risk),
        "Oceanography": risk_to_number(ocean_risk),
        "Cyclone": risk_to_number(cyclone_risk),
        "Boat/Trip": risk_to_number(boat_risk)
    }

    # Environmental risks
    environmental_values = [
        risks["Sea Forecast"],
        risks["Oceanography"],
        risks["Cyclone"]
    ]

    # Safety-first rule:
    # Any HIGH environmental risk makes final risk HIGH
    if 2 in environmental_values:
        final_risk = "High"

    # Two or more MODERATE environmental risks
    elif environmental_values.count(1) >= 2:
        final_risk = "Moderate"

    # One MODERATE environmental risk
    elif 1 in environmental_values:
        final_risk = "Moderate"

    # Environment is LOW, but boat/trip vulnerability is HIGH
    elif risks["Boat/Trip"] == 2:
        final_risk = "Moderate"

    else:
        final_risk = "Low"

    # Boat vulnerability can increase Moderate environmental risk to High
    if final_risk == "Moderate" and risks["Boat/Trip"] == 2:
        final_risk = "High"

    # Safe / Unsafe indication
    if final_risk == "Low":
        safety_status = "Safe"
    else:
        safety_status = "Unsafe"

    return final_risk, safety_status, risks


def predict_oceanography_risk(
    windspeed,
    windgust,
    dominant_period,
    average_period,
    pressure,
    air_temp,
    water_temp,
    dewpoint,
    wind_direction,
    wave_direction,
    hour,
    month,
    day_of_year
):

    # Convert angles to sin/cos
    wind_rad = np.radians(wind_direction)
    wave_rad = np.radians(wave_direction)

    # Time cyclic features
    hour_rad = 2 * np.pi * hour / 24
    month_rad = 2 * np.pi * month / 12
    day_rad = 2 * np.pi * day_of_year / 365

    # Derived features
    gust_difference = windgust - windspeed
    air_water_temp_difference = air_temp - water_temp
    air_dewpoint_difference = air_temp - dewpoint
    period_difference = dominant_period - average_period

    input_data = pd.DataFrame([{
        'WSPD(m/s)': windspeed,
        'GST(m/s)': windgust,
        'DPD(sec)': dominant_period,
        'APD(sec)': average_period,
        'PRES(hPa)': pressure,
        'ATMP(degC)': air_temp,
        'WTMP(degC)': water_temp,
        'DEWP(degC)': dewpoint,

        'wind_direction_sin': np.sin(wind_rad),
        'wind_direction_cos': np.cos(wind_rad),

        'wave_direction_sin': np.sin(wave_rad),
        'wave_direction_cos': np.cos(wave_rad),

        'hour_sin': np.sin(hour_rad),
        'hour_cos': np.cos(hour_rad),

        'month_sin': np.sin(month_rad),
        'month_cos': np.cos(month_rad),

        'day_of_year_sin': np.sin(day_rad),
        'day_of_year_cos': np.cos(day_rad),

        'gust_difference': gust_difference,
        'air_water_temp_difference': air_water_temp_difference,
        'air_dewpoint_difference': air_dewpoint_difference,
        'period_difference': period_difference
    }])

    # Predict wave height — fall back to rule if model unavailable/corrupt
    if ocean_model is not None:
        try:
            predicted_wave_height = float(ocean_model.predict(input_data)[0])
        except Exception:
            predicted_wave_height = windspeed * 0.05 + dominant_period * 0.1
    else:
        predicted_wave_height = windspeed * 0.05 + dominant_period * 0.1

    # Convert wave height to risk
    risk = ocean_wave_to_risk(predicted_wave_height)

    return round(predicted_wave_height, 2), risk


def predict_cyclone_risk(
    lat,
    lon,
    distance_to_land,
    landfall,
    storm_speed,
    storm_direction,
    year,
    month,
    hour
):

    input_data = pd.DataFrame([{
        'LAT': lat,
        'LON': lon,
        'DIST2LAND': distance_to_land,
        'LANDFALL': landfall,
        'STORM_SPEED': storm_speed,
        'STORM_DIR': storm_direction,
        'YEAR': year,
        'MONTH': month,
        'HOUR': hour
    }])

    if cyclone_model is not None:
        try:
            prediction = cyclone_model.predict(input_data)[0]
            risk = standardize_cyclone_risk(prediction)
        except Exception:
            risk = "Low"
    else:
        risk = "Low"

    return risk


def predict_sea_risk(
    temperature,
    preciptation,
    humidity,
    pressure,
    cloundover,
    dewpoint,
    windspeed,
    windgust,
    wind_direction,
    wind_spot_difference,
    sigheight,
    swellheight,
    period,
    watertemp,
    swell_direction,
    swell_spot_difference,
    hour,
    month,
    day_of_week,
    idbeach
):

    wind_rad = np.radians(wind_direction)
    swell_rad = np.radians(swell_direction)

    hour_rad = 2 * np.pi * hour / 24
    month_rad = 2 * np.pi * month / 12

    input_data = pd.DataFrame([{
        'temperature': temperature,
        'preciptation': preciptation,
        'humidity': humidity,
        'pressure': pressure,
        'cloundover': cloundover,
        'dewpoint': dewpoint,
        'windspeed': windspeed,
        'windgust': windgust,

        'winddir_sin': np.sin(wind_rad),
        'winddir_cos': np.cos(wind_rad),

        'wind_spot_difference': wind_spot_difference,

        'sigheight': sigheight,
        'swellheight': swellheight,
        'period': period,
        'watertemp': watertemp,

        'swelldir_sin': np.sin(swell_rad),
        'swelldir_cos': np.cos(swell_rad),

        'swell_spot_difference': swell_spot_difference,

        'hour_sin': np.sin(hour_rad),
        'hour_cos': np.cos(hour_rad),

        'month_sin': np.sin(month_rad),
        'month_cos': np.cos(month_rad),

        'day_of_week': day_of_week,
        'idbeach': idbeach
    }])

    if sea_pipeline is not None:
        try:
            prediction = sea_pipeline.predict(input_data)[0]
            risk = standardize_sea_risk(prediction)
        except Exception:
            risk = "Low"
    else:
        risk = "Low"

    return risk


def fishersafe_predict(
    # Oceanography inputs
    ocean_windspeed,
    ocean_windgust,
    dominant_period,
    average_period,
    ocean_pressure,
    air_temp,
    water_temp,
    ocean_dewpoint,
    ocean_wind_direction,
    wave_direction,

    # Sea forecast inputs
    precipitation,
    humidity,
    cloud_cover,
    sea_wind_spot_difference,
    sigheight,
    swellheight,
    sea_period,
    swell_direction,
    swell_spot_difference,
    day_of_week,
    idbeach,

    # Cyclone inputs
    lat,
    lon,
    distance_to_land,
    landfall,
    storm_speed,
    storm_direction,

    # Boat / trip inputs
    boat_length_ft,
    engine_hp,
    distance_km,
    trip_hours,
    crew_size,

    # Common time inputs
    year,
    month,
    hour,
    day_of_year
):

    # 1. Oceanography prediction
    wave_height, ocean_risk = predict_oceanography_risk(
        windspeed=ocean_windspeed,
        windgust=ocean_windgust,
        dominant_period=dominant_period,
        average_period=average_period,
        pressure=ocean_pressure,
        air_temp=air_temp,
        water_temp=water_temp,
        dewpoint=ocean_dewpoint,
        wind_direction=ocean_wind_direction,
        wave_direction=wave_direction,
        hour=hour,
        month=month,
        day_of_year=day_of_year
    )

    # 2. Sea forecast prediction
    sea_risk = predict_sea_risk(
        temperature=air_temp,
        preciptation=precipitation,
        humidity=humidity,
        pressure=ocean_pressure,
        cloundover=cloud_cover,
        dewpoint=ocean_dewpoint,
        windspeed=ocean_windspeed,
        windgust=ocean_windgust,
        wind_direction=ocean_wind_direction,
        wind_spot_difference=sea_wind_spot_difference,
        sigheight=sigheight,
        swellheight=swellheight,
        period=sea_period,
        watertemp=water_temp,
        swell_direction=swell_direction,
        swell_spot_difference=swell_spot_difference,
        hour=hour,
        month=month,
        day_of_week=day_of_week,
        idbeach=idbeach
    )

    # 3. Cyclone prediction
    cyclone_risk = predict_cyclone_risk(
        lat=lat,
        lon=lon,
        distance_to_land=distance_to_land,
        landfall=landfall,
        storm_speed=storm_speed,
        storm_direction=storm_direction,
        year=year,
        month=month,
        hour=hour
    )

    # 4. Boat vulnerability
    boat_score, boat_risk, boat_reasons = calculate_boat_vulnerability(
        boat_length_ft=boat_length_ft,
        engine_hp=engine_hp,
        distance_km=distance_km,
        trip_hours=trip_hours,
        crew_size=crew_size
    )

    # 5. Final fusion
    final_risk, safety_status, individual_risks = calculate_final_risk(
        sea_risk=sea_risk,
        ocean_risk=ocean_risk,
        cyclone_risk=cyclone_risk,
        boat_risk=boat_risk
    )

    return {
        "predicted_wave_height_m": wave_height,
        "sea_risk": sea_risk,
        "ocean_risk": ocean_risk,
        "cyclone_risk": cyclone_risk,
        "boat_vulnerability_score": boat_score,
        "boat_risk": boat_risk,
        "boat_reasons": boat_reasons,
        "final_risk": final_risk,
        "safety_status": safety_status,
        "individual_risks": individual_risks
    }


def generate_recommendation(result):

    final_risk = result["final_risk"]
    safety_status = result["safety_status"]

    reasons = []

    # Environmental reasons
    if result["sea_risk"] == "High":
        reasons.append("High sea-condition risk")
    elif result["sea_risk"] == "Moderate":
        reasons.append("Moderate sea-condition risk")

    if result["ocean_risk"] == "High":
        reasons.append("High predicted wave conditions")
    elif result["ocean_risk"] == "Moderate":
        reasons.append("Moderate predicted wave conditions")

    if result["cyclone_risk"] == "High":
        reasons.append("High cyclone-related risk")
    elif result["cyclone_risk"] == "Moderate":
        reasons.append("Moderate cyclone-related risk")

    # Boat reasons
    reasons.extend(result["boat_reasons"])

    # Recommendation
    if final_risk == "Low":
        recommendation = (
            "Conditions appear relatively favorable. "
            "Proceed with normal safety precautions and continue monitoring updates."
        )

    elif final_risk == "Moderate":
        recommendation = (
            "Use caution before departure. "
            "Recheck marine conditions and consider delaying the trip if conditions worsen."
        )

    else:
        recommendation = (
            "Departure is not recommended under the current assessed conditions. "
            "Consider delaying the voyage and checking for a safer departure window."
        )

    return {
        "final_risk": final_risk,
        "safety_status": safety_status,
        "main_reasons": reasons,
        "recommendation": recommendation
    }


def find_safer_departure_window(forecast_results):

    """
    forecast_results should be a list like:

    [
        {"time": "08:00", "final_risk": "High"},
        {"time": "11:00", "final_risk": "Moderate"},
        {"time": "14:00", "final_risk": "Low"}
    ]
    """

    risk_priority = {
        "Low": 0,
        "Moderate": 1,
        "High": 2
    }

    if not forecast_results:
        return None

    best_slot = min(
        forecast_results,
        key=lambda x: risk_priority[x["final_risk"]]
    )

    return best_slot


def find_safer_departure_windows(forecast_results):

    risk_priority = {
        "Low": 0,
        "Moderate": 1,
        "High": 2
    }

    if not forecast_results:
        return []

    # Find minimum risk value
    minimum_risk = min(
        risk_priority[item["final_risk"]]
        for item in forecast_results
    )

    # Return every slot with that minimum risk
    best_slots = [
        item
        for item in forecast_results
        if risk_priority[item["final_risk"]] == minimum_risk
    ]

    return best_slots


def evaluate_departure_slots(slots):

    evaluated_slots = []

    for slot in slots:

        result = fishersafe_predict(**slot["inputs"])

        evaluated_slots.append({
            "time": slot["time"],
            "final_risk": result["final_risk"],
            "safety_status": result["safety_status"],
            "sea_risk": result["sea_risk"],
            "ocean_risk": result["ocean_risk"],
            "cyclone_risk": result["cyclone_risk"],
            "boat_risk": result["boat_risk"]
        })

    best_slot = find_safer_departure_window(evaluated_slots)

    return evaluated_slots, best_slot


def choose_recommended_window(best_slots):

    if not best_slots:
        return None

    # Since slots are already in time order,
    # choose the earliest safest slot
    return best_slots[0]


def create_final_report(result, recommended_slot):

    report = {
        "Final Voyage Risk": result["final_risk"],
        "Safety Status": result["safety_status"],
        "Predicted Wave Height (m)": result["predicted_wave_height_m"],
        "Sea Forecast Risk": result["sea_risk"],
        "Oceanography Risk": result["ocean_risk"],
        "Cyclone Risk": result["cyclone_risk"],
        "Boat Vulnerability Score": result["boat_vulnerability_score"],
        "Boat Risk": result["boat_risk"],
        "Risk Factors": result["boat_reasons"],
        "Recommended Departure Time": recommended_slot["time"],
        "Recommended Window Risk": recommended_slot["final_risk"]
    }

    return report


