# Competition Charter

## Mission

Build the most trustworthy memory capability for Agent Zero: a plugin that improves continuity across work while keeping memory behavior visible, attributable, controllable, and reversible.

## The competitor stance

A feature-rich memory plugin is not enough. The winning entry must prove that its memory changes real task performance while allowing a human to understand and intervene in that process. We optimize for trustworthy assistance, not storage volume, graph complexity, or dashboard breadth.

## Target users

- Operators who need agents to retain project context without silently steering work.
- Builders who need prior decisions, tasks, and episodes to be discoverable and attributable.
- Reviewers who need to inspect retrieval evidence, uncertainty, and changes to memory state.

## Product principles

1. **Evidence before assertion.** Never imply that a memory influenced a decision unless the evidence supports that claim.
2. **Explain by default.** Every material capture, retrieval, conflict, reflection, and resolution has an inspectable record.
3. **Human control without data loss.** Corrections preserve provenance and history; they do not silently rewrite the past.
4. **Episodes over fragments.** The product must preserve meaningful task narratives, not merely isolated embeddings.
5. **Progressive disclosure.** Normal users see concise signals; advanced users can inspect the full trace.
6. **Safe interoperability.** Public integration contracts are explicit, scoped, versioned, and independently tested.

## Non-goals for the first release

- Replacing Agent Zero's framework-owned memory implementation.
- Framework-wide shared primitives before the local plugin loop is proven.
- Opaque always-on LLM classification or contradiction calls.
- A dashboard that reports activity without demonstrating task value.

## Winning criteria

The entry is ready to compete only when the benchmark plan is passed, the runtime path is testable in an isolated namespace, the user-facing explanation path is accessible, and all external claims can be traced to reproducible evidence.