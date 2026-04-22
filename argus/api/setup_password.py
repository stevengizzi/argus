"""CLI tool for generating password hash for Command Center authentication.

Prompts for a password, confirms it, and outputs the bcrypt hash to add
to config/system.yaml.

Usage:
    python -m argus.api.setup_password
"""

from __future__ import annotations

import getpass
import os
import secrets
import string
import sys
from pathlib import Path

from argus.api.auth import hash_password

MIN_PASSWORD_LENGTH = 8


def generate_jwt_secret(length: int = 64) -> str:
    """Generate a cryptographically secure JWT secret.

    Args:
        length: Length of the secret string. Default 64.

    Returns:
        Random alphanumeric string suitable for JWT signing.
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def main() -> int:
    """Main entry point for the setup_password CLI.

    Returns:
        Exit code: 0 for success, 1 for error.
    """
    print("=" * 60)
    print("Argus Command Center — Password Setup")
    print("=" * 60)
    print()

    # Get password with confirmation
    try:
        password = getpass.getpass("Enter password: ")
        if len(password) < MIN_PASSWORD_LENGTH:
            print(
                f"\nError: Password must be at least {MIN_PASSWORD_LENGTH} characters.",
                file=sys.stderr,
            )
            return 1

        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("\nError: Passwords do not match.", file=sys.stderr)
            return 1
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        return 1

    # Generate hash
    password_hash = hash_password(password)

    # Generate a suggested JWT secret and write it to .env.example with
    # owner-only permissions (0600). Printing the secret to stdout would
    # leak it via shell history, screen-sharing, or terminal multiplexer
    # logs — so we write it to a file and tell the operator where to find it.
    jwt_secret = generate_jwt_secret()
    env_example_path = Path.cwd() / ".env.example"
    try:
        # Write file then chmod 0600 (owner read/write only)
        env_example_path.write_text(
            f'ARGUS_JWT_SECRET="{jwt_secret}"\n',
            encoding="utf-8",
        )
        os.chmod(env_example_path, 0o600)
        jwt_secret_written = True
    except OSError as exc:
        print(
            f"\nWarning: Could not write {env_example_path}: {exc}",
            file=sys.stderr,
        )
        jwt_secret_written = False

    print()
    print("=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print()
    print("1. Add this password_hash to config/system.yaml:")
    print()
    print("   api:")
    print(f'     password_hash: "{password_hash}"')
    print()
    print("-" * 60)
    print()
    if jwt_secret_written:
        print(f"2. A JWT secret was written to: {env_example_path}")
        print("   (permissions: 0600 — owner read/write only).")
        print()
        print("   Copy this line into your .env file or shell profile:")
        print()
        print(f"     cat {env_example_path}")
        print()
        print("   Then delete .env.example (or keep it as a template")
        print("   with the secret rotated out).")
    else:
        print("2. Could not write .env.example.")
        print("   Generate a JWT secret manually (recommended):")
        print()
        print("     python -c 'import secrets, string; "
              "print(\"\".join(secrets.choice(string.ascii_letters + string.digits) "
              "for _ in range(64)))'")
        print()
        print("   Store the output as ARGUS_JWT_SECRET in your .env file.")
    print()
    print("-" * 60)
    print()
    print("Important:")
    print("  - Keep the JWT secret secure — anyone with it can forge tokens")
    print("  - The password_hash can be stored in version control")
    print("  - The JWT secret should NOT be in version control")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
