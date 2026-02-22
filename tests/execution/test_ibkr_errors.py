"""Tests for IBKR error handling and classification.

Tests:
1. Classify known error code
2. Classify unknown error code (defaults to WARNING)
3. is_order_rejection true/false
4. is_connection_error true/false
5. Critical severity codes correct
6. Info severity codes correct
"""

from __future__ import annotations

import dataclasses

import pytest

from argus.execution.ibkr_errors import (
    IBKR_ERROR_MAP,
    IBKRErrorInfo,
    IBKRErrorSeverity,
    classify_error,
    get_critical_error_codes,
    get_info_error_codes,
    is_connection_error,
    is_order_rejection,
)


class TestClassifyError:
    """Test suite for error classification."""

    def test_classify_known_error_code_returns_mapped_info(self) -> None:
        """Known error codes return their mapped IBKRErrorInfo."""
        # Test connection error
        result = classify_error(1100, "Connectivity lost")

        assert isinstance(result, IBKRErrorInfo)
        assert result.code == 1100
        assert result.severity == IBKRErrorSeverity.CRITICAL
        assert result.category == "connection"
        assert result.action == "reconnect"

    def test_classify_known_order_rejection_error(self) -> None:
        """Order rejection error is correctly classified."""
        result = classify_error(201, "Order rejected")

        assert result.code == 201
        assert result.severity == IBKRErrorSeverity.WARNING
        assert result.category == "order"
        assert result.action == "reject_order"

    def test_classify_unknown_error_defaults_to_warning(self) -> None:
        """Unknown error codes default to WARNING severity with 'log' action."""
        unknown_code = 99999
        error_message = "Some unknown IBKR error"

        result = classify_error(unknown_code, error_message)

        assert result.code == unknown_code
        assert result.severity == IBKRErrorSeverity.WARNING
        assert result.category == "unknown"
        assert result.description == error_message
        assert result.action == "log"

    def test_classify_info_level_error(self) -> None:
        """INFO level errors are correctly classified."""
        result = classify_error(2104, "Market data farm connection is OK")

        assert result.severity == IBKRErrorSeverity.INFO
        assert result.category == "system"
        assert result.action == "log"


class TestIsOrderRejection:
    """Test suite for is_order_rejection function."""

    def test_is_order_rejection_true_for_rejection_codes(self) -> None:
        """Known order rejection codes return True."""
        rejection_codes = [110, 200, 201, 203]

        for code in rejection_codes:
            assert is_order_rejection(code) is True, f"Code {code} should be rejection"

    def test_is_order_rejection_false_for_non_rejection_codes(self) -> None:
        """Non-rejection codes return False."""
        non_rejection_codes = [1100, 502, 104, 202, 2104, 99999]

        for code in non_rejection_codes:
            assert is_order_rejection(code) is False, f"Code {code} should not be rejection"


class TestIsConnectionError:
    """Test suite for is_connection_error function."""

    def test_is_connection_error_true_for_connection_codes(self) -> None:
        """Known connection error codes return True."""
        connection_codes = [502, 504, 1100]

        for code in connection_codes:
            assert is_connection_error(code) is True, f"Code {code} should be connection error"

    def test_is_connection_error_false_for_non_connection_codes(self) -> None:
        """Non-connection codes return False."""
        non_connection_codes = [1101, 1102, 201, 202, 2104, 99999]

        for code in non_connection_codes:
            assert is_connection_error(code) is False, f"Code {code} should not be connection error"


class TestCriticalSeverityCodes:
    """Test suite for critical severity code identification."""

    def test_critical_severity_codes_are_correct(self) -> None:
        """All CRITICAL severity codes are correctly identified."""
        critical_codes = get_critical_error_codes()

        # Known critical codes from the spec
        expected_critical = {1100, 502, 504, 135, 203, 321}

        assert critical_codes == expected_critical

    def test_each_critical_code_has_critical_severity_in_map(self) -> None:
        """Each code in critical set has CRITICAL severity in the map."""
        critical_codes = get_critical_error_codes()

        for code in critical_codes:
            assert code in IBKR_ERROR_MAP
            assert IBKR_ERROR_MAP[code].severity == IBKRErrorSeverity.CRITICAL


class TestInfoSeverityCodes:
    """Test suite for info severity code identification."""

    def test_info_severity_codes_are_correct(self) -> None:
        """All INFO severity codes are correctly identified."""
        info_codes = get_info_error_codes()

        # Known info codes from the spec
        expected_info = {1102, 161, 202, 354, 10167, 2103, 2104, 2106, 2158}

        assert info_codes == expected_info

    def test_info_codes_should_just_be_logged(self) -> None:
        """INFO severity errors typically have 'log' action."""
        info_codes = get_info_error_codes()

        for code in info_codes:
            assert IBKR_ERROR_MAP[code].action == "log"


class TestErrorMapCompleteness:
    """Test error map contains all expected entries."""

    def test_all_spec_error_codes_present(self) -> None:
        """All error codes from the spec are present in the map."""
        expected_codes = {
            # Connection
            1100,
            1101,
            1102,
            502,
            504,
            # Order
            103,
            104,
            105,
            110,
            135,
            161,
            200,
            201,
            202,
            203,
            # Account
            321,
            # Data
            354,
            10167,
            # System
            2103,
            2104,
            2105,
            2106,
            2158,
        }

        assert set(IBKR_ERROR_MAP.keys()) == expected_codes

    def test_error_info_dataclass_is_frozen(self) -> None:
        """IBKRErrorInfo instances are immutable (frozen dataclass)."""
        info = IBKR_ERROR_MAP[1100]

        # Attempting to modify should raise FrozenInstanceError
        with pytest.raises(dataclasses.FrozenInstanceError):
            info.code = 9999  # type: ignore[misc]
