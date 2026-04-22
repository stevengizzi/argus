"""Tests for _init_learning_loop lifespan phase.

Covers DEF-173 regression guard: LearningStore.enforce_retention must be
called with ll_config.report_retention_days immediately after initialize.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.api.dependencies import AppState
from argus.api.server import _init_learning_loop
from argus.core.config import SystemConfig
from argus.intelligence.learning.models import LearningLoopConfig


@pytest.mark.asyncio
async def test_init_learning_loop_enforces_retention(tmp_path: Path) -> None:
    """DEF-173: _init_learning_loop must call enforce_retention(report_retention_days).

    Mirrors the FIX-03 ExperimentStore retention pattern (main.py) — ensures
    learning.db does not grow unbounded between sprints.
    """
    ll_config = LearningLoopConfig(enabled=True, report_retention_days=90)
    config = SystemConfig(data_dir=str(tmp_path))
    config.learning_loop = ll_config

    app_state = MagicMock(spec=AppState)
    app_state.config = config
    app_state.event_bus = MagicMock()

    fake_store = AsyncMock()

    with (
        patch(
            "argus.intelligence.learning.learning_store.LearningStore",
            return_value=fake_store,
        ),
        patch(
            "argus.intelligence.learning.outcome_collector.OutcomeCollector"
        ),
        patch("argus.intelligence.learning.weight_analyzer.WeightAnalyzer"),
        patch(
            "argus.intelligence.learning.threshold_analyzer.ThresholdAnalyzer"
        ),
        patch(
            "argus.intelligence.learning.correlation_analyzer.CorrelationAnalyzer"
        ),
        patch(
            "argus.intelligence.learning.learning_service.LearningService"
        ) as mock_service_cls,
        patch(
            "argus.intelligence.learning.config_proposal_manager.ConfigProposalManager"
        ) as mock_cpm_cls,
    ):
        mock_cpm = AsyncMock()
        mock_cpm.apply_pending.return_value = []
        mock_cpm_cls.return_value = mock_cpm
        mock_service_cls.return_value = MagicMock()

        await _init_learning_loop(app_state)

    fake_store.initialize.assert_awaited_once()
    fake_store.enforce_retention.assert_awaited_once_with(90)
