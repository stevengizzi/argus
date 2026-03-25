"""Rate-limited logging utility.

Prevents high-volume warning sources from flooding the log with repeated
identical messages. Each unique key is rate-limited independently.
"""

from __future__ import annotations

import logging
import threading
import time


class ThrottledLogger:
    """Logger wrapper that rate-limits repeated warnings by key.

    Each unique key tracks its last emission time and a count of
    suppressed messages. The first call for any key always passes
    through. Subsequent calls within the interval are suppressed,
    and the next emission includes the suppressed count.

    Thread-safe via a threading.Lock.

    Args:
        logger: The underlying Python logger to delegate to.
    """

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._lock = threading.Lock()
        # key -> (last_emit_time, suppressed_count)
        self._state: dict[str, tuple[float, int]] = {}

    def warn_throttled(
        self,
        key: str,
        message: str,
        interval_seconds: float = 60.0,
    ) -> None:
        """Emit a warning, rate-limited by key.

        The first call for a given key always emits. Subsequent calls
        within ``interval_seconds`` are suppressed. When the interval
        elapses and a new call arrives, the message is emitted with
        a "(N suppressed)" suffix indicating how many were dropped.

        Args:
            key: Unique identifier for this warning source.
            message: The warning message to log.
            interval_seconds: Minimum seconds between emissions for the
                same key.
        """
        now = time.monotonic()

        with self._lock:
            if key not in self._state:
                # First occurrence — always emit
                self._state[key] = (now, 0)
                self._logger.warning(message)
                return

            last_time, suppressed = self._state[key]

            if now - last_time < interval_seconds:
                # Within interval — suppress
                self._state[key] = (last_time, suppressed + 1)
                return

            # Interval elapsed — emit with suppressed count
            self._state[key] = (now, 0)

        if suppressed > 0:
            self._logger.warning("%s (%d suppressed)", message, suppressed)
        else:
            self._logger.warning(message)

    def reset(self) -> None:
        """Clear all throttle state.

        After calling reset(), the next call for any key will emit
        immediately as if it were the first occurrence.
        """
        with self._lock:
            self._state.clear()


def get_throttled_logger(name: str) -> ThrottledLogger:
    """Create a ThrottledLogger wrapping the logger for the given name.

    Args:
        name: Logger name (typically ``__name__``).

    Returns:
        A ThrottledLogger instance.
    """
    return ThrottledLogger(logging.getLogger(name))
