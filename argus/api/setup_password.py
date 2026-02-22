"""CLI tool for generating password hash for Command Center authentication.

Prompts for a password, confirms it, and outputs the bcrypt hash to add
to config/system.yaml.

Usage:
    python -m argus.api.setup_password
"""

from __future__ import annotations

import getpass
import secrets
import string
import sys

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

    # Generate a suggested JWT secret
    jwt_secret = generate_jwt_secret()

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
    print("2. Set the JWT secret as an environment variable.")
    print("   Add this to your .env file or shell profile:")
    print()
    print(f'   export ARGUS_JWT_SECRET="{jwt_secret}"')
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
