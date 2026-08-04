# Neuro Core 2 Continuity Guide

## Mission

Neuro Core 2 is an evidence-first, scoped memory capability for Agent Zero v2.8+. Its core promise is explainable retrieval: selected memories expose scoring factors; memory lifecycle is explicit; meaningful operations are auditable. This document is the authoritative status and continuation guide. Use existing architecture, product, benchmark, and competition documents for detail.

## What is implemented

- Framework-independent domain: immutable `Memory`, `Scope`, lexical/trust ranking, and factor-level retrieval explanations.
- Lifecycle policy: `unreviewed`, `validated`, `disputed`, and terminal `superseded`; superseded memories are excluded, not deleted.
- Append-only in-process activity ledger.
- `MemoryStore` port with in-memory and SQLite adapters.
- `NeuroCoreService` composing capture, retrieve, validation, storage, and activity events.
- Standard-library tests for scope isolation, lifecycle, storage, SQLite persistence, and service flow.
- Agent Zero plugin shell, installer, and `NeuroCapture`, `NeuroRetrieve`, and `NeuroValidate` tools.

## What is not proven

- Plugin discovery or tool execution inside the target Agent Zero v2.8+ container.
- Filesystem permissions for `/a0/usr/plugins/neuro_core/neuro_core.db`.
- Performance, concurrency, security, benchmark, or competition claims. Do not claim these as completed.

## Non-negotiable decisions

1. Keep Agent Zero imports in `plugins/neuro_core/`; root modules must remain host-independent.
2. Treat `Scope(project, agent)` as a hard isolation boundary.
3. Preserve inspectable ranking factors when replacing lexical retrieval with semantic/vector retrieval.
4. Preserve superseded records for audit; do not retrieve them.
5. Add storage backends behind `MemoryStore`, not directly in the service.
6. Keep explicit tool scope inputs unless a documented host-session mapping is proven.

## Known debt

- Ranking is a correctness baseline, not semantic retrieval.
- SQLite opens per invocation and has no migration or concurrency strategy.
- Tool code hardcodes the database path rather than reading `default_config.yaml`.
- Activity events are not durable across tool invocations because each tool creates a service/ledger.
- The installer copies files but does not validate imports, discovery, permissions, or manifest behavior.
- There is no authorization policy, input-size control, observability, or evaluation harness.

## Completion sequence

1. Run `python scripts/verify.py`.
2. In the target Agent Zero container, run `python plugins/neuro_core/install.py`, reload plugins, and record the exact Agent Zero version/commit.
3. Smoke-test capture, retrieve, and validate with one project/agent scope; confirm superseded records disappear from retrieval.
4. Resolve all host-contract and deployment-path findings before feature expansion.
5. Make tool configuration real and persist activity events.
6. Add schema migrations, concurrency/failure policy, and a benchmark harness before production or competition claims.

## Change discipline

Every behavior change needs a `unittest` update. Record lifecycle, ranking, or public-contract decisions in `docs/decisions/`. Preserve constructor and port compatibility or provide a deliberate migration. Keep implemented, planned, and unverified behavior clearly separated.

## Acceptance evidence

For deployment work, record the Agent Zero version/commit, install command, plugin discovery result, capture/retrieve/validate inputs and outputs, database path, test output, and deviations in a dated issue, PR, or `docs/validation/` artifact.
