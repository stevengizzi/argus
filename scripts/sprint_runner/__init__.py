"""ARGUS Autonomous Sprint Runner.

A Python-based orchestrator that drives sprint execution by invoking
Claude Code CLI programmatically. Replaces the manual paste-prompt →
read-output → paste-into-review → read-verdict cycle with a deterministic
state machine.

See docs/protocols/autonomous-sprint-runner.md for full documentation.
"""

__version__ = "1.0.0"
