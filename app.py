from datetime import date, datetime
from io import BytesIO
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
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from xml.sax.saxutils import escape as xml_escape

init_db()
    
st.set_page_config(page_title="Weather • AccuWeather", page_icon="⛅", layout="centered")

c_head_1, c_head_2 = st.columns([6,1])

with c_head_1:
    st.title("⛅ Weather App")
    st.caption("Built by **Revanth Mudavath**")

with c_head_2:
    
    if "show_info" not in st.session_state:
        st.session_state.show_info = False
    if st.button("☰ Info"):
        st.session_state.show_info = not st.session_state.show_info


if st.session_state.show_info:
    st.sidebar.title("About PM Accelerator")
    st.sidebar.markdown("""
**Product Manager Accelerator (PMA)**

The Product Manager Accelerator Program is designed to support PM professionals through every stage of their careers. From students looking for entry-level jobs to Directors looking to take on a leadership role, our program has helped over hundreds of students fulfill their career aspirations.

Our Product Manager Accelerator community are ambitious and committed. Through our program they have learnt, honed and developed new PM and leadership skills, giving them a strong foundation for their future endeavors.

**Services we offer**  
- 🚀 **PMA Pro** – End-to-end product manager job hunting program that helps you master FAANG-level Product Management skills, conduct unlimited mock interviews, and gain job referrals through our largest alumni network. 25% of our offers came from tier 1 companies and get paid as high as $800K/year.  
- 🚀 **AI PM Bootcamp** – Gain hands-on AI Product Management skills by building a real-life AI product with a team of AI Engineers, data scientists, and designers. We will also help you launch your product with real user engagement using our 100,000+ PM community and social media channels.  
- 🚀 **PMA Power Skills** – Designed for existing product managers to sharpen their product management skills, leadership skills, and executive presentation skills  
- 🚀 **PMA Leader** – We help you accelerate your product management career, get promoted to Director and product executive levels, and win in the board room.  
- 🚀 **1:1 Resume Review** – We help you rewrite your killer product manager resume to stand out from the crowd, with an interview guarantee.  
  Get started with the FREE killer PM resume template used by over 14,000 product managers: https://www.drnancyli.com/pmresume

We also published over **500+ free trainings and courses**.  
YouTube: https://www.youtube.com/c/drnancyli  
Instagram: @drnancyli

LinkedIn page: *Product Manager Accelerator*
""")

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

def daily_forecasts_to_df(dfs):
    return pd.DataFrame([{
        "date": fmt_dt(d.get("Date","")),
        "min": d.get("Temperature",{}).get("Minimum",{}).get("Value"),
        "max": d.get("Temperature",{}).get("Maximum",{}).get("Value"),
        "day": d.get("Day",{}).get("IconPhrase"),
        "night": d.get("Night",{}).get("IconPhrase")
    } for d in dfs])

def df_to_xml(df: pd.DataFrame, root_tag="Forecast", row_tag="Day"):
    lines = [f"<{root_tag}>"]
    for _, row in df.iterrows():
        lines.append(f"  <{row_tag}>")
        for col, val in row.items():
            text = "" if pd.isna(val) else str(val)
            lines.append(f"    <{col}>{xml_escape(text)}</{col}>")
        lines.append(f"  </{row_tag}>")
    lines.append(f"</{root_tag}>")
    return "\n".join(lines)

def df_to_pdf_bytes(df: pd.DataFrame, title="Weather Forecast"):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter
    x = 40
    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y, title)
    y -= 20
    c.setFont("Helvetica", 10)
    
    headers = list(df.columns)
    c.drawString(x, y, " | ".join(headers))
    y -= 15
    c.line(x, y, width - x, y)
    y -= 15
    
    for _, row in df.iterrows():
        line = " | ".join("" if pd.isna(v) else str(v) for v in row.tolist())
        if y < 50:
            c.showPage()
            y = height - 50
        c.drawString(x, y, line)
        y -= 15
    c.showPage()
    c.save()
    pdf = buf.getvalue()
    buf.close()
    return pdf

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
            st.markdown(f"**Location:** {row[2]}  \\n**Dates:** {row[3]} → {row[4]}  \\n**Units:** {row[5]}")
            try:
                data = json.loads(row[6]) if row[6] else {}
            except Exception:
                data = {}
            dfs = data.get("DailyForecasts", []) if isinstance(data, dict) else []
            if dfs:
                df = daily_forecasts_to_df(dfs)
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

            # EXPORT
            with col3:
                st.markdown("**Export**")
                if dfs:
                    fmt = st.selectbox("Format", ["CSV", "JSON", "XML", "PDF"], index=0)
                    fname_base = f"weather_request_{row[0]}"
                    if fmt == "CSV":
                        csv_bytes = df.to_csv(index=False).encode()
                        st.download_button("Download CSV", csv_bytes, file_name=f"{fname_base}.csv", mime="text/csv")
                    elif fmt == "JSON":
                        json_bytes = json.dumps(data, indent=2).encode()
                        st.download_button("Download JSON", json_bytes, file_name=f"{fname_base}.json", mime="application/json")
                    elif fmt == "XML":
                        xml_str = df_to_xml(df, root_tag="Forecast", row_tag="Day")
                        st.download_button("Download XML", xml_str.encode(), file_name=f"{fname_base}.xml", mime="application/xml")
                    elif fmt == "PDF":
                        pdf_bytes = df_to_pdf_bytes(df, title=f"Forecast for {row[2]}")
                        st.download_button("Download PDF", pdf_bytes, file_name=f"{fname_base}.pdf", mime="application/pdf")

st.markdown("---")
st.caption("Tip: Enter GPS like `37.7749,-122.4194` for precision.")