# Template: Specification by Contradiction

This document defines what Sprint [N] explicitly does NOT do. It prevents scope
creep during implementation and gives the Tier 2 reviewer clear boundaries to check.

---

    # Sprint [N]: What This Sprint Does NOT Do

    ## Out of Scope
    These items are related to the sprint goal but are explicitly excluded:
    1. [Item]: [Why it is excluded -- e.g., "deferred to Sprint N+1", "not needed for MVP"]
    2. [Item]: [Why]

    ## Edge Cases to Reject
    The implementation should NOT handle these cases in this sprint:
    1. [Edge case]: [Expected behavior -- e.g., "return error", "ignore", "log and skip"]
    2. [Edge case]: [Expected behavior]

    ## Scope Boundaries
    - Do NOT modify: [list of files, modules, or systems that must not be touched]
    - Do NOT optimize: [areas where correctness is sufficient, performance is deferred]
    - Do NOT refactor: [areas that may look like they need cleanup but are out of scope]
    - Do NOT add: [features or capabilities that are tempting but not in the spec]

    ## Interaction Boundaries
    - This sprint does NOT change the behavior of: [list of interfaces, APIs, or contracts]
    - This sprint does NOT affect: [list of components that should be unaware of the changes]

    ## Deferred to Future Sprints
    | Item | Target Sprint | DEF Reference |
    |------|--------------|---------------|
    | [item] | Sprint [N+X] or Unscheduled | DEF-[N] |
