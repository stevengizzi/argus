"""Slippage model calibration from real execution records.

Queries execution_records to produce per-strategy slippage models with
time-of-day and order-size adjustments. Used by BacktestEngine for
calibrated fills instead of fixed assumptions (Sprint 27.5 S5).
"""

from __future__ import annotations

import json
import logging
import tempfile
from dataclasses import dataclass
from datetime import datetime, time, timezone
from enum import StrEnum
from pathlib import Path

from argus.db.manager import DatabaseManager

logger = logging.getLogger(__name__)

__all__ = [
    "SlippageConfidence",
    "StrategySlippageModel",
    "calibrate_slippage_model",
    "save_slippage_model",
    "load_slippage_model",
]


class SlippageConfidence(StrEnum):
    """Confidence level based on execution record sample size."""

    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    INSUFFICIENT = "insufficient"


def _confidence_from_count(count: int) -> SlippageConfidence:
    """Determine confidence tier from sample count.

    Args:
        count: Number of execution records.

    Returns:
        Appropriate confidence tier.
    """
    if count >= 50:
        return SlippageConfidence.HIGH
    if count >= 20:
        return SlippageConfidence.MODERATE
    if count >= 5:
        return SlippageConfidence.LOW
    return SlippageConfidence.INSUFFICIENT


def _mean(values: list[float]) -> float:
    """Compute arithmetic mean.

    Args:
        values: Non-empty list of floats.

    Returns:
        Mean value.
    """
    return sum(values) / len(values)


def _std_dev(values: list[float], mean_val: float) -> float:
    """Compute population standard deviation.

    Args:
        values: Non-empty list of floats.
        mean_val: Pre-computed mean of values.

    Returns:
        Standard deviation.
    """
    variance = sum((v - mean_val) ** 2 for v in values) / len(values)
    return variance**0.5


def _linear_regression_slope(x_values: list[float], y_values: list[float]) -> float:
    """Compute slope of simple linear regression (y = a + bx).

    Uses least-squares: slope = Σ(xi - x̄)(yi - ȳ) / Σ(xi - x̄)²

    Args:
        x_values: Independent variable values.
        y_values: Dependent variable values.

    Returns:
        Regression slope, or 0.0 if insufficient variation.
    """
    n = len(x_values)
    if n < 2:
        return 0.0

    x_mean = _mean(x_values)
    y_mean = _mean(y_values)

    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    denominator = sum((x - x_mean) ** 2 for x in x_values)

    if denominator == 0.0:
        return 0.0

    return numerator / denominator


# Time-of-day bucket boundaries (Eastern Time)
_PRE_10AM = time(10, 0)
_POST_2PM = time(14, 0)


def _time_bucket(time_of_day_str: str) -> str:
    """Classify a time-of-day string into a bucket.

    Args:
        time_of_day_str: Time string in HH:MM:SS format (Eastern Time).

    Returns:
        Bucket key: "pre_10am", "10am_2pm", or "post_2pm".
    """
    t = time.fromisoformat(time_of_day_str)
    if t < _PRE_10AM:
        return "pre_10am"
    if t < _POST_2PM:
        return "10am_2pm"
    return "post_2pm"


@dataclass
class StrategySlippageModel:
    """Per-strategy slippage model calibrated from execution records.

    Attributes:
        strategy_id: Strategy this model was calibrated for.
        estimated_mean_slippage_bps: Mean observed slippage in basis points.
        estimated_std_slippage_bps: Standard deviation of slippage in bps.
        time_of_day_adjustment: Additive bps adjustment per time bucket.
        size_adjustment_slope: Additional bps per 100 shares order size.
        sample_count: Number of execution records used for calibration.
        confidence: Confidence tier based on sample count.
        last_calibrated: Timestamp of last calibration.
    """

    strategy_id: str
    estimated_mean_slippage_bps: float
    estimated_std_slippage_bps: float
    time_of_day_adjustment: dict[str, float]
    size_adjustment_slope: float
    sample_count: int
    confidence: SlippageConfidence
    last_calibrated: datetime

    def to_dict(self) -> dict[str, object]:
        """Serialize model to a JSON-compatible dictionary.

        Returns:
            Dictionary representation of the model.
        """
        return {
            "strategy_id": self.strategy_id,
            "estimated_mean_slippage_bps": self.estimated_mean_slippage_bps,
            "estimated_std_slippage_bps": self.estimated_std_slippage_bps,
            "time_of_day_adjustment": self.time_of_day_adjustment,
            "size_adjustment_slope": self.size_adjustment_slope,
            "sample_count": self.sample_count,
            "confidence": self.confidence.value,
            "last_calibrated": self.last_calibrated.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> StrategySlippageModel:
        """Deserialize model from a dictionary.

        Args:
            data: Dictionary previously produced by to_dict().

        Returns:
            Reconstructed StrategySlippageModel.

        Raises:
            KeyError: If required fields are missing.
            ValueError: If field values are invalid.
        """
        strategy_id = str(data["strategy_id"])
        estimated_mean = float(data["estimated_mean_slippage_bps"])  # type: ignore[arg-type]
        estimated_std = float(data["estimated_std_slippage_bps"])  # type: ignore[arg-type]
        tod_raw = data["time_of_day_adjustment"]
        if not isinstance(tod_raw, dict):
            raise ValueError("time_of_day_adjustment must be a dict")
        time_of_day_adjustment = {str(k): float(v) for k, v in tod_raw.items()}
        size_slope = float(data["size_adjustment_slope"])  # type: ignore[arg-type]
        sample_count = int(data["sample_count"])  # type: ignore[arg-type]
        confidence = SlippageConfidence(str(data["confidence"]))
        last_calibrated = datetime.fromisoformat(str(data["last_calibrated"]))

        return cls(
            strategy_id=strategy_id,
            estimated_mean_slippage_bps=estimated_mean,
            estimated_std_slippage_bps=estimated_std,
            time_of_day_adjustment=time_of_day_adjustment,
            size_adjustment_slope=size_slope,
            sample_count=sample_count,
            confidence=confidence,
            last_calibrated=last_calibrated,
        )


def _zeroed_model(strategy_id: str, sample_count: int) -> StrategySlippageModel:
    """Create a zeroed-out model for insufficient data.

    Args:
        strategy_id: Strategy identifier.
        sample_count: Actual record count (will be <5).

    Returns:
        Model with all-zero values and INSUFFICIENT confidence.
    """
    return StrategySlippageModel(
        strategy_id=strategy_id,
        estimated_mean_slippage_bps=0.0,
        estimated_std_slippage_bps=0.0,
        time_of_day_adjustment={"pre_10am": 0.0, "10am_2pm": 0.0, "post_2pm": 0.0},
        size_adjustment_slope=0.0,
        sample_count=sample_count,
        confidence=SlippageConfidence.INSUFFICIENT,
        last_calibrated=datetime.now(timezone.utc),
    )


async def calibrate_slippage_model(
    db_manager: DatabaseManager, strategy_id: str
) -> StrategySlippageModel:
    """Calibrate a slippage model from execution records.

    Queries the execution_records table for the given strategy and computes
    mean slippage, time-of-day adjustments, and size-dependent slope.

    Args:
        db_manager: Initialized DatabaseManager instance.
        strategy_id: Strategy to calibrate.

    Returns:
        Calibrated StrategySlippageModel with appropriate confidence tier.
    """
    rows = await db_manager.fetch_all(
        "SELECT actual_slippage_bps, time_of_day, order_size_shares "
        "FROM execution_records WHERE strategy_id = ?",
        (strategy_id,),
    )

    sample_count = len(rows)

    if sample_count < 5:
        return _zeroed_model(strategy_id, sample_count)

    slippage_values = [float(row["actual_slippage_bps"]) for row in rows]
    overall_mean = _mean(slippage_values)
    overall_std = _std_dev(slippage_values, overall_mean)

    # Time-of-day adjustment: bucket mean - overall mean
    buckets: dict[str, list[float]] = {"pre_10am": [], "10am_2pm": [], "post_2pm": []}
    for row in rows:
        bucket = _time_bucket(str(row["time_of_day"]))
        buckets[bucket].append(float(row["actual_slippage_bps"]))

    time_of_day_adjustment: dict[str, float] = {}
    for bucket_name, bucket_values in buckets.items():
        if len(bucket_values) < 3:
            time_of_day_adjustment[bucket_name] = 0.0
        else:
            time_of_day_adjustment[bucket_name] = _mean(bucket_values) - overall_mean

    # Size adjustment: linear regression of slippage on (order_size / 100)
    size_values = [float(row["order_size_shares"]) / 100.0 for row in rows]
    size_std = _std_dev(size_values, _mean(size_values))

    if size_std > 0.0:
        size_adjustment_slope = _linear_regression_slope(size_values, slippage_values)
    else:
        size_adjustment_slope = 0.0

    confidence = _confidence_from_count(sample_count)

    return StrategySlippageModel(
        strategy_id=strategy_id,
        estimated_mean_slippage_bps=overall_mean,
        estimated_std_slippage_bps=overall_std,
        time_of_day_adjustment=time_of_day_adjustment,
        size_adjustment_slope=size_adjustment_slope,
        sample_count=sample_count,
        confidence=confidence,
        last_calibrated=datetime.now(timezone.utc),
    )


def save_slippage_model(model: StrategySlippageModel, path: str) -> None:
    """Persist a slippage model to a JSON file.

    Uses atomic write (temp file + rename) to prevent partial writes.

    Args:
        model: The calibrated model to save.
        path: Destination file path.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write: write to temp file in same directory, then rename
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=str(target.parent),
        suffix=".tmp",
        delete=False,
    ) as tmp_file:
        json.dump(model.to_dict(), tmp_file, indent=2)
        tmp_path = Path(tmp_file.name)

    tmp_path.rename(target)
    logger.info("Slippage model saved: %s (%d records)", path, model.sample_count)


def load_slippage_model(path: str) -> StrategySlippageModel:
    """Load a slippage model from a JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        Deserialized StrategySlippageModel.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the JSON is malformed or missing required fields.
    """
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Slippage model file not found: {path}")

    try:
        data = json.loads(target.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in slippage model file: {path}") from exc

    try:
        return StrategySlippageModel.from_dict(data)
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Invalid slippage model data in {path}: {exc}") from exc
