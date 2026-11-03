---
title: "Data Provenance and Source Integrity"
description: "Rules for data tagging, source isolation, unit tracking, and preventing conflation of physical sensors with reanalysis models or external weather stations."
always_apply: true
---

# Data Provenance & Source Integrity — AgriKafka-Agent

Data integrity and scientific honesty are paramount. In agricultural decision-support, misleading a farmer or reviewer regarding the physical ground truth of an environmental reading can lead to crop loss or invalid research claims.

---

## 1. Mandatory Metadata on Every Record
Every event published to or processed by Kafka must retain:
- `event_id`: Unique UUIDv4 identifier.
- `source`: Specific provider/feed identifier (e.g., `open_meteo_archive`, `opensensemap_station_xyz`, `injected_harness`).
- `source_type`: Exactly one of:
  - `physical_sensor`
  - `weather_station`
  - `reanalysis_model`
  - `numerical_forecast`
  - `derived_calculation`
  - `historical_replay`
  - `injected_fault`
  - `injected_stress`
- `event_time`: ISO-8601 UTC timestamp of observation generation.
- `ingestion_time`: ISO-8601 UTC timestamp when Kafka ingestion accepted the record.
- `field_id`: Logical field identifier for partitioning.
- `sensor_id`: Specific physical or virtual probe identifier.
- `units`: Explicit physical measurement units (e.g., `celsius`, `percent`, `mm_per_hour`, `m3_per_m3`, `kpa`, `m_per_s`).
- `location`: Requested and actual GPS coordinates and elevation where available.
- `provenance_label`: Clear audit label distinguishing simulation from in-situ measurements.

## 2. Prohibition Against Conflating Modelled and Physical Telemetry
- **Never represent modelled/reanalysis soil moisture as a physical sensor measurement.**
  The Open-Meteo ERA5-Land reanalysis values (0–7 cm soil moisture) are gridded algorithmic estimates. They must never be displayed to a farmer or in an academic paper as ground-truth field sensor readings.
- **Never represent a remote station observation as a farmer's field probe.**
  Readings from an IMD weather station or public openSenseMap node miles away reflect local atmospheric conditions, not the specific soil or micro-climatic state of the farmer's parcel.
- Any derived variable (such as leaf wetness estimated from RH and dew point, or Crop Stress Index) must be explicitly flagged with `source_type: derived_calculation`.

## 3. Preservation of Ingestion Audit Payload
- Where practical and lawful, the raw upstream payload or reference hash must be recorded in the ingestion envelope to enable complete forensic replay and bug debugging.
