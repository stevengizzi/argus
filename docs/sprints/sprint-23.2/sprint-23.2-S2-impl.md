# Sprint 23.2, Session 2: Executor + Git Operations

## Pre-Flight Checks
1. Read:
   - `scripts/sprint_runner/config.py` (S1 output)
   - `docs/protocols/schemas/structured-closeout-schema.md` (extraction target)
   - `docs/protocols/schemas/structured-review-verdict-schema.md` (extraction target)
   - `docs/protocols/autonomous-sprint-runner.md` (Steps 3–6: implementation, close-out extraction, review, verdict extraction, plus interruption recovery section)
2. Run: `python -m pytest tests/ -x -q` — all passing including S1 tests
3. Verify S1: `python scripts/sprint-runner.py --help`

## Objective
Implement Claude Code CLI invocation via subprocess with structured output extraction, and git operations for checkpoint/rollback/diff/commit.

## Requirements

1. **Create `scripts/sprint_runner/executor.py`**: Claude Code CLI executor.
   - `ClaudeCodeExecutor(config: ExecutionConfig)`.
   - **`async run_session(prompt: str, timeout: int | None) -> ExecutionResult`**:
     - Invoke Claude Code via `subprocess.run` (or `asyncio.create_subprocess_exec` for async): `claude --print --output-format text -p "{prompt}"`. Verify the actual CLI syntax against `claude --help` at runtime — the exact flag names may vary. If the command doesn't exist, raise a clear error.
     - Capture stdout as the full output. Save immediately.
     - Return `ExecutionResult(output, exit_code, duration_seconds, output_size_bytes)`.
   - **`extract_structured_closeout(output: str) -> dict | None`**: Regex extraction of `json:structured-closeout` block. Parse JSON. Validate against schema (check required fields). Return None if block absent.
   - **`extract_structured_verdict(output: str) -> dict | None`**: Same for `json:structured-verdict`.
   - **`classify_failure(output: str) -> str`**: Per DEC-286/295 — if `---BEGIN-CLOSE-OUT---` exists but no JSON block → "llm_compliance". Otherwise → "transient".
   - **Retry logic:** `retry_with_backoff(func, max_retries, base_delay)`. Exponential: delay × 4^attempt. On LLM-compliance failure, prepend reinforcement instruction to prompt on retry.
   - **Compaction detection (DEC-293):** If output_size_bytes > `config.compaction_threshold_bytes`, set `compaction_likely = True` on result.
   - **Dry-run support:** If `dry_run=True`, return a mock ExecutionResult without invoking subprocess.

2. **Create `scripts/sprint_runner/git_ops.py`**: Git operations.
   - All operations via `subprocess.run(["git", ...])` with error checking.
   - **`verify_branch(expected: str) -> bool`**: Check current branch matches.
   - **`is_clean() -> bool`**: No uncommitted changes.
   - **`get_sha() -> str`**: Current HEAD SHA.
   - **`checkpoint() -> str`**: Return current SHA (for rollback reference).
   - **`rollback(sha: str)`**: `git checkout -- .` + `git clean -fd` to restore to checkpoint state.
   - **`diff_files() -> list[str]`**: List of changed files since last commit.
   - **`diff_full() -> str`**: Full diff patch.
   - **`commit(message: str)`**: Stage all + commit.
   - **`validate_pre_session_files(files: list[str])`**: Per DEC-292 — verify all listed files exist and are non-empty. Raise if any missing.
   - **`validate_protected_files(diff_files: list[str], protected: list[str]) -> list[str]`**: Per DEC-294 — return list of protected files that appear in diff.
   - **`compute_file_hash(path: str) -> str`**: SHA-256 of file content. For DEC-297 review context hash.
   - **`run_tests(command: str) -> tuple[int, bool]`**: Execute test command, parse output for test count and pass/fail. Return (count, all_passed).

## Constraints
- Do NOT modify anything under `argus/`
- ALL subprocess calls in tests must be mocked (no actual Claude Code or git commands in CI)
- Git fixture: create temp repos in pytest fixtures using `subprocess.run(["git", "init", ...])` in a temp directory
- Use `unittest.mock.patch` for subprocess mocking

## Test Targets
- `test_executor.py`: mock CLI success, timeout, retry backoff, structured extraction (valid/missing/malformed), failure classification, compaction detection, dry-run (~7)
- `test_git_ops.py`: Using tmp git repo fixture: checkpoint, rollback, diff, commit, branch verify, file validation, protected file check, hash computation (~8)
- Minimum: 15 tests
- Command: `python -m pytest tests/sprint_runner/test_executor.py tests/sprint_runner/test_git_ops.py -v`

## Definition of Done
- [ ] All requirements implemented, all existing + new tests pass (≥15 new)
- [ ] No argus/ files modified. Ruff passes.

## Close-Out
Follow `.claude/skills/close-out.md`. Include structured JSON appendix.

## Sprint-Level Regression Checklist
R1–R8 from `docs/sprints/sprint-23.2/review-context.md`

## Sprint-Level Escalation Criteria
Items 1–6 from `docs/sprints/sprint-23.2/review-context.md`
