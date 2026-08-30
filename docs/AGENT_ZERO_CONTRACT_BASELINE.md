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
tool-invocation level through a **five-layer minimal authorization
model**. This section is the authoritative newcomer-facing description
of that contract; the durable policy record is
`docs/decisions/0007-authorization-policy.md` (ADR-0007).

### Five-layer model

| Layer | Where | What it does |
|---|---|---|
| **1. Caller-context binding** | Host contract | Tools derive caller identity from the Agent Zero tool instance — `self.agent` and `self.agent.context` — rather than from a pre-packaged `caller_context` parameter. The host is the single source of truth for "who is calling." |
| **2. Tool-layer scope check** | Tool boundary | Each tool compares `self.agent.context.caller_project` and `self.agent.context.caller_agent` against the `project` / `agent` arguments supplied to the tool. On mismatch, the tool **hard raises an exception** (fail closed, no silent fallback) and does not invoke the service. |
| **3. Service-layer scope check** | Service boundary | `NeuroCoreService.capture()`, `retrieve()`, and `validate()` accept a caller-context parameter and re-check scope at the service boundary. Defense-in-depth: catches any tool that forgot to check, and any future tool that bypasses the check. Returns a **structured error dict** (not a hard raise) so the service can return a structured response to the tool. |
| **4. Memory-bound scope check for validate** | Service boundary (validate only) | `NeuroCoreService.validate()` looks up the memory by `memory_id`, then verifies that the caller context matches the memory's stored scope before applying the lifecycle transition. Closes the prior hole where `validate()` accepted only `memory_id` with no scope check. |
| **5. Authorization audit** | Activity ledger | Every authorization decision (allow or deny) is appended to the activity ledger as an `authorization_decided` event with caller context, requested scope, target `memory_id` (if any), outcome (allow/deny), and **denial reason** (e.g., "scope mismatch", "missing caller context"). Makes authorization decisions fully inspectable via the existing audit tool. |

### Breaking-additive contract change

The authorization model introduces a **breaking-additive** change to
the public tool contract:

- **Before:** Tools were invoked with explicit `project` and optional
  `agent` scope arguments, and the service trusted whatever scope was
  passed.
- **After:** Tools additionally require a populated
  `self.agent` / `self.agent.context` from the Agent Zero host. Caller
  identity is derived from `self.agent.context.caller_project` and
  `self.agent.context.caller_agent`.

**Failure mode:** Existing callers that do not supply a populated
`self.agent.context` will fail closed (authorization error). Silent
fallback to "trust the caller" is explicitly prohibited — it would
re-introduce the gap this contract closes.

**Migration:** Callers must ensure the Agent Zero host populates
`self.agent` / `self.agent.context` with the authenticated caller's
identity before invoking any Neuro Core 2 tool. This is the host's
responsibility; Neuro Core 2 verifies the host's claim.

### Error shape

| Layer | Error shape | Rationale |
|---|---|---|
| Layer 2 (tool-layer) | **Hard raise** (exception) | Prevents any caller from accidentally proceeding past a denial. Fail closed, no silent fallback. |
| Layer 3 (service-layer) | **Structured error dict** | Allows the service to return a structured response to the tool, which can then surface the denial reason to the caller. |

### Audit event

The `authorization_decided` activity event is the durable record of
every authorization decision. It includes:

- Caller context (`caller_project`, `caller_agent`)
- Requested scope (`project`, `agent`)
- Target `memory_id` (if applicable)
- Outcome (`allow` or `deny`)
- **Denial reason** (e.g., "scope mismatch", "missing caller context")

This is consistent with ADR-0004's audit-durability principle and
makes authorization decisions fully inspectable via the existing audit
tool.

### Explicit non-claims

The authorization model is a minimal, honest baseline. The following
non-claims must be preserved in any documentation or claim that
references this model:

- This is **NOT** a security boundary against a malicious Agent Zero
  host. The host is trusted.
- This is **NOT** authentication. The host authenticates; Neuro Core 2
  verifies the host's claim.
- This is **NOT** a defense against a compromised tool implementation.
  It is a defense against a misbehaving or buggy tool.
- This does **NOT** prove authorization is "complete" or
  "production-grade." It establishes a minimal, honest baseline that
  addresses the maturity limit listed in Project Instructions §1.

### Maturity limit

The maturity-limit language **"authorization is unproven"** remains in
Project Instructions §1 until a future work item escalates the claim
with new evidence. This contract establishes a baseline; it does not
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

### Authorization verification (per ADR-0007)

The following items verify the authorization contract. These are
**documentation-level checks** against this baseline; runtime
verification requires the implementation work item to be authorized
and completed.

- [ ] This baseline documents the five-layer authorization model
      (caller-context binding, tool-layer check, service-layer check,
      memory-bound check for validate, authorization audit).
- [ ] This baseline documents the breaking-additive contract change:
      tools require a populated `self.agent` / `self.agent.context`
      from the host, and fail closed if it is absent.
- [ ] This baseline documents the error shape: hard raise at the
      tool-layer (Layer 2), structured error dict at the service-layer
      (Layer 3).
- [ ] This baseline documents the `authorization_decided` audit event
      with denial reason.
- [ ] This baseline preserves the explicit non-claims (not a security
      boundary against malicious host, not authentication, not a
      defense against compromised tool, not production-grade).
- [ ] This baseline preserves the maturity limit: "authorization is
      unproven" remains in Project Instructions §1.
- [ ] ADR-0007 (`docs/decisions/0007-authorization-policy.md`) exists
      and is referenced from this baseline.

---

## References

- `README.md` — project entry point.
- `docs/ARCHITECTURE.md` — component boundaries.
- `docs/PROJECT_CONTINUITY.md` — current state and known debt.
- `docs/validation/README.md` — index of validation evidence.
- `docs/decisions/ADR-001-record-format.md` — durable decision records.
- `docs/decisions/0007-authorization-policy.md` — authorization policy
  (ADR-0007); authoritative record of the five-layer authorization
  model and the breaking-additive contract change.
