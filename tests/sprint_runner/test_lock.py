"""Tests for sprint runner lock file management."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from scripts.sprint_runner.lock import LockError, LockFile


class TestLockFile:
    """Tests for LockFile."""

    def test_acquire_and_release(self, temp_dir: Path) -> None:
        """Test acquiring and releasing a lock."""
        lock = LockFile(temp_dir)

        assert not lock.is_locked()

        lock.acquire("23")
        assert lock.is_locked()
        assert lock.lock_path.exists()

        lock_info = lock.get_lock_info()
        assert lock_info is not None
        assert lock_info["sprint"] == "23"
        assert lock_info["pid"] == os.getpid()

        lock.release()
        assert not lock.is_locked()

    def test_acquire_fails_if_pid_running(self, temp_dir: Path) -> None:
        """Test that acquiring fails if another runner is active."""
        lock = LockFile(temp_dir)

        # Create a lock with current PID (simulating another instance)
        lock_data = {
            "pid": os.getpid(),
            "started": "2026-03-07T14:00:00Z",
            "sprint": "22",
            "host": "test-host",
        }
        lock.lock_path.write_text(json.dumps(lock_data))

        # Should fail because PID is running
        with pytest.raises(LockError, match="Another runner instance"):
            lock.acquire("23")

    def test_acquire_clears_stale_lock(self, temp_dir: Path) -> None:
        """Test that stale lock (dead PID) is cleared."""
        lock = LockFile(temp_dir)

        # Create a lock with a non-existent PID
        lock_data = {
            "pid": 99999999,  # Very unlikely to be running
            "started": "2026-03-07T14:00:00Z",
            "sprint": "22",
            "host": "test-host",
        }
        lock.lock_path.write_text(json.dumps(lock_data))

        # Should succeed by clearing the stale lock
        lock.acquire("23")
        assert lock.is_locked()

        new_info = lock.get_lock_info()
        assert new_info is not None
        assert new_info["sprint"] == "23"
        assert new_info["pid"] == os.getpid()

    def test_validate_or_clear_with_stale_lock(self, temp_dir: Path) -> None:
        """Test validate_or_clear clears stale locks."""
        lock = LockFile(temp_dir)

        # Create a stale lock
        lock_data = {
            "pid": 99999999,
            "started": "2026-03-07T14:00:00Z",
            "sprint": "22",
            "host": "test-host",
        }
        lock.lock_path.write_text(json.dumps(lock_data))

        result = lock.validate_or_clear()
        assert result is False  # Lock was stale, cleared
        assert not lock.is_locked()

    def test_validate_or_clear_no_lock(self, temp_dir: Path) -> None:
        """Test validate_or_clear with no existing lock."""
        lock = LockFile(temp_dir)

        result = lock.validate_or_clear()
        assert result is False

    def test_release_only_if_acquired(self, temp_dir: Path) -> None:
        """Test that release only works if this instance acquired."""
        lock = LockFile(temp_dir)

        # Create a lock manually (not via acquire)
        lock_data = {
            "pid": os.getpid(),
            "started": "2026-03-07T14:00:00Z",
            "sprint": "22",
            "host": "test-host",
        }
        lock.lock_path.write_text(json.dumps(lock_data))

        # Release should not remove it (since we didn't acquire)
        lock.release()
        assert lock.is_locked()  # Still locked
