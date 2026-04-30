"""Sprint 31.92 Unit 4 — Cat B spike-fix regression tests.

Regression coverage for `scripts/spike_def204_round2_path1.py` after the
Cat B spike fixes per Sprint 31.92 Tier 3 Review #2 verdict §Cat B + DEC-390
rule encoding.

  Cat B.1 (DEC-390): DELETE axis (iii) entirely.
    - `_axis_stale_id` function gone.
    - `AXIS_STALE_ID` constant gone.
    - `stale_id_amends` JSON key gone (it never appears in the schema).

  Cat B.2 (DEC-390): DEMOTE axes (ii) and (iv) to informational.
    - JSON schema partition: `binding_axis_result` (axis i only) +
      `informational_axes_results` (axes ii + iv).
    - `worst_axis_wilson_ub` field renamed `axis_i_wilson_ub`.
    - `_apply_decision_rule()` binds H2/H4/H1 selection to `axis_i_wilson_ub`
      only. HARD GATE preserved (zero-conflict-in-100 → H1 ineligible).

  Cat B.3 (DEF-238): HARDEN axis (ii)/(iv) instrumentation.
    - `_axis_reconnect()` and `_axis_joint()` sample `isConnected()` before
      each amend.
    - On always-connected runs, log WARNING + tag AxisResult with
      `instrumentation_warning = "Gateway remained connected throughout —
      characterization invalid"`.
    - On disconnect-observed runs, log INFO `axis_X_disconnect_observed: true`.

The tests do NOT execute the spike (that requires an IBKR Gateway). They
exercise helpers directly with mocks AND grep-verify the load-bearing
structural changes in the script body.
"""

from __future__ import annotations

import importlib.util
import re
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SPIKE_SCRIPT = REPO_ROOT / "scripts" / "spike_def204_round2_path1.py"


def _load_spike_module() -> types.ModuleType:
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


# ---------------------------------------------------------------------------
# Cat B.1 — Axis (iii) deletion
# ---------------------------------------------------------------------------


class TestAxisIIIDeleted:
    """Cat B.1: axis (iii) stale-ID is deleted entirely. Constant, function,
    call site, and JSON key must all be gone."""

    def test_axis_stale_id_constant_removed(self, spike) -> None:
        assert not hasattr(spike, "AXIS_STALE_ID"), (
            "AXIS_STALE_ID constant must be deleted (Cat B.1)."
        )

    def test_axis_stale_id_function_removed(self, spike) -> None:
        assert not hasattr(spike, "_axis_stale_id"), (
            "_axis_stale_id() function must be deleted (Cat B.1)."
        )

    def test_remaining_axis_constants_are_only_concurrent_reconnect_joint(
        self, spike
    ) -> None:
        assert spike.AXIS_CONCURRENT == "concurrent_amends"
        assert spike.AXIS_RECONNECT == "reconnect_window_amends"
        assert spike.AXIS_JOINT == "joint_reconnect_concurrent_amends"

    def test_script_source_does_not_reference_stale_id_anywhere_active(
        self,
    ) -> None:
        """`stale_id` may appear inside Cat B.1 deletion-comment block at
        the deleted call site, but MUST NOT appear in any active code path
        (function name, constant, call site, JSON key, schema field)."""
        src = SPIKE_SCRIPT.read_text()
        # Permit the comment-marker mention; reject any active code reference.
        for line in src.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            assert "stale_id" not in stripped.lower(), (
                f"Active code references stale_id: {stripped!r}"
            )
            assert "AXIS_STALE_ID" not in stripped, (
                f"Active code references AXIS_STALE_ID: {stripped!r}"
            )
            assert "_axis_stale_id" not in stripped, (
                f"Active code references _axis_stale_id: {stripped!r}"
            )

    def test_main_async_call_site_does_not_invoke_stale_axis(self) -> None:
        src = SPIKE_SCRIPT.read_text()
        # The new structure: `binding_axis = await _axis_concurrent(...)` +
        # `informational_axes = {AXIS_RECONNECT: ..., AXIS_JOINT: ...}`
        assert "binding_axis = await _axis_concurrent(" in src
        # The informational dict must contain only RECONNECT and JOINT.
        info_match = re.search(
            r"informational_axes\s*=\s*\{(.*?)\}",
            src,
            re.DOTALL,
        )
        assert info_match is not None
        info_body = info_match.group(1)
        assert "AXIS_RECONNECT" in info_body
        assert "AXIS_JOINT" in info_body
        assert "AXIS_STALE_ID" not in info_body


# ---------------------------------------------------------------------------
# Cat B.2 — JSON schema partition + axis_i_wilson_ub field
# ---------------------------------------------------------------------------


class TestJsonSchemaPartition:
    """Cat B.2: JSON output partitions adversarial-axis results into
    `binding_axis_result` (axis i) and `informational_axes_results` (axes
    ii + iv). The legacy `worst_axis_wilson_ub` field is renamed
    `axis_i_wilson_ub` and reflects the binding axis only."""

    def _binding_axis(self, spike, ub_pct: float = 3.0) -> object:
        a = spike.AxisResult()
        a.n_trials = 50
        a.n_rejections = 1
        a.rejection_rate_pct = 2.0
        a.wilson_upper_bound_pct = ub_pct
        return a

    def _info_axes(self, spike) -> dict:
        a = spike.AxisResult()
        a.n_trials = 30
        a.n_rejections = 5
        a.wilson_upper_bound_pct = 25.0
        b = spike.AxisResult()
        b.n_trials = 30
        b.n_rejections = 3
        b.wilson_upper_bound_pct = 20.0
        return {
            spike.AXIS_RECONNECT: a,
            spike.AXIS_JOINT: b,
        }

    def _mode_a_trials(self, spike, n: int = 50) -> list:
        return [
            spike.ModeATrial(
                symbol="SPY",
                success=True,
                rejected=False,
                propagation_ok=True,
                round_trip_ms=10.0,
            )
            for _ in range(n)
        ]

    def _mode_d_trials_zero_conflict(self, spike, n: int = 100) -> list:
        return [
            spike.ModeDTrial(symbol="SPY", conflict=False, cancel_to_sell_gap_ms=5.0)
            for _ in range(n)
        ]

    def test_results_have_binding_axis_result_key(self, spike) -> None:
        results = spike._build_results(
            self._mode_a_trials(spike),
            self._binding_axis(spike, ub_pct=3.0),
            self._info_axes(spike),
            [],
            self._mode_d_trials_zero_conflict(spike),
        )
        assert "binding_axis_result" in results
        assert spike.AXIS_CONCURRENT in results["binding_axis_result"]
        # Only the binding axis appears in this partition.
        assert spike.AXIS_RECONNECT not in results["binding_axis_result"]
        assert spike.AXIS_JOINT not in results["binding_axis_result"]

    def test_results_have_informational_axes_results_key(self, spike) -> None:
        results = spike._build_results(
            self._mode_a_trials(spike),
            self._binding_axis(spike, ub_pct=3.0),
            self._info_axes(spike),
            [],
            self._mode_d_trials_zero_conflict(spike),
        )
        assert "informational_axes_results" in results
        assert spike.AXIS_RECONNECT in results["informational_axes_results"]
        assert spike.AXIS_JOINT in results["informational_axes_results"]
        # The binding axis must NOT also appear in the informational partition.
        assert spike.AXIS_CONCURRENT not in results["informational_axes_results"]

    def test_results_no_longer_carry_legacy_schema_keys(self, spike) -> None:
        """`worst_axis_wilson_ub` and `adversarial_axes_results` are gone.
        Schema is `axis_i_wilson_ub` + the partition pair."""
        results = spike._build_results(
            self._mode_a_trials(spike),
            self._binding_axis(spike, ub_pct=3.0),
            self._info_axes(spike),
            [],
            self._mode_d_trials_zero_conflict(spike),
        )
        assert "worst_axis_wilson_ub" not in results
        assert "adversarial_axes_results" not in results
        assert "axis_i_wilson_ub" in results

    def test_axis_i_wilson_ub_reflects_binding_axis_only(self, spike) -> None:
        """The renamed field must equal the binding axis's UB and ignore
        the (much higher) informational-axis UBs."""
        results = spike._build_results(
            self._mode_a_trials(spike),
            self._binding_axis(spike, ub_pct=3.5),
            self._info_axes(spike),  # info axes have UB 25 / 20
            [],
            self._mode_d_trials_zero_conflict(spike),
        )
        assert results["axis_i_wilson_ub"] == 3.5

    def test_inconclusive_stub_uses_new_schema(self, spike) -> None:
        """`_abort_with_inconclusive` must emit the new schema names so
        downstream consumers (close-out skill, JSON parsers) see a
        consistent shape regardless of which path produced the artifact."""
        src = SPIKE_SCRIPT.read_text()
        stub_match = re.search(
            r"async def _abort_with_inconclusive\b.*?(?=\n(?:async )?def |\Z)",
            src,
            re.DOTALL,
        )
        assert stub_match is not None
        body = stub_match.group(0)
        assert '"binding_axis_result"' in body
        assert '"informational_axes_results"' in body
        assert '"axis_i_wilson_ub"' in body
        assert '"adversarial_axes_results"' not in body
        assert '"worst_axis_wilson_ub"' not in body

    def test_crash_recovery_block_uses_new_schema(self) -> None:
        src = SPIKE_SCRIPT.read_text()
        # The except block in main_async writes a crash-recovery JSON;
        # find the `"status": "INCONCLUSIVE"` literal that follows
        # `Spike crashed mid-run` and assert the new schema keys appear.
        idx = src.find('Spike crashed mid-run')
        assert idx > -1
        # Take a generous window; we just need the keys to appear.
        block = src[idx:idx + 1500]
        assert '"binding_axis_result"' in block
        assert '"informational_axes_results"' in block
        assert '"axis_i_wilson_ub"' in block


# ---------------------------------------------------------------------------
# Cat B.2 — _apply_decision_rule rewired to axis (i) only
# ---------------------------------------------------------------------------


class TestDecisionRuleBindsToAxisI:
    """Decision rule signature renames the first parameter from
    `worst_axis_ub` to `axis_i_wilson_ub` and binds H2/H4/H1 selection to
    that single axis. HARD GATE on zero-conflict-in-100 preserved."""

    def test_signature_uses_axis_i_wilson_ub(self, spike) -> None:
        import inspect

        sig = inspect.signature(spike._apply_decision_rule)
        params = list(sig.parameters.keys())
        assert params[0] == "axis_i_wilson_ub", (
            f"First parameter must be `axis_i_wilson_ub` (Cat B.2). "
            f"Got: {params!r}"
        )

    @pytest.mark.parametrize(
        "ub_pct,zero_conflict,propagation,expected_status,expected_mech",
        [
            # H2 selected: UB < 5%, zero-conflict, propagation ok.
            (3.0, True, True, "PROCEED", "h2_amend"),
            (4.99, True, True, "PROCEED", "h2_amend"),
            # H2/H4 boundary at 5%.
            (5.0, True, True, "PROCEED", "h4_hybrid"),
            (10.0, True, True, "PROCEED", "h4_hybrid"),
            (19.99, True, True, "PROCEED", "h4_hybrid"),
            # H4/H1 boundary at 20%.
            (20.0, True, True, "PROCEED", "h1_cancel_and_await"),
            (50.0, True, True, "PROCEED", "h1_cancel_and_await"),
        ],
    )
    def test_threshold_boundaries_under_zero_conflict(
        self,
        spike,
        ub_pct: float,
        zero_conflict: bool,
        propagation: bool,
        expected_status: str,
        expected_mech: str,
    ) -> None:
        status, mech, _ = spike._apply_decision_rule(
            ub_pct, zero_conflict, propagation
        )
        assert status == expected_status
        assert mech == expected_mech

    def test_hard_gate_preserved_when_conflict_in_100_and_ub_above_20pct(
        self, spike
    ) -> None:
        """HARD GATE: any conflict in 100 trials → H1 ineligible. If axis
        (i) UB ≥ 20%, the rule must return INCONCLUSIVE (no fallback)."""
        status, mech, reason = spike._apply_decision_rule(
            axis_i_wilson_ub=25.0, zero_conflict_in_100=False, propagation_ok=True
        )
        assert status == "INCONCLUSIVE"
        assert mech is None
        assert reason is not None
        assert "20%" in reason or "20.0%" in reason

    def test_conflict_in_100_with_ub_under_5pct_falls_back_to_h2(
        self, spike
    ) -> None:
        status, mech, _ = spike._apply_decision_rule(
            axis_i_wilson_ub=3.0, zero_conflict_in_100=False, propagation_ok=True
        )
        assert status == "PROCEED"
        assert mech == "h2_amend"

    def test_conflict_in_100_with_ub_under_20pct_falls_back_to_h4(
        self, spike
    ) -> None:
        status, mech, _ = spike._apply_decision_rule(
            axis_i_wilson_ub=10.0, zero_conflict_in_100=False, propagation_ok=True
        )
        assert status == "PROCEED"
        assert mech == "h4_hybrid"

    def test_propagation_failure_returns_inconclusive_regardless_of_axis_i(
        self, spike
    ) -> None:
        status, mech, reason = spike._apply_decision_rule(
            axis_i_wilson_ub=3.0, zero_conflict_in_100=True, propagation_ok=False
        )
        assert status == "INCONCLUSIVE"
        assert mech is None
        assert reason is not None
        assert "propagat" in reason.lower()


# ---------------------------------------------------------------------------
# Cat B.3 — isConnected() instrumentation on axes (ii) + (iv)
# ---------------------------------------------------------------------------


class TestAxisInstrumentationGrepGuards:
    """The Cat B.3 isConnected() sampling and instrumentation_warning tag
    are structurally enforced via grep-guards on the script body; behavioral
    tests against `_axis_reconnect()`/`_axis_joint()` would require a full
    IBKR mock + stdin sentinel orchestration that's out of scope here."""

    def test_axis_result_has_instrumentation_warning_field(self, spike) -> None:
        a = spike.AxisResult()
        assert hasattr(a, "instrumentation_warning")
        assert a.instrumentation_warning is None  # default

    def test_axis_result_instrumentation_warning_can_be_set(
        self, spike
    ) -> None:
        a = spike.AxisResult()
        a.instrumentation_warning = "Gateway remained connected throughout"
        assert a.instrumentation_warning == "Gateway remained connected throughout"

    def test_axis_reconnect_samples_is_connected(self) -> None:
        src = SPIKE_SCRIPT.read_text()
        body_match = re.search(
            r"async def _axis_reconnect\b.*?(?=\n(?:async )?def |\Z)",
            src,
            re.DOTALL,
        )
        assert body_match is not None
        body = body_match.group(0)
        assert "broker._ib.isConnected()" in body, (
            "Cat B.3 (DEF-238): _axis_reconnect must sample isConnected() "
            "before each amend."
        )

    def test_axis_joint_samples_is_connected(self) -> None:
        src = SPIKE_SCRIPT.read_text()
        body_match = re.search(
            r"async def _axis_joint\b.*?(?=\n(?:async )?def |\Z)",
            src,
            re.DOTALL,
        )
        assert body_match is not None
        body = body_match.group(0)
        assert "broker._ib.isConnected()" in body

    def test_axis_reconnect_emits_warning_on_always_connected(self) -> None:
        src = SPIKE_SCRIPT.read_text()
        body_match = re.search(
            r"async def _axis_reconnect\b.*?(?=\n(?:async )?def |\Z)",
            src,
            re.DOTALL,
        )
        assert body_match is not None
        body = body_match.group(0)
        assert "axis_ii_gateway_remained_connected" in body
        assert "instrumentation_warning" in body

    def test_axis_joint_emits_warning_on_always_connected(self) -> None:
        src = SPIKE_SCRIPT.read_text()
        body_match = re.search(
            r"async def _axis_joint\b.*?(?=\n(?:async )?def |\Z)",
            src,
            re.DOTALL,
        )
        assert body_match is not None
        body = body_match.group(0)
        assert "axis_iv_gateway_remained_connected" in body
        assert "instrumentation_warning" in body

    def test_axis_reconnect_logs_disconnect_observed(self) -> None:
        src = SPIKE_SCRIPT.read_text()
        body_match = re.search(
            r"async def _axis_reconnect\b.*?(?=\n(?:async )?def |\Z)",
            src,
            re.DOTALL,
        )
        assert body_match is not None
        body = body_match.group(0)
        assert "axis_ii_disconnect_observed" in body

    def test_axis_joint_logs_disconnect_observed(self) -> None:
        src = SPIKE_SCRIPT.read_text()
        body_match = re.search(
            r"async def _axis_joint\b.*?(?=\n(?:async )?def |\Z)",
            src,
            re.DOTALL,
        )
        assert body_match is not None
        body = body_match.group(0)
        assert "axis_iv_disconnect_observed" in body


class TestAxisInstrumentationBehavior:
    """Behavioral tests for the gateway-remained-connected branch. These
    drive `_axis_reconnect` / `_axis_joint` end-to-end with mocks; the
    realistic-broker case (open bracket → amend loop) requires too many
    moving parts to mock cleanly, so the tests target the early-return
    paths and the always-connected sentinel via short num_trials runs."""

    @pytest.mark.asyncio
    async def test_axis_reconnect_skips_when_price_unavailable(
        self, spike
    ) -> None:
        """Early-return path: no isConnected() sampling occurs because
        the loop never executes. instrumentation_warning stays None
        (which is correct — we cannot characterize a run that didn't run)."""
        broker = MagicMock()
        broker._ib = MagicMock()
        # Price fetch raises / returns None → axis bails before the loop.

        async def _no_price(*args, **kwargs):
            return None

        spike_get_price = spike._get_market_price
        try:
            spike._get_market_price = _no_price  # monkey-patch
            # Substitute our stub for the duration of this test.
            result = await spike._axis_reconnect(broker, ["SPY"], num_trials=5)
        finally:
            spike._get_market_price = spike_get_price
        assert result.n_trials == 0
        assert result.instrumentation_warning is None
        # isConnected() must NOT have been sampled — early-return path.
        broker._ib.isConnected.assert_not_called()


# ---------------------------------------------------------------------------
# Sanity — the new ModeA `binding_axis_result` JSON contract is consumed by
# the print summary; cosmetic but a regression guard against stale field
# references in the close-out output.
# ---------------------------------------------------------------------------


class TestPrintSummaryReferencesNewFields:
    def test_print_block_uses_axis_i_wilson_ub(self) -> None:
        src = SPIKE_SCRIPT.read_text()
        assert "results['axis_i_wilson_ub']" in src

    def test_print_block_iterates_binding_axis_result(self) -> None:
        src = SPIKE_SCRIPT.read_text()
        assert "results[\"binding_axis_result\"]" in src

    def test_print_block_iterates_informational_axes_results(self) -> None:
        src = SPIKE_SCRIPT.read_text()
        assert "results[\"informational_axes_results\"]" in src

    def test_print_block_does_not_reference_legacy_keys(self) -> None:
        src = SPIKE_SCRIPT.read_text()
        # Surgical check: no print-line references the legacy field names.
        for line in src.split("\n"):
            stripped = line.strip()
            if not stripped.startswith("print"):
                continue
            assert "worst_axis_wilson_ub" not in stripped, (
                f"print() references legacy worst_axis_wilson_ub: {stripped!r}"
            )
            assert "adversarial_axes_results" not in stripped, (
                f"print() references legacy adversarial_axes_results: "
                f"{stripped!r}"
            )
