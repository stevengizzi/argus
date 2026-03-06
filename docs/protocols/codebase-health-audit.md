# Protocol: Codebase Health Audit

**Context:** Claude.ai conversation
**Frequency:** Every 4-6 sprints
**Output:** Health assessment, technical debt inventory, roadmap adjustments

---

## When to Use
- At the cadence specified above (every 4-6 sprints)
- When technical debt feels like it is slowing development
- Before a major new phase that will build on the existing codebase
- When onboarding a new contributor who needs to understand code quality

This is NOT tied to any sprint. It is a systemic check.

## Conversation Structure

### 1. Architectural Coherence

Provide Claude with the architecture document and ask it to survey the repo:

"Survey this codebase against our architecture document. Identify:
1. Components that have drifted from the documented architecture
2. Emergent patterns that are not documented
3. Inconsistencies in how similar problems are solved across the codebase
4. Dead code or unused modules
5. Coupling that was not intended by the architecture"

### 2. Test Coverage Analysis

"Analyze the test suite:
1. What is the overall coverage picture? (not just line count -- which critical paths are tested?)
2. Are there important code paths with no test coverage?
3. Are tests meaningful or are any trivial/tautological?
4. Is the test suite maintainable? (brittle tests, excessive mocking, slow tests?)
5. Are there patterns in what gets tested vs. what does not?"

### 3. Dependency Hygiene

"Review the project dependencies:
1. Are any dependencies outdated by more than one major version?
2. Are any dependencies unmaintained or deprecated?
3. Are there redundant dependencies (two libraries doing the same thing)?
4. Are there dependencies we are barely using that could be replaced with simple code?
5. Are there known security vulnerabilities?"

### 4. Naming and Convention Consistency

"Evaluate naming and convention consistency:
1. Are file naming patterns consistent?
2. Are function/method naming conventions consistent?
3. Are error handling patterns consistent?
4. Are logging patterns consistent?
5. Is there a style that has evolved organically that should be documented as a rule?"

### 5. Deferred Items Debt

"Review the deferred items tracker alongside the codebase:
1. Are deferred items accumulating faster than they are being resolved?
2. Are any deferred items becoming urgent (blocking new work, creating risk)?
3. Should any deferred items be promoted to sprint scope?
4. Should any deferred items be cancelled (no longer relevant)?"

### 6. Technical Debt Inventory

"Based on everything above, produce a prioritized technical debt inventory:

| Item | Severity | Impact on Velocity | Recommended Action | Target Sprint |
|------|----------|-------------------|-------------------|---------------|

Severity: HIGH (blocking or degrading work) / MEDIUM (slowing but not blocking) / LOW (cosmetic)
Impact: How much faster would we move if this were resolved?"

---

## Output

The conversation should produce:
1. Technical debt inventory (prioritized)
2. Revised .claude/rules/ entries for any conventions that should be enforced
3. Specific items to add to the sprint roadmap
4. Updated DEF entries for new or re-prioritized deferred items
5. Architecture document updates (if drift was found)
