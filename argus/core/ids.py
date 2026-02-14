"""ULID-based ID generation for Argus.

All database primary keys use ULIDs — globally unique, time-sortable,
26 characters. Wrapping in a utility centralizes the dependency.
"""

from ulid import ULID


def generate_id() -> str:
    """Generate a new ULID as a 26-character string.

    Returns:
        A new ULID string, e.g. '01HQJY7Z4K0G5P3VXJK5MZQN9T'.
    """
    return str(ULID())
