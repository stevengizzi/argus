"""Routes orders to the correct broker based on asset class configuration.

V1: Everything routes to the single configured broker. The router exists
to establish the pattern for multi-broker routing when IBKR is added.
"""

from __future__ import annotations

import logging

from argus.core.config import BrokerConfig
from argus.execution.broker import Broker

logger = logging.getLogger(__name__)


class BrokerRouter:
    """Routes orders to the appropriate broker based on asset class.

    In V1, all orders route to the primary broker. The routing logic
    exists to make multi-broker support a config change, not a code change.

    Args:
        config: Broker configuration from YAML.
        brokers: Dict mapping broker name to Broker instance.
    """

    def __init__(self, config: BrokerConfig, brokers: dict[str, Broker]) -> None:
        self._config = config
        self._brokers = brokers
        self._primary = config.primary

        if self._primary not in self._brokers:
            raise ValueError(
                f"Primary broker '{self._primary}' not found in registered brokers: "
                f"{list(self._brokers.keys())}"
            )

    def route(self, asset_class: str = "us_stocks") -> Broker:
        """Return the broker instance for the given asset class.

        Args:
            asset_class: The asset class of the order (e.g., "us_stocks", "crypto").

        Returns:
            The Broker instance that should handle this order.

        Raises:
            ValueError: If no broker is configured for the asset class.
        """
        # V1: everything routes to primary. Log for future routing visibility.
        broker = self._brokers.get(self._primary)
        if broker is None:
            raise ValueError(f"No broker registered for primary '{self._primary}'")

        logger.debug(
            "Routing %s order to broker '%s'",
            asset_class,
            self._primary,
        )
        return broker

    @property
    def primary_broker(self) -> Broker:
        """Direct access to the primary broker instance."""
        return self._brokers[self._primary]
