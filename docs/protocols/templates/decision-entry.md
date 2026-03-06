# Template: Decision Log Entry

Use this format for every decision logged in the Decision Log.
Copy this template and fill in all fields.

---

    **DEC-[NNN]:** [Decision Title]
    **Date:** [YYYY-MM-DD]
    **Sprint:** [Sprint number, or "Bootstrap" / "Discovery" / "Impromptu X.Y"]

    **Decision:**
    [What was decided. Be specific and unambiguous.]

    **Alternatives Rejected:**
    1. [Alternative A]: [Why it was rejected]
    2. [Alternative B]: [Why it was rejected]
    (Write "None considered" only if this was truly the only viable option.)

    **Rationale:**
    [Why this choice was made, given the constraints. Include any empirical
    evidence, performance data, or prior experience that informed the decision.]

    **Constraints:**
    [What made this decision necessary. External requirements, dependencies,
    timeline pressure, technical limitations, etc.]

    **Supersedes:** [DEC-NNN if this replaces a previous decision, or "N/A"]

    **Cross-References:**
    - Related decisions: [DEC-NNN, DEC-NNN]
    - Related risks: [RSK-NNN]
    - Related deferred items: [DEF-NNN]
    (Write "None" if this decision is standalone.)

---

## Guidance

- Log decisions at the time they are made, not after. Deferred logging
  leads to forgotten rationale.
- "Alternatives Rejected" is the most valuable field for preventing future
  regressions. A future session that sees a design choice and thinks "this
  should be done differently" can check the DEC log to see if the alternative
  was already considered and rejected.
- Mark inferred decisions (from retrofit/archaeology) with [INFERRED] after
  the rationale. These should be confirmed or corrected by the developer.
- When a decision is superseded, update the old entry to note:
  "Superseded by DEC-[NNN] on [date]"
