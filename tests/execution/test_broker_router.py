"""Tests for the BrokerRouter."""

import pytest

from argus.core.config import BrokerConfig
from argus.execution.broker_router import BrokerRouter
from argus.execution.simulated_broker import SimulatedBroker


class TestBrokerRouter:
    """Tests for BrokerRouter routing logic."""

    def test_route_returns_primary_broker(self) -> None:
        """Route should return the primary broker."""
        broker = SimulatedBroker()
        config = BrokerConfig(primary="alpaca")
        router = BrokerRouter(config, {"alpaca": broker})

        result = router.route("us_stocks")
        assert result is broker

    def test_route_different_asset_class_still_returns_primary_v1(self) -> None:
        """V1: all asset classes route to primary broker."""
        broker = SimulatedBroker()
        config = BrokerConfig(primary="alpaca")
        router = BrokerRouter(config, {"alpaca": broker})

        result = router.route("crypto")
        assert result is broker

    def test_primary_broker_property(self) -> None:
        """Primary broker property should return the primary broker."""
        broker = SimulatedBroker()
        config = BrokerConfig(primary="alpaca")
        router = BrokerRouter(config, {"alpaca": broker})

        assert router.primary_broker is broker

    def test_invalid_primary_raises_on_construction(self) -> None:
        """Constructor should raise if primary broker not in brokers dict."""
        broker = SimulatedBroker()
        config = BrokerConfig(primary="nonexistent")

        with pytest.raises(ValueError, match="not found"):
            BrokerRouter(config, {"alpaca": broker})
