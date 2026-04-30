"""Sprint 31.92 Unit 3 — Cat A spike-fix regression tests.

Regression coverage for `scripts/spike_def204_round2_path1.py` after the
Cat A spike fixes per Sprint 31.92 Tier 3 Review #2 verdict §Cat A.

  Cat A.1 (DEF-236): Mode A propagation measurement bug fix.
    - `_verify_aux_price()` logs the observed auxPrice unconditionally so
      a False return is diagnostic.
    - Mode A trial body waits 2.5s (was 500ms) + force-pulls broker state
      via `reqOpenOrders()` before sampling.

  Cat A.2 (DEF-237): side-aware `_flatten()` + pre-spike sweep gate.
    - `SpikeShortPositionDetected` exception class at module scope.
    - `_flatten()` reads `(p.side, p.shares)` for three-branch dispatch:
      genuine long → SELL; short → raise; UNKNOWN → log + break;
      shares == 0 → defensive no-op.
    - Pre-spike sweep gate in `main_async()` refuses to start when
      `broker.get_positions()` returns any nonzero position.

The tests do NOT execute the spike (that requires an IBKR Gateway). They
exercise the helpers directly with mocks AND grep-verify the load-bearing
structural changes in the script body.
"""

from __future__ import annotations

import importlib.util
import re
import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.models.trading import OrderSide

REPO_ROOT = Path(__file__).resolve().parents[2]
SPIKE_SCRIPT = REPO_ROOT / "scripts" / "spike_def204_round2_path1.py"


def _load_spike_module() -> types.ModuleType:
    """Import the spike script as a module without running its CLI entry.

    The module's top-level imports succeed cleanly (verified at session
    pre-flight); only `main()` triggers the IBKR connection.
    """
    spec = importlib.util.spec_from_file_location(
        "spike_def204_round2_path1", SPIKE_SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["spike_def204_round2_path1"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def spike() -> types.ModuleType:
    return _load_spike_module()


def _make_position(symbol: str, side: OrderSide, shares: int) -> MagicMock:
    """Build a Position-shaped mock with just the (symbol, side, shares)
    fields the Cat A.2 _flatten() reads. Avoids constructing a real
    Pydantic Position (which has many required fields)."""
    p = MagicMock()
    p.symbol = symbol
    p.side = side
    p.shares = shares
    return p


def _make_broker() -> MagicMock:
    """IBKRBroker mock with the methods _flatten() invokes."""
    broker = MagicMock()
    broker.cancel_all_orders = AsyncMock()
    broker.place_order = AsyncMock()
    broker.get_positions = AsyncMock(return_value=[])
    return broker


# ---------------------------------------------------------------------------
# Cat A.2 — SpikeShortPositionDetected exception
# ---------------------------------------------------------------------------


class TestSpikeShortPositionDetected:
    """The new exception class is module-scope, accepts (symbol, side,
    shares), and is raise-able from `_flatten()`."""

    def test_exception_class_exists_at_module_scope(self, spike) -> None:
        assert hasattr(spike, "SpikeShortPositionDetected")
        assert issubclass(spike.SpikeShortPositionDetected, Exception)

    def test_exception_stores_symbol_side_shares(self, spike) -> None:
        exc = spike.SpikeShortPositionDetected("QQQ", OrderSide.SELL, 200)
        assert exc.symbol == "QQQ"
        assert exc.side == OrderSide.SELL
        assert exc.shares == 200

    def test_exception_message_includes_symbol_and_shares(self, spike) -> None:
        exc = spike.SpikeShortPositionDetected("QQQ", OrderSide.SELL, 200)
        msg = str(exc)
        assert "QQQ" in msg
        assert "200" in msg
        assert "SHORT" in msg or "short" in msg.lower()


# ---------------------------------------------------------------------------
# Cat A.2 — _flatten() three-branch dispatch
# ---------------------------------------------------------------------------


class TestFlattenSideAware:
    """_flatten() must read (p.side, p.shares) — NOT raw p.shares — to
    decide the SELL/raise/no-op disposition. Mirrors IMPROMPTU-04."""

    @pytest.mark.asyncio
    async def test_long_position_is_flattened_via_sell(self, spike) -> None:
        broker = _make_broker()
        broker.get_positions.return_value = [
            _make_position("SPY", OrderSide.BUY, 1)
        ]
        await spike._flatten(broker, "SPY")
        broker.cancel_all_orders.assert_awaited_once()
        broker.place_order.assert_awaited_once()
        order_arg = broker.place_order.await_args.args[0]
        assert order_arg.symbol == "SPY"
        assert order_arg.side == OrderSide.SELL
        assert order_arg.quantity == 1

    @pytest.mark.asyncio
    async def test_short_position_raises_spike_short_position_detected(
        self, spike
    ) -> None:
        broker = _make_broker()
        broker.get_positions.return_value = [
            _make_position("QQQ", OrderSide.SELL, 200)
        ]
        with pytest.raises(spike.SpikeShortPositionDetected) as exc_info:
            await spike._flatten(broker, "QQQ")
        assert exc_info.value.symbol == "QQQ"
        assert exc_info.value.side == OrderSide.SELL
        assert exc_info.value.shares == 200
        # Critical: NO place_order against the short.
        broker.place_order.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_position_for_symbol_is_noop(self, spike) -> None:
        broker = _make_broker()
        broker.get_positions.return_value = []
        await spike._flatten(broker, "IWM")
        broker.cancel_all_orders.assert_awaited_once()
        broker.place_order.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_position_for_other_symbol_is_skipped(self, spike) -> None:
        broker = _make_broker()
        broker.get_positions.return_value = [
            _make_position("XLF", OrderSide.BUY, 5)
        ]
        await spike._flatten(broker, "SPY")
        broker.place_order.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_zero_shares_defensive_branch_is_noop(self, spike) -> None:
        """IBKRBroker.get_positions filters zero-share positions upstream;
        this defense-in-depth branch protects against a future regression
        of that filter without re-introducing the absolute-value trap."""
        broker = _make_broker()
        broker.get_positions.return_value = [
            _make_position("SPY", OrderSide.BUY, 0)
        ]
        await spike._flatten(broker, "SPY")
        broker.place_order.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unknown_side_logs_error_and_breaks(
        self, spike, caplog
    ) -> None:
        """Defends against future OrderSide enum extension. Current enum
        has only BUY/SELL so this branch is unreachable today; the test
        synthesizes an unknown value to prove the branch is structurally
        present."""
        broker = _make_broker()
        broker.get_positions.return_value = [
            _make_position("SPY", "MARGIN_CALL_LIQUIDATION", 5)
        ]
        with caplog.at_level("ERROR"):
            await spike._flatten(broker, "SPY")
        broker.place_order.assert_not_awaited()
        assert any("UNKNOWN side" in rec.message for rec in caplog.records)

    def test_flatten_source_does_not_use_absolute_value_trap(
        self, spike
    ) -> None:
        """RULE-038 grep-guard: ensure the prior side-blind pattern
        `p.shares > 0` (without a `p.side` predicate) does not return."""
        import inspect

        src = inspect.getsource(spike._flatten)
        # The three valid usage patterns combine side + shares:
        #   `p.side == OrderSide.BUY and p.shares > 0`
        #   `p.side == OrderSide.SELL and p.shares > 0`
        # The defensive zero check is `p.shares == 0`.
        # Reject any bare `p.shares > 0` that's NOT preceded by `side ==`.
        for line in src.split("\n"):
            stripped = line.strip()
            if "p.shares > 0" in stripped and "p.side" not in stripped:
                pytest.fail(
                    f"Side-blind pattern detected (DEF-237 regression): "
                    f"{stripped!r}"
                )


# ---------------------------------------------------------------------------
# Cat A.2 — pre-spike position-sweep refusal-to-start gate (grep-guards)
# ---------------------------------------------------------------------------


class TestPreSpikeSweepGate:
    """The pre-spike sweep gate's structural presence is the load-bearing
    invariant — running main_async() requires a live IBKR connection so
    behavioral tests aren't feasible. Grep-guards are the regression
    surface."""

    def test_main_async_calls_get_positions_after_connect(self) -> None:
        src = SPIKE_SCRIPT.read_text()
        # The gate's structural shape: after `await broker.connect()`, the
        # next significant async call against the broker (within main_async)
        # must be `await broker.get_positions()`.
        connect_idx = src.find("await broker.connect()")
        assert connect_idx > -1
        get_positions_idx = src.find(
            "pre_positions = await broker.get_positions()", connect_idx
        )
        assert get_positions_idx > -1, (
            "Pre-spike sweep gate missing: `pre_positions = await "
            "broker.get_positions()` not found after `broker.connect()`."
        )
        # And the qualify_contracts call must come AFTER the gate (the
        # gate gates everything downstream).
        qualify_idx = src.find("qualify_contracts", get_positions_idx)
        assert qualify_idx > -1
        assert get_positions_idx < qualify_idx

    def test_pre_spike_sweep_gate_filters_nonzero_shares(self) -> None:
        src = SPIKE_SCRIPT.read_text()
        # The filter must use `p.shares > 0`, not raw `p.position` or
        # `p._raw_ib_pos.position` (which doesn't exist; verdict literal
        # was Option-A path, this codebase is Option-B per the Work Journal
        # disposition).
        assert "[p for p in pre_positions if p.shares > 0]" in src

    def test_pre_spike_sweep_gate_calls_sys_exit_2(self) -> None:
        src = SPIKE_SCRIPT.read_text()
        # The gate's refusal-to-start fires sys.exit(2). The error log
        # cites scripts/ibkr_close_all_positions.py + DEF-239 as the
        # operator's verified-safe flatten path.
        gate_block = re.search(
            r"if nonzero:.*?sys\.exit\(2\)",
            src,
            re.DOTALL,
        )
        assert gate_block is not None, "Sweep gate sys.exit(2) not found"
        gate_text = gate_block.group(0)
        assert "ibkr_close_all_positions.py" in gate_text
        assert "DEF-239" in gate_text


# ---------------------------------------------------------------------------
# Cat A.1 — _verify_aux_price logging + Mode A trial body changes
# ---------------------------------------------------------------------------


class TestVerifyAuxPriceLogging:
    """_verify_aux_price logs the observed auxPrice unconditionally."""

    def test_verify_aux_price_logs_on_match(self, spike, caplog) -> None:
        broker = MagicMock()
        broker._ulid_to_ibkr = {"stop_ulid_x": 42}
        trade = MagicMock()
        trade.order.orderId = 42
        trade.order.auxPrice = 100.50
        broker._ib.openTrades = MagicMock(return_value=[trade])
        with caplog.at_level("INFO"):
            result = spike._verify_aux_price(broker, "stop_ulid_x", 100.50)
        assert result is True
        assert any(
            "actual_auxPrice" in rec.message and "matched=True" in rec.message
            for rec in caplog.records
        )

    def test_verify_aux_price_logs_on_mismatch(self, spike, caplog) -> None:
        broker = MagicMock()
        broker._ulid_to_ibkr = {"stop_ulid_x": 42}
        trade = MagicMock()
        trade.order.orderId = 42
        trade.order.auxPrice = 95.00  # Stale / unpropagated.
        broker._ib.openTrades = MagicMock(return_value=[trade])
        with caplog.at_level("INFO"):
            result = spike._verify_aux_price(broker, "stop_ulid_x", 100.50)
        assert result is False
        assert any(
            "actual_auxPrice" in rec.message
            and "95.0" in rec.message
            and "matched=False" in rec.message
            for rec in caplog.records
        )

    def test_verify_aux_price_logs_on_unknown_ulid(self, spike, caplog) -> None:
        broker = MagicMock()
        broker._ulid_to_ibkr = {}
        with caplog.at_level("INFO"):
            result = spike._verify_aux_price(broker, "unknown", 100.0)
        assert result is False
        assert any(
            "not in _ulid_to_ibkr" in rec.message for rec in caplog.records
        )

    def test_verify_aux_price_logs_on_order_not_in_open_trades(
        self, spike, caplog
    ) -> None:
        broker = MagicMock()
        broker._ulid_to_ibkr = {"stop_ulid_x": 42}
        broker._ib.openTrades = MagicMock(return_value=[])
        with caplog.at_level("INFO"):
            result = spike._verify_aux_price(broker, "stop_ulid_x", 100.0)
        assert result is False
        assert any(
            "not found in openTrades" in rec.message for rec in caplog.records
        )


class TestModeATrialBodyChanges:
    """The Mode A trial body extends the propagation wait to 2.5s and
    force-pulls broker state via reqOpenOrders before sampling."""

    def test_mode_a_trial_waits_2_5_seconds_before_sampling(self) -> None:
        src = SPIKE_SCRIPT.read_text()
        # The Cat A.1 fix replaces `await asyncio.sleep(0.5)` with
        # `await asyncio.sleep(2.5)` in the Mode A trial body. Find the
        # _measure_mode_a body and assert the wait is 2.5s.
        mode_a_match = re.search(
            r"async def _measure_mode_a\b.*?(?=\n(?:async )?def |\Z)",
            src,
            re.DOTALL,
        )
        assert mode_a_match is not None
        body = mode_a_match.group(0)
        assert "asyncio.sleep(2.5)" in body, (
            "Cat A.1 (DEF-236) regression: Mode A trial body must wait 2.5s "
            "(was 500ms) before sampling auxPrice."
        )
        assert "asyncio.sleep(0.5)" not in body or body.count(
            "asyncio.sleep(0.5)"
        ) == 0, "Stale 500ms sleep still present in Mode A body."

    def test_mode_a_trial_calls_req_open_orders_before_verify(self) -> None:
        src = SPIKE_SCRIPT.read_text()
        mode_a_match = re.search(
            r"async def _measure_mode_a\b.*?(?=\n(?:async )?def |\Z)",
            src,
            re.DOTALL,
        )
        assert mode_a_match is not None
        body = mode_a_match.group(0)
        # The reqOpenOrders call must precede the _verify_aux_price call.
        req_idx = body.find("reqOpenOrders()")
        verify_idx = body.find("_verify_aux_price(")
        assert req_idx > -1, "reqOpenOrders() not called in Mode A trial body"
        assert verify_idx > -1
        assert req_idx < verify_idx, (
            "reqOpenOrders() must precede _verify_aux_price() per Cat A.1."
        )


class TestCatA2DocstringJudgmentCallNote:
    """The Cat A.2 fix's audit-trail Judgment-Call lives in `_flatten()`'s
    docstring referencing the verdict, the IMPROMPTU-04 production
    precedent, and the Work Journal Option-B disposition."""

    def test_flatten_docstring_cites_imprompt_04_precedent(self, spike) -> None:
        doc = spike._flatten.__doc__ or ""
        assert "IMPROMPTU-04" in doc
        assert "DEF-237" in doc

    def test_flatten_docstring_cites_option_b_work_journal_disposition(
        self, spike
    ) -> None:
        doc = spike._flatten.__doc__ or ""
        assert "Option-B" in doc or "Option B" in doc

    def test_flatten_docstring_cites_raw_ib_pos_grep_finding(
        self, spike
    ) -> None:
        doc = spike._flatten.__doc__ or ""
        assert "_raw_ib_pos" in doc
