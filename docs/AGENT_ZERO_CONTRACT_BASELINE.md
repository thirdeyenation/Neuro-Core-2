# Agent Zero Contract Baseline

This document records the minimal contract Neuro Core 2 requires from
the Agent Zero host to operate correctly. It is the authoritative
newcomer entry point for the **install-plugin** onboarding journey.

---

## Plugin identity

- Plugin name in manifest: `neuro_core_2`.
- Plugin folder: `/a0/usr/plugins/neuro_core_2/`.
- Tools: `NeuroCore2Capture`, `NeuroCore2Retrieve`,
  `NeuroCore2Validate` (modules `neuro_core_2_capture`,
  `neuro_core_2_retrieve`, `neuro_core_2_validate`).

---

## File layout

The runtime plugin source lives at `/a0/usr/plugins/neuro_core_2/`:

- `plugin.yaml` — plugin manifest.
- `default_config.yaml` — plugin-local defaults.
- `install.py` — installer script.
- `hooks.py` — Agent Zero lifecycle hooks: `register_plugin` (registers plugin metadata: name=`neuro_core_2`, version=`0.1.0`, tools=`[NeuroCore2Capture, NeuroCore2Retrieve, NeuroCore2Validate]`), `on_plugin_load` (loads `default_config.yaml`, resolves `database_path`, constructs `SQLiteStore` and `NeuroCoreService`, registers the lifecycle extension), and `on_plugin_activate` (verifies database accessibility with `SELECT 1`, runs startup validation via `PRAGMA user_version`, logs activation status, returns a status dict).
- `extensions/` — lifecycle extension modules: `extensions/__init__.py` registers a functional `SessionLifecycleExtension` (subclass of `helpers.extension.Extension`) at the `agent_init` session-lifecycle point that appends an `ActivityEvent` (kind=`session_initialized`) to the Neuro Core 2 service ledger and store.
- `tools/` — tool implementations.
- `neuro_core_2.db` — SQLite database (created at runtime).

---

## Runtime expectations

- Plugin discovery loads `/a0/usr/plugins/neuro_core_2/plugin.yaml`.
- Tools are invoked with explicit `project` and optional `agent` scope
  arguments.
- Plugin-local config is read from
  `/a0/usr/plugins/neuro_core_2/default_config.yaml`.
- `hooks.py` registers plugin metadata (`neuro_core_2`, `0.1.0`, the three tools) via `register_plugin`, initializes the service from `default_config.yaml` via `on_plugin_load`, and verifies database accessibility and startup validation via `on_plugin_activate`.
- `extensions/__init__.py` registers a `SessionLifecycleExtension` at the `agent_init` session-lifecycle point that appends a `session_initialized` `ActivityEvent`.
- Lifecycle hook firing and extension registration are verified in-process only; actual Agent Zero host lifecycle firing is not yet verified.
- `NeuroCore2Retrieve` results are bounded: at most `max_results` results
  are returned (default 100, configurable via `max_results` in
  `default_config.yaml`; the optional `max_results` tool argument
  overrides the config value for a single call). The cap is applied AFTER
  scoring and sorting. When the full match count exceeds the cap, the
  payload includes `count_exceeded: true` and `total_matches: <int>` so
  callers can distinguish truncation from exhaustion — silent truncation
  is prohibited.
- Retrieval uses an inverted-term index: a `memory_terms` table (schema
  version 2) is maintained on capture and used as a pure candidate
  pre-filter before domain scoring. Tokenization is exactly
  `text.lower().split()`; scoring, ranking, and the inspectable-factors
  explanation contract are unchanged.

---

## Authorization contract

Neuro Core 2 enforces `Scope(project, agent)` isolation at the
tool-invocation level through a **derivation-based authorization
model**. This section is the authoritative newcomer-facing description
of that contract; the durable policy record is
`docs/decisions/0008-authorization-policy.md` (ADR-0008), which
supersedes ADR-0007 in full.

> **Current state (2026-09-01):** the redesigned mechanism is
> **implemented** in the plugin and covered by the test suite.
> Enforcement is **ACTIVE** — `AUTHORIZATION_ENFORCEMENT_ACTIVE` is
> `True` in all three tools (capture.py:35, retrieve.py:35,
> validate.py:41). Host-level flag-enabled behavior on the real host
> dispatch path (real `AgentConfig` → `AgentContext` → `ctx.agent0` →
> `agent.get_tool`) has been **validated by VAL**
> (validation-report.yaml rev 1, decision: pass, required_level: host;
> 5/5 ARC Condition 5 scenarios; raw probe evidence under
> `.a0proj/notepad_temp/val/20260901T0910-AUTHZ-REENABLE-VALIDATION/`).
> The earlier integration-level pass (10/10 scenarios) is retained as
> historical context. Binding is not authentication; authorization
> remains unproven as a security mechanism, and authorization-event
> evidence (`identity_source`, `denial_reason`) lives on the in-memory
> ActivityLedger and is not durably persisted across restart
> (ADR-0004/ADR-0006).

### Why the model changed

The prior model (ADR-0007) relied on a host contract: the host would
populate `agent.context.caller_project`/`caller_agent`. Empirical
verification proved the host never populates caller identity, producing
a fail-closed non-functional state (3 of 3 tools denying 100% of real
dispatches). ADR-0008 inverts the premise: caller identity is derived
**plugin-side from host inputs that verifiably exist at dispatch time**.

### Derivation-based model

| Layer | Where | What it does |
|---|---|---|
| **0. Operator-optional `_tool_access` gating** | Host policy substrate | Reuses `helpers/tool_policy.py` via the existing `_tool_access` extension. **Operator-optional and additive** — no default policy ships. Canonical policy IDs bind to the dispatchable snake_case tool names (see table below). |
| **1. Plugin-side identity derivation** | Tool boundary | The plugin derives caller identity from host inputs that exist at dispatch: `caller_project` from `helpers.projects.get_context_project_name(agent.context)` (the same input `helpers/tool_policy.py` consumes), `agent_name` from `self.agent.agent_name` (host-assigned), `profile` from `agent.config.profile`. Implemented in `plugins/neuro_core_2/caller_identity.py`. |
| **2. Scope binding** | Tool boundary | The requested `Scope(project, agent)` must **match** the derived identity tuple `(caller_project, agent_factor)`; a caller-supplied scope value can only match the derived value, never define it. On mismatch the tool raises `AuthorizationError` (fail closed) and a denial event is audited. A None/unmapped agent factor binds as the distinct sentinel `agent:None`, derived from the absence of a host-provided agent mapping — never from caller input — so it creates no unenforced path. |
| **3. Service-layer scope check** | Service boundary | `NeuroCoreService.capture()`, `retrieve()`, and `validate()` re-check scope at the service boundary using the derived caller identity. Returns a structured error dict so the tool can surface the denial reason. |
| **4. Authorization audit** | Activity ledger | Every authorization decision (allow or deny) is appended as an `authorization_decided` event with derived scope values, the `identity_source` marker, requested scope, target `memory_id` (if any), outcome, and **denial reason**. Denial events record scope values and denial reasons only — no credentials, secrets, or identity material beyond project name, `agent_name`, and profile. |

### Audited fallback with `identity_source`

When no active project is set on the context, `caller_project` falls back
to the plugin's configured `default_scope.project` (operator-controlled
configuration, never caller-supplied). Every authorization decision
records `identity_source` as exactly one of `active-project` or
`default-scope-fallback`, written into the activity-ledger event so
fallback-derived identity is distinguishable in the audit trail. Under
fallback identity, `neuro_core_2_validate`'s target-scope derivation
never widens beyond the configured default scope.

### Binding, not authentication

`agent_name` and `profile` are **host-controlled scope-binding factors**,
not authenticated caller identity. They are sufficient for scope binding
(the requested scope must match host-derived identity or the call is
denied and audited) and insufficient for caller authentication. No
caller-authentication, adversarial-bypass-resistance, or
security-assurance claim is made or permitted.

### Tool names and Layer 0 policy IDs

The declared tool names (`NeuroCore2Capture`, `NeuroCore2Retrieve`,
`NeuroCore2Validate`) are not resolvable through the host's
filename-based dispatch (known constraint). Tools are reachable only
under their dispatchable snake_case names, and authorization binds those
names. Canonical `_tool_access` policy IDs (operator-optional; no
default policy ships) bind to the dispatchable names:

| Canonical policy ID | Dispatchable tool name |
|---|---|
| `plugin:neuro_core_2:neuro_core_2_capture` | `neuro_core_2_capture` |
| `plugin:neuro_core_2:neuro_core_2_retrieve` | `neuro_core_2_retrieve` |
| `plugin:neuro_core_2:neuro_core_2_validate` | `neuro_core_2_validate` |

### Enforcement flag and rollback

`AUTHORIZATION_ENFORCEMENT_ACTIVE` is `True` in all three tools
(capture.py:35, retrieve.py:35, validate.py:41). Enforcement is active
on the real dispatch path. Setting the flag to `False` remains the
one-flag rollback: tools then behave exactly as in the P0 hotfix state —
functional, with zero authorization enforcement. The staged re-enable
condition is satisfied and completed: VAL passed integration-level
validation (validation-report.yaml rev 1, 10/10 scenarios, retained as
historical context), and after the ORC-authorized re-enable sub-step,
VAL passed host-level flag-enabled validation (validation-report.yaml
rev 1, decision: pass, required_level: host, 5/5 ARC Condition 5
scenarios on the real dispatch path).

### Error shape

| Layer | Error shape | Rationale |
|---|---|---|
| Layer 2 (tool-layer) | **Hard raise** (`AuthorizationError`) | Prevents any caller from accidentally proceeding past a denial. Fail closed, no silent fallback. |
| Service-layer | **Structured error dict** | Allows the service to return a structured response to the tool, which can then surface the denial reason to the caller. |

### Audit event

The `authorization_decided` activity event is the durable record of
every authorization decision. It includes:

- Derived caller scope (`caller_project`, agent factor — including the
  `agent:None` sentinel)
- **`identity_source`** (`active-project` or `default-scope-fallback`)
- Requested scope (`project`, `agent`)
- Target `memory_id` (if applicable)
- Outcome (`allow` or `deny`)
- **Denial reason** (scope values and denial reasons only; no
  credentials, secrets, or identity material beyond project name,
  `agent_name`, and profile)

This is consistent with ADR-0004's audit-durability principle and
makes authorization decisions fully inspectable via the existing audit
tool.

### Explicit non-claims

The authorization model is a minimal, honest baseline. The following
non-claims must be preserved in any documentation or claim that
references this model:

- This is **NOT** a security boundary against a malicious Agent Zero
  host. The host is trusted.
- This is **NOT** caller authentication. `agent_name` and `profile` are
  host-controlled binding factors, not credentials.
- This is **NOT** a defense against a compromised tool implementation.
- This does **NOT** prove authorization is "complete,"
  "production-grade," or a security mechanism. Host-level flag-enabled
  functional effectiveness is validated by VAL (validation-report.yaml
  rev 1, decision: pass, required_level: host, 5/5 ARC Condition 5
  scenarios), but this does not establish security assurance,
  adversarial resistance, or caller authentication. Concurrency and
  performance under enforcement are explicitly not tested.

### Maturity limit

The maturity-limit language **"authorization is unproven"** remains in
Project Instructions §1 until a future work item escalates the claim
with new evidence. Implementing the redesigned mechanism does not
retire the maturity limit.

---

## Environment variables

**No environment variable is currently required** to install,
configure, or run Neuro Core 2. A read-only inspection of the runtime
plugin source for `os.environ`, `getenv`, and `environ[...]`
references returned no matches. All configuration is read from the
plugin-local `default_config.yaml`.

If a future change introduces an environment-variable prerequisite, it
must be:
1. Documented in this file with its exact name, purpose, and safe
   provisioning instructions.
2. Documented in `README.md` under the "Environment variables"
   section.
3. Recorded as a durable decision in `docs/decisions/`.

---

## Versioning

- Neuro Core 2 targets Agent Zero v2.8+.
- The plugin identity `neuro_core_2` is fixed; do not rename to
  `neuro_core`.

---

## Validation checklist

A newcomer or operator can verify the install-plugin journey by
confirming each of the following:

- [ ] Plugin appears in Agent Zero with name `neuro_core_2`.
- [ ] Tools `NeuroCore2Capture`, `NeuroCore2Retrieve`,
      `NeuroCore2Validate` are callable.
- [ ] A captured memory is persisted to
      `/a0/usr/plugins/neuro_core_2/neuro_core_2.db`.
- [ ] Retrieval for the same scope returns the memory with factors.
- [ ] Validating to `superseded` removes the memory from retrieval but
      not from storage.
- [ ] Restarting the host preserves the database and allows new
      captures/retrievals.
- [ ] Activity events are appended for captured, retrieved, and
      validation-changed memories.
- Lifecycle hook firing and extension registration are verified in-process (unit/integration). Host-level firing against a real Agent Zero host is not yet verified.
- [ ] Retrieval results are bounded at `max_results` (default 100); when
      the full match count exceeds the cap, the payload includes
      `count_exceeded: true` and `total_matches: <int>` — no silent
      truncation.
- [ ] Index effectiveness: retrieval latency at 5000-memory corpus scale
      is sub-second (bounded diagnostic, n=5 queries, synthetic corpus,
      median ~657ms). This is a bounded diagnostic, not a full benchmark.

### Authorization verification (per ADR-0008)

The following items verify the authorization contract. These are
**documentation-level checks** against this baseline; runtime
verification on the real dispatch path has passed at the integration
level (VAL, 10/10 scenarios) and, after the completed ORC-authorized
re-enable, at the host level with the flag enabled (VAL,
validation-report.yaml rev 1, decision: pass, required_level: host,
5/5 ARC Condition 5 scenarios).

- [ ] This baseline documents the derivation-based authorization model
      (operator-optional Layer 0, plugin-side identity derivation, scope
      binding with the `agent:None` sentinel, service-layer check,
      authorization audit with `identity_source`).
- [ ] This baseline documents the audited fallback with the
      `identity_source` marker (`active-project` vs
      `default-scope-fallback`) and the no-widening rule under fallback.
- [ ] This baseline documents binding-not-authentication: `agent_name`
      and `profile` are host-controlled binding factors, not
      authenticated caller identity.
- [ ] This baseline documents the canonical Layer 0 policy IDs together
      with the dispatchable snake_case tool names, and the declared-name
      dispatch mismatch as a known constraint.
- [ ] This baseline documents the enforcement flag state
      (`AUTHORIZATION_ENFORCEMENT_ACTIVE = True` in all three tools),
      the one-flag rollback, and the completed staged re-enable (VAL
      integration confirmation passed; the ORC-authorized re-enable
      sub-step was executed; host-level flag-enabled validation passed —
      validation-report.yaml rev 1, decision: pass, required_level:
      host, 5/5 ARC Condition 5 scenarios).
- [ ] This baseline documents the `authorization_decided` audit event
      with `identity_source` and denial reason, and the denial-event
      content limit (scope values and denial reasons only).
- [ ] This baseline preserves the explicit non-claims (not a security
      boundary against malicious host, not caller authentication, not a
      defense against compromised tool, not production-grade or
      host-level-effective).
- [ ] This baseline preserves the maturity limit: "authorization is
      unproven" remains in Project Instructions §1.
- [ ] ADR-0008 (`docs/decisions/0008-authorization-policy.md`) exists,
      supersedes ADR-0007 in full, and is referenced from this baseline;
      ADR-0007 is annotated superseded with content preserved.

---

## References

- `README.md` — project entry point.
- `docs/ARCHITECTURE.md` — component boundaries.
- `docs/PROJECT_CONTINUITY.md` — current state and known debt.
- `docs/validation/README.md` — index of validation evidence.
- `docs/decisions/ADR-001-record-format.md` — durable decision records.
- `docs/decisions/0008-authorization-policy.md` — authorization policy
  (ADR-0008); authoritative record of the derivation-based authorization
  model, the audited fallback with `identity_source`, the `agent:None`
  sentinel semantics, and the enforcement flag state with the
  completed staged re-enable.
- `docs/decisions/0007-authorization-policy.md` — superseded predecessor
  ADR (content preserved, status annotated).
