"""Tests for argus.utils.log_throttle — ThrottledLogger utility.

Note: ``ThrottledLogger`` gates emissions on ``time.monotonic()``, so a
subset of tests here intentionally use real ``time.sleep`` (≤20 ms) to
advance past the suppression window. See ``.claude/rules/testing.md``
§"Tests that use real asyncio.sleep" — the same reasoning applies.
"""

from __future__ import annotations

import logging
import threading
import time
from unittest.mock import MagicMock

import pytest

from argus.utils.log_throttle import ThrottledLogger, get_throttled_logger


@pytest.fixture()
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    return MagicMock(spec=logging.Logger)


@pytest.fixture()
def throttled(mock_logger: MagicMock) -> ThrottledLogger:
    """Create a ThrottledLogger wrapping a mock logger."""
    return ThrottledLogger(mock_logger)


def test_first_message_always_emits(
    throttled: ThrottledLogger, mock_logger: MagicMock
) -> None:
    """First call to warn_throttled passes through immediately."""
    throttled.warn_throttled("key1", "hello world")
    mock_logger.warning.assert_called_once_with("hello world")


def test_duplicate_within_interval_suppressed(
    throttled: ThrottledLogger, mock_logger: MagicMock
) -> None:
    """Second call within the interval is suppressed."""
    throttled.warn_throttled("key1", "msg", interval_seconds=60.0)
    throttled.warn_throttled("key1", "msg", interval_seconds=60.0)
    throttled.warn_throttled("key1", "msg", interval_seconds=60.0)
    # Only the first call should have emitted
    assert mock_logger.warning.call_count == 1


def test_message_after_interval_emits(
    throttled: ThrottledLogger, mock_logger: MagicMock
) -> None:
    """Call after the interval elapses passes through with suppressed count."""
    throttled.warn_throttled("key1", "msg", interval_seconds=0.01)
    throttled.warn_throttled("key1", "msg", interval_seconds=0.01)  # suppressed
    time.sleep(0.02)
    throttled.warn_throttled("key1", "msg after", interval_seconds=0.01)
    assert mock_logger.warning.call_count == 2
    # Second emission includes suppressed count
    mock_logger.warning.assert_called_with("%s (%d suppressed)", "msg after", 1)


def test_different_keys_independent(
    throttled: ThrottledLogger, mock_logger: MagicMock
) -> None:
    """Two different keys don't interfere with each other."""
    throttled.warn_throttled("key_a", "alpha", interval_seconds=60.0)
    throttled.warn_throttled("key_b", "beta", interval_seconds=60.0)
    assert mock_logger.warning.call_count == 2


def test_suppressed_count_in_message(
    throttled: ThrottledLogger, mock_logger: MagicMock
) -> None:
    """Suppressed count is appended to message after suppression period."""
    throttled.warn_throttled("k", "base", interval_seconds=0.01)
    for _ in range(5):
        throttled.warn_throttled("k", "base", interval_seconds=0.01)
    time.sleep(0.02)
    throttled.warn_throttled("k", "base", interval_seconds=0.01)
    mock_logger.warning.assert_called_with("%s (%d suppressed)", "base", 5)


def test_reset_clears_state(
    throttled: ThrottledLogger, mock_logger: MagicMock
) -> None:
    """After reset(), the first message for any key emits again."""
    throttled.warn_throttled("key1", "first", interval_seconds=60.0)
    throttled.warn_throttled("key1", "suppressed", interval_seconds=60.0)
    assert mock_logger.warning.call_count == 1

    throttled.reset()
    throttled.warn_throttled("key1", "after reset", interval_seconds=60.0)
    assert mock_logger.warning.call_count == 2
    mock_logger.warning.assert_called_with("after reset")


def test_thread_safety(throttled: ThrottledLogger, mock_logger: MagicMock) -> None:
    """Concurrent calls from multiple threads don't crash."""
    errors: list[Exception] = []

    def worker() -> None:
        try:
            for i in range(50):
                throttled.warn_throttled(f"thread_key_{i % 5}", f"msg {i}")
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    assert not errors, f"Thread safety violation: {errors}"


def test_get_throttled_logger_returns_instance() -> None:
    """get_throttled_logger factory returns a ThrottledLogger."""
    tl = get_throttled_logger("test.module")
    assert isinstance(tl, ThrottledLogger)
