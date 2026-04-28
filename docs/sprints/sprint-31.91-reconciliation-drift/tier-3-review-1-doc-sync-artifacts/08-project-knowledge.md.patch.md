# Doc-Sync Patch 8 — `docs/project-knowledge.md`

**Purpose:** Update the "Most-cited foundational decisions" list to point at DEC-386 as the most recent (instead of DEC-384), and update the Reference table's Latest-DEC pointer.

**Anchor verification (must hold before applying):**
- Line 228: `- DEC-383 (22 shadow variant fleet) · **DEC-384 (FIX-01: standalone overlay registry — \`_STANDALONE_SYSTEM_OVERLAYS\` extensible registry in \`argus/core/config.py\`, most recent)**`
- Line 253: `| \`docs/decision-log.md\` | All DEC entries with full rationale. Latest: DEC-384 (FIX-01, standalone overlay registry). |`

---

## Patch A — Update most-cited DEC list

### Find:

```
- DEC-383 (22 shadow variant fleet) · **DEC-384 (FIX-01: standalone overlay registry — `_STANDALONE_SYSTEM_OVERLAYS` extensible registry in `argus/core/config.py`, most recent)**
```

### Replace with:

```
- DEC-383 (22 shadow variant fleet) · DEC-384 (FIX-01: standalone overlay registry — `_STANDALONE_SYSTEM_OVERLAYS` extensible registry in `argus/core/config.py`) · **DEC-386 (Sprint 31.91 OCA-group threading + broker-only safety — 4-layer architecture closing ~98% of DEF-204's mechanism, Tier 3 verdict 2026-04-27, most recent)**
```

---

## Patch B — Update Reference table Latest-DEC pointer

### Find:

```
| `docs/decision-log.md` | All DEC entries with full rationale. Latest: DEC-384 (FIX-01, standalone overlay registry). |
```

### Replace with:

```
| `docs/decision-log.md` | All DEC entries with full rationale. Latest: DEC-386 (Sprint 31.91 OCA-group threading + broker-only safety, Tier 3 verdict 2026-04-27). |
```

---

## Application notes

- The "Most-cited foundational" list deliberately still mentions DEC-384 (just without the bold/`most recent` annotation) because DEC-384's standalone overlay registry remains active and frequently referenced. Only the "most recent" badge moves to DEC-386.
- The "Completed infrastructure" line at line 85 also mentions DEC-384's standalone overlay registry; that line is correct as-is and does NOT need updating (it's a feature inventory, not a "most recent" pointer).
- Two surgical replacements. No other lines in `project-knowledge.md` are touched.
