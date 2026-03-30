# Sprint 28.75: Review Context

## Sprint Overview
Impromptu fix sprint addressing operational and UI issues found in the
March 30, 2026 market session debrief. Two sessions: backend operational
fixes (S1) then frontend bug fixes + UI improvements (S2).

## DEF Items Addressed
| DEF | Description | Session |
|-----|-------------|---------|
| DEF-111 | Trail stops not firing in live session (config timing — verify) | S1 |
| DEF-112 | Flatten-pending orders hang indefinitely | S1 |
| DEF-113 | "flatten already pending" log spam | S1 |
| DEF-114 | "IBKR portfolio snapshot missing" log spam | S1 |
| DEF-115 | Closed positions tab capped at 50 | S2 |
| DEF-116 | TodayStats win rate 0% | S2 |
| DEF-117 | Trades page stats freeze + filter bug (subsumes DEF-102) | S2 |
| DEF-118 | Avg R missing from Trades page | S2 |
| DEF-119 | Open positions P&L column + colored exit | S2 |
| DEF-120 | VixRegimeCard fills viewport | S2 |

## Sprint-Level Regression Checklist
| Check | How to Verify |
|-------|---------------|
| Order Manager bracket invariant (DEC-117) | grep test_bracket in tests, passing |
| Flatten-pending guard (DEC-363) | Verify guard still prevents duplicates |
| Stop resubmission cap (DEC-372) | Verify cap still triggers flatten |
| Reconciliation safety (DEC-369) | Verify broker-confirmed never auto-closed |
| All 8 Command Center pages load | Visual navigation check |
| Full test suite passes | pytest + vitest |

## Sprint-Level Escalation Criteria
- ESCALATE: Any changes to bracket order creation, risk manager, event bus,
  strategy base class, or config loading architecture
- ESCALATE: Any changes to reconciliation logic beyond log rate-limiting
- CONCERNS: Trail fix requires changes to >3 files
- CONCERNS: Frontend stats endpoint duplicates existing computation logic
