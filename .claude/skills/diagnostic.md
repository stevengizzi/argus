# Skill: Diagnostic-First Bug Investigation

## Trigger
Invoke this skill when:
- A bug has survived 2 or more fix attempts, OR
- The implementation prompt explicitly requests diagnostic-first approach, OR
- The Tier 2 review recommended diagnostic-first for a recurring issue

## Philosophy
Do NOT touch application code until you understand the bug. Build an isolated
reproduction first. Let the evidence guide the fix.

## Procedure

### Step 1: Document the Bug
Before writing any code, create a diagnostic log entry:

```
## Diagnostic Log

**Bug ID:** [reference from issue tracker or sprint spec]
**Symptom:** [what the user/developer observes]
**Expected behavior:** [what should happen instead]

**Previous fix attempts:**
1. [description] — Result: [why it failed or regressed]
2. [description] — Result: [why it failed or regressed]

**Hypotheses:**
1. [theory about root cause]
2. [alternative theory]
3. [alternative theory]
```

### Step 2: Build Isolated Reproduction
Create a standalone test file (NOT in the main test suite yet) that:
- Reproduces the bug with minimal dependencies
- Has a clear PASS/FAIL assertion
- Does NOT modify any application code
- File naming convention: `diagnostic_[bug-id].test.[ext]`

Run the test. Verify it FAILS in the expected way.

If the test does NOT fail as expected: your understanding of the bug is wrong.
Revise hypotheses and rebuild the reproduction. Do NOT proceed until you have
a failing test that matches the reported symptom.

### Step 3: Narrow the Cause
Using the diagnostic test as your probe:
- Add logging or assertions to narrow which component/layer is responsible
- Identify the EXACT line(s) where behavior diverges from expectation
- Update your hypotheses based on evidence

Record your findings:
```
**Root cause identified:**
- Component: [file/module]
- Line(s): [specific lines]
- Mechanism: [what's actually happening and why]
- Why previous fixes failed: [explanation]
```

### Step 4: Design the Fix
Based on diagnostic findings, design a fix. Before implementing:
- Verify the fix addresses the root cause, not just the symptom
- Check that the fix doesn't violate any "do not modify" constraints
- Consider whether the fix could affect other components
- If the fix is non-trivial, describe it before coding it

### Step 5: Implement and Verify
1. Implement the fix
2. Run the diagnostic test — it MUST now pass
3. Run the full test suite — no regressions
4. If the diagnostic test is a good regression test, move it into the main test suite
5. If it's too specific or slow, keep it as a reference but don't add it to CI

### Step 6: Document in Close-Out
In the session close-out, explicitly note:
- This was a diagnostic-first investigation
- Root cause found (vs. the symptom that was reported)
- Why previous fix attempts failed
- The diagnostic test that now encodes this knowledge
