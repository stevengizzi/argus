"""Tests for argus.core.logging_config (FIX-13a / P1-G1-M03)."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from argus.core.logging_config import ConsoleFormatter, JsonFormatter, setup_logging


def _make_record(
    *,
    name: str = "argus.test",
    level: int = logging.INFO,
    msg: str = "hello",
    extra: dict | None = None,
    exc_info: bool = False,
) -> logging.LogRecord:
    record = logging.LogRecord(
        name=name,
        level=level,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )
    if extra:
        for key, value in extra.items():
            setattr(record, key, value)
    if exc_info:
        try:
            raise ValueError("boom")
        except ValueError:
            record.exc_info = sys.exc_info()
    return record


class TestJsonFormatter:
    def test_produces_valid_json_with_core_fields(self) -> None:
        formatter = JsonFormatter()
        line = formatter.format(_make_record())
        payload = json.loads(line)
        assert payload["level"] == "INFO"
        assert payload["logger"] == "argus.test"
        assert payload["message"] == "hello"
        assert "timestamp" in payload

    def test_includes_recognized_extra_fields(self) -> None:
        formatter = JsonFormatter()
        record = _make_record(extra={"component": "broker", "symbol": "TSLA"})
        payload = json.loads(formatter.format(record))
        assert payload["component"] == "broker"
        assert payload["symbol"] == "TSLA"

    def test_includes_exception_traceback(self) -> None:
        formatter = JsonFormatter()
        record = _make_record(msg="failed", exc_info=True)
        payload = json.loads(formatter.format(record))
        assert "exception" in payload
        assert "ValueError" in payload["exception"]


class TestConsoleFormatter:
    def test_returns_string_with_level_and_message(self) -> None:
        formatter = ConsoleFormatter()
        rendered = formatter.format(_make_record(level=logging.WARNING, msg="careful"))
        assert "WARNING" in rendered
        assert "careful" in rendered
        assert "argus.test" in rendered


class TestSetupLogging:
    def test_creates_log_dir_and_jsonl_file(self, tmp_path: Path) -> None:
        log_dir = tmp_path / "logs"
        try:
            setup_logging(log_level="INFO", log_dir=log_dir)
            logging.getLogger("argus.test").info("hello")
            files = sorted(log_dir.glob("argus_*.jsonl"))
            assert files, "expected at least one argus_*.jsonl log file"
            content = files[0].read_text().splitlines()
            assert content, "log file should not be empty"
            parsed = json.loads(content[-1])
            assert parsed["message"] == "hello"
        finally:
            root = logging.getLogger()
            for handler in list(root.handlers):
                root.removeHandler(handler)
                handler.close()

    def test_suppresses_noisy_third_party_loggers(self, tmp_path: Path) -> None:
        try:
            setup_logging(log_level="DEBUG", log_dir=tmp_path / "logs")
            for noisy in ("aiohttp", "websockets", "databento", "httpx"):
                assert logging.getLogger(noisy).level == logging.WARNING
        finally:
            root = logging.getLogger()
            for handler in list(root.handlers):
                root.removeHandler(handler)
                handler.close()
