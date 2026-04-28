"""ARGUS schema migration framework.

Sprint 31.91 Session 5a.2 (MEDIUM #9). Pluggable, append-only forward
migrations keyed by ``schema_name`` in a ``schema_version`` table that
lives alongside each managed database. Future schema changes register a
``Migration`` object instead of executing ad-hoc ``CREATE TABLE`` /
``ALTER TABLE`` statements at random call sites.

Production does NOT auto-rollback. The ``down`` callable on each
migration is advisory only — present to document the inverse operation
for manual recovery.
"""

from __future__ import annotations

from argus.data.migrations.framework import (
    Migration,
    apply_migrations,
    current_version,
)

__all__ = ["Migration", "apply_migrations", "current_version"]
