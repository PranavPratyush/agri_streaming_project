"""AgriKafka-Agent Database Migration Runner.

Manages TimescaleDB / PostgreSQL schema migrations with up, down, status, and validate verbs.
Tracks applied versions in the `schema_migrations` table.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

try:
    import psycopg
    from psycopg import sql
except ImportError:
    psycopg = None  # type: ignore

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


@dataclass
class MigrationFile:
    version: int
    name: str
    up_path: Path
    down_path: Optional[Path] = None


def discover_migrations(migrations_dir: Path = MIGRATIONS_DIR) -> List[MigrationFile]:
    """Discovers all migration scripts in the migrations directory."""
    if not migrations_dir.exists():
        return []

    up_pattern = re.compile(r"^(\d{3})_(.+)\.up\.sql$")
    migrations_map: dict[int, MigrationFile] = {}

    for file in sorted(migrations_dir.glob("*.sql")):
        up_match = up_pattern.match(file.name)
        if up_match:
            version = int(up_match.group(1))
            name = up_match.group(2)
            down_path = migrations_dir / f"{up_match.group(1)}_{name}.down.sql"
            migrations_map[version] = MigrationFile(
                version=version,
                name=name,
                up_path=file,
                down_path=down_path if down_path.exists() else None,
            )

    return sorted(migrations_map.values(), key=lambda m: m.version)


def get_db_connection_params() -> dict[str, str | int]:
    """Reads database connection parameters from environment or safe defaults."""
    return {
        "host": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "dbname": os.environ.get("POSTGRES_DB", "agrikafka"),
        "user": os.environ.get("POSTGRES_USER", "agri_admin"),
        "password": os.environ.get("POSTGRES_PASSWORD", "agri_dev_password_insecure"),
    }


def ensure_migration_table(conn: psycopg.Connection) -> None:
    """Creates schema_migrations table if it does not already exist."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
    conn.commit()


def get_applied_migrations(conn: psycopg.Connection) -> dict[int, datetime]:
    """Retrieves applied migrations as a map of version -> applied_at."""
    ensure_migration_table(conn)
    with conn.cursor() as cur:
        cur.execute("SELECT version, applied_at FROM schema_migrations ORDER BY version ASC;")
        rows = cur.fetchall()
        return {int(row[0]): row[1] for row in rows}


def apply_migration_up(conn: psycopg.Connection, migration: MigrationFile) -> None:
    """Applies a single migration within a transaction."""
    sql_content = migration.up_path.read_text(encoding="utf-8")
    print(f"Applying migration {migration.version:03d}_{migration.name} (UP)...")

    with conn.cursor() as cur:
        cur.execute(sql_content)
        cur.execute(
            """
            INSERT INTO schema_migrations (version, name, applied_at)
            VALUES (%s, %s, now())
            ON CONFLICT (version) DO UPDATE SET name = EXCLUDED.name, applied_at = now();
            """,
            (migration.version, migration.name),
        )
    conn.commit()
    print(f"Successfully applied {migration.version:03d}_{migration.name}.")


def apply_migration_down(conn: psycopg.Connection, migration: MigrationFile) -> None:
    """Rolls back a single migration within a transaction."""
    if not migration.down_path or not migration.down_path.exists():
        raise FileNotFoundError(f"Down migration not found for version {migration.version:03d}")

    sql_content = migration.down_path.read_text(encoding="utf-8")
    print(f"Reverting migration {migration.version:03d}_{migration.name} (DOWN)...")

    with conn.cursor() as cur:
        cur.execute(sql_content)
        cur.execute("DELETE FROM schema_migrations WHERE version = %s;", (migration.version,))
    conn.commit()
    print(f"Successfully reverted {migration.version:03d}_{migration.name}.")


def cmd_up(conn: psycopg.Connection) -> int:
    """Applies all pending migrations."""
    all_migrations = discover_migrations()
    applied = get_applied_migrations(conn)

    pending = [m for m in all_migrations if m.version not in applied]
    if not pending:
        print("Database schema is up to date. No pending migrations.")
        return 0

    print(f"Found {len(pending)} pending migration(s).")
    for migration in pending:
        apply_migration_up(conn, migration)
    return 0


def cmd_down(conn: psycopg.Connection) -> int:
    """Rolls back the latest applied migration."""
    all_migrations = {m.version: m for m in discover_migrations()}
    applied = get_applied_migrations(conn)

    if not applied:
        print("No migrations have been applied. Nothing to revert.")
        return 0

    latest_version = max(applied.keys())
    migration = all_migrations.get(latest_version)
    if not migration:
        raise RuntimeError(f"Applied migration version {latest_version} not found in files.")

    apply_migration_down(conn, migration)
    return 0


def cmd_status(conn: psycopg.Connection) -> int:
    """Displays migration status (applied vs pending)."""
    all_migrations = discover_migrations()
    applied = get_applied_migrations(conn)

    print("\n--- AgriKafka-Agent Schema Migration Status ---")
    print(f"{'Version':<10} {'Name':<35} {'Status':<15} {'Applied At'}")
    print("-" * 80)

    for m in all_migrations:
        if m.version in applied:
            status = "APPLIED"
            applied_at = applied[m.version].strftime("%Y-%m-%d %H:%M:%S UTC")
        else:
            status = "PENDING"
            applied_at = "—"
        print(f"{m.version:<10} {m.name:<35} {status:<15} {applied_at}")

    print("-" * 80)
    print(f"Total: {len(all_migrations)} migrations ({len(applied)} applied, {len(all_migrations) - len(applied)} pending)\n")
    return 0


def cmd_validate() -> int:
    """Offline validation: checks migration files and SQL syntax pairing."""
    all_migrations = discover_migrations()
    print(f"Validating {len(all_migrations)} migration files in {MIGRATIONS_DIR}...")
    errors = []

    for m in all_migrations:
        if not m.up_path.exists():
            errors.append(f"Missing UP file for version {m.version}")
        if not m.down_path or not m.down_path.exists():
            errors.append(f"Missing DOWN rollback file for version {m.version} ({m.name})")

        # Basic check for empty files
        if m.up_path.stat().st_size == 0:
            errors.append(f"UP migration {m.up_path.name} is empty.")
        if m.down_path and m.down_path.stat().st_size == 0:
            errors.append(f"DOWN migration {m.down_path.name} is empty.")

    if errors:
        print("Validation FAILED:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("All migration files are paired (UP/DOWN) and non-empty. Validation PASS.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="AgriKafka-Agent TimescaleDB Schema Migrations")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("up", help="Apply all pending migrations")
    subparsers.add_parser("down", help="Roll back the latest applied migration")
    subparsers.add_parser("status", help="Show migration status")
    subparsers.add_parser("validate", help="Validate migration files offline")

    args = parser.parse_args()

    if args.command == "validate":
        return cmd_validate()

    if psycopg is None:
        print("ERROR: psycopg is required to run live database migrations.")
        print("Install via: uv pip install psycopg[binary]")
        return 1

    params = get_db_connection_params()
    try:
        with psycopg.connect(**params) as conn:
            if args.command == "up":
                return cmd_up(conn)
            elif args.command == "down":
                return cmd_down(conn)
            elif args.command == "status":
                return cmd_status(conn)
    except Exception as e:
        print(f"Database connection or migration failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

