# Benchmark Plan

## Purpose

The competition entry must demonstrate better memory outcomes, not merely more features. Benchmarks compare a no-memory baseline, a basic retrieval baseline where available, and Neuro Core 2 under the same controlled scenarios.

## Required scenarios

### B1 — Prior decision recall

A multi-step task contains a prior decision with a reason and a later request that depends on it. Success requires correct retrieval, attribution to the source decision, and no unsupported inference.

### B2 — Episode continuity

An earlier task episode includes investigation, implementation, and a deferred question. A later task must recover the episode, avoid repeating completed investigation, and surface the deferred question.

### B3 — Contradiction safety

Two scoped memories contain incompatible claims. Success requires a visible conflict signal, source comparison, correct distinction between detection and resolution, and an auditable user action.

### B4 — Operator explanation

A reviewer receives a retrieved item and must answer what it is, why it appeared, what scope it belongs to, how trustworthy/fresh it is, and how to correct it.

### B5 — Degraded operation

A dependency, index, or policy is unavailable/disabled. Success requires an explicit degraded-state signal, no fabricated retrieval claim, and a recoverable operator path.

## Metrics

| Metric | Definition | Initial target |
|---|---|---:|
| Attributed recall | Correct retrieval with valid source attribution | ≥ 90% |
| Unsupported-memory claims | Claims of memory use/influence without trace evidence | 0 |
| Episode continuity | Scenarios where prior work is correctly recovered and redundant work avoided | ≥ 80% |
| Retrieval explanation coverage | Displayed retrieved items with complete explanation data | 100% |
| Conflict handling completeness | Conflicts with both sources, rationale, and an auditable outcome | 100% |
| Operator inspection success | Reviewers correctly answer all five B4 questions | ≥ 85% |
| Degraded-state honesty | Failures presented without false-success claims | 100% |

## Evidence requirements

Each benchmark run records fixture version, configuration/policy version, execution trace, retrieval explanations, UI evidence where applicable, results, and deviations. A pass cannot be based only on logs or a verbal claim.

## Release gate

The project may claim competitive superiority only after all five scenarios pass in the defined environment, targets are met across repeated runs, accessibility checks pass for the Workbench, and the results are reproducible from documented fixtures.