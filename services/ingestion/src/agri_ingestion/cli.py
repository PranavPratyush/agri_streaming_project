"""Unified CLI entrypoint for AgriKafka-Agent Ingestion Service."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time

from agri_ingestion.adapters.historical_replay import HistoricalReplayAdapter
from agri_ingestion.adapters.injected_scenarios import InjectedScenarioAdapter
from agri_ingestion.adapters.live_opensensemap import OpenSenseMapAdapter
from agri_ingestion.adapters.openmeteo_context import OpenMeteoContextAdapter
from agri_ingestion.config import IngestionConfig
from agri_ingestion.metrics import METRICS
from agri_ingestion.producer import AgriKafkaProducer


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def handle_live_osm(args: argparse.Namespace, config: IngestionConfig) -> int:
    producer = AgriKafkaProducer(config=config, dry_run=args.dry_run)
    adapter = OpenSenseMapAdapter(
        station_id=args.station_id,
        config=config,
        producer=producer,
        dry_run=args.dry_run,
    )

    if args.once:
        count = adapter.poll_once()
        print(f"Polled {count} observations from station {args.station_id} (dry_run={args.dry_run}).")
        if args.dry_run:
            print(json.dumps([h["data"].model_dump(mode="json") for h in producer.get_published_history()], indent=2))
        return 0

    adapter.start()
    print(f"Running continuous live polling for station {args.station_id} (interval={args.interval}s)...")
    try:
        while adapter.is_running:
            adapter.poll_once()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        adapter.stop()
    return 0


def handle_weather_context(args: argparse.Namespace, config: IngestionConfig) -> int:
    producer = AgriKafkaProducer(config=config, dry_run=args.dry_run)
    adapter = OpenMeteoContextAdapter(
        lat=args.lat,
        lon=args.lon,
        field_id=args.field_id,
        config=config,
        producer=producer,
        dry_run=args.dry_run,
    )

    if args.once:
        count = adapter.poll_once()
        print(f"Polled {count} weather context events for {args.field_id} (dry_run={args.dry_run}).")
        if args.dry_run:
            print(json.dumps([h["data"].model_dump(mode="json") for h in producer.get_published_history()], indent=2))
        return 0

    adapter.start()
    print(f"Running continuous weather polling for {args.field_id} (interval={args.interval}s)...")
    try:
        while adapter.is_running:
            adapter.poll_once()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        adapter.stop()
    return 0


def handle_replay(args: argparse.Namespace, config: IngestionConfig) -> int:
    producer = AgriKafkaProducer(config=config, dry_run=args.dry_run)
    adapter = HistoricalReplayAdapter(
        csv_path=args.csv_path,
        speed_multiplier=args.speed,
        field_filter=args.fields,
        start_date=args.start_date,
        end_date=args.end_date,
        config=config,
        producer=producer,
        dry_run=args.dry_run,
    )

    print(
        f"Starting historical replay from {args.csv_path} (speed={args.speed}x, max_rows={args.max_rows}, dry_run={args.dry_run})..."
    )
    total = adapter.run_replay(max_rows=args.max_rows)
    print(f"Replay completed! Emitted {total} events.")
    return 0


def handle_inject(args: argparse.Namespace, config: IngestionConfig) -> int:
    producer = AgriKafkaProducer(config=config, dry_run=args.dry_run)
    adapter = InjectedScenarioAdapter(
        scenario_type=args.scenario,
        field_id=args.field_id,
        steps=args.steps,
        config=config,
        producer=producer,
        dry_run=args.dry_run,
    )

    print(f"Injecting scenario '{args.scenario}' with {args.steps} steps into field '{args.field_id}'...")
    count = adapter.poll_once()
    print(f"Injected {count} events successfully (dry_run={args.dry_run}).")
    if args.dry_run:
        print(json.dumps([h["data"].model_dump(mode="json") for h in producer.get_published_history()], indent=2))
    return 0


def handle_status(args: argparse.Namespace, config: IngestionConfig) -> int:
    print("=== AgriKafka-Agent Ingestion Service Status ===")
    print(f"Bootstrap Servers: {config.bootstrap_servers}")
    print(f"Observations Topic: {config.topic_raw_observations}")
    print(f"Weather Topic:      {config.topic_weather_data}")
    print(f"DLQ Topic:          {config.topic_dead_letter}")
    print(f"Metrics Topic:      {config.topic_operational_metrics}")
    print("\nSource Cadence & Limits:")
    print("  - openSenseMap: Verified cadence 15-45s, limit ~1 req/sec (public citizen-science API, 0 cost)")
    print("  - Open-Meteo Context: Cadence 15 min, rate limit 10,000 calls/day (free tier, 0 cost)")
    print("  - Historical Replay: Configurable 1x to 3600x, deterministic hourly pacing")
    print("  - Injected Scenarios: 8 labeled benchmark scenarios (0 external network dependency)")
    print("\nTelemetry Snapshot:")
    print(json.dumps(METRICS.snapshot(), indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="agri-ingestion",
        description="AgriKafka-Agent Ingestion Service: Live Connectors, Replay, and Injected Harness",
    )
    parser.add_argument("--bootstrap-server", default=None, help="Kafka bootstrap server address")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. live-osm
    p_osm = subparsers.add_parser("live-osm", help="Poll openSenseMap live physical station")
    p_osm.add_argument("--station-id", default="689b2bdc569c2d0007586ae9", help="openSenseMap box ID")
    p_osm.add_argument("--interval", type=float, default=30.0, help="Polling interval in seconds")
    p_osm.add_argument("--once", action="store_true", help="Poll once and exit")
    p_osm.add_argument("--dry-run", action="store_true", help="Print events without publishing to Kafka")

    # 2. weather-context
    p_weather = subparsers.add_parser("weather-context", help="Poll Open-Meteo for regional weather context")
    p_weather.add_argument("--lat", type=float, default=13.137, help="Latitude")
    p_weather.add_argument("--lon", type=float, default=78.129, help="Longitude")
    p_weather.add_argument("--field-id", default="FIELD-KA-KOLAR-001", help="Target field identifier")
    p_weather.add_argument("--interval", type=float, default=900.0, help="Polling interval in seconds")
    p_weather.add_argument("--once", action="store_true", help="Poll once and exit")
    p_weather.add_argument("--dry-run", action="store_true", help="Print events without publishing to Kafka")

    # 3. replay
    p_replay = subparsers.add_parser("replay", help="Replay historical Open-Meteo dataset")
    p_replay.add_argument(
        "--csv-path",
        default="data/open_meteo_karnataka_2024-10-05_to_2026-10-04.csv",
        help="Path to historical CSV",
    )
    p_replay.add_argument("--speed", type=float, default=3600.0, help="Speed multiplier (3600 = 1hr/sec)")
    p_replay.add_argument("--fields", nargs="+", default=None, help="Specific field IDs to replay")
    p_replay.add_argument("--start-date", default=None, help="Start date (YYYY-MM-DD)")
    p_replay.add_argument("--end-date", default=None, help="End date (YYYY-MM-DD)")
    p_replay.add_argument("--max-rows", type=int, default=None, help="Maximum rows to process")
    p_replay.add_argument("--dry-run", action="store_true", help="Parse without publishing to Kafka")

    # 4. inject
    p_inject = subparsers.add_parser("inject", help="Inject deterministic stress/fault scenario")
    p_inject.add_argument(
        "--scenario",
        default="drought_drydown_ragi",
        choices=InjectedScenarioAdapter.SCENARIO_TYPES,
        help="Scenario type to inject",
    )
    p_inject.add_argument("--field-id", default="FIELD-KA-KOLAR-001", help="Target field ID")
    p_inject.add_argument("--steps", type=int, default=10, help="Number of simulated hourly steps")
    p_inject.add_argument("--dry-run", action="store_true", help="Generate without publishing to Kafka")

    # 5. status
    subparsers.add_parser("status", help="Show ingestion service configuration and metrics")

    args = parser.parse_args()
    setup_logging(args.verbose)

    config = IngestionConfig()
    if args.bootstrap_server:
        config.bootstrap_servers = args.bootstrap_server

    if args.command == "live-osm":
        return handle_live_osm(args, config)
    elif args.command == "weather-context":
        return handle_weather_context(args, config)
    elif args.command == "replay":
        return handle_replay(args, config)
    elif args.command == "inject":
        return handle_inject(args, config)
    elif args.command == "status":
        return handle_status(args, config)
    return 0


if __name__ == "__main__":
    sys.exit(main())

