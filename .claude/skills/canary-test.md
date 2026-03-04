# Skill: Canary Tests

## Trigger
Run this BEFORE making any implementation changes, when the sprint spec or
implementation prompt includes pre-implementation tests (canary tests).

Canary tests encode design intent and "do not break" constraints as executable
assertions. They must pass both before AND after implementation.

## Pre-Conditions
- You have not yet modified any application code for this session
- You have the list of canary tests from the implementation prompt or sprint spec
- The codebase is in a clean state (no uncommitted changes)

## Procedure

### Step 1: Verify Clean State
Run the existing test suite. All tests must pass before you begin.
If any tests fail, STOP and report this in the close-out — do not proceed
with canary tests on top of a failing suite.

Record the baseline:
- Tests run: [count]
- Tests passed: [count]
- All passing: [YES/NO — if NO, stop here]

### Step 2: Write Canary Tests
For each canary test specified in the prompt:

1. Create the test in the appropriate test file/directory
2. The test should assert the CURRENT correct behavior (not the new behavior you are about to implement)
3. Name the test clearly: `test_canary_[what_it_protects]`
4. Add a comment explaining what design intent or constraint this test encodes, including the DEC reference if applicable

Example naming and commenting pattern:

    # Canary: [DEC-NNN] Users with expired tokens must receive 401, not 500
    # This test encodes the design intent from Sprint 4. Do not modify.
    def test_canary_expired_token_returns_401():
        ...

### Step 3: Run Canary Tests
Run the full test suite including your new canary tests.

All canary tests must PASS. They are encoding current behavior — if they fail,
either your test is wrong or the behavior has already regressed.

If a canary test fails:
- Investigate whether the behavior has already regressed
- If yes: flag in the close-out and STOP — this needs diagnosis before new work begins
- If no (your test was wrong): fix the test until it correctly asserts current behavior

### Step 4: Confirm Baseline
Record the new baseline with canary tests included:
- Previous test count: [count]
- Canary tests added: [count]
- New total: [count]
- All passing: YES

### Step 5: Proceed to Implementation
You may now begin the implementation work specified in the prompt.

After implementation is complete, run the full suite again.
ALL canary tests must still pass.

If any canary test fails after implementation:
- Your changes broke a protected invariant
- This is a FLAGGED condition in the close-out
- Do NOT rationalize the failure as "expected" or "the test needs updating"
- Either fix your implementation to preserve the invariant, or escalate for spec revision

### Step 6: Document in Close-Out
In the close-out report's Regression Checks section, include a row for each canary test:

| Check | Result | Notes |
|-------|--------|-------|
| Canary: [description] | [PASS/FAIL] | [details if FAIL] |

Also add to the Test Results section:
- Canary tests written: [count]
- Pre-implementation: ALL PASS
- Post-implementation: [ALL PASS / FAILURES: list which failed]
