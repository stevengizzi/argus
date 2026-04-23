# Dependency Management — Python Lockfiles

> **Landed:** IMPROMPTU-05 (2026-04-23, DEF-180).
> See `CLAUDE.md` DEF-180 entry for historical context (pre-lockfile reproducibility gap).

ARGUS uses `uv` to produce two lockfiles that pin the full transitive Python
dependency tree. CI installs from the lockfile; local developers can do the
same to get a byte-reproducible environment.

## Lockfile Inventory

| File | Purpose | Extras |
|------|---------|--------|
| `requirements.lock` | Runtime-only resolution for production deploys | none |
| `requirements-dev.lock` | Full dev/test resolution — what CI installs | `dev`, `backtest` |

The `[project.optional-dependencies]` section in `pyproject.toml` currently
defines `dev` (pytest/ruff/httpx) and `backtest` (numpy/matplotlib/scipy/
seaborn/plotly). The `incubator` extra, if ever added, is intentionally NOT
included in `requirements-dev.lock` — DEF-178 tracks moving `alpaca-py`
there.

## Installation

### Local development (recommended)

```bash
pip install -r requirements-dev.lock
pip install -e . --no-deps
```

The `--no-deps` flag is important: the lockfile is authoritative. The
editable install only registers the `argus` package path so `import argus`
resolves to the working tree.

### Production (runtime-only)

```bash
pip install -r requirements.lock
pip install -e . --no-deps
```

## Regeneration

Regenerate both lockfiles whenever `pyproject.toml` dependencies change —
adding a new dep, bumping a version range, or adding/removing an extra.

```bash
# Install uv if you don't have it
pip install uv

# Regenerate runtime lockfile
uv pip compile pyproject.toml -o requirements.lock

# Regenerate dev lockfile (dev + backtest extras)
uv pip compile --extra dev --extra backtest pyproject.toml -o requirements-dev.lock
```

Commit both lockfiles in the same commit as the `pyproject.toml` change.
Never hand-edit lockfile entries to force a version — change the range in
`pyproject.toml` and regenerate.

## CI Integration

`.github/workflows/ci.yml` installs from `requirements-dev.lock`:

```yaml
- name: Install dependencies from lockfile
  run: |
    python -m pip install --upgrade pip
    pip install -r requirements-dev.lock
    pip install -e . --no-deps
```

The `cache-dependency-path` on `actions/setup-python` is set to
`requirements-dev.lock` so the pip cache invalidates when the lockfile
changes.

## Reproducibility

`uv pip compile` is deterministic given the same `pyproject.toml` and the
same PyPI index state. If two operators regenerate the lockfile at
different times and get different output, it means:

1. A transitive dependency published a new release between the two runs.
   (Expected behaviour — the lockfile resolves to the newest compatible
   version.)
2. The runs were on different Python versions. `requires-python = ">=3.11"`
   in `pyproject.toml` still allows `>=3.12`-only transitive deps to be
   selected on 3.12 runners. Regenerate on Python 3.11 to match CI.

## Cross-References

- `CLAUDE.md` DEF-180 — historical context for why this was introduced
- `.github/workflows/ci.yml` — CI install step
- `pyproject.toml` — source of truth for direct dependencies
