## PERT Estimate: <Replace with Project/Feature Title>

### Metadata

- **Date**: <YYYY-MM-DD>
- **Scope**: <Brief scope statement>
- **Unit**: <hours|days> (default hours; assume 1 day = 8 hours unless noted)
- **Single Source of Truth (Confluence)**: [<Confluence page title>](<https://confluence.example.com/x/XXXX>)
- **Assumptions**:
  - ...
  - ...
- **Dependencies**:
  - ...
  - ...
- **Risks/Unknowns**:
  - ...
  - ...

### Task Breakdown

Provide task-level estimates with optimistic (O), most likely (M), and pessimistic (P) durations. Compute expected duration `E = (O + 4M + P) / 6` and standard deviation `σ = (P − O) / 6`.

| ID | Task | O | M | P | E = (O + 4M + P) / 6 | σ = (P − O) / 6 | Notes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | <Task name> |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |  |
| ... |  |  |  |  |  |  |  |

> Tip: Keep tasks small enough that O/M/P are reasoned estimates rather than guesses.

### Rollup

- **Sum of expected durations (ΣE)**: <fill>
- **Sum of variances (Σσ²) on critical path**: <fill>
- **Overall σ (sqrt(Σσ²))**: <fill>

#### Confidence Ranges

Report ranges for the chosen scope (e.g., critical path or whole set with caveats):

- **~68% (±1σ)**: <E_total − σ, E_total + σ>
- **~95% (±2σ)**: <E_total − 2σ, E_total + 2σ>
- **~99.7% (±3σ)**: <E_total − 3σ, E_total + 3σ>

> Caveat: PERT assumes approximate normality and independence; use judgment, especially with shared resources and correlated risks.

### Notes and Rationale

Capture the why behind significant O/M/P spreads, key assumptions, and any constraints that could impact delivery.

