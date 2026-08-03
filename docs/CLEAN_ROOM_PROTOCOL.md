# Clean-Room Protocol

## Purpose

Neuro Core 2 is intentionally separate from the existing Neuro Core plugin. Separation protects both repositories from accidental file crossover and ensures that this entry earns its design through independent reasoning and implementation.

## Allowed inputs

- Public or independently verified Agent Zero framework contracts.
- Product requirements, user workflows, benchmarks, and design principles written for this repository.
- High-level observations of competitor behavior and publicly observable interfaces.
- Original analysis, code, documentation, tests, fixtures, and UX created for this repository.

## Prohibited inputs

- Copying source code, tests, prompts, configuration, documentation text, commit messages, or assets from the existing Neuro Core repository.
- Importing from, vendoring, or depending on the existing Neuro Core repository.
- Reusing its private data, sidecars, memory stores, fixtures, or runtime namespaces.
- Presenting behavior as independently verified when it was inferred from a competitor artifact.

## Implementation rules

1. All repository writes occur in `thirdeyenation/Neuro-Core-2`.
2. New package, module, API, event, and UI names are created here and documented before use.
3. Agent Zero framework-facing behavior is preceded by an independent contract check and a local ADR.
4. Tests and fixtures use isolated namespaces and synthetic data only.
5. Every imported dependency is documented with its purpose and license compatibility before release.

## Comparative integrity

Competitor analysis may identify an outcome gap, such as missing retrieval explanation or poor contradiction review. It must not dictate a copied implementation. Comparative claims are written as measurable outcomes, not unverified assertions about another repository.

## Violation response

If a potential crossover is identified, stop the affected work, document the concern, replace the affected material with an independently designed version, and reassess any benchmark claim that depended on it.