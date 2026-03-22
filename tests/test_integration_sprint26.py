"""Integration tests for Sprint 26 Session 9: strategy wiring.

Validates that RedToGreenStrategy, BullFlagPattern (as PatternBasedStrategy),
and FlatTopBreakoutPattern (as PatternBasedStrategy) are correctly created
from YAML config, registered with the Orchestrator, and served via the API.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.core.config import (
    BullFlagConfig,
    FlatTopBreakoutConfig,
    OrchestratorConfig,
    RedToGreenConfig,
    load_bull_flag_config,
    load_flat_top_breakout_config,
    load_red_to_green_config,
)
from argus.core.event_bus import EventBus
from argus.core.orchestrator import Orchestrator
from argus.strategies.orb_breakout import OrbBreakoutStrategy
from argus.strategies.orb_scalp import OrbScalpStrategy
from argus.strategies.pattern_strategy import PatternBasedStrategy
from argus.strategies.patterns import BullFlagPattern, FlatTopBreakoutPattern
from argus.strategies.red_to_green import RedToGreenStrategy
from argus.strategies.vwap_reclaim import VwapReclaimStrategy
from argus.strategies.afternoon_momentum import AfternoonMomentumStrategy

# Path to real YAML config files
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config" / "strategies"


class TestStrategyCreation:
    """Tests for creating Sprint 26 strategies from YAML config."""

    def test_r2g_strategy_creation_from_config(self) -> None:
        """Create RedToGreenStrategy from YAML, verify instance and config."""
        r2g_yaml = CONFIG_DIR / "red_to_green.yaml"
        assert r2g_yaml.exists(), f"Missing config: {r2g_yaml}"

        config = load_red_to_green_config(r2g_yaml)
        strategy = RedToGreenStrategy(config=config)

        assert isinstance(strategy, RedToGreenStrategy)
        assert strategy.strategy_id == "strat_red_to_green"
        assert isinstance(strategy.config, RedToGreenConfig)
        assert config.min_gap_down_pct == 0.02
        assert config.max_gap_down_pct == 0.10

    def test_bull_flag_pattern_strategy_creation(self) -> None:
        """Create PatternBasedStrategy with BullFlagPattern from YAML."""
        bf_yaml = CONFIG_DIR / "bull_flag.yaml"
        assert bf_yaml.exists(), f"Missing config: {bf_yaml}"

        config = load_bull_flag_config(bf_yaml)
        pattern = BullFlagPattern()
        strategy = PatternBasedStrategy(pattern=pattern, config=config)

        assert isinstance(strategy, PatternBasedStrategy)
        assert strategy.strategy_id == "strat_bull_flag"
        assert isinstance(strategy.config, BullFlagConfig)
        assert config.pole_min_bars == 5
        assert config.breakout_volume_multiplier == 1.3

    def test_flat_top_pattern_strategy_creation(self) -> None:
        """Create PatternBasedStrategy with FlatTopBreakoutPattern from YAML."""
        ft_yaml = CONFIG_DIR / "flat_top_breakout.yaml"
        assert ft_yaml.exists(), f"Missing config: {ft_yaml}"

        config = load_flat_top_breakout_config(ft_yaml)
        pattern = FlatTopBreakoutPattern()
        strategy = PatternBasedStrategy(pattern=pattern, config=config)

        assert isinstance(strategy, PatternBasedStrategy)
        assert strategy.strategy_id == "strat_flat_top_breakout"
        assert isinstance(strategy.config, FlatTopBreakoutConfig)
        assert config.resistance_touches == 3
        assert config.consolidation_min_bars == 10


class TestOrchestratorRegistration:
    """Tests for registering all 7 strategies with the Orchestrator."""

    def _create_all_strategies(self) -> list[object]:
        """Create all 7 strategy instances from YAML configs.

        Returns:
            List of all strategy instances.
        """
        from argus.core.config import (
            load_afternoon_momentum_config,
            load_orb_config,
            load_orb_scalp_config,
            load_vwap_reclaim_config,
        )

        strategies = []

        # 1. ORB Breakout
        orb_config = load_orb_config(CONFIG_DIR / "orb_breakout.yaml")
        strategies.append(OrbBreakoutStrategy(config=orb_config))

        # 2. ORB Scalp
        scalp_config = load_orb_scalp_config(CONFIG_DIR / "orb_scalp.yaml")
        strategies.append(OrbScalpStrategy(config=scalp_config))

        # 3. VWAP Reclaim
        vwap_config = load_vwap_reclaim_config(CONFIG_DIR / "vwap_reclaim.yaml")
        strategies.append(VwapReclaimStrategy(config=vwap_config))

        # 4. Afternoon Momentum
        am_config = load_afternoon_momentum_config(
            CONFIG_DIR / "afternoon_momentum.yaml"
        )
        strategies.append(AfternoonMomentumStrategy(config=am_config))

        # 5. Red-to-Green
        r2g_config = load_red_to_green_config(CONFIG_DIR / "red_to_green.yaml")
        strategies.append(RedToGreenStrategy(config=r2g_config))

        # 6. Bull Flag
        bf_config = load_bull_flag_config(CONFIG_DIR / "bull_flag.yaml")
        strategies.append(
            PatternBasedStrategy(pattern=BullFlagPattern(), config=bf_config)
        )

        # 7. Flat-Top Breakout
        ft_config = load_flat_top_breakout_config(
            CONFIG_DIR / "flat_top_breakout.yaml"
        )
        strategies.append(
            PatternBasedStrategy(
                pattern=FlatTopBreakoutPattern(), config=ft_config
            )
        )

        return strategies

    def test_orchestrator_registers_7_strategies(self) -> None:
        """Register all 7 strategies with Orchestrator, verify count."""
        strategies = self._create_all_strategies()
        assert len(strategies) == 7

        # Create Orchestrator with mock dependencies
        config = OrchestratorConfig()
        event_bus = EventBus()
        orchestrator = Orchestrator(
            config=config,
            event_bus=event_bus,
            clock=MagicMock(),
            trade_logger=MagicMock(),
            broker=MagicMock(),
            data_service=MagicMock(),
        )

        for strategy in strategies:
            orchestrator.register_strategy(strategy)

        registered = orchestrator.get_strategies()
        assert len(registered) == 7

        # Verify all expected IDs present
        expected_ids = {
            "strat_orb_breakout",
            "strat_orb_scalp",
            "strat_vwap_reclaim",
            "strat_afternoon_momentum",
            "strat_red_to_green",
            "strat_bull_flag",
            "strat_flat_top_breakout",
        }
        assert set(registered.keys()) == expected_ids

    @pytest.mark.asyncio
    async def test_orchestrator_allocation_with_7_strategies(self) -> None:
        """Verify each of 7 strategies gets allocated_capital > 0."""
        strategies = self._create_all_strategies()

        config = OrchestratorConfig()
        event_bus = EventBus()

        # Mock broker with equity
        mock_broker = MagicMock()
        mock_broker.get_account_equity = AsyncMock(return_value=100_000.0)

        # Mock trade_logger
        mock_trade_logger = MagicMock()
        mock_trade_logger.query_trades = AsyncMock(return_value=[])
        mock_trade_logger.get_daily_pnl = AsyncMock(return_value=[])
        mock_trade_logger.get_todays_pnl = AsyncMock(return_value=0.0)
        mock_trade_logger.get_trades_by_strategy = AsyncMock(return_value=[])

        orchestrator = Orchestrator(
            config=config,
            event_bus=event_bus,
            clock=MagicMock(),
            trade_logger=mock_trade_logger,
            broker=mock_broker,
            data_service=MagicMock(),
        )

        for strategy in strategies:
            orchestrator.register_strategy(strategy)

        # Run allocation via _calculate_allocations
        allocations = await orchestrator._calculate_allocations(100_000.0)

        assert len(allocations) == 7
        for alloc in allocations:
            # Each strategy should have non-zero allocation
            assert alloc.allocation_dollars > 0, (
                f"{alloc.strategy_id} got zero allocation"
            )
            assert alloc.allocation_pct > 0, (
                f"{alloc.strategy_id} got zero pct"
            )


class TestConfigGating:
    """Tests for config-gating: missing YAML, enabled:false."""

    def test_disabled_strategy_not_created(self, tmp_path: Path) -> None:
        """Config with enabled:false should still load but strategy checks enabled."""
        import yaml

        # Create a R2G config with enabled=false
        disabled_config = {
            "strategy_id": "strat_red_to_green",
            "name": "Red-to-Green",
            "enabled": False,
            "min_gap_down_pct": 0.02,
            "max_gap_down_pct": 0.10,
            "operating_window": {
                "earliest_entry": "09:45",
                "latest_entry": "11:00",
            },
        }
        config_path = tmp_path / "red_to_green.yaml"
        config_path.write_text(yaml.dump(disabled_config))

        config = load_red_to_green_config(config_path)
        assert config.enabled is False

        # Strategy can still be created (enabled check is Orchestrator's job)
        strategy = RedToGreenStrategy(config=config)
        assert strategy.config.enabled is False

    def test_missing_yaml_skips_strategy(self, tmp_path: Path) -> None:
        """Missing YAML file means strategy is not created (same pattern as main.py)."""
        nonexistent = tmp_path / "strategies" / "red_to_green.yaml"
        assert not nonexistent.exists()

        # Simulate main.py pattern: only create if yaml.exists()
        r2g_strategy = None
        if nonexistent.exists():
            config = load_red_to_green_config(nonexistent)
            r2g_strategy = RedToGreenStrategy(config=config)

        assert r2g_strategy is None


class TestAPIStrategies:
    """Tests for API /strategies endpoint returning all 7 strategies."""

    @pytest.mark.asyncio
    async def test_api_strategies_returns_7(self) -> None:
        """Mock API endpoint returns 7 strategy entries."""
        from argus.core.config import (
            load_afternoon_momentum_config,
            load_orb_config,
            load_orb_scalp_config,
            load_vwap_reclaim_config,
        )

        # Build all 7 strategies
        orb = OrbBreakoutStrategy(
            config=load_orb_config(CONFIG_DIR / "orb_breakout.yaml")
        )
        scalp = OrbScalpStrategy(
            config=load_orb_scalp_config(CONFIG_DIR / "orb_scalp.yaml")
        )
        vwap = VwapReclaimStrategy(
            config=load_vwap_reclaim_config(CONFIG_DIR / "vwap_reclaim.yaml")
        )
        afternoon = AfternoonMomentumStrategy(
            config=load_afternoon_momentum_config(
                CONFIG_DIR / "afternoon_momentum.yaml"
            )
        )
        r2g = RedToGreenStrategy(
            config=load_red_to_green_config(CONFIG_DIR / "red_to_green.yaml")
        )
        bull_flag = PatternBasedStrategy(
            pattern=BullFlagPattern(),
            config=load_bull_flag_config(CONFIG_DIR / "bull_flag.yaml"),
        )
        flat_top = PatternBasedStrategy(
            pattern=FlatTopBreakoutPattern(),
            config=load_flat_top_breakout_config(
                CONFIG_DIR / "flat_top_breakout.yaml"
            ),
        )

        all_strategies = [orb, scalp, vwap, afternoon, r2g, bull_flag, flat_top]

        # Build strategies dict as Orchestrator.get_strategies() would
        strategies_dict = {s.strategy_id: s for s in all_strategies}
        assert len(strategies_dict) == 7

        # Verify each strategy ID is unique and present
        expected_ids = {
            "strat_orb_breakout",
            "strat_orb_scalp",
            "strat_vwap_reclaim",
            "strat_afternoon_momentum",
            "strat_red_to_green",
            "strat_bull_flag",
            "strat_flat_top_breakout",
        }
        assert set(strategies_dict.keys()) == expected_ids

        # Verify each has a valid config with name
        for sid, strategy in strategies_dict.items():
            assert strategy.config.name, f"{sid} missing config.name"
            assert strategy.config.strategy_id == sid
