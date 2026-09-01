# Neuro Core 2 Architecture

Neuro Core 2 is a scoped, auditable memory capability for Agent Zero
v2.8+. It provides capture, retrieval, and validation tools backed by
SQLite, with explicit memory lifecycle and activity logging.

This document describes the **component boundaries** of the system. It
is the authoritative newcomer entry point for architecture questions.

---

## Components

The runtime plugin source lives at `/a0/usr/plugins/neuro_core_2/`. The
following components are defined there:

- **Domain** (`neuro_core_2.py`): `Memory`, `Scope`, and retrieval with
  factor-level explanations.
- **Lifecycle** (`memory_lifecycle.py`): states `unreviewed`, `validated`,
  `disputed`, `superseded`.
- **Storage port** (`memory_store.py`): `MemoryStore` interface.
- **SQLite adapter** (`sqlite_store.py`): durable `MemoryStore`
  implementation.
- **Activity ledger** (`activity_ledger.py`): append-only event log.
- **Service** (`neuro_service.py`): composes capture, retrieve,
  validate, store, and activity.
- **Caller identity** (`caller_identity.py`): plugin-side caller-identity
  derivation (active-project with audited default-scope fallback and
  `identity_source` markers) and Layer 2 scope binding with the
  `agent:None` sentinel, per ADR-0008.
- **Plugin** (`plugins/neuro_core_2/`): Agent Zero tools
  `NeuroCore2Capture`, `NeuroCore2Retrieve`, `NeuroCore2Validate`.

---

### Authorization state note (2026-08-31)

> **Current state (2026-09-01):** the redesigned authorization mechanism
> is **implemented** in the plugin and covered by the test suite.
> Enforcement is **ACTIVE** — `AUTHORIZATION_ENFORCEMENT_ACTIVE` is
> `True` in all three tools (capture.py:35, retrieve.py:35,
> validate.py:41). Host-level flag-enabled behavior has been **validated
> by VAL** (validation-report.yaml rev 1, decision: pass,
> required_level: host; 5/5 ARC Condition 5 scenarios on the real
> dispatch path; raw probe evidence under
> `.a0proj/notepad_temp/val/20260901T0910-AUTHZ-REENABLE-VALIDATION/`).
> The earlier integration-level pass (10/10 scenarios) is retained as
> historical context. Binding is not authentication; authorization
> remains unproven as a security mechanism, and authorization-event
> evidence (`identity_source`, `denial_reason`) lives on the in-memory
> ActivityLedger and is not durably persisted across restart
> (ADR-0004/ADR-0006).

---

## Data flow

1. Tools derive caller identity plugin-side from host inputs that exist
   at dispatch (`caller_identity.py`), bind the requested
   `Scope(project, agent)` against it, and call `NeuroCoreService` with
   the bound scope. Enforcement is flag-gated
   (`AUTHORIZATION_ENFORCEMENT_ACTIVE`, currently `True` — active in all
   three tools; one-flag rollback to `False` restores the unenforced
   functional state).
2. Service writes to `MemoryStore` and appends to `ActivityLedger`.
3. Retrieval ranks candidates lexically and by trust, returning factors.
4. Superseded memories remain stored but are excluded from retrieval.

---

## Persistence

- SQLite database path is configured in
  `/a0/usr/plugins/neuro_core_2/default_config.yaml` as
  `plugins/neuro_core_2/neuro_core_2.db`.
- Activity events are durably stored alongside memories.

### Schema versioning and migrations

- Schema version is tracked with `PRAGMA user_version`.
- `migrations.py` owns `PRAGMA user_version`. No other code path may
  read, set, or interpret `user_version` as a schema marker; the
  migration runner is the only component that may modify it, and it
  does so only inside a committed migration transaction. Other code
  that needs the schema version calls `SQLiteStore.schema_version()`
  (an internal API, not part of the `MemoryStore` port and not exposed
  through any tool).
- `run_migrations(connection)` runs on every `SQLiteStore` open. It
  reads `user_version`, applies pending migrations in ascending order
  inside `BEGIN IMMEDIATE` transactions, and bumps `user_version` only
  after each migration commits. It is idempotent by construction: a
  second run is a no-op. Fresh databases (version 0, no tables) and
  legacy databases (version 0, tables already present) both converge on
  version 1 through an additive baseline migration that preserves all
  existing rows.
- Databases with `user_version` newer than the code's latest known
  version are rejected on open with a clear error, preventing
  accidental downgrade corruption.

### Concurrency model

- Neuro Core 2 provides a **single-writer serialization guarantee**
  only. Every write and every migration runs inside `BEGIN IMMEDIATE`,
  which acquires the SQLite write lock up front, and a bounded
  `PRAGMA busy_timeout` (default **5000 ms**) makes a writer wait for
  the lock instead of failing immediately.
- The busy timeout is configurable through the
  `busy_timeout_ms` constructor argument of `SQLiteStore`; the default
  is the module constant `DEFAULT_BUSY_TIMEOUT_MS = 5000` in
  `sqlite_store.py`.
- **No multi-writer, distributed, or performance guarantees are made.**
  Concurrent writers are serialized by SQLite; this is not a
  multi-writer database, is not distributed, and no throughput or
  latency claims are implied or supported.

---

## Boundaries

- Core modules (`neuro_core_2.py`, `memory_lifecycle.py`,
  `memory_store.py`, `sqlite_store.py`, `activity_ledger.py`,
  `neuro_service.py`) are host-independent.
- All Agent Zero integration lives under
  `/a0/usr/plugins/neuro_core_2/`.
- Scope isolation is strict: `Scope(project, agent)` is a hard boundary.

---

## Non-goals (for now)

- Semantic/vector retrieval (replaceable behind the ranking port).
- Multi-writer, distributed, or performance concurrency guarantees.
  The only concurrency guarantee is single-writer serialization via
  `BEGIN IMMEDIATE` plus `busy_timeout`.
- Input-size controls or observability. (Authorization is no longer a
  non-goal: a derivation-based authorization model is implemented per
  `docs/decisions/0008-authorization-policy.md` (ADR-0008, superseding
  ADR-0007 in full), with explicit non-claims — not a security boundary,
  not caller authentication, not production-grade — and the maturity
  limit "authorization is unproven" preserved in Project Instructions
  §1. Enforcement is ACTIVE (`AUTHORIZATION_ENFORCEMENT_ACTIVE = True`
  in all three tools) and host-level flag-enabled behavior is validated
  by VAL (validation-report.yaml rev 1, decision: pass,
  required_level: host, 5/5 ARC Condition 5 scenarios); authorization
  remains unproven as a security mechanism.)
- Benchmark or competition claims.

---

## Environment variables

**No environment variable is currently required.** All configuration is
read from the plugin-local `default_config.yaml`. See `README.md` for
the full environment-variable policy.

---

## References

- `README.md` — project entry point.
- `docs/PROJECT_CONTINUITY.md` — current state and known debt.
- `docs/AGENT_ZERO_CONTRACT_BASELINE.md` — host contract.
- `docs/decisions/ADR-001-record-format.md` — durable decision records.
