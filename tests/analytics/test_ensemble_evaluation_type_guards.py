"""Revert-proof type-guard tests for EnsembleResult.from_dict (DEF-185).

Each test passes a type-mismatched payload into from_dict() and asserts that
TypeError is raised with a clear message. If the `if not isinstance: raise`
guards in argus/analytics/ensemble_evaluation.py are reverted to the original
`assert isinstance(...)` pattern, these tests will fail under `python -O`
(asserts are stripped) AND they depend on TypeError being raised explicitly,
so the reversion is caught regardless.

Paired with DEF-106 / FIX-07 pattern.
"""

from __future__ import annotations

import pytest


def _minimal_valid_dict() -> dict:
    """Minimal dict shape accepted by EnsembleResult.from_dict.

    Only the fields exercised by the three type-guard sites matter —
    we never reach the remainder because the guards short-circuit.
    """
    return {
        "cohort_id": "test",
        "strategy_ids": [],
        "evaluation_date": "2026-04-23T00:00:00",
        "data_range": ["2026-04-01", "2026-04-23"],
        "aggregate": {},
        "diversification_ratio": 1.0,
        "marginal_contributions": {},
        "tail_correlation": 0.0,
        "max_concurrent_drawdown": 0.0,
        "capital_utilization": 0.0,
        "turnover_rate": 0.0,
    }


class TestEnsembleResultFromDictTypeGuards:
    """Cover the 3 DEF-185 sites in argus/analytics/ensemble_evaluation.py."""

    def test_data_range_non_list_raises_typeerror(self) -> None:
        from argus.analytics.ensemble_evaluation import EnsembleResult

        payload = _minimal_valid_dict()
        payload["data_range"] = "not-a-list"  # wrong type: str instead of list

        with pytest.raises(TypeError, match="Expected list for data_range"):
            EnsembleResult.from_dict(payload)

    def test_marginal_contributions_non_dict_raises_typeerror(self) -> None:
        from argus.analytics.ensemble_evaluation import EnsembleResult

        payload = _minimal_valid_dict()
        payload["marginal_contributions"] = ["not-a-dict"]  # wrong type: list

        with pytest.raises(TypeError, match="Expected dict for marginal_contributions"):
            EnsembleResult.from_dict(payload)

    def test_baseline_ensemble_non_dict_raises_typeerror(self) -> None:
        from argus.analytics.ensemble_evaluation import EnsembleResult

        payload = _minimal_valid_dict()
        payload["baseline_ensemble"] = "not-a-dict"  # wrong type: str

        with pytest.raises(TypeError, match="Expected dict for baseline_ensemble"):
            EnsembleResult.from_dict(payload)
