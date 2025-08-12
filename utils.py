from datetime import datetime
    
ICON_MAP = {
        1: "☀️", 2: "🌤️", 3: "⛅", 4: "🌥️", 5: "☁️",
        6: "☁️", 7: "☁️", 8: "☁️", 11: "🌫️",
        12: "🌧️", 13: "🌦️", 14: "🌦️", 15: "⛈️",
        16: "⛈️", 17: "⛈️", 18: "🌧️", 19: "🌧️",
        20: "🌧️", 21: "🌧️", 22: "🌧️", 23: "❄️",
        24: "🌨️", 25: "🌨️", 26: "🌨️", 29: "🌧️❄️",
        30: "🥶", 31: "🥶", 32: "💨", 33: "🌙",
        34: "🌤️", 35: "🌙⛅", 36: "☁️", 37: "☁️",
        38: "☁️", 39: "🌧️", 40: "🌧️", 41: "⛈️",
        42: "⛈️", 43: "🌨️", 44: "🌨️"
    }
    
def icon_emoji(icon_number: int) -> str:
    return ICON_MAP.get(icon_number, "🌡️")
    
def fmt_dt(ts: str) -> str:
        
    try:
        return datetime.fromisoformat(ts.replace("Z","+00:00")).strftime("%a, %b %d")
    except Exception:
        return ts