"""Action proposal management for the AI Copilot.

Handles the lifecycle of AI-proposed actions that require operator approval:
- Create proposals from tool_use blocks
- Approve/reject proposals
- Track expiration and cleanup
- Publish events to Event Bus

NOTE: Execution happens in Session 3b — this session only handles the
proposal lifecycle (create → approve/reject/expire).
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from argus.ai.tools import TOOLS_REQUIRING_APPROVAL
from argus.core.events import ApprovalRequestedEvent, ApprovalGrantedEvent, ApprovalDeniedEvent
from argus.core.ids import generate_id

if TYPE_CHECKING:
    from argus.ai.config import AIConfig
    from argus.core.event_bus import EventBus
    from argus.db.manager import DatabaseManager

logger = logging.getLogger(__name__)


class ActionProposalError(Exception):
    """Base exception for action proposal errors."""

    pass


class ProposalNotFoundError(ActionProposalError):
    """Raised when a proposal is not found."""

    pass


class ProposalExpiredError(ActionProposalError):
    """Raised when attempting to approve an expired proposal."""

    pass


class ProposalNotPendingError(ActionProposalError):
    """Raised when attempting to approve/reject a non-pending proposal."""

    def __init__(self, current_status: str) -> None:
        """Initialize with current status.

        Args:
            current_status: The current status of the proposal.
        """
        self.current_status = current_status
        super().__init__(f"Proposal is {current_status}")


class InvalidToolError(ActionProposalError):
    """Raised when a tool is not in TOOLS_REQUIRING_APPROVAL."""

    pass


@dataclass
class ActionProposal:
    """A proposed action from the AI that requires operator approval.

    Attributes:
        id: Unique ULID for the proposal.
        conversation_id: The conversation this proposal originated from.
        message_id: The assistant message that contained the tool_use.
        tool_name: The tool being invoked (e.g., 'propose_allocation_change').
        tool_use_id: Claude's tool_use_id for correlation.
        tool_input: The tool input parameters.
        status: Current status (pending, approved, rejected, expired, executed, failed).
        result: Execution result (after approve+execute).
        failure_reason: Reason if status is 'failed'.
        created_at: When the proposal was created.
        expires_at: When the proposal expires.
        resolved_at: When the proposal was approved/rejected/expired.
    """

    id: str
    conversation_id: str
    message_id: str | None
    tool_name: str
    tool_use_id: str
    tool_input: dict
    status: str
    result: dict | None
    failure_reason: str | None
    created_at: datetime
    expires_at: datetime
    resolved_at: datetime | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary representation.

        Returns:
            Dict with all proposal fields serializable to JSON.
        """
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id,
            "tool_name": self.tool_name,
            "tool_use_id": self.tool_use_id,
            "tool_input": self.tool_input,
            "status": self.status,
            "result": self.result,
            "failure_reason": self.failure_reason,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


class ActionManager:
    """Manages AI action proposals and their lifecycle.

    Handles creating proposals from tool_use blocks, approving/rejecting,
    tracking expiration, and publishing events. Persists to SQLite.

    Usage:
        manager = ActionManager(db, event_bus, config)
        await manager.initialize()

        proposal = await manager.create_proposal(
            conversation_id="...",
            message_id="...",
            tool_name="propose_allocation_change",
            tool_use_id="...",
            tool_input={"strategy_id": "orb_breakout", ...},
        )

        approved = await manager.approve_proposal(proposal.id)
    """

    _TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS ai_action_proposals (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            message_id TEXT,
            tool_name TEXT NOT NULL,
            tool_use_id TEXT NOT NULL,
            tool_input TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            result TEXT,
            failure_reason TEXT,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            resolved_at TEXT
        )
    """

    _INDEX_SQL = [
        "CREATE INDEX IF NOT EXISTS idx_proposals_status ON ai_action_proposals(status)",
        "CREATE INDEX IF NOT EXISTS idx_proposals_conversation ON ai_action_proposals(conversation_id)",
    ]

    def __init__(
        self,
        db: DatabaseManager,
        event_bus: EventBus,
        config: AIConfig,
    ) -> None:
        """Initialize the action manager.

        Args:
            db: Database manager for persistence.
            event_bus: Event bus for publishing approval events.
            config: AI configuration with TTL settings.
        """
        self._db = db
        self._event_bus = event_bus
        self._config = config
        self._cleanup_task: asyncio.Task[None] | None = None

    async def initialize(self) -> None:
        """Initialize database tables and clean up stale proposals.

        Creates the ai_action_proposals table if it doesn't exist,
        then marks any pending proposals from previous runs as expired.
        """
        await self._db.execute(self._TABLE_SQL)
        for index_sql in self._INDEX_SQL:
            await self._db.execute(index_sql)
        await self._db.commit()

        # Clean up any expired proposals from previous runs
        await self.cleanup_expired()

        logger.info("ActionManager initialized")

    def start_cleanup_task(self) -> None:
        """Start the periodic cleanup task.

        Runs cleanup every 30 seconds to expire stale proposals.
        Call this after initialize() during server startup.
        """
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(
                self._periodic_cleanup(),
                name="action_manager_cleanup",
            )
            logger.debug("Started ActionManager cleanup task")

    def stop_cleanup_task(self) -> None:
        """Stop the periodic cleanup task.

        Call this during server shutdown.
        """
        if self._cleanup_task is not None and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            logger.debug("Stopped ActionManager cleanup task")

    async def _periodic_cleanup(self) -> None:
        """Periodically clean up expired proposals."""
        while True:
            try:
                await asyncio.sleep(30)
                await self.cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in periodic cleanup: {e}")

    async def create_proposal(
        self,
        conversation_id: str,
        message_id: str | None,
        tool_name: str,
        tool_use_id: str,
        tool_input: dict,
    ) -> ActionProposal:
        """Create a new action proposal.

        Validates the tool requires approval, supersedes any existing pending
        proposal of the same type, creates the new proposal, and publishes
        ApprovalRequestedEvent.

        Args:
            conversation_id: The conversation this proposal originated from.
            message_id: The assistant message that contained the tool_use.
            tool_name: The tool being invoked.
            tool_use_id: Claude's tool_use_id for correlation.
            tool_input: The tool input parameters.

        Returns:
            The created ActionProposal.

        Raises:
            InvalidToolError: If tool_name is not in TOOLS_REQUIRING_APPROVAL.
        """
        # Validate tool requires approval
        if tool_name not in TOOLS_REQUIRING_APPROVAL:
            raise InvalidToolError(
                f"Tool '{tool_name}' does not require approval. "
                f"Valid tools: {TOOLS_REQUIRING_APPROVAL}"
            )

        # Supersede any existing pending proposal of same type
        await self._supersede_existing_pending(tool_name)

        # Create new proposal
        proposal_id = generate_id()
        now = datetime.now(ZoneInfo("UTC"))
        ttl_seconds = self._config.proposal_ttl_seconds
        expires_at = now + timedelta(seconds=ttl_seconds)

        proposal = ActionProposal(
            id=proposal_id,
            conversation_id=conversation_id,
            message_id=message_id,
            tool_name=tool_name,
            tool_use_id=tool_use_id,
            tool_input=tool_input,
            status="pending",
            result=None,
            failure_reason=None,
            created_at=now,
            expires_at=expires_at,
            resolved_at=None,
        )

        # Persist to database
        sql = """
            INSERT INTO ai_action_proposals (
                id, conversation_id, message_id, tool_name, tool_use_id,
                tool_input, status, result, failure_reason, created_at,
                expires_at, resolved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self._db.execute(
            sql,
            (
                proposal.id,
                proposal.conversation_id,
                proposal.message_id,
                proposal.tool_name,
                proposal.tool_use_id,
                json.dumps(proposal.tool_input),
                proposal.status,
                json.dumps(proposal.result) if proposal.result else None,
                proposal.failure_reason,
                proposal.created_at.isoformat(),
                proposal.expires_at.isoformat(),
                None,
            ),
        )
        await self._db.commit()

        # Publish ApprovalRequestedEvent
        description = self._build_proposal_description(tool_name, tool_input)
        risk_level = self._assess_risk_level(tool_name, tool_input)

        await self._event_bus.publish(
            ApprovalRequestedEvent(
                action_id=proposal_id,
                action_type=tool_name,
                description=description,
                risk_level=risk_level,
            )
        )

        logger.info(
            "Created proposal %s for %s (expires in %ds)",
            proposal_id[:8],
            tool_name,
            ttl_seconds,
        )

        return proposal

    async def approve_proposal(self, proposal_id: str) -> ActionProposal:
        """Approve a pending proposal.

        Marks the proposal as approved and publishes ApprovalGrantedEvent.
        Execution happens separately (Session 3b).

        Args:
            proposal_id: The proposal ULID.

        Returns:
            The updated ActionProposal.

        Raises:
            ProposalNotFoundError: If proposal doesn't exist.
            ProposalExpiredError: If proposal has expired.
            ProposalNotPendingError: If proposal is not in 'pending' status.
        """
        proposal = await self.get_proposal(proposal_id)
        if proposal is None:
            raise ProposalNotFoundError(f"Proposal {proposal_id} not found")

        if proposal.status != "pending":
            raise ProposalNotPendingError(proposal.status)

        # Check expiration
        now = datetime.now(ZoneInfo("UTC"))
        if now > proposal.expires_at:
            # Mark as expired first
            await self._update_status(proposal_id, "expired", resolved_at=now)
            raise ProposalExpiredError(f"Proposal {proposal_id} expired")

        # Mark as approved
        await self._update_status(proposal_id, "approved", resolved_at=now)

        # Publish ApprovalGrantedEvent
        await self._event_bus.publish(
            ApprovalGrantedEvent(action_id=proposal_id)
        )

        logger.info("Approved proposal %s for %s", proposal_id[:8], proposal.tool_name)

        # Return updated proposal
        return await self.get_proposal(proposal_id)  # type: ignore

    async def reject_proposal(
        self,
        proposal_id: str,
        reason: str = "",
    ) -> ActionProposal:
        """Reject a pending proposal.

        Marks the proposal as rejected and publishes ApprovalDeniedEvent.

        Args:
            proposal_id: The proposal ULID.
            reason: Optional reason for rejection.

        Returns:
            The updated ActionProposal.

        Raises:
            ProposalNotFoundError: If proposal doesn't exist.
            ProposalNotPendingError: If proposal is not in 'pending' status.
        """
        proposal = await self.get_proposal(proposal_id)
        if proposal is None:
            raise ProposalNotFoundError(f"Proposal {proposal_id} not found")

        if proposal.status != "pending":
            raise ProposalNotPendingError(proposal.status)

        now = datetime.now(ZoneInfo("UTC"))
        await self._update_status(proposal_id, "rejected", resolved_at=now)

        # Publish ApprovalDeniedEvent
        await self._event_bus.publish(
            ApprovalDeniedEvent(action_id=proposal_id, reason=reason)
        )

        logger.info("Rejected proposal %s for %s", proposal_id[:8], proposal.tool_name)

        return await self.get_proposal(proposal_id)  # type: ignore

    async def execute_proposal(
        self,
        proposal_id: str,
        result: dict,
    ) -> ActionProposal:
        """Mark an approved proposal as executed with result.

        Called after successful action execution (Session 3b).

        Args:
            proposal_id: The proposal ULID.
            result: The execution result.

        Returns:
            The updated ActionProposal.

        Raises:
            ProposalNotFoundError: If proposal doesn't exist.
            ProposalNotPendingError: If proposal is not 'approved'.
        """
        proposal = await self.get_proposal(proposal_id)
        if proposal is None:
            raise ProposalNotFoundError(f"Proposal {proposal_id} not found")

        if proposal.status != "approved":
            raise ProposalNotPendingError(proposal.status)

        sql = """
            UPDATE ai_action_proposals
            SET status = 'executed', result = ?
            WHERE id = ?
        """
        await self._db.execute(sql, (json.dumps(result), proposal_id))
        await self._db.commit()

        logger.info("Executed proposal %s", proposal_id[:8])

        return await self.get_proposal(proposal_id)  # type: ignore

    async def fail_proposal(
        self,
        proposal_id: str,
        reason: str,
    ) -> ActionProposal:
        """Mark a proposal as failed with reason.

        Called when action execution fails (Session 3b).

        Args:
            proposal_id: The proposal ULID.
            reason: The failure reason.

        Returns:
            The updated ActionProposal.

        Raises:
            ProposalNotFoundError: If proposal doesn't exist.
        """
        proposal = await self.get_proposal(proposal_id)
        if proposal is None:
            raise ProposalNotFoundError(f"Proposal {proposal_id} not found")

        sql = """
            UPDATE ai_action_proposals
            SET status = 'failed', failure_reason = ?
            WHERE id = ?
        """
        await self._db.execute(sql, (reason, proposal_id))
        await self._db.commit()

        logger.error("Failed proposal %s: %s", proposal_id[:8], reason)

        return await self.get_proposal(proposal_id)  # type: ignore

    async def get_proposal(self, proposal_id: str) -> ActionProposal | None:
        """Retrieve a proposal by ID.

        Args:
            proposal_id: The proposal ULID.

        Returns:
            The ActionProposal, or None if not found.
        """
        sql = "SELECT * FROM ai_action_proposals WHERE id = ?"
        row = await self._db.fetch_one(sql, (proposal_id,))

        if row is None:
            return None

        return self._row_to_proposal(row)

    async def get_pending_proposals(
        self,
        conversation_id: str | None = None,
    ) -> list[ActionProposal]:
        """Get all pending proposals.

        Args:
            conversation_id: Optional filter by conversation.

        Returns:
            List of pending ActionProposals.
        """
        if conversation_id is not None:
            sql = """
                SELECT * FROM ai_action_proposals
                WHERE status = 'pending' AND conversation_id = ?
                ORDER BY created_at DESC
            """
            rows = await self._db.fetch_all(sql, (conversation_id,))
        else:
            sql = """
                SELECT * FROM ai_action_proposals
                WHERE status = 'pending'
                ORDER BY created_at DESC
            """
            rows = await self._db.fetch_all(sql)

        return [self._row_to_proposal(row) for row in rows]

    async def cleanup_expired(self) -> int:
        """Mark all expired pending proposals as expired.

        Returns:
            Number of proposals marked as expired.
        """
        now = datetime.now(ZoneInfo("UTC")).isoformat()

        # Find expired pending proposals
        sql = """
            SELECT id FROM ai_action_proposals
            WHERE status = 'pending' AND expires_at < ?
        """
        rows = await self._db.fetch_all(sql, (now,))

        if not rows:
            return 0

        # Mark them as expired
        update_sql = """
            UPDATE ai_action_proposals
            SET status = 'expired', resolved_at = ?
            WHERE status = 'pending' AND expires_at < ?
        """
        await self._db.execute(update_sql, (now, now))
        await self._db.commit()

        count = len(rows)
        if count > 0:
            logger.info("Cleaned up %d expired proposals", count)

        return count

    async def _supersede_existing_pending(self, tool_name: str) -> None:
        """Supersede any existing pending proposals of the same tool type.

        Args:
            tool_name: The tool type to check.
        """
        now = datetime.now(ZoneInfo("UTC")).isoformat()

        sql = """
            UPDATE ai_action_proposals
            SET status = 'expired',
                resolved_at = ?,
                failure_reason = 'Superseded by new proposal'
            WHERE status = 'pending' AND tool_name = ?
        """
        cursor = await self._db.execute(sql, (now, tool_name))
        await self._db.commit()

        if cursor.rowcount > 0:
            logger.info("Superseded %d existing pending %s proposals", cursor.rowcount, tool_name)

    async def _update_status(
        self,
        proposal_id: str,
        status: str,
        resolved_at: datetime | None = None,
    ) -> None:
        """Update a proposal's status.

        Args:
            proposal_id: The proposal ULID.
            status: The new status.
            resolved_at: When the proposal was resolved.
        """
        sql = """
            UPDATE ai_action_proposals
            SET status = ?, resolved_at = ?
            WHERE id = ?
        """
        resolved_str = resolved_at.isoformat() if resolved_at else None
        await self._db.execute(sql, (status, resolved_str, proposal_id))
        await self._db.commit()

    def _row_to_proposal(self, row: object) -> ActionProposal:
        """Convert a database row to an ActionProposal.

        Args:
            row: The database row (aiosqlite.Row).

        Returns:
            ActionProposal instance.
        """
        r = dict(row)  # type: ignore[arg-type]
        return ActionProposal(
            id=r["id"],
            conversation_id=r["conversation_id"],
            message_id=r["message_id"],
            tool_name=r["tool_name"],
            tool_use_id=r["tool_use_id"],
            tool_input=json.loads(r["tool_input"]),
            status=r["status"],
            result=json.loads(r["result"]) if r["result"] else None,
            failure_reason=r["failure_reason"],
            created_at=datetime.fromisoformat(r["created_at"]),
            expires_at=datetime.fromisoformat(r["expires_at"]),
            resolved_at=datetime.fromisoformat(r["resolved_at"]) if r["resolved_at"] else None,
        )

    def _build_proposal_description(self, tool_name: str, tool_input: dict) -> str:
        """Build a human-readable description for a proposal.

        Args:
            tool_name: The tool being invoked.
            tool_input: The tool input parameters.

        Returns:
            A descriptive string.
        """
        if tool_name == "propose_allocation_change":
            strategy = tool_input.get("strategy_id", "unknown")
            new_alloc = tool_input.get("new_allocation_pct", 0)
            return f"Change {strategy} allocation to {new_alloc}%"
        elif tool_name == "propose_risk_param_change":
            param = tool_input.get("param_path", "unknown")
            new_val = tool_input.get("new_value", 0)
            return f"Change {param} to {new_val}"
        elif tool_name == "propose_strategy_suspend":
            strategy = tool_input.get("strategy_id", "unknown")
            return f"Suspend strategy {strategy}"
        elif tool_name == "propose_strategy_resume":
            strategy = tool_input.get("strategy_id", "unknown")
            return f"Resume strategy {strategy}"
        else:
            return f"Execute {tool_name}"

    def _assess_risk_level(self, tool_name: str, tool_input: dict) -> str:
        """Assess the risk level of a proposal.

        Args:
            tool_name: The tool being invoked.
            tool_input: The tool input parameters.

        Returns:
            Risk level: 'low', 'medium', or 'high'.
        """
        # Suspending a strategy is high risk
        if tool_name == "propose_strategy_suspend":
            return "high"

        # Risk parameter changes could be high risk
        if tool_name == "propose_risk_param_change":
            param = tool_input.get("param_path", "")
            if "loss_limit" in param or "max_" in param:
                return "high"
            return "medium"

        # Allocation changes depend on magnitude
        if tool_name == "propose_allocation_change":
            new_alloc = tool_input.get("new_allocation_pct", 0)
            if new_alloc == 0:
                return "high"  # Zeroing allocation is high risk
            return "medium"

        return "medium"
