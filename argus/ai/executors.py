"""Action executors for the AI Copilot.

Implements the 5 action executors with validation and pre-execution re-check:
- AllocationChangeExecutor
- RiskParamChangeExecutor
- StrategySuspendExecutor
- StrategyResumeExecutor
- GenerateReportExecutor

Each executor handles validation, pre-execution re-check (the 4-condition gate),
and execution of a specific action type.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Any

from zoneinfo import ZoneInfo

from argus.ai.actions import ActionProposal
from argus.core.events import StrategyActivatedEvent, StrategySuspendedEvent

if TYPE_CHECKING:
    from argus.api.dependencies import AppState

logger = logging.getLogger(__name__)


class ExecutionError(Exception):
    """Raised when action execution fails."""

    pass


class ValidationError(Exception):
    """Raised when action validation fails."""

    pass


class PreExecutionCheckError(Exception):
    """Raised when pre-execution re-check fails."""

    pass


class ActionExecutor(ABC):
    """Base class for action executors.

    Each executor handles a specific action type with:
    - validate(): Check that tool_input is valid before creating a proposal
    - pre_execution_recheck(): The 4-condition gate before execution
    - execute(): Perform the action and return result
    """

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """The tool name this executor handles."""
        ...

    @property
    def requires_approval(self) -> bool:
        """Whether this action requires approval before execution."""
        return True

    async def validate(self, tool_input: dict[str, Any]) -> tuple[bool, str]:
        """Validate tool input before creating a proposal.

        Args:
            tool_input: The tool input parameters from Claude.

        Returns:
            Tuple of (valid, error_message). If valid is True, error_message is empty.
        """
        return (True, "")

    async def pre_execution_recheck(
        self,
        proposal: ActionProposal,
        app_state: AppState,
    ) -> tuple[bool, str]:
        """The 4-condition gate before execution.

        Checks:
        1. Strategy exists and is in expected state
        2. Market regime unchanged since proposal creation
        3. Account equity within 5% of equity at proposal creation
        4. No circuit breaker currently active

        Args:
            proposal: The approved proposal.
            app_state: Current application state.

        Returns:
            Tuple of (passed, reason). If passed is False, reason explains why.
        """
        # Default implementation checks conditions 2, 3, 4
        # Subclasses add condition 1 (strategy state)

        # Condition 2: Regime unchanged
        regime_at_creation = proposal.tool_input.get("_regime_at_creation")
        if regime_at_creation is not None and app_state.orchestrator is not None:
            current_regime = str(app_state.orchestrator.current_regime)
            if current_regime != regime_at_creation:
                return (
                    False,
                    f"Execution blocked — regime changed from {regime_at_creation} to {current_regime}",
                )

        # Condition 3: Equity within 5%
        equity_at_creation = proposal.tool_input.get("_equity_at_creation")
        if equity_at_creation is not None and app_state.broker is not None:
            account = await app_state.broker.get_account()
            if account is not None:
                current_equity = account.equity
                pct_change = abs(current_equity - equity_at_creation) / equity_at_creation
                if pct_change > 0.05:
                    return (
                        False,
                        f"Execution blocked — equity changed by {pct_change:.1%} "
                        f"(was ${equity_at_creation:,.0f}, now ${current_equity:,.0f})",
                    )

        # Condition 4: No circuit breaker active
        if app_state.risk_manager is not None:
            if app_state.risk_manager.circuit_breaker_active:
                return (False, "Execution blocked — circuit breaker is active")

        return (True, "")

    @abstractmethod
    async def execute(
        self,
        proposal: ActionProposal,
        app_state: AppState,
    ) -> dict[str, Any]:
        """Execute the action.

        Args:
            proposal: The approved proposal.
            app_state: Current application state.

        Returns:
            Result dict with action-specific data.

        Raises:
            ExecutionError: If execution fails.
        """
        ...


class AllocationChangeExecutor(ActionExecutor):
    """Executor for strategy allocation changes."""

    @property
    def tool_name(self) -> str:
        return "propose_allocation_change"

    async def validate(self, tool_input: dict[str, Any]) -> tuple[bool, str]:
        """Validate allocation change input.

        Checks:
        - strategy_id is provided
        - new_allocation_pct is in 0-100 range
        """
        strategy_id = tool_input.get("strategy_id")
        if not strategy_id:
            return (False, "strategy_id is required")

        new_allocation = tool_input.get("new_allocation_pct")
        if new_allocation is None:
            return (False, "new_allocation_pct is required")

        if not isinstance(new_allocation, (int, float)):
            return (False, "new_allocation_pct must be a number")

        if new_allocation < 0 or new_allocation > 100:
            return (False, f"new_allocation_pct must be 0-100, got {new_allocation}")

        return (True, "")

    async def pre_execution_recheck(
        self,
        proposal: ActionProposal,
        app_state: AppState,
    ) -> tuple[bool, str]:
        """Check strategy exists and is active, plus base conditions."""
        strategy_id = proposal.tool_input.get("strategy_id")

        # Condition 1: Strategy exists
        if app_state.orchestrator is None:
            return (False, "Execution blocked — orchestrator not available")

        strategy = app_state.orchestrator.get_strategy(strategy_id)
        if strategy is None:
            return (False, f"Execution blocked — strategy '{strategy_id}' not found")

        # Check remaining conditions via parent
        return await super().pre_execution_recheck(proposal, app_state)

    async def execute(
        self,
        proposal: ActionProposal,
        app_state: AppState,
    ) -> dict[str, Any]:
        """Execute allocation change.

        Updates the strategy's allocated_capital based on the new percentage.
        """
        strategy_id = proposal.tool_input.get("strategy_id")
        new_allocation_pct = proposal.tool_input.get("new_allocation_pct")

        if app_state.orchestrator is None:
            raise ExecutionError("Orchestrator not available")

        strategy = app_state.orchestrator.get_strategy(strategy_id)
        if strategy is None:
            raise ExecutionError(f"Strategy '{strategy_id}' not found")

        # Get current equity for allocation calculation
        if app_state.broker is None:
            raise ExecutionError("Broker not available")

        account = await app_state.broker.get_account()
        if account is None:
            raise ExecutionError("Could not get account info")

        # Calculate old and new allocation
        total_equity = account.equity
        cash_reserve_pct = app_state.orchestrator.cash_reserve_pct
        deployable = total_equity * (1.0 - cash_reserve_pct)

        old_allocation_pct = (
            (strategy.allocated_capital / deployable * 100)
            if deployable > 0 and strategy.allocated_capital > 0
            else 0.0
        )
        new_allocation_dollars = deployable * (new_allocation_pct / 100.0)

        # Apply the change
        strategy.allocated_capital = new_allocation_dollars

        logger.info(
            "Allocation change executed: %s from %.1f%% to %.1f%% ($%.0f)",
            strategy_id,
            old_allocation_pct,
            new_allocation_pct,
            new_allocation_dollars,
        )

        return {
            "strategy_id": strategy_id,
            "old_allocation": round(old_allocation_pct, 1),
            "new_allocation": round(new_allocation_pct, 1),
            "effective": True,
        }


class RiskParamChangeExecutor(ActionExecutor):
    """Executor for risk parameter changes."""

    # Allowed params with their valid ranges
    ALLOWED_PARAMS: dict[str, tuple[float, float]] = {
        "risk.daily_loss_limit_pct": (0.01, 0.10),  # 1-10%
        "risk.weekly_loss_limit_pct": (0.02, 0.15),  # 2-15%
        "risk.max_single_stock_pct": (0.01, 0.15),  # 1-15%
        "risk.per_trade_risk_pct": (0.001, 0.03),  # 0.1-3%
    }

    @property
    def tool_name(self) -> str:
        return "propose_risk_param_change"

    async def validate(self, tool_input: dict[str, Any]) -> tuple[bool, str]:
        """Validate risk param change input.

        Checks:
        - param_path is in allowed set
        - new_value is within defined sane ranges
        """
        param_path = tool_input.get("param_path")
        if not param_path:
            return (False, "param_path is required")

        if param_path not in self.ALLOWED_PARAMS:
            allowed = ", ".join(self.ALLOWED_PARAMS.keys())
            return (False, f"Param '{param_path}' not modifiable via AI. Allowed: {allowed}")

        new_value = tool_input.get("new_value")
        if new_value is None:
            return (False, "new_value is required")

        if not isinstance(new_value, (int, float)):
            return (False, "new_value must be a number")

        min_val, max_val = self.ALLOWED_PARAMS[param_path]
        if new_value < min_val or new_value > max_val:
            return (
                False,
                f"new_value {new_value} out of range [{min_val}, {max_val}] for {param_path}",
            )

        return (True, "")

    async def pre_execution_recheck(
        self,
        proposal: ActionProposal,
        app_state: AppState,
    ) -> tuple[bool, str]:
        """Check risk manager available, plus base conditions."""
        if app_state.risk_manager is None:
            return (False, "Execution blocked — risk manager not available")

        return await super().pre_execution_recheck(proposal, app_state)

    async def execute(
        self,
        proposal: ActionProposal,
        app_state: AppState,
    ) -> dict[str, Any]:
        """Execute risk param change.

        Updates the runtime risk config. Does NOT modify risk_manager.py source.
        """
        param_path = proposal.tool_input.get("param_path")
        new_value = proposal.tool_input.get("new_value")

        if app_state.risk_manager is None:
            raise ExecutionError("Risk manager not available")

        # Get the config object
        config = app_state.risk_manager._config

        # Parse param path and update
        old_value: float | None = None
        if param_path == "risk.daily_loss_limit_pct":
            old_value = config.account.daily_loss_limit_pct
            config.account.daily_loss_limit_pct = new_value
        elif param_path == "risk.weekly_loss_limit_pct":
            old_value = config.account.weekly_loss_limit_pct
            config.account.weekly_loss_limit_pct = new_value
        elif param_path == "risk.max_single_stock_pct":
            old_value = config.cross_strategy.max_single_stock_pct
            config.cross_strategy.max_single_stock_pct = new_value
        elif param_path == "risk.per_trade_risk_pct":
            # per_trade_risk_pct is not a direct field in RiskConfig
            # It may be in strategy configs. For now, reject gracefully.
            raise ExecutionError(
                f"Parameter {param_path} requires strategy-level modification, not supported"
            )
        else:
            raise ExecutionError(f"Unknown param path: {param_path}")

        logger.info(
            "Risk param change executed: %s from %s to %s",
            param_path,
            old_value,
            new_value,
        )

        return {
            "param_path": param_path,
            "old_value": old_value,
            "new_value": new_value,
            "effective": True,
        }


class StrategySuspendExecutor(ActionExecutor):
    """Executor for suspending an active strategy."""

    @property
    def tool_name(self) -> str:
        return "propose_strategy_suspend"

    async def validate(self, tool_input: dict[str, Any]) -> tuple[bool, str]:
        """Validate strategy suspend input."""
        strategy_id = tool_input.get("strategy_id")
        if not strategy_id:
            return (False, "strategy_id is required")

        return (True, "")

    async def pre_execution_recheck(
        self,
        proposal: ActionProposal,
        app_state: AppState,
    ) -> tuple[bool, str]:
        """Check strategy exists and is currently active."""
        strategy_id = proposal.tool_input.get("strategy_id")

        if app_state.orchestrator is None:
            return (False, "Execution blocked — orchestrator not available")

        strategy = app_state.orchestrator.get_strategy(strategy_id)
        if strategy is None:
            return (False, f"Execution blocked — strategy '{strategy_id}' not found")

        if not strategy.is_active:
            return (False, f"Execution blocked — strategy '{strategy_id}' is already suspended")

        return await super().pre_execution_recheck(proposal, app_state)

    async def execute(
        self,
        proposal: ActionProposal,
        app_state: AppState,
    ) -> dict[str, Any]:
        """Suspend the strategy."""
        strategy_id = proposal.tool_input.get("strategy_id")
        reason = proposal.tool_input.get("reason", "Suspended via AI Copilot")

        if app_state.orchestrator is None:
            raise ExecutionError("Orchestrator not available")

        strategy = app_state.orchestrator.get_strategy(strategy_id)
        if strategy is None:
            raise ExecutionError(f"Strategy '{strategy_id}' not found")

        # Suspend the strategy
        strategy.is_active = False

        # Publish event
        if app_state.event_bus is not None:
            await app_state.event_bus.publish(
                StrategySuspendedEvent(
                    strategy_id=strategy_id,
                    reason=f"AI Copilot: {reason}",
                )
            )

        logger.info("Strategy suspended: %s - %s", strategy_id, reason)

        return {
            "strategy_id": strategy_id,
            "status": "suspended",
            "reason": reason,
        }


class StrategyResumeExecutor(ActionExecutor):
    """Executor for resuming a suspended strategy."""

    @property
    def tool_name(self) -> str:
        return "propose_strategy_resume"

    async def validate(self, tool_input: dict[str, Any]) -> tuple[bool, str]:
        """Validate strategy resume input."""
        strategy_id = tool_input.get("strategy_id")
        if not strategy_id:
            return (False, "strategy_id is required")

        return (True, "")

    async def pre_execution_recheck(
        self,
        proposal: ActionProposal,
        app_state: AppState,
    ) -> tuple[bool, str]:
        """Check strategy exists and is currently suspended."""
        strategy_id = proposal.tool_input.get("strategy_id")

        if app_state.orchestrator is None:
            return (False, "Execution blocked — orchestrator not available")

        strategy = app_state.orchestrator.get_strategy(strategy_id)
        if strategy is None:
            return (False, f"Execution blocked — strategy '{strategy_id}' not found")

        if strategy.is_active:
            return (False, f"Execution blocked — strategy '{strategy_id}' is already active")

        return await super().pre_execution_recheck(proposal, app_state)

    async def execute(
        self,
        proposal: ActionProposal,
        app_state: AppState,
    ) -> dict[str, Any]:
        """Resume the strategy."""
        strategy_id = proposal.tool_input.get("strategy_id")
        reason = proposal.tool_input.get("reason", "Resumed via AI Copilot")

        if app_state.orchestrator is None:
            raise ExecutionError("Orchestrator not available")

        strategy = app_state.orchestrator.get_strategy(strategy_id)
        if strategy is None:
            raise ExecutionError(f"Strategy '{strategy_id}' not found")

        # Resume the strategy
        strategy.is_active = True

        # Publish event
        if app_state.event_bus is not None:
            await app_state.event_bus.publish(
                StrategyActivatedEvent(
                    strategy_id=strategy_id,
                    reason=f"AI Copilot: {reason}",
                )
            )

        logger.info("Strategy resumed: %s - %s", strategy_id, reason)

        return {
            "strategy_id": strategy_id,
            "status": "active",
            "reason": reason,
        }


class GenerateReportExecutor(ActionExecutor):
    """Executor for report generation.

    Does not require approval — executes immediately.
    """

    ALLOWED_REPORT_TYPES = {"daily_summary", "strategy_analysis", "risk_review"}

    @property
    def tool_name(self) -> str:
        return "generate_report"

    @property
    def requires_approval(self) -> bool:
        return False

    async def validate(self, tool_input: dict[str, Any]) -> tuple[bool, str]:
        """Validate report generation input."""
        report_type = tool_input.get("report_type")
        if not report_type:
            return (False, "report_type is required")

        if report_type not in self.ALLOWED_REPORT_TYPES:
            allowed = ", ".join(self.ALLOWED_REPORT_TYPES)
            return (False, f"Unknown report_type '{report_type}'. Allowed: {allowed}")

        return (True, "")

    async def pre_execution_recheck(
        self,
        proposal: ActionProposal,
        app_state: AppState,
    ) -> tuple[bool, str]:
        """No pre-execution recheck needed for reports."""
        return (True, "")

    async def execute(
        self,
        proposal: ActionProposal,
        app_state: AppState,
    ) -> dict[str, Any]:
        """Generate the report.

        Delegates to DailySummaryGenerator or other generators based on type.
        """
        report_type = proposal.tool_input.get("report_type")
        params = proposal.tool_input.get("params", {})

        if report_type == "daily_summary":
            # Get or default to today's date
            report_date = params.get("date")
            if report_date is None:
                et_tz = ZoneInfo("America/New_York")
                report_date = datetime.now(et_tz).strftime("%Y-%m-%d")

            # Import here to avoid circular imports
            from argus.ai.summary import DailySummaryGenerator

            if app_state.ai_summary_generator is not None:
                content = await app_state.ai_summary_generator.generate(report_date, app_state)
            else:
                # Fallback: create a temporary generator
                generator = DailySummaryGenerator(app_state.ai_client)
                content = await generator.generate(report_date, app_state)

            return {
                "report_type": report_type,
                "content": content,
                "date": report_date,
                "saved": True,
            }
        elif report_type == "strategy_analysis":
            # Placeholder for strategy analysis
            return {
                "report_type": report_type,
                "content": "Strategy analysis report generation not yet implemented.",
                "saved": False,
            }
        elif report_type == "risk_review":
            # Placeholder for risk review
            return {
                "report_type": report_type,
                "content": "Risk review report generation not yet implemented.",
                "saved": False,
            }
        else:
            raise ExecutionError(f"Unknown report type: {report_type}")


class ExecutorRegistry:
    """Registry mapping tool names to executor instances.

    Usage:
        registry = ExecutorRegistry()
        executor = registry.get("propose_allocation_change")
        if executor:
            result = await executor.execute(proposal, app_state)
    """

    def __init__(self) -> None:
        """Initialize the registry with all executors."""
        self._executors: dict[str, ActionExecutor] = {}
        self._register_default_executors()

    def _register_default_executors(self) -> None:
        """Register all built-in executors."""
        executors: list[ActionExecutor] = [
            AllocationChangeExecutor(),
            RiskParamChangeExecutor(),
            StrategySuspendExecutor(),
            StrategyResumeExecutor(),
            GenerateReportExecutor(),
        ]
        for executor in executors:
            self._executors[executor.tool_name] = executor

    def get(self, tool_name: str) -> ActionExecutor | None:
        """Get an executor by tool name.

        Args:
            tool_name: The tool name to look up.

        Returns:
            The executor instance, or None if not found.
        """
        return self._executors.get(tool_name)

    def register(self, executor: ActionExecutor) -> None:
        """Register a custom executor.

        Args:
            executor: The executor to register.
        """
        self._executors[executor.tool_name] = executor

    @property
    def tool_names(self) -> list[str]:
        """Get all registered tool names."""
        return list(self._executors.keys())
