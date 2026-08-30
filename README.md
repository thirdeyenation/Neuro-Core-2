# Neuro Core 2

Evidence-first, scoped, auditable memory for Agent Zero v2.8+.

This project implements the **Neuro Core 2** plugin: capture, retrieval, and
validation tools backed by SQLite, with explicit memory lifecycle and audit.

---

## Quick start (newcomer path)

1. **Read the project entry documents in this order:**
   - `README.md` (this file) — purpose, scope, non-goals, and where to go next.
   - `docs/ARCHITECTURE.md` — component boundaries and data flow.
   - `docs/PROJECT_CONTINUITY.md` — current state, known debt, change discipline.
   - `docs/AGENT_ZERO_CONTRACT_BASELINE.md` — host contract and validation checklist.
2. **Locate the runtime plugin source** at `/a0/usr/plugins/neuro_core_2/`.
   This is the authoritative code path. The project root contains only
   documentation and the Agent Zero Project control plane (`.a0proj/`).
3. **Review validation evidence** indexed by `docs/validation/README.md`.
4. **Review durable decisions** in `docs/decisions/` before proposing changes.

---

## What is implemented

- Framework-independent domain: immutable `Memory`, `Scope`, lexical/trust
  ranking, and factor-level retrieval explanations.
- Lifecycle policy: `unreviewed`, `validated`, `disputed`, and terminal
  `superseded`; superseded memories are excluded from retrieval, not deleted.
- Append-only in-process activity ledger.
- `MemoryStore` port with in-memory and SQLite adapters.
- `NeuroCoreService` composing capture, retrieve, validation, storage, and
  activity events.
- Standard-library tests for scope isolation, lifecycle, storage, SQLite
  persistence, and service flow.
- Agent Zero plugin (`neuro_core_2`) with `NeuroCore2Capture`,
  `NeuroCore2Retrieve`, and `NeuroCore2Validate` tools.
- Verified Agent Zero host run on 2026-08-05 with plugin identity
  `neuro_core_2`, capture/retrieve/validate/supersede flow, cross-scope
  isolation, and writable SQLite store evidence. See
  `docs/validation/2026-08-05-agent-zero-host-validation.md`.
- Verified post-restart persistence check on 2026-08-05: database survived
  restart, remained writable, and capture/retrieve worked after restart. See
  `docs/validation/2026-08-05-post-restart-persistence-check.md`.
- Durable activity-event persistence in SQLite alongside memories, with a
  tiny read path via `NeuroCoreService.list_activity(...)`.
- `NeuroCoreService.list_activity(...)` covered by a unit test for
  scope-filtered in-memory activity access.
- SQLite schema compatibility protected by a regression test that exercises
  restart plus additive activity writes.
- Lifecycle hook and extension integration: `hooks.py` implements `register_plugin` (plugin metadata: name=`neuro_core_2`, version=`0.1.0`, tools=`[NeuroCore2Capture, NeuroCore2Retrieve, NeuroCore2Validate]`), `on_plugin_load` (service initialization from `default_config.yaml`), and `on_plugin_activate` (database accessibility check, startup validation, activation logging); `extensions/__init__.py` registers a `SessionLifecycleExtension` at `agent_init` that appends a `session_initialized` `ActivityEvent`. Verified in-process only — host-level firing against a real Agent Zero host is not yet verified.
- Inverted-term retrieval index: a `memory_terms` table (schema version 2)
  is maintained on capture and used as a pure candidate pre-filter before
  domain scoring. Tokenization is exactly `text.lower().split()`;
  scoring, ranking, and the inspectable-factors explanation contract are
  unchanged.
- Bounded retrieval results: `NeuroCore2Retrieve` returns at most
  `max_results` results (default 100, configurable via `max_results` in
  `default_config.yaml`; the optional `max_results` tool argument
  overrides the config value for a single call). The cap is applied AFTER
  scoring and sorting. When the full match count exceeds the cap, the
  payload includes `count_exceeded: true` and `total_matches: <int>` so
  callers can distinguish truncation from exhaustion — silent truncation
  is prohibited.
- Authorization policy: a five-layer minimal authorization model
  (caller-context binding, tool-layer scope check, service-layer scope
  check, memory-bound scope check for validate, authorization audit with
  denial reason) enforces `Scope(project, agent)` isolation at the
  tool-invocation level. Verified by unit and integration tests. This is
  a minimal baseline with explicit non-claims (not a security boundary,
  not authentication, not production-grade); the maturity limit
  ("authorization is unproven") remains in Project Instructions §1. See
  `docs/AGENT_ZERO_CONTRACT_BASELINE.md` "Authorization contract" and
  `docs/decisions/0007-authorization-policy.md`.

---

## What is not proven

- Performance, concurrency, security, benchmark, or competition claims.
  Do not assert these as completed.
- Durable cross-session audit querying surface beyond the service method.
- Tool configuration sourced from `default_config.yaml` instead of
  hardcoded paths (design intent; implementation may still be evolving).
- Actual Agent Zero host lifecycle firing (the real framework calling `on_plugin_load`/`on_plugin_activate`/`register_extension` as part of its own plugin loading sequence) is not exercised. Only in-process code-path verification was performed.

---

## Non-negotiable decisions

1. Keep Agent Zero imports in `plugins/neuro_core_2/`; root modules must
   remain host-independent.
2. Treat `Scope(project, agent)` as a hard isolation boundary.
3. Preserve inspectable ranking factors when replacing lexical retrieval
   with semantic/vector retrieval.
4. Preserve superseded records for audit; do not retrieve them.
5. Add storage backends behind `MemoryStore`, not directly in the service.
6. Keep explicit tool scope inputs unless a documented host-session mapping
   is proven.

---

## Known debt

- Ranking is a correctness baseline, not semantic retrieval.
- SQLite opens per invocation and has no migration or concurrency strategy.
- Tool code should load the plugin-local database path from
  `default_config.yaml` at runtime.
- Activity events are durably appended when the underlying store supports
  it, but cross-invocation audit querying is not yet exposed as a tool.
- The installer copies files but does not validate imports, discovery,
  permissions, or manifest behavior.
- There is no input-size control, observability, or evaluation harness.
- Authorization is implemented as a minimal baseline (five-layer model per
  ADR-0007) with explicit non-claims (not a security boundary, not
  authentication, not production-grade) and the maturity limit ("authorization
  is unproven") preserved in Project Instructions §1. See
  `docs/AGENT_ZERO_CONTRACT_BASELINE.md` "Authorization contract" and
  `docs/decisions/0007-authorization-policy.md`.
- Lifecycle integration code is implemented, but host-level firing (real Agent Zero framework load/activate/agent_init invocation) remains unverified.

---

## Environment variables

**No environment variable is currently required** to install, configure,
or run Neuro Core 2. A read-only inspection of the runtime plugin source
(`/a0/usr/plugins/neuro_core_2/`) for `os.environ`, `getenv`, and
`environ[...]` references returned no matches. All configuration is read
from the plugin-local `default_config.yaml` at
`/a0/usr/plugins/neuro_core_2/default_config.yaml`. If a future change
introduces an environment-variable prerequisite, it must be documented
here and in `docs/AGENT_ZERO_CONTRACT_BASELINE.md` before being required.

---

## Dependencies

The runtime plugin source has **no third-party Python dependencies**.
A read-only inspection of `/a0/usr/plugins/neuro_core_2/` for `import`
statements confirmed only standard-library modules are imported by
production code (`sqlite3`, `json`, `dataclasses`, `datetime`, `pathlib`,
`typing`, `hashlib`, `uuid`, `re`, `os`, `sys`, `collections`, `abc`,
`functools`, `itertools`, `threading`, `unittest`, `tempfile`).

**Development tooling dependency:** the git pre-commit hook at
`scripts/hooks/pre-commit` requires **PyYAML 6.0.3** (third-party) to
validate YAML parseability of staged files. This dependency is needed
only for contributors who install the hook locally; it is not required
to install, configure, or run the plugin itself. Install with:

```bash
pip install 'PyYAML==6.0.3'
```

The hook's six unit tests (`tests/test_precommit_yaml_hook.py`) also
require PyYAML. If a future change introduces a runtime dependency, it
must be documented here and in `docs/AGENT_ZERO_CONTRACT_BASELINE.md`
before being required.

---

## Repository layout

```text
/a0/usr/projects/neuro_core_2/
├── README.md                              # this file (project-root entry)
├── docs/
│   ├── ARCHITECTURE.md                    # component boundaries
│   ├── PROJECT_CONTINUITY.md              # current state, debt, discipline
│   ├── AGENT_ZERO_CONTRACT_BASELINE.md    # host contract & checklist
│   ├── validation/
│   │   └── README.md                      # index of validation evidence
│   └── decisions/
│       └── ADR-001-record-format.md       # durable decision records
└── .a0proj/                               # Agent Zero Project control plane
    ├── instructions/                      # project instructions & schemas
    ├── team/                              # workflow state & work items
    ├── decision_log/                      # non-negotiable decisions log
    └── notepad_temp/                      # non-authoritative scratch
```

The runtime plugin source lives at `/a0/usr/plugins/neuro_core_2/` and
contains the actual code, tests, installer, and runtime docs. The project
root contains only the newcomer-facing documentation and the Agent Zero
Project control plane.

---

## Change discipline

Every behavior change needs a `unittest` update. Record lifecycle,
ranking, or public-contract decisions in `docs/decisions/`. Preserve
constructor and port compatibility or provide a deliberate migration.
Keep implemented, planned, and unverified behavior clearly separated.

---

## Acceptance evidence

For deployment work, record the Agent Zero version/commit, install
command, plugin discovery result, capture/retrieve/validate inputs and
outputs, database path, test output, and deviations in a dated issue,
PR, or `docs/validation/` artifact.
