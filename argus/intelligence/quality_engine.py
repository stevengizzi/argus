"""Setup quality scoring engine for the ARGUS intelligence layer.

Stateless, synchronous scorer. All inputs passed as arguments — no IO.
Optionally records quality history to the database.

Sprint 24, Sessions 4 + 6a.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import yaml

from argus.core.events import SignalEvent
from argus.core.ids import generate_id
from argus.core.regime import MarketRegime
from argus.intelligence.config import QualityEngineConfig
from argus.intelligence.models import ClassifiedCatalyst

if TYPE_CHECKING:
    from argus.db.manager import DatabaseManager

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")

_DEFAULT_QE_YAML = "config/quality_engine.yaml"


def load_quality_engine_config(
    yaml_path: str = _DEFAULT_QE_YAML,
) -> QualityEngineConfig:
    """Read quality_engine.yaml and return a fresh QualityEngineConfig.

    Used by ConfigProposalManager for validation and by tests. NOT used
    at runtime — the running QE instance is NOT swapped (Amendment 1).

    Args:
        yaml_path: Path to the quality_engine.yaml file.

    Returns:
        A new QualityEngineConfig instance parsed from the YAML file.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
        ValueError: If the YAML content fails Pydantic validation.
    """
    from pathlib import Path

    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"quality_engine.yaml not found: {yaml_path}")

    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"quality_engine.yaml root is not a mapping: {yaml_path}")

    return QualityEngineConfig(**raw)


@dataclass(frozen=True)
class SetupQuality:
    """Composite quality score for a trade setup."""

    score: float
    grade: str
    risk_tier: str
    components: dict[str, float]
    rationale: str


class SetupQualityEngine:
    """Scores trade setups across five quality dimensions."""

    def __init__(
        self, config: QualityEngineConfig, db_manager: DatabaseManager | None = None
    ) -> None:
        self._config = config
        self._db = db_manager

    @property
    def db(self) -> DatabaseManager | None:
        """Public accessor for database manager."""
        return self._db

    @property
    def config(self) -> QualityEngineConfig:
        """Public accessor for quality engine config."""
        return self._config

    def score_setup(
        self,
        signal: SignalEvent,
        catalysts: list[ClassifiedCatalyst],
        rvol: float | None,
        regime: MarketRegime,
        allowed_regimes: list[str],
    ) -> SetupQuality:
        """Score a trade setup and return a composite SetupQuality."""
        components = {
            "pattern_strength": self._score_pattern_strength(signal),
            "catalyst_quality": self._score_catalyst_quality(catalysts),
            "volume_profile": self._score_volume_profile(rvol),
            "historical_match": self._score_historical_match(),
            "regime_alignment": self._score_regime_alignment(regime, allowed_regimes),
        }
        weights = self._config.weights
        score = sum(components[k] * weights.get(k, 0.2) for k in components)
        grade = self._grade_from_score(score)
        return SetupQuality(
            score=round(score, 1),
            grade=grade,
            risk_tier=self._risk_tier_from_grade(grade),
            components=components,
            rationale=self._build_rationale(components, round(score, 1), grade),
        )

    def _score_pattern_strength(self, signal: SignalEvent) -> float:
        return max(0.0, min(100.0, signal.pattern_strength))

    def _score_catalyst_quality(self, catalysts: list[ClassifiedCatalyst]) -> float:
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        recent = [
            c for c in catalysts
            if (c.published_at if c.published_at.tzinfo else c.published_at.replace(tzinfo=UTC))
            >= cutoff
        ]
        if not recent:
            return 50.0
        return max(0.0, min(100.0, max(c.quality_score for c in recent)))

    def _score_volume_profile(self, rvol: float | None) -> float:
        if rvol is None:
            return 50.0
        breakpoints = [(0.5, 10.0), (1.0, 40.0), (2.0, 70.0), (3.0, 95.0)]
        if rvol <= breakpoints[0][0]:
            return breakpoints[0][1]
        if rvol >= breakpoints[-1][0]:
            return breakpoints[-1][1]
        for i in range(len(breakpoints) - 1):
            x0, y0 = breakpoints[i]
            x1, y1 = breakpoints[i + 1]
            if x0 <= rvol <= x1:
                t = (rvol - x0) / (x1 - x0)
                return y0 + t * (y1 - y0)
        return 50.0

    def _score_historical_match(self) -> float:
        return 50.0

    def _score_regime_alignment(
        self, regime: MarketRegime, allowed_regimes: list[str]
    ) -> float:
        # FUTURE (post-Sprint 28): When strategies specify phase-space conditions in
        # their operating conditions, the regime_alignment dimension (10% weight) can
        # incorporate VIX regime phase and momentum. Currently dormant — new dimensions
        # are match-any, so regime_alignment score is unchanged.
        if not allowed_regimes:
            return 70.0
        if regime.value in allowed_regimes:
            return 80.0
        return 20.0

    def _grade_from_score(self, score: float) -> str:
        t = self._config.thresholds
        if score >= t.a_plus:
            return "A+"
        if score >= t.a:
            return "A"
        if score >= t.a_minus:
            return "A-"
        if score >= t.b_plus:
            return "B+"
        if score >= t.b:
            return "B"
        if score >= t.b_minus:
            return "B-"
        if score >= t.c_plus:
            return "C+"
        return "C"

    def _risk_tier_from_grade(self, grade: str) -> str:
        return grade

    def _build_rationale(
        self, components: dict, score: float, grade: str
    ) -> str:
        ps = components["pattern_strength"]
        cq = components["catalyst_quality"]
        vp = components["volume_profile"]
        hm = components["historical_match"]
        ra = components["regime_alignment"]
        return (
            f"PS:{ps:.0f} CQ:{cq:.0f} VP:{vp:.0f} HM:{hm:.0f} RA:{ra:.0f}"
            f" \u2192 Score:{score} ({grade})"
        )

    async def record_quality_history(
        self, signal: SignalEvent, quality: SetupQuality, shares: int = 0
    ) -> None:
        """Persist quality scoring result to quality_history table.

        Records the full component breakdown, composite score, grade, and
        execution parameters for every scored signal — whether traded or not.

        Args:
            signal: The scored SignalEvent.
            quality: The SetupQuality result from score_setup().
            shares: Calculated share count (0 if filtered/skipped).
        """
        if self._db is None:
            return

        scored_at = datetime.now(_ET).isoformat()
        row_id = generate_id()
        context_json = json.dumps(signal.signal_context) if signal.signal_context else None

        await self._db.execute(
            """
            INSERT INTO quality_history (
                id, symbol, strategy_id, scored_at,
                pattern_strength, catalyst_quality, volume_profile,
                historical_match, regime_alignment,
                composite_score, grade, risk_tier,
                entry_price, stop_price, calculated_shares,
                signal_context
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                signal.symbol,
                signal.strategy_id,
                scored_at,
                quality.components["pattern_strength"],
                quality.components["catalyst_quality"],
                quality.components["volume_profile"],
                quality.components["historical_match"],
                quality.components["regime_alignment"],
                quality.score,
                quality.grade,
                quality.risk_tier,
                signal.entry_price,
                signal.stop_price,
                shares,
                context_json,
            ),
        )
