# Sprint 23.2: Review Context File

## Review Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session. Do NOT modify any files.
Follow the review skill in `.claude/skills/review.md`.
Your review report MUST include a structured JSON verdict at the end, fenced with ```json:structured-verdict.

## Sprint Spec Summary
**Goal:** Implement the Autonomous Sprint Runner per Sprint 23.1 protocol docs.
**Deliverables:** 12 files in `scripts/sprint_runner/` + entry point. Config, state, lock, executor, git ops, core loop, notifications, triage, conformance, cost, parallel execution.
**Key constraint:** Nothing under `argus/` is modified. All external calls (subprocess, HTTP) mocked in tests.

## Specification by Contradiction
- Do NOT modify: `argus/`, existing `scripts/*.py`, `config/system.yaml`, `docs/protocols/`
- Do NOT add: GUI, CI/CD integration, Windows support
- Do NOT change: Any trading system behavior, any existing test

## Regression Checklist
- R1: All 2,101+ pytest pass
- R2: All 392+ Vitest pass
- R3: No files modified under `argus/`
- R4: No existing scripts modified
- R5: Sprint 23.5 config loads successfully
- R6: Ruff linting passes
- R7: All subprocess/HTTP calls mocked in tests
- R8: Entry point `--help` works

## Escalation Criteria
1. Any modification to `argus/` or existing `scripts/*.py`
2. Runner fails to load Sprint 23.5 runner-config.yaml
3. Existing test regression
4. Live API calls in tests
5. Test count below 60
6. Session compaction
