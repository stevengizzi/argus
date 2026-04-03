"""Generic pattern factory and parameter fingerprint utility.

Provides lazy-import-based construction of any PatternModule from its
Pydantic StrategyConfig, and deterministic fingerprinting of detection
parameters for experiment tracking and registry keying.

Public API:
    get_pattern_class(name)              -- resolve name to class
    extract_detection_params(config, cls) -- extract params via PatternParam
    build_pattern_from_config(config)    -- construct pattern from config
    compute_parameter_fingerprint(...)   -- deterministic hash of params
"""

from __future__ import annotations

import hashlib
import importlib
import json
import logging
from typing import Any

from argus.core.config import StrategyConfig
from argus.strategies.patterns.base import PatternModule, PatternParam

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pattern registry
# ---------------------------------------------------------------------------

# Maps PascalCase class name → (module_path, class_name).
# Imports are deferred — patterns are only loaded when first requested.
_PATTERN_REGISTRY: dict[str, tuple[str, str]] = {
    "BullFlagPattern": (
        "argus.strategies.patterns.bull_flag",
        "BullFlagPattern",
    ),
    "FlatTopBreakoutPattern": (
        "argus.strategies.patterns.flat_top_breakout",
        "FlatTopBreakoutPattern",
    ),
    "DipAndRipPattern": (
        "argus.strategies.patterns.dip_and_rip",
        "DipAndRipPattern",
    ),
    "HODBreakPattern": (
        "argus.strategies.patterns.hod_break",
        "HODBreakPattern",
    ),
    "GapAndGoPattern": (
        "argus.strategies.patterns.gap_and_go",
        "GapAndGoPattern",
    ),
    "ABCDPattern": (
        "argus.strategies.patterns.abcd",
        "ABCDPattern",
    ),
    "PreMarketHighBreakPattern": (
        "argus.strategies.patterns.premarket_high_break",
        "PreMarketHighBreakPattern",
    ),
    "MicroPullbackPattern": (
        "argus.strategies.patterns.micro_pullback",
        "MicroPullbackPattern",
    ),
    "VwapBouncePattern": (
        "argus.strategies.patterns.vwap_bounce",
        "VwapBouncePattern",
    ),
}

# Convenience snake_case aliases → PascalCase class name.
_SNAKE_CASE_ALIASES: dict[str, str] = {
    "bull_flag": "BullFlagPattern",
    "flat_top_breakout": "FlatTopBreakoutPattern",
    "dip_and_rip": "DipAndRipPattern",
    "hod_break": "HODBreakPattern",
    "gap_and_go": "GapAndGoPattern",
    "abcd": "ABCDPattern",
    "premarket_high_break": "PreMarketHighBreakPattern",
    "micro_pullback": "MicroPullbackPattern",
    "vwap_bounce": "VwapBouncePattern",
}

# Module-level cache — avoids repeated importlib lookups.
_CLASS_CACHE: dict[str, type[PatternModule]] = {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_pattern_class(name: str) -> type[PatternModule]:
    """Resolve a pattern name to the concrete PatternModule class.

    Accepts either the PascalCase class name (e.g., ``"BullFlagPattern"``)
    or a snake_case convenience alias (e.g., ``"bull_flag"``).  The resolved
    class is cached after the first call.

    Args:
        name: Pattern class name or snake_case alias.

    Returns:
        The PatternModule subclass.

    Raises:
        ValueError: If *name* does not match any registered pattern.
    """
    class_name = _SNAKE_CASE_ALIASES.get(name, name)

    if class_name not in _PATTERN_REGISTRY:
        known = sorted(set(list(_PATTERN_REGISTRY.keys()) + list(_SNAKE_CASE_ALIASES.keys())))
        raise ValueError(
            f"Unknown pattern '{name}'. Known patterns: {known}"
        )

    if class_name in _CLASS_CACHE:
        return _CLASS_CACHE[class_name]

    module_path, attr_name = _PATTERN_REGISTRY[class_name]
    module = importlib.import_module(module_path)
    cls: type[PatternModule] = getattr(module, attr_name)
    _CLASS_CACHE[class_name] = cls
    return cls


def extract_detection_params(
    config: StrategyConfig,
    pattern_class: type[PatternModule],
) -> dict[str, Any]:
    """Extract detection parameter values from a Pydantic config object.

    Instantiates *pattern_class* with its constructor defaults, calls
    ``get_default_params()`` to discover the set of ``PatternParam`` names,
    then reads the corresponding field values from *config*.

    A WARNING is logged (and the param is skipped) if a ``PatternParam``
    name is not present on *config* — this provides forward compatibility
    for patterns that gain new parameters before the config is updated.

    Args:
        config: Strategy Pydantic config instance supplying parameter values.
        pattern_class: The PatternModule subclass to introspect.

    Returns:
        ``dict`` mapping each ``PatternParam.name`` to the value found on
        *config*.
    """
    default_instance = pattern_class()
    params: list[PatternParam] = default_instance.get_default_params()

    result: dict[str, Any] = {}
    for param in params:
        if hasattr(config, param.name):
            result[param.name] = getattr(config, param.name)
        else:
            logger.warning(
                "PatternParam '%s' not found on config class '%s'. "
                "This param will be skipped (pattern may define a parameter "
                "not yet present in the Pydantic config).",
                param.name,
                type(config).__name__,
            )

    return result


def build_pattern_from_config(
    config: StrategyConfig,
    pattern_name: str | None = None,
) -> PatternModule:
    """Construct a PatternModule instance from a Pydantic config.

    Resolution order for the pattern class:
    1. *pattern_name* argument, if provided.
    2. ``config.pattern_class`` field, if present on the config object.
    3. Infer from the config class name by replacing the ``Config`` suffix
       with ``Pattern`` (e.g., ``BullFlagConfig`` → ``BullFlagPattern``).

    Detection parameters are extracted via PatternParam introspection —
    no parameter names are hardcoded in this function.

    Args:
        config: Strategy Pydantic config instance supplying parameter values.
        pattern_name: Optional explicit pattern name (PascalCase or
            snake_case).  When omitted the name is inferred from *config*.

    Returns:
        A fully constructed PatternModule instance.

    Raises:
        ValueError: If the resolved pattern name is unknown.
    """
    resolved_name = _resolve_pattern_name(config, pattern_name)
    pattern_class = get_pattern_class(resolved_name)
    detection_params = extract_detection_params(config, pattern_class)
    return pattern_class(**detection_params)


def compute_parameter_fingerprint(
    config: StrategyConfig,
    pattern_class: type[PatternModule],
    exit_overrides: dict[str, Any] | None = None,
) -> str:
    """Compute a deterministic 16-character hex fingerprint of detection params.

    Only detection parameters (those declared in ``get_default_params()``)
    contribute to the hash by default.  Base ``StrategyConfig`` fields such as
    ``strategy_id``, ``name``, and ``operating_window`` are excluded.

    When *exit_overrides* is non-empty, the fingerprint is computed over a
    namespaced structure so that two variants differing only in exit
    configuration receive distinct fingerprints.  Passing ``None`` or ``{}``
    produces the **same hash** as the detection-only variant (backward compat).

    The algorithm — detection-only (exit_overrides is None or empty):
    1. Extract detection params via :func:`extract_detection_params`.
    2. Serialise to canonical JSON with sorted keys and compact separators.
    3. Compute SHA-256 of the UTF-8 encoded JSON string.
    4. Return the first 16 hex characters.

    The algorithm — with exit overrides (exit_overrides is non-empty):
    1. Extract detection params as above.
    2. Build namespaced dict:
       ``{"detection": {sorted detection params}, "exit": {sorted exit overrides}}``.
    3. Serialise to canonical JSON (sort_keys=True, compact separators).
    4. SHA-256 → first 16 hex characters.

    The result is deterministic across process restarts: identical inputs
    always produce the same fingerprint.

    Args:
        config: Strategy Pydantic config instance.
        pattern_class: The PatternModule class defining the parameter space.
        exit_overrides: Optional dict of exit management overrides. When None
            or empty, the hash is identical to the detection-only variant.

    Returns:
        First 16 hex characters of the SHA-256 hash.
    """
    detection_params = extract_detection_params(config, pattern_class)

    if exit_overrides:
        payload: dict[str, object] = {
            "detection": detection_params,
            "exit": exit_overrides,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    else:
        canonical = json.dumps(detection_params, sort_keys=True, separators=(",", ":"))

    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return digest[:16]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_pattern_name(
    config: StrategyConfig,
    pattern_name: str | None,
) -> str:
    """Determine the pattern class name from args or config.

    Resolution order:
    1. *pattern_name* argument (if not None).
    2. ``config.pattern_class`` field (if present on the config).
    3. Replace the ``"Config"`` suffix with ``"Pattern"`` in the config
       class name (e.g., ``BullFlagConfig`` → ``BullFlagPattern``).

    Args:
        config: Strategy config instance.
        pattern_name: Optional explicit name override.

    Returns:
        Resolved pattern class name string.
    """
    if pattern_name is not None:
        return pattern_name

    if hasattr(config, "pattern_class"):
        return str(getattr(config, "pattern_class"))

    return type(config).__name__.replace("Config", "Pattern")
