"""Logging configuration for Argus.

Sets up structured JSON logging to file and human-readable logging to console.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path


class JsonFormatter(logging.Formatter):
    """JSON log formatter for machine-parseable logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON.

        Args:
            record: The log record to format.

        Returns:
            JSON-formatted log entry.
        """
        log_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = self.formatException(record.exc_info)

        # Include extra fields if present
        for key in ("component", "symbol", "order_id", "position_id", "trade_id"):
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter with colors."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[1;31m",  # Bold Red
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record for console output with colors.

        Args:
            record: The log record to format.

        Returns:
            Formatted log string with ANSI colors.
        """
        color = self.COLORS.get(record.levelname, "")
        reset = self.RESET if color else ""

        timestamp = datetime.now().strftime("%H:%M:%S")
        return (
            f"{color}{timestamp} [{record.levelname:>8}]{reset} "
            f"{record.name}: {record.getMessage()}"
        )


def setup_logging(
    log_level: str = "INFO",
    log_dir: Path | None = None,
    file_level: str | None = None,
) -> None:
    """Configure logging for the Argus system.

    Console: human-readable format, colored.
    File: JSON format, one line per entry.

    Args:
        log_level: Root log level (DEBUG, INFO, WARNING, ERROR).
        log_dir: Directory for log files. Default: logs/
        file_level: File handler log level. Defaults to same as log_level.
            Set to "DEBUG" only when actively debugging — generates high volume.
    """
    if log_dir is None:
        log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Clear existing handlers
    root.handlers.clear()

    # Console handler — human-readable
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(ConsoleFormatter())
    console.setLevel(logging.INFO)
    root.addHandler(console)

    # File handler — JSON structured
    # Default to same level as log_level (INFO for production)
    effective_file_level = file_level or log_level
    log_file = log_dir / f"argus_{datetime.now().strftime('%Y%m%d')}.jsonl"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(JsonFormatter())
    file_handler.setLevel(getattr(logging, effective_file_level.upper(), logging.INFO))
    root.addHandler(file_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("alpaca").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("databento").setLevel(logging.WARNING)
    logging.getLogger("ib_async").setLevel(logging.WARNING)
    logging.getLogger("ib_insync").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)

    logging.info("Logging initialized (level=%s, file=%s)", log_level, log_file)
