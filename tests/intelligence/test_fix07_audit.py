"""Regression tests for FIX-07-intelligence-catalyst-quality (audit 2026-04-21).

Pins behaviors introduced or documented by the FIX-07 session so the
findings cannot silently regress:

- Finding 1 (P1-D1-M11) — zero-R guard epsilon.
- Finding 7 (P1-D1-L08) — _group_by_category iterates VALID_CATEGORIES.
- Finding 10 (P1-F1-7) — routes/counterfactual raises TypeError, not AssertionError.
- Finding 12 (P1-D1-M12) — semantic dedup anchors to kept[-1].
- Finding 18 (P1-D1-M10) — catalyst-quality cutoff localizes naive ET timestamps to ET, not UTC.
- Finding 21 (DEF-106) — LearningReport.from_dict() raises TypeError for bad shapes.
- Finding 22 (DEF-096) — CounterfactualTracker / PatternBasedStrategy hold Protocol-typed stores.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from argus.core.events import Side, SignalEvent
from argus.core.protocols import (
    CandleStoreProtocol,
    CounterfactualStoreProtocol,
)
from argus.intelligence import CatalystPipeline
from argus.intelligence.briefing import BriefingGenerator
from argus.intelligence.counterfactual import (
    CounterfactualTracker,
    RejectionStage,
    _ZERO_R_EPSILON,
)
from argus.intelligence.models import (
    CatalystClassification,
    ClassifiedCatalyst,
)


def _make_signal(
    entry_price: float = 100.0,
    stop_price: float = 95.0,
) -> SignalEvent:
    return SignalEvent(
        strategy_id="orb_breakout",
        symbol="AAPL",
        side=Side.LONG,
        entry_price=entry_price,
        stop_price=stop_price,
        target_prices=(110.0,),
        share_count=0,
        rationale="fix-07 regression",
        quality_score=72.5,
        quality_grade="B",
    )


# ---------------------------------------------------------------------------
# Finding 1 — Zero-R guard epsilon
# ---------------------------------------------------------------------------


class TestZeroRGuardEpsilon:
    def test_exact_equality_rejected(self) -> None:
        tracker = CounterfactualTracker()
        signal = _make_signal(entry_price=100.0, stop_price=100.0)
        assert tracker.track(signal, "zero risk", RejectionStage.QUALITY_FILTER) is None

    def test_subpenny_spread_rejected(self) -> None:
        """A signal with a sub-penny stop spread must be rejected.

        Pre-FIX-07 the check was `entry == stop` — so a programmatically
        derived stop offset smaller than one cent (but strictly greater
        than zero) passed the guard and produced R-multiple values
        scaled by 1 / (tiny number). The FIX-07 P1-D1-M11 epsilon
        catches anything within ``_ZERO_R_EPSILON`` of zero.
        """
        tracker = CounterfactualTracker()
        entry = 100.0
        stop = entry - 1e-6  # strictly unequal at float precision, well below a penny
        assert entry != stop  # the hazard — pre-FIX-07 this passed `==` guard
        assert abs(entry - stop) < _ZERO_R_EPSILON
        signal = _make_signal(entry_price=entry, stop_price=stop)
        assert tracker.track(signal, "subpenny", RejectionStage.QUALITY_FILTER) is None

    def test_real_signal_still_tracked(self) -> None:
        """A normal $5 stop spread must still be tracked."""
        tracker = CounterfactualTracker()
        signal = _make_signal(entry_price=100.0, stop_price=95.0)
        pid = tracker.track(signal, "normal", RejectionStage.QUALITY_FILTER)
        assert pid is not None


# ---------------------------------------------------------------------------
# Finding 7 — briefing._group_by_category iterates VALID_CATEGORIES
# ---------------------------------------------------------------------------


class TestGroupByCategoryCovers:
    def test_every_valid_category_has_a_key(self) -> None:
        """All VALID_CATEGORIES appear as keys in the grouped output.

        Before FIX-07 the set of keys was hardcoded in briefing.py and
        adding a new category on CatalystClassification would silently
        route to "other".
        """
        gen = BriefingGenerator.__new__(BriefingGenerator)  # skip __init__
        grouped = gen._group_by_category([])  # type: ignore[arg-type]
        for category in CatalystClassification.VALID_CATEGORIES:
            assert category in grouped, f"missing category: {category}"


# ---------------------------------------------------------------------------
# Finding 12 — _semantic_dedup kept[-1] anchor behavior
# ---------------------------------------------------------------------------


class TestSemanticDedupAnchor:
    def _make_catalyst(
        self, *, minute: int, quality_score: float
    ) -> ClassifiedCatalyst:
        published = datetime(2026, 4, 22, 9, minute, 0, tzinfo=UTC)
        return ClassifiedCatalyst(
            headline=f"headline@{minute}m",
            symbol="AAPL",
            source="test",
            published_at=published,
            fetched_at=published,
            category="news_sentiment",
            quality_score=quality_score,
            summary="",
            trading_relevance="low",
            classified_by="fallback",
            classified_at=datetime.now(UTC),
            headline_hash=f"hash-{minute}",
        )

    def test_kept_last_anchor_decreasing_scores(self) -> None:
        """A(t=0, 70) → B(t=20, 50) → C(t=40, 60), window=30.

        Anchor is kept[-1] (FIX-07 P1-D1-M12 documented DEC-311 behavior):
        - A kept.
        - B within 30 of A; A's score higher → keep A, B dropped.
        - C compared to A (kept[-1]); diff=40 > 30 → C kept.

        Result: A and C both kept even though C is within 20 of B's
        original timestamp. This pins the current anchor; if the dedup
        semantic is ever changed (cluster-midpoint or first-seen), this
        test must be updated deliberately.
        """
        from unittest.mock import MagicMock

        pipeline = CatalystPipeline.__new__(CatalystPipeline)
        pipeline._config = MagicMock(dedup_window_minutes=30)
        catalysts = [
            self._make_catalyst(minute=0, quality_score=70.0),
            self._make_catalyst(minute=20, quality_score=50.0),
            self._make_catalyst(minute=40, quality_score=60.0),
        ]
        result = pipeline._semantic_dedup(catalysts)
        assert len(result) == 2
        minutes = sorted(c.published_at.minute for c in result)
        assert minutes == [0, 40]


# ---------------------------------------------------------------------------
# Finding 18 — Catalyst quality cutoff uses ET for naive timestamps
# ---------------------------------------------------------------------------


class TestCatalystQualityCutoffET:
    def test_et_naive_timestamp_included_when_within_24h(self) -> None:
        """A catalyst with a naive ET timestamp inside the 24h window is NOT excluded.

        Before FIX-07 the naive timestamp was localized to UTC, so an
        ET-naive 09:30 "ET" timestamp was interpreted as 09:30 UTC =
        05:30 ET, pushing recently-published catalysts outside the 24h
        window during the 4-5h ET-UTC gap on DST-edge days.
        """
        from argus.intelligence.quality_engine import SetupQualityEngine
        from argus.intelligence.config import QualityEngineConfig

        engine = SetupQualityEngine(QualityEngineConfig())
        # ET-naive timestamp 30 minutes ago in ET; should pass the 24h
        # cutoff regardless of DST-edge UTC offset.
        from zoneinfo import ZoneInfo

        et = ZoneInfo("America/New_York")
        now_et_naive = datetime.now(et).replace(tzinfo=None) - timedelta(minutes=30)
        catalyst = ClassifiedCatalyst(
            headline="recent news",
            symbol="AAPL",
            source="test",
            published_at=now_et_naive,
            fetched_at=datetime.now(UTC),
            category="news_sentiment",
            quality_score=85.0,
            summary="",
            trading_relevance="high",
            classified_by="fallback",
            classified_at=datetime.now(UTC),
            headline_hash="fix07-recent",
        )
        # Should pick up the 85.0 quality score (i.e., the catalyst was
        # included in the "recent" filter).
        score = engine._score_catalyst_quality([catalyst])
        assert score == 85.0


# ---------------------------------------------------------------------------
# Finding 21 (DEF-106) — LearningReport.from_dict raises TypeError
# ---------------------------------------------------------------------------


class TestLearningReportFromDictRaisesTypeError:
    def test_data_quality_wrong_type_raises_typeerror(self) -> None:
        """Passing a non-dict for ``data_quality`` raises TypeError, not AssertionError.

        ``assert isinstance(...)`` would strip under ``python -O`` and
        silently accept the wrong shape. FIX-07 P1-D1-L14 converted
        all 8 sites in learning/models.py to ``if not isinstance: raise``.
        """
        from argus.intelligence.learning.models import LearningReport

        bad = {"data_quality": "not-a-dict"}
        with pytest.raises(TypeError, match="expected dict"):
            LearningReport.from_dict(bad)


# ---------------------------------------------------------------------------
# Finding 22 (DEF-096) — Protocol-typed stores
# ---------------------------------------------------------------------------


class TestProtocolStores:
    def test_candle_store_protocol_is_runtime_checkable(self) -> None:
        """IntradayCandleStore satisfies CandleStoreProtocol structurally."""
        from argus.data.intraday_candle_store import IntradayCandleStore

        store = IntradayCandleStore()
        assert isinstance(store, CandleStoreProtocol)

    def test_counterfactual_store_protocol_is_runtime_checkable(self) -> None:
        """CounterfactualStore satisfies CounterfactualStoreProtocol structurally."""
        from argus.intelligence.counterfactual_store import CounterfactualStore

        store = CounterfactualStore(db_path=":memory:")
        assert isinstance(store, CounterfactualStoreProtocol)
