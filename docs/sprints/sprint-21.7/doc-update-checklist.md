# Sprint 21.7 — Doc Update Checklist

After all sessions complete and doc-sync skill runs:

1. [ ] CLAUDE.md — Add FMP_API_KEY to required environment variables section
2. [ ] config/scanner.yaml — Comments updated; scanner_type: "fmp" is the
       production default; "static" is for replay/backtest
3. [ ] decision-log.md — DEC-258 and DEC-259 already logged; add implementation
       cross-reference: "Implemented Sprint 21.7, session 1-3"
4. [ ] docs/03_ARCHITECTURE.md — Scanner section: update to reflect hybrid
       architecture (FMP primary for pre-market, Databento for streaming).
       Add FMPScannerSource to scanner component list.
5. [ ] docs/project-knowledge.md — Update current state: "FMP Scanner active
       (Sprint 21.7). Dynamic symbol selection via gainers/losers/actives."
6. [ ] docs/sprint-history.md — Add Sprint 21.7 entry
