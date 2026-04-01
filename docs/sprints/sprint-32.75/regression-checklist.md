# Sprint 32.75: Regression Checklist

## Test Suite Gates
- [ ] All pre-existing pytest tests pass (baseline: 4,405 + Sprint 32.5 additions)
- [ ] All pre-existing Vitest tests pass (baseline: 700, 1 known failure in GoalTracker.test.tsx)
- [ ] No new test failures introduced

## Strategy Pipeline Invariants
- [ ] All 12 strategies generate signals during their operating windows (verify via evaluation telemetry)
- [ ] Signal → Quality → Risk Manager → Order Manager pipeline unchanged
- [ ] ORB family mutual exclusion behavior unchanged (configurable via `orb_family_mutual_exclusion`)
- [ ] Shadow mode routing for shadow-configured strategies unchanged
- [ ] Overflow routing to CounterfactualTracker unchanged (new threshold: 60 instead of 30)

## Event Bus & WebSocket Invariants
- [ ] `/ws/v1/live` continues delivering position updates, trade events, and health data
- [ ] `/ws/v1/observatory` pipeline updates and tier transitions unchanged
- [ ] `/ws/v1/ai/chat` streaming responses unchanged
- [ ] New `/ws/v1/arena` channel does not interfere with existing channels
- [ ] Event Bus FIFO delivery order preserved (no priority changes)

## Order Management Invariants
- [ ] Bracket order lifecycle (entry → stop + targets) unchanged
- [ ] EOD flatten triggers at 3:50 PM ET and closes all positions
- [ ] Startup zombie cleanup unchanged
- [ ] Flatten-pending guard (DEC-363) unchanged
- [ ] Broker-confirmed positions never auto-closed by reconciliation (DEC-369)
- [ ] Stop resubmission cap and emergency flatten unchanged (DEC-372)
- [ ] Post-reconnect delay (new) does not block order operations or EOD flatten

## Frontend Page Invariants
- [ ] Dashboard renders correctly in phone, tablet, and desktop layouts (minus removed cards)
- [ ] Orchestrator page renders all strategy cards with correct status
- [ ] Performance page all 6 tabs functional
- [ ] Trades page filter and detail panel functional
- [ ] Pattern Library page shows all 12 strategies with correct badges
- [ ] Debrief page functional
- [ ] System page functional
- [ ] Observatory page 3D views functional

## Config Validation
- [ ] `overflow.broker_capacity: 60` correctly read by OverflowConfig Pydantic model
- [ ] No silently ignored YAML keys (Pydantic `extra="forbid"` or explicit validation)
- [ ] Pre-live transition checklist updated with new broker_capacity value note

## Data Integrity
- [ ] Trade records continue to include strategy_id, quality_grade, config_fingerprint
- [ ] MFE/MAE tracking on managed positions unchanged
- [ ] Counterfactual position tracking unchanged
- [ ] Learning Loop auto-trigger on SessionEndEvent unchanged
- [ ] Evaluation telemetry SQLite writes unchanged
