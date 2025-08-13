from datetime import date, datetime
import json
import pandas as pd
import streamlit as st
from accuweather_client import (
        search_by_text, search_by_postal, search_by_geo,
        current_conditions, forecast_5day, ip_lookup_coords, AccuError
    )
from utils import icon_emoji, fmt_dt
from typing import Optional
from db_ops import save_request, get_requests, delete_request, list_requests, update_request
from db import init_db

init_db()
    
st.set_page_config(page_title="Weather • AccuWeather", page_icon="⛅", layout="centered")
st.title("⛅ Weather App")

    
@st.cache_data(show_spinner=False, ttl=600)
def _search_location(query: str):
       
    q = query.strip()
    if "," in q:
        try:
            lat, lon = [float(x.strip()) for x in q.split(",", 1)]
            loc = search_by_geo(lat, lon)
            return [loc] if loc else []
        except Exception:
            pass
    if q.replace("-", "").replace(" ", "").isdigit():
        return search_by_postal(q)
    return search_by_text(q)
    
@st.cache_data(show_spinner=False, ttl=300)
def _get_current(location_key: str):
    return current_conditions(location_key)
    
@st.cache_data(show_spinner=False, ttl=300)
def _get_forecast(location_key: str):
    return forecast_5day(location_key, metric=True)

def _slice_forecast_json(fjson: dict, start_str: str, end_str: str) -> dict:
    
    try:
        start = date.fromisoformat(start_str)
        end = date.fromisoformat(end_str)
    except Exception:
        return fjson
    dfs = fjson.get("DailyForecasts", []) if isinstance(fjson, dict) else []
    kept = []
    for d in dfs:
        try:
            dt = datetime.fromisoformat(d["Date"].replace("Z", "+00:00")).date()
        except Exception:
            continue
        if start <= dt <= end:
            kept.append(d)
    return {**fjson, "DailyForecasts": kept}



    
def pick_location_ui(default_query: str = "") -> Optional[dict]:
    with st.container(border=True):
        st.subheader("Find a location")
        c1, c2 = st.columns([3,1])
        with c1:
            query = st.text_input("Enter city, landmark, ZIP/Postal code, or GPS (lat,lon)", value=default_query, placeholder="e.g., Seattle or 10001 or 47.60,-122.33", label_visibility="collapsed")
        with c2:
            use_ip = st.button("📍 Use my location")
        
        if use_ip:
            with st.spinner("Detecting your location…"):
                guess = ip_lookup_coords()
            if guess:
                st.info(f"Using approximate location based on IP: {guess.get('city')}, {guess.get('region')} ({guess.get('country')})")
                try:
                    loc = search_by_geo(guess["lat"], guess["lon"])
                    return loc
                except AccuError as e:
                    st.error(str(e))
            else:
                st.warning("Could not determine your location automatically. Please type a city or ZIP.")
        
        if query:
            with st.spinner("Searching…"):
                try:
                    results = _search_location(query)
                except AccuError as e:
                    st.error(str(e))
                    return None
            if not results:
                st.warning("No matches. Try a nearby city or ZIP code.")
                return None
            # If multiple, let user choose
            if isinstance(results, list) and len(results) > 1:
                labels = []
                for r in results:
                    admin = r.get("AdministrativeArea", {}).get("LocalizedName", "")
                    country = r.get("Country", {}).get("LocalizedName", "")
                    name = r.get("LocalizedName", r.get("EnglishName", ""))
                    labels.append(f"{name}, {admin}, {country}  ·  Key: {r.get('Key')}")
                idx = st.selectbox("Did you mean…", options=list(range(len(labels))), format_func=lambda i: labels[i])
                return results[idx]
            # If single item or geoposition
            if isinstance(results, list):
                return results[0]
            return results
    return None

tabs = st.tabs(["Search", "Saved Requests"])

    
with tabs[0]:
    loc = pick_location_ui()
    if loc:
        location_key = loc.get("Key")
        header = f"{loc.get('LocalizedName', loc.get('EnglishName', 'Selected'))}"
        admin = loc.get("AdministrativeArea", {}).get("LocalizedName", "")
        country = loc.get("Country", {}).get("LocalizedName", "")
        st.markdown(f"### **{header}**  \n{admin}, {country}  \nLocation Key: `{location_key}`")

        # Current conditions
        try:
            cc = _get_current(location_key)
        except AccuError as e:
            st.error(str(e))
            st.stop()

        if isinstance(cc, list) and cc:
            c = cc[0]
            icon_no = c.get("WeatherIcon", 1)
            text = c.get("WeatherText", "")
            temp_c = c.get("Temperature", {}).get("Metric", {}).get("Value")
            realfeel_c = c.get("RealFeelTemperature", {}).get("Metric", {}).get("Value")
            humidity = c.get("RelativeHumidity")
            wind = c.get("Wind", {}).get("Speed", {}).get("Metric", {}).get("Value")
            uv = c.get("UVIndex")

            st.markdown("---")
            colA, colB = st.columns([1,2])
            with colA:
                st.markdown(f"# {icon_emoji(icon_no)}")
                if temp_c is not None:
                    st.markdown(f"## {temp_c:.0f}°C")
                if text:
                    st.caption(text)
            with colB:
                st.metric("RealFeel®", f"{realfeel_c:.0f}°C" if realfeel_c is not None else "—")
                st.metric("Humidity", f"{humidity}%" if humidity is not None else "—")
                st.metric("Wind", f"{wind} km/h" if wind is not None else "—")
                st.metric("UV Index", uv if uv is not None else "—")
        else:
            st.info("No current conditions available.")

        # Forecast + Save controls
        try:
            f = _get_forecast(location_key)
        except AccuError as e:
            st.error(str(e))
            st.stop()

        st.markdown("### 5-Day Forecast")
        dfs = f.get("DailyForecasts", []) if isinstance(f, dict) else []
        if dfs:
            rows = len(dfs)
            cols = st.columns(rows)
            for i, d in enumerate(dfs):
                with cols[i]:
                    date_lbl = fmt_dt(d.get("Date", ""))
                    min_c = d.get("Temperature", {}).get("Minimum", {}).get("Value")
                    max_c = d.get("Temperature", {}).get("Maximum", {}).get("Value")
                    day_icon = d.get("Day", {}).get("Icon", 1)
                    night_icon = d.get("Night", {}).get("Icon", 33)
                    day_phrase = d.get("Day", {}).get("IconPhrase", "")
                    night_phrase = d.get("Night", {}).get("IconPhrase", "")
                    st.markdown(f"**{date_lbl}**")
                    st.markdown(f"{icon_emoji(day_icon)}  **Day**: {day_phrase}")
                    st.markdown(f"{icon_emoji(night_icon)}  **Night**: {night_phrase}")
                    st.markdown(f"**Min/Max**: {min_c:.0f}°C / {max_c:.0f}°C")
        else:
            st.info("No forecast data available.")

        

        # Simple persistence block
        st.subheader("Save this forecast (CREATE)")
        c1, c2 = st.columns(2)
        with c1:
            start_date = st.date_input("Start date", value=date.today())
        with c2:
            end_date = st.date_input("End date", value=date.today())
        units = "metric"
        if st.button("Save request"):
            if start_date > end_date:
                st.error("Start date must be ≤ end date.")
            else:
                label = f"{header} - {admin}, {country}"
                rid = save_request(location_key, label, str(start_date), str(end_date), units, f)
                st.success(f"Saved request #{rid} for {label}.")


with tabs[1]:
    st.subheader("Saved Requests")
    reqs = list_requests()
    if not reqs:
        st.info("No saved requests yet.")
    else:
        
        display = [f"#{r[0]} — {r[1]} [{r[2]} → {r[3]}] ({r[4]})" for r in reqs]
        idx = st.selectbox("Select", options=list(range(len(display))), format_func=lambda i: display[i])
        rid = reqs[idx][0]

        row = get_requests(rid)  
        if row:
            st.markdown(f"**Location:** {row[2]}  \n**Dates:** {row[3]} → {row[4]}  \n**Units:** {row[5]}")
            try:
                data = json.loads(row[6]) if row[6] else {}
            except Exception:
                data = {}
            dfs = data.get("DailyForecasts", []) if isinstance(data, dict) else []
            if dfs:
                df = pd.DataFrame([{
                    "date": fmt_dt(d.get("Date","")),
                    "min": d.get("Temperature",{}).get("Minimum",{}).get("Value"),
                    "max": d.get("Temperature",{}).get("Maximum",{}).get("Value"),
                    "day": d.get("Day",{}).get("IconPhrase"),
                    "night": d.get("Night",{}).get("IconPhrase")
                } for d in dfs])
                st.dataframe(df, use_container_width=True)

            st.divider()
            col1, col2, col3 = st.columns(3)

            # UPDATE
            with col1:
                st.markdown("**Update dates**")
                old_start = date.fromisoformat(row[3])
                old_end = date.fromisoformat(row[4])
                new_start = st.date_input("New start", key=f"upd_start_{rid}", value=old_start)
                new_end   = st.date_input("New end",   key=f"upd_end_{rid}",   value=old_end)

                if st.button("Update", key=f"upd_btn_{rid}"):
                    
                    if new_start > new_end:
                        st.error("Start date must be ≤ end date.")
                        st.stop()

                   
                    if new_start < old_start:
                        st.error(f"You can only update within the original start date ({old_start}).")
                        st.stop()
                    if new_end > old_end:
                        st.error(f"You can only update within the original end date ({old_end}).")
                        st.stop()

                    try:
                        current_json = json.loads(row[6]) if row[6] else {}
                    except Exception:
                        current_json = {}

                    sliced = _slice_forecast_json(current_json, str(new_start), str(new_end))
                    days = sliced.get("DailyForecasts", [])
                    if not days:
                        st.warning("No days remain in that range. Nothing to update.")
                    else:
                        update_request(rid, str(new_start), str(new_end), sliced)  
                        st.success(f"Updated! Kept {len(days)} day(s) within {new_start} → {new_end}.")

            # DELETE
            with col2:
                st.markdown("**Delete**")
                if st.button("Delete request", key=f"del_btn_{rid}"):
                    delete_request(rid)
                    st.success("Deleted. Refresh the list from the select box.")

st.markdown("---")
st.caption("Tip: Enter GPS like `37.7749,-122.4194` for precision.")