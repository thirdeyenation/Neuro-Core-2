# Neuro Core 2 Continuity Guide

## Mission

Neuro Core 2 is an evidence-first, scoped memory capability for Agent Zero v2.8+. Its core promise is explainable retrieval: selected memories expose scoring factors; memory lifecycle is explicit; meaningful operations are auditable. This document is the authoritative status and continuation guide. Use existing architecture, product, benchmark, and competition documents for detail.

## What is implemented

- Framework-independent domain: immutable `Memory`, `Scope`, lexical/trust ranking, and factor-level retrieval explanations.
- Lifecycle policy: `unreviewed`, `validated`, `disputed`, and terminal `superseded`; superseded memories are excluded, not deleted.
- Append-only in-process activity ledger.
- `MemoryStore` port with in-memory and SQLite adapters.
- `NeuroCore2Service` composing capture, retrieve, validation, storage, and activity events.
- Standard-library tests for scope isolation, lifecycle, storage, SQLite persistence, and service flow.
- Agent Zero plugin shell, installer, and `NeuroCore2Capture`, `NeuroCore2Retrieve`, and `NeuroCore2Validate` tools.
- Verified Agent Zero host run on 2026-08-05 with plugin identity `neuro_core_2`, capture/retrieve/validate/supersede flow, cross-scope isolation, and writable SQLite store evidence. See `/a0/usr/plugins/neuro_core_2/docs/validation/2026-08-05-agent-zero-host-validation.md`.
- Verified post-restart persistence check on 2026-08-05: database survived restart, remained writable, and capture/retrieve worked after restart. See `/a0/usr/plugins/neuro_core_2/docs/validation/2026-08-05-post-restart-persistence-check.md`.
- Durable activity-event persistence now stored in SQLite alongside memories, with a tiny read path exposed through `NeuroCoreService.list_activity(...)`.
- `NeuroCoreService.list_activity(...)` is now covered by a unit test for scope-filtered in-memory activity access.
- SQLite schema compatibility is now protected by a regression test that exercises restart plus additive activity writes.

## What is not proven

- Performance, concurrency, security, benchmark, or competition claims. Do not claim these as completed.
- Durable cross-session audit querying surface beyond the service method.
- Tool configuration sourced from `default_config.yaml` instead of hardcoded paths.

## Non-negotiable decisions

1. Keep Agent Zero imports in `/a0/usr/plugins/neuro_core_2/`; root modules must remain host-independent.
2. Treat `Scope(project, agent)` as a hard isolation boundary.
3. Preserve inspectable ranking factors when replacing lexical retrieval with semantic/vector retrieval.
4. Preserve superseded records for audit; do not retrieve them.
5. Add storage backends behind `MemoryStore`, not directly in the service.
6. Keep explicit tool scope inputs unless a documented host-session mapping is proven.

## Known debt

- Ranking is a correctness baseline, not semantic retrieval.
- SQLite opens per invocation and has no migration or concurrency strategy.
- Tool code should load the plugin-local database path from `default_config.yaml` at runtime.
- Activity events are now durably appended when the underlying store supports it, but cross-invocation audit querying is not yet exposed as a tool.
- The installer copies files but does not validate imports, discovery, permissions, or manifest behavior.
- There is no authorization policy, input-size control, observability, or evaluation harness.

## Completion sequence

1. Run `python /a0/usr/plugins/neuro_core_2/scripts/verify.py`.
2. In the target Agent Zero container, run `python /a0/usr/plugins/neuro_core_2/install.py`, reload plugins, and record the exact Agent Zero version/commit.
3. Smoke-test capture, retrieve, and validate with one project/agent scope; confirm superseded records disappear from retrieval.
4. Resolve all host-contract and deployment-path findings before feature expansion.
5. Make tool configuration real and persist activity events.
6. Add schema migrations, concurrency/failure policy, and a benchmark harness before production or competition claims.

## Change discipline

Every behavior change needs a `unittest` update. Record lifecycle, ranking, or public-contract decisions in `/a0/usr/plugins/neuro_core_2/docs/decisions/`. Preserve constructor and port compatibility or provide a deliberate migration. Keep implemented, planned, and unverified behavior clearly separated.

## Onboarding for new contributors

Before touching code:
1. Read this file, `/a0/usr/plugins/neuro_core_2/docs/ARCHITECTURE.md`, and `/a0/usr/plugins/neuro_core_2/docs/AGENT_ZERO_CONTRACT_BASELINE.md`.
2. Run the tests locally and ensure they pass.
3. Reproduce the host validation steps in `/a0/usr/plugins/neuro_core_2/docs/validation/` using the recorded Agent Zero version/commit.

When proposing changes:
- State the objective and why it matters.
- Identify affected modules, tests, and ADRs.
- Call out any assumptions, risks, and downstream effects.
- Preserve backward compatibility or provide a migration note.

## Acceptance evidence

For deployment work, record the Agent Zero version/commit, install command, plugin discovery result, capture/retrieve/validate inputs and outputs, database path, test output, and deviations in a dated issue, PR, or `/a0/usr/plugins/neuro_core_2/docs/validation/` artifact.
