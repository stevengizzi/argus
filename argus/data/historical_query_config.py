"""Historical Query Service configuration model.

Pydantic config for the DuckDB-based read-only analytical layer
over ARGUS's Parquet historical cache.

Sprint 31A.5, Session 1.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class HistoricalQueryConfig(BaseModel):
    """Configuration for the DuckDB-backed historical query service.

    Gates the service and controls DuckDB resource limits.
    All operations are read-only; the Parquet cache is never modified.

    Attributes:
        enabled: Whether the service should be initialized at startup.
        cache_dir: Path to the Databento Parquet cache directory.
        max_memory_mb: DuckDB in-memory working set limit (MB).
        default_threads: Number of DuckDB worker threads.
    """

    enabled: bool = False
    # Sprint 31.85 activation (FIX-06 audit 2026-04-21, P1-C2-6): default points
    # at the consolidated cache so that if the ``historical_query.yaml`` overlay
    # is ever missing or cleared, the runtime still lands on the fast path.
    # ``data/databento_cache/`` is the read-only source of truth for
    # ``BacktestEngine`` only — never point ``HistoricalQueryService`` at it.
    cache_dir: str = "data/databento_cache_consolidated"
    max_memory_mb: int = Field(default=2048, gt=0, description="DuckDB memory limit in MB")
    default_threads: int = Field(default=4, gt=0, description="DuckDB worker thread count")

    persist_path: str | None = Field(
        default=None,
        description=(
            "Path to persistent DuckDB database file. When set, the VIEW is "
            "created once and survives across invocations. When None, uses "
            "in-memory mode (legacy behavior)."
        ),
    )

    @field_validator("cache_dir")
    @classmethod
    def validate_cache_dir_non_empty(cls, v: str) -> str:
        """Ensure cache_dir is not blank."""
        if not v.strip():
            raise ValueError("cache_dir must not be empty")
        return v
