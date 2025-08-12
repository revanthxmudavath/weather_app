import os
import requests
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

ACCU_API = "https://dataservice.accuweather.com"
API_KEY = os.getenv("ACCUWEATHER_API_KEY", "")

class AccuError(Exception):
    pass

def _check_key():
    if not API_KEY:
        raise AccuError("Missing ACCUWEATHER_API_KEY. Set it in your .env")

def _get(url: str, params: Dict[str, Any]) -> Any:
    _check_key()
    params = {**params, "apikey": API_KEY}
    r = requests.get(url, params=params, timeout=15)
    if r.status_code != 200:
        raise AccuError(f"AccuWeather API error: {r.status_code} {r.text[:200]}")
    return r.json()

def search_by_text(query: str) -> List[Dict[str, Any]]:
    # Cities/landmarks text search
    url = f"{ACCU_API}/locations/v1/cities/search"
    return _get(url, {"q": query, "details": "true"})

def search_by_postal(query: str) -> List[Dict[str, Any]]:
    url = f"{ACCU_API}/locations/v1/postalcodes/search"
    return _get(url, {"q": query, "details": "true"})

def search_by_geo(lat: float, lon: float) -> Dict[str, Any]:
    url = f"{ACCU_API}/locations/v1/cities/geoposition/search"
    return _get(url, {"q": f"{lat},{lon}", "details": "true"})

def current_conditions(location_key: str) -> List[Dict[str, Any]]:
    url = f"{ACCU_API}/currentconditions/v1/{location_key}"
    return _get(url, {"details": "true"})

def forecast_5day(location_key: str, metric: bool=True) -> Dict[str, Any]:
    url = f"{ACCU_API}/forecasts/v1/daily/5day/{location_key}"
    return _get(url, {"metric": str(metric).lower()})

def ip_lookup_coords() -> Optional[Dict[str, float]]:

    try:
        r = requests.get("https://ipinfo.io/json", timeout=10)
        if r.status_code == 200:
            data = r.json()
            if "loc" in data:
                lat, lon = [float(x) for x in data["loc"].split(",")]
                return {"lat": lat, "lon": lon, "city": data.get("city"), "region": data.get("region"), "country": data.get("country")}
    except Exception:
        return None
    return None