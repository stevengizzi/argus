#!/usr/bin/env python3
"""
ARGUS Historical Data Cache Population Script

Downloads OHLCV-1m data from Databento and populates the HistoricalDataFeed cache.
Uses ALL_SYMBOLS per-month downloads (~35 API calls instead of 140,000).

Cache structure: {cache_dir}/{SYMBOL}/{YYYY-MM}.parquet
  - Matches HistoricalDataFeed._parquet_path() exactly
  - Each Parquet file: [timestamp, open, high, low, close, volume]

Datasets and date ranges:
  - EQUS.MINI:   Mar 2023 → present  (consolidated US equities mini feed)
  - XNAS.ITCH:   May 2018 → Feb 2023 (Nasdaq TotalView — pre-EQUS.MINI period)
  - XNYS.PILLAR: May 2018 → Feb 2023 (NYSE Integrated — pre-EQUS.MINI period)

For the pre-2023 period, XNAS.ITCH is downloaded first. XNYS.PILLAR then fills in
symbols not already covered by XNAS.ITCH (NYSE-only listings).

Prerequisites:
    pip install databento pandas pyarrow
    DATABENTO_API_KEY in environment or .env file

Usage:
    python populate_historical_cache.py                        # Full download
    python populate_historical_cache.py --update               # Download new months only
    python populate_historical_cache.py --dry-run              # Show plan, don't download
    python populate_historical_cache.py --datasets EQUS.MINI   # Single dataset only
    python populate_historical_cache.py --cache-dir /path/to/cache

Cron (monthly update on the 2nd at 2 AM):
    0 2 2 * * cd /path/to/argus && python scripts/populate_historical_cache.py --update >> logs/cache_update.log 2>&1
"""

import argparse
import calendar
import json
import logging
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCHEMA = "ohlcv-1m"
EXPECTED_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]

DATASETS = {
    "EQUS.MINI": {
        "start": date(2023, 4, 1),  # Dataset available from 2023-03-28; start April for full months
        "description": "Consolidated US equities mini feed",
    },
    "XNAS.ITCH": {
        "start": date(2018, 5, 1),
        "end": date(2023, 4, 1),  # exclusive — EQUS.MINI takes over from April 2023
        "description": "Nasdaq TotalView (pre-EQUS.MINI)",
    },
    "XNYS.PILLAR": {
        "start": date(2018, 5, 1),
        "end": date(2023, 4, 1),  # exclusive — EQUS.MINI takes over from April 2023
        "description": "NYSE Integrated (pre-EQUS.MINI)",
    },
}

# Candidate mount paths for external drive (macOS)
CANDIDATE_CACHE_DIRS = [
    "/Volumes/LaCie/argus-cache",
    "/LaCie/argus-cache",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("populate_cache")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def find_api_key() -> str:
    """Find Databento API key from environment or .env files."""
    key = os.environ.get("DATABENTO_API_KEY")
    if key:
        return key

    for env_path in [".env", "../.env", "argus/.env"]:
        p = Path(env_path)
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line.startswith("DATABENTO_API_KEY="):
                    return line.split("=", 1)[1].strip().strip("'\"")

    logger.error("DATABENTO_API_KEY not found in environment or .env")
    sys.exit(1)


def find_cache_dir(override: str | None) -> Path:
    """Resolve cache directory path."""
    if override:
        p = Path(override)
        p.mkdir(parents=True, exist_ok=True)
        return p

    for candidate in CANDIDATE_CACHE_DIRS:
        p = Path(candidate)
        if p.parent.exists():
            p.mkdir(parents=True, exist_ok=True)
            return p

    logger.error(
        "Could not find external drive. Tried: %s\n"
        "Use --cache-dir to specify the path explicitly.",
        ", ".join(CANDIDATE_CACHE_DIRS),
    )
    sys.exit(1)


def month_range(start: date, end: date) -> list[tuple[int, int]]:
    """Generate list of (year, month) tuples from start to end (exclusive)."""
    months = []
    current = date(start.year, start.month, 1)
    end_month = date(end.year, end.month, 1)
    while current < end_month:
        months.append((current.year, current.month))
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return months


def parquet_path(cache_dir: Path, symbol: str, year: int, month: int) -> Path:
    """Match HistoricalDataFeed._parquet_path() exactly."""
    return cache_dir / symbol / f"{year}-{month:02d}.parquet"


def normalize_databento_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize Databento DataFrame to ARGUS schema.

    Replicates argus/data/databento_utils.py exactly.
    """
    if df.empty:
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

    if "ts_event" in df.columns:
        result = df[["ts_event", "open", "high", "low", "close", "volume"]].copy()
        result = result.rename(columns={"ts_event": "timestamp"})
    elif df.index.name == "ts_event":
        result = df[["open", "high", "low", "close", "volume"]].copy()
        result = result.reset_index()
        result = result.rename(columns={"ts_event": "timestamp"})
    else:
        result = df[["open", "high", "low", "close", "volume"]].copy()
        result = result.reset_index()
        result.columns = EXPECTED_COLUMNS

    if result["timestamp"].dt.tz is None:
        result["timestamp"] = result["timestamp"].dt.tz_localize("UTC")
    elif str(result["timestamp"].dt.tz) != "UTC":
        result["timestamp"] = result["timestamp"].dt.tz_convert("UTC")

    return result.sort_values("timestamp").reset_index(drop=True)


def resolve_symbols(data, df: pd.DataFrame, client=None) -> pd.Series:
    """Resolve symbol names from a Databento ALL_SYMBOLS download.

    Databento ALL_SYMBOLS queries populate instrument_id but leave the symbol
    column as None. The symbology mapping is embedded in the DBNStore metadata
    and maps raw_symbol → instrument_id. We invert this to build
    instrument_id → raw_symbol.

    Returns a Series aligned with df's index containing symbol strings.
    """
    # Approach 1: symbol column already populated (non-ALL_SYMBOLS queries)
    if "symbol" in df.columns:
        valid = df["symbol"].notna() & (df["symbol"] != "") & (df["symbol"] != "0")
        if valid.sum() > len(df) * 0.5:
            logger.info("Symbols already in DataFrame (%d/%d valid)", valid.sum(), len(df))
            return df["symbol"]

    # We need instrument_id for all remaining approaches
    if "instrument_id" not in df.columns:
        raise RuntimeError("No 'symbol' or 'instrument_id' column in DataFrame")

    # Primary approach: request_symbology(client)
    # Returns: {'result': {'A': [{'d0': '...', 'd1': '...', 's': '1'}], 'AA': [{'s': '2'}], ...}}
    # where keys are ticker symbols and 's' is instrument_id as string
    if client is not None and hasattr(data, "request_symbology"):
        try:
            logger.info("Resolving symbols via request_symbology API call...")
            sym_result = data.request_symbology(client)

            sym_map: dict[int, str] = {}

            # Unwrap: the mapping lives under the 'result' key
            mapping = sym_result
            if isinstance(sym_result, dict) and "result" in sym_result:
                mapping = sym_result["result"]

            if isinstance(mapping, dict):
                for raw_symbol, intervals in mapping.items():
                    if not isinstance(intervals, (list, tuple)):
                        continue
                    for iv in intervals:
                        if isinstance(iv, dict) and "s" in iv:
                            try:
                                sym_map[int(iv["s"])] = str(raw_symbol)
                            except (ValueError, TypeError):
                                pass

            if sym_map:
                resolved = df["instrument_id"].map(sym_map)
                n_resolved = resolved.notna().sum()
                logger.info(
                    "Resolved %d/%d rows (%d unique symbols)",
                    n_resolved, len(df), len(sym_map),
                )
                if n_resolved > len(df) * 0.5:
                    return resolved
                else:
                    logger.warning(
                        "Low resolution rate (%.1f%%) — map has %d entries, "
                        "iid range in data: %d–%d, in map: %d–%d",
                        100 * n_resolved / len(df), len(sym_map),
                        df["instrument_id"].min(), df["instrument_id"].max(),
                        min(sym_map.keys()), max(sym_map.keys()),
                    )
            else:
                logger.warning("request_symbology returned no usable mappings")

        except Exception as e:
            logger.warning("request_symbology(client) failed: %s", e, exc_info=True)

    # All approaches failed — dump full diagnostics
    logger.error("Symbol resolution FAILED after all approaches.")
    logger.error("  DataFrame shape: %s", df.shape)
    logger.error("  instrument_id unique count: %d", df["instrument_id"].nunique())
    logger.error("  instrument_id sample: %s", df["instrument_id"].head(5).tolist())

    if hasattr(data, "symbology") and data.symbology:
        symbology = data.symbology
        logger.error("  symbology type: %s", type(symbology).__name__)
        if isinstance(symbology, dict):
            keys = list(symbology.keys())[:5]
            logger.error("  symbology first 5 keys: %s", keys)
            if keys:
                first_val = symbology[keys[0]]
                logger.error("  symbology[%r] type: %s", keys[0], type(first_val).__name__)
                logger.error("  symbology[%r] repr: %r", keys[0], first_val)
        else:
            logger.error("  symbology repr (first 500 chars): %r", repr(symbology)[:500])

    if hasattr(data, "mappings") and data.mappings:
        mappings = data.mappings
        logger.error("  mappings type: %s", type(mappings).__name__)
        logger.error("  mappings dir: %s", [a for a in dir(mappings) if not a.startswith("_")])

    raise RuntimeError(
        "Cannot resolve symbols from ALL_SYMBOLS download. "
        "See diagnostic output above and share it in the Claude.ai conversation."
    )


def _extract_instrument_id(interval) -> int | None:
    """Extract instrument_id from a symbology mapping interval.

    Handles multiple possible formats:
      - dict with key 's', 'symbol', or 'instrument_id'
      - object with attribute 's', 'symbol', or 'instrument_id'
      - plain int or string
    """
    if isinstance(interval, (int, float)):
        return int(interval)
    if isinstance(interval, str):
        try:
            return int(interval)
        except ValueError:
            return None

    # Dict-like
    if isinstance(interval, dict):
        for key in ("s", "symbol", "instrument_id"):
            if key in interval:
                try:
                    return int(interval[key])
                except (ValueError, TypeError):
                    pass
        return None

    # Object with attributes
    for attr in ("s", "symbol", "instrument_id"):
        if hasattr(interval, attr):
            val = getattr(interval, attr)
            if val is not None:
                try:
                    return int(val)
                except (ValueError, TypeError):
                    pass

    return None


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------
class Manifest:
    """Tracks what's been downloaded: dataset, month, symbol counts, timestamps."""

    def __init__(self, cache_dir: Path):
        self._path = cache_dir / "cache_manifest.json"
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except (json.JSONDecodeError, OSError):
                logger.warning("Corrupt manifest, starting fresh")
        return {"version": 1, "downloads": {}, "last_updated": None}

    def save(self):
        self._data["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._path.write_text(json.dumps(self._data, indent=2))

    def is_downloaded(self, dataset: str, year: int, month: int) -> bool:
        key = f"{dataset}/{year}-{month:02d}"
        return key in self._data["downloads"]

    def record_download(
        self,
        dataset: str,
        year: int,
        month: int,
        symbol_count: int,
        row_count: int,
        total_size_bytes: int,
        elapsed_s: float,
        new_symbols: int = 0,
        skipped_symbols: int = 0,
    ):
        key = f"{dataset}/{year}-{month:02d}"
        self._data["downloads"][key] = {
            "dataset": dataset,
            "year": year,
            "month": month,
            "symbol_count": symbol_count,
            "new_symbols_written": new_symbols,
            "skipped_overlap": skipped_symbols,
            "row_count": row_count,
            "total_size_bytes": total_size_bytes,
            "elapsed_s": round(elapsed_s, 1),
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        }
        self.save()

    def get_latest_month(self, dataset: str) -> tuple[int, int] | None:
        """Return the latest (year, month) downloaded for a dataset."""
        latest = None
        for key, info in self._data["downloads"].items():
            if info.get("dataset") == dataset:
                ym = (info["year"], info["month"])
                if latest is None or ym > latest:
                    latest = ym
        return latest

    @property
    def summary(self) -> dict:
        by_dataset: dict[str, int] = {}
        total_bytes = 0
        for info in self._data["downloads"].values():
            ds = info.get("dataset", "unknown")
            by_dataset[ds] = by_dataset.get(ds, 0) + 1
            total_bytes += info.get("total_size_bytes", 0)
        return {
            "total_months": len(self._data["downloads"]),
            "months_by_dataset": by_dataset,
            "total_size_gb": round(total_bytes / (1024**3), 2),
            "last_updated": self._data.get("last_updated"),
        }


# ---------------------------------------------------------------------------
# Core download logic
# ---------------------------------------------------------------------------
def verify_dataset(client, dataset: str) -> bool:
    """Verify $0 cost for a dataset before bulk download."""
    logger.info("Verifying cost for %s...", dataset)
    try:
        cost = client.metadata.get_cost(
            dataset=dataset,
            symbols="ALL_SYMBOLS",
            schema=SCHEMA,
            start="2023-06-01" if dataset == "EQUS.MINI" else "2022-06-01",
            end="2023-07-01" if dataset == "EQUS.MINI" else "2022-07-01",
        )
        if cost > 0:
            logger.error("  %s: cost is $%.4f — ABORTING", dataset, cost)
            return False
        logger.info("  %s: $0.00 confirmed ✓", dataset)
        return True
    except Exception as e:
        logger.error("  %s: cost check failed — %s", dataset, e)
        return False


def download_and_split_month(
    client,
    dataset: str,
    year: int,
    month: int,
    cache_dir: Path,
    existing_symbols: set[str] | None = None,
    dry_run: bool = False,
) -> dict:
    """Download ALL_SYMBOLS for one month, split into per-symbol Parquet files.

    Args:
        client: Databento Historical client.
        dataset: Databento dataset ID.
        year, month: Target month.
        cache_dir: Root cache directory.
        existing_symbols: If set, skip symbols already in this set
                          (used for XNYS.PILLAR after XNAS.ITCH).
        dry_run: If True, just log what would happen.

    Returns:
        Dict with stats: symbol_count, row_count, size_bytes, elapsed_s, etc.
    """
    _, last_day = calendar.monthrange(year, month)
    start_str = f"{year}-{month:02d}-01"
    end_str = (date(year, month, last_day) + timedelta(days=1)).isoformat()
    month_label = f"{year}-{month:02d}"

    if dry_run:
        logger.info("  [DRY RUN] Would download %s %s", dataset, month_label)
        return {"symbol_count": 0, "row_count": 0, "size_bytes": 0, "elapsed_s": 0}

    logger.info("  Downloading %s %s (ALL_SYMBOLS)...", dataset, month_label)
    t0 = time.time()

    max_retries = 3
    data = None
    df = None
    for attempt in range(1, max_retries + 1):
        try:
            data = client.timeseries.get_range(
                dataset=dataset,
                symbols="ALL_SYMBOLS",
                schema=SCHEMA,
                start=start_str,
                end=end_str,
            )

            # Inject symbology BEFORE converting to DataFrame.
            # For ALL_SYMBOLS queries, the symbol column is None until
            # symbology is resolved. request_symbology() makes an API call
            # and injects the instrument_id → symbol mapping into the DBNStore.
            try:
                data.request_symbology(client)
                logger.info("  Symbology injected for %s %s", dataset, month_label)
            except Exception as sym_err:
                logger.warning(
                    "  request_symbology failed for %s %s: %s — will attempt fallback",
                    dataset, month_label, sym_err,
                )

            df = data.to_df()
            break  # Success
        except Exception as e:
            error_msg = str(e).lower()
            is_retryable = any(s in error_msg for s in [
                "prematurely", "timeout", "connection", "stream",
                "broken pipe", "reset by peer",
            ])
            if is_retryable and attempt < max_retries:
                wait = 10 * attempt
                logger.warning(
                    "  Attempt %d/%d failed for %s %s: %s — retrying in %ds",
                    attempt, max_retries, dataset, month_label, e, wait,
                )
                time.sleep(wait)
            else:
                logger.error("  API error for %s %s: %s", dataset, month_label, e)
                return {"error": str(e)}

    elapsed_download = time.time() - t0

    if df is None:
        return {"error": "All retry attempts failed"}

    if df.empty:
        logger.warning("  No data for %s %s", dataset, month_label)
        return {"symbol_count": 0, "row_count": 0, "size_bytes": 0, "elapsed_s": elapsed_download}

    # Resolve symbols
    symbols = resolve_symbols(data, df, client=client)
    df = df.copy()
    df["_symbol"] = symbols

    # Drop rows where symbol resolution failed
    unresolved = df["_symbol"].isna() | (df["_symbol"] == "")
    if unresolved.any():
        logger.warning(
            "  Dropped %d/%d rows with unresolved symbols",
            unresolved.sum(),
            len(df),
        )
        df = df[~unresolved]

    # Split by symbol and write
    grouped = df.groupby("_symbol")
    n_symbols = len(grouped)
    n_written = 0
    n_skipped = 0
    total_size = 0
    total_rows = 0
    written_symbols: set[str] = set()

    for symbol, group_df in grouped:
        symbol = str(symbol).strip()

        # Skip if already covered by a prior dataset (e.g., XNAS.ITCH)
        if existing_symbols is not None and symbol in existing_symbols:
            n_skipped += 1
            continue

        # Normalize to ARGUS schema
        normalized = normalize_databento_df(group_df)
        if normalized.empty:
            continue

        # Validate
        assert list(normalized.columns) == EXPECTED_COLUMNS, (
            f"Column mismatch for {symbol}: {list(normalized.columns)}"
        )

        # Write
        out_path = parquet_path(cache_dir, symbol, year, month)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        normalized.to_parquet(out_path, index=False)

        # Validate written file
        file_size = out_path.stat().st_size
        if file_size == 0:
            logger.warning("  Zero-size file: %s", out_path)
            out_path.unlink()
            continue

        total_size += file_size
        total_rows += len(normalized)
        n_written += 1
        written_symbols.add(symbol)

    elapsed_total = time.time() - t0

    logger.info(
        "  %s %s: %d symbols (%d written, %d overlap-skipped), "
        "%s rows, %.1f MB, %.1fs (%.1fs download + %.1fs split)",
        dataset,
        month_label,
        n_symbols,
        n_written,
        n_skipped,
        f"{total_rows:,}",
        total_size / (1024**2),
        elapsed_total,
        elapsed_download,
        elapsed_total - elapsed_download,
    )

    return {
        "symbol_count": n_symbols,
        "new_symbols_written": n_written,
        "skipped_overlap": n_skipped,
        "row_count": total_rows,
        "size_bytes": total_size,
        "elapsed_s": elapsed_total,
        "written_symbols": written_symbols,
    }


def get_months_to_download(
    dataset: str,
    manifest: Manifest,
    update_mode: bool,
) -> list[tuple[int, int]]:
    """Determine which months need downloading for a dataset."""
    cfg = DATASETS[dataset]
    start = cfg["start"]
    end = cfg.get("end", date.today().replace(day=1))  # default: up to current month

    all_months = month_range(start, end)

    if update_mode:
        # Only download months newer than the latest cached
        latest = manifest.get_latest_month(dataset)
        if latest:
            all_months = [(y, m) for y, m in all_months if (y, m) > latest]
            if not all_months:
                logger.info("  %s: up to date (latest: %d-%02d)", dataset, *latest)

    # Skip already-downloaded months
    needed = [
        (y, m) for y, m in all_months if not manifest.is_downloaded(dataset, y, m)
    ]

    return needed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Populate ARGUS historical data cache from Databento"
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default=None,
        help="Cache directory path (default: auto-detect external drive)",
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=list(DATASETS.keys()),
        choices=list(DATASETS.keys()),
        help="Which datasets to download (default: all three)",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Only download months newer than what's cached",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show download plan without executing",
    )
    args = parser.parse_args()

    # Setup
    try:
        import databento as db
    except ImportError:
        logger.error("databento not installed. Run: pip install databento")
        sys.exit(1)

    api_key = find_api_key()
    cache_dir = find_cache_dir(args.cache_dir)
    client = db.Historical(api_key)
    manifest = Manifest(cache_dir)

    logger.info("Cache directory: %s", cache_dir)
    logger.info("Datasets: %s", ", ".join(args.datasets))
    logger.info("Mode: %s", "update" if args.update else "full")
    if args.dry_run:
        logger.info("DRY RUN — no data will be downloaded")

    # Show current manifest state
    summary = manifest.summary
    if summary["total_months"] > 0:
        logger.info(
            "Existing cache: %d months, %.2f GB",
            summary["total_months"],
            summary["total_size_gb"],
        )

    # Verify cost for each dataset
    if not args.dry_run:
        for ds in args.datasets:
            if not verify_dataset(client, ds):
                logger.error("Cost verification failed for %s — aborting", ds)
                sys.exit(1)

    # Build download plan
    plan: list[tuple[str, list[tuple[int, int]]]] = []
    total_months = 0
    for ds in args.datasets:
        months = get_months_to_download(ds, manifest, args.update)
        if months:
            plan.append((ds, months))
            total_months += len(months)
            logger.info(
                "  %s: %d months to download (%d-%02d → %d-%02d)",
                ds,
                len(months),
                *months[0],
                *months[-1],
            )
        else:
            logger.info("  %s: nothing to download", ds)

    if not plan:
        logger.info("Everything is up to date!")
        return

    # Estimate time (based on investigation: ~6.4 min per ALL_SYMBOLS month)
    est_hours = (total_months * 6.5) / 60
    logger.info(
        "\nDownload plan: %d months across %d dataset(s), ~%.1f hours estimated",
        total_months,
        len(plan),
        est_hours,
    )

    if args.dry_run:
        logger.info("DRY RUN complete. Remove --dry-run to execute.")
        return

    # Execute downloads
    # Track symbols covered by earlier datasets to handle XNAS/XNYS overlap
    all_covered_symbols: set[str] = set()
    # Build set of existing symbols from cache directory (from prior runs)
    for symbol_dir in cache_dir.iterdir():
        if symbol_dir.is_dir() and not symbol_dir.name.startswith("."):
            all_covered_symbols.add(symbol_dir.name)

    grand_start = time.time()
    months_done = 0

    for dataset, months in plan:
        logger.info("\n" + "=" * 60)
        logger.info("Dataset: %s (%d months)", dataset, len(months))
        logger.info("=" * 60)

        # For XNYS.PILLAR, skip symbols already covered by XNAS.ITCH
        use_existing = all_covered_symbols if dataset == "XNYS.PILLAR" else None

        for year, month_num in months:
            months_done += 1
            remaining = total_months - months_done
            elapsed_so_far = time.time() - grand_start
            if months_done > 1:
                avg_per_month = elapsed_so_far / (months_done - 1)
                eta_min = (remaining * avg_per_month) / 60
                logger.info(
                    "\n[%d/%d] ETA: %.0f min remaining",
                    months_done,
                    total_months,
                    eta_min,
                )

            stats = download_and_split_month(
                client=client,
                dataset=dataset,
                year=year,
                month=month_num,
                cache_dir=cache_dir,
                existing_symbols=use_existing,
                dry_run=args.dry_run,
            )

            if "error" not in stats:
                manifest.record_download(
                    dataset=dataset,
                    year=year,
                    month=month_num,
                    symbol_count=stats.get("symbol_count", 0),
                    row_count=stats.get("row_count", 0),
                    total_size_bytes=stats.get("size_bytes", 0),
                    elapsed_s=stats.get("elapsed_s", 0),
                    new_symbols=stats.get("new_symbols_written", 0),
                    skipped_symbols=stats.get("skipped_overlap", 0),
                )

                # Track newly written symbols for XNYS overlap detection
                if "written_symbols" in stats:
                    all_covered_symbols.update(stats["written_symbols"])
            else:
                logger.error(
                    "  FAILED: %s %d-%02d — %s (continuing with next month)",
                    dataset,
                    year,
                    month_num,
                    stats["error"],
                )

    # Final summary
    total_elapsed = time.time() - grand_start
    final_summary = manifest.summary
    logger.info("\n" + "=" * 60)
    logger.info("DOWNLOAD COMPLETE")
    logger.info("=" * 60)
    logger.info("Total time:    %.1f min (%.1f hours)", total_elapsed / 60, total_elapsed / 3600)
    logger.info("Total months:  %d", final_summary["total_months"])
    logger.info("Total size:    %.2f GB", final_summary["total_size_gb"])
    logger.info("By dataset:    %s", final_summary["months_by_dataset"])
    logger.info("Manifest:      %s", manifest._path)

    # Count total symbols in cache
    symbol_dirs = [d for d in cache_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
    logger.info("Total symbols: %d", len(symbol_dirs))


if __name__ == "__main__":
    main()