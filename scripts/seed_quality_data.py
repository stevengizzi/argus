#!/usr/bin/env python3
"""Seed quality_history table with synthetic data for visual verification.

Dev-only tool. NOT production code.

Usage:
    python scripts/seed_quality_data.py [--db path/to/argus.db]
    python scripts/seed_quality_data.py --cleanup [--db path/to/argus.db]

If --db is omitted, defaults to data/argus.db.
"""

import argparse
import json
import random
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SEED_MARKER = "seed_marker_visual_qa"

STRATEGIES = ["orb_breakout", "vwap_reclaim", "afternoon_momentum"]
SYMBOLS = ["AAPL", "TSLA", "NVDA", "META", "MSFT", "GOOG", "AMD", "AMZN", "NFLX", "CRM"]

# Grade distribution weighted toward B range
GRADE_WEIGHTS = {
    "A+": 1, "A": 2, "A-": 3,
    "B+": 5, "B": 6, "B-": 4,
    "C+": 3, "C": 1,
}

GRADE_SCORE_RANGES = {
    "A+": (88, 95), "A": (80, 88), "A-": (73, 80),
    "B+": (65, 73), "B": (55, 65), "B-": (45, 55),
    "C+": (35, 45), "C": (15, 35),
}


def weighted_grade_pick() -> str:
    """Pick a grade weighted toward B range."""
    grades = list(GRADE_WEIGHTS.keys())
    weights = list(GRADE_WEIGHTS.values())
    return random.choices(grades, weights=weights, k=1)[0]


def generate_rows(count: int = 28) -> list[tuple]:
    """Generate synthetic quality_history rows."""
    et = ZoneInfo("America/New_York")
    now = datetime.now(et)
    base_time = now.replace(hour=9, minute=30, second=0, microsecond=0)

    rows = []
    for i in range(count):
        grade = weighted_grade_pick()
        lo, hi = GRADE_SCORE_RANGES[grade]
        composite_score = round(random.uniform(lo, hi), 1)

        pattern_strength = round(random.uniform(20, 95), 1)
        catalyst_quality = round(random.uniform(15, 85), 1)
        volume_profile = round(random.uniform(20, 90), 1)
        historical_match = round(random.uniform(30, 80), 1)
        regime_alignment = round(random.uniform(25, 90), 1)

        symbol = random.choice(SYMBOLS)
        strategy = random.choice(STRATEGIES)
        scored_at = (base_time + timedelta(minutes=random.randint(0, 360))).isoformat()

        entry_price = round(random.uniform(100, 800), 2)
        stop_price = round(entry_price * random.uniform(0.97, 0.995), 2)
        calculated_shares = random.randint(10, 200)

        context = json.dumps({"seed": SEED_MARKER, "idx": i})

        # ~60% have outcome data
        has_outcome = random.random() < 0.6
        if has_outcome:
            # Mix of winners and losers (55% winners)
            is_winner = random.random() < 0.55
            if is_winner:
                outcome_pnl = round(random.uniform(15, 500), 2)
                risk_per_share = entry_price - stop_price
                outcome_r = round(
                    outcome_pnl / (risk_per_share * calculated_shares) if risk_per_share > 0 else 0,
                    2,
                )
            else:
                outcome_pnl = round(random.uniform(-400, -10), 2)
                risk_per_share = entry_price - stop_price
                outcome_r = round(
                    outcome_pnl / (risk_per_share * calculated_shares) if risk_per_share > 0 else 0,
                    2,
                )
            outcome_trade_id = f"seed_trade_{i:03d}"
        else:
            outcome_pnl = None
            outcome_r = None
            outcome_trade_id = None

        row_id = f"seed_{i:03d}"

        rows.append((
            row_id, symbol, strategy, scored_at,
            pattern_strength, catalyst_quality, volume_profile,
            historical_match, regime_alignment,
            composite_score, grade, grade,  # risk_tier = grade
            entry_price, stop_price, calculated_shares,
            context,
            outcome_trade_id, outcome_pnl, outcome_r,
        ))

    return rows


def seed(db_path: str) -> None:
    """Insert seed rows into quality_history."""
    conn = sqlite3.connect(db_path)
    rows = generate_rows()

    conn.executemany(
        """
        INSERT OR REPLACE INTO quality_history (
            id, symbol, strategy_id, scored_at,
            pattern_strength, catalyst_quality, volume_profile,
            historical_match, regime_alignment,
            composite_score, grade, risk_tier,
            entry_price, stop_price, calculated_shares,
            signal_context,
            outcome_trade_id, outcome_realized_pnl, outcome_r_multiple
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()

    count = conn.execute(
        "SELECT COUNT(*) FROM quality_history WHERE signal_context LIKE ?",
        (f"%{SEED_MARKER}%",),
    ).fetchone()[0]

    conn.close()
    print(f"Seeded {count} quality_history rows into {db_path}")


def cleanup(db_path: str) -> None:
    """Remove all seeded rows."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "DELETE FROM quality_history WHERE signal_context LIKE ?",
        (f"%{SEED_MARKER}%",),
    )
    conn.commit()
    print(f"Removed {cursor.rowcount} seeded rows from {db_path}")
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed quality_history for visual QA")
    parser.add_argument("--cleanup", action="store_true", help="Remove seeded rows")
    parser.add_argument("--db", default="data/argus.db", help="Path to SQLite DB")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Database not found: {db_path}", file=sys.stderr)
        print("Start the dev server first: python -m argus.api --dev", file=sys.stderr)
        sys.exit(1)

    if args.cleanup:
        cleanup(str(db_path))
    else:
        seed(str(db_path))


if __name__ == "__main__":
    main()
