"""Broker abstraction layer.

All broker implementations must implement the Broker ABC. Orders are routed
through this interface — no component should ever call a broker SDK directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from argus.models.trading import (
    AccountInfo,
    BracketOrderResult,
    Order,
    OrderResult,
    OrderStatus,
    Position,
)


class Broker(ABC):
    """Abstract base class for all broker implementations.

    Implementations:
        - SimulatedBroker: Deterministic test double for backtesting and testing.
        - AlpacaBroker: Live/paper trading via Alpaca API (Sprint 4).
        - IBKRBroker: Interactive Brokers adapter (Phase 3+).
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the broker.

        Called once at system startup. Implementations should verify
        credentials and connectivity.

        Raises:
            ConnectionError: If the broker cannot be reached.
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Cleanly disconnect from the broker.

        Called at system shutdown. Implementations should close WebSocket
        connections, cancel pending heartbeats, etc.
        """

    @abstractmethod
    async def place_order(self, order: Order) -> OrderResult:
        """Submit a single order to the broker.

        Args:
            order: The order to place (market, limit, stop, etc.).

        Returns:
            OrderResult with fill information or rejection reason.
        """

    @abstractmethod
    async def place_bracket_order(
        self,
        entry: Order,
        stop: Order,
        targets: list[Order],
    ) -> BracketOrderResult:
        """Submit a bracket order (entry + stop-loss + profit targets).

        The stop and target orders become active only after the entry fills.
        If the entry is rejected, stop and targets are not submitted.

        Args:
            entry: The entry order.
            stop: The stop-loss order (activated on entry fill).
            targets: Profit target orders (activated on entry fill).

        Returns:
            BracketOrderResult with results for all component orders.
        """

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending or partially filled order.

        Args:
            order_id: The ID of the order to cancel.

        Returns:
            True if the order was successfully cancelled, False otherwise.
        """

    @abstractmethod
    async def modify_order(self, order_id: str, modifications: dict) -> OrderResult:
        """Modify a pending order (price, quantity, etc.).

        Args:
            order_id: The ID of the order to modify.
            modifications: Dict of field names to new values.

        Returns:
            OrderResult reflecting the modified order state.
        """

    @abstractmethod
    async def get_positions(self) -> list[Position]:
        """Get all currently open positions.

        Returns:
            List of open Position objects. Empty list if no positions.
        """

    @abstractmethod
    async def get_account(self) -> AccountInfo:
        """Get current account information.

        Returns:
            AccountInfo snapshot with equity, cash, buying power.
        """

    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderStatus:
        """Get the current status of a specific order.

        Args:
            order_id: The ID of the order to check.

        Returns:
            Current OrderStatus.

        Raises:
            KeyError: If the order_id is not found.
        """

    @abstractmethod
    async def get_open_orders(self) -> list[Order]:
        """Get all open (unfilled, not cancelled) orders.

        Returns:
            List of Order objects for all open orders at the broker.
        """

    @abstractmethod
    async def flatten_all(self) -> list[OrderResult]:
        """Emergency: close all open positions at market price.

        This is the nuclear option. Used by circuit breakers and manual
        emergency shutdown. Cancels all pending orders first, then
        submits market orders to close every open position.

        Returns:
            List of OrderResults for each closing order.
        """
