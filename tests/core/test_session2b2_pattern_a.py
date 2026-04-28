"""Sprint 31.91 Session 2b.2 — Pattern A.2 (RiskManager max-concurrent) + Pattern A.4 (Health hybrid).

Pattern A.2: side-aware count filter on ``RiskManager.evaluate_signal``'s
max-concurrent-positions gate. Phantom shorts (DEF-204) must not consume
slots reserved for legitimate longs.

Pattern A.4 hybrid: Health daily integrity check splits broker positions
into longs (existing 'Integrity Check FAILED' alert path, with Option C
cross-reference to ``stranded_broker_long`` if active) and shorts
(``phantom_short`` SystemAlertEvent via Session 2b.1's taxonomy).

Tests:
- A.2 base case: 49 longs + 5 shorts, max=50 → entry NOT rejected.
- A.2 phantom-short B5 regression: 0 longs + 50 shorts, max=50 →
  entry NOT rejected (the foundational anti-regression that proves the
  pre-fix lock-out is gone).
- A.4 long-orphan no-stop → existing alert fires; no phantom_short.
- A.4 broker-side short → phantom_short SystemAlertEvent fires;
  no Integrity Check FAILED alert (no longs without stops).
- A.4 mixed: log breakdown line is operator-readable.
- A.4 + Option C cross-reference: long-orphan + active stranded_broker_long
  → cross-reference text appended to the alert body.

Spec note (RULE-038): The Sprint 31.91 Session 2b.2 implementation prompt
referenced a 'second max-concurrent-positions site at risk_manager.py:771'.
Grep confirmed the file has exactly ONE max-concurrent check (at line 337);
line 771 is inside the ``daily_integrity_check`` docstring and does not
enforce any cap. Tests for the non-existent second site are therefore
omitted; Test 5 (B5 regression) covers the structural fix at the single
real site.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.core.clock import FixedClock
from argus.core.config import (
    AccountRiskConfig,
    AccountType,
    CrossStrategyRiskConfig,
    DuplicateStockPolicy,
    HealthConfig,
    PDTConfig,
    RiskConfig,
)
from argus.core.event_bus import EventBus
from argus.core.events import OrderRejectedEvent, Side, SignalEvent, SystemAlertEvent
from argus.core.health import HealthMonitor
from argus.core.risk_manager import RiskManager
from argus.models.trading import OrderSide, Position


# ---------------------------------------------------------------------------
# Risk Manager Pattern A.2 helpers
# ---------------------------------------------------------------------------


def _make_signal(
    symbol: str = "AAPL",
    side: Side = Side.LONG,
    entry_price: float = 150.0,
    stop_price: float = 147.0,
    share_count: int = 100,
    strategy_id: str = "strat_orb_breakout",
) -> SignalEvent:
    return SignalEvent(
        strategy_id=strategy_id,
        symbol=symbol,
        side=side,
        entry_price=entry_price,
        stop_price=stop_price,
        target_prices=(153.0, 156.0),
        share_count=share_count,
        rationale="Test signal — Sprint 31.91 S2b.2",
    )


def _make_risk_config(max_concurrent_positions: int = 50) -> RiskConfig:
    return RiskConfig(
        account=AccountRiskConfig(
            daily_loss_limit_pct=0.03,
            weekly_loss_limit_pct=0.05,
            cash_reserve_pct=0.20,
            max_concurrent_positions=max_concurrent_positions,
            min_position_risk_dollars=100.0,
        ),
        cross_strategy=CrossStrategyRiskConfig(
            max_single_stock_pct=0.05,
            duplicate_stock_policy=DuplicateStockPolicy.ALLOW_ALL,
        ),
        pdt=PDTConfig(
            enabled=True,
            account_type=AccountType.MARGIN,
            threshold_balance=25_000.0,
        ),
    )


def _make_position_mock(symbol: str, side: OrderSide) -> MagicMock:
    pos = MagicMock(spec=Position)
    pos.symbol = symbol
    pos.shares = 100
    pos.side = side
    return pos


def _make_broker_with_positions(positions: list[MagicMock]) -> MagicMock:
    broker = MagicMock()
    broker.get_positions = AsyncMock(return_value=positions)

    # Account / equity surface for the rest of evaluate_signal
    account = MagicMock()
    account.equity = 1_000_000.0
    account.cash = 500_000.0
    account.buying_power = 1_500_000.0
    broker.get_account = AsyncMock(return_value=account)

    return broker


def _fixed_clock() -> FixedClock:
    return FixedClock(datetime(2026, 4, 28, 15, 0, 0, tzinfo=UTC))


# ---------------------------------------------------------------------------
# Pattern A.2 — Risk Manager max-concurrent
# ---------------------------------------------------------------------------


class TestPatternA2RiskManagerMaxConcurrent:
    """Side-aware long-only filter on the max-concurrent gate.

    Note (RULE-038): only one max-concurrent site exists in
    ``risk_manager.py`` (line 337). The spec's reference to a second site
    at line 771 is a grep-disproven authoring drift; tests are scoped to
    the single real site.
    """

    @pytest.mark.asyncio
    async def test_max_concurrent_uses_longs_only(self) -> None:
        """49 longs + 5 shorts, max=50 → entry NOT rejected on max-concurrent.

        Without the fix, ``len(positions)=54 >= 50`` would reject. With the
        fix, ``len(longs)=49 < 50`` lets the signal through to subsequent
        checks. We assert specifically that the rejection (if any) is NOT
        the max-concurrent rejection.
        """
        positions = [
            _make_position_mock(f"LONG{i}", OrderSide.BUY) for i in range(49)
        ] + [
            _make_position_mock(f"SHORT{i}", OrderSide.SELL) for i in range(5)
        ]
        broker = _make_broker_with_positions(positions)

        bus = EventBus()
        rm = RiskManager(
            config=_make_risk_config(max_concurrent_positions=50),
            broker=broker,
            event_bus=bus,
            clock=_fixed_clock(),
        )

        result = await rm.evaluate_signal(_make_signal(symbol="NEWLONG"))

        # The crucial assertion: NOT rejected for max-concurrent.
        if isinstance(result, OrderRejectedEvent):
            assert "concurrent positions" not in result.reason.lower(), (
                f"Signal was rejected for max-concurrent despite long_count=49 < 50; "
                f"reason: {result.reason}"
            )

    @pytest.mark.asyncio
    async def test_max_concurrent_phantom_shorts_dont_consume_position_cap(self) -> None:
        """B5 regression: 0 longs + 50 phantom shorts, max=50 → NOT rejected.

        This is the foundational anti-regression for DEF-204. Pre-fix,
        ARGUS would lock itself out of taking ANY new long when the
        broker reported 50 phantom shorts. With Pattern A.2, the 50
        shorts are correctly excluded from the cap.
        """
        positions = [
            _make_position_mock(f"PHANTOM{i}", OrderSide.SELL) for i in range(50)
        ]
        broker = _make_broker_with_positions(positions)

        bus = EventBus()
        rm = RiskManager(
            config=_make_risk_config(max_concurrent_positions=50),
            broker=broker,
            event_bus=bus,
            clock=_fixed_clock(),
        )

        result = await rm.evaluate_signal(_make_signal(symbol="LEGITLONG"))

        if isinstance(result, OrderRejectedEvent):
            assert "concurrent positions" not in result.reason.lower(), (
                f"DEF-204 REGRESSION: 50 phantom shorts blocked a legitimate long. "
                f"Reason: {result.reason}"
            )

    @pytest.mark.asyncio
    async def test_max_concurrent_logs_breakdown_line(
        self, caplog: pytest.LogCaptureFixture,
    ) -> None:
        """The INFO breakdown line surfaces longs / shorts / cap / would_reject."""
        positions = [
            _make_position_mock(f"LONG{i}", OrderSide.BUY) for i in range(20)
        ] + [
            _make_position_mock(f"SHORT{i}", OrderSide.SELL) for i in range(3)
        ]
        broker = _make_broker_with_positions(positions)

        bus = EventBus()
        rm = RiskManager(
            config=_make_risk_config(max_concurrent_positions=50),
            broker=broker,
            event_bus=bus,
            clock=_fixed_clock(),
        )

        with caplog.at_level(logging.INFO, logger="argus.core.risk_manager"):
            await rm.evaluate_signal(_make_signal())

        breakdown = [
            r.getMessage() for r in caplog.records
            if "Risk Manager max-concurrent #1" in r.getMessage()
        ]
        assert breakdown, "Expected an INFO breakdown line at the entry gate"
        msg = breakdown[0]
        assert "longs=20" in msg
        assert "shorts=3" in msg
        assert "max_concurrent=50" in msg
        assert "would_reject=False" in msg

    @pytest.mark.asyncio
    async def test_max_concurrent_rejects_when_longs_at_cap(self) -> None:
        """Non-regression: a fully-loaded long book still triggers rejection.

        50 longs + 0 shorts, max=50 → rejected with the standard
        max-concurrent reason. This guards against an inverted comparator.
        """
        positions = [
            _make_position_mock(f"LONG{i}", OrderSide.BUY) for i in range(50)
        ]
        broker = _make_broker_with_positions(positions)

        bus = EventBus()
        rm = RiskManager(
            config=_make_risk_config(max_concurrent_positions=50),
            broker=broker,
            event_bus=bus,
            clock=_fixed_clock(),
        )

        result = await rm.evaluate_signal(_make_signal(symbol="OVERFLOW"))
        assert isinstance(result, OrderRejectedEvent)
        assert "concurrent positions" in result.reason.lower()


# ---------------------------------------------------------------------------
# Pattern A.4 — Health daily integrity check (hybrid)
# ---------------------------------------------------------------------------


def _make_health_position(symbol: str, side: OrderSide, shares: int = 100) -> MagicMock:
    pos = MagicMock()
    pos.symbol = symbol
    pos.side = side
    pos.shares = shares
    return pos


def _make_health_config() -> HealthConfig:
    return HealthConfig(
        heartbeat_interval_seconds=60,
        heartbeat_url_env="",
        alert_webhook_url_env="",
    )


class _AlertCapture:
    """Subscribe to SystemAlertEvent and record everything that passes."""

    def __init__(self, bus: EventBus) -> None:
        self.events: list[SystemAlertEvent] = []
        bus.subscribe(SystemAlertEvent, self._on_alert)

    async def _on_alert(self, evt: SystemAlertEvent) -> None:
        self.events.append(evt)


class TestPatternA4HealthIntegrityCheckHybrid:

    @pytest.mark.asyncio
    async def test_long_orphan_no_stop_emits_existing_alert(self) -> None:
        """1 long without stop, 0 shorts → 'Integrity Check FAILED' fires;
        NO phantom_short alert."""
        event_bus = EventBus()
        capture = _AlertCapture(event_bus)
        clock = _fixed_clock()

        long_pos = _make_health_position("AAPL", OrderSide.BUY)
        broker = AsyncMock()
        broker.get_positions = AsyncMock(return_value=[long_pos])
        broker.get_open_orders = AsyncMock(return_value=[])  # no stop

        with patch.dict(
            os.environ, {"TEST_ALERT_URL": "https://webhook.example.com/alert"}
        ):
            config = HealthConfig(
                heartbeat_interval_seconds=60,
                heartbeat_url_env="",
                alert_webhook_url_env="TEST_ALERT_URL",
            )
            hm = HealthMonitor(
                event_bus=event_bus, clock=clock, config=config, broker=broker,
            )

            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_session.post.return_value.__aenter__.return_value = mock_response
                mock_session_class.return_value.__aenter__.return_value = mock_session

                await hm._run_daily_integrity_check()
                await event_bus.drain()

                # Existing alert fires
                assert mock_session.post.called
                payload = mock_session.post.call_args[1]["json"]
                assert "Integrity Check FAILED" in payload["title"]
                assert "AAPL" in payload["body"]

        # No phantom_short event (no shorts present)
        phantom = [e for e in capture.events if e.alert_type == "phantom_short"]
        assert phantom == []

    @pytest.mark.asyncio
    async def test_short_routes_to_phantom_short_alert(self) -> None:
        """0 longs, 1 short → phantom_short SystemAlertEvent published;
        no 'Integrity Check FAILED' alert (no longs without stops)."""
        event_bus = EventBus()
        capture = _AlertCapture(event_bus)
        clock = _fixed_clock()

        short_pos = _make_health_position("FAKE", OrderSide.SELL, shares=42)
        broker = AsyncMock()
        broker.get_positions = AsyncMock(return_value=[short_pos])
        broker.get_open_orders = AsyncMock(return_value=[])

        config = _make_health_config()
        hm = HealthMonitor(
            event_bus=event_bus, clock=clock, config=config, broker=broker,
        )

        await hm._run_daily_integrity_check()
        await event_bus.drain()

        phantom = [e for e in capture.events if e.alert_type == "phantom_short"]
        assert len(phantom) == 1
        alert = phantom[0]
        assert alert.severity == "critical"
        assert alert.source == "health.integrity_check"
        assert "FAKE" in alert.message
        assert alert.metadata is not None
        assert alert.metadata["symbol"] == "FAKE"
        assert alert.metadata["shares"] == 42
        assert alert.metadata["side"] == "SELL"
        assert alert.metadata["detection_source"] == "health.integrity_check"

    @pytest.mark.asyncio
    async def test_log_breakdown_longs_protected_shorts_phantom(
        self, caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Mixed positions: log line surfaces longs(without_stop) + shorts."""
        event_bus = EventBus()
        clock = _fixed_clock()

        long_with = _make_health_position("L1", OrderSide.BUY)
        long_with2 = _make_health_position("L2", OrderSide.BUY)
        long_without = _make_health_position("L3", OrderSide.BUY)
        short1 = _make_health_position("S1", OrderSide.SELL)
        short2 = _make_health_position("S2", OrderSide.SELL)

        broker = AsyncMock()
        broker.get_positions = AsyncMock(
            return_value=[long_with, long_with2, long_without, short1, short2]
        )
        # Stops exist for L1 + L2 only
        stop_l1 = MagicMock()
        stop_l1.symbol = "L1"
        stop_l1.order_type = "stop"
        stop_l2 = MagicMock()
        stop_l2.symbol = "L2"
        stop_l2.order_type = "stop"
        broker.get_open_orders = AsyncMock(return_value=[stop_l1, stop_l2])

        hm = HealthMonitor(
            event_bus=event_bus,
            clock=clock,
            config=_make_health_config(),
            broker=broker,
        )

        with caplog.at_level(logging.INFO, logger="argus.core.health"):
            await hm._run_daily_integrity_check()
            await event_bus.drain()

        breakdown = [
            r.getMessage() for r in caplog.records
            if "Health integrity check:" in r.getMessage()
        ]
        assert breakdown, "Expected the INFO breakdown line"
        msg = breakdown[0]
        assert "longs=3" in msg
        assert "without_stop=1" in msg
        assert "shorts=2" in msg
        assert "all phantom by long-only design" in msg
        assert "total_broker=5" in msg

    @pytest.mark.asyncio
    async def test_long_orphan_with_active_stranded_alert_includes_cross_reference(
        self,
    ) -> None:
        """Option C: when OrderManager has an active stranded_broker_long
        alert for the symbol, the integrity-check alert body cites it."""
        event_bus = EventBus()
        capture = _AlertCapture(event_bus)
        clock = _fixed_clock()

        long_orphan = _make_health_position("AAPL", OrderSide.BUY)
        broker = AsyncMock()
        broker.get_positions = AsyncMock(return_value=[long_orphan])
        broker.get_open_orders = AsyncMock(return_value=[])

        # Stand-in for OrderManager with the cycle map populated
        fake_om = MagicMock()
        fake_om._broker_orphan_last_alerted_cycle = {"AAPL": 6}

        with patch.dict(
            os.environ, {"TEST_ALERT_URL": "https://webhook.example.com/alert"}
        ):
            config = HealthConfig(
                heartbeat_interval_seconds=60,
                heartbeat_url_env="",
                alert_webhook_url_env="TEST_ALERT_URL",
            )
            hm = HealthMonitor(
                event_bus=event_bus, clock=clock, config=config, broker=broker,
            )
            hm.set_order_manager(fake_om)

            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_session.post.return_value.__aenter__.return_value = mock_response
                mock_session_class.return_value.__aenter__.return_value = mock_session

                await hm._run_daily_integrity_check()
                await event_bus.drain()

                payload = mock_session.post.call_args[1]["json"]
                body = payload["body"]
                assert "AAPL" in body
                assert "see also stranded_broker_long" in body
                assert "cycle 6" in body

    @pytest.mark.asyncio
    async def test_long_orphan_without_active_stranded_alert_omits_cross_reference(
        self,
    ) -> None:
        """No active stranded_broker_long → no spurious cross-reference text."""
        event_bus = EventBus()
        clock = _fixed_clock()

        long_orphan = _make_health_position("AAPL", OrderSide.BUY)
        broker = AsyncMock()
        broker.get_positions = AsyncMock(return_value=[long_orphan])
        broker.get_open_orders = AsyncMock(return_value=[])

        fake_om = MagicMock()
        fake_om._broker_orphan_last_alerted_cycle = {}  # empty

        with patch.dict(
            os.environ, {"TEST_ALERT_URL": "https://webhook.example.com/alert"}
        ):
            config = HealthConfig(
                heartbeat_interval_seconds=60,
                heartbeat_url_env="",
                alert_webhook_url_env="TEST_ALERT_URL",
            )
            hm = HealthMonitor(
                event_bus=event_bus, clock=clock, config=config, broker=broker,
            )
            hm.set_order_manager(fake_om)

            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_session.post.return_value.__aenter__.return_value = mock_response
                mock_session_class.return_value.__aenter__.return_value = mock_session

                await hm._run_daily_integrity_check()
                await event_bus.drain()

                payload = mock_session.post.call_args[1]["json"]
                body = payload["body"]
                assert "AAPL" in body
                assert "see also stranded_broker_long" not in body
                assert "cross-reference" not in body.lower()
