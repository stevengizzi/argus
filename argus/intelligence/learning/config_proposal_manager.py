"""Config proposal management for the Learning Loop.

Bridges UI approval workflow to YAML config changes with full safety
guardrails. Changes are applied at application startup only (Amendment 1).
Atomic write pattern: backup → tempfile → os.rename (Amendment 9).
Cumulative drift guard prevents runaway config drift (Amendment 2).

Sprint 28, Session 4.
"""

from __future__ import annotations

import logging
import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

from argus.intelligence.config import QualityEngineConfig
from argus.intelligence.learning.learning_store import LearningStore
from argus.intelligence.learning.models import ConfigProposal, LearningLoopConfig

logger = logging.getLogger(__name__)

_DEFAULT_QE_YAML = "config/quality_engine.yaml"

# Weight dimension names that map to weights.* in quality_engine.yaml
_WEIGHT_DIMENSIONS = frozenset({
    "pattern_strength",
    "catalyst_quality",
    "volume_profile",
    "historical_match",
    "regime_alignment",
})


class ConfigProposalManager:
    """Manages config proposals from the Learning Loop.

    Applies APPROVED proposals to quality_engine.yaml at startup only.
    Validates all changes through Pydantic before writing. Uses atomic
    write pattern (backup + tempfile + os.rename) for safety.

    Args:
        config: LearningLoopConfig with guard thresholds.
        store: LearningStore for proposal and change history queries.
        quality_engine_yaml_path: Path to quality_engine.yaml.
    """

    def __init__(
        self,
        config: LearningLoopConfig,
        store: LearningStore,
        quality_engine_yaml_path: str = _DEFAULT_QE_YAML,
    ) -> None:
        self._config = config
        self._store = store
        self._yaml_path = quality_engine_yaml_path

        # Startup YAML parse check (Amendment 1)
        self._validate_yaml_parseable()

    def _validate_yaml_parseable(self) -> None:
        """Verify quality_engine.yaml can be parsed on startup.

        Raises:
            RuntimeError: If the YAML file cannot be parsed.
        """
        path = Path(self._yaml_path)
        if not path.exists():
            logger.critical(
                "quality_engine.yaml not found at %s", self._yaml_path
            )
            raise RuntimeError(
                f"quality_engine.yaml not found: {self._yaml_path}"
            )

        try:
            raw = path.read_text()
            parsed = yaml.safe_load(raw)
            if not isinstance(parsed, dict):
                raise ValueError("YAML root is not a mapping")
            # Validate through Pydantic
            QualityEngineConfig(**parsed)
        except Exception as exc:
            logger.critical(
                "Failed to parse quality_engine.yaml at %s: %s",
                self._yaml_path,
                exc,
            )
            raise RuntimeError(
                f"quality_engine.yaml parse failure: {exc}"
            ) from exc

    def _read_yaml(self) -> dict[str, object]:
        """Read and parse quality_engine.yaml.

        Returns:
            Parsed YAML as a dict.
        """
        raw = Path(self._yaml_path).read_text()
        parsed = yaml.safe_load(raw)
        if not isinstance(parsed, dict):
            raise ValueError(f"Expected YAML to parse as dict, got {type(parsed).__name__}")
        return parsed

    def _write_yaml_atomic(self, data: dict[str, object]) -> None:
        """Write YAML atomically: backup → tempfile → os.rename.

        Amendment 9: Ensures no corrupt YAML on disk at any point.

        Args:
            data: The complete YAML dict to write.
        """
        target = Path(self._yaml_path)
        backup = Path(f"{self._yaml_path}.bak")

        # Step 1: Backup current file
        if target.exists():
            backup.write_text(target.read_text())

        # Step 2: Write to tempfile in same directory (same filesystem for rename)
        dir_path = target.parent
        fd, tmp_path = tempfile.mkstemp(
            suffix=".yaml.tmp", dir=str(dir_path)
        )
        try:
            with os.fdopen(fd, "w") as f:
                yaml.safe_dump(
                    data, f, default_flow_style=False, sort_keys=False
                )

            # Step 3: Atomic rename
            os.rename(tmp_path, str(target))
        except Exception:
            # Clean up tempfile on failure
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    async def apply_pending(self) -> list[str]:
        """Apply all APPROVED proposals at startup.

        Amendment 1: Called once at application startup, not mid-session.
        Amendment 2: Cumulative drift guard stops application if next
        proposal would exceed max_cumulative_drift for any dimension.

        P1-D2-M05 (FIX-08): When a weight proposal is applied,
        ``_redistribute_weights`` proportionally adjusts the other weight
        dimensions to maintain sum-to-1.0. Pre-FIX-08 those redistribution
        deltas were never recorded in ``config_change_history``, so
        ``get_cumulative_drift(dim)`` undercounted drift on every
        redistributed dimension. Repeated promotions of dim A could
        silently push dims B/C/D/E far below their initial anchors with
        the guard never tripping. This method now snapshots weight values
        pre-redistribution and emits a separate ``record_change`` entry
        per redistributed dimension with
        ``source="learning_loop_redistribution"`` so the drift-guard query
        sees the full picture.

        Returns:
            List of proposal IDs that were applied.
        """
        approved = await self._store.get_approved_proposals()
        if not approved:
            return []

        current_yaml = self._read_yaml()
        applied_ids: list[str] = []
        # P1-D2-M05 (FIX-08): per-proposal map of {dim_name: (old_weight,
        # new_weight)} for weight dims that the redistribution step
        # modified. Used by the recording loop below.
        redistribution_deltas: dict[str, dict[str, tuple[float, float]]] = {}

        for proposal in approved:
            # Check cumulative drift guard before applying
            dimension = self._extract_dimension(proposal.field_path)
            if dimension is not None:
                current_drift = await self.get_cumulative_drift(
                    dimension,
                    self._config.cumulative_drift_window_days,
                )
                # NOTE: When processing multiple proposals in a single batch, later proposals
                # use current_value from analysis time, not post-prior-proposal values.
                # This is conservative by design — drift may be overcounted, never undercounted.
                proposed_delta = abs(proposal.proposed_value - proposal.current_value)
                if current_drift + proposed_delta > self._config.max_cumulative_drift:
                    logger.info(
                        "Cumulative drift guard: skipping proposal %s for %s "
                        "(drift %.4f + delta %.4f > limit %.4f)",
                        proposal.proposal_id,
                        dimension,
                        current_drift,
                        proposed_delta,
                        self._config.max_cumulative_drift,
                    )
                    # Proposal stays APPROVED for next cycle
                    continue

            # Apply the change to the in-memory YAML dict
            self._set_nested(current_yaml, proposal.field_path, proposal.proposed_value)

            # If this is a weight change, redistribute other weights
            # and capture the per-dim deltas so they can be recorded below.
            if proposal.field_path.startswith("weights."):
                pre_weights = self._snapshot_weights(current_yaml)
                self._redistribute_weights(current_yaml, proposal.field_path)
                post_weights = self._snapshot_weights(current_yaml)
                changed_dim = proposal.field_path.split(".", 1)[1]
                redistribution_deltas[proposal.proposal_id] = {
                    dim: (pre_weights[dim], post_weights[dim])
                    for dim in pre_weights
                    if dim != changed_dim and pre_weights[dim] != post_weights[dim]
                }

            applied_ids.append(proposal.proposal_id)

        if not applied_ids:
            return []

        # Validate the cumulative result through Pydantic
        try:
            QualityEngineConfig(**current_yaml)
        except Exception as exc:
            logger.critical(
                "Pydantic validation failed after applying %d proposals: %s. "
                "YAML unchanged, all proposals remain APPROVED.",
                len(applied_ids),
                exc,
            )
            return []

        # Atomic write
        self._write_yaml_atomic(current_yaml)

        # Update proposal statuses and record changes
        original_yaml = self._read_yaml_from_backup()
        for pid in applied_ids:
            proposal = next(p for p in approved if p.proposal_id == pid)
            await self._store.update_proposal_status(pid, "APPLIED")
            old_val = self._get_nested(original_yaml, proposal.field_path)
            old_float = float(old_val) if old_val is not None else proposal.current_value
            await self._store.record_change(
                field_path=proposal.field_path,
                old_value=old_float,
                new_value=proposal.proposed_value,
                source="learning_loop",
                proposal_id=pid,
                report_id=proposal.report_id,
            )

            # P1-D2-M05 (FIX-08): emit drift records for each redistributed
            # dim. Distinct source tag so a future drift-guard refinement
            # could weight these differently if needed; the sum-of-deltas
            # is what matters for ``get_cumulative_drift``.
            for dim, (pre, post) in redistribution_deltas.get(pid, {}).items():
                await self._store.record_change(
                    field_path=f"weights.{dim}",
                    old_value=pre,
                    new_value=post,
                    source="learning_loop_redistribution",
                    proposal_id=pid,
                    report_id=proposal.report_id,
                )

        logger.info("Applied %d config proposals at startup", len(applied_ids))
        return applied_ids

    @staticmethod
    def _snapshot_weights(yaml_data: dict[str, object]) -> dict[str, float]:
        """Snapshot current weight values from the in-memory YAML dict.

        Used by ``apply_pending`` to capture pre- and post-redistribution
        weight values for drift-record emission (P1-D2-M05).
        """
        weights = yaml_data.get("weights")
        if not isinstance(weights, dict):
            return {}
        return {
            str(dim): float(weights.get(dim, 0.0)) for dim in _WEIGHT_DIMENSIONS
        }

    def validate_proposal(
        self, proposal: ConfigProposal
    ) -> tuple[bool, str]:
        """Validate a proposal against safety guards.

        Checks max_change_per_cycle and weight sum-to-1.0 constraints.

        Args:
            proposal: The ConfigProposal to validate.

        Returns:
            Tuple of (valid, explanation).
        """
        # Check max_change_per_cycle
        delta = abs(proposal.proposed_value - proposal.current_value)
        if delta > self._config.max_weight_change_per_cycle:
            return (
                False,
                f"Change delta {delta:.4f} exceeds "
                f"max_change_per_cycle {self._config.max_weight_change_per_cycle:.4f}",
            )

        # Check weight sum-to-1.0 with redistribution
        if proposal.field_path.startswith("weights."):
            current_yaml = self._read_yaml()
            weights = current_yaml.get("weights", {})
            if not isinstance(weights, dict):
                raise ValueError(f"Expected weights to be a dict, got {type(weights).__name__}")

            dimension = proposal.field_path.split(".", 1)[1]
            if dimension not in _WEIGHT_DIMENSIONS:
                return (False, f"Unknown weight dimension: {dimension}")

            # Simulate redistribution
            new_weights = dict(weights)
            new_weights[dimension] = proposal.proposed_value

            # Proportional redistribution of other weights
            other_dims = [d for d in _WEIGHT_DIMENSIONS if d != dimension]
            remaining = 1.0 - proposal.proposed_value
            other_sum = sum(float(new_weights[d]) for d in other_dims)

            if other_sum <= 0:
                return (False, "Cannot redistribute: all other weights are zero")

            for d in other_dims:
                new_weights[d] = float(new_weights[d]) / other_sum * remaining
                if new_weights[d] < 0.01:
                    return (
                        False,
                        f"Redistribution would push {d} weight below 0.01 "
                        f"({new_weights[d]:.4f})",
                    )

        return (True, "Proposal passes all validation checks")

    async def apply_single_change(
        self,
        field_path: str,
        new_value: float,
    ) -> None:
        """Apply a single config change (for reverts).

        Reads current YAML, applies the change, validates through Pydantic,
        and writes atomically. Records in change history with source="revert".
        Takes effect on next restart.

        Args:
            field_path: Config field path (e.g., "weights.pattern_strength").
            new_value: The value to set.

        Raises:
            ValueError: If Pydantic validation fails after the change.
        """
        current_yaml = self._read_yaml()
        old_value = self._get_nested(current_yaml, field_path)
        old_float = float(old_value) if old_value is not None else 0.0

        self._set_nested(current_yaml, field_path, new_value)

        # If weight change, redistribute
        if field_path.startswith("weights."):
            self._redistribute_weights(current_yaml, field_path)

        # Validate
        try:
            QualityEngineConfig(**current_yaml)
        except Exception as exc:
            raise ValueError(
                f"Pydantic validation failed after revert: {exc}"
            ) from exc

        # Atomic write
        self._write_yaml_atomic(current_yaml)

        # Record in change history
        await self._store.record_change(
            field_path=field_path,
            old_value=old_float,
            new_value=new_value,
            source="revert",
        )

        logger.info(
            "Applied revert: %s = %.4f (was %.4f)",
            field_path,
            new_value,
            old_float,
        )

    async def get_cumulative_drift(
        self, dimension: str, window_days: int
    ) -> float:
        """Get cumulative absolute drift for a dimension over a rolling window.

        Args:
            dimension: Weight dimension name (e.g., "pattern_strength").
            window_days: Number of days for the rolling window.

        Returns:
            Cumulative absolute drift as a float.
        """
        start = datetime.now(UTC) - timedelta(days=window_days)
        changes = await self._store.get_change_history(start_date=start)

        field_path = f"weights.{dimension}"
        total_drift = 0.0
        for change in changes:
            if change.get("field_path") == field_path:
                old = float(change["old_value"])  # type: ignore[arg-type]
                new = float(change["new_value"])  # type: ignore[arg-type]
                total_drift += abs(new - old)

        return total_drift

    # --- Internal helpers ---

    @staticmethod
    def _extract_dimension(field_path: str) -> str | None:
        """Extract the dimension name from a field_path like 'weights.X'.

        Args:
            field_path: Config field path.

        Returns:
            Dimension name or None if not a weight field.
        """
        if field_path.startswith("weights."):
            dim = field_path.split(".", 1)[1]
            if dim in _WEIGHT_DIMENSIONS:
                return dim
        return None

    @staticmethod
    def _get_nested(data: dict[str, object], field_path: str) -> object:
        """Get a nested value from a dict using dot-separated path.

        Args:
            data: The dict to traverse.
            field_path: Dot-separated path (e.g., "weights.pattern_strength").

        Returns:
            The value at the path, or None if not found.
        """
        parts = field_path.split(".")
        current: object = data
        for part in parts:
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current

    @staticmethod
    def _set_nested(data: dict[str, object], field_path: str, value: object) -> None:
        """Set a nested value in a dict using dot-separated path.

        Args:
            data: The dict to modify.
            field_path: Dot-separated path.
            value: The value to set.
        """
        parts = field_path.split(".")
        current = data
        for part in parts[:-1]:
            child = current.get(part)
            if not isinstance(child, dict):
                child = {}
                current[part] = child
            current = child
        current[parts[-1]] = value

    @staticmethod
    def _redistribute_weights(
        yaml_data: dict[str, object], changed_field_path: str
    ) -> None:
        """Redistribute other weights proportionally to maintain sum-to-1.0.

        Args:
            yaml_data: The full YAML dict (modified in place).
            changed_field_path: The field_path that was changed (e.g., "weights.X").
        """
        weights = yaml_data.get("weights")
        if not isinstance(weights, dict):
            return

        changed_dim = changed_field_path.split(".", 1)[1]
        new_value = float(weights[changed_dim])
        remaining = 1.0 - new_value

        other_dims = [d for d in _WEIGHT_DIMENSIONS if d != changed_dim]
        other_sum = sum(float(weights.get(d, 0.0)) for d in other_dims)

        if other_sum <= 0:
            # Distribute equally if all others are zero
            equal_share = remaining / len(other_dims)
            for d in other_dims:
                weights[d] = round(equal_share, 6)
        else:
            for d in other_dims:
                proportion = float(weights.get(d, 0.0)) / other_sum
                weights[d] = round(proportion * remaining, 6)

    def _read_yaml_from_backup(self) -> dict[str, object]:
        """Read the backup YAML file.

        Returns:
            Parsed backup YAML as dict, or empty dict if no backup.
        """
        backup = Path(f"{self._yaml_path}.bak")
        if not backup.exists():
            return {}
        raw = backup.read_text()
        parsed = yaml.safe_load(raw)
        if isinstance(parsed, dict):
            return parsed
        return {}
