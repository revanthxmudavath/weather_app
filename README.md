 # Streamlit Weather App (AccuWeather)

    A clean Streamlit app that fetches current weather and a 5-day forecast from AccuWeather.

    
    - Search by **city/town/landmark**, **ZIP/Postal code**, or **GPS coordinates** (`lat,lon`)
    - Button for **Use my current location** (IP-based, approximate)
    - **5-day forecast**
    
    ## Quick Start

    1) Create and fill `.env` 
  
    cp .env.example .env
    # open .env and paste your AccuWeather API key
  

    2) Install deps
    
    pip install -r requirements.txt
   

    3) Run the app
   
    streamlit run app.py
 

    ## Notes

    - AccuWeather has multiple search endpoints. This app supports:
      - Text search (cities/landmarks): `/locations/v1/cities/search`
      - Postal/ZIP search: `/locations/v1/postalcodes/search`
      - GPS coordinates: `/locations/v1/cities/geoposition/search?q=lat,lon`
    - Current conditions: `/currentconditions/v1/{locationKey}?details=true`
    - 5-day forecast (metric): `/forecasts/v1/daily/5day/{locationKey}?metric=true`
