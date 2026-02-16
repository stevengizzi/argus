"""Backtest Report Generator.

Generates self-contained HTML reports for backtest analysis. Aggregates data
from Replay Harness runs (SQLite databases), VectorBT sweep results (Parquet
files), and walk-forward analysis results (JSON/CSV files).

Usage:
    # From Replay Harness DB only
    python -m argus.backtest.report_generator \
        --db data/backtest_runs/orb_20250601_20251231.db \
        --output reports/orb_baseline.html

    # Full report with all data sources
    python -m argus.backtest.report_generator \
        --db data/backtest_runs/orb_20250601_20251231.db \
        --sweep-dir data/backtest_runs/sweeps \
        --walk-forward-dir data/backtest_runs/walk_forward \
        --output reports/orb_full_validation.html
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ReportConfig:
    """Configuration for report generation."""

    # Required: at least one of these must be provided
    replay_db_path: str | None = None  # Path to Replay Harness SQLite DB
    sweep_dir: str | None = None  # Path to VectorBT sweep output directory
    walk_forward_dir: str | None = None  # Path to walk-forward results directory

    # Report metadata
    strategy_name: str = "ORB Breakout"
    report_title: str | None = None  # Auto-generated if None

    # Output
    output_path: str = "reports/orb_validation.html"

    # Chart settings
    chart_library: str = "plotly"  # "plotly" or "matplotlib"
    embed_charts: bool = True  # Embed as base64 in HTML (vs separate files)
    chart_height: int = 400
    chart_width: int = 900


# ---------------------------------------------------------------------------
# Data Loading Functions
# ---------------------------------------------------------------------------


def load_replay_data(db_path: str) -> dict[str, Any]:
    """Load trade data from Replay Harness SQLite database.

    Reads from the trades table (same schema as production).

    Args:
        db_path: Path to the SQLite database.

    Returns:
        Dict with:
        - trades: list of trade dicts
        - daily_pnl: list of (date_str, cumulative_pnl) tuples
        - monthly_summary: list of monthly aggregates
    """
    if not Path(db_path).exists():
        logger.warning("Database file not found: %s", db_path)
        return {"trades": [], "daily_pnl": [], "monthly_summary": []}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        # Load trades
        cursor = conn.execute(
            """
            SELECT
                id, strategy_id, symbol, side, quantity,
                entry_price, entry_time, exit_price, exit_time,
                original_stop_price, original_target_price,
                initial_risk_per_share, net_pnl, r_multiple,
                exit_reason, hold_duration_seconds, commission_total
            FROM trades
            ORDER BY exit_time
            """
        )
        trades = [dict(row) for row in cursor.fetchall()]

        if not trades:
            return {"trades": [], "daily_pnl": [], "monthly_summary": []}

        # Build daily P&L
        daily_pnl: dict[str, float] = {}
        for trade in trades:
            exit_date = trade["exit_time"][:10] if trade["exit_time"] else None
            if exit_date:
                daily_pnl[exit_date] = daily_pnl.get(exit_date, 0.0) + trade["net_pnl"]

        # Compute cumulative
        cumulative = 0.0
        daily_cumulative: list[tuple[str, float]] = []
        for date_str in sorted(daily_pnl.keys()):
            cumulative += daily_pnl[date_str]
            daily_cumulative.append((date_str, cumulative))

        # Build monthly summary
        monthly_summary = _compute_monthly_summary(trades)

        return {
            "trades": trades,
            "daily_pnl": daily_cumulative,
            "monthly_summary": monthly_summary,
        }

    finally:
        conn.close()


def _compute_monthly_summary(trades: list[dict]) -> list[dict]:
    """Compute monthly P&L summary from trades."""
    monthly: dict[str, dict[str, Any]] = {}

    for trade in trades:
        exit_time = trade.get("exit_time", "")
        if not exit_time:
            continue

        month_key = exit_time[:7]  # "YYYY-MM"
        if month_key not in monthly:
            monthly[month_key] = {
                "month": month_key,
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "net_pnl": 0.0,
                "win_rate": 0.0,
            }

        monthly[month_key]["trades"] += 1
        monthly[month_key]["net_pnl"] += trade["net_pnl"]

        if trade["net_pnl"] > 0.50:
            monthly[month_key]["wins"] += 1
        elif trade["net_pnl"] < -0.50:
            monthly[month_key]["losses"] += 1

    # Compute win rates
    for data in monthly.values():
        if data["trades"] > 0:
            data["win_rate"] = data["wins"] / data["trades"]

    return sorted(monthly.values(), key=lambda x: x["month"])


def load_sweep_data(sweep_dir: str) -> dict[str, Any]:
    """Load VectorBT sweep results from Parquet files.

    Args:
        sweep_dir: Directory containing sweep output files.

    Returns:
        Dict with:
        - summary_df: cross-symbol aggregated DataFrame (or None)
        - heatmap_paths: list of paths to existing heatmap HTML files
    """
    sweep_path = Path(sweep_dir)
    if not sweep_path.exists():
        logger.warning("Sweep directory not found: %s", sweep_dir)
        return {"summary_df": None, "heatmap_paths": []}

    # Load summary parquet
    summary_path = sweep_path / "sweep_summary.parquet"
    summary_df = None
    if summary_path.exists():
        summary_df = pd.read_parquet(summary_path)

    # Find heatmap HTML files
    interactive_dir = sweep_path / "interactive"
    heatmap_paths: list[str] = []
    if interactive_dir.exists():
        heatmap_paths = [str(p) for p in interactive_dir.glob("*.html")]

    return {
        "summary_df": summary_df,
        "heatmap_paths": sorted(heatmap_paths),
    }


def load_walk_forward_data(wf_dir: str) -> dict[str, Any] | None:
    """Load walk-forward results from JSON/CSV files.

    Args:
        wf_dir: Directory containing walk-forward output.

    Returns:
        Dict with summary data or None if files don't exist.
    """
    wf_path = Path(wf_dir)
    summary_path = wf_path / "walk_forward_summary.json"

    if not summary_path.exists():
        logger.warning("Walk-forward summary not found: %s", summary_path)
        return None

    with open(summary_path) as f:
        summary = json.load(f)

    # Load windows CSV for detailed data
    windows_path = wf_path / "walk_forward_windows.csv"
    windows_df = None
    if windows_path.exists():
        windows_df = pd.read_csv(windows_path)

    return {
        "summary": summary,
        "windows_df": windows_df,
    }


# ---------------------------------------------------------------------------
# Chart Generation Functions
# ---------------------------------------------------------------------------


def generate_equity_curve(trades: list[dict], config: ReportConfig) -> str:
    """Generate equity curve chart.

    Args:
        trades: List of trade dicts with net_pnl and exit_time.
        config: ReportConfig for chart settings.

    Returns:
        HTML string (embedded Plotly chart).
    """
    if not trades:
        return "<p>No trades to display equity curve.</p>"

    import plotly.graph_objects as go

    # Build cumulative equity
    dates: list[str] = []
    equity: list[float] = [0.0]  # Start at 0 (showing cumulative P&L)

    for trade in trades:
        exit_time = trade.get("exit_time", "")
        if exit_time:
            dates.append(exit_time[:10])
            equity.append(equity[-1] + trade["net_pnl"])

    # Remove initial 0
    dates.insert(0, "Start")

    # Compute drawdown
    peak = 0.0
    drawdown: list[float] = []
    for eq in equity:
        if eq > peak:
            peak = eq
        dd = (peak - eq) if peak > 0 else 0.0
        drawdown.append(-dd)  # Negative for display below zero line

    fig = go.Figure()

    # Equity curve
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=equity,
            mode="lines",
            name="Cumulative P&L",
            line={"color": "#16a34a", "width": 2},
            hovertemplate="Date: %{x}<br>P&L: $%{y:,.2f}<extra></extra>",
        )
    )

    # Drawdown
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=drawdown,
            mode="lines",
            name="Drawdown",
            line={"color": "#dc2626", "width": 1},
            fill="tozeroy",
            fillcolor="rgba(220, 38, 38, 0.1)",
            hovertemplate="Date: %{x}<br>Drawdown: $%{y:,.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        title="Equity Curve",
        xaxis_title="Date",
        yaxis_title="Cumulative P&L ($)",
        height=config.chart_height,
        hovermode="x unified",
        legend={"yanchor": "top", "y": 0.99, "xanchor": "left", "x": 0.01},
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def generate_monthly_table(monthly_data: list[dict]) -> str:
    """Generate HTML table of monthly P&L breakdown.

    Args:
        monthly_data: List of monthly summary dicts.

    Returns:
        HTML table string.
    """
    if not monthly_data:
        return "<p>No monthly data available.</p>"

    rows = []
    for month in monthly_data:
        pnl = month["net_pnl"]
        color = "positive" if pnl >= 0 else "negative"
        win_rate_pct = month["win_rate"] * 100

        rows.append(
            f"""
            <tr>
                <td style="text-align: left;">{month["month"]}</td>
                <td>{month["trades"]}</td>
                <td>{month["wins"]}</td>
                <td>{month["losses"]}</td>
                <td class="{color}">${pnl:,.2f}</td>
                <td>{win_rate_pct:.1f}%</td>
            </tr>
            """
        )

    return f"""
    <table>
        <thead>
            <tr>
                <th style="text-align: left;">Month</th>
                <th>Trades</th>
                <th>Wins</th>
                <th>Losses</th>
                <th>Net P&L</th>
                <th>Win Rate</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows)}
        </tbody>
    </table>
    """


def generate_monthly_chart(monthly_data: list[dict], config: ReportConfig) -> str:
    """Generate monthly P&L bar chart.

    Args:
        monthly_data: List of monthly summary dicts.
        config: ReportConfig for chart settings.

    Returns:
        HTML string (embedded Plotly chart).
    """
    if not monthly_data:
        return ""

    import plotly.graph_objects as go

    months = [m["month"] for m in monthly_data]
    pnls = [m["net_pnl"] for m in monthly_data]
    colors = ["#16a34a" if p >= 0 else "#dc2626" for p in pnls]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=months,
            y=pnls,
            marker_color=colors,
            hovertemplate="Month: %{x}<br>P&L: $%{y:,.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        title="Monthly P&L",
        xaxis_title="Month",
        yaxis_title="Net P&L ($)",
        height=config.chart_height,
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def generate_trade_distribution(trades: list[dict], config: ReportConfig) -> str:
    """Generate R-multiple histogram chart.

    Args:
        trades: List of trade dicts with r_multiple.
        config: ReportConfig for chart settings.

    Returns:
        HTML string (embedded Plotly chart).
    """
    if not trades:
        return "<p>No trades to display distribution.</p>"

    import plotly.graph_objects as go

    r_multiples = [t["r_multiple"] for t in trades if t.get("r_multiple") is not None]

    if not r_multiples:
        return "<p>No R-multiple data available.</p>"

    # Create histogram
    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=r_multiples,
            nbinsx=30,
            marker_color="#2563eb",
            hovertemplate="R-Multiple: %{x:.2f}<br>Count: %{y}<extra></extra>",
        )
    )

    # Add vertical line at 0
    fig.add_vline(x=0, line_dash="dash", line_color="red")

    fig.update_layout(
        title="Trade Distribution (R-Multiples)",
        xaxis_title="R-Multiple",
        yaxis_title="Count",
        height=config.chart_height,
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def generate_time_analysis(trades: list[dict], config: ReportConfig) -> str:
    """Generate time-of-day and day-of-week analysis charts.

    Args:
        trades: List of trade dicts with exit_time.
        config: ReportConfig for chart settings.

    Returns:
        HTML string with charts.
    """
    if not trades:
        return "<p>No trades to analyze.</p>"

    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    # Analyze by hour
    pnl_by_hour: dict[int, float] = {}
    trades_by_hour: dict[int, int] = {}

    # Analyze by weekday
    pnl_by_weekday: dict[int, float] = {}
    trades_by_weekday: dict[int, int] = {}

    for trade in trades:
        exit_time = trade.get("exit_time", "")
        if not exit_time:
            continue

        try:
            dt = datetime.fromisoformat(exit_time.replace("Z", "+00:00"))
            hour = dt.hour
            weekday = dt.weekday()

            pnl_by_hour[hour] = pnl_by_hour.get(hour, 0.0) + trade["net_pnl"]
            trades_by_hour[hour] = trades_by_hour.get(hour, 0) + 1

            pnl_by_weekday[weekday] = pnl_by_weekday.get(weekday, 0.0) + trade["net_pnl"]
            trades_by_weekday[weekday] = trades_by_weekday.get(weekday, 0) + 1
        except (ValueError, TypeError):
            continue

    # Create subplots
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Average P&L by Hour", "Average P&L by Day of Week"),
    )

    # Hour chart
    hours = sorted(pnl_by_hour.keys())
    hour_avg_pnl = [
        pnl_by_hour[h] / trades_by_hour[h] if trades_by_hour.get(h, 0) > 0 else 0
        for h in hours
    ]
    hour_colors = ["#16a34a" if p >= 0 else "#dc2626" for p in hour_avg_pnl]

    fig.add_trace(
        go.Bar(
            x=[f"{h}:00" for h in hours],
            y=hour_avg_pnl,
            marker_color=hour_colors,
            name="By Hour",
            hovertemplate="Hour: %{x}<br>Avg P&L: $%{y:,.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # Weekday chart
    weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    weekdays = sorted(pnl_by_weekday.keys())
    weekday_avg_pnl = [
        pnl_by_weekday[w] / trades_by_weekday[w] if trades_by_weekday.get(w, 0) > 0 else 0
        for w in weekdays
    ]
    weekday_colors = ["#16a34a" if p >= 0 else "#dc2626" for p in weekday_avg_pnl]

    fig.add_trace(
        go.Bar(
            x=[weekday_names[w] for w in weekdays],
            y=weekday_avg_pnl,
            marker_color=weekday_colors,
            name="By Weekday",
            hovertemplate="Day: %{x}<br>Avg P&L: $%{y:,.2f}<extra></extra>",
        ),
        row=1,
        col=2,
    )

    fig.update_layout(
        height=config.chart_height,
        showlegend=False,
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def generate_parameter_sensitivity(sweep_data: dict, config: ReportConfig) -> str:
    """Generate parameter sensitivity section.

    Embeds links to existing heatmap HTML files and generates summary table.

    Args:
        sweep_data: Dict from load_sweep_data().
        config: ReportConfig for chart settings.

    Returns:
        HTML string for the section.
    """
    summary_df = sweep_data.get("summary_df")
    heatmap_paths = sweep_data.get("heatmap_paths", [])

    html_parts = []

    # Summary table of best parameters
    if summary_df is not None and not summary_df.empty:
        param_cols = [
            "or_minutes",
            "target_r",
            "stop_buffer_pct",
            "max_hold_minutes",
            "min_gap_pct",
            "max_range_atr_ratio",
        ]

        # Find best parameters by Sharpe
        best_idx = summary_df["sharpe_ratio"].idxmax()
        best_row = summary_df.loc[best_idx]

        rows = []
        for col in param_cols:
            if col in best_row:
                rows.append(f"<tr><td>{col}</td><td>{best_row[col]}</td></tr>")

        html_parts.append(
            f"""
            <h4>Best Parameters (by Sharpe)</h4>
            <table>
                <thead><tr><th>Parameter</th><th>Value</th></tr></thead>
                <tbody>{"".join(rows)}</tbody>
            </table>
            <p>Sharpe: {best_row['sharpe_ratio']:.2f}, Trades: {best_row['total_trades']}</p>
            """
        )

    # Heatmap links
    if heatmap_paths:
        links = []
        for path in heatmap_paths[:10]:  # Limit to first 10
            name = Path(path).stem
            links.append(f'<li><a href="file://{path}" target="_blank">{name}</a></li>')

        html_parts.append(
            f"""
            <h4>Parameter Heatmaps</h4>
            <ul>{"".join(links)}</ul>
            <p><small>Open these HTML files in a browser for interactive exploration.</small></p>
            """
        )

    if not html_parts:
        return "<p>No sweep data available.</p>"

    return "".join(html_parts)


def generate_walk_forward_section(wf_data: dict, config: ReportConfig) -> str:
    """Generate walk-forward analysis section.

    Args:
        wf_data: Dict from load_walk_forward_data().
        config: ReportConfig for chart settings.

    Returns:
        HTML string for the section.
    """
    if not wf_data:
        return "<p>No walk-forward data available.</p>"

    import plotly.graph_objects as go

    summary = wf_data.get("summary", {})
    windows_df = wf_data.get("windows_df")

    html_parts = []

    # Summary stats
    aggregates = summary.get("aggregates", {})
    avg_wfe = aggregates.get("avg_wfe_sharpe", 0.0)
    total_trades = aggregates.get("total_oos_trades", 0)
    overall_pnl = aggregates.get("overall_oos_pnl", 0.0)

    # WFE assessment
    if avg_wfe >= 0.5:
        assessment = "GOOD - WFE ≥ 0.5 indicates robust parameters"
        assessment_class = "positive"
    elif avg_wfe >= 0.3:
        assessment = "ACCEPTABLE - WFE ≥ 0.3 meets DEC-047 threshold"
        assessment_class = ""
    else:
        assessment = "POOR - WFE < 0.3 indicates potential overfitting"
        assessment_class = "negative"

    html_parts.append(
        f"""
        <div class="metric-card">
            <strong>Avg WFE (Sharpe)</strong><br>
            <span style="font-size: 1.5em;">{avg_wfe:.2f}</span>
        </div>
        <div class="metric-card">
            <strong>Total OOS Trades</strong><br>
            <span style="font-size: 1.5em;">{total_trades}</span>
        </div>
        <div class="metric-card">
            <strong>Overall OOS P&L</strong><br>
            <span class="{'positive' if overall_pnl >= 0 else 'negative'}"
                  style="font-size: 1.5em;">
                ${overall_pnl:,.2f}
            </span>
        </div>
        <p class="{assessment_class}"><strong>Assessment:</strong> {assessment}</p>
        """
    )

    # Windows table
    if windows_df is not None and not windows_df.empty:
        rows = []
        for _, row in windows_df.iterrows():
            wfe = row.get("wfe_sharpe", 0.0)
            wfe_class = "positive" if wfe >= 0.3 else "negative"
            rows.append(
                f"""
                <tr>
                    <td>{row.get('window_number', '')}</td>
                    <td>{row.get('is_start', '')} to {row.get('is_end', '')}</td>
                    <td>{row.get('oos_start', '')} to {row.get('oos_end', '')}</td>
                    <td>{row.get('is_sharpe', 0.0):.2f}</td>
                    <td>{row.get('oos_sharpe', 0.0):.2f}</td>
                    <td class="{wfe_class}">{wfe:.2f}</td>
                </tr>
                """
            )

        html_parts.append(
            f"""
            <h4>Per-Window Results</h4>
            <table>
                <thead>
                    <tr>
                        <th>Window</th>
                        <th>IS Period</th>
                        <th>OOS Period</th>
                        <th>IS Sharpe</th>
                        <th>OOS Sharpe</th>
                        <th>WFE</th>
                    </tr>
                </thead>
                <tbody>{"".join(rows)}</tbody>
            </table>
            """
        )

        # IS vs OOS chart
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                name="IS Sharpe",
                x=[f"W{i}" for i in windows_df["window_number"]],
                y=windows_df["is_sharpe"],
                marker_color="#2563eb",
            )
        )
        fig.add_trace(
            go.Bar(
                name="OOS Sharpe",
                x=[f"W{i}" for i in windows_df["window_number"]],
                y=windows_df["oos_sharpe"],
                marker_color="#16a34a",
            )
        )
        fig.update_layout(
            title="IS vs OOS Sharpe by Window",
            barmode="group",
            height=config.chart_height,
        )
        html_parts.append(fig.to_html(full_html=False, include_plotlyjs=False))

    # Parameter stability
    stability = summary.get("parameter_stability", {})
    if stability:
        stability_rows = []
        for param, stats in stability.items():
            stability_pct = stats.get("stability", 0.0) * 100
            mode_val = stats.get("mode", "N/A")
            stability_rows.append(
                f"<tr><td>{param}</td><td>{mode_val}</td><td>{stability_pct:.0f}%</td></tr>"
            )

        html_parts.append(
            f"""
            <h4>Parameter Stability</h4>
            <table>
                <thead><tr><th>Parameter</th><th>Mode</th><th>Stability</th></tr></thead>
                <tbody>{"".join(stability_rows)}</tbody>
            </table>
            <p><small>Stability shows what fraction of windows chose the mode value.
            High stability suggests robust parameters.</small></p>
            """
        )

    return "".join(html_parts)


def generate_trade_tables(trades: list[dict], n: int = 10) -> str:
    """Generate best/worst trade tables as HTML.

    Args:
        trades: List of trade dicts.
        n: Number of trades to show in each table.

    Returns:
        HTML string with both tables.
    """
    if not trades:
        return "<p>No trades to display.</p>"

    # Sort by P&L
    sorted_trades = sorted(trades, key=lambda t: t.get("net_pnl", 0.0))

    def make_table(trade_list: list[dict], title: str) -> str:
        rows = []
        for t in trade_list:
            pnl = t.get("net_pnl", 0.0)
            pnl_class = "positive" if pnl >= 0 else "negative"
            r_mult = t.get("r_multiple", 0.0)

            rows.append(
                f"""
                <tr>
                    <td>{t.get('exit_time', '')[:16]}</td>
                    <td>{t.get('symbol', '')}</td>
                    <td>${t.get('entry_price', 0.0):.2f}</td>
                    <td>${t.get('exit_price', 0.0):.2f}</td>
                    <td class="{pnl_class}">${pnl:,.2f}</td>
                    <td class="{pnl_class}">{r_mult:.2f}R</td>
                    <td>{t.get('exit_reason', '')}</td>
                </tr>
                """
            )

        return f"""
        <h4>{title}</h4>
        <table>
            <thead>
                <tr>
                    <th>Exit Time</th>
                    <th>Symbol</th>
                    <th>Entry</th>
                    <th>Exit</th>
                    <th>P&L</th>
                    <th>R</th>
                    <th>Exit Reason</th>
                </tr>
            </thead>
            <tbody>{"".join(rows)}</tbody>
        </table>
        """

    worst = make_table(sorted_trades[:n], f"Worst {n} Trades")
    best = make_table(sorted_trades[-n:][::-1], f"Best {n} Trades")

    return worst + best


# ---------------------------------------------------------------------------
# Report Assembly
# ---------------------------------------------------------------------------


def _compute_summary_metrics(trades: list[dict]) -> dict[str, Any]:
    """Compute key metrics for executive summary."""
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "total_pnl": 0.0,
        }

    total_trades = len(trades)
    winners = [t for t in trades if t.get("net_pnl", 0) > 0.50]
    losers = [t for t in trades if t.get("net_pnl", 0) < -0.50]

    win_rate = len(winners) / total_trades if total_trades > 0 else 0.0

    gross_wins = sum(t.get("net_pnl", 0) for t in winners)
    gross_losses = abs(sum(t.get("net_pnl", 0) for t in losers))
    profit_factor = gross_wins / gross_losses if gross_losses > 0 else float("inf")

    total_pnl = sum(t.get("net_pnl", 0) for t in trades)

    # Compute drawdown from cumulative equity
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in sorted(trades, key=lambda x: x.get("exit_time", "")):
        equity += t.get("net_pnl", 0)
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd

    max_dd_pct = max_dd / peak * 100 if peak > 0 else 0.0

    # Simplified Sharpe (from R-multiples)
    r_multiples = [t.get("r_multiple", 0) for t in trades if t.get("r_multiple") is not None]
    if len(r_multiples) >= 2:
        mean_r = sum(r_multiples) / len(r_multiples)
        variance = sum((r - mean_r) ** 2 for r in r_multiples) / (len(r_multiples) - 1)
        std_r = variance ** 0.5
        sharpe = (mean_r / std_r) * (252 ** 0.5) if std_r > 0 else 0.0
    else:
        sharpe = 0.0

    return {
        "total_trades": total_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor if profit_factor != float("inf") else 999.0,
        "sharpe": sharpe,
        "max_drawdown": max_dd_pct,
        "total_pnl": total_pnl,
    }


def generate_report(config: ReportConfig) -> str:
    """Main entry point. Loads all available data, generates all applicable sections.

    Args:
        config: ReportConfig with data sources and output settings.

    Returns:
        Path to generated HTML file.
    """
    # Load data
    replay_data = None
    sweep_data = None
    wf_data = None

    if config.replay_db_path:
        replay_data = load_replay_data(config.replay_db_path)
    if config.sweep_dir:
        sweep_data = load_sweep_data(config.sweep_dir)
    if config.walk_forward_dir:
        wf_data = load_walk_forward_data(config.walk_forward_dir)

    # Generate report title
    title = config.report_title
    if not title:
        title = f"{config.strategy_name} Backtest Report"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Build sections
    sections = []
    trades = replay_data.get("trades", []) if replay_data else []
    metrics = _compute_summary_metrics(trades)

    # Section 1: Executive Summary (always present)
    assessment = ""
    if metrics["sharpe"] >= 1.0 and metrics["profit_factor"] >= 1.5:
        assessment = "🟢 GOOD: Strategy shows promising risk-adjusted returns"
    elif metrics["sharpe"] >= 0.5 and metrics["profit_factor"] >= 1.0:
        assessment = "🟡 ACCEPTABLE: Strategy shows modest returns, consider optimization"
    elif metrics["total_trades"] > 0:
        assessment = "🔴 POOR: Strategy underperforms, requires significant changes"
    else:
        assessment = "⚪ NO DATA: No trades to analyze"

    pf_str = f"{metrics['profit_factor']:.2f}" if metrics["profit_factor"] < 999 else "∞"

    sections.append(
        f"""
        <div class="section" id="executive-summary">
            <h2>Executive Summary</h2>
            <div class="metric-card">
                <strong>Total Trades</strong><br>
                <span style="font-size: 1.5em;">{metrics['total_trades']}</span>
            </div>
            <div class="metric-card">
                <strong>Win Rate</strong><br>
                <span style="font-size: 1.5em;">{metrics['win_rate']:.1%}</span>
            </div>
            <div class="metric-card">
                <strong>Profit Factor</strong><br>
                <span style="font-size: 1.5em;">{pf_str}</span>
            </div>
            <div class="metric-card">
                <strong>Sharpe Ratio</strong><br>
                <span style="font-size: 1.5em;">{metrics['sharpe']:.2f}</span>
            </div>
            <div class="metric-card">
                <strong>Max Drawdown</strong><br>
                <span style="font-size: 1.5em;">{metrics['max_drawdown']:.1f}%</span>
            </div>
            <div class="metric-card">
                <strong>Total P&L</strong><br>
                <span class="{'positive' if metrics['total_pnl'] >= 0 else 'negative'}"
                      style="font-size: 1.5em;">${metrics['total_pnl']:,.2f}</span>
            </div>
            <p style="margin-top: 20px;"><strong>Assessment:</strong> {assessment}</p>
        </div>
        """
    )

    # Sections 2-5, 8: Require replay_db_path
    if replay_data and trades:
        # Section 2: Equity Curve
        sections.append(
            f"""
            <div class="section" id="equity-curve">
                <h2>Equity Curve</h2>
                {generate_equity_curve(trades, config)}
            </div>
            """
        )

        # Section 3: Monthly P&L Breakdown
        monthly = replay_data.get("monthly_summary", [])
        sections.append(
            f"""
            <div class="section" id="monthly-pnl">
                <h2>Monthly P&L Breakdown</h2>
                {generate_monthly_table(monthly)}
                {generate_monthly_chart(monthly, config)}
            </div>
            """
        )

        # Section 4: Trade Distribution
        sections.append(
            f"""
            <div class="section" id="trade-distribution">
                <h2>Trade Distribution</h2>
                {generate_trade_distribution(trades, config)}
            </div>
            """
        )

        # Section 5: Time Analysis
        sections.append(
            f"""
            <div class="section" id="time-analysis">
                <h2>Time Analysis</h2>
                {generate_time_analysis(trades, config)}
            </div>
            """
        )

        # Section 8: Trade Tables
        sections.append(
            f"""
            <div class="section" id="trade-tables">
                <h2>Individual Trades</h2>
                {generate_trade_tables(trades)}
            </div>
            """
        )

    # Section 6: Parameter Sensitivity (requires sweep_dir)
    if sweep_data:
        sections.append(
            f"""
            <div class="section" id="parameter-sensitivity">
                <h2>Parameter Sensitivity</h2>
                {generate_parameter_sensitivity(sweep_data, config)}
            </div>
            """
        )

    # Section 7: Walk-Forward Results (requires walk_forward_dir)
    if wf_data:
        sections.append(
            f"""
            <div class="section" id="walk-forward">
                <h2>Walk-Forward Analysis</h2>
                {generate_walk_forward_section(wf_data, config)}
            </div>
            """
        )

    # Assemble HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }}
        h1 {{
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
        }}
        .meta {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 30px;
        }}
        .metric-card {{
            display: inline-block;
            padding: 15px 20px;
            margin: 5px;
            border: 1px solid #ddd;
            border-radius: 8px;
            background: #f8f9fa;
            min-width: 120px;
            text-align: center;
        }}
        .positive {{ color: #16a34a; }}
        .negative {{ color: #dc2626; }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            padding: 8px 12px;
            text-align: right;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            text-align: right;
        }}
        .section {{
            margin: 40px 0;
        }}
        .section h2 {{
            border-bottom: 2px solid #333;
            padding-bottom: 8px;
        }}
        .section h4 {{
            margin-top: 20px;
            color: #555;
        }}
        @media print {{
            .no-print {{ display: none; }}
            .section {{ page-break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p class="meta">
        Generated: {timestamp} | Strategy: {config.strategy_name}
    </p>

    {"".join(sections)}

    <footer style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #ddd;
                   color: #666; font-size: 0.9em;">
        <p>Generated by Argus Backtest Report Generator</p>
    </footer>
</body>
</html>
"""

    # Write output
    output_path = Path(config.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(html)

    logger.info("Report generated: %s", output_path)
    return str(output_path)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Argus Backtest Report Generator",
        prog="python -m argus.backtest.report_generator",
    )

    parser.add_argument(
        "--db",
        dest="replay_db_path",
        help="Path to Replay Harness SQLite database",
    )
    parser.add_argument(
        "--sweep-dir",
        help="Path to VectorBT sweep output directory",
    )
    parser.add_argument(
        "--walk-forward-dir",
        help="Path to walk-forward results directory",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="reports/orb_validation.html",
        help="Output HTML file path",
    )
    parser.add_argument(
        "--title",
        help="Report title (auto-generated if not provided)",
    )
    parser.add_argument(
        "--strategy-name",
        default="ORB Breakout",
        help="Strategy name for the report",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    args = parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Validate at least one data source
    if not any([args.replay_db_path, args.sweep_dir, args.walk_forward_dir]):
        logger.error(
            "At least one data source (--db, --sweep-dir, or --walk-forward-dir) is required"
        )
        return

    config = ReportConfig(
        replay_db_path=args.replay_db_path,
        sweep_dir=args.sweep_dir,
        walk_forward_dir=args.walk_forward_dir,
        output_path=args.output,
        report_title=args.title,
        strategy_name=args.strategy_name,
    )

    output_path = generate_report(config)
    print(f"Report generated: {output_path}")


if __name__ == "__main__":
    main()
