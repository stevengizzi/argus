# Template: Sprint Spec

Fill in all sections. Leave nothing as TBD -- if something is genuinely unknown,
that is a signal to do more discovery before committing to the sprint.

---

    # Sprint [N]: [Title]

    ## Goal
    [1-2 sentences: what this sprint delivers and why it matters]

    ## Scope

    ### Deliverables
    [Numbered list of concrete, testable deliverables]
    1. [Deliverable with clear definition of done]
    2. [Deliverable with clear definition of done]

    ### Acceptance Criteria
    For each deliverable, the specific conditions that must be true for it to be complete:
    1. [Deliverable 1]:
       - [Criterion A -- testable assertion]
       - [Criterion B -- testable assertion]
    2. [Deliverable 2]:
       - [Criterion A]
       - [Criterion B]

    ### Performance Benchmarks (if applicable)
    | Metric | Target | Measurement Method |
    |--------|--------|--------------------|
    | [e.g., Response time] | [e.g., < 200ms p95] | [e.g., load test with k6] |

    ### Config Changes (if applicable)
    List every new or modified config field introduced by this sprint.
    For each field, provide the YAML path and the corresponding Pydantic model
    field name. Verify the names match exactly -- Pydantic silently ignores
    unrecognized fields and uses defaults.

    | YAML Path | Pydantic Model | Field Name | Default |
    |-----------|---------------|------------|---------|
    | [e.g., ai.model] | [e.g., AIConfig] | [e.g., model] | [e.g., "claude-opus-4-5-20251101"] |

    If no config changes, write "No config changes in this sprint."

    ## Dependencies
    - [What must be true before this sprint starts]
    - [What external systems, APIs, or data must be available]
    - [What previous sprint work this builds on]

    ## Relevant Decisions
    - DEC-[N]: [brief description -- how it constrains this sprint]
    - DEC-[N]: [brief description]

    ## Relevant Risks
    - RSK-[N]: [brief description -- how it affects this sprint]

    ## Session Count Estimate
    [N] sessions estimated. [Brief rationale for the estimate.]
    [If frontend sessions with visual review items: +0.5 sessions budgeted
    for visual-review fix contingency.]
