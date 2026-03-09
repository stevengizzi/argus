"""Git operations for the sprint runner.

Provides subprocess-based git operations for checkpoint, rollback, diff,
and commit functionality.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class GitError(Exception):
    """Base exception for git operation errors."""


class GitStateError(GitError):
    """Git repository is in unexpected state."""


class FileValidationError(GitError):
    """File validation failed."""


# ---------------------------------------------------------------------------
# Git Operations
# ---------------------------------------------------------------------------


def _run_git(*args: str, cwd: Path | str | None = None) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the result.

    Args:
        *args: Git command arguments (without 'git' prefix).
        cwd: Working directory for the command.

    Returns:
        CompletedProcess with stdout/stderr.

    Raises:
        GitError: If the git command fails.
    """
    cmd = ["git", *args]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            check=False,
        )
        return result
    except FileNotFoundError as e:
        raise GitError("Git is not installed or not in PATH") from e


def _run_git_checked(*args: str, cwd: Path | str | None = None) -> str:
    """Run a git command and return stdout, raising on failure.

    Args:
        *args: Git command arguments.
        cwd: Working directory.

    Returns:
        stdout as string.

    Raises:
        GitError: If the command fails.
    """
    result = _run_git(*args, cwd=cwd)
    if result.returncode != 0:
        raise GitError(f"Git command failed: git {' '.join(args)}\n{result.stderr}")
    return result.stdout.strip()


def verify_branch(expected: str, cwd: Path | str | None = None) -> bool:
    """Check if the current branch matches the expected branch.

    Args:
        expected: Expected branch name.
        cwd: Working directory.

    Returns:
        True if current branch matches, False otherwise.
    """
    try:
        current = _run_git_checked("rev-parse", "--abbrev-ref", "HEAD", cwd=cwd)
        return current == expected
    except GitError:
        return False


def is_clean(cwd: Path | str | None = None) -> bool:
    """Check if the working directory has no uncommitted changes.

    Args:
        cwd: Working directory.

    Returns:
        True if working directory is clean, False otherwise.
    """
    result = _run_git("status", "--porcelain", cwd=cwd)
    if result.returncode != 0:
        return False
    return result.stdout.strip() == ""


def get_sha(cwd: Path | str | None = None) -> str:
    """Get the current HEAD SHA.

    Args:
        cwd: Working directory.

    Returns:
        Full SHA of HEAD.

    Raises:
        GitError: If not in a git repository.
    """
    return _run_git_checked("rev-parse", "HEAD", cwd=cwd)


def checkpoint(cwd: Path | str | None = None) -> str:
    """Create a checkpoint by returning current HEAD SHA.

    Args:
        cwd: Working directory.

    Returns:
        Current HEAD SHA for later rollback.

    Raises:
        GitError: If not in a git repository.
    """
    return get_sha(cwd=cwd)


def rollback(sha: str, cwd: Path | str | None = None) -> None:
    """Rollback to a checkpoint state.

    Restores the working directory to match the given SHA by:
    1. Discarding all changes to tracked files (git checkout -- .)
    2. Removing untracked files and directories (git clean -fd)

    Args:
        sha: The SHA to verify we're rolling back to (for validation).
        cwd: Working directory.

    Raises:
        GitError: If rollback fails.
        GitStateError: If HEAD doesn't match the expected SHA after rollback.
    """
    # Discard changes to tracked files
    _run_git_checked("checkout", "--", ".", cwd=cwd)

    # Remove untracked files and directories
    _run_git_checked("clean", "-fd", cwd=cwd)

    # Verify we're at the expected SHA
    current = get_sha(cwd=cwd)
    if current != sha:
        raise GitStateError(
            f"Rollback verification failed. Expected SHA {sha}, found {current}"
        )


def diff_files(cwd: Path | str | None = None) -> list[str]:
    """Get list of changed files since last commit.

    Includes both staged and unstaged changes, plus untracked files.

    Args:
        cwd: Working directory.

    Returns:
        List of changed file paths.
    """
    # Get modified/staged files
    result = _run_git("diff", "--name-only", "HEAD", cwd=cwd)
    files = set()

    if result.returncode == 0 and result.stdout.strip():
        files.update(result.stdout.strip().split("\n"))

    # Also get untracked files
    result = _run_git("ls-files", "--others", "--exclude-standard", cwd=cwd)
    if result.returncode == 0 and result.stdout.strip():
        files.update(result.stdout.strip().split("\n"))

    return sorted(files)


def diff_full(cwd: Path | str | None = None) -> str:
    """Get full diff patch of all changes.

    Args:
        cwd: Working directory.

    Returns:
        Full diff output as string.
    """
    # Get diff of tracked files
    result = _run_git("diff", "HEAD", cwd=cwd)
    if result.returncode != 0:
        return ""
    return result.stdout


def commit(message: str, cwd: Path | str | None = None) -> str:
    """Stage all changes and commit.

    Args:
        message: Commit message.
        cwd: Working directory.

    Returns:
        SHA of the new commit.

    Raises:
        GitError: If commit fails.
    """
    # Stage all changes
    _run_git_checked("add", "-A", cwd=cwd)

    # Commit
    _run_git_checked("commit", "-m", message, cwd=cwd)

    # Return new SHA
    return get_sha(cwd=cwd)


def validate_pre_session_files(files: list[str], cwd: Path | str | None = None) -> None:
    """Validate that all listed files exist and are non-empty.

    Per DEC-292: Verify all files from prior sessions' "Creates" columns exist
    before starting a new session.

    Args:
        files: List of file paths to validate.
        cwd: Working directory (files are relative to this).

    Raises:
        FileValidationError: If any file is missing or empty.
    """
    base_path = Path(cwd) if cwd else Path.cwd()

    missing = []
    empty = []

    for file_path in files:
        full_path = base_path / file_path
        if not full_path.exists():
            missing.append(file_path)
        elif full_path.stat().st_size == 0:
            empty.append(file_path)

    if missing or empty:
        errors = []
        if missing:
            errors.append(f"Missing files: {missing}")
        if empty:
            errors.append(f"Empty files: {empty}")
        raise FileValidationError("; ".join(errors))


def validate_protected_files(
    changed_files: list[str],
    protected: list[str],
) -> list[str]:
    """Check if any protected files appear in the changed files list.

    Per DEC-294: Return list of protected files that were modified.

    Args:
        changed_files: List of files that changed (from diff_files).
        protected: List of protected file patterns.

    Returns:
        List of protected files that appear in changed_files.
    """
    violations = []
    changed_set = set(changed_files)

    for pattern in protected:
        # Direct match
        if pattern in changed_set:
            violations.append(pattern)
        # Also check if pattern is a prefix (directory protection)
        elif pattern.endswith("/"):
            for changed in changed_files:
                if changed.startswith(pattern):
                    violations.append(changed)

    return sorted(set(violations))


def compute_file_hash(path: str, cwd: Path | str | None = None) -> str:
    """Compute SHA-256 hash of a file's content.

    Per DEC-297: Used for review context file hash verification.

    Args:
        path: Path to the file (relative to cwd or absolute).
        cwd: Working directory.

    Returns:
        Hex digest of SHA-256 hash.

    Raises:
        FileValidationError: If the file cannot be read.
    """
    base_path = Path(cwd) if cwd else Path.cwd()
    full_path = base_path / path

    try:
        content = full_path.read_bytes()
        return hashlib.sha256(content).hexdigest()
    except OSError as e:
        raise FileValidationError(f"Cannot read file {path}: {e}") from e


def run_tests(command: str, cwd: Path | str | None = None) -> tuple[int, bool]:
    """Execute a test command and parse results.

    Args:
        command: Test command to execute (e.g., "python -m pytest tests/ -x -q").
        cwd: Working directory.

    Returns:
        Tuple of (test_count, all_passed).
        test_count is extracted from pytest output; defaults to 0 if not parseable.
        all_passed is True if exit code is 0.
    """
    import re
    import shlex

    try:
        args = shlex.split(command)
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            cwd=cwd,
            check=False,
        )

        all_passed = result.returncode == 0
        test_count = 0

        # Parse pytest output for test count
        # Patterns: "N passed", "N passed, M failed", etc.
        output = result.stdout + result.stderr

        # Match patterns like "123 passed" or "45 passed, 3 failed"
        passed_match = re.search(r"(\d+)\s+passed", output)
        failed_match = re.search(r"(\d+)\s+failed", output)

        if passed_match:
            test_count += int(passed_match.group(1))
        if failed_match:
            test_count += int(failed_match.group(1))

        return (test_count, all_passed)

    except (OSError, ValueError):
        return (0, False)
