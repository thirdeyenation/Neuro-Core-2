# Architecture Decision Records

This directory (`docs/decisions/`) contains Architecture Decision
Records (ADRs) for Neuro Core 2. ADRs document durable architectural
decisions and their rationale.

---

## Index

- [ADR-001: Record Format for Architecture Decision Records](ADR-001-record-format.md)
  — defines the format and lifecycle of ADRs in this directory.
- [ADR-002: Ratification of Structural Fixes (Tool Identity and SqliteStore Export)](ADR-002-ratification-of-structural-fixes.md)
  — retroactive ratification of the tool-identity and SqliteStore-export
  fixes performed under WI-2026-08-16-RATIFY-STRUCTURAL-FIXES.

---

## Legacy ADRs (pre-rename, retained for history)

The following ADRs predate the ADR-001 record format and the
`neuro_core_2` rename. They are retained for historical reference and
have not been migrated to the current format:

- `0001-product-and-architecture.md`
- `0002-plugin-identity-and-integration-strategy.md`
- `0003-neuro-core-2-identity-and-host-validation.md`
- `0004-audit-durability-and-migration-policy.md`
- `0005-concurrency-and-migration-policy.md`
- `0006-implementation-rules-for-sqlite-durability.md`

---

## How to add a new ADR

1. Create a new file named `NNNN-<short-title>.md` in
   `docs/decisions/`, where `NNNN` is the next available
   zero-padded sequence number.
2. Follow the format defined in
   [ADR-001-record-format.md](ADR-001-record-format.md).
3. Add a link to the new ADR in this index.

---

## References

- `README.md` — project entry point.
- `docs/ARCHITECTURE.md` — component boundaries.
- `docs/PROJECT_CONTINUITY.md` — current state and known debt.
- `.a0proj/decision_log/decisions.md` — non-negotiable decisions log
  maintained by ORC.
