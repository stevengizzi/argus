"""E2E tests for the quality pipeline through ArgusSystem._process_signal().

Exercises the real code path: SignalEvent → SetupQualityEngine.score_setup()
→ DynamicPositionSizer.calculate_shares() → RiskManager.evaluate_signal(),
with in-memory SQLite and mocked broker/data services.

Sprint 24.1, Session 2 — DEF-050.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.core.config import (
    ArgusConfig,
    BrokerSource,
    RiskConfig,
    SystemConfig,
)
from argus.core.event_bus import EventBus
from argus.core.events import (
    Event,
    OrderApprovedEvent,
    OrderRejectedEvent,
    QualitySignalEvent,
    Side,
    SignalEvent,
)
from argus.db.manager import DatabaseManager
from argus.intelligence.config import QualityEngineConfig
from argus.intelligence.position_sizer import DynamicPositionSizer
from argus.intelligence.quality_engine import SetupQualityEngine
from argus.models.trading import AccountInfo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_signal(
    *,
    symbol: str = "TSLA",
    strategy_id: str = "orb_breakout",
    entry_price: float = 150.0,
    stop_price: float = 148.0,
    pattern_strength: float = 75.0,
    share_count: int = 0,
) -> SignalEvent:
    """Build a realistic SignalEvent with share_count=0 (post-Sprint 24)."""
    return SignalEvent(
        strategy_id=strategy_id,
        symbol=symbol,
        side=Side.LONG,
        entry_price=entry_price,
        stop_price=stop_price,
        target_prices=(152.0, 154.0),
        share_count=share_count,
        rationale="ORB breakout above range high",
        pattern_strength=pattern_strength,
        signal_context={"atr_ratio": 0.8, "volume_ratio": 1.5},
    )


def _make_account(
    equity: float = 100_000.0,
    cash: float = 100_000.0,
    buying_power: float = 200_000.0,
) -> AccountInfo:
    return AccountInfo(equity=equity, cash=cash, buying_power=buying_power)


def _make_strategy_stub(allocated_capital: float = 25_000.0) -> MagicMock:
    """Create a strategy-like stub with the fields _process_signal reads."""
    strategy = MagicMock()
    strategy.allocated_capital = allocated_capital
    strategy.config.risk_limits.max_loss_per_trade_pct = 0.01
    return strategy


def _make_quality_config(
    *, enabled: bool = True, min_grade: str = "C+"
) -> QualityEngineConfig:
    return QualityEngineConfig(enabled=enabled, min_grade_to_trade=min_grade)


def _event_collector(target: list[Event]) -> Any:
    """Return an async handler that appends events to *target*."""
    async def _handler(event: Event) -> None:
        target.append(event)
    return _handler


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture()
async def db() -> DatabaseManager:
    """In-memory SQLite with full schema applied."""
    manager = DatabaseManager(":memory:")
    await manager.initialize()
    return manager


@pytest.fixture()
def mock_broker() -> AsyncMock:
    broker = AsyncMock()
    broker.get_account = AsyncMock(return_value=_make_account())
    broker.get_positions = AsyncMock(return_value=[])
    return broker


@pytest.fixture()
def risk_config() -> RiskConfig:
    return RiskConfig()


# ---------------------------------------------------------------------------
# Core helper: build a minimal ArgusSystem with real quality pipeline
# ---------------------------------------------------------------------------


async def _build_argus_system(
    *,
    event_bus: EventBus,
    db: DatabaseManager,
    broker: AsyncMock,
    risk_config: RiskConfig,
    quality_enabled: bool = True,
    min_grade: str = "C+",
    broker_source: BrokerSource = BrokerSource.IBKR,
) -> Any:
    """Construct a minimal ArgusSystem with real quality pipeline components.

    Instead of running the full ArgusSystem.__init__() + start(), we import the
    class and wire only the fields that _process_signal() touches. This avoids
    requiring Databento, IBKR, or any external service.
    """
    from argus.core.risk_manager import RiskManager
    from argus.main import ArgusSystem

    qe_config = _make_quality_config(enabled=quality_enabled, min_grade=min_grade)

    # Build config object with quality engine settings and broker source
    config = ArgusConfig(
        system=SystemConfig(
            quality_engine=qe_config,
            broker_source=broker_source,
        ),
        risk=risk_config,
    )

    # Construct ArgusSystem without calling __init__ (which reads config files).
    # We create an empty instance and populate the fields _process_signal uses.
    system = object.__new__(ArgusSystem)

    # Core components
    system._event_bus = event_bus
    system._config = config
    system._broker = broker
    system._orchestrator = None  # Falls back to MarketRegime.RANGE_BOUND
    system._catalyst_storage = None  # No catalyst data in tests
    system._db = db

    # Risk Manager (real — uses mock broker for account queries)
    rm = RiskManager(
        config=risk_config,
        broker=broker,
        event_bus=event_bus,
    )
    await rm.initialize()
    system._risk_manager = rm

    # Quality pipeline: real engine + sizer when enabled
    if quality_enabled and broker_source != BrokerSource.SIMULATED:
        system._quality_engine = SetupQualityEngine(qe_config, db_manager=db)
        system._position_sizer = DynamicPositionSizer(qe_config)
    else:
        system._quality_engine = None
        system._position_sizer = None

    return system


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestQualityPipelineHappyPath:
    """E2E: signal → score → size → RM approval."""

    @pytest.mark.asyncio
    async def test_quality_pipeline_scores_and_sizes_signal(
        self, event_bus: EventBus, db: DatabaseManager, mock_broker: AsyncMock,
        risk_config: RiskConfig,
    ) -> None:
        """Full happy path: quality engine scores, sizer calculates shares,
        signal reaches RM with quality_grade and quality_score populated."""
        system = await _build_argus_system(
            event_bus=event_bus, db=db, broker=mock_broker, risk_config=risk_config,
        )
        signal = _make_signal()
        strategy = _make_strategy_stub()

        approved_events: list[OrderApprovedEvent] = []
        quality_events: list[QualitySignalEvent] = []
        event_bus.subscribe(OrderApprovedEvent, _event_collector(approved_events))
        event_bus.subscribe(QualitySignalEvent, _event_collector(quality_events))

        await system._process_signal(signal, strategy)
        await event_bus.drain()

        # RM should have approved (with enriched signal)
        assert len(approved_events) == 1
        approved = approved_events[0]
        assert approved.signal.quality_grade != ""
        assert approved.signal.quality_score > 0
        assert approved.signal.share_count > 0

        # QualitySignalEvent published for UI consumers
        assert len(quality_events) == 1
        assert quality_events[0].grade != ""
        assert quality_events[0].score > 0

    @pytest.mark.asyncio
    async def test_quality_history_recorded_on_happy_path(
        self, event_bus: EventBus, db: DatabaseManager, mock_broker: AsyncMock,
        risk_config: RiskConfig,
    ) -> None:
        """Quality history table gets a row with shares > 0 on happy path."""
        system = await _build_argus_system(
            event_bus=event_bus, db=db, broker=mock_broker, risk_config=risk_config,
        )
        signal = _make_signal()
        strategy = _make_strategy_stub()

        await system._process_signal(signal, strategy)
        await event_bus.drain()

        cursor = await db.execute("SELECT * FROM quality_history")
        rows = await cursor.fetchall()
        assert len(rows) == 1
        row = rows[0]
        assert row["symbol"] == "TSLA"
        assert row["strategy_id"] == "orb_breakout"
        assert row["calculated_shares"] > 0
        assert row["grade"] != ""
        assert row["composite_score"] > 0

    @pytest.mark.asyncio
    async def test_quality_enrichment_reaches_risk_manager(
        self, event_bus: EventBus, db: DatabaseManager, mock_broker: AsyncMock,
        risk_config: RiskConfig,
    ) -> None:
        """RM receives signal with quality_grade and quality_score populated."""
        system = await _build_argus_system(
            event_bus=event_bus, db=db, broker=mock_broker, risk_config=risk_config,
        )
        signal = _make_signal()
        strategy = _make_strategy_stub()

        # Spy on RM's evaluate_signal to capture the enriched signal
        original_evaluate = system._risk_manager.evaluate_signal
        captured_signals: list[SignalEvent] = []

        async def spy_evaluate(sig: SignalEvent) -> Any:
            captured_signals.append(sig)
            return await original_evaluate(sig)

        system._risk_manager.evaluate_signal = spy_evaluate

        await system._process_signal(signal, strategy)
        await event_bus.drain()

        assert len(captured_signals) == 1
        enriched = captured_signals[0]
        assert enriched.quality_grade != ""
        assert enriched.quality_score > 0
        assert enriched.share_count > 0


class TestQualityPipelineBypass:
    """E2E: bypass path when quality is disabled or broker is SIMULATED."""

    @pytest.mark.asyncio
    async def test_bypass_with_quality_disabled(
        self, event_bus: EventBus, db: DatabaseManager, mock_broker: AsyncMock,
        risk_config: RiskConfig,
    ) -> None:
        """Quality disabled → legacy sizing → signal reaches RM without quality."""
        system = await _build_argus_system(
            event_bus=event_bus, db=db, broker=mock_broker, risk_config=risk_config,
            quality_enabled=False,
        )
        signal = _make_signal()
        strategy = _make_strategy_stub(allocated_capital=50_000.0)

        approved_events: list[OrderApprovedEvent] = []
        event_bus.subscribe(OrderApprovedEvent, _event_collector(approved_events))

        await system._process_signal(signal, strategy)
        await event_bus.drain()

        assert len(approved_events) == 1
        approved = approved_events[0]
        assert approved.signal.quality_grade == ""
        assert approved.signal.quality_score == 0.0
        # Legacy formula: allocated_capital * max_loss_per_trade_pct / risk_per_share
        risk_per_share = abs(signal.entry_price - signal.stop_price)  # 2.0
        expected_shares = int(50_000.0 * 0.01 / risk_per_share)  # 250
        assert approved.signal.share_count == expected_shares

    @pytest.mark.asyncio
    async def test_bypass_with_simulated_broker(
        self, event_bus: EventBus, db: DatabaseManager, mock_broker: AsyncMock,
        risk_config: RiskConfig,
    ) -> None:
        """BrokerSource.SIMULATED → bypass even if quality_engine.enabled=true."""
        system = await _build_argus_system(
            event_bus=event_bus, db=db, broker=mock_broker, risk_config=risk_config,
            quality_enabled=True,
            broker_source=BrokerSource.SIMULATED,
        )
        signal = _make_signal()
        strategy = _make_strategy_stub()

        approved_events: list[OrderApprovedEvent] = []
        event_bus.subscribe(OrderApprovedEvent, _event_collector(approved_events))

        await system._process_signal(signal, strategy)
        await event_bus.drain()

        assert len(approved_events) == 1
        assert approved_events[0].signal.quality_grade == ""
        assert approved_events[0].signal.quality_score == 0.0

    @pytest.mark.asyncio
    async def test_bypass_no_quality_history_recorded(
        self, event_bus: EventBus, db: DatabaseManager, mock_broker: AsyncMock,
        risk_config: RiskConfig,
    ) -> None:
        """Bypass path does NOT write to quality_history table."""
        system = await _build_argus_system(
            event_bus=event_bus, db=db, broker=mock_broker, risk_config=risk_config,
            quality_enabled=False,
        )
        signal = _make_signal()
        strategy = _make_strategy_stub()

        await system._process_signal(signal, strategy)
        await event_bus.drain()

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM quality_history")
        row = await cursor.fetchone()
        assert row["cnt"] == 0


class TestGradeFilter:
    """E2E: signal filtered when quality grade is below min_grade_to_trade."""

    @pytest.mark.asyncio
    async def test_low_grade_signal_filtered(
        self, event_bus: EventBus, db: DatabaseManager, mock_broker: AsyncMock,
        risk_config: RiskConfig,
    ) -> None:
        """Signal with low pattern_strength gets low grade → filtered before RM."""
        system = await _build_argus_system(
            event_bus=event_bus, db=db, broker=mock_broker, risk_config=risk_config,
            min_grade="A",  # High bar — only A or A+ pass
        )
        signal = _make_signal(pattern_strength=10.0)
        strategy = _make_strategy_stub()

        approved_events: list[OrderApprovedEvent] = []
        rejected_events: list[OrderRejectedEvent] = []
        event_bus.subscribe(OrderApprovedEvent, _event_collector(approved_events))
        event_bus.subscribe(OrderRejectedEvent, _event_collector(rejected_events))

        await system._process_signal(signal, strategy)
        await event_bus.drain()

        # Signal should NOT reach RM at all — no approved or rejected events
        assert len(approved_events) == 0
        assert len(rejected_events) == 0

    @pytest.mark.asyncio
    async def test_filtered_signal_records_quality_history_with_zero_shares(
        self, event_bus: EventBus, db: DatabaseManager, mock_broker: AsyncMock,
        risk_config: RiskConfig,
    ) -> None:
        """Filtered signal still records quality_history with shares=0."""
        system = await _build_argus_system(
            event_bus=event_bus, db=db, broker=mock_broker, risk_config=risk_config,
            min_grade="A",
        )
        signal = _make_signal(pattern_strength=10.0)
        strategy = _make_strategy_stub()

        await system._process_signal(signal, strategy)
        await event_bus.drain()

        cursor = await db.execute("SELECT * FROM quality_history")
        rows = await cursor.fetchall()
        assert len(rows) == 1
        assert rows[0]["calculated_shares"] == 0
        assert rows[0]["grade"] != ""  # Grade was computed, just below threshold


class TestEdgeCases:
    """Additional edge case tests for the quality pipeline."""

    @pytest.mark.asyncio
    async def test_zero_risk_per_share_in_bypass_yields_zero_shares(
        self, event_bus: EventBus, db: DatabaseManager, mock_broker: AsyncMock,
        risk_config: RiskConfig,
    ) -> None:
        """entry_price == stop_price in bypass path → 0 shares → RM rejects."""
        system = await _build_argus_system(
            event_bus=event_bus, db=db, broker=mock_broker, risk_config=risk_config,
            quality_enabled=False,
        )
        signal = _make_signal(entry_price=150.0, stop_price=150.0)
        strategy = _make_strategy_stub()

        rejected_events: list[OrderRejectedEvent] = []
        event_bus.subscribe(OrderRejectedEvent, _event_collector(rejected_events))

        await system._process_signal(signal, strategy)
        await event_bus.drain()

        # share_count=0 → RM Check 0 rejects
        assert len(rejected_events) == 1
        assert "zero or negative" in rejected_events[0].reason.lower()

    @pytest.mark.asyncio
    async def test_sizer_returns_zero_shares_records_history(
        self, event_bus: EventBus, db: DatabaseManager, mock_broker: AsyncMock,
        risk_config: RiskConfig,
    ) -> None:
        """When sizer returns 0 shares (e.g. no buying power), history records 0."""
        mock_broker.get_account = AsyncMock(
            return_value=_make_account(buying_power=1.0)
        )
        system = await _build_argus_system(
            event_bus=event_bus, db=db, broker=mock_broker, risk_config=risk_config,
        )
        signal = _make_signal()
        strategy = _make_strategy_stub()

        approved_events: list[OrderApprovedEvent] = []
        event_bus.subscribe(OrderApprovedEvent, _event_collector(approved_events))

        await system._process_signal(signal, strategy)
        await event_bus.drain()

        # No approval — sizer returned 0
        assert len(approved_events) == 0

        cursor = await db.execute("SELECT calculated_shares FROM quality_history")
        rows = await cursor.fetchall()
        assert len(rows) == 1
        assert rows[0]["calculated_shares"] == 0

    @pytest.mark.asyncio
    async def test_high_quality_signal_gets_larger_position(
        self, event_bus: EventBus, db: DatabaseManager, mock_broker: AsyncMock,
        risk_config: RiskConfig,
    ) -> None:
        """A+ quality signal should get larger position than B- signal."""
        results: dict[str, int] = {}

        for label, strength in [("high", 95.0), ("low", 35.0)]:
            local_bus = EventBus()
            local_db = DatabaseManager(":memory:")
            await local_db.initialize()

            system = await _build_argus_system(
                event_bus=local_bus, db=local_db, broker=mock_broker,
                risk_config=risk_config,
            )
            signal = _make_signal(pattern_strength=strength)
            strategy = _make_strategy_stub()

            approved: list[OrderApprovedEvent] = []
            local_bus.subscribe(OrderApprovedEvent, _event_collector(approved))
            await system._process_signal(signal, strategy)
            await local_bus.drain()

            if approved:
                results[label] = approved[0].signal.share_count
            else:
                results[label] = 0

            await local_db.close()

        # Higher quality → more shares (via higher risk tier)
        assert results["high"] > results["low"]
