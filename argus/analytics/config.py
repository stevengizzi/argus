"""Pydantic configuration models for the analytics layer.

Provides typed, validated config for the observatory: section
in system.yaml and system_live.yaml.

Sprint 25, Session 1.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ObservatoryConfig(BaseModel):
    """Configuration for The Observatory pipeline visualization page.

    Attributes:
        enabled: Whether Observatory endpoints are active.
        ws_update_interval_ms: WebSocket push interval in milliseconds.
        timeline_bucket_seconds: Timeline view event bucketing interval.
        matrix_max_rows: Maximum rows rendered in Matrix view.
        debrief_retention_days: Days of historical data available in Debrief mode.
    """

    enabled: bool = True
    ws_update_interval_ms: int = Field(default=1000, ge=100)
    timeline_bucket_seconds: int = Field(default=60, ge=1)
    matrix_max_rows: int = Field(default=100, ge=10)
    debrief_retention_days: int = Field(default=7, ge=1)
