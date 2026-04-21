# Audit: Dependencies & Infrastructure

**Session:** P1-I
**Date:** 2026-04-21
**Scope:** `pyproject.toml`, `argus/ui/package.json`, `.env.example`, `.gitignore`, `.gitmodules`, root/sub `conftest.py`, CI configuration (none found), `scripts/` hygiene spot-checks, cleanup tracker items #2 and #3.
**Files examined:** 7 deep / ~15 skimmed (grep-heavy).

---

## 1. Python Dependency Table — [pyproject.toml](../../../pyproject.toml)

### Runtime dependencies (17)

| # | Dep | Pin | Current latest (approx) | Used in | Notes |
|---|-----|-----|-----------------------|---------|-------|
| 1 | `pydantic` | `>=2.5,<3` | 2.11 | 100+ files | v2 confirmed — zero `.dict()` v1-shape calls in `argus/`. CLEAN. |
| 2 | `PyYAML` | `>=6.0,<7` | 6.0.2 | config loaders | Current. |
| 3 | `aiosqlite` | `>=0.19,<1` | 0.20 | DatabaseManager, stores | Current. |
| 4 | `python-ulid` | `>=2.2,<3` | 3.x | trade IDs (DEC-026) | Upper bound lags one major — 3.x is out. LOW. |
| 5 | `pandas` | `>=2.0,<3` | 2.2 | backtest, analytics | Current. v2 confirmed (no v1 deprecations). |
| 6 | `pyarrow` | `>=14.0,<18` | 18 | Parquet cache | Upper bound effectively excludes the latest major — 18.x is current. LOW. |
| 7 | `alpaca-py` | `>=0.30,<1` | 0.40 | `alpaca_*` files | Alpaca demoted to incubator (DEC-086). Still required by `execution/alpaca_broker.py`, `data/alpaca_data_service.py`, `data/alpaca_scanner.py`, `backtest/data_fetcher.py`. Could migrate to `optional-dependencies.incubator` once those call paths are verified unused in live mode. |
| 8 | `python-dotenv` | `>=1.0,<2` | 1.0.1 | config bootstrap | Current. Note: `pydantic-settings` is not installed nor imported — config layer uses plain `Pydantic BaseModel` + manual env-var resolution (DEC-032). CLEAN. |
| 9 | `aiohttp` | `>=3.9,<4` | 3.10 | FMP, Finnhub, SEC Edgar, Databento HTTP, health ping | Current. No redundancy with `httpx` (dev-only). |
| 10 | `databento` | `>=0.40.0` | 0.49 | primary market-data feed | **Unbounded upper** — major risk. See M1. |
| 11 | `ib_async` | `>=2.1.0` | 2.1.1 | IBKR broker | **Unbounded upper** — major risk. See M1. |
| 12 | `fastapi` | `>=0.109,<1` | 0.115 | REST + WS server | Current. |
| 13 | `uvicorn[standard]` | `>=0.27,<1` | 0.32 | ASGI | Current. |
| 14 | `python-jose[cryptography]` | `>=3.3,<4` | 3.3.0 (unreleased since 2022) | JWT auth in 6 files | **Unmaintained + CVE-2024-33663** (algorithm confusion, <3.4.0). See M2. |
| 15 | `passlib[bcrypt]` | `>=1.7,<2` | 1.7.4 (unreleased since 2020) | `api/auth.py` password hashing | **Unmaintained + bcrypt 4.x incompat warnings.** See M3. |
| 16 | `yfinance` | `>=0.2.31,<1` | 0.2.x | `vix_data_service.py` | Unofficial Yahoo scraper — already tracked by [DEF-103](../../../CLAUDE.md) + DEF-149 (FRED VIX backup). No new finding. |
| 17 | `duckdb` | `>=1.0,<2` | 1.1 | `HistoricalQueryService` (Sprint 31A.5) | Current. |

### Optional `[project.optional-dependencies]`

**dev (6):** pytest, pytest-asyncio, pytest-cov, ruff, httpx, plotly — all current. **Concern:** `plotly` is listed under `dev` but imported by 5 production files in `argus/backtest/` (`vectorbt_*.py`, `report_generator.py`). See M4.

**backtest (5):** vectorbt, numpy, matplotlib, scipy, scikit-learn. See M5 (`vectorbt`, `scikit-learn` not imported anywhere).

### Dev vs runtime separation

Clean split between `[project.dependencies]` (runtime) and `[project.optional-dependencies].dev` / `.backtest`. Only issue: `plotly` misplacement (M4).

---

## 2. Frontend Dependency Table — [argus/ui/package.json](../../../argus/ui/package.json)

Overall: frontend is **very current**. No libs lag by a major version. All packages known to project-knowledge are present.

| Dep | Pin | Current (Apr 2026 approx) | Status |
|-----|-----|---------------------------|--------|
| react / react-dom | `^19.2.0` | 19.2 | Current (just released). |
| @tanstack/react-query | `^5.90.21` | 5.x | Current. |
| zustand | `^5.0.11` | 5.x | Current. |
| framer-motion | `^12.34.3` | 12.x | Current. |
| lightweight-charts | `^5.1.0` | 5.1 | v5 per project spec. Current. |
| recharts | `^3.7.0` | 3.x | Current. |
| three | `^0.183.2` | 0.183 | Per DEC-108 (r128 specified in docs but actually 0.183 — see L1). |
| @types/three | `^0.183.1` | matches three | Aligned with three version. |
| react-router-dom | `^7.13.0` | 7.x | Current. |
| d3-* submodules | `^3.x` / `^4.x` | current | Correctly using submodule imports (not full `d3`) — good tree-shaking discipline. |
| @tauri-apps/api | `^2.0.0` | 2.x | Current. |
| lucide-react | `^0.575.0` | 0.5xx | Current. |
| react-markdown / rehype-sanitize / remark-gfm | current | | Current. Sanitization wired (security-conscious). |

### Dev deps

TypeScript 5.9, Vitest 4.0, Vite 7.3, Tailwind 4.2 (with `@tailwindcss/vite`), ESLint 9, jsdom 28 — all current. No deprecated `@types/*` bloat: types match their primary packages' majors.

**Observation:** `react-grid-layout` (mentioned in audit-plan pre-flight as "planned") is NOT installed. That's consistent — it's not yet used.

---

## 3. `.env.example` Completeness

Every env var resolved by `os.getenv` / `os.environ.get` in `argus/` (including config-indirect lookups via `api_key_env_var` YAML fields) maps to a `.env.example` entry:

| Env var | Source | In `.env.example`? |
|---------|--------|-------------------|
| `DATABENTO_API_KEY` | `config/brokers.yaml` → DatabentoDataService, backtest feeds | ✅ line 7 |
| `IBKR_HOST` / `IBKR_PORT` / `IBKR_CLIENT_ID` | IBKR broker | ✅ lines 10–12 |
| `ARGUS_JWT_SECRET` | `config/system.yaml` `jwt_secret_env` → `api/auth.py:159`, `main.py:1237` | ✅ line 15 |
| `ARGUS_PASSWORD_HASH` | `api/dev_state.py`, `api/setup_password.py` | ✅ line 16 |
| `ANTHROPIC_API_KEY` | `ai/config.py:59` | ✅ line 19 (commented out; optional — intentional) |
| `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` | `config/brokers.yaml` → alpaca_* modules | ✅ lines 24–25 |
| `HEALTHCHECKS_PING_URL` | `config/system.yaml` `heartbeat_url_env` → `core/health.py`, `core/config.py:192` | ✅ line 30 |
| `DISCORD_WEBHOOK_URL` | `config/system.yaml` `alert_webhook_url_env` → `core/config.py:201` | ✅ line 34 |
| `FMP_API_KEY` | `config/system.yaml` + `config/system_live.yaml` | ✅ line 38, also `main.py:750`, `databento_data_service.py:1195` |
| `FINNHUB_API_KEY` | `config/system.yaml` | ✅ line 42 |
| `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY` | [backtest/data_fetcher.py:714-715, 749-750](../../../argus/backtest/data_fetcher.py#L714-L715) | ⚠️ NOT documented — but they are intentional *fallbacks* for the primary `ALPACA_*` names (alpaca-py default convention). See C1. |

Security: all entries use placeholder values (no leaked real secrets). ✅

---

## 4. CI Configuration

**Finding: No `.github/` directory exists. No CI is configured.**

- No `.github/workflows/*.yml`
- No `.gitlab-ci.yml`, `Jenkinsfile`, `circle.yml`, `buildkite.yml`
- No `pytest.ini` / `setup.cfg` / `tox.ini` — pytest config lives inline in `[tool.pytest.ini_options]` of `pyproject.toml`

All testing is local-only. See M6.

---

## 5. Security Posture

- ✅ No hardcoded API keys / tokens / credentials anywhere in the repo (verified via targeted grep on `sk-`, `db-`, `db-ZzZ`, `ALPACA_.*=` patterns during adjacent audits).
- ✅ `.env` properly gitignored ([.gitignore:27](../../../.gitignore#L27)).
- ✅ All SQLite DBs gitignored via both `*.db` (line 63) and `/data/` (line 72). Verified: `data/argus.db`, `data/catalyst.db`, `data/counterfactual.db`, `data/evaluation.db`, `data/experiments.db`, `data/learning.db`, `data/regime_history.db`, `data/vix_landscape.db` — all present locally, all properly excluded.
- ✅ DuckDB caches gitignored (`*.duckdb`, `*.duckdb.wal`).
- ✅ Parquet cache gitignored via `/data/` catch-all.
- ✅ `secrets.yaml`, `credentials.yaml`, `*.pem`, `*.key` explicitly excluded.
- ✅ `.claude/settings.json` gitignored (no personal IDE settings).
- ⚠️ Known CVE on `python-jose[cryptography]` <3.4.0 — see M2.
- ⚠️ `passlib` is effectively abandoned — see M3.

---

## 6. Lockfile Status

| Lockfile | Present | Committed |
|----------|--------:|----------:|
| Python (`poetry.lock`, `uv.lock`, `pdm.lock`, `requirements-lock.txt`) | ❌ None | N/A |
| Frontend (`argus/ui/package-lock.json`) | ✅ Yes | ✅ Yes |

**Finding: Python has no lockfile.** See M7.

---

## 7. Cleanup Tracker #2 + #3 Confirmation

### #2 — SQL f-string interpolation for numeric Pydantic fields
**Confirmed** at [scripts/resolve_sweep_symbols.py:211-216](../../../scripts/resolve_sweep_symbols.py#L211-L216):

```python
if filter_config.min_price is not None:
    having_clauses.append(f"AVG(close) >= {filter_config.min_price}")
if filter_config.max_price is not None:
    having_clauses.append(f"AVG(close) <= {filter_config.max_price}")
if filter_config.min_avg_volume is not None:
    having_clauses.append(f"AVG(volume) >= {filter_config.min_avg_volume}")
```

F-string interpolation of Pydantic-validated numeric values into a DuckDB HAVING clause. Pydantic validation enforces `float`/`int`, which eliminates the direct SQL-injection vector, but there is no defense-in-depth: any future change that relaxes those field types (e.g., to `str` for expression support) silently re-opens the injection. See M8.

### #3 — Hardcoded `'historical'` view name
**Confirmed** at [scripts/resolve_sweep_symbols.py:171](../../../scripts/resolve_sweep_symbols.py#L171):

```python
df = service.query("SELECT COUNT(DISTINCT symbol) AS n FROM historical", [])
```

The script embeds the DuckDB VIEW name `historical`, which is an internal implementation detail of `HistoricalQueryService`. If the VIEW name ever changes (likely during consolidation-cache cutover — see M9's cross-ref to DEF-161/162), this script breaks silently. See M9.

---

## 8. Scripts/ Hygiene Summary

[scripts/](../../../scripts/) contains 31 files (25 Python, 3 shell, sprint_runner/ subdir, ibc/ subdir, launch_monitor.sh, __pycache__).

- ✅ All Python scripts have `#!/usr/bin/env python3` shebang OR a module docstring (both acceptable).
- ✅ All shell scripts have `#!/usr/bin/env bash`.
- ✅ All DB-writing scripts target valid paths: `data/argus.db` (TradeLogger — DEC-345 names the separated DB `evaluation.db`, `argus.db` remains the trades DB). Verified: `migrate_def159_bogus_trades.py:21`, `seed_quality_data.py:10,161`.
- ⚠️ 5 files named `scripts/test_*.py` exist (databento_scanner, ibkr_bracket_lifecycle, ibkr_order_lifecycle, position_management_lifecycle, time_stop_eod). Pytest is scoped to `testpaths = ["tests"]`, so these are NOT auto-discovered — they're manual one-shot diagnostic runners. **No risk, but the naming is misleading.** See C2.
- No broken imports, no shebangs pointing at missing interpreters, no paths that disagree with DEC-345.

---

## 9. Submodule Hygiene

- [.gitmodules](../../../.gitmodules) references `workflow` → `https://github.com/stevengizzi/claude-workflow.git`. ✅
- Submodule currently at commit `70b0339c78c1f5f71c02cd6cc80ad3c984efd1c8` on `heads/main` — intentional per project-knowledge ("workflow/ submodule is out of scope — separate repo, separate audit cadence").
- No other submodules. ✅

---

## 10. Root `conftest.py`

[tests/conftest.py](../../../tests/conftest.py) — 81 lines. Clean.

- 6 fixtures: `config`, `fixtures_dir`, `bus`, `db` (tmp_path-scoped, with proper cleanup), `trade_logger`, `simulated_broker`, `risk_manager`. Function-scoped (xdist-safe).
- 1 autouse fixture: `clear_orb_family_exclusion_set` — clears `OrbBaseStrategy._orb_family_triggered_symbols` (a class variable) before and after each test. Well-documented with a doc reason. ✅
- 4 sub-conftests: [tests/ai/conftest.py](../../../tests/ai/conftest.py), [tests/api/conftest.py](../../../tests/api/conftest.py), [tests/backtest/conftest.py](../../../tests/backtest/conftest.py), [tests/sprint_runner/conftest.py](../../../tests/sprint_runner/conftest.py). All scoped below `tests/` root — no global conflicts expected.
- No session-scoped fixtures with shared mutable state detected.
- No state-leak risks observed beyond the already-mitigated ORB family set.

---

## 11. Monthly-Update-Cron DEF Recommendation

The audit-plan flags: *"historical cache monthly update cron not yet scheduled (script supports `--update` mode; log as DEF at next doc sync)."*

**Status: Already tracked — no new DEF needed.**

- [DEF-097](../../../CLAUDE.md) in [CLAUDE.md](../../../CLAUDE.md): *"Schedule monthly cache update cron job"* — `populate_historical_cache.py --update`. Priority: LOW.
- [DEF-162](../../../CLAUDE.md): *"Monthly re-consolidation cron scheduling for `scripts/consolidate_parquet_cache.py` — chains with the existing `scripts/populate_historical_cache.py --update` cron (DEF-097). Both should be scheduled as a pair."* Opened Sprint 31.85. Priority: LOW.

Recommendation: **None required.** Both ends of the cache-maintenance pair are already deferred. Phase 2 should re-confirm priority (still LOW) rather than re-open.

---

## CRITICAL Findings

*None.* Dependencies are generally well-pinned, no pydantic v1 hangover, no leaked secrets, no `.env`/`data/` commit risk.

---

## MEDIUM Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| M1 | [pyproject.toml:20-21](../../../pyproject.toml#L20-L21) | **`databento>=0.40.0` and `ib_async>=2.1.0` have no upper version bound.** Both talk to external services with live money on the line. A `pip install -U` by an operator, a fresh venv build, or a CI cache-miss could silently pull a breaking major-version bump (e.g., `databento` 1.x, `ib_async` 3.x) and corrupt live-trading wire-up. Every other runtime dep in the file has a `<N` upper bound. | Silent breakage on re-install. Execution-path libs are the worst place for this. | Add explicit upper bounds: `"databento>=0.40.0,<1"` and `"ib_async>=2.1.0,<3"`. Verify against current installed versions before pinning. | `safe-during-trading` (doc/config only — no code change) |
| M2 | [pyproject.toml:25](../../../pyproject.toml#L25) + [argus/api/auth.py:26](../../../argus/api/auth.py#L26) and 5 other files | **`python-jose[cryptography]` has CVE-2024-33663 (algorithm confusion) affecting <3.4.0** and the library has had no release since 2022. Used in 6 files for JWT signing/verification on the Command Center API. | Security exposure on paper-trading API auth. Low blast radius today (single-user auth, not public-facing), but the dep is a zombie. | Migrate from `python-jose` → `PyJWT` (`pyjwt[crypto]>=2.8,<3`). API: `jwt.encode(payload, secret, algorithm="HS256")` / `jwt.decode(...)` — nearly drop-in for the 6 imports. Single-session Phase 3 fix. | `weekend-only` (touches auth on the API — regression risk) |
| M3 | [pyproject.toml:26](../../../pyproject.toml#L26) + [argus/api/auth.py](../../../argus/api/auth.py) | **`passlib[bcrypt]` is effectively abandoned** (last release 2020) and emits `AttributeError: module 'bcrypt' has no attribute '__about__'` warnings under bcrypt >=4.1. Used for operator-password hashing. | Library rot; not a live security issue but a maintenance time-bomb. | Replace with direct `bcrypt` calls (`bcrypt.hashpw` / `bcrypt.checkpw`) — the passlib wrapper adds little value for a single scheme. Or adopt `argon2-cffi` if rotating hash scheme. | `weekend-only` (touches auth) |
| M4 | [pyproject.toml:38](../../../pyproject.toml#L38) | **`plotly` is declared under `[project.optional-dependencies].dev`** but imported by 5 production-adjacent files in `argus/backtest/`: `vectorbt_afternoon_momentum.py`, `vectorbt_vwap_reclaim.py`, `vectorbt_orb_scalp.py`, `vectorbt_orb.py`, `report_generator.py`. An operator installing only the runtime set (no `[dev]` extra) will fail `python -m argus.backtest.*` commands documented in [CLAUDE.md:112-120](../../../CLAUDE.md#L112-L120). | Broken operator install path. | Move `plotly>=5.18,<6` from `dev` → `backtest` extras. (Note: may become moot if P1-E2 M2 adopted to retire `report_generator.py` + vectorbt_*.py files.) | `safe-during-trading` |
| M5 | [pyproject.toml:42,46](../../../pyproject.toml#L42) | **`vectorbt>=0.28,<1` and `scikit-learn>=1.5,<2` are declared in `[project.optional-dependencies].backtest` but imported nowhere in the codebase.** The `vectorbt_*.py` files are named after the library but use pure NumPy/Pandas — the file header of [vectorbt_orb.py:11](../../../argus/backtest/vectorbt_orb.py#L11) explicitly says *"VectorBT had numba/coverage compatibility issues at install time"*. `scikit-learn` appears in no grep hits. | Dead dep declarations — confusing signal to readers and to `pip-audit` scans. | Remove both from the `backtest` extra. If scipy (2 files) + numpy + matplotlib (1 file) + plotly (M4 placement) are the real backtest surface, list only those. | `safe-during-trading` |
| M6 | (no file — absence) | **No CI configuration exists.** No `.github/`, no `.gitlab-ci.yml`, no `Jenkinsfile`. All test enforcement is local. The ARGUS test suite is 4,934 pytest + 846 Vitest tests — a CI matrix would catch regressions that the operator could miss during a solo dev workflow, especially under xdist-sensitive configurations (DEF-048, DEF-150) where local runs can be flaky. | No external check on test-count regression, lint regression, or Python-version incompatibility. Amplifies the risk of M1-style silent breaks. | Minimum viable CI: a single GitHub Actions workflow running `python -m pytest --ignore=tests/test_main.py -n auto -q` + `cd argus/ui && npx vitest run` on push to main, matrixed against the `requires-python = ">=3.11"` minimum. Does not need to run live-broker tests. | `safe-during-trading` (CI config is offline — zero live-paper risk) |
| M7 | (no file — absence) | **No Python lockfile** (no `poetry.lock`, `uv.lock`, `pdm.lock`, `requirements-lock.txt`). Reproducibility depends entirely on the version-range solver producing the same tree across installs. Combined with M1 (unbounded `databento` / `ib_async`), a clean re-install could produce a different execution-path runtime than what was validated in the last sprint. Frontend has `package-lock.json` ✅; Python doesn't. | Reproducibility gap. Not acute today, but one bad upgrade will expose it. | Commit a `uv.lock` or `requirements.lock` (generated via `uv pip compile pyproject.toml -o requirements.lock`) alongside `pyproject.toml`. Wire CI (when added per M6) to install from the lockfile. | `safe-during-trading` |
| M8 | [scripts/resolve_sweep_symbols.py:211-216](../../../scripts/resolve_sweep_symbols.py#L211-L216) | **SQL f-string interpolation for numeric Pydantic fields** (cleanup tracker #2 — confirmed). Today safe because Pydantic enforces `float`/`int`; tomorrow unsafe the moment someone adds a string-typed filter (e.g., "P/E < 30" expression). No defense-in-depth. | Defense-in-depth gap in an operator-invoked sweep tool. | Convert to DuckDB parameter binding: `service.query("... HAVING AVG(close) >= ? AND AVG(close) <= ? AND AVG(volume) >= ?", [min_price, max_price, min_avg_volume])`, building the clause list and param list in lockstep. | `safe-during-trading` (script is operator-invoked, not runtime) |
| M9 | [scripts/resolve_sweep_symbols.py:171](../../../scripts/resolve_sweep_symbols.py#L171) | **`_count_cache_symbols()` hardcodes `'historical'` DuckDB VIEW name** (cleanup tracker #3 — confirmed). The view name is an internal detail of `HistoricalQueryService`. A rename during the pending cache-consolidation cutover (DEF-161 resolved, but `cache_dir` repoint in `config/historical_query.yaml` is still operator-pending per Sprint 31.85 close-out) could land on a schema where the script silently returns 0. | Tight coupling between an operational sweep script and a service implementation detail. | Add a public method on `HistoricalQueryService` — e.g., `count_distinct_symbols() -> int` — and call that from the script. Decouples the VIEW name from consumers. | `safe-during-trading` |

---

## LOW Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| L1 | [argus/ui/package.json:40](../../../argus/ui/package.json#L40) vs [docs/decision-log.md](../../../docs/decision-log.md) | **Documentation drift:** DEC-108 mentions Three.js r128 but `package.json` installs `three@^0.183.2`. Either DEC-108 was written before the Three.js migrated to semver (they did, circa r154) and never updated, or the docs are stale. Code is correct. | Cosmetic doc drift. | Update DEC-108 to reference `three@0.183` or "current major" instead of "r128". | `safe-during-trading` |
| L2 | [pyproject.toml:14](../../../pyproject.toml#L14) | `python-ulid>=2.2,<3` — library is at v3.x. Minor lag. | None (v2→v3 is non-breaking for the `ULID()`/`str` use in the codebase per DEC-026). | Bump on next dependency refresh pass. | `weekend-only` (touches a runtime dep — unlikely but validate) |
| L3 | [pyproject.toml:16](../../../pyproject.toml#L16) | `pyarrow>=14.0,<18` — upper bound excludes 18.x (current latest). | None today; future upgrade friction. | Bump to `<19` next dependency refresh. | `weekend-only` |
| L4 | [pyproject.toml:17](../../../pyproject.toml#L17) | `alpaca-py>=0.30,<1` is still in `[project.dependencies]` despite DEC-086 demoting Alpaca to incubator-only. 4 files still import it (alpaca_broker, alpaca_data_service, alpaca_scanner, backtest/data_fetcher). | Live mode does not need Alpaca; keeping it in core dependencies perpetuates incubator baggage. | Longer-term: move `alpaca-py` to `[project.optional-dependencies].incubator` and gate the 4 imports behind feature detection. Cross-ref PF-07 (flagged for P1-C1 / P1-C2). | `weekend-only` |
| L5 | [pyproject.toml:45](../../../pyproject.toml#L45) | `matplotlib` is declared under `backtest` extras but imported by exactly one file: [vectorbt_orb.py](../../../argus/backtest/vectorbt_orb.py). If that file is retired (P1-E2 M5 scenario), matplotlib becomes dead. | None today. | Recheck once P1-E2 decisions land. | `safe-during-trading` |

---

## COSMETIC Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| C1 | [.env.example:21-25](../../../.env.example#L21-L25) | **`APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` fallback env-var names** (read by `backtest/data_fetcher.py:714-715, 749-750`) are undocumented. `.env.example` only mentions `ALPACA_API_KEY` / `ALPACA_SECRET_KEY`. | Mildly confusing for operators who have legacy alpaca-py environment layouts (APCA_ is the alpaca-py default naming). | Add one-line comment in `.env.example` after line 25: `# Alternate names also supported: APCA_API_KEY_ID, APCA_API_SECRET_KEY (alpaca-py default convention)` | `safe-during-trading` |
| C2 | [scripts/test_databento_scanner.py](../../../scripts/test_databento_scanner.py), `test_ibkr_bracket_lifecycle.py`, `test_ibkr_order_lifecycle.py`, `test_position_management_lifecycle.py`, `test_time_stop_eod.py` | Five files in `scripts/` named `test_*.py` are manual diagnostic runners, NOT pytest tests. Not auto-discovered (testpaths is `tests/`) so no functional issue, but the naming is misleading. | Minor confusion. A new contributor might assume they run under pytest. | Rename to `diagnose_*.py` (matches the pattern already established by `scripts/diagnose_databento.py`, `diagnose_feed.py`, `diagnose_live_streaming.py`) OR `verify_*.py`. | `safe-during-trading` |
| C3 | [pyproject.toml:54-56](../../../pyproject.toml#L54-L56) | Pytest markers: only `slow` registered. Elsewhere in the codebase `@pytest.mark.asyncio` is used pervasively (auto mode handles it) but no other custom markers are registered — however, the project uses `-n auto` (xdist) without a registered marker, and test-selection tools like `-m "not slow"` could benefit from an `integration` / `unit` split. | Minor — no warnings spam today. | Consider adding `integration` and `unit` markers for test-selection precision. Optional. | `safe-during-trading` |

---

## Positive Observations

1. **Pydantic v2 discipline is complete.** Zero `.dict()` v1-shape calls in `argus/`. All config uses `Pydantic BaseModel` consistently (DEC-032). This is rare — many projects in their 10th+ sprint still have v1 rot.
2. **Env-var resolution is declarative via config.** `api_key_env_var` / `heartbeat_url_env` / `alert_webhook_url_env` YAML fields feed `os.getenv(...)`. This lets operators re-map env-var names without code changes and centralizes the secret-name registry. Exemplary config hygiene.
3. **Frontend dep currency is excellent.** React 19.2, TypeScript 5.9, Vite 7.3, Vitest 4.0, Tailwind 4.2 — no lib lags by a major version. Correct d3-submodule imports (not full `d3`) for tree-shakeability. `package-lock.json` committed.
4. **`.gitignore` is defense-in-depth.** Double-covers DBs (`*.db` + `/data/`), explicitly excludes `secrets.yaml`/`credentials.yaml` on top of the `.env` rule, and excludes sprint-runner runtime artifacts. Verified: all 8 live SQLite DBs plus DuckDB WAL files are excluded at both levels.
5. **Single autouse fixture is narrowly scoped and well-explained.** The `clear_orb_family_exclusion_set` fixture has a full docstring explaining the class-variable hazard. This is the right documentation density for state-leak mitigations.
6. **Scripts directory has zero dead imports and zero mis-pathed DB targets.** The `_pycache__`/`ibc`/`sprint_runner` subdirs aside, all 25 top-level Python scripts either import from live modules or are self-contained one-shots. All DB paths verified against DEC-345's separation.
7. **Pydantic-settings was deliberately not adopted.** DEC-032 chose plain `BaseModel` over `BaseSettings`; the implementation is consistent with that decision — no creep.
8. **No secret leakage risk detected.** Placeholder values only in `.env.example`; no committed `.env`, no committed SQLite DBs, no committed Parquet cache.

---

## Statistics

- Files deep-read: 7 (`pyproject.toml`, `argus/ui/package.json`, `.env.example`, `.gitignore`, `.gitmodules`, `tests/conftest.py`, `scripts/resolve_sweep_symbols.py` segments)
- Files skimmed: ~15 (config YAMLs for env-var references, 5 `scripts/test_*.py` headers, 5 `scripts/*.py` headers, vectorbt_orb.py header, data_fetcher.py env-var sections)
- Total findings: **18** (0 critical, 9 medium, 5 low, 3 cosmetic, 1 positive-only section)
- Safety distribution: **12 safe-during-trading** / **5 weekend-only** / **1 read-only-no-fix-needed** (none in primary list — all tagged per table) / 0 deferred-to-defs
- Estimated Phase 3 fix effort: **~3 sessions**
  - **Session α (safe-during-trading, weekday):** M1 (upper bounds) + M4 (plotly extras) + M5 (dead vectorbt/sklearn) + M7 (uv.lock) + M8 (SQL params) + M9 (public symbol-count API) + C1 + C2 → ~1 session (all config/docs/scripts)
  - **Session β (weekend-only):** M2 (python-jose → PyJWT) + M3 (passlib retirement) → 1 session (auth refactor + 6 import rewrites + fixture touch-ups)
  - **Session γ (safe-during-trading, can stack with α):** M6 (GitHub Actions minimal CI) → ~0.5 session depending on matrix appetite
- DEFs to open: **0** (monthly-cron pair already tracked as DEF-097 + DEF-162).
