"""Connection pool management and bounded retries for TimescaleDB / PostgreSQL."""

from __future__ import annotations

import logging
import random
import time
from contextlib import contextmanager
from typing import Generator, Optional

try:
    import psycopg
    from psycopg_pool import ConnectionPool
except ImportError:
    psycopg = None  # type: ignore
    ConnectionPool = None  # type: ignore

from agri_persistence.config import DatabaseConfig, ReadOnlyDatabaseConfig

logger = logging.getLogger(__name__)


class DatabasePoolManager:
    """Manages connection pooling, lifecycle, healthchecks, and bounded retries."""

    def __init__(self, config: Optional[DatabaseConfig | ReadOnlyDatabaseConfig] = None) -> None:
        self.config = config or DatabaseConfig()
        self._pool: Optional[ConnectionPool] = None

    def open(self) -> None:
        """Initializes the connection pool if not already open."""
        if psycopg is None or ConnectionPool is None:
            raise RuntimeError("psycopg and psycopg-pool must be installed to use DatabasePoolManager.")

        if self._pool is None:
            logger.info("Initializing database connection pool to %s:%s/%s", self.config.host, self.config.port, self.config.dbname)
            self._pool = ConnectionPool(
                conninfo=self.config.conninfo,
                min_size=self.config.min_size,
                max_size=self.config.max_size,
                timeout=self.config.timeout_sec,
                open=True,
            )

    def close(self) -> None:
        """Closes all connections in the pool."""
        if self._pool is not None:
            logger.info("Closing database connection pool.")
            self._pool.close()
            self._pool = None

    def __enter__(self) -> DatabasePoolManager:
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def check_health(self) -> bool:
        """Executes a ping check against the database."""
        try:
            with self.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    result = cur.fetchone()
                    return result is not None and result[0] == 1
        except Exception as e:
            logger.warning("Database healthcheck failed: %s", e)
            return False

    @contextmanager
    def connection(self) -> Generator[psycopg.Connection, None, None]:
        """Provides a managed connection from the pool with bounded retries on transient errors."""
        if self._pool is None:
            self.open()

        assert self._pool is not None

        retries = 0
        max_retries = getattr(self.config, "max_retries", 3)
        base_delay = getattr(self.config, "retry_base_delay_sec", 0.5)
        max_delay = getattr(self.config, "retry_max_delay_sec", 5.0)

        while True:
            try:
                with self._pool.connection() as conn:
                    yield conn
                return
            except (psycopg.OperationalError, psycopg.errors.ConnectionException) as err:
                retries += 1
                if retries > max_retries:
                    logger.error("Database connection failed after %s retries: %s", retries, err)
                    raise

                delay = min(max_delay, base_delay * (2 ** (retries - 1))) + random.uniform(0, 0.1)
                logger.warning("Transient DB operational error: %s. Retrying in %.2fs (attempt %s/%s)...", err, delay, retries, max_retries)
                time.sleep(delay)

