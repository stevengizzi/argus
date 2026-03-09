"""Lock file management.

Prevents concurrent runner instances from operating on the same repository.
"""

from __future__ import annotations

import json
import os
import socket
from datetime import UTC, datetime
from pathlib import Path


class LockError(Exception):
    """Raised when a lock cannot be acquired."""

    pass


class LockFile:
    """Manages the sprint runner lock file.

    The lock file prevents multiple runner instances from operating
    concurrently. Located at `.sprint-runner.lock` in the repo root.

    Lock file format:
        {
            "pid": 12345,
            "started": "2026-03-07T14:00:00Z",
            "sprint": "23",
            "host": "Stevens-MacBook"
        }
    """

    LOCK_FILENAME = ".sprint-runner.lock"

    def __init__(self, repo_root: str | Path | None = None):
        """Initialize the lock file manager.

        Args:
            repo_root: Path to the repository root. If None, uses current
                working directory.
        """
        if repo_root is None:
            repo_root = Path.cwd()
        self.repo_root = Path(repo_root)
        self.lock_path = self.repo_root / self.LOCK_FILENAME
        self._acquired = False

    def acquire(self, sprint: str) -> None:
        """Acquire the lock for a sprint run.

        Args:
            sprint: The sprint identifier (e.g., "23").

        Raises:
            LockError: If another runner instance holds the lock.
        """
        if self.lock_path.exists():
            existing = self._read_lock()
            if existing and self._is_pid_running(existing.get("pid")):
                raise LockError(
                    f"Another runner instance may be active (Sprint {existing.get('sprint')}). "
                    "If the previous run crashed, use --resume to clear the stale lock."
                )
            # Stale lock — warn and clear
            self._clear_lock()

        # Write new lock
        lock_data = {
            "pid": os.getpid(),
            "started": datetime.now(UTC).isoformat(),
            "sprint": sprint,
            "host": socket.gethostname(),
        }
        with open(self.lock_path, "w") as f:
            json.dump(lock_data, f, indent=2)
        self._acquired = True

    def release(self) -> None:
        """Release the lock.

        Only releases if this instance acquired the lock.
        """
        if self._acquired and self.lock_path.exists():
            self._clear_lock()
            self._acquired = False

    def is_locked(self) -> bool:
        """Check if a lock file exists.

        Returns:
            True if a lock file exists, False otherwise.
        """
        return self.lock_path.exists()

    def validate_or_clear(self) -> bool:
        """Validate existing lock or clear if stale.

        Used with --resume: if a lock exists, check if the PID is still
        running. If not, clear the stale lock.

        Returns:
            True if lock was valid (PID running), False if cleared or
            no lock existed.
        """
        if not self.lock_path.exists():
            return False

        existing = self._read_lock()
        if existing and self._is_pid_running(existing.get("pid")):
            return True

        # Stale lock — clear it
        self._clear_lock()
        return False

    def get_lock_info(self) -> dict | None:
        """Get information from the current lock file.

        Returns:
            Lock file data dict, or None if no lock exists.
        """
        if not self.lock_path.exists():
            return None
        return self._read_lock()

    def _read_lock(self) -> dict | None:
        """Read and parse the lock file.

        Returns:
            Lock data dict, or None if file cannot be read/parsed.
        """
        try:
            with open(self.lock_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def _clear_lock(self) -> None:
        """Remove the lock file."""
        self.lock_path.unlink(missing_ok=True)

    @staticmethod
    def _is_pid_running(pid: int | None) -> bool:
        """Check if a process with the given PID is running.

        Uses os.kill(pid, 0) which doesn't actually send a signal,
        but raises an error if the process doesn't exist.

        Args:
            pid: Process ID to check.

        Returns:
            True if the process is running, False otherwise.
        """
        if pid is None:
            return False
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            # ProcessLookupError: PID doesn't exist
            # PermissionError: PID exists but belongs to another user (rare)
            return False
        except OSError:
            return False
