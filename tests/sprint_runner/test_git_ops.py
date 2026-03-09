"""Tests for git operations module."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

from scripts.sprint_runner.git_ops import (
    FileValidationError,
    checkpoint,
    commit,
    compute_file_hash,
    diff_files,
    diff_full,
    get_sha,
    is_clean,
    rollback,
    run_tests,
    validate_pre_session_files,
    validate_protected_files,
    verify_branch,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def git_repo() -> Path:
    """Create a temporary git repository for testing.

    Sets up a repo with an initial commit so we have a valid HEAD.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Configure user for commits
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create initial file and commit
        (repo_path / "initial.txt").write_text("initial content")
        subprocess.run(
            ["git", "add", "-A"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        yield repo_path


# ---------------------------------------------------------------------------
# Branch Verification Tests
# ---------------------------------------------------------------------------


class TestVerifyBranch:
    """Tests for branch verification."""

    def test_verify_branch_matches_current(self, git_repo: Path) -> None:
        """Returns True when branch matches current branch."""
        # Default branch after git init is typically main or master
        # Get actual branch name
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        current_branch = result.stdout.strip()

        assert verify_branch(current_branch, cwd=git_repo) is True

    def test_verify_branch_different_returns_false(self, git_repo: Path) -> None:
        """Returns False when branch doesn't match."""
        assert verify_branch("nonexistent-branch", cwd=git_repo) is False


# ---------------------------------------------------------------------------
# Clean State Tests
# ---------------------------------------------------------------------------


class TestIsClean:
    """Tests for working directory cleanliness check."""

    def test_is_clean_when_no_changes(self, git_repo: Path) -> None:
        """Returns True when working directory is clean."""
        assert is_clean(cwd=git_repo) is True

    def test_is_clean_false_with_modified_file(self, git_repo: Path) -> None:
        """Returns False when tracked file is modified."""
        (git_repo / "initial.txt").write_text("modified content")
        assert is_clean(cwd=git_repo) is False

    def test_is_clean_false_with_untracked_file(self, git_repo: Path) -> None:
        """Returns False when untracked file exists."""
        (git_repo / "new_file.txt").write_text("new content")
        assert is_clean(cwd=git_repo) is False


# ---------------------------------------------------------------------------
# SHA Tests
# ---------------------------------------------------------------------------


class TestGetSha:
    """Tests for SHA retrieval."""

    def test_get_sha_returns_valid_sha(self, git_repo: Path) -> None:
        """Returns a valid 40-character SHA."""
        sha = get_sha(cwd=git_repo)

        assert len(sha) == 40
        assert all(c in "0123456789abcdef" for c in sha)


# ---------------------------------------------------------------------------
# Checkpoint and Rollback Tests
# ---------------------------------------------------------------------------


class TestCheckpointAndRollback:
    """Tests for checkpoint and rollback operations."""

    def test_checkpoint_returns_current_sha(self, git_repo: Path) -> None:
        """Checkpoint returns the current HEAD SHA."""
        expected = get_sha(cwd=git_repo)
        actual = checkpoint(cwd=git_repo)
        assert actual == expected

    def test_rollback_restores_clean_state(self, git_repo: Path) -> None:
        """Rollback restores working directory to checkpoint state."""
        # Get checkpoint SHA
        sha = checkpoint(cwd=git_repo)

        # Make modifications
        (git_repo / "initial.txt").write_text("modified")
        (git_repo / "new_file.txt").write_text("new")

        assert is_clean(cwd=git_repo) is False

        # Rollback
        rollback(sha, cwd=git_repo)

        # Verify clean state
        assert is_clean(cwd=git_repo) is True

        # Verify original content restored
        assert (git_repo / "initial.txt").read_text() == "initial content"

        # Verify untracked file removed
        assert not (git_repo / "new_file.txt").exists()


# ---------------------------------------------------------------------------
# Diff Tests
# ---------------------------------------------------------------------------


class TestDiffOperations:
    """Tests for diff operations."""

    def test_diff_files_empty_when_clean(self, git_repo: Path) -> None:
        """diff_files returns empty list when no changes."""
        result = diff_files(cwd=git_repo)
        assert result == []

    def test_diff_files_includes_modified(self, git_repo: Path) -> None:
        """diff_files includes modified tracked files."""
        (git_repo / "initial.txt").write_text("modified")

        result = diff_files(cwd=git_repo)
        assert "initial.txt" in result

    def test_diff_files_includes_untracked(self, git_repo: Path) -> None:
        """diff_files includes untracked files."""
        (git_repo / "new.txt").write_text("new content")

        result = diff_files(cwd=git_repo)
        assert "new.txt" in result

    def test_diff_full_returns_patch(self, git_repo: Path) -> None:
        """diff_full returns diff patch for changes."""
        (git_repo / "initial.txt").write_text("modified content")

        result = diff_full(cwd=git_repo)

        assert "diff --git" in result
        assert "modified content" in result


# ---------------------------------------------------------------------------
# Commit Tests
# ---------------------------------------------------------------------------


class TestCommit:
    """Tests for commit operations."""

    def test_commit_creates_new_commit(self, git_repo: Path) -> None:
        """commit stages and commits changes."""
        original_sha = get_sha(cwd=git_repo)

        # Make a change
        (git_repo / "new_file.txt").write_text("new content")

        # Commit
        new_sha = commit("Add new file", cwd=git_repo)

        # Verify new SHA
        assert new_sha != original_sha
        assert new_sha == get_sha(cwd=git_repo)

        # Verify clean state
        assert is_clean(cwd=git_repo) is True


# ---------------------------------------------------------------------------
# File Validation Tests
# ---------------------------------------------------------------------------


class TestValidatePreSessionFiles:
    """Tests for pre-session file validation."""

    def test_validate_files_exist_passes(self, git_repo: Path) -> None:
        """Passes when all files exist and are non-empty."""
        (git_repo / "file1.txt").write_text("content1")
        (git_repo / "file2.txt").write_text("content2")

        # Should not raise
        validate_pre_session_files(["file1.txt", "file2.txt"], cwd=git_repo)

    def test_validate_missing_file_raises(self, git_repo: Path) -> None:
        """Raises FileValidationError when file is missing."""
        with pytest.raises(FileValidationError, match="Missing files"):
            validate_pre_session_files(["nonexistent.txt"], cwd=git_repo)

    def test_validate_empty_file_raises(self, git_repo: Path) -> None:
        """Raises FileValidationError when file is empty."""
        (git_repo / "empty.txt").write_text("")

        with pytest.raises(FileValidationError, match="Empty files"):
            validate_pre_session_files(["empty.txt"], cwd=git_repo)


# ---------------------------------------------------------------------------
# Protected Files Tests
# ---------------------------------------------------------------------------


class TestValidateProtectedFiles:
    """Tests for protected file validation."""

    def test_no_violations_returns_empty(self) -> None:
        """Returns empty list when no protected files changed."""
        changed = ["src/new_file.py", "tests/test_new.py"]
        protected = ["argus/core/", "config/system.yaml"]

        result = validate_protected_files(changed, protected)
        assert result == []

    def test_direct_match_violation(self) -> None:
        """Detects direct file match violation."""
        changed = ["config/system.yaml", "src/new.py"]
        protected = ["config/system.yaml"]

        result = validate_protected_files(changed, protected)
        assert "config/system.yaml" in result

    def test_directory_prefix_violation(self) -> None:
        """Detects directory prefix violation."""
        changed = ["argus/core/risk_manager.py", "tests/test.py"]
        protected = ["argus/core/"]

        result = validate_protected_files(changed, protected)
        assert "argus/core/risk_manager.py" in result


# ---------------------------------------------------------------------------
# File Hash Tests
# ---------------------------------------------------------------------------


class TestComputeFileHash:
    """Tests for file hash computation."""

    def test_compute_file_hash_valid(self, git_repo: Path) -> None:
        """Computes SHA-256 hash of file content."""
        content = "test content for hashing"
        (git_repo / "hashtest.txt").write_text(content)

        result = compute_file_hash("hashtest.txt", cwd=git_repo)

        # SHA-256 produces 64 hex characters
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_compute_file_hash_same_content_same_hash(self, git_repo: Path) -> None:
        """Same content produces same hash."""
        content = "identical content"
        (git_repo / "file1.txt").write_text(content)
        (git_repo / "file2.txt").write_text(content)

        hash1 = compute_file_hash("file1.txt", cwd=git_repo)
        hash2 = compute_file_hash("file2.txt", cwd=git_repo)

        assert hash1 == hash2

    def test_compute_file_hash_missing_file_raises(self, git_repo: Path) -> None:
        """Raises FileValidationError for missing file."""
        with pytest.raises(FileValidationError, match="Cannot read file"):
            compute_file_hash("nonexistent.txt", cwd=git_repo)


# ---------------------------------------------------------------------------
# Test Runner Tests
# ---------------------------------------------------------------------------


class TestRunTests:
    """Tests for test runner function."""

    def test_run_tests_with_echo_command(self, git_repo: Path) -> None:
        """Parses basic command output."""
        # Use a simple command that exits 0
        count, passed = run_tests("echo 'hello world'", cwd=git_repo)

        assert passed is True
        # No pytest output, so count should be 0
        assert count == 0

    def test_run_tests_failing_command(self, git_repo: Path) -> None:
        """Detects failing command."""
        count, passed = run_tests("false", cwd=git_repo)

        assert passed is False
        assert count == 0

    def test_run_tests_invalid_command(self, git_repo: Path) -> None:
        """Handles invalid command gracefully."""
        count, passed = run_tests("nonexistent_command_xyz", cwd=git_repo)

        # Should return failure, not crash
        assert passed is False
        assert count == 0
