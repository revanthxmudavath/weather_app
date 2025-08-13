 # Streamlit Weather App (AccuWeather)

    A clean Streamlit app that fetches current weather and a 5-day forecast from AccuWeather.

    
     What it does

    - Search weather by city/landmark, ZIP/postal code, or GPS (`lat,lon`)
    - See current conditions and a 5-day forecast
    - Save a request (location + date range + forecast JSON) to a local SQLite DB
    - Browse previously saved requests
    - Update the saved date range (only within the original window; extra days get trimmed)
    - Delete any saved request

     How location search works

    Users can enter:
    - City / landmark → AccuWeather cities search  
    - ZIP / postal code → AccuWeather postal search  
    - GPS coordinates (`lat,lon`) → AccuWeather geoposition search  
    If multiple matches are found, the app asks you to pick the correct one.

     Tech & why

    - Streamlit for a fast, friendly UI
    - AccuWeather API for weather data (free tier = forecast, typically 5 days)
    - SQLite (built-in Python `sqlite3`) for a no-setup local database
    - Pandas only for displaying/ exporting tables

     Files (high level)

    - `app.py` — Streamlit app (search UI, display, and CRUD tabs)
    - `accuweather_client.py` — tiny client for AccuWeather endpoints
    - `db.py` — creates `weather_requests` table
    - `db_ops.py` — minimal CRUD helpers (save / list / get / update / delete)
    - `utils.py` — small helpers (emoji icons, date formatting)
    - `requirements.txt` — dependencies
    - `.env` — put your AccuWeather API key here as `ACCUWEATHER_API_KEY=...`
        
     Quick Start

    1) Create and fill `.env` 
  
    2) Install deps
    
    pip install -r requirements.txt
   
    3) Run the app
   
    streamlit run app.py
 

