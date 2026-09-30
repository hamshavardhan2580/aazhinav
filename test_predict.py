import urllib.request, json

data = json.dumps({
    "boat_type": "Small",
    "distance_km": 15.0,
    "departure_time": "06:00",
    "return_time": "18:00",
    "crew_size": 4,
    "wind_speed": 20.0,
    "wave_height": 1.5,
    "temperature": 32.0,
    "latitude": 13.0,
    "longitude": 80.0
}).encode("utf-8")

req = urllib.request.Request(
    "http://localhost:8000/api/predict",
    data=data,
    headers={"Content-Type": "application/json"}
)

try:
    res = urllib.request.urlopen(req)
    result = json.loads(res.read().decode("utf-8"))
    print("SUCCESS!")
    print(f"  Risk Score:  {result.get('risk_score')}")
    print(f"  Risk Level:  {result.get('risk_level')}")
    print(f"  Sea Risk:    {result.get('sea_risk')}")
    print(f"  Ocean Risk:  {result.get('ocean_risk')}")
    print(f"  Cyclone Risk:{result.get('cyclone_risk')}")
    print(f"  Final Risk:  {result.get('final_risk')}")
    print(f"  Status:      {result.get('safety_status')}")
except Exception as e:
    print(f"FAILED: {e}")
    try:
        error_body = e.read().decode("utf-8")
        print("Error body:", error_body[:500])
    except:
        pass
