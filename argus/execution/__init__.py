"""Execution layer — broker abstraction and order routing."""

from argus.execution.broker import Broker
from argus.execution.ibkr_broker import IBKRBroker
from argus.execution.ibkr_contracts import IBKRContractResolver
from argus.execution.ibkr_errors import (
    IBKR_ERROR_MAP,
    IBKRErrorInfo,
    IBKRErrorSeverity,
    classify_error,
    is_connection_error,
    is_order_rejection,
)

__all__ = [
    "Broker",
    "IBKRBroker",
    "IBKRContractResolver",
    "IBKRErrorInfo",
    "IBKRErrorSeverity",
    "IBKR_ERROR_MAP",
    "classify_error",
    "is_connection_error",
    "is_order_rejection",
]
