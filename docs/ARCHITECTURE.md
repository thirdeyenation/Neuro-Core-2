# Architecture

## Architectural thesis

Neuro Core 2 is designed around an evidence path rather than a storage path. Every material system action must be representable as an event, tied to a scoped memory record, and explainable to an operator.

## Components

| Component | Responsibility | Boundary |
|---|---|---|
| Capture gateway | Creates validated memory candidates from approved inputs | Does not choose retrieval results |
| Memory registry | Stores canonical records, provenance, lifecycle state, and schema version | Does not render UI |
| Relationship service | Maintains typed, directed evidence relationships | Does not silently infer resolution |
| Episode service | Builds and audits task narratives from memory records | Does not alter source content |
| Retrieval planner | Produces scoped candidates and reason codes | Does not claim decision influence |
| Ranking service | Applies transparent, configurable factor scoring | Emits factor-level explanations |
| Activity ledger | Appends scoped operation events | Is not the canonical memory store |
| Review service | Manages validation, contradiction, and resolution state | Preserves history |
| Integration adapter | Implements independently verified Agent Zero contracts | Keeps framework details out of core domain logic |
| Memory Workbench | Presents activity, context, review, controls, and semantic navigation | Does not invent state |

## Canonical record

A canonical memory record will include: stable ID; schema version; content and human-readable title; source/provenance; project, agent, and namespace scope; memory type; importance, confidence, stability, and freshness; validation state; episode/reflection lineage; relationship references; lifecycle timestamps; and policy/evidence references.

## Activity event envelope

Every material event uses a versioned envelope: event ID, event type, timestamp, actor, scope, targets, outcome, evidence references, policy version, and optional human-readable summary. Events are append-only.

## Dependency direction

`Integration adapter → application services → domain model → persistence ports`

The workbench consumes read models and event projections. Framework-specific code must not leak into domain records, benchmark fixtures, or UI state.

## Reliability requirements

- Idempotency for capture and lifecycle actions.
- Explicit failure events; no swallowed operation failure.
- Atomic persistence boundaries for a record and its declared indexes.
- Isolated test namespaces and deterministic fixtures.
- Schema migrations that preserve prior evidence and surface compatibility state.

## Integration gate

No Agent Zero adapter is implemented until this repository has recorded the exact framework contract, the integration surface is covered by a test, and a safe runtime smoke scenario has been defined.