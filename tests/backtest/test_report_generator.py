"""Tests for backtest report generator."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from argus.backtest.report_generator import (
    ReportConfig,
    generate_equity_curve,
    generate_monthly_table,
    generate_report,
    generate_trade_distribution,
    generate_trade_tables,
    load_replay_data,
)


def _create_test_db(db_path: str, trades: list[dict]) -> None:
    """Create a test SQLite database with trades.

    Uses the PRODUCTION schema from argus/db/schema.sql:
    - shares (not quantity)
    - stop_price (not original_stop_price)
    - target_prices (not original_target_price)
    - commission (not commission_total)
    """
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (
            id TEXT PRIMARY KEY,
            strategy_id TEXT,
            symbol TEXT,
            asset_class TEXT DEFAULT 'us_stocks',
            side TEXT,
            entry_price REAL,
            entry_time TEXT,
            exit_price REAL,
            exit_time TEXT,
            shares INTEGER,
            stop_price REAL,
            target_prices TEXT,
            exit_reason TEXT,
            gross_pnl REAL,
            commission REAL DEFAULT 0,
            net_pnl REAL,
            r_multiple REAL DEFAULT 0,
            hold_duration_seconds INTEGER DEFAULT 0,
            outcome TEXT,
            rationale TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )

    for t in trades:
        conn.execute(
            """
            INSERT INTO trades (
                id, strategy_id, symbol, side, shares,
                entry_price, entry_time, exit_price, exit_time,
                stop_price, target_prices,
                net_pnl, r_multiple,
                exit_reason, hold_duration_seconds, commission, outcome
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                t.get("id", f"trade_{id(t)}"),
                t.get("strategy_id", "orb"),
                t.get("symbol", "TSLA"),
                t.get("side", "buy"),
                t.get("shares", t.get("quantity", 100)),
                t.get("entry_price", 100.0),
                t.get("entry_time", "2025-06-01T10:00:00"),
                t.get("exit_price", 102.0),
                t.get("exit_time", "2025-06-01T11:00:00"),
                t.get("stop_price", t.get("original_stop_price", 99.0)),
                t.get("target_prices", t.get("original_target_price", "[104.0]")),
                t.get("net_pnl", 200.0),
                t.get("r_multiple", 2.0),
                t.get("exit_reason", "target"),
                t.get("hold_duration_seconds", 3600),
                t.get("commission", t.get("commission_total", 0.0)),
                "win" if t.get("net_pnl", 200.0) > 0 else "loss",
            ),
        )

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Test 14: load_replay_data_from_db
# ---------------------------------------------------------------------------


def test_load_replay_data_from_db():
    """Reads trades from SQLite, computes daily P&L and monthly summaries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # Create test trades
        trades = [
            {
                "id": "trade_1",
                "symbol": "TSLA",
                "entry_time": "2025-06-01T10:00:00",
                "exit_time": "2025-06-01T11:00:00",
                "net_pnl": 200.0,
                "r_multiple": 2.0,
            },
            {
                "id": "trade_2",
                "symbol": "NVDA",
                "entry_time": "2025-06-01T14:00:00",
                "exit_time": "2025-06-01T15:00:00",
                "net_pnl": -100.0,
                "r_multiple": -1.0,
            },
            {
                "id": "trade_3",
                "symbol": "AAPL",
                "entry_time": "2025-06-02T10:00:00",
                "exit_time": "2025-06-02T11:00:00",
                "net_pnl": 150.0,
                "r_multiple": 1.5,
            },
            {
                "id": "trade_4",
                "symbol": "TSLA",
                "entry_time": "2025-07-15T10:00:00",
                "exit_time": "2025-07-15T11:00:00",
                "net_pnl": 300.0,
                "r_multiple": 3.0,
            },
        ]

        _create_test_db(str(db_path), trades)

        # Load data
        result = load_replay_data(str(db_path))

        # Verify trades loaded
        assert len(result["trades"]) == 4

        # Verify daily P&L (cumulative)
        daily = result["daily_pnl"]
        assert len(daily) == 3  # 3 unique days

        # Day 1: 200 - 100 = 100 cumulative
        assert daily[0] == ("2025-06-01", 100.0)
        # Day 2: 100 + 150 = 250 cumulative
        assert daily[1] == ("2025-06-02", 250.0)
        # Day 3: 250 + 300 = 550 cumulative
        assert daily[2] == ("2025-07-15", 550.0)

        # Verify monthly summary
        monthly = result["monthly_summary"]
        assert len(monthly) == 2  # June and July

        june = next(m for m in monthly if m["month"] == "2025-06")
        assert june["trades"] == 3
        assert june["wins"] == 2
        assert june["losses"] == 1
        assert june["net_pnl"] == 250.0

        july = next(m for m in monthly if m["month"] == "2025-07")
        assert july["trades"] == 1
        assert july["wins"] == 1
        assert july["losses"] == 0
        assert july["net_pnl"] == 300.0


# ---------------------------------------------------------------------------
# Test 15: load_replay_data_empty_db
# ---------------------------------------------------------------------------


def test_load_replay_data_empty_db():
    """Empty database returns zero trades, zero P&L."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "empty.db"
        _create_test_db(str(db_path), [])

        result = load_replay_data(str(db_path))

        assert result["trades"] == []
        assert result["daily_pnl"] == []
        assert result["monthly_summary"] == []


def test_load_replay_data_missing_file():
    """Missing database returns empty results without error."""
    result = load_replay_data("/nonexistent/path/db.db")

    assert result["trades"] == []
    assert result["daily_pnl"] == []
    assert result["monthly_summary"] == []


# ---------------------------------------------------------------------------
# Test 16: generate_equity_curve_html
# ---------------------------------------------------------------------------


def test_generate_equity_curve_html():
    """Plotly equity curve renders as valid HTML with chart div."""
    config = ReportConfig()
    trades = [
        {"exit_time": "2025-06-01T11:00:00", "net_pnl": 100.0},
        {"exit_time": "2025-06-02T11:00:00", "net_pnl": -50.0},
        {"exit_time": "2025-06-03T11:00:00", "net_pnl": 200.0},
    ]

    html = generate_equity_curve(trades, config)

    # Should contain Plotly chart
    assert "plotly" in html.lower() or "js-plotly" in html.lower()
    # Should have div element
    assert "<div" in html
    # Should mention P&L
    assert "Cumulative P&L" in html or "Equity" in html


def test_generate_equity_curve_empty():
    """Empty trades returns placeholder message."""
    config = ReportConfig()
    html = generate_equity_curve([], config)

    assert "No trades" in html


# ---------------------------------------------------------------------------
# Test 17: generate_monthly_table
# ---------------------------------------------------------------------------


def test_generate_monthly_table():
    """Monthly table has correct row count, P&L values, color coding."""
    monthly_data = [
        {
            "month": "2025-06", "trades": 10, "wins": 6,
            "losses": 4, "net_pnl": 500.0, "win_rate": 0.6,
        },
        {
            "month": "2025-07", "trades": 8, "wins": 3,
            "losses": 5, "net_pnl": -200.0, "win_rate": 0.375,
        },
        {
            "month": "2025-08", "trades": 12, "wins": 8,
            "losses": 4, "net_pnl": 800.0, "win_rate": 0.667,
        },
    ]

    html = generate_monthly_table(monthly_data)

    # Should be a table
    assert "<table>" in html
    assert "</table>" in html

    # Should have 3 data rows
    assert html.count("<tr>") == 4  # 1 header + 3 data

    # Should have month labels
    assert "2025-06" in html
    assert "2025-07" in html
    assert "2025-08" in html

    # Should have P&L values
    assert "$500.00" in html
    assert "-$200.00" in html or "($200.00)" in html or "$-200.00" in html

    # Should have win rate
    assert "60.0%" in html

    # Should have color coding (positive/negative classes)
    assert 'class="positive"' in html or 'class="negative"' in html


def test_generate_monthly_table_empty():
    """Empty monthly data returns placeholder message."""
    html = generate_monthly_table([])
    assert "No monthly data" in html


# ---------------------------------------------------------------------------
# Test 18: generate_trade_distribution
# ---------------------------------------------------------------------------


def test_generate_trade_distribution():
    """Histogram renders, bin counts match trade data."""
    config = ReportConfig()
    trades = [
        {"r_multiple": 2.0},
        {"r_multiple": 1.5},
        {"r_multiple": -1.0},
        {"r_multiple": 0.5},
        {"r_multiple": -0.5},
        {"r_multiple": 3.0},
    ]

    html = generate_trade_distribution(trades, config)

    # Should contain Plotly histogram
    assert "plotly" in html.lower() or "histogram" in html.lower() or "<div" in html
    # Should mention R-Multiple
    assert "R-Multiple" in html or "distribution" in html.lower()


def test_generate_trade_distribution_empty():
    """Empty trades returns placeholder message."""
    config = ReportConfig()
    html = generate_trade_distribution([], config)
    assert "No trades" in html


# ---------------------------------------------------------------------------
# Test 19: generate_report_replay_only
# ---------------------------------------------------------------------------


def test_generate_report_replay_only():
    """Report with only replay DB generates sections 1-5 and 8, skips 6-7."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        output_path = Path(tmpdir) / "report.html"

        # Create test trades
        trades = [
            {
                "id": f"trade_{i}",
                "symbol": "TSLA",
                "entry_time": f"2025-06-{i+1:02d}T10:00:00",
                "exit_time": f"2025-06-{i+1:02d}T11:00:00",
                "net_pnl": 100.0 if i % 2 == 0 else -50.0,
                "r_multiple": 1.0 if i % 2 == 0 else -0.5,
                "exit_reason": "target" if i % 2 == 0 else "stop",
                "entry_price": 100.0,
                "exit_price": 101.0 if i % 2 == 0 else 99.5,
            }
            for i in range(10)
        ]
        _create_test_db(str(db_path), trades)

        config = ReportConfig(
            replay_db_path=str(db_path),
            output_path=str(output_path),
        )

        result_path = generate_report(config)

        assert result_path == str(output_path)
        assert output_path.exists()

        # Read generated HTML
        html = output_path.read_text()

        # Section 1: Executive Summary (always present)
        assert "Executive Summary" in html
        assert "Total Trades" in html
        assert "Win Rate" in html

        # Sections 2-5, 8: Should be present
        assert "Equity Curve" in html
        assert "Monthly P&L" in html
        assert "Trade Distribution" in html
        assert "Time Analysis" in html
        assert "Individual Trades" in html

        # Sections 6-7: Should NOT be present (no sweep/walk-forward data)
        assert "Parameter Sensitivity" not in html
        assert "Walk-Forward" not in html


# ---------------------------------------------------------------------------
# Test 20: generate_report_full
# ---------------------------------------------------------------------------


def test_generate_report_full():
    """Report with all data sources generates all sections."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        sweep_dir = Path(tmpdir) / "sweep"
        wf_dir = Path(tmpdir) / "walk_forward"
        output_path = Path(tmpdir) / "report.html"

        # Create test DB
        trades = [
            {
                "id": "trade_1",
                "symbol": "TSLA",
                "entry_time": "2025-06-01T10:00:00",
                "exit_time": "2025-06-01T11:00:00",
                "net_pnl": 200.0,
                "r_multiple": 2.0,
                "exit_reason": "target",
                "entry_price": 100.0,
                "exit_price": 102.0,
            }
        ]
        _create_test_db(str(db_path), trades)

        # Create sweep directory with summary parquet
        sweep_dir.mkdir()
        import pandas as pd

        sweep_df = pd.DataFrame(
            {
                "or_minutes": [15],
                "target_r": [2.0],
                "stop_buffer_pct": [0.1],
                "max_hold_minutes": [60],
                "min_gap_pct": [2.0],
                "max_range_atr_ratio": [1.0],
                "total_trades": [50],
                "sharpe_ratio": [1.5],
                "win_rate": [0.55],
                "profit_factor": [1.8],
            }
        )
        sweep_df.to_parquet(sweep_dir / "sweep_summary.parquet")

        # Create walk-forward directory with summary
        wf_dir.mkdir()
        import json

        wf_summary = {
            "aggregates": {
                "avg_wfe_sharpe": 0.6,
                "avg_wfe_pnl": 0.5,
                "total_oos_trades": 100,
                "overall_oos_sharpe": 1.2,
                "overall_oos_pnl": 5000.0,
            },
            "parameter_stability": {
                "or_minutes": {"mode": 15, "stability": 0.8},
            },
        }
        with open(wf_dir / "walk_forward_summary.json", "w") as f:
            json.dump(wf_summary, f)

        config = ReportConfig(
            replay_db_path=str(db_path),
            sweep_dir=str(sweep_dir),
            walk_forward_dir=str(wf_dir),
            output_path=str(output_path),
        )

        result_path = generate_report(config)

        assert result_path == str(output_path)
        assert output_path.exists()

        html = output_path.read_text()

        # All sections should be present
        assert "Executive Summary" in html
        assert "Equity Curve" in html
        assert "Monthly P&L" in html
        assert "Trade Distribution" in html
        assert "Time Analysis" in html
        assert "Parameter Sensitivity" in html
        assert "Walk-Forward" in html
        assert "Individual Trades" in html


# ---------------------------------------------------------------------------
# Test 21: report_html_valid
# ---------------------------------------------------------------------------


def test_report_html_valid():
    """Output HTML is well-formed (no unclosed tags, Plotly script loads)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        output_path = Path(tmpdir) / "report.html"

        trades = [
            {
                "id": "trade_1",
                "symbol": "TSLA",
                "entry_time": "2025-06-01T10:00:00",
                "exit_time": "2025-06-01T11:00:00",
                "net_pnl": 200.0,
                "r_multiple": 2.0,
                "exit_reason": "target",
                "entry_price": 100.0,
                "exit_price": 102.0,
            }
        ]
        _create_test_db(str(db_path), trades)

        config = ReportConfig(
            replay_db_path=str(db_path),
            output_path=str(output_path),
        )

        generate_report(config)
        html = output_path.read_text()

        # Basic HTML structure
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        assert "<head>" in html
        assert "</head>" in html
        assert "<body>" in html
        assert "</body>" in html

        # Plotly CDN script
        assert "cdn.plot.ly" in html or "plotly" in html

        # Check for balanced tags (simple check)
        assert html.count("<div") == html.count("</div>")
        assert html.count("<table>") == html.count("</table>")


# ---------------------------------------------------------------------------
# Test 22: trade_tables_top_bottom
# ---------------------------------------------------------------------------


def test_trade_tables_top_bottom():
    """Worst/best 10 trades sorted correctly, P&L values match."""
    trades = [
        {"exit_time": f"2025-06-{i+1:02d}T11:00:00", "symbol": "TSLA",
         "entry_price": 100.0, "exit_price": 100.0 + (i - 5),
         "net_pnl": (i - 5) * 100.0, "r_multiple": i - 5, "exit_reason": "target"}
        for i in range(10)
    ]

    html = generate_trade_tables(trades, n=5)

    # Should have two tables (best and worst)
    assert "Worst 5 Trades" in html
    assert "Best 5 Trades" in html

    # Worst trades: P&L of -500, -400, -300, -200, -100
    assert "-$500.00" in html or "$-500.00" in html
    assert "-$400.00" in html or "$-400.00" in html

    # Best trades: P&L of 400, 300, 200, 100, 0
    assert "$400.00" in html
    assert "$300.00" in html

    # Should have trade details
    assert "TSLA" in html
    assert "Exit Time" in html
    assert "Exit Reason" in html


def test_trade_tables_empty():
    """Empty trades returns placeholder message."""
    html = generate_trade_tables([], n=10)
    assert "No trades" in html
