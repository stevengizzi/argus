"""One-shot migration: mark reconstructed trades with unrecoverable entry prices.

DEF-159: Trades logged with entry_price=0.0 from the reconstruction path
(strategy_id="reconstructed") have bogus P&L because the original entry
price was unrecoverable. This script marks them as entry_price_known=0
so analytics consumers exclude them from P&L/win-rate calculations.

Target: 10 rows from the 2026-04-20 incident (09:26–15:46 ET window).

Usage:
    python scripts/migrate_def159_bogus_trades.py [--dry-run]
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path("data/argus.db")


def main() -> None:
    """Mark bogus reconstruction trades with entry_price_known=0."""
    parser = argparse.ArgumentParser(description="DEF-159 migration")
    parser.add_argument("--dry-run", action="store_true", help="Show affected rows without updating")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Precise query: entry_price=0.0 AND strategy_id="reconstructed"
    # This targets only reconstruction trades where entry was unrecoverable.
    # Normal trades never have entry_price=0.0 (validated by Risk Manager).
    query = """
        SELECT id, symbol, entry_price, exit_price, net_pnl, outcome, exit_reason, exit_time
        FROM trades
        WHERE entry_price = 0.0
          AND strategy_id = 'reconstructed'
    """
    rows = conn.execute(query).fetchall()

    print(f"Found {len(rows)} trades with unrecoverable entry price:")
    for row in rows:
        print(
            f"  {row['id'][:12]} | {row['symbol']:6s} | "
            f"entry={row['entry_price']:.2f} -> exit={row['exit_price']:.2f} | "
            f"net_pnl=${row['net_pnl']:.2f} | {row['outcome']} | {row['exit_reason']}"
        )

    if args.dry_run:
        print("\n--dry-run: No changes made.")
        conn.close()
        return

    # Ensure the column exists (in case migration hasn't run yet)
    try:
        conn.execute("ALTER TABLE trades ADD COLUMN entry_price_known INTEGER NOT NULL DEFAULT 1")
        conn.commit()
        print("\nAdded entry_price_known column.")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Update the affected rows
    update_sql = """
        UPDATE trades
        SET entry_price_known = 0
        WHERE entry_price = 0.0
          AND strategy_id = 'reconstructed'
    """
    cursor = conn.execute(update_sql)
    conn.commit()

    print(f"\nUpdated {cursor.rowcount} rows: entry_price_known = 0")

    # Verify
    verify = conn.execute(
        "SELECT COUNT(*) FROM trades WHERE entry_price_known = 0"
    ).fetchone()
    print(f"Verification: {verify[0]} rows now marked as entry_price_known=0")

    conn.close()


if __name__ == "__main__":
    main()
