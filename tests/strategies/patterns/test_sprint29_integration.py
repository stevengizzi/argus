"""Sprint 29 integration verification tests.

Verifies all 5 new patterns (Dip-and-Rip, HOD Break, ABCD, Gap-and-Go,
Pre-Market High Break) load correctly, configs parse, universe filters
route, exit overrides apply, and cross-pattern invariants hold.

Sprint 29, Session 8.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from argus.core.config import (
    ABCDConfig,
    DipAndRipConfig,
    ExitManagementConfig,
    GapAndGoConfig,
    HODBreakConfig,
    PreMarketHighBreakConfig,
    deep_update,
    load_abcd_config,
    load_dip_and_rip_config,
    load_gap_and_go_config,
    load_hod_break_config,
    load_premarket_high_break_config,
)
from argus.strategies.pattern_strategy import PatternBasedStrategy
from argus.strategies.patterns import (
    ABCDPattern,
    DipAndRipPattern,
    GapAndGoPattern,
    HODBreakPattern,
    PatternDetection,
    PreMarketHighBreakPattern,
)
from argus.strategies.patterns.base import CandleBar

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONFIG_DIR = Path("config")
STRATEGIES_DIR = CONFIG_DIR / "strategies"
FILTERS_DIR = CONFIG_DIR / "universe_filters"

# Pattern registry: pattern_key → (config_class, loader, yaml_name,
#   pattern_class, strategy_id, pattern_name, filter_yaml_name)
PATTERN_REGISTRY: list[
    tuple[
        str,
        type,
        object,
        str,
        type,
        str,
        str,
        str,
    ]
] = [
    (
        "dip_and_rip",
        DipAndRipConfig,
        load_dip_and_rip_config,
        "dip_and_rip.yaml",
        DipAndRipPattern,
        "strat_dip_and_rip",
        "dip_and_rip",
        "dip_and_rip.yaml",
    ),
    (
        "hod_break",
        HODBreakConfig,
        load_hod_break_config,
        "hod_break.yaml",
        HODBreakPattern,
        "strat_hod_break",
        "HOD Break",
        "hod_break.yaml",
    ),
    (
        "abcd",
        ABCDConfig,
        load_abcd_config,
        "abcd.yaml",
        ABCDPattern,
        "strat_abcd",
        "abcd",
        "abcd.yaml",
    ),
    (
        "gap_and_go",
        GapAndGoConfig,
        load_gap_and_go_config,
        "gap_and_go.yaml",
        GapAndGoPattern,
        "strat_gap_and_go",
        "Gap-and-Go",
        "gap_and_go.yaml",
    ),
    (
        "premarket_high_break",
        PreMarketHighBreakConfig,
        load_premarket_high_break_config,
        "premarket_high_break.yaml",
        PreMarketHighBreakPattern,
        "strat_premarket_high_break",
        "Pre-Market High Break",
        "premarket_high_break.yaml",
    ),
]

# 14:00 UTC = 10:00 ET (EDT) — inside most operating windows
BASE_TIME = datetime(2026, 3, 31, 14, 0, 0, tzinfo=UTC)


def _make_candle_event(
    symbol: str,
    close: float,
    offset_minutes: int = 0,
    volume: int = 10000,
) -> object:
    """Build a CandleEvent for strategy wrapper tests."""
    from argus.core.events import CandleEvent

    ts = BASE_TIME + timedelta(minutes=offset_minutes)
    return CandleEvent(
        symbol=symbol,
        timestamp=ts,
        open=close - 0.50,
        high=close + 0.50,
        low=close - 1.0,
        close=close,
        volume=volume,
    )


# ---------------------------------------------------------------------------
# 1. Config YAML Parse Verification (per pattern)
# ---------------------------------------------------------------------------


class TestConfigYAMLParsing:
    """Each new pattern's YAML parses into its Pydantic config without error."""

    @pytest.mark.parametrize(
        "key,config_cls,loader,yaml_name,_pat,strat_id,_pname,_filt",
        PATTERN_REGISTRY,
        ids=[r[0] for r in PATTERN_REGISTRY],
    )
    def test_strategy_yaml_parses(
        self,
        key: str,
        config_cls: type,
        loader: object,
        yaml_name: str,
        _pat: type,
        strat_id: str,
        _pname: str,
        _filt: str,
    ) -> None:
        """Strategy YAML loads and validates via Pydantic."""
        yaml_path = STRATEGIES_DIR / yaml_name
        assert yaml_path.exists(), f"Missing: {yaml_path}"

        config = loader(yaml_path)
        assert isinstance(config, config_cls)
        assert config.strategy_id == strat_id
        assert config.enabled is True
        # All new patterns have target_1_r and target_2_r
        assert config.target_1_r > 0
        assert config.target_2_r > config.target_1_r or config.target_2_r > 0

    @pytest.mark.parametrize(
        "key,_cls,_loader,yaml_name,_pat,_sid,_pname,_filt",
        PATTERN_REGISTRY,
        ids=[r[0] for r in PATTERN_REGISTRY],
    )
    def test_no_unknown_keys_silently_ignored(
        self,
        key: str,
        _cls: type,
        _loader: object,
        yaml_name: str,
        _pat: type,
        _sid: str,
        _pname: str,
        _filt: str,
    ) -> None:
        """All keys in strategy YAML are recognized by the config model."""
        yaml_path = STRATEGIES_DIR / yaml_name
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        # Pydantic v2 with model_config extra="ignore" silently drops unknown
        # keys. Instead, verify each top-level YAML key maps to a model field
        # or known nested section.
        known_sections = {
            "risk_limits",
            "benchmarks",
            "backtest_summary",
            "universe_filter",
            "exit_management",
            "operating_window",
            "allowed_regimes",
        }
        model_fields = set(_cls.model_fields.keys())
        for yaml_key in data:
            assert yaml_key in model_fields or yaml_key in known_sections, (
                f"Unrecognized key '{yaml_key}' in {yaml_name}"
            )


# ---------------------------------------------------------------------------
# 2. Universe Filter Verification
# ---------------------------------------------------------------------------


class TestUniverseFilters:
    """Universe filter YAMLs exist and contain valid fields."""

    @pytest.mark.parametrize(
        "key,_cls,_loader,_yname,_pat,_sid,_pname,filter_yaml",
        PATTERN_REGISTRY,
        ids=[r[0] for r in PATTERN_REGISTRY],
    )
    def test_filter_yaml_exists_and_parses(
        self,
        key: str,
        _cls: type,
        _loader: object,
        _yname: str,
        _pat: type,
        _sid: str,
        _pname: str,
        filter_yaml: str,
    ) -> None:
        """Universe filter YAML exists and has required base fields."""
        filter_path = FILTERS_DIR / filter_yaml
        assert filter_path.exists(), f"Missing universe filter: {filter_path}"

        with open(filter_path) as f:
            data = yaml.safe_load(f)

        assert "min_price" in data
        assert "max_price" in data
        assert "min_avg_volume" in data
        assert data["min_price"] > 0
        assert data["max_price"] > data["min_price"]
        assert data["min_avg_volume"] > 0

    def test_gap_and_go_filter_has_min_gap_percent(self) -> None:
        """Gap-and-Go filter has custom min_gap_percent field."""
        with open(FILTERS_DIR / "gap_and_go.yaml") as f:
            data = yaml.safe_load(f)
        assert "min_gap_percent" in data
        assert data["min_gap_percent"] > 0

    def test_premarket_high_break_filter_has_min_premarket_volume(self) -> None:
        """Pre-Market High Break filter has custom min_premarket_volume."""
        with open(FILTERS_DIR / "premarket_high_break.yaml") as f:
            data = yaml.safe_load(f)
        assert "min_premarket_volume" in data
        assert data["min_premarket_volume"] > 0

    def test_dip_and_rip_filter_has_min_relative_volume(self) -> None:
        """Dip-and-Rip filter has custom min_relative_volume field."""
        with open(FILTERS_DIR / "dip_and_rip.yaml") as f:
            data = yaml.safe_load(f)
        assert "min_relative_volume" in data
        assert data["min_relative_volume"] > 0

    def test_strategy_yaml_universe_filter_matches_filter_yaml(self) -> None:
        """Strategy YAML universe_filter section matches standalone filter."""
        for key, _cls, _loader, yaml_name, _pat, _sid, _pname, filt in PATTERN_REGISTRY:
            strat_path = STRATEGIES_DIR / yaml_name
            filter_path = FILTERS_DIR / filt

            with open(strat_path) as f:
                strat_data = yaml.safe_load(f)
            with open(filter_path) as f:
                filter_data = yaml.safe_load(f)

            strat_filter = strat_data.get("universe_filter", {})
            # All keys in standalone filter must appear in strategy filter
            for fkey, fval in filter_data.items():
                assert fkey in strat_filter, (
                    f"{key}: filter key '{fkey}' missing from strategy YAML"
                )
                assert strat_filter[fkey] == fval, (
                    f"{key}: filter key '{fkey}' mismatch: "
                    f"{strat_filter[fkey]} != {fval}"
                )


# ---------------------------------------------------------------------------
# 3. Exit Override Verification
# ---------------------------------------------------------------------------


class TestExitOverrides:
    """Exit management overrides apply correctly via deep_update."""

    @pytest.mark.parametrize(
        "key,_cls,_loader,yaml_name,_pat,_sid,_pname,_filt",
        PATTERN_REGISTRY,
        ids=[r[0] for r in PATTERN_REGISTRY],
    )
    def test_exit_override_present_in_strategy_yaml(
        self,
        key: str,
        _cls: type,
        _loader: object,
        yaml_name: str,
        _pat: type,
        _sid: str,
        _pname: str,
        _filt: str,
    ) -> None:
        """Strategy YAML contains exit_management section."""
        with open(STRATEGIES_DIR / yaml_name) as f:
            data = yaml.safe_load(f)
        assert "exit_management" in data, f"{key}: no exit_management section"
        em = data["exit_management"]
        assert "trailing_stop" in em
        assert em["trailing_stop"]["enabled"] is True
        assert "escalation" in em
        assert em["escalation"]["enabled"] is True
        assert len(em["escalation"]["phases"]) >= 2

    @pytest.mark.parametrize(
        "key,_cls,_loader,yaml_name,_pat,_sid,_pname,_filt",
        PATTERN_REGISTRY,
        ids=[r[0] for r in PATTERN_REGISTRY],
    )
    def test_exit_override_merges_with_global(
        self,
        key: str,
        _cls: type,
        _loader: object,
        yaml_name: str,
        _pat: type,
        _sid: str,
        _pname: str,
        _filt: str,
    ) -> None:
        """deep_update merges strategy exit override onto global defaults."""
        global_path = CONFIG_DIR / "exit_management.yaml"
        with open(global_path) as f:
            global_data = yaml.safe_load(f)
        with open(STRATEGIES_DIR / yaml_name) as f:
            strat_data = yaml.safe_load(f)

        override = strat_data["exit_management"]
        merged = deep_update(global_data, override)
        cfg = ExitManagementConfig(**merged)

        # Strategy override should win
        assert cfg.trailing_stop.enabled is True
        assert cfg.escalation.enabled is True
        assert len(cfg.escalation.phases) >= 2


# ---------------------------------------------------------------------------
# 4. Strategy Registration — all patterns wrap in PatternBasedStrategy
# ---------------------------------------------------------------------------


class TestStrategyRegistration:
    """All new patterns instantiate and wrap in PatternBasedStrategy."""

    @pytest.mark.parametrize(
        "key,config_cls,loader,yaml_name,pattern_cls,strat_id,pattern_name,_filt",
        PATTERN_REGISTRY,
        ids=[r[0] for r in PATTERN_REGISTRY],
    )
    def test_pattern_wraps_in_strategy(
        self,
        key: str,
        config_cls: type,
        loader: object,
        yaml_name: str,
        pattern_cls: type,
        strat_id: str,
        pattern_name: str,
        _filt: str,
    ) -> None:
        """Pattern loads into PatternBasedStrategy with correct ID."""
        config = loader(STRATEGIES_DIR / yaml_name)
        pattern = pattern_cls()
        strategy = PatternBasedStrategy(pattern=pattern, config=config)

        assert strategy.strategy_id == strat_id
        assert strategy._pattern.name == pattern_name

    def test_no_strategy_id_collisions(self) -> None:
        """All 12 strategy IDs are unique (7 existing + 5 new)."""
        new_ids = {r[5] for r in PATTERN_REGISTRY}
        existing_ids = {
            "orb_breakout",
            "orb_scalp",
            "vwap_reclaim",
            "afternoon_momentum",
            "red_to_green",
            "strat_bull_flag",
            "strat_flat_top_breakout",
        }
        all_ids = new_ids | existing_ids
        assert len(all_ids) == len(new_ids) + len(existing_ids), "ID collision detected"

    def test_all_patterns_importable_from_package(self) -> None:
        """All 5 new patterns import from argus.strategies.patterns."""
        from argus.strategies.patterns import (
            ABCDPattern,
            DipAndRipPattern,
            GapAndGoPattern,
            HODBreakPattern,
            PreMarketHighBreakPattern,
        )

        for cls in (
            ABCDPattern,
            DipAndRipPattern,
            GapAndGoPattern,
            HODBreakPattern,
            PreMarketHighBreakPattern,
        ):
            pattern = cls()
            assert pattern.lookback_bars > 0
            assert len(pattern.name) > 0


# ---------------------------------------------------------------------------
# 5. Cross-Pattern Invariants
# ---------------------------------------------------------------------------


class TestCrossPatternInvariants:
    """Cross-pattern consistency checks."""

    @pytest.mark.parametrize(
        "key,_cls,_loader,_yname,pattern_cls,_sid,_pname,_filt",
        PATTERN_REGISTRY,
        ids=[r[0] for r in PATTERN_REGISTRY],
    )
    def test_score_returns_0_to_100(
        self,
        key: str,
        _cls: type,
        _loader: object,
        _yname: str,
        pattern_cls: type,
        _sid: str,
        _pname: str,
        _filt: str,
    ) -> None:
        """Pattern.score() returns value in [0, 100] for a mock detection."""
        pattern = pattern_cls()
        # Create a minimal detection with dummy metadata
        detection = PatternDetection(
            pattern_type=pattern.name,
            confidence=75.0,
            entry_price=150.0,
            stop_price=148.0,
            metadata={"volume_ratio": 2.0, "recovery_pct": 0.7},
        )
        score = pattern.score(detection)
        assert 0.0 <= score <= 100.0, (
            f"{key}: score {score} outside [0, 100]"
        )

    @pytest.mark.parametrize(
        "key,_cls,_loader,_yname,pattern_cls,_sid,_pname,_filt",
        PATTERN_REGISTRY,
        ids=[r[0] for r in PATTERN_REGISTRY],
    )
    def test_get_default_params_returns_list(
        self,
        key: str,
        _cls: type,
        _loader: object,
        _yname: str,
        pattern_cls: type,
        _sid: str,
        _pname: str,
        _filt: str,
    ) -> None:
        """get_default_params() returns a non-empty list of PatternParam."""
        from argus.strategies.patterns.base import PatternParam

        pattern = pattern_cls()
        params = pattern.get_default_params()
        assert isinstance(params, list)
        assert len(params) > 0
        for p in params:
            assert isinstance(p, PatternParam)
            assert len(p.name) > 0

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "key,config_cls,loader,yaml_name,pattern_cls,strat_id,_pname,_filt",
        PATTERN_REGISTRY,
        ids=[r[0] for r in PATTERN_REGISTRY],
    )
    async def test_candle_accumulates_in_window(
        self,
        key: str,
        config_cls: type,
        loader: object,
        yaml_name: str,
        pattern_cls: type,
        strat_id: str,
        _pname: str,
        _filt: str,
    ) -> None:
        """Candle events accumulate in per-symbol window for each pattern."""
        config = loader(STRATEGIES_DIR / yaml_name)
        pattern = pattern_cls()
        strategy = PatternBasedStrategy(pattern=pattern, config=config)
        strategy.set_watchlist(["AAPL"])

        for i in range(5):
            event = _make_candle_event("AAPL", 150.0 + i * 0.5, offset_minutes=i)
            await strategy.on_candle(event)

        window = strategy._candle_windows.get("AAPL")
        assert window is not None
        assert len(window) == 5, f"{key}: expected 5 candles, got {len(window)}"


# ---------------------------------------------------------------------------
# 6. Counterfactual Tracker Accepts New Strategy IDs
# ---------------------------------------------------------------------------


class TestCounterfactualAcceptsNewStrategies:
    """CounterfactualTracker handles signals from new strategy IDs."""

    def test_tracker_accepts_new_strategy_ids(self) -> None:
        """CounterfactualTracker.track() succeeds for all new strategy IDs."""
        from argus.core.events import Side, SignalEvent
        from argus.intelligence.counterfactual import (
            CounterfactualTracker,
            RejectionStage,
        )

        tracker = CounterfactualTracker()

        for _key, _cls, _loader, _yname, _pat, strat_id, _pname, _filt in PATTERN_REGISTRY:
            signal = SignalEvent(
                strategy_id=strat_id,
                symbol="AAPL",
                side=Side.LONG,
                entry_price=150.0,
                stop_price=148.0,
                target_prices=(152.0, 154.0),
                share_count=0,
                rationale="integration test signal",
                pattern_strength=70.0,
                signal_context={},
                quality_score=65.0,
                quality_grade="C+",
            )
            pid = tracker.track(
                signal, "grade too low", RejectionStage.QUALITY_FILTER
            )
            assert pid is not None, f"Tracker returned None for {strat_id}"

        # Verify all 5 positions tracked
        positions = tracker.get_open_positions()
        assert len(positions) == 5
