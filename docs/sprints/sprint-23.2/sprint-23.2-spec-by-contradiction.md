# Sprint 23.2: What This Sprint Does NOT Do

## Out of Scope
1. **GUI/web dashboard for runner monitoring**: Terminal output only. No React UI.
2. **Real-time token usage from Anthropic API**: Cost is estimated from output length, not actual billing.
3. **Automatic sprint planning**: Runner executes plans, doesn't create them.
4. **CI/CD integration**: No GitHub Actions, no Jenkins, no automated triggers.
5. **Windows support**: Linux/macOS only (subprocess, asyncio patterns).
6. **Modifications to ARGUS trading system**: Nothing under `argus/` is touched.
7. **Modifications to existing scripts**: Nothing under `scripts/*.py` (diagnostic scripts) is touched.
8. **Runner self-testing**: The runner doesn't test itself during sprint execution — that's what this sprint's tests do.

## Edge Cases to Reject
1. **Claude Code CLI not installed**: Print clear error message and exit. Do not attempt installation.
2. **Git repo has uncommitted changes on startup**: Refuse to start. Print "git stash or commit first."
3. **run-state.json corrupted (invalid JSON)**: Refuse to resume. Print "run-state.json is corrupted. Remove it to start fresh or fix manually."
4. **Lock file from different machine**: Print warning but allow --resume to clear it (PID validation is local).

## Scope Boundaries
- **Do NOT modify:** Anything under `argus/`, existing `scripts/*.py`, `config/system.yaml`, `docs/protocols/` (protocol docs are read-only inputs)
- **Do NOT optimize:** Runner execution speed beyond the performance benchmarks listed. No Cython, no compiled extensions.
- **Do NOT refactor:** Protocol documents or schema definitions — implement them as specified.

## Interaction Boundaries
- This sprint does NOT change: Any trading system behavior, any existing test, any config file, any API endpoint.
- This sprint does NOT affect: Paper trading, data pipelines, Command Center UI.

## Deferred to Future Sprints
| Item | Target | DEF Reference |
|------|--------|---------------|
| Runner self-update mechanism | Unscheduled | DEF-NEW |
| Web-based run monitoring dashboard | Unscheduled | DEF-NEW |
| Windows/WSL support | Unscheduled | DEF-NEW |
| CI/CD trigger integration | Unscheduled | DEF-NEW |
