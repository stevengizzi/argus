"""Tests for ActionManager and ActionProposal."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from argus.ai.actions import (
    ActionManager,
    ActionProposal,
    InvalidToolError,
    ProposalExpiredError,
    ProposalNotFoundError,
    ProposalNotPendingError,
)
from argus.ai.config import AIConfig
from argus.core.event_bus import EventBus
from argus.core.events import ApprovalRequestedEvent, ApprovalGrantedEvent, ApprovalDeniedEvent
from argus.db.manager import DatabaseManager


@pytest.fixture
def ai_config() -> AIConfig:
    """Provide a test AIConfig with short TTL."""
    return AIConfig(
        enabled=True,
        api_key="test-key",
        proposal_ttl_seconds=5,  # Short TTL for testing
    )


@pytest.fixture
async def action_manager(
    db: DatabaseManager,
    bus: EventBus,
    ai_config: AIConfig,
) -> ActionManager:
    """Provide an initialized ActionManager."""
    manager = ActionManager(db, bus, ai_config)
    await manager.initialize()
    return manager


class TestActionManagerCreate:
    """Test proposal creation."""

    async def test_create_proposal_happy_path(
        self,
        action_manager: ActionManager,
    ) -> None:
        """create_proposal creates a proposal with correct fields."""
        proposal = await action_manager.create_proposal(
            conversation_id="conv_123",
            message_id="msg_456",
            tool_name="propose_allocation_change",
            tool_use_id="tu_789",
            tool_input={"strategy_id": "orb_breakout", "new_allocation_pct": 30, "reason": "test"},
        )

        assert proposal.id is not None
        assert len(proposal.id) == 26  # ULID length
        assert proposal.conversation_id == "conv_123"
        assert proposal.message_id == "msg_456"
        assert proposal.tool_name == "propose_allocation_change"
        assert proposal.tool_use_id == "tu_789"
        assert proposal.tool_input["strategy_id"] == "orb_breakout"
        assert proposal.status == "pending"
        assert proposal.result is None
        assert proposal.failure_reason is None
        assert proposal.created_at is not None
        assert proposal.expires_at > proposal.created_at
        assert proposal.resolved_at is None

    async def test_create_proposal_supersedes_existing(
        self,
        action_manager: ActionManager,
    ) -> None:
        """create_proposal supersedes existing pending proposal of same type."""
        # Create first proposal
        first = await action_manager.create_proposal(
            conversation_id="conv_123",
            message_id=None,
            tool_name="propose_allocation_change",
            tool_use_id="tu_001",
            tool_input={"strategy_id": "orb_breakout", "new_allocation_pct": 30, "reason": "first"},
        )
        assert first.status == "pending"

        # Create second proposal of same type
        second = await action_manager.create_proposal(
            conversation_id="conv_123",
            message_id=None,
            tool_name="propose_allocation_change",
            tool_use_id="tu_002",
            tool_input={"strategy_id": "orb_breakout", "new_allocation_pct": 40, "reason": "second"},
        )
        assert second.status == "pending"
        assert second.id != first.id

        # First should be superseded (expired)
        first_updated = await action_manager.get_proposal(first.id)
        assert first_updated is not None
        assert first_updated.status == "expired"
        assert first_updated.failure_reason == "Superseded by new proposal"

    async def test_create_proposal_different_types_not_superseded(
        self,
        action_manager: ActionManager,
    ) -> None:
        """create_proposal does not supersede proposals of different types."""
        # Create allocation change proposal
        allocation = await action_manager.create_proposal(
            conversation_id="conv_123",
            message_id=None,
            tool_name="propose_allocation_change",
            tool_use_id="tu_001",
            tool_input={"strategy_id": "orb_breakout", "new_allocation_pct": 30, "reason": "test"},
        )

        # Create strategy suspend proposal
        suspend = await action_manager.create_proposal(
            conversation_id="conv_123",
            message_id=None,
            tool_name="propose_strategy_suspend",
            tool_use_id="tu_002",
            tool_input={"strategy_id": "orb_breakout", "reason": "test"},
        )

        # Both should be pending
        allocation_updated = await action_manager.get_proposal(allocation.id)
        assert allocation_updated is not None
        assert allocation_updated.status == "pending"

        suspend_updated = await action_manager.get_proposal(suspend.id)
        assert suspend_updated is not None
        assert suspend_updated.status == "pending"

    async def test_create_proposal_invalid_tool_raises_error(
        self,
        action_manager: ActionManager,
    ) -> None:
        """create_proposal raises InvalidToolError for non-approval tools."""
        with pytest.raises(InvalidToolError, match="does not require approval"):
            await action_manager.create_proposal(
                conversation_id="conv_123",
                message_id=None,
                tool_name="generate_report",
                tool_use_id="tu_001",
                tool_input={"report_type": "daily_summary"},
            )

    async def test_create_proposal_publishes_event(
        self,
        action_manager: ActionManager,
        bus: EventBus,
    ) -> None:
        """create_proposal publishes ApprovalRequestedEvent."""
        events_received: list[ApprovalRequestedEvent] = []

        async def handler(event: ApprovalRequestedEvent) -> None:
            events_received.append(event)

        bus.subscribe(ApprovalRequestedEvent, handler)

        proposal = await action_manager.create_proposal(
            conversation_id="conv_123",
            message_id=None,
            tool_name="propose_allocation_change",
            tool_use_id="tu_001",
            tool_input={"strategy_id": "orb_breakout", "new_allocation_pct": 30, "reason": "test"},
        )

        await bus.drain()

        assert len(events_received) == 1
        event = events_received[0]
        assert event.action_id == proposal.id
        assert event.action_type == "propose_allocation_change"
        assert "orb_breakout" in event.description


class TestActionManagerApprove:
    """Test proposal approval."""

    async def test_approve_proposal_happy_path(
        self,
        action_manager: ActionManager,
    ) -> None:
        """approve_proposal marks proposal as approved."""
        proposal = await action_manager.create_proposal(
            conversation_id="conv_123",
            message_id=None,
            tool_name="propose_allocation_change",
            tool_use_id="tu_001",
            tool_input={"strategy_id": "orb_breakout", "new_allocation_pct": 30, "reason": "test"},
        )

        approved = await action_manager.approve_proposal(proposal.id)

        assert approved.status == "approved"
        assert approved.resolved_at is not None

    async def test_approve_proposal_publishes_event(
        self,
        action_manager: ActionManager,
        bus: EventBus,
    ) -> None:
        """approve_proposal publishes ApprovalGrantedEvent."""
        events_received: list[ApprovalGrantedEvent] = []

        async def handler(event: ApprovalGrantedEvent) -> None:
            events_received.append(event)

        bus.subscribe(ApprovalGrantedEvent, handler)

        proposal = await action_manager.create_proposal(
            conversation_id="conv_123",
            message_id=None,
            tool_name="propose_allocation_change",
            tool_use_id="tu_001",
            tool_input={"strategy_id": "orb_breakout", "new_allocation_pct": 30, "reason": "test"},
        )

        await action_manager.approve_proposal(proposal.id)
        await bus.drain()

        assert len(events_received) == 1
        assert events_received[0].action_id == proposal.id

    async def test_approve_expired_proposal_raises_error(
        self,
        db: DatabaseManager,
        bus: EventBus,
    ) -> None:
        """approve_proposal raises ProposalExpiredError for expired proposals."""
        import asyncio

        # Use 1s TTL and wait for expiration
        config = AIConfig(enabled=True, api_key="test", proposal_ttl_seconds=1)
        manager = ActionManager(db, bus, config)
        await manager.initialize()

        proposal = await manager.create_proposal(
            conversation_id="conv_123",
            message_id=None,
            tool_name="propose_allocation_change",
            tool_use_id="tu_001",
            tool_input={"strategy_id": "orb_breakout", "new_allocation_pct": 30, "reason": "test"},
        )

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Proposal should have expired
        with pytest.raises(ProposalExpiredError):
            await manager.approve_proposal(proposal.id)

    async def test_approve_already_approved_raises_error(
        self,
        action_manager: ActionManager,
    ) -> None:
        """approve_proposal raises ProposalNotPendingError for already-approved proposals."""
        proposal = await action_manager.create_proposal(
            conversation_id="conv_123",
            message_id=None,
            tool_name="propose_allocation_change",
            tool_use_id="tu_001",
            tool_input={"strategy_id": "orb_breakout", "new_allocation_pct": 30, "reason": "test"},
        )

        await action_manager.approve_proposal(proposal.id)

        with pytest.raises(ProposalNotPendingError) as exc_info:
            await action_manager.approve_proposal(proposal.id)

        assert exc_info.value.current_status == "approved"

    async def test_approve_nonexistent_proposal_raises_error(
        self,
        action_manager: ActionManager,
    ) -> None:
        """approve_proposal raises ProposalNotFoundError for unknown ID."""
        with pytest.raises(ProposalNotFoundError):
            await action_manager.approve_proposal("nonexistent_id")


class TestActionManagerReject:
    """Test proposal rejection."""

    async def test_reject_proposal_happy_path(
        self,
        action_manager: ActionManager,
    ) -> None:
        """reject_proposal marks proposal as rejected."""
        proposal = await action_manager.create_proposal(
            conversation_id="conv_123",
            message_id=None,
            tool_name="propose_allocation_change",
            tool_use_id="tu_001",
            tool_input={"strategy_id": "orb_breakout", "new_allocation_pct": 30, "reason": "test"},
        )

        rejected = await action_manager.reject_proposal(proposal.id, reason="Not now")

        assert rejected.status == "rejected"
        assert rejected.resolved_at is not None

    async def test_reject_proposal_publishes_event(
        self,
        action_manager: ActionManager,
        bus: EventBus,
    ) -> None:
        """reject_proposal publishes ApprovalDeniedEvent."""
        events_received: list[ApprovalDeniedEvent] = []

        async def handler(event: ApprovalDeniedEvent) -> None:
            events_received.append(event)

        bus.subscribe(ApprovalDeniedEvent, handler)

        proposal = await action_manager.create_proposal(
            conversation_id="conv_123",
            message_id=None,
            tool_name="propose_allocation_change",
            tool_use_id="tu_001",
            tool_input={"strategy_id": "orb_breakout", "new_allocation_pct": 30, "reason": "test"},
        )

        await action_manager.reject_proposal(proposal.id, reason="Not appropriate")
        await bus.drain()

        assert len(events_received) == 1
        assert events_received[0].action_id == proposal.id
        assert events_received[0].reason == "Not appropriate"


class TestActionManagerCleanup:
    """Test expired proposal cleanup."""

    async def test_cleanup_expired_marks_stale_proposals(
        self,
        db: DatabaseManager,
        bus: EventBus,
    ) -> None:
        """cleanup_expired marks all stale proposals as expired."""
        import asyncio

        # Use 1s TTL and wait for expiration
        config = AIConfig(enabled=True, api_key="test", proposal_ttl_seconds=1)
        manager = ActionManager(db, bus, config)
        await manager.initialize()

        # Create a few proposals
        await manager.create_proposal(
            conversation_id="conv_123",
            message_id=None,
            tool_name="propose_allocation_change",
            tool_use_id="tu_001",
            tool_input={"strategy_id": "orb_breakout", "new_allocation_pct": 30, "reason": "test"},
        )
        await manager.create_proposal(
            conversation_id="conv_123",
            message_id=None,
            tool_name="propose_strategy_suspend",
            tool_use_id="tu_002",
            tool_input={"strategy_id": "orb_breakout", "reason": "test"},
        )

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Run cleanup
        count = await manager.cleanup_expired()

        # Both should be expired
        assert count == 2

        # Verify no pending proposals
        pending = await manager.get_pending_proposals()
        assert len(pending) == 0


class TestActionManagerPersistence:
    """Test database persistence."""

    async def test_persistence_survives_restart(
        self,
        db: DatabaseManager,
        bus: EventBus,
        ai_config: AIConfig,
    ) -> None:
        """Proposals persist across manager restarts."""
        # Create first manager and proposal
        manager1 = ActionManager(db, bus, ai_config)
        await manager1.initialize()

        proposal = await manager1.create_proposal(
            conversation_id="conv_123",
            message_id=None,
            tool_name="propose_allocation_change",
            tool_use_id="tu_001",
            tool_input={"strategy_id": "orb_breakout", "new_allocation_pct": 30, "reason": "test"},
        )
        proposal_id = proposal.id

        # Create second manager (simulating restart)
        manager2 = ActionManager(db, bus, ai_config)
        await manager2.initialize()

        # Retrieve proposal - should still exist
        retrieved = await manager2.get_proposal(proposal_id)
        assert retrieved is not None
        assert retrieved.id == proposal_id
        assert retrieved.tool_name == "propose_allocation_change"
        assert retrieved.tool_input["strategy_id"] == "orb_breakout"
        assert retrieved.status == "pending"


class TestActionManagerTTL:
    """Test proposal TTL respects config."""

    async def test_proposal_ttl_from_config(
        self,
        db: DatabaseManager,
        bus: EventBus,
    ) -> None:
        """Proposal expires_at uses TTL from config."""
        config = AIConfig(enabled=True, api_key="test", proposal_ttl_seconds=600)
        manager = ActionManager(db, bus, config)
        await manager.initialize()

        proposal = await manager.create_proposal(
            conversation_id="conv_123",
            message_id=None,
            tool_name="propose_allocation_change",
            tool_use_id="tu_001",
            tool_input={"strategy_id": "orb_breakout", "new_allocation_pct": 30, "reason": "test"},
        )

        # expires_at should be ~600 seconds after created_at
        diff = (proposal.expires_at - proposal.created_at).total_seconds()
        assert 590 <= diff <= 610  # Allow small variance


class TestActionManagerExecuteAndFail:
    """Test execute and fail methods."""

    async def test_execute_proposal_sets_result(
        self,
        action_manager: ActionManager,
    ) -> None:
        """execute_proposal stores result and marks as executed."""
        proposal = await action_manager.create_proposal(
            conversation_id="conv_123",
            message_id=None,
            tool_name="propose_allocation_change",
            tool_use_id="tu_001",
            tool_input={"strategy_id": "orb_breakout", "new_allocation_pct": 30, "reason": "test"},
        )

        # First approve
        await action_manager.approve_proposal(proposal.id)

        # Then execute
        result = {"old_allocation": 25, "new_allocation": 30}
        executed = await action_manager.execute_proposal(proposal.id, result)

        assert executed.status == "executed"
        assert executed.result == result

    async def test_fail_proposal_stores_reason(
        self,
        action_manager: ActionManager,
    ) -> None:
        """fail_proposal stores failure reason."""
        proposal = await action_manager.create_proposal(
            conversation_id="conv_123",
            message_id=None,
            tool_name="propose_allocation_change",
            tool_use_id="tu_001",
            tool_input={"strategy_id": "orb_breakout", "new_allocation_pct": 30, "reason": "test"},
        )

        # First approve
        await action_manager.approve_proposal(proposal.id)

        # Then fail
        failed = await action_manager.fail_proposal(proposal.id, "Strategy not found")

        assert failed.status == "failed"
        assert failed.failure_reason == "Strategy not found"


class TestActionManagerGetPending:
    """Test getting pending proposals."""

    async def test_get_pending_proposals_all(
        self,
        action_manager: ActionManager,
    ) -> None:
        """get_pending_proposals returns all pending proposals."""
        await action_manager.create_proposal(
            conversation_id="conv_1",
            message_id=None,
            tool_name="propose_allocation_change",
            tool_use_id="tu_001",
            tool_input={"strategy_id": "orb_breakout", "new_allocation_pct": 30, "reason": "test"},
        )
        await action_manager.create_proposal(
            conversation_id="conv_2",
            message_id=None,
            tool_name="propose_strategy_suspend",
            tool_use_id="tu_002",
            tool_input={"strategy_id": "vwap_reclaim", "reason": "test"},
        )

        pending = await action_manager.get_pending_proposals()
        assert len(pending) == 2

    async def test_get_pending_proposals_by_conversation(
        self,
        action_manager: ActionManager,
    ) -> None:
        """get_pending_proposals filters by conversation_id."""
        await action_manager.create_proposal(
            conversation_id="conv_1",
            message_id=None,
            tool_name="propose_allocation_change",
            tool_use_id="tu_001",
            tool_input={"strategy_id": "orb_breakout", "new_allocation_pct": 30, "reason": "test"},
        )
        await action_manager.create_proposal(
            conversation_id="conv_2",
            message_id=None,
            tool_name="propose_strategy_suspend",
            tool_use_id="tu_002",
            tool_input={"strategy_id": "vwap_reclaim", "reason": "test"},
        )

        pending = await action_manager.get_pending_proposals(conversation_id="conv_1")
        assert len(pending) == 1
        assert pending[0].conversation_id == "conv_1"
