"""
Fetches hawker centre / market closure data from data.gov.sg NEA datasets.

Datasets used:
- Dates of Hawker Centres Closure: d_bda4baa634dd1cc7a6c7cad5f19e2d68
- List of Government Markets & Hawker Centres: d_68a42f09f350881996d83f9cd73ab02f
- Hawker Centres GeoJSON (locations): d_4a086da0a5553be1d89383cd90d07ecd
"""

import requests

BASE_URL = "https://data.gov.sg/api/action/datastore_search"

CLOSURE_DATASET_ID = "d_bda4baa634dd1cc7a6c7cad5f19e2d68"
MARKETS_LIST_DATASET_ID = "d_68a42f09f350881996d83f9cd73ab02f"
GEOJSON_DATASET_ID = "d_4a086da0a5553be1d89383cd90d07ecd"

# Fallback: initiate-download API (v1) for full CSV download
DOWNLOAD_INITIATE_URL = (
    "https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/initiate-download"
)
DOWNLOAD_POLL_URL = (
    "https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"
)


def fetch_closure_data(limit=500, offset=0):
    """Fetch hawker centre closure dates from data.gov.sg."""
    params = {
        "resource_id": CLOSURE_DATASET_ID,
        "limit": limit,
        "offset": offset,
    }
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    result = data.get("result", {})
    return result.get("records", []), result.get("total", 0)


def fetch_all_closure_data():
    """Fetch all closure records (handles pagination)."""
    all_records = []
    offset = 0
    limit = 500
    while True:
        records, total = fetch_closure_data(limit=limit, offset=offset)
        all_records.extend(records)
        offset += limit
        if offset >= total:
            break
    return all_records


def fetch_markets_list(limit=500, offset=0):
    """Fetch the list of government markets and hawker centres."""
    params = {
        "resource_id": MARKETS_LIST_DATASET_ID,
        "limit": limit,
        "offset": offset,
    }
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    result = data.get("result", {})
    return result.get("records", []), result.get("total", 0)


def fetch_all_markets():
    """Fetch all market/hawker centre records."""
    all_records = []
    offset = 0
    limit = 500
    while True:
        records, total = fetch_markets_list(limit=limit, offset=offset)
        all_records.extend(records)
        offset += limit
        if offset >= total:
            break
    return all_records


def fetch_hawker_geojson():
    """Fetch hawker centre locations as GeoJSON from data.gov.sg.

    Uses the poll-download endpoint (GeoJSON datasets skip initiate-download).
    Returns a GeoJSON FeatureCollection dict.
    """
    poll_url = DOWNLOAD_POLL_URL.format(dataset_id=GEOJSON_DATASET_ID)
    resp = requests.get(poll_url, timeout=30)
    resp.raise_for_status()
    poll_data = resp.json()

    if poll_data.get("code") != 0:
        raise RuntimeError(f"GeoJSON poll failed: {poll_data.get('errMsg', 'unknown error')}")

    download_url = poll_data["data"]["url"]
    geo_resp = requests.get(download_url, timeout=30)
    geo_resp.raise_for_status()
    return geo_resp.json()
