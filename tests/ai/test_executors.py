"""Tests for ActionExecutor and ExecutorRegistry."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.ai.actions import ActionProposal
from argus.ai.executors import (
    ActionExecutor,
    AllocationChangeExecutor,
    ExecutionError,
    ExecutorRegistry,
    GenerateReportExecutor,
    RiskParamChangeExecutor,
    StrategyResumeExecutor,
    StrategySuspendExecutor,
)


def make_proposal(
    tool_name: str,
    tool_input: dict[str, Any],
    status: str = "approved",
) -> ActionProposal:
    """Create a test proposal."""
    now = datetime.now(UTC)
    return ActionProposal(
        id="test_proposal_123",
        conversation_id="conv_123",
        message_id=None,
        tool_name=tool_name,
        tool_use_id="tu_123",
        tool_input=tool_input,
        status=status,
        result=None,
        failure_reason=None,
        created_at=now,
        expires_at=now + timedelta(seconds=300),
        resolved_at=now,
    )


@dataclass
class MockStrategy:
    """Mock strategy for testing."""

    name: str = "test_strategy"
    is_active: bool = True
    allocated_capital: float = 25000.0


@dataclass
class MockAccountConfig:
    """Mock account config."""

    daily_loss_limit_pct: float = 0.03
    weekly_loss_limit_pct: float = 0.05
    max_concurrent_positions: int = 5


@dataclass
class MockCrossStrategyConfig:
    """Mock cross-strategy config."""

    max_single_stock_pct: float = 0.05


@dataclass
class MockRiskConfig:
    """Mock risk config."""

    account: MockAccountConfig = field(default_factory=MockAccountConfig)
    cross_strategy: MockCrossStrategyConfig = field(default_factory=MockCrossStrategyConfig)


@dataclass
class MockOrchestrator:
    """Mock orchestrator."""

    current_regime: str = "NEUTRAL"
    cash_reserve_pct: float = 0.20
    _strategies: dict[str, MockStrategy] = field(default_factory=dict)

    def get_strategy(self, strategy_id: str) -> MockStrategy | None:
        return self._strategies.get(strategy_id)


@dataclass
class MockRiskManager:
    """Mock risk manager."""

    circuit_breaker_active: bool = False
    _config: MockRiskConfig = field(default_factory=MockRiskConfig)


@dataclass
class MockBrokerAccount:
    """Mock broker account."""

    equity: float = 100000.0


class MockBroker:
    """Mock broker."""

    def __init__(self, equity: float = 100000.0) -> None:
        self._equity = equity

    async def get_account(self) -> MockBrokerAccount:
        return MockBrokerAccount(equity=self._equity)


class MockEventBus:
    """Mock event bus."""

    def __init__(self) -> None:
        self.published: list[Any] = []

    async def publish(self, event: Any) -> None:
        self.published.append(event)


@dataclass
class MockAppState:
    """Mock app state for testing."""

    orchestrator: MockOrchestrator | None = None
    risk_manager: MockRiskManager | None = None
    broker: MockBroker | None = None
    event_bus: MockEventBus | None = None
    ai_summary_generator: Any = None
    ai_client: Any = None


class TestAllocationChangeExecutor:
    """Test AllocationChangeExecutor."""

    async def test_validate_valid_input(self) -> None:
        """validate returns True for valid input."""
        executor = AllocationChangeExecutor()
        tool_input = {
            "strategy_id": "orb_breakout",
            "new_allocation_pct": 30.0,
            "reason": "Test reallocation",
        }

        valid, error = await executor.validate(tool_input)

        assert valid is True
        assert error == ""

    async def test_validate_missing_strategy_id(self) -> None:
        """validate returns error for missing strategy_id."""
        executor = AllocationChangeExecutor()
        tool_input = {"new_allocation_pct": 30.0}

        valid, error = await executor.validate(tool_input)

        assert valid is False
        assert "strategy_id" in error

    async def test_validate_allocation_too_high(self) -> None:
        """validate returns error for allocation > 100."""
        executor = AllocationChangeExecutor()
        tool_input = {
            "strategy_id": "orb_breakout",
            "new_allocation_pct": 150.0,
        }

        valid, error = await executor.validate(tool_input)

        assert valid is False
        assert "0-100" in error

    async def test_validate_allocation_negative(self) -> None:
        """validate returns error for negative allocation."""
        executor = AllocationChangeExecutor()
        tool_input = {
            "strategy_id": "orb_breakout",
            "new_allocation_pct": -10.0,
        }

        valid, error = await executor.validate(tool_input)

        assert valid is False
        assert "0-100" in error

    async def test_execute_updates_allocation(self) -> None:
        """execute updates strategy allocated_capital."""
        executor = AllocationChangeExecutor()
        strategy = MockStrategy(allocated_capital=25000.0)
        orchestrator = MockOrchestrator(_strategies={"orb_breakout": strategy})
        broker = MockBroker(equity=100000.0)
        app_state = MockAppState(orchestrator=orchestrator, broker=broker)
        tool_input = {
            "strategy_id": "orb_breakout",
            "new_allocation_pct": 50.0,
        }
        proposal = make_proposal("propose_allocation_change", tool_input)

        result = await executor.execute(proposal, app_state)

        # 50% of 80000 deployable (20% reserve) = 40000
        assert strategy.allocated_capital == 40000.0
        assert result["new_allocation"] == 50.0

    async def test_pre_execution_recheck_passes(self) -> None:
        """pre_execution_recheck passes when conditions match."""
        executor = AllocationChangeExecutor()
        strategy = MockStrategy(is_active=True)
        orchestrator = MockOrchestrator(_strategies={"orb_breakout": strategy})
        broker = MockBroker(equity=100000.0)
        risk_manager = MockRiskManager(circuit_breaker_active=False)
        app_state = MockAppState(
            orchestrator=orchestrator,
            broker=broker,
            risk_manager=risk_manager,
        )
        tool_input = {
            "strategy_id": "orb_breakout",
            "new_allocation_pct": 40.0,
            "_regime_at_creation": "NEUTRAL",
            "_equity_at_creation": 100000.0,
        }
        proposal = make_proposal("propose_allocation_change", tool_input)

        passed, reason = await executor.pre_execution_recheck(proposal, app_state)

        assert passed is True
        assert reason == ""

    async def test_pre_execution_recheck_fails_regime_changed(self) -> None:
        """pre_execution_recheck fails if regime changed."""
        executor = AllocationChangeExecutor()
        strategy = MockStrategy()
        orchestrator = MockOrchestrator(
            current_regime="RISK_OFF",
            _strategies={"orb_breakout": strategy},
        )
        app_state = MockAppState(orchestrator=orchestrator, broker=MockBroker())
        tool_input = {
            "strategy_id": "orb_breakout",
            "_regime_at_creation": "NEUTRAL",
            "_equity_at_creation": 100000.0,
        }
        proposal = make_proposal("propose_allocation_change", tool_input)

        passed, reason = await executor.pre_execution_recheck(proposal, app_state)

        assert passed is False
        assert "regime changed" in reason.lower()

    async def test_pre_execution_recheck_fails_equity_dropped(self) -> None:
        """pre_execution_recheck fails if equity dropped >5%."""
        executor = AllocationChangeExecutor()
        strategy = MockStrategy()
        orchestrator = MockOrchestrator(_strategies={"orb_breakout": strategy})
        broker = MockBroker(equity=90000.0)  # 10% drop
        app_state = MockAppState(orchestrator=orchestrator, broker=broker)
        tool_input = {
            "strategy_id": "orb_breakout",
            "_regime_at_creation": "NEUTRAL",
            "_equity_at_creation": 100000.0,
        }
        proposal = make_proposal("propose_allocation_change", tool_input)

        passed, reason = await executor.pre_execution_recheck(proposal, app_state)

        assert passed is False
        assert "equity changed" in reason.lower()

    async def test_pre_execution_recheck_fails_circuit_breaker(self) -> None:
        """pre_execution_recheck fails if circuit breaker active."""
        executor = AllocationChangeExecutor()
        strategy = MockStrategy()
        orchestrator = MockOrchestrator(_strategies={"orb_breakout": strategy})
        risk_manager = MockRiskManager(circuit_breaker_active=True)
        app_state = MockAppState(
            orchestrator=orchestrator,
            broker=MockBroker(),
            risk_manager=risk_manager,
        )
        tool_input = {"strategy_id": "orb_breakout"}
        proposal = make_proposal("propose_allocation_change", tool_input)

        passed, reason = await executor.pre_execution_recheck(proposal, app_state)

        assert passed is False
        assert "circuit breaker" in reason.lower()


class TestRiskParamChangeExecutor:
    """Test RiskParamChangeExecutor."""

    async def test_validate_valid_param(self) -> None:
        """validate returns True for valid param."""
        executor = RiskParamChangeExecutor()
        tool_input = {
            "param_path": "risk.daily_loss_limit_pct",
            "new_value": 0.04,
        }

        valid, error = await executor.validate(tool_input)

        assert valid is True

    async def test_validate_unknown_param(self) -> None:
        """validate returns error for unknown param."""
        executor = RiskParamChangeExecutor()
        tool_input = {
            "param_path": "unknown.param",
            "new_value": 0.5,
        }

        valid, error = await executor.validate(tool_input)

        assert valid is False
        assert "not modifiable" in error

    async def test_validate_value_out_of_range(self) -> None:
        """validate returns error for value out of range."""
        executor = RiskParamChangeExecutor()
        tool_input = {
            "param_path": "risk.daily_loss_limit_pct",
            "new_value": 0.50,  # 50% is outside 1-10% range
        }

        valid, error = await executor.validate(tool_input)

        assert valid is False
        assert "out of range" in error

    async def test_execute_updates_config(self) -> None:
        """execute updates the risk config value."""
        executor = RiskParamChangeExecutor()
        risk_config = MockRiskConfig()
        risk_manager = MockRiskManager(_config=risk_config)
        app_state = MockAppState(risk_manager=risk_manager)
        tool_input = {
            "param_path": "risk.daily_loss_limit_pct",
            "new_value": 0.05,
        }
        proposal = make_proposal("propose_risk_param_change", tool_input)

        result = await executor.execute(proposal, app_state)

        assert risk_config.account.daily_loss_limit_pct == 0.05
        assert result["old_value"] == 0.03
        assert result["new_value"] == 0.05


class TestStrategySuspendExecutor:
    """Test StrategySuspendExecutor."""

    async def test_validate_valid_input(self) -> None:
        """validate returns True for valid input."""
        executor = StrategySuspendExecutor()
        tool_input = {"strategy_id": "orb_breakout", "reason": "Test"}

        valid, error = await executor.validate(tool_input)

        assert valid is True

    async def test_validate_missing_strategy_id(self) -> None:
        """validate returns error for missing strategy_id."""
        executor = StrategySuspendExecutor()
        tool_input = {"reason": "Test"}

        valid, error = await executor.validate(tool_input)

        assert valid is False
        assert "strategy_id" in error

    async def test_pre_execution_recheck_fails_if_already_suspended(self) -> None:
        """pre_execution_recheck fails if strategy already suspended."""
        executor = StrategySuspendExecutor()
        strategy = MockStrategy(is_active=False)
        orchestrator = MockOrchestrator(_strategies={"orb_breakout": strategy})
        app_state = MockAppState(orchestrator=orchestrator)
        tool_input = {"strategy_id": "orb_breakout"}
        proposal = make_proposal("propose_strategy_suspend", tool_input)

        passed, reason = await executor.pre_execution_recheck(proposal, app_state)

        assert passed is False
        assert "already suspended" in reason.lower()

    async def test_execute_suspends_strategy(self) -> None:
        """execute sets is_active to False."""
        executor = StrategySuspendExecutor()
        strategy = MockStrategy(is_active=True)
        orchestrator = MockOrchestrator(_strategies={"orb_breakout": strategy})
        event_bus = MockEventBus()
        app_state = MockAppState(orchestrator=orchestrator, event_bus=event_bus)
        tool_input = {"strategy_id": "orb_breakout", "reason": "Test"}
        proposal = make_proposal("propose_strategy_suspend", tool_input)

        result = await executor.execute(proposal, app_state)

        assert strategy.is_active is False
        assert result["status"] == "suspended"
        assert len(event_bus.published) == 1


class TestStrategyResumeExecutor:
    """Test StrategyResumeExecutor."""

    async def test_pre_execution_recheck_fails_if_already_active(self) -> None:
        """pre_execution_recheck fails if strategy already active."""
        executor = StrategyResumeExecutor()
        strategy = MockStrategy(is_active=True)
        orchestrator = MockOrchestrator(_strategies={"orb_breakout": strategy})
        app_state = MockAppState(orchestrator=orchestrator)
        tool_input = {"strategy_id": "orb_breakout"}
        proposal = make_proposal("propose_strategy_resume", tool_input)

        passed, reason = await executor.pre_execution_recheck(proposal, app_state)

        assert passed is False
        assert "already active" in reason.lower()

    async def test_execute_resumes_strategy(self) -> None:
        """execute sets is_active to True."""
        executor = StrategyResumeExecutor()
        strategy = MockStrategy(is_active=False)
        orchestrator = MockOrchestrator(_strategies={"suspended": strategy})
        event_bus = MockEventBus()
        app_state = MockAppState(orchestrator=orchestrator, event_bus=event_bus)
        tool_input = {"strategy_id": "suspended", "reason": "Test"}
        proposal = make_proposal("propose_strategy_resume", tool_input)

        result = await executor.execute(proposal, app_state)

        assert strategy.is_active is True
        assert result["status"] == "active"
        assert len(event_bus.published) == 1


class TestGenerateReportExecutor:
    """Test GenerateReportExecutor."""

    async def test_requires_approval_is_false(self) -> None:
        """GenerateReportExecutor does not require approval."""
        executor = GenerateReportExecutor()
        assert executor.requires_approval is False

    async def test_validate_valid_report_type(self) -> None:
        """validate returns True for valid report type."""
        executor = GenerateReportExecutor()
        tool_input = {"report_type": "daily_summary"}

        valid, error = await executor.validate(tool_input)

        assert valid is True

    async def test_validate_invalid_report_type(self) -> None:
        """validate returns error for invalid report type."""
        executor = GenerateReportExecutor()
        tool_input = {"report_type": "unknown_report"}

        valid, error = await executor.validate(tool_input)

        assert valid is False
        assert "Unknown report_type" in error


class TestExecutorRegistry:
    """Test ExecutorRegistry."""

    def test_registry_maps_tool_names(self) -> None:
        """Registry correctly maps tool names to executors."""
        registry = ExecutorRegistry()

        assert isinstance(registry.get("propose_allocation_change"), AllocationChangeExecutor)
        assert isinstance(registry.get("propose_risk_param_change"), RiskParamChangeExecutor)
        assert isinstance(registry.get("propose_strategy_suspend"), StrategySuspendExecutor)
        assert isinstance(registry.get("propose_strategy_resume"), StrategyResumeExecutor)
        assert isinstance(registry.get("generate_report"), GenerateReportExecutor)

    def test_registry_returns_none_for_unknown_tool(self) -> None:
        """Registry returns None for unknown tool names."""
        registry = ExecutorRegistry()

        assert registry.get("unknown_tool") is None

    def test_registry_tool_names_property(self) -> None:
        """Registry exposes all registered tool names."""
        registry = ExecutorRegistry()

        names = registry.tool_names

        assert "propose_allocation_change" in names
        assert "propose_risk_param_change" in names
        assert "propose_strategy_suspend" in names
        assert "propose_strategy_resume" in names
        assert "generate_report" in names
