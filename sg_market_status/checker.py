"""
Core logic for checking which Singapore markets/hawker centres are currently
closed for washing, cleaning, or renovation works.
"""

from datetime import date, datetime
from sg_market_status.data_fetcher import fetch_all_closure_data, fetch_all_markets, fetch_hawker_geojson


def parse_date(date_str):
    """Parse a date string in common formats from data.gov.sg."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _normalise_record(record):
    """Normalise field names to a consistent format (lowercase, underscored).

    The data.gov.sg dataset may use varying column names such as:
      - name_of_centre / Name of Centre
      - cleaning_startdate / Cleaning Start Date
      - cleaning_enddate / Cleaning End Date
      - remarks / Remarks
      - other_works_startdate / Other Works Start Date
      - other_works_enddate / Other Works End Date
    """
    normalised = {}
    for key, value in record.items():
        norm_key = key.strip().lower().replace(" ", "_")
        normalised[norm_key] = value
    return normalised


def _get_field(record, *possible_keys, default=None):
    """Try multiple possible field names and return the first match."""
    for key in possible_keys:
        if key in record and record[key]:
            return record[key]
    return default


def get_closures_on_date(target_date=None):
    """Return list of markets/hawker centres closed on a given date.

    Each entry contains:
      - name: centre name
      - closure_type: 'cleaning' or 'other_works' (renovation/R&R)
      - start_date: closure start date
      - end_date: closure end date
      - remarks: any additional notes
    """
    if target_date is None:
        target_date = date.today()
    elif isinstance(target_date, str):
        target_date = parse_date(target_date) or date.today()

    records = fetch_all_closure_data()
    closed = []

    for raw_record in records:
        record = _normalise_record(raw_record)

        name = _get_field(
            record,
            "name_of_centre",
            "name",
            "centre_name",
            "hawker_centre",
            default="Unknown",
        )

        # Check cleaning closure period
        cleaning_start = parse_date(
            _get_field(record, "cleaning_startdate", "cleaning_start_date", "q1_cleaningstartdate")
        )
        cleaning_end = parse_date(
            _get_field(record, "cleaning_enddate", "cleaning_end_date", "q1_cleaningenddate")
        )

        if cleaning_start and cleaning_end and cleaning_start <= target_date <= cleaning_end:
            closed.append({
                "name": name,
                "closure_type": "cleaning",
                "start_date": cleaning_start.isoformat(),
                "end_date": cleaning_end.isoformat(),
                "remarks": _get_field(record, "remarks", "cleaning_remarks", default=""),
            })
            continue

        # Check for quarterly cleaning fields (q1-q4)
        for q in range(1, 5):
            q_start = parse_date(
                _get_field(record, f"q{q}_cleaningstartdate", f"q{q}_cleaning_startdate")
            )
            q_end = parse_date(
                _get_field(record, f"q{q}_cleaningenddate", f"q{q}_cleaning_enddate")
            )
            if q_start and q_end and q_start <= target_date <= q_end:
                closed.append({
                    "name": name,
                    "closure_type": "cleaning",
                    "start_date": q_start.isoformat(),
                    "end_date": q_end.isoformat(),
                    "remarks": _get_field(record, "remarks", default=f"Q{q} cleaning"),
                })
                break

        # Check other works (renovation / R&R) closure period
        works_start = parse_date(
            _get_field(
                record,
                "other_works_startdate",
                "other_works_start_date",
                "others_startdate",
            )
        )
        works_end = parse_date(
            _get_field(
                record,
                "other_works_enddate",
                "other_works_end_date",
                "others_enddate",
            )
        )

        if works_start and works_end and works_start <= target_date <= works_end:
            closed.append({
                "name": name,
                "closure_type": "other_works",
                "start_date": works_start.isoformat(),
                "end_date": works_end.isoformat(),
                "remarks": _get_field(record, "remarks_for_other_works", "remarks_other", "remarks", default=""),
            })

    return closed


def get_upcoming_closures(days_ahead=30, target_date=None):
    """Return closures happening within the next N days."""
    if target_date is None:
        target_date = date.today()
    elif isinstance(target_date, str):
        target_date = parse_date(target_date) or date.today()

    from datetime import timedelta
    end_window = target_date + timedelta(days=days_ahead)

    records = fetch_all_closure_data()
    upcoming = []

    for raw_record in records:
        record = _normalise_record(raw_record)

        name = _get_field(
            record,
            "name_of_centre",
            "name",
            "centre_name",
            "hawker_centre",
            default="Unknown",
        )

        date_fields = []

        # Collect all cleaning dates
        for prefix in ["cleaning", "q1_cleaning", "q2_cleaning", "q3_cleaning", "q4_cleaning"]:
            start = parse_date(_get_field(record, f"{prefix}startdate", f"{prefix}_startdate"))
            end = parse_date(_get_field(record, f"{prefix}enddate", f"{prefix}_enddate"))
            if start and end:
                date_fields.append(("cleaning", start, end))

        # Other works dates
        works_start = parse_date(
            _get_field(record, "other_works_startdate", "other_works_start_date", "others_startdate")
        )
        works_end = parse_date(
            _get_field(record, "other_works_enddate", "other_works_end_date", "others_enddate")
        )
        if works_start and works_end:
            date_fields.append(("other_works", works_start, works_end))

        for closure_type, start, end in date_fields:
            # Include if closure overlaps with the window [target_date, end_window]
            if start <= end_window and end >= target_date:
                upcoming.append({
                    "name": name,
                    "closure_type": closure_type,
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                    "remarks": _get_field(record, "remarks", default=""),
                })

    # Sort by start date
    upcoming.sort(key=lambda x: x["start_date"])
    return upcoming


def search_market(query):
    """Search for a specific market/hawker centre by name and return its closure info."""
    records = fetch_all_closure_data()
    query_lower = query.lower()
    results = []

    for raw_record in records:
        record = _normalise_record(raw_record)
        name = _get_field(
            record,
            "name_of_centre",
            "name",
            "centre_name",
            "hawker_centre",
            default="Unknown",
        )
        if query_lower in name.lower():
            closures = []
            for prefix in ["cleaning", "q1_cleaning", "q2_cleaning", "q3_cleaning", "q4_cleaning"]:
                start = parse_date(_get_field(record, f"{prefix}startdate", f"{prefix}_startdate"))
                end = parse_date(_get_field(record, f"{prefix}enddate", f"{prefix}_enddate"))
                if start and end:
                    closures.append({
                        "type": "cleaning",
                        "start_date": start.isoformat(),
                        "end_date": end.isoformat(),
                    })

            works_start = parse_date(
                _get_field(record, "other_works_startdate", "other_works_start_date", "others_startdate")
            )
            works_end = parse_date(
                _get_field(record, "other_works_enddate", "other_works_end_date", "others_enddate")
            )
            if works_start and works_end:
                closures.append({
                    "type": "other_works",
                    "start_date": works_start.isoformat(),
                    "end_date": works_end.isoformat(),
                })

            results.append({
                "name": name,
                "closures": closures,
                "remarks": _get_field(record, "remarks", default=""),
            })

    return results


def get_map_data(target_date=None):
    """Build map marker data: each hawker centre with lat/lng and colour status.

    Returns a list of dicts:
        - name, lat, lng
        - status: 'closed' | 'closing_soon' | 'open'
        - colour: 'red' | 'yellow' | 'green'
        - closure_info: string with details (if applicable)
    """
    from datetime import timedelta

    if target_date is None:
        target_date = date.today()
    elif isinstance(target_date, str):
        target_date = parse_date(target_date) or date.today()

    week_ahead = target_date + timedelta(days=7)

    # 1. Build a lookup of closure status by centre name (lowered)
    records = fetch_all_closure_data()
    closure_lookup = {}  # name_lower -> { status, info }

    for raw_record in records:
        record = _normalise_record(raw_record)
        name = _get_field(
            record,
            "name_of_centre", "name", "centre_name", "hawker_centre",
            default="Unknown",
        )
        name_lower = name.strip().lower()

        # Gather all closure periods
        periods = []
        for prefix in ["cleaning", "q1_cleaning", "q2_cleaning", "q3_cleaning", "q4_cleaning"]:
            start = parse_date(_get_field(record, f"{prefix}startdate", f"{prefix}_startdate"))
            end = parse_date(_get_field(record, f"{prefix}enddate", f"{prefix}_enddate"))
            if start and end:
                periods.append(("Cleaning/Washing", start, end))

        works_start = parse_date(
            _get_field(record, "other_works_startdate", "other_works_start_date", "others_startdate")
        )
        works_end = parse_date(
            _get_field(record, "other_works_enddate", "other_works_end_date", "others_enddate")
        )
        if works_start and works_end:
            periods.append(("Renovation/Other Works", works_start, works_end))

        for label, start, end in periods:
            if start <= target_date <= end:
                closure_lookup[name_lower] = {
                    "status": "closed",
                    "info": f"{label}: {start.isoformat()} to {end.isoformat()}",
                }
                break
            elif target_date < start <= week_ahead:
                if name_lower not in closure_lookup or closure_lookup[name_lower]["status"] != "closed":
                    closure_lookup[name_lower] = {
                        "status": "closing_soon",
                        "info": f"{label}: {start.isoformat()} to {end.isoformat()}",
                    }

    # 2. Get GeoJSON features
    geojson = fetch_hawker_geojson()
    features = geojson.get("features", [])

    colour_map = {"closed": "red", "closing_soon": "yellow", "open": "green"}
    markers = []

    for feature in features:
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", [])
        if not coords or len(coords) < 2:
            continue

        lng, lat = coords[0], coords[1]
        name = props.get("NAME", props.get("name", "Unknown"))
        name_lower = name.strip().lower()

        # Match against closure lookup (fuzzy: try substring matching)
        matched_status = None
        for closure_name, info in closure_lookup.items():
            if closure_name in name_lower or name_lower in closure_name:
                matched_status = info
                break

        if matched_status:
            status = matched_status["status"]
            closure_info = matched_status["info"]
        else:
            status = "open"
            closure_info = ""

        markers.append({
            "name": name,
            "lat": lat,
            "lng": lng,
            "status": status,
            "colour": colour_map[status],
            "closure_info": closure_info,
            "address": props.get("ADDRESSSTREETNAME", ""),
        })

    return markers
