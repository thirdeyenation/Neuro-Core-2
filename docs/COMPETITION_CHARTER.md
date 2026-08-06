# Neuro Core 2 Competition Charter

## Entry

Neuro Core 2: scoped, auditable memory for Agent Zero v2.8+.

## Problem

Agents need memory that is:
- **Scoped**: isolated by `(project, agent)` so different workstreams do not bleed together.
- **Explainable**: retrieval decisions expose why items were selected.
- **Auditable**: meaningful operations are logged and can be inspected later.
- **Durable**: memory and audit survive restarts and remain consistent.

## Solution

Neuro Core 2 provides:
- Capture, retrieval, and validation tools scoped by `(project, agent)`.
- Explicit memory lifecycle: `unreviewed` → `validated`/`disputed` → `superseded`.
- Factor-level retrieval explanations (lexical match, trust, scope, etc.).
- Durable SQLite storage and append-only activity logging.
- A minimal, test-backed plugin for Agent Zero (`neuro_core_2`).

## Claims

Neuro Core 2 claims:
1. **Explainable retrieval**: selected memories expose scoring factors.
2. **Explicit lifecycle**: `unreviewed`, `validated`, `disputed`, `superseded`; superseded memories are excluded from retrieval but preserved for audit.
3. **Durable storage**: SQLite database survives restart and remains writable; schema compatibility is protected by a regression test.
4. **Audit**: append-only activity events are stored durably alongside memories.
5. **Scoped isolation**: `Scope(project, agent)` is a hard boundary; memories and events are not leaked across scopes.

## Evidence

- Verified host run on 2026-08-05 with plugin identity `neuro_core_2`, capture/retrieve/validate/supersede flow, cross-scope isolation, and writable SQLite store evidence. See `docs/validation/2026-08-05-agent-zero-host-validation.md`.
- Post-restart persistence check on 2026-08-05: database survived restart, remained writable, and capture/retrieve worked after restart. See `docs/validation/2026-08-05-post-restart-persistence-check.md`.
- Schema compatibility regression test in `test_sqlite_store.py` that exercises restart plus additive activity writes.
- ADRs documenting:
  - Product and architecture (`docs/decisions/0001-product-and-architecture.md`),
  - Plugin identity and integration strategy (`0002-plugin-identity-and-integration-strategy.md`),
  - Neuro Core 2 identity and host validation (`0003-neuro-core-2-identity-and-host-validation.md`),
  - Audit durability and migration policy (`0004-audit-durability-and-migration-policy.md`),
  - Concurrency and migration policy (`0005-concurrency-and-migration-policy.md`),
  - Implementation rules for SQLite durability (`0006-implementation-rules-for-sqlite-durability.md`).

## Out of scope

For this competition entry, the following are explicitly out of scope:
- Performance, concurrency, security, or benchmark claims.
- Semantic/vector retrieval (future work; must preserve factor explanations when added).
- Authorization, input-size controls, or observability.

## Identity

- Plugin folder: `plugins/neuro_core_2/`.
- Manifest name: `neuro_core_2`.
- Tools: `NeuroCore2Capture`, `NeuroCore2Retrieve`, `NeuroCore2Validate`.
- Database: `plugins/neuro_core_2/neuro_core_2.db`.

## Evaluation criteria alignment

Neuro Core 2 is designed to demonstrate:
- **Correctness**: scope isolation, lifecycle, retrieval ranking, and audit behavior are tested and validated.
- **Explainability**: retrieval results include factors; audit events are inspectable.
- **Robustness**: persistence and restart behavior are verified; schema changes are guarded by tests.
- **Clarity**: documentation distinguishes implemented, planned, and unverified behavior.

## Future work

After the core slice is stable and host-contract findings are resolved:
- Add a benchmark harness for latency, result quality, and storage growth.
- Introduce schema migrations and a concurrency/failure policy.
- Extend audit into a first-class query surface (e.g. tool or UI for activity inspection).
- Evaluate semantic/vector retrieval as an optional ranking backend.
