"""IBKR error handling and classification.

IBKR error codes are extensive and cryptic. This module provides
classification and human-readable mapping for handling errors
appropriately in IBKRBroker.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class IBKRErrorSeverity(StrEnum):
    """Severity classification for IBKR errors."""

    CRITICAL = "critical"  # Connection lost, no trading permission
    WARNING = "warning"  # Order rejected, cannot modify
    INFO = "info"  # Market data not subscribed (irrelevant for us)


@dataclass(frozen=True)
class IBKRErrorInfo:
    """Information about a specific IBKR error code.

    Attributes:
        code: IBKR error code number.
        severity: Error severity classification.
        category: Error category ("connection", "order", "account", "data", "system").
        description: Human-readable description of the error.
        action: Recommended ARGUS action ("reconnect", "log", "reject_order",
                "circuit_break", "verify_state", "generate_new_id").
    """

    code: int
    severity: IBKRErrorSeverity
    category: str
    description: str
    action: str


# Comprehensive error map — key errors that IBKRBroker must handle
IBKR_ERROR_MAP: dict[int, IBKRErrorInfo] = {
    # Connection errors
    1100: IBKRErrorInfo(
        1100,
        IBKRErrorSeverity.CRITICAL,
        "connection",
        "Connectivity between IB and TWS has been lost",
        "reconnect",
    ),
    1101: IBKRErrorInfo(
        1101,
        IBKRErrorSeverity.WARNING,
        "connection",
        "Connectivity restored — data may have been lost during disconnect",
        "verify_state",
    ),
    1102: IBKRErrorInfo(
        1102,
        IBKRErrorSeverity.INFO,
        "connection",
        "Connectivity restored — data maintained",
        "log",
    ),
    502: IBKRErrorInfo(
        502,
        IBKRErrorSeverity.CRITICAL,
        "connection",
        "Couldn't connect to TWS/Gateway",
        "reconnect",
    ),
    504: IBKRErrorInfo(
        504,
        IBKRErrorSeverity.CRITICAL,
        "connection",
        "Not connected",
        "reconnect",
    ),
    # Order errors
    103: IBKRErrorInfo(
        103,
        IBKRErrorSeverity.WARNING,
        "order",
        "Duplicate order ID",
        "generate_new_id",
    ),
    104: IBKRErrorInfo(
        104,
        IBKRErrorSeverity.WARNING,
        "order",
        "Can't modify a filled order",
        "log",
    ),
    105: IBKRErrorInfo(
        105,
        IBKRErrorSeverity.WARNING,
        "order",
        "Order being modified does not match original",
        "log",
    ),
    110: IBKRErrorInfo(
        110,
        IBKRErrorSeverity.WARNING,
        "order",
        "The price does not conform to the minimum price variation",
        "reject_order",
    ),
    135: IBKRErrorInfo(
        135,
        IBKRErrorSeverity.CRITICAL,
        "account",
        "Can't find order with ID",
        "log",
    ),
    161: IBKRErrorInfo(
        161,
        IBKRErrorSeverity.INFO,
        "order",
        "Cancel attempted",
        "log",
    ),
    200: IBKRErrorInfo(
        200,
        IBKRErrorSeverity.WARNING,
        "order",
        "No security definition has been found (ambiguous contract)",
        "reject_order",
    ),
    201: IBKRErrorInfo(
        201,
        IBKRErrorSeverity.WARNING,
        "order",
        "Order rejected — reason in error message",
        "reject_order",
    ),
    202: IBKRErrorInfo(
        202,
        IBKRErrorSeverity.INFO,
        "order",
        "Order cancelled",
        "log",
    ),
    203: IBKRErrorInfo(
        203,
        IBKRErrorSeverity.CRITICAL,
        "account",
        "The security is not available or allowed for this account",
        "reject_order",
    ),
    # Account errors
    321: IBKRErrorInfo(
        321,
        IBKRErrorSeverity.CRITICAL,
        "account",
        "Server error validating API client request",
        "log",
    ),
    # Market data (informational — we use Databento, not IBKR data)
    354: IBKRErrorInfo(
        354,
        IBKRErrorSeverity.INFO,
        "data",
        "Requested market data is not subscribed",
        "log",
    ),
    10167: IBKRErrorInfo(
        10167,
        IBKRErrorSeverity.INFO,
        "data",
        "Requested market data is not subscribed (delayed data available)",
        "log",
    ),
    # System
    2103: IBKRErrorInfo(
        2103,
        IBKRErrorSeverity.INFO,
        "system",
        "A market data farm is connecting",
        "log",
    ),
    2104: IBKRErrorInfo(
        2104,
        IBKRErrorSeverity.INFO,
        "system",
        "Market data farm connection is OK",
        "log",
    ),
    2105: IBKRErrorInfo(
        2105,
        IBKRErrorSeverity.WARNING,
        "system",
        "A historical data farm is connecting",
        "log",
    ),
    2106: IBKRErrorInfo(
        2106,
        IBKRErrorSeverity.INFO,
        "system",
        "A historical data farm connection is OK",
        "log",
    ),
    2158: IBKRErrorInfo(
        2158,
        IBKRErrorSeverity.INFO,
        "system",
        "Sec-def data farm connection is OK",
        "log",
    ),
}

# Error codes that indicate order rejection
_ORDER_REJECTION_CODES: frozenset[int] = frozenset({110, 200, 201, 203})

# Error codes that indicate connection problems
_CONNECTION_ERROR_CODES: frozenset[int] = frozenset({502, 504, 1100})


def classify_error(error_code: int, error_string: str) -> IBKRErrorInfo:
    """Classify an IBKR error code.

    Returns info with severity and recommended action.
    Unknown codes default to WARNING severity with 'log' action.

    Args:
        error_code: IBKR error code number.
        error_string: IBKR error message string.

    Returns:
        IBKRErrorInfo with classification and recommended action.
    """
    if error_code in IBKR_ERROR_MAP:
        return IBKR_ERROR_MAP[error_code]

    # Unknown error — default to warning
    return IBKRErrorInfo(
        code=error_code,
        severity=IBKRErrorSeverity.WARNING,
        category="unknown",
        description=error_string,
        action="log",
    )


def is_order_rejection(error_code: int) -> bool:
    """Check if this error code means an order was rejected.

    Args:
        error_code: IBKR error code number.

    Returns:
        True if the error indicates order rejection.
    """
    return error_code in _ORDER_REJECTION_CODES


def is_connection_error(error_code: int) -> bool:
    """Check if this error code indicates a connection problem.

    Args:
        error_code: IBKR error code number.

    Returns:
        True if the error indicates a connection issue.
    """
    return error_code in _CONNECTION_ERROR_CODES


def get_critical_error_codes() -> frozenset[int]:
    """Return all error codes classified as CRITICAL severity.

    Useful for testing and validation.

    Returns:
        Frozenset of CRITICAL severity error codes.
    """
    return frozenset(
        code
        for code, info in IBKR_ERROR_MAP.items()
        if info.severity == IBKRErrorSeverity.CRITICAL
    )


def get_info_error_codes() -> frozenset[int]:
    """Return all error codes classified as INFO severity.

    Useful for testing and validation.

    Returns:
        Frozenset of INFO severity error codes.
    """
    return frozenset(
        code
        for code, info in IBKR_ERROR_MAP.items()
        if info.severity == IBKRErrorSeverity.INFO
    )
