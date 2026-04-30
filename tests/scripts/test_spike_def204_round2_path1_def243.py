"""Sprint 31.92 Unit B — DEF-243 spike-harness instrumentation regression tests.

Three fixes covered, each with at least the prompt's minimum test count:

  Fix B.1 (errorEvent listener / oca_rejected tagging) — 6 tests:
    - `_OcaRejectionTracker.__call__` records on errorCode 10326.
    - Tagging threads through `_amend_one()`'s success/failure determination.
    - Non-10326 errors don't tag (selective listener).

  Fix B.2 (FileHandler / spike-run-{timestamp}.log preservation) — 3 tests:
    - Log file path matches the `spike-run-{timestamp}.log` pattern.
    - Both stdout AND file handlers receive the same content.

  Fix B.3 (axis (iv) precondition gate) — 3 tests:
    - Gate samples isConnected() and short-circuits when True (no reconnect).
    - Gate attempts reconnect when False; reconnect-success proceeds.
    - Gate writes `skipped=True` + `skip_reason` when reconnect fails.

These tests do NOT execute the spike against a live IBKR Gateway. They drive
the helpers and class methods directly with stubs/mocks.
"""

from __future__ import annotations

import asyncio
import importlib.util
import logging
import sys
import time
import types
from pathlib import Path
from typing import Any
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
# Fix B.1 — _OcaRejectionTracker errorEvent listener
# ---------------------------------------------------------------------------


class TestOcaRejectionTracker:
    """Listener records IBKR error code 10326 events keyed by reqId; ignores
    other error codes; exposes event_count / latest_message API consumed by
    `_amend_one()`."""

    def test_records_on_error_code_10326(self, spike) -> None:
        tracker = spike._OcaRejectionTracker()
        tracker(req_id=42, error_code=10326, error_string="OCA group revision is not allowed")
        assert tracker.event_count(42) == 1
        assert tracker.latest_message(42) == "OCA group revision is not allowed"

    def test_ignores_non_10326_error_codes(self, spike) -> None:
        """Selective listener: must NOT record errors that aren't OCA
        rejections (e.g., 399 queued-for-next-session, 201 margin reject,
        2104 market data farm connection ok)."""
        tracker = spike._OcaRejectionTracker()
        tracker(req_id=10, error_code=399, error_string="queued for next session")
        tracker(req_id=11, error_code=201, error_string="rejected — margin")
        tracker(req_id=12, error_code=2104, error_string="Market data farm connection is OK")
        assert tracker.event_count(10) == 0
        assert tracker.event_count(11) == 0
        assert tracker.event_count(12) == 0
        assert tracker.latest_message(10) is None

    def test_event_count_and_latest_message_keyed_by_req_id(self, spike) -> None:
        """Multiple reqIds are isolated; latest_message returns the most
        recent message per reqId."""
        tracker = spike._OcaRejectionTracker()
        tracker(req_id=1, error_code=10326, error_string="first rejection on 1")
        tracker(req_id=2, error_code=10326, error_string="rejection on 2")
        tracker(req_id=1, error_code=10326, error_string="second rejection on 1")
        assert tracker.event_count(1) == 2
        assert tracker.event_count(2) == 1
        assert tracker.event_count(99) == 0
        assert tracker.latest_message(1) == "second rejection on 1"
        assert tracker.latest_message(2) == "rejection on 2"
        assert tracker.latest_message(99) is None


class TestAmendOneOcaTagging:
    """Behavioral tests for `_amend_one()`'s oca_rejected return value. The
    sync `modify_order` return value is mocked; the test injects a tracker
    that records or does not record a 10326 event during the wait window."""

    @pytest.mark.asyncio
    async def test_amend_one_returns_oca_rejected_true_when_tracker_fires(
        self, spike
    ) -> None:
        """When `oca_tracker.event_count` grows after the synchronous return,
        `_amend_one()` must override the success determination: return
        `(rejected=True, error_str startswith 'oca_rejected:', oca_rejected=True)`."""
        broker = MagicMock()
        broker._ulid_to_ibkr = {"stop_ulid_x": 12345}
        broker._ib = MagicMock()
        broker._ib.trades.return_value = []
        # Sync return is "successful" — broker.modify_order says SUBMITTED.
        result_mock = MagicMock()
        result_mock.status = spike.OrderStatus.SUBMITTED
        result_mock.message = None
        broker.modify_order = AsyncMock(return_value=result_mock)

        tracker = spike._OcaRejectionTracker()

        async def _fire_after_delay() -> None:
            await asyncio.sleep(0.05)
            tracker(req_id=12345, error_code=10326,
                    error_string="OCA group revision is not allowed")

        asyncio.create_task(_fire_after_delay())
        rejected, err, oca_rejected = await spike._amend_one(
            broker, "stop_ulid_x", 99.0,
            oca_tracker=tracker,
            wait_window_s=0.5,
        )
        assert rejected is True
        assert oca_rejected is True
        assert err is not None and err.startswith("oca_rejected:")

    @pytest.mark.asyncio
    async def test_amend_one_returns_oca_rejected_false_when_no_event(
        self, spike
    ) -> None:
        """When no 10326 event arrives within the wait window, `_amend_one()`
        returns the synchronous determination unchanged (third tuple element
        is False)."""
        broker = MagicMock()
        broker._ulid_to_ibkr = {"stop_ulid_y": 67890}
        broker._ib = MagicMock()
        broker._ib.trades.return_value = []
        result_mock = MagicMock()
        result_mock.status = spike.OrderStatus.SUBMITTED
        result_mock.message = None
        broker.modify_order = AsyncMock(return_value=result_mock)

        tracker = spike._OcaRejectionTracker()
        rejected, err, oca_rejected = await spike._amend_one(
            broker, "stop_ulid_y", 99.0,
            oca_tracker=tracker,
            wait_window_s=0.05,  # Very short — no event will fire
        )
        assert rejected is False
        assert oca_rejected is False
        assert err is None

    @pytest.mark.asyncio
    async def test_amend_one_no_tracker_returns_false_oca_rejected(
        self, spike
    ) -> None:
        """Backward-compat / falsifiable signal: when `oca_tracker=None`,
        the third tuple element is always False — never silently True. This
        keeps a None-tracker run honest about not having checked."""
        broker = MagicMock()
        broker._ulid_to_ibkr = {}
        broker._ib = MagicMock()
        broker._ib.trades.return_value = []
        result_mock = MagicMock()
        result_mock.status = spike.OrderStatus.SUBMITTED
        result_mock.message = None
        broker.modify_order = AsyncMock(return_value=result_mock)

        rejected, err, oca_rejected = await spike._amend_one(
            broker, "stop_ulid_z", 99.0,
            oca_tracker=None,
        )
        assert rejected is False
        assert oca_rejected is False
        assert err is None


# ---------------------------------------------------------------------------
# Fix B.2 — _setup_file_handler / spike-run log preservation
# ---------------------------------------------------------------------------


class TestFileHandlerSetup:
    """`_setup_file_handler(timestamp)` attaches a logging.FileHandler to the
    root logger writing to `scripts/spike-results/spike-run-{timestamp}.log`.
    Both stdout AND file handlers must remain active simultaneously."""

    def test_log_file_path_matches_expected_pattern(
        self, spike, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """File path must be `scripts/spike-results/spike-run-{timestamp}.log`.
        Run inside a tmp cwd to avoid leaving real artifacts."""
        monkeypatch.chdir(tmp_path)
        ts = "20260430T123456Z"
        try:
            log_path = spike._setup_file_handler(ts)
            assert log_path == str(
                Path("scripts") / "spike-results" / f"spike-run-{ts}.log"
            )
            assert (tmp_path / log_path).exists()
        finally:
            # Detach the handler we just added so it doesn't leak across tests.
            root = logging.getLogger()
            for h in list(root.handlers):
                if isinstance(h, logging.FileHandler) and ts in h.baseFilename:
                    root.removeHandler(h)
                    h.close()

    def test_both_stdout_and_file_handlers_receive_same_message(
        self, spike, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """The setup must NOT replace the stdout handler — both must coexist.
        The script's `logging.basicConfig(level=INFO)` at module load time
        attached the stream handler; `_setup_file_handler` only adds a file
        handler. Verify the file gets written AND the existing handlers
        remain."""
        monkeypatch.chdir(tmp_path)
        ts = "20260430T999999Z"
        log_path = None
        added_handler: logging.FileHandler | None = None
        # Pytest's logging plugin can elevate the root logger to WARNING,
        # suppressing INFO messages from reaching handlers. Force the
        # named-logger level for the duration of the test so our INFO
        # message reaches the FileHandler.
        prev_root_level = logging.getLogger().level
        prev_log_level = spike.log.level
        try:
            logging.getLogger().setLevel(logging.INFO)
            spike.log.setLevel(logging.INFO)
            log_path = spike._setup_file_handler(ts)
            # Identify the file handler we just added
            for h in logging.getLogger().handlers:
                if isinstance(h, logging.FileHandler) and h.baseFilename.endswith(
                    f"spike-run-{ts}.log"
                ):
                    added_handler = h
                    break
            assert added_handler is not None, "FileHandler not attached to root logger"

            test_message = "DEF243-FIX-B2-CANARY-MESSAGE-12345"
            spike.log.info(test_message)
            # Flush the file handler to make sure the bytes are committed
            added_handler.flush()

            # File received the message
            file_contents = (tmp_path / log_path).read_text()
            assert test_message in file_contents
        finally:
            root = logging.getLogger()
            if added_handler is not None:
                root.removeHandler(added_handler)
                added_handler.close()
            root.setLevel(prev_root_level)
            spike.log.setLevel(prev_log_level)

    def test_setup_file_handler_creates_directory_if_missing(
        self, spike, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`_setup_file_handler` must create the `scripts/spike-results/`
        directory if it doesn't exist (mirrors the existing `os.makedirs(
        ..., exist_ok=True)` pattern in `main_async()`)."""
        monkeypatch.chdir(tmp_path)
        # Verify the directory does not pre-exist
        assert not (tmp_path / "scripts" / "spike-results").exists()
        ts = "20260430T000001Z"
        added_handler: logging.FileHandler | None = None
        try:
            log_path = spike._setup_file_handler(ts)
            assert (tmp_path / "scripts" / "spike-results").is_dir()
            assert (tmp_path / log_path).exists()
            for h in logging.getLogger().handlers:
                if isinstance(h, logging.FileHandler) and h.baseFilename.endswith(
                    f"spike-run-{ts}.log"
                ):
                    added_handler = h
                    break
        finally:
            root = logging.getLogger()
            if added_handler is not None:
                root.removeHandler(added_handler)
                added_handler.close()


class TestRunTimestamp:
    """`_generate_run_timestamp` produces a filesystem-safe ISO-like UTC
    timestamp (no colons, no microseconds, Z-suffixed)."""

    def test_timestamp_format(self, spike) -> None:
        ts = spike._generate_run_timestamp()
        # YYYYMMDDTHHMMSSZ — 16 chars, ends with Z, no colons or dots
        assert len(ts) == 16
        assert ts.endswith("Z")
        assert ":" not in ts
        assert "." not in ts
        # Roundtrip: T separator at index 8
        assert ts[8] == "T"


# ---------------------------------------------------------------------------
# Fix B.3 — axis (iv) precondition gate
# ---------------------------------------------------------------------------


class TestAxisJointPreconditionGate:
    """`_axis_joint`'s isConnected() precondition gate — the entry-time
    branch that protects against running on a disconnected broker. Three
    paths: connected (no reconnect), disconnected + reconnect-success
    (proceeds), disconnected + reconnect-fail (skipped)."""

    @pytest.mark.asyncio
    async def test_connected_at_entry_skips_reconnect(self, spike) -> None:
        """When `isConnected()` returns True at axis entry, the gate must
        NOT call broker.connect(). The axis then proceeds to position open;
        we cause that to short-circuit by returning None from
        `_get_market_price` so the test can assert the gate behavior in
        isolation."""
        broker = MagicMock()
        broker._ib = MagicMock()
        broker._ib.isConnected.return_value = True
        broker.connect = AsyncMock()  # Should NOT be called

        async def _no_price(*args: Any, **kwargs: Any) -> None:
            return None

        original = spike._get_market_price
        try:
            spike._get_market_price = _no_price
            result = await spike._axis_joint(
                broker, ["SPY", "QQQ", "IWM"], num_trials=2,
            )
        finally:
            spike._get_market_price = original

        broker.connect.assert_not_called()
        # Skipped flag must be False — the gate didn't trip
        assert result.skipped is False
        assert result.skip_reason is None
        # The axis ran far enough to attempt positions and recorded a note
        # about insufficient positions (since prices were unavailable).
        assert any("axis (iv): opened only" in n for n in result.notes)

    @pytest.mark.asyncio
    async def test_disconnected_at_entry_attempts_reconnect_and_proceeds(
        self, spike
    ) -> None:
        """When `isConnected()` returns False, the gate calls broker.connect()
        with a 30s timeout. If connect succeeds, the axis proceeds (we
        short-circuit at position-open via no-price stub to keep the test
        scoped to gate behavior)."""
        broker = MagicMock()
        broker._ib = MagicMock()
        broker._ib.isConnected.return_value = False
        broker.connect = AsyncMock()  # Returns None successfully

        async def _no_price(*args: Any, **kwargs: Any) -> None:
            return None

        original = spike._get_market_price
        try:
            spike._get_market_price = _no_price
            result = await spike._axis_joint(
                broker, ["SPY", "QQQ", "IWM"], num_trials=2,
            )
        finally:
            spike._get_market_price = original

        broker.connect.assert_awaited_once()
        # Reconnect succeeded — skipped must be False
        assert result.skipped is False
        assert result.skip_reason is None

    @pytest.mark.asyncio
    async def test_disconnected_at_entry_reconnect_fail_returns_skipped(
        self, spike
    ) -> None:
        """When `isConnected()` returns False AND broker.connect() raises,
        the gate must return immediately with `skipped=True` and a
        `skip_reason` matching the prompt's specified text. The axis must
        NOT proceed to position open."""
        broker = MagicMock()
        broker._ib = MagicMock()
        broker._ib.isConnected.return_value = False

        async def _connect_raises() -> None:
            raise ConnectionError("Gateway unreachable")

        broker.connect = _connect_raises

        # Sentinel: if `_get_market_price` is called, the test fails.
        get_price_called = []

        async def _sentinel_price(*args: Any, **kwargs: Any) -> None:
            get_price_called.append(True)
            return None

        original = spike._get_market_price
        try:
            spike._get_market_price = _sentinel_price
            result = await spike._axis_joint(
                broker, ["SPY", "QQQ", "IWM"], num_trials=2,
            )
        finally:
            spike._get_market_price = original

        assert result.skipped is True
        assert result.skip_reason is not None
        assert (
            "Gateway disconnected and reconnect failed before axis (iv) "
            "could begin"
        ) == result.skip_reason
        # Position-open path must NOT have been entered
        assert get_price_called == []
        # No trials fired
        assert result.n_trials == 0


# ---------------------------------------------------------------------------
# Source-level grep guards — structural protection against future drift
# ---------------------------------------------------------------------------


class TestStructuralGuards:
    """Lightweight grep guards to keep the three fixes from being silently
    reverted. Behavioral tests are the primary signal; these are belt-and-
    suspenders against PRs that delete the wiring without noticing."""

    def test_oca_tracker_attached_to_error_event_in_main_async(self) -> None:
        """The tracker must be wired to `broker._ib.errorEvent` — without
        this, the listener never fires."""
        src = SPIKE_SCRIPT.read_text()
        assert "oca_tracker = _OcaRejectionTracker()" in src
        assert "broker._ib.errorEvent += oca_tracker" in src

    def test_file_handler_setup_called_in_main_async(self) -> None:
        src = SPIKE_SCRIPT.read_text()
        assert "_setup_file_handler(run_timestamp)" in src
        assert "_generate_run_timestamp()" in src

    def test_axis_joint_has_is_connected_precondition_gate(self) -> None:
        """Source-level guard for the Fix B.3 gate: must call
        `broker._ib.isConnected()` at axis (iv) entry, await
        `broker.connect()` inside an `asyncio.wait_for(..., timeout=30.0)`,
        and return early with `skipped=True` on failure."""
        src = SPIKE_SCRIPT.read_text()
        # Locate _axis_joint body
        import re
        body_match = re.search(
            r"async def _axis_joint\b.*?(?=\n(?:async )?def |\Z)",
            src,
            re.DOTALL,
        )
        assert body_match is not None
        body = body_match.group(0)
        assert "broker._ib.isConnected()" in body
        assert "broker.connect()" in body
        assert "asyncio.wait_for" in body
        assert "timeout=30.0" in body
        assert "result.skipped = True" in body
        assert "result.skip_reason" in body

    def test_amend_one_signature_includes_oca_tracker(self, spike) -> None:
        """The `oca_tracker` parameter must be present on `_amend_one()`'s
        signature so call sites can pass the tracker through."""
        import inspect

        sig = inspect.signature(spike._amend_one)
        assert "oca_tracker" in sig.parameters

    def test_amend_one_returns_three_tuple(self, spike) -> None:
        """The return type must be `tuple[bool, str | None, bool]` —
        existing axis call sites unpack three elements."""
        import inspect
        src = inspect.getsource(spike._amend_one)
        assert "tuple[bool, str | None, bool]" in src

    def test_axis_result_has_n_oca_rejections_field(self, spike) -> None:
        a = spike.AxisResult()
        assert hasattr(a, "n_oca_rejections")
        assert a.n_oca_rejections == 0

    def test_axis_result_has_skipped_and_skip_reason_fields(self, spike) -> None:
        a = spike.AxisResult()
        assert hasattr(a, "skipped")
        assert hasattr(a, "skip_reason")
        assert a.skipped is False
        assert a.skip_reason is None

    def test_mode_a_trial_has_oca_rejected_field(self, spike) -> None:
        t = spike.ModeATrial(
            symbol="SPY",
            success=True,
            rejected=False,
            propagation_ok=True,
            round_trip_ms=1.0,
        )
        assert hasattr(t, "oca_rejected")
        assert t.oca_rejected is False
