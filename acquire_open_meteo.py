"""
Acquire the timestamped Open-Meteo backbone for the Smart Agriculture
Crop Health Monitoring stream-processing project.

Run:
    python acquire_open_meteo.py

Output:
    data/open_meteo_karnataka_2024-10-05_to_2026-10-04.csv
    data/open_meteo_metadata.json

The script intentionally uses real Open-Meteo data; it does NOT generate
synthetic observations or inject faults. Fault/stress injection belongs
after the baseline EDA.
"""
from pathlib import Path
import json
import time
import requests
import pandas as pd

START = "2024-10-05"
END = "2026-10-04"
TIMEZONE = "Asia/Kolkata"

LOCATIONS = {
    "KA_BENGALURU": (12.9716, 77.5946),
    "KA_MYSURU": (12.2958, 76.6394),
    "KA_MANDYA": (12.5218, 76.8951),
    "KA_TUMAKURU": (13.3392, 77.1130),
    "KA_HASSAN": (13.0033, 76.1004),
    "KA_SHIVAMOGGA": (13.9299, 75.5681),
    "KA_BELAGAVI": (15.8497, 74.4977),
    "KA_DHARWAD": (15.4589, 75.0078),
    "KA_KALABURAGI": (17.3297, 76.8343),
    "KA_BALLARI": (15.1394, 76.9214),
}

HOURLY = ",".join([
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation",
    "vapour_pressure_deficit",
    "soil_moisture_0_to_7cm",
    "wind_speed_10m",
])

API = "https://archive-api.open-meteo.com/v1/archive"

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)

session = requests.Session()
session.headers.update({"User-Agent": "smart-agriculture-streaming-student-project/1.0"})

frames = []
metadata = []

for field_id, (lat, lon) in LOCATIONS.items():
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": START,
        "end_date": END,
        "hourly": HOURLY,
        "timezone": TIMEZONE,
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "timeformat": "iso8601",
        "cell_selection": "land",
    }

    print(f"Downloading {field_id} ...")
    r = session.get(API, params=params, timeout=120)
    r.raise_for_status()
    payload = r.json()

    if "hourly" not in payload:
        raise RuntimeError(f"No hourly data returned for {field_id}: {payload}")

    h = payload["hourly"]
    df = pd.DataFrame(h)
    df["timestamp"] = pd.to_datetime(df["time"], utc=False)
    df = df.drop(columns=["time"])
    df.insert(0, "field_id", field_id)
    df.insert(1, "latitude_requested", lat)
    df.insert(2, "longitude_requested", lon)

    # Keep returned grid-cell information for reproducibility.
    df["latitude_grid"] = payload.get("latitude")
    df["longitude_grid"] = payload.get("longitude")
    df["elevation_m"] = payload.get("elevation")
    frames.append(df)

    metadata.append({
        "field_id": field_id,
        "latitude_requested": lat,
        "longitude_requested": lon,
        "latitude_grid": payload.get("latitude"),
        "longitude_grid": payload.get("longitude"),
        "elevation_m": payload.get("elevation"),
        "timezone": payload.get("timezone"),
        "timezone_abbreviation": payload.get("timezone_abbreviation"),
        "utc_offset_seconds": payload.get("utc_offset_seconds"),
        "hourly_units": payload.get("hourly_units"),
    })
    time.sleep(0.2)

data = pd.concat(frames, ignore_index=True)
data = data.sort_values(["field_id", "timestamp"]).reset_index(drop=True)

csv_path = DATA / f"open_meteo_karnataka_{START}_to_{END}.csv"
data.to_csv(csv_path, index=False)

meta = {
    "source": "Open-Meteo Historical Weather API",
    "api": API,
    "start_date": START,
    "end_date": END,
    "timezone": TIMEZONE,
    "hourly_variables": HOURLY.split(","),
    "n_locations": len(LOCATIONS),
    "rows": int(len(data)),
    "fields": list(LOCATIONS.keys()),
    "notes": [
        "Each location is a virtual field, keyed by field_id.",
        "Leaf wetness is not downloaded; derive a clearly-labelled proxy later.",
        "NPK and pH are intentionally excluded from the core pipeline.",
        "Do not inject faults/stress events until baseline EDA is complete."
    ],
    "locations": metadata,
}
(DATA / "open_meteo_metadata.json").write_text(json.dumps(meta, indent=2))

print(f"\nSaved: {csv_path}")
print(f"Rows: {len(data):,}")
print(f"Columns: {len(data.columns)}")
print(data.groupby("field_id").size())
