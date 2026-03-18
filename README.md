# SG Market Status Checker

A web app to check which Singapore hawker centres and markets are closed for cleaning, washing, or renovation. Powered by live data from [data.gov.sg](https://data.gov.sg) (NEA).

## Features

- **Closed Today** — Shows closures for today and the next 3 days, grouped by date
- **Upcoming Closures** — Browse closures up to 90 days ahead
- **Search Market** — Live search with instant results as you type
- **Calendar View** — Monthly calendar with continuous spanning event bars across multi-day closures; click any day or event for details in a popup
- **Map View** — Interactive Leaflet map with colour-coded markers (open/closed/closing soon), stall counts, photos, and Google 3D view links
- **Favourites** — Star any market to save it; persisted in localStorage across sessions

Each market card shows:
- Photo from NEA
- Closure type badge (Cleaning / Renovation)
- Date range
- Remarks

## Getting Started

### Option 1: Static HTML (no server needed)

Open `index.html` directly in a browser. It fetches data client-side from the data.gov.sg API.

### Option 2: Flask server

```bash
pip install -r requirements.txt
python app.py
```

Then visit [http://localhost:5000](http://localhost:5000).

### Option 3: CLI

```bash
pip install -r requirements.txt
python cli.py --help
```

## Tech Stack

- **Frontend**: Vanilla HTML/CSS/JS (single file, no build step)
- **Map**: [Leaflet.js](https://leafletjs.com/) + OpenStreetMap tiles
- **Backend** (optional): Flask + Python
- **Data source**: [data.gov.sg Datastore API](https://data.gov.sg) — NEA hawker centre closure dataset

## Data Source

Dataset ID: `d_bda4baa634dd1cc7a6c7cad5f19e2d68`

Fields used: `name`, `q1-q4_cleaningstartdate/enddate`, `other_works_startdate/enddate`, `remarks_*`, `latitude_hc`, `longitude_hc`, `address_myenv`, `photourl`, `no_of_food_stalls`, `no_of_market_stalls`, `google_3d_view`, `description_myenv`

## Mobile Support

Responsive design with breakpoints at 768px, 480px, and 360px. Cards stack vertically on phones, calendar adapts to small screens, and the map resizes appropriately.

## License

Data provided by the National Environment Agency (NEA) via data.gov.sg.
