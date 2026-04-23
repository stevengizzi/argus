"""Tests for Sprint 32 S3 — Runtime Wiring.

Covers:
  1. All 7 patterns constructed via factory when given their real YAML configs
  2. PatternBasedStrategy carries config_fingerprint after factory wiring
  3. _create_pattern_by_name supports all 7 patterns (DEF-121 resolved)
  4. _load_pattern_config maps all 7 names to the correct config type
  5. Trade.config_fingerprint field exists and round-trips through TradeLogger
  6. Historical trade records (without fingerprint) remain queryable
  7. Fingerprint is deterministic: same config → same hash
  8. Fingerprint is param-sensitive: changing a detection param changes hash
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import pytest

from argus.core.config import (
    ABCDConfig,
    BullFlagConfig,
    DipAndRipConfig,
    FlatTopBreakoutConfig,
    GapAndGoConfig,
    HODBreakConfig,
    PreMarketHighBreakConfig,
    load_abcd_config,
    load_bull_flag_config,
    load_dip_and_rip_config,
    load_flat_top_breakout_config,
    load_gap_and_go_config,
    load_hod_break_config,
    load_premarket_high_break_config,
)
from argus.strategies.patterns.factory import (
    build_pattern_from_config,
    compute_parameter_fingerprint,
    get_pattern_class,
)
from argus.strategies.patterns.base import PatternModule
from argus.strategies.pattern_strategy import PatternBasedStrategy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_FIELDS = {"strategy_id": "test", "name": "Test Strategy"}
_CONFIG_DIR = Path(__file__).parent.parent / "config" / "strategies"

_ALL_PATTERNS: list[tuple[str, object]] = [
    ("bull_flag", BullFlagConfig(**_BASE_FIELDS)),  # type: ignore[arg-type]
    ("flat_top_breakout", FlatTopBreakoutConfig(**_BASE_FIELDS)),  # type: ignore[arg-type]
    ("dip_and_rip", DipAndRipConfig(**_BASE_FIELDS)),  # type: ignore[arg-type]
    ("hod_break", HODBreakConfig(**_BASE_FIELDS)),  # type: ignore[arg-type]
    ("gap_and_go", GapAndGoConfig(**_BASE_FIELDS)),  # type: ignore[arg-type]
    ("abcd", ABCDConfig(**_BASE_FIELDS)),  # type: ignore[arg-type]
    ("premarket_high_break", PreMarketHighBreakConfig(**_BASE_FIELDS)),  # type: ignore[arg-type]
]

_YAML_LOADERS = {
    "bull_flag": load_bull_flag_config,
    "flat_top_breakout": load_flat_top_breakout_config,
    "dip_and_rip": load_dip_and_rip_config,
    "hod_break": load_hod_break_config,
    "gap_and_go": load_gap_and_go_config,
    "abcd": load_abcd_config,
    "premarket_high_break": load_premarket_high_break_config,
}


def _make_pattern_strategy(pattern_name: str) -> PatternBasedStrategy:
    """Build a PatternBasedStrategy using the factory, mirroring main.py wiring."""
    config_dict = {**_BASE_FIELDS}
    config: object

    if pattern_name == "bull_flag":
        config = BullFlagConfig(**config_dict)  # type: ignore[arg-type]
    elif pattern_name == "flat_top_breakout":
        config = FlatTopBreakoutConfig(**config_dict)  # type: ignore[arg-type]
    elif pattern_name == "dip_and_rip":
        config = DipAndRipConfig(**config_dict)  # type: ignore[arg-type]
    elif pattern_name == "hod_break":
        config = HODBreakConfig(**config_dict)  # type: ignore[arg-type]
    elif pattern_name == "gap_and_go":
        config = GapAndGoConfig(**config_dict)  # type: ignore[arg-type]
    elif pattern_name == "abcd":
        config = ABCDConfig(**config_dict)  # type: ignore[arg-type]
    elif pattern_name == "premarket_high_break":
        config = PreMarketHighBreakConfig(**config_dict)  # type: ignore[arg-type]
    else:
        raise ValueError(f"Unknown pattern: {pattern_name}")

    pattern = build_pattern_from_config(config, pattern_name)  # type: ignore[arg-type]
    strategy = PatternBasedStrategy(pattern=pattern, config=config)  # type: ignore[arg-type]
    strategy._config_fingerprint = compute_parameter_fingerprint(
        config, get_pattern_class(pattern_name)  # type: ignore[arg-type]
    )
    return strategy


# ---------------------------------------------------------------------------
# Test 1: All 7 patterns instantiate via factory
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pattern_name,config", _ALL_PATTERNS)
def test_all_7_patterns_build_via_factory(pattern_name: str, config: object) -> None:
    pattern = build_pattern_from_config(config, pattern_name)  # type: ignore[arg-type]
    assert isinstance(pattern, PatternModule)
    assert pattern.name  # non-empty name string


# ---------------------------------------------------------------------------
# Test 2: PatternBasedStrategy carries fingerprint after factory wiring
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pattern_name,config", _ALL_PATTERNS)
def test_pattern_strategy_carries_fingerprint(pattern_name: str, config: object) -> None:
    strategy = _make_pattern_strategy(pattern_name)
    fp = strategy.config_fingerprint
    assert fp is not None
    assert len(fp) == 16
    assert all(c in "0123456789abcdef" for c in fp)


# ---------------------------------------------------------------------------
# Test 3: build_pattern_from_config supports all 7 patterns (DEF-121 resolved)
# FIX-09 P1-E2-M01: migrated from the now-retired
# ``argus.backtest.vectorbt_pattern._create_pattern_by_name`` helper to
# the canonical factory in ``argus.strategies.patterns.factory``.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pattern_name", list(_YAML_LOADERS.keys()))
def test_build_pattern_from_config_all_7(pattern_name: str) -> None:
    yaml_path = _CONFIG_DIR / f"{pattern_name}.yaml"
    if not yaml_path.exists():
        pytest.skip(f"Config file not found: {yaml_path}")

    loader = _YAML_LOADERS[pattern_name]
    config = loader(yaml_path)
    pattern = build_pattern_from_config(config, pattern_name)
    assert isinstance(pattern, PatternModule)


# ---------------------------------------------------------------------------
# Test 4: Per-pattern YAML loader returns the correct config type
# FIX-09 P1-E2-M01: migrated from the now-retired
# ``argus.backtest.vectorbt_pattern._load_pattern_config`` to the
# canonical per-pattern ``load_*_config`` functions in argus.core.config.
# ---------------------------------------------------------------------------

_EXPECTED_CONFIG_TYPES = {
    "bull_flag": BullFlagConfig,
    "flat_top_breakout": FlatTopBreakoutConfig,
    "dip_and_rip": DipAndRipConfig,
    "hod_break": HODBreakConfig,
    "gap_and_go": GapAndGoConfig,
    "abcd": ABCDConfig,
    "premarket_high_break": PreMarketHighBreakConfig,
}


@pytest.mark.parametrize("pattern_name,expected_type", list(_EXPECTED_CONFIG_TYPES.items()))
def test_yaml_loader_returns_correct_type(
    pattern_name: str, expected_type: type
) -> None:
    yaml_path = _CONFIG_DIR / f"{pattern_name}.yaml"
    if not yaml_path.exists():
        pytest.skip(f"Config file not found: {yaml_path}")

    loader = _YAML_LOADERS[pattern_name]
    config = loader(yaml_path)
    assert isinstance(config, expected_type)


# ---------------------------------------------------------------------------
# Test 5: Trade model has config_fingerprint; round-trips through TradeLogger
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_trade_config_fingerprint_stored_and_retrieved() -> None:
    from argus.db.manager import DatabaseManager
    from argus.analytics.trade_logger import TradeLogger
    from argus.models.trading import Trade, ExitReason, OrderSide

    db = DatabaseManager(":memory:")
    await db.initialize()
    logger = TradeLogger(db)

    trade = Trade(
        strategy_id="bull_flag",
        symbol="AAPL",
        side=OrderSide.BUY,
        entry_price=150.0,
        entry_time=datetime(2025, 6, 1, 14, 0, tzinfo=timezone.utc),
        exit_price=153.0,
        exit_time=datetime(2025, 6, 1, 14, 30, tzinfo=timezone.utc),
        shares=100,
        stop_price=148.0,
        target_prices=[153.0, 156.0],
        exit_reason=ExitReason.TARGET_1,
        gross_pnl=300.0,
        config_fingerprint="abc123def456abcd",
    )

    trade_id = await logger.log_trade(trade)
    retrieved = await logger.get_trade(trade_id)

    assert retrieved is not None
    assert retrieved.config_fingerprint == "abc123def456abcd"


# ---------------------------------------------------------------------------
# Test 6: Historical trade (no fingerprint) is still queryable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_historical_trade_without_fingerprint_queryable() -> None:
    from argus.db.manager import DatabaseManager
    from argus.analytics.trade_logger import TradeLogger
    from argus.models.trading import Trade, ExitReason, OrderSide

    db = DatabaseManager(":memory:")
    await db.initialize()
    logger = TradeLogger(db)

    trade = Trade(
        strategy_id="orb_breakout",
        symbol="TSLA",
        side=OrderSide.BUY,
        entry_price=200.0,
        entry_time=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
        exit_price=204.0,
        exit_time=datetime(2025, 1, 1, 14, 30, tzinfo=timezone.utc),
        shares=50,
        stop_price=197.0,
        target_prices=[204.0, 208.0],
        exit_reason=ExitReason.TARGET_1,
        gross_pnl=200.0,
        config_fingerprint=None,  # no fingerprint — legacy record
    )

    trade_id = await logger.log_trade(trade)
    retrieved = await logger.get_trade(trade_id)

    assert retrieved is not None
    assert retrieved.config_fingerprint is None


# ---------------------------------------------------------------------------
# Test 7: Fingerprint is deterministic
# ---------------------------------------------------------------------------

def test_fingerprint_is_deterministic() -> None:
    config_a = BullFlagConfig(**_BASE_FIELDS)  # type: ignore[arg-type]
    config_b = BullFlagConfig(**_BASE_FIELDS)  # type: ignore[arg-type]
    cls = get_pattern_class("bull_flag")
    assert compute_parameter_fingerprint(config_a, cls) == compute_parameter_fingerprint(config_b, cls)


# ---------------------------------------------------------------------------
# Test 8: Fingerprint changes when a detection param changes
# ---------------------------------------------------------------------------

def test_fingerprint_sensitive_to_detection_param_change() -> None:
    config_default = BullFlagConfig(**_BASE_FIELDS)  # type: ignore[arg-type]
    config_altered = BullFlagConfig(**{**_BASE_FIELDS, "pole_min_bars": 10})  # type: ignore[arg-type]
    cls = get_pattern_class("bull_flag")
    fp_default = compute_parameter_fingerprint(config_default, cls)
    fp_altered = compute_parameter_fingerprint(config_altered, cls)
    assert fp_default != fp_altered


# ---------------------------------------------------------------------------
# Test 9: Unknown pattern name raises ValueError in the canonical factory
# FIX-09 P1-E2-M01: migrated from the now-retired
# ``argus.backtest.vectorbt_pattern._create_pattern_by_name`` to the
# canonical ``get_pattern_class`` in ``argus.strategies.patterns.factory``.
# ---------------------------------------------------------------------------

def test_get_pattern_class_unknown_raises() -> None:
    with pytest.raises(ValueError):
        get_pattern_class("nonexistent_pattern")


# ---------------------------------------------------------------------------
# Test 10: OrderManager wires config_fingerprint into logged trade record
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_order_manager_wires_fingerprint_into_trade_record() -> None:
    """register_strategy_fingerprint() causes log_trade() to receive the fingerprint."""
    from datetime import datetime, timezone
    from unittest.mock import AsyncMock, MagicMock

    from argus.db.manager import DatabaseManager
    from argus.analytics.trade_logger import TradeLogger
    from argus.execution.order_manager import OrderManager, ManagedPosition
    from argus.core.config import OrderManagerConfig
    from argus.models.trading import ExitReason, OrderSide

    # Minimal OM setup with an in-memory TradeLogger
    db = DatabaseManager(":memory:")
    await db.initialize()
    trade_logger = TradeLogger(db)

    event_bus = MagicMock()
    event_bus.subscribe = MagicMock()
    event_bus.publish = AsyncMock()

    broker = MagicMock()
    clock = MagicMock()
    clock.now.return_value = datetime(2025, 6, 1, 15, 30, tzinfo=timezone.utc)

    om = OrderManager(
        event_bus=event_bus,
        broker=broker,
        clock=clock,
        config=OrderManagerConfig(),
        trade_logger=trade_logger,
    )

    # Register a fingerprint for the test strategy
    om.register_strategy_fingerprint("bull_flag", "abc123def456abcd")

    # Build a ManagedPosition whose strategy_id matches the registered fingerprint
    entry_time = datetime(2025, 6, 1, 14, 0, tzinfo=timezone.utc)
    position = ManagedPosition(
        symbol="AAPL",
        strategy_id="bull_flag",
        entry_price=150.0,
        entry_time=entry_time,
        shares_total=100,
        shares_remaining=0,
        stop_price=148.0,
        original_stop_price=148.0,
        stop_order_id=None,
        t1_price=153.0,
        t1_order_id=None,
        t1_shares=50,
        t1_filled=True,
        t2_price=156.0,
        high_watermark=153.0,
        realized_pnl=300.0,
        quality_grade="A",
        quality_score=85.0,
        mfe_price=153.5,
        mae_price=149.5,
        mfe_r=1.75,
        mae_r=-0.25,
    )

    # Invoke the private close path — this logs the trade via TradeLogger
    await om._close_position(position, exit_price=153.0, exit_reason=ExitReason.TARGET_1)

    trades = await trade_logger.query_trades(strategy_id="bull_flag", limit=1)
    assert len(trades) == 1
    trade_id = trades[0]["id"]
    retrieved = await trade_logger.get_trade(trade_id)
    assert retrieved is not None
    assert retrieved.config_fingerprint == "abc123def456abcd"


@pytest.mark.asyncio
async def test_order_manager_non_pattern_strategy_gets_none_fingerprint() -> None:
    """Strategies absent from the fingerprint registry produce config_fingerprint=None."""
    from datetime import datetime, timezone
    from unittest.mock import AsyncMock, MagicMock

    from argus.db.manager import DatabaseManager
    from argus.analytics.trade_logger import TradeLogger
    from argus.execution.order_manager import OrderManager, ManagedPosition
    from argus.core.config import OrderManagerConfig
    from argus.models.trading import ExitReason

    db = DatabaseManager(":memory:")
    await db.initialize()
    trade_logger = TradeLogger(db)

    event_bus = MagicMock()
    event_bus.subscribe = MagicMock()
    event_bus.publish = AsyncMock()

    broker = MagicMock()
    clock = MagicMock()
    clock.now.return_value = datetime(2025, 6, 1, 15, 30, tzinfo=timezone.utc)

    om = OrderManager(
        event_bus=event_bus,
        broker=broker,
        clock=clock,
        config=OrderManagerConfig(),
        trade_logger=trade_logger,
    )
    # orb_breakout is NOT registered — should resolve to None

    entry_time = datetime(2025, 6, 1, 14, 0, tzinfo=timezone.utc)
    position = ManagedPosition(
        symbol="TSLA",
        strategy_id="orb_breakout",
        entry_price=200.0,
        entry_time=entry_time,
        shares_total=50,
        shares_remaining=0,
        stop_price=197.0,
        original_stop_price=197.0,
        stop_order_id=None,
        t1_price=204.0,
        t1_order_id=None,
        t1_shares=25,
        t1_filled=True,
        t2_price=208.0,
        high_watermark=204.0,
        realized_pnl=200.0,
        mfe_price=204.5,
        mae_price=199.0,
        mfe_r=1.5,
        mae_r=-0.33,
    )

    await om._close_position(position, exit_price=204.0, exit_reason=ExitReason.TARGET_1)

    trades = await trade_logger.query_trades(strategy_id="orb_breakout", limit=1)
    assert len(trades) == 1
    trade_id = trades[0]["id"]
    retrieved = await trade_logger.get_trade(trade_id)
    assert retrieved is not None
    assert retrieved.config_fingerprint is None
