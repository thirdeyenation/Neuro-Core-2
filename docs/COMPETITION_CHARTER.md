# Neuro Core 2 Competition Charter

## Entry

Neuro Core 2: scoped, auditable memory for Agent Zero v2.8+.

## Claims

- Explainable retrieval: selected memories expose scoring factors.
- Explicit lifecycle: `unreviewed`, `validated`, `disputed`, `superseded`.
- Durable storage: SQLite with restart survival and additive writes.
- Audit: append-only activity events stored durably.

## Evidence

- Verified host run on 2026-08-05 with plugin identity `neuro_core_2`.
- Post-restart persistence check on 2026-08-05.
- Schema compatibility regression test.
- ADRs documenting product/architecture, plugin identity, host validation, audit durability, concurrency/migration, and SQLite implementation rules.

## Out of scope

- Performance, concurrency, security, or benchmark claims.
- Semantic/vector retrieval (future work).

## Identity

- Plugin folder: `plugins/neuro_core_2/`.
- Manifest name: `neuro_core_2`.
- Tools: `neuro_core_2_capture`, `neuro_core_2_retrieve`, `neuro_core_2_validate`.
