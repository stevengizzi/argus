"""Runner configuration models.

Pydantic models matching the canonical schema in
docs/protocols/schemas/runner-config-schema.md.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Enums (as Literals for Pydantic validation)
# ---------------------------------------------------------------------------


ExecutionMode = str  # "autonomous" | "human-in-the-loop"
DriftAction = str  # "warn" | "halt"


# ---------------------------------------------------------------------------
# Extension Models (optional, not in base schema)
# ---------------------------------------------------------------------------


class SplitDef(BaseModel):
    """A single split definition for auto-split configuration."""

    id: str
    title: str
    scope: str


class AutoSplitConfig(BaseModel):
    """Auto-split configuration for a session."""

    trigger: str  # e.g., "compaction_score > 7"
    splits: list[SplitDef] = Field(default_factory=list)


class SessionMetadata(BaseModel):
    """Extended metadata for individual sessions."""

    title: str = ""
    compaction_score: int = Field(default=5, ge=0, le=10)
    expected_test_delta: int = 0
    test_command: str = "python -m pytest tests/ -x -q"
    parallelizable: bool = False
    parallel_group: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    has_visual_review: bool = False
    contingency: str | None = None
    auto_split: AutoSplitConfig | None = None


class ForbiddenPattern(BaseModel):
    """A forbidden pattern that halts execution if matched."""

    pattern: str
    message: str


# ---------------------------------------------------------------------------
# Config Sub-Models
# ---------------------------------------------------------------------------


class SprintConfig(BaseModel):
    """Sprint package location configuration."""

    directory: str
    session_order: list[str] = Field(default_factory=list)
    review_context_file: str = ""

    @field_validator("directory")
    @classmethod
    def validate_directory_exists(cls, v: str) -> str:
        """Validate that the sprint directory exists."""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Sprint directory does not exist: {v}")
        return v


class ExecutionConfig(BaseModel):
    """Execution mode configuration."""

    mode: str = "autonomous"
    max_retries: int = Field(default=2, ge=0, le=5)
    retry_delay_seconds: int = Field(default=30, ge=1)
    session_timeout_seconds: int = Field(default=0, ge=0)
    enable_agent_teams: bool = False
    model_override: str | None = None
    test_count_tolerance: int = Field(default=0, ge=0)
    compaction_threshold_bytes: int = Field(default=102400, ge=0)

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        """Validate execution mode is valid."""
        valid = {"autonomous", "human-in-the-loop"}
        if v not in valid:
            raise ValueError(f"Invalid execution mode '{v}'. Valid: {sorted(valid)}")
        return v


class GitConfig(BaseModel):
    """Git configuration."""

    branch: str = "main"
    commit_message_format: str = "[Sprint {sprint}] Session {session_id}: {title}"
    auto_commit: bool = True
    save_patches: bool = True


class NotificationTiers(BaseModel):
    """Per-tier notification toggles."""

    HALTED: bool = True
    SESSION_COMPLETE: bool = True
    PHASE_TRANSITION: bool = True
    WARNING: bool = True
    COMPLETED: bool = True

    @model_validator(mode="after")
    def validate_halted_always_true(self) -> NotificationTiers:
        """HALTED and COMPLETED must always be True."""
        if not self.HALTED:
            raise ValueError("notifications.tiers.HALTED cannot be disabled")
        if not self.COMPLETED:
            raise ValueError("notifications.tiers.COMPLETED cannot be disabled")
        return self


class NotificationChannel(BaseModel):
    """Primary notification channel configuration."""

    type: str = "ntfy"
    endpoint: str = ""
    auth_token: str | None = None


class SecondaryChannel(BaseModel):
    """Secondary notification channel (Slack, email, etc.)."""

    type: str
    webhook_url: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    from_addr: str | None = Field(default=None, alias="from")
    to: str | None = None


class QuietHours(BaseModel):
    """Quiet hours configuration."""

    enabled: bool = True
    start_utc: str = "07:00"
    end_utc: str = "13:00"

    @field_validator("start_utc", "end_utc")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Validate HH:MM format."""
        import re

        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError(f"Invalid time format '{v}'. Expected HH:MM")
        hours, minutes = map(int, v.split(":"))
        if hours > 23 or minutes > 59:
            raise ValueError(f"Invalid time value '{v}'")
        return v


class NotificationsConfig(BaseModel):
    """Notifications configuration."""

    tiers: NotificationTiers = Field(default_factory=NotificationTiers)
    primary: NotificationChannel = Field(default_factory=NotificationChannel)
    secondary: list[SecondaryChannel] = Field(default_factory=list)
    quiet_hours: QuietHours = Field(default_factory=QuietHours)
    halted_reminder_minutes: int = Field(default=60, ge=1)


class CostRates(BaseModel):
    """Token-to-cost conversion rates."""

    input_per_million: float = Field(default=3.0, ge=0)
    output_per_million: float = Field(default=15.0, ge=0)
    cached_input_per_million: float = Field(default=0.30, ge=0)


class CostConfig(BaseModel):
    """Cost tracking configuration."""

    ceiling_usd: float = Field(default=50.0, gt=0)
    rates: CostRates = Field(default_factory=CostRates)
    halt_on_ceiling: bool = True


class RunLogConfig(BaseModel):
    """Run log configuration."""

    base_directory: str = ""
    auto_generate_journal: bool = True
    commit_run_log: bool = True


class TriageConfig(BaseModel):
    """Tier 2.5 triage configuration."""

    enabled: bool = True
    prompt_template: str = "docs/protocols/templates/tier-2.5-triage-prompt.md"
    auto_insert_fixes: bool = True
    max_auto_fixes: int = Field(default=3, ge=0, le=10)
    fix_prompt_template: str = "docs/protocols/templates/fix-prompt.md"


class ConformanceConfig(BaseModel):
    """Spec conformance check configuration."""

    enabled: bool = True
    prompt_template: str = "docs/protocols/templates/spec-conformance-prompt.md"
    drift_minor_action: str = "warn"
    drift_major_action: str = "halt"

    @field_validator("drift_minor_action", "drift_major_action")
    @classmethod
    def validate_drift_action(cls, v: str) -> str:
        """Validate drift action is valid."""
        valid = {"warn", "halt"}
        if v not in valid:
            raise ValueError(f"Invalid drift action '{v}'. Valid: {sorted(valid)}")
        return v


class DocSyncConfig(BaseModel):
    """Doc sync configuration."""

    enabled: bool = True
    prompt_template: str = "docs/protocols/templates/doc-sync-automation-prompt.md"
    target_documents: list[str] = Field(
        default_factory=lambda: [
            "docs/project-knowledge.md",
            "docs/architecture.md",
            "docs/decision-log.md",
            "docs/dec-index.md",
            "docs/sprint-history.md",
            "CLAUDE.md",
        ]
    )


# ---------------------------------------------------------------------------
# Top-Level Config
# ---------------------------------------------------------------------------


class RunnerConfig(BaseModel):
    """Complete runner configuration.

    Matches the canonical schema in docs/protocols/schemas/runner-config-schema.md.
    """

    sprint: SprintConfig
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    cost: CostConfig = Field(default_factory=CostConfig)
    run_log: RunLogConfig = Field(default_factory=RunLogConfig)
    triage: TriageConfig = Field(default_factory=TriageConfig)
    conformance: ConformanceConfig = Field(default_factory=ConformanceConfig)
    doc_sync: DocSyncConfig = Field(default_factory=DocSyncConfig)

    # Extension sections (optional)
    session_metadata: dict[str, SessionMetadata] | None = None
    protected_files: list[str] | None = None
    forbidden_patterns: list[ForbiddenPattern] | None = None

    @classmethod
    def from_yaml(cls, path: str) -> RunnerConfig:
        """Load and validate configuration from a YAML file.

        Args:
            path: Path to the YAML configuration file.

        Returns:
            Validated RunnerConfig instance.

        Raises:
            FileNotFoundError: If the file does not exist.
            yaml.YAMLError: If the file is not valid YAML.
            pydantic.ValidationError: If validation fails.
        """
        filepath = Path(path)
        if not filepath.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(filepath) as f:
            raw = yaml.safe_load(f)

        if raw is None:
            raw = {}

        # Apply environment variable overrides
        raw = cls._apply_env_overrides(raw)

        return cls(**raw)

    @staticmethod
    def _apply_env_overrides(raw: dict[str, Any]) -> dict[str, Any]:
        """Apply environment variable overrides to raw config.

        Environment variables:
            ARGUS_RUNNER_MODE: Overrides execution.mode
            ARGUS_RUNNER_SPRINT_DIR: Overrides sprint.directory
            NTFY_TOPIC: Overrides notifications.primary.endpoint
            ARGUS_COST_CEILING: Overrides cost.ceiling_usd
        """
        # ARGUS_RUNNER_MODE
        if mode := os.environ.get("ARGUS_RUNNER_MODE"):
            if "execution" not in raw:
                raw["execution"] = {}
            raw["execution"]["mode"] = mode

        # ARGUS_RUNNER_SPRINT_DIR
        if sprint_dir := os.environ.get("ARGUS_RUNNER_SPRINT_DIR"):
            if "sprint" not in raw:
                raw["sprint"] = {}
            raw["sprint"]["directory"] = sprint_dir

        # NTFY_TOPIC
        if ntfy_topic := os.environ.get("NTFY_TOPIC"):
            if "notifications" not in raw:
                raw["notifications"] = {}
            if "primary" not in raw["notifications"]:
                raw["notifications"]["primary"] = {}
            raw["notifications"]["primary"]["endpoint"] = ntfy_topic

        # ARGUS_COST_CEILING
        if cost_ceiling := os.environ.get("ARGUS_COST_CEILING"):
            if "cost" not in raw:
                raw["cost"] = {}
            with contextlib.suppress(ValueError):
                raw["cost"]["ceiling_usd"] = float(cost_ceiling)

        return raw
