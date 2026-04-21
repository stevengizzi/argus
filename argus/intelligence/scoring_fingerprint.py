"""Scoring-context fingerprint for CounterfactualTracker.

Produces a 16-char SHA-256 hex fingerprint over the currently-active
QualityEngine configuration (weights + thresholds + risk tiers). Used to
tag shadow positions so PromotionEvaluator can separate pre-fix and
post-fix data when the quality pipeline changes.

Mirrors the two existing fingerprint patterns in ARGUS:
- ``compute_parameter_fingerprint()`` in ``argus.strategies.patterns.factory``
  (detection-params fingerprint for PatternModule variants).
- ``config_fingerprint`` column on the ``trades`` table (DEC-383).

Same algorithm: SHA-256 of canonical JSON (sort_keys=True, compact
separators), first 16 hex characters.

NOTE on module location: per FIX-01-catalyst-db-quality-pipeline, the
target sub-package ``argus/intelligence/quality/`` was not created
because ``quality_engine.py`` lives directly under ``argus/intelligence/``.
Module placed here at ``argus/intelligence/scoring_fingerprint.py`` for
operator to optionally reshuffle later.
"""
from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argus.intelligence.config import QualityEngineConfig


def compute_scoring_fingerprint(quality_config: QualityEngineConfig) -> str:
    """Return a 16-character hex SHA-256 fingerprint of the scoring config.

    Serialises weights + thresholds + risk_tiers as canonical JSON
    (sorted keys, compact separators) and hashes. Identical algorithm
    to the detection-params pattern in
    ``argus.strategies.patterns.factory.compute_parameter_fingerprint``.

    Args:
        quality_config: The live QualityEngineConfig instance whose
            scoring context should be fingerprinted.

    Returns:
        First 16 hex characters of the SHA-256 digest.
    """
    payload = {
        "weights": quality_config.weights.model_dump(mode="json"),
        "thresholds": quality_config.thresholds.model_dump(mode="json"),
        "risk_tiers": quality_config.risk_tiers.model_dump(mode="json"),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
