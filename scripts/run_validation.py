"""Thin wrapper around revalidate_strategy.py that injects universe symbols.

The revalidation script's WalkForwardConfig.symbols defaults to None,
which auto-detects for VectorBT (scans directories) but leaves the
BacktestEngine OOS path with no symbols to load. This wrapper patches
run_fixed_params_walk_forward to set symbols before execution.

Usage:
    python scripts/run_validation.py --strategy orb --start 2023-04-01 --end 2025-03-01 \
        --output-dir data/backtest_runs/validation/ --log-level WARNING
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import yaml


def load_universe_symbols() -> list[str]:
    """Load symbols from backtest_universe.yaml, excluding unavailable ones."""
    config_path = Path("config/backtest_universe.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    symbols = config.get("symbols", [])
    return [s for s in symbols if s != "ARM"]


def main() -> None:
    """Run revalidation with universe symbols injected."""
    symbols = load_universe_symbols()
    print(f"Using {len(symbols)} symbols from backtest_universe.yaml")

    # Monkey-patch run_fixed_params_walk_forward to inject symbols
    from argus.backtest import walk_forward

    original_run = walk_forward.run_fixed_params_walk_forward

    async def patched_run(
        config: Any, fixed_params: dict[str, Any]
    ) -> Any:
        if config.symbols is None:
            config.symbols = symbols
        return await original_run(config, fixed_params)

    walk_forward.run_fixed_params_walk_forward = patched_run

    # Import and run the revalidation script
    spec = importlib.util.spec_from_file_location(
        "revalidate_strategy",
        Path("scripts/revalidate_strategy.py"),
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main(sys.argv[1:])


if __name__ == "__main__":
    main()
