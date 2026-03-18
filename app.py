#!/usr/bin/env python3
"""
Flask web app for checking Singapore market/hawker centre closure status.

Run:
    pip install -r requirements.txt
    python app.py

Then visit http://localhost:5000
"""

from datetime import date, timedelta

from flask import Flask, render_template_string, request, jsonify

from sg_market_status.checker import (
    get_closures_on_date,
    get_map_data,
    get_upcoming_closures,
    search_market,
)

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SG Market Status Checker</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f2f5;
            color: #333;
            line-height: 1.6;
        }
        .container { max-width: 900px; margin: 0 auto; padding: 20px; }
        header {
            background: linear-gradient(135deg, #e53935, #d32f2f);
            color: white;
            padding: 30px 20px;
            text-align: center;
            border-radius: 12px;
            margin-bottom: 24px;
        }
        header h1 { font-size: 1.8em; margin-bottom: 6px; }
        header p { opacity: 0.9; font-size: 0.95em; }
        .tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .tab {
            padding: 10px 20px;
            background: white;
            border: 2px solid #ddd;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.95em;
            transition: all 0.2s;
        }
        .tab:hover { border-color: #e53935; color: #e53935; }
        .tab.active { background: #e53935; color: white; border-color: #e53935; }
        .search-box {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 20px;
        }
        .search-box input, .search-box select {
            padding: 10px 14px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 1em;
            width: 100%;
            margin-bottom: 10px;
        }
        .search-box button {
            padding: 10px 24px;
            background: #e53935;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
        }
        .search-box button:hover { background: #c62828; }
        .card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border-left: 4px solid #e53935;
        }
        .card.cleaning { border-left-color: #fb8c00; }
        .card.other_works { border-left-color: #7b1fa2; }
        .card h3 { font-size: 1.1em; margin-bottom: 8px; }
        .badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
            color: white;
        }
        .badge.cleaning { background: #fb8c00; }
        .badge.other_works { background: #7b1fa2; }
        .date-range { color: #666; font-size: 0.9em; margin-top: 4px; }
        .remarks { color: #888; font-size: 0.85em; margin-top: 4px; font-style: italic; }
        .empty { text-align: center; padding: 40px; color: #999; }
        .loading { text-align: center; padding: 30px; color: #666; }
        footer {
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 0.85em;
        }
        footer a { color: #e53935; text-decoration: none; }
        #map { height: 500px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        .legend {
            background: white;
            padding: 10px 14px;
            border-radius: 8px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.15);
            line-height: 1.8;
            font-size: 0.9em;
        }
        .legend-dot {
            display: inline-block;
            width: 14px;
            height: 14px;
            border-radius: 50%;
            margin-right: 6px;
            vertical-align: middle;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>SG Market Status Checker</h1>
            <p>Check which Singapore hawker centres & markets are closed for washing or renovation</p>
        </header>

        <div class="tabs">
            <div class="tab active" onclick="switchTab('today')">Closed Today</div>
            <div class="tab" onclick="switchTab('upcoming')">Upcoming Closures</div>
            <div class="tab" onclick="switchTab('search')">Search Market</div>
            <div class="tab" onclick="switchTab('date')">Check Date</div>
            <div class="tab" onclick="switchTab('map')">Map View</div>
        </div>

        <div id="panel-today" class="panel">
            <div id="today-results" class="loading">Loading...</div>
        </div>

        <div id="panel-upcoming" class="panel" style="display:none">
            <div class="search-box">
                <label>Days ahead: </label>
                <select id="upcoming-days" onchange="loadUpcoming()">
                    <option value="7">7 days</option>
                    <option value="14">14 days</option>
                    <option value="30" selected>30 days</option>
                    <option value="60">60 days</option>
                    <option value="90">90 days</option>
                </select>
            </div>
            <div id="upcoming-results" class="loading">Loading...</div>
        </div>

        <div id="panel-search" class="panel" style="display:none">
            <div class="search-box">
                <input type="text" id="search-input" placeholder="Enter market or hawker centre name..."
                       onkeydown="if(event.key==='Enter') doSearch()">
                <button onclick="doSearch()">Search</button>
            </div>
            <div id="search-results"></div>
        </div>

        <div id="panel-date" class="panel" style="display:none">
            <div class="search-box">
                <input type="date" id="date-input" value="{{ today }}">
                <button onclick="checkDate()">Check</button>
            </div>
            <div id="date-results"></div>
        </div>

        <div id="panel-map" class="panel" style="display:none">
            <div id="map"></div>
        </div>

        <footer>
            Data from <a href="https://data.gov.sg" target="_blank">data.gov.sg</a> (NEA)
        </footer>
    </div>

    <script>
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.style.display = 'none');
            event.target.classList.add('active');
            document.getElementById('panel-' + tab).style.display = 'block';

            if (tab === 'today') loadToday();
            if (tab === 'upcoming') loadUpcoming();
            if (tab === 'map') loadMap();
        }

        function renderClosures(closures, container) {
            const el = document.getElementById(container);
            if (!closures.length) {
                el.innerHTML = '<div class="empty">No closures found.</div>';
                return;
            }
            el.innerHTML = closures.map(c => {
                const typeLabel = c.closure_type === 'cleaning' ? 'Cleaning / Washing' : 'Renovation / Other Works';
                const badgeClass = c.closure_type;
                return `<div class="card ${badgeClass}">
                    <h3>${c.name}</h3>
                    <span class="badge ${badgeClass}">${typeLabel}</span>
                    <div class="date-range">${c.start_date} to ${c.end_date}</div>
                    ${c.remarks ? '<div class="remarks">' + c.remarks + '</div>' : ''}
                </div>`;
            }).join('');
        }

        function renderSearchResults(results, container) {
            const el = document.getElementById(container);
            if (!results.length) {
                el.innerHTML = '<div class="empty">No markets found.</div>';
                return;
            }
            el.innerHTML = results.map(r => {
                const closureHtml = r.closures.length
                    ? r.closures.map(c => {
                        const typeLabel = c.type === 'cleaning' ? 'Cleaning / Washing' : 'Renovation / Other Works';
                        return `<div style="margin-top:6px"><span class="badge ${c.type}">${typeLabel}</span>
                                <span class="date-range">${c.start_date} to ${c.end_date}</span></div>`;
                    }).join('')
                    : '<div style="margin-top:6px;color:#999">No scheduled closures found.</div>';
                return `<div class="card">
                    <h3>${r.name}</h3>
                    ${r.remarks ? '<div class="remarks">' + r.remarks + '</div>' : ''}
                    ${closureHtml}
                </div>`;
            }).join('');
        }

        async function loadToday() {
            document.getElementById('today-results').innerHTML = '<div class="loading">Loading...</div>';
            const res = await fetch('/api/today');
            const data = await res.json();
            renderClosures(data.closures, 'today-results');
        }

        async function loadUpcoming() {
            document.getElementById('upcoming-results').innerHTML = '<div class="loading">Loading...</div>';
            const days = document.getElementById('upcoming-days').value;
            const res = await fetch('/api/upcoming?days=' + days);
            const data = await res.json();
            renderClosures(data.closures, 'upcoming-results');
        }

        async function doSearch() {
            const q = document.getElementById('search-input').value.trim();
            if (!q) return;
            document.getElementById('search-results').innerHTML = '<div class="loading">Searching...</div>';
            const res = await fetch('/api/search?q=' + encodeURIComponent(q));
            const data = await res.json();
            renderSearchResults(data.results, 'search-results');
        }

        async function checkDate() {
            const d = document.getElementById('date-input').value;
            if (!d) return;
            document.getElementById('date-results').innerHTML = '<div class="loading">Loading...</div>';
            const res = await fetch('/api/date?date=' + d);
            const data = await res.json();
            renderClosures(data.closures, 'date-results');
        }

        let mapInstance = null;
        let mapLoaded = false;

        async function loadMap() {
            if (mapLoaded) {
                mapInstance.invalidateSize();
                return;
            }

            // Initialise Leaflet map centred on Singapore
            mapInstance = L.map('map').setView([1.3521, 103.8198], 12);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap contributors',
                maxZoom: 19,
            }).addTo(mapInstance);

            // Add legend
            const legend = L.control({ position: 'bottomright' });
            legend.onAdd = function () {
                const div = L.DomUtil.create('div', 'legend');
                div.innerHTML =
                    '<strong>Status</strong><br>' +
                    '<span class="legend-dot" style="background:#d32f2f"></span> Closed today<br>' +
                    '<span class="legend-dot" style="background:#f9a825"></span> Closing within 7 days<br>' +
                    '<span class="legend-dot" style="background:#388e3c"></span> Open';
                return div;
            };
            legend.addTo(mapInstance);

            // Fetch marker data
            const res = await fetch('/api/map');
            const data = await res.json();

            const colourHex = { red: '#d32f2f', yellow: '#f9a825', green: '#388e3c' };

            data.markers.forEach(m => {
                const colour = colourHex[m.colour] || '#388e3c';
                const circle = L.circleMarker([m.lat, m.lng], {
                    radius: 8,
                    fillColor: colour,
                    color: '#fff',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.9,
                }).addTo(mapInstance);

                let popup = '<strong>' + m.name + '</strong>';
                if (m.address) popup += '<br>' + m.address;
                if (m.status === 'closed') {
                    popup += '<br><span style="color:#d32f2f;font-weight:600">CLOSED</span>';
                } else if (m.status === 'closing_soon') {
                    popup += '<br><span style="color:#f9a825;font-weight:600">CLOSING SOON</span>';
                } else {
                    popup += '<br><span style="color:#388e3c;font-weight:600">OPEN</span>';
                }
                if (m.closure_info) popup += '<br><em>' + m.closure_info + '</em>';
                circle.bindPopup(popup);
            });

            mapLoaded = true;
        }

        // Load today's closures on page load
        loadToday();
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, today=date.today().isoformat())


@app.route("/api/today")
def api_today():
    closures = get_closures_on_date()
    return jsonify({"date": date.today().isoformat(), "closures": closures})


@app.route("/api/upcoming")
def api_upcoming():
    days = request.args.get("days", 30, type=int)
    days = min(days, 365)
    closures = get_upcoming_closures(days_ahead=days)
    return jsonify({"days_ahead": days, "closures": closures})


@app.route("/api/search")
def api_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Please provide a search query (?q=name)"}), 400
    results = search_market(query)
    return jsonify({"query": query, "results": results})


@app.route("/api/map")
def api_map():
    markers = get_map_data()
    return jsonify({"markers": markers})


@app.route("/api/date")
def api_date():
    date_str = request.args.get("date", "")
    if not date_str:
        return jsonify({"error": "Please provide a date (?date=YYYY-MM-DD)"}), 400
    closures = get_closures_on_date(date_str)
    return jsonify({"date": date_str, "closures": closures})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
