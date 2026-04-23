# Historical Integration Tests

Tests moved here cover architecture from ARGUS sprints 2-5 and earlier.
They are preserved as regression guards against re-breaking resolved
behaviors, but are NOT expected to exercise currently-active code paths.

- Sprint 2-4b: pre-IBKR-dominance broker wiring
- Sprint 5: HealthMonitor v1 (superseded by current HealthMonitor tests
  at `tests/core/test_health_monitor*.py`)
- Sprint 13: broker-selection branching + IBKR instantiation smoke tests
  (broker instantiation/connection coverage superseded by
  `tests/execution/test_ibkr_broker.py`; BrokerSource/IBKRConfig enum
  + default assertions retained as thin regression guards)

New integration tests should NOT be added here. This directory is
frozen; if a test fails due to legitimate architecture changes, either
update the test or mark it `@pytest.mark.skip(reason="Superseded by...")`.
