# ADR-0008: Authorization Policy (Redesigned)

## Status

Accepted — 2026-08-31. Supersedes
[0007-authorization-policy.md](0007-authorization-policy.md) (ADR-0007)
**in full**.

This ADR is the durable policy record for
`WI-2026-08-31-AUTHORIZATION-POLICY-REDESIGN` (S2), approved by ARC's
steward-design-decision (revision 1, `approved-with-conditions`, seven
conditions). It replaces ADR-0007's five-layer model, whose Layer 1 host
contract was empirically falsified; ADR-0007 is retained as a historical
record with its content preserved and its status annotated as superseded.

**Current implementation state (do not overclaim):** the redesigned
mechanism is **implemented** in the plugin and covered by the test suite.
Enforcement is **ACTIVE** — `AUTHORIZATION_ENFORCEMENT_ACTIVE` is `True`
in all three tools (capture.py:35, retrieve.py:35, validate.py:41).
Host-level flag-enabled behavior has been **validated by VAL**
(validation-report.yaml rev 1, decision: pass, required_level: host,
5/5 ARC Condition 5 scenarios on the real dispatch path; raw probe
evidence under
`.a0proj/notepad_temp/val/20260901T0910-AUTHZ-REENABLE-VALIDATION/`).
The earlier integration-level pass (10/10 scenarios) is retained as
historical context. Implemented, active, and validated remain distinct
states from proven-as-a-security-mechanism: this validation does not
establish security assurance, adversarial resistance, or caller
authentication, and must not be conflated with any such claim.

## Context

### Why ADR-0007 was superseded

ADR-0007's Layer 1 was a host contract: "the host is responsible for
populating `self.agent.context` with the authenticated caller's identity
(`caller_project`, `caller_agent`)." Empirical verification under
`WI-2026-08-30-AUTHZ-HOST-VERIFICATION` falsified this premise on the real
Agent Zero dispatch path:

- **Injection-path probe** (`notepad_temp/val/20260830T1137-AUTHZ-HOST-VERIFICATION/substep-a-injection-path.md`):
  zero grep matches for `caller_project`/`caller_agent` anywhere in the
  core host, and `hasattr` returns `False` for these attributes on a real
  `AgentContext`. The host never populates caller identity.
- **Blast-radius probe** (`notepad_temp/val/20260831T0910-AUTHZ-BLAST-RADIUS/blast-radius.md`):
  3 of 3 tools raised `AuthorizationError` on 100% of real dispatches
  before any business logic — a fail-closed, non-functional state.

The consequence was a P0 hotfix (`WI-2026-08-31-AUTHZ-HOTFIX`, commit
`88c1062`): enforcement disabled via `AUTHORIZATION_ENFORCEMENT_ACTIVE = False`
in all three tools, restoring functionality with zero authorization
enforcement on the real dispatch path. The prior design approval
(`WI-2026-08-28-AUTHORIZATION-POLICY-DESIGN`) was superseded.

Because ADR-0007's Layer 1 was a **host contract** — a claim about what the
host provides — the redesign inverts it rather than amends it: identity is
derived plugin-side from host inputs that verifiably exist at dispatch
time. The core identity mechanism is replaced, not extended, so a new ADR
superseding ADR-0007 in full is required (ARC Condition 5); an amendment
would leave a falsified host contract standing inside an Accepted ADR.

### Verified host inputs that exist at dispatch

Every identity input the redesign relies on was verified to exist on the
real dispatch path (all 17 grounding citations in the design request were
independently verified by ARC, verification scope: all):

- `self.agent` is host-injected into every tool instance
  (`/a0/helpers/tool.py:20`; consumed by `agent.py` `get_tool`).
- The active project is readable from host-populated context data via
  `helpers.projects.get_context_project_name(agent.context)`
  (`/a0/helpers/projects.py:669-670`) — the same identity input
  `helpers/tool_policy.py:43` itself consumes.
- `agent.config.profile` is host configuration (`/a0/agent.py:324-326`).
- `self.agent.agent_name` is assigned by the host at Agent construction
  (`/a0/agent.py:381`, `self.agent_name = f"A{self.number}"`) and is not
  caller-supplied.

## Decision

Neuro Core 2 adopts a **derivation-based authorization model** for
`Scope(project, agent)` enforcement at the tool-invocation level. The core
inversion: caller identity is **never** accepted from caller input and
**never** assumed to be host-populated caller-identity fields; it is
**derived plugin-side from host inputs that verifiably exist at dispatch
time**.

### Layer 1 — Plugin-side identity derivation (inverted host contract)

Implemented in `plugins/neuro_core_2/caller_identity.py`
(`derive_caller_identity`). The plugin derives caller identity exclusively
from host inputs that exist at dispatch:

- **`caller_project`**: `helpers.projects.get_context_project_name(agent.context)`
  — the same active-project identity input `helpers/tool_policy.py`
  consumes. This replaces ADR-0007's falsified
  `agent.context.caller_project` premise.
- **`agent_name`**: `self.agent.agent_name` (host-assigned at Agent
  construction).
- **`profile`**: `agent.config.profile` (host configuration).

### Audited fallback with `identity_source` marker (ARC Condition 1)

When no active project is set on the context, `caller_project` falls back
to the plugin's configured `default_scope.project` — operator-controlled
plugin configuration (`default_config.yaml`), never caller-supplied. The
fallback preserves the property whose absence falsified ADR-0007's Layer 1:
identity is not caller-supplied. This mirrors the host's own behavior
(`helpers/tool_policy.py:43` treats an absent active project as an empty
string rather than a denial); fail-closed was rejected because it would
recreate the empirically proven non-functional state for every unscoped
session.

Every authorization decision records `identity_source` with exactly one of:

- `active-project` — `caller_project` derived from the active project.
- `default-scope-fallback` — no active project; `caller_project` bound to
  the configured `default_scope.project`.

The marker is written into the activity-ledger authorization event
alongside the decision, so fallback-derived identity is distinguishable
from active-project-derived identity in the audit trail. Under fallback
identity, `neuro_core_2_validate`'s target-scope derivation never widens
beyond the configured default scope — fallback binds at most to
`default_scope`, never to a caller-supplied scope value.

### Binding, not authentication (ARC Condition 2)

`agent_name` and `profile` are **host-controlled scope-binding factors**,
not authenticated caller identity. They are configuration/construct-time
identifiers, sufficient for scope **binding** (the requested scope must
match host-derived identity or the call is denied and audited) and
insufficient for caller **authentication**. No caller-authentication,
adversarial-bypass-resistance, or security-assurance claim is made or
permitted in any documentation or narrative surface referencing this
model. This is consistent with the project's known maturity limits.

### Layer 2 — Scope binding and the `agent:None` sentinel (ARC Condition 3)

Each tool binds the requested `Scope(project, agent)` against the derived
identity tuple `(caller_project, agent_factor)`. The requested scope must
**match** the derived value; a caller-supplied scope value can only match
the derived value, never define it. On mismatch the tool raises
`AuthorizationError` (fail closed) and a denial event is audited.

**`agent:None` sentinel semantics:** when the derived `agent_name` is
None/empty, or matches no configured agent-factor mapping (e.g., a
top-level A0 caller), the agent factor binds as the distinct sentinel
value **`agent:None`** (implemented as `AGENT_NONE_SENTINEL` in
`caller_identity.py`). The sentinel is derived from the **absence of a
host-provided agent mapping**, never from caller input, so it does not
create an unenforced path: the requested scope must still match the
sentinel, and any caller-supplied concrete agent value is a mismatch and
is denied with an audited event. Denial was explicitly rejected because it
would recreate the proven fail-closed non-functional state for every
top-level A0 caller — the exact defect this redesign cures. Sentinel-bound
allows are distinguishable from named-agent allows in the ledger via the
recorded agent factor and `identity_source`.

### Layer 0 — Operator-optional `_tool_access` gating (ARC Condition 4)

Layer 0 reuses the host's single sanctioned policy substrate
(`helpers/tool_policy.py` via the existing `_tool_access`
`tool_execute_before` extension). It is **operator-optional and additive**:
no default `_tool_access` policy entry ships for Neuro Core 2, preserving
the host's documented inherit/standard-access default and the design's
public-contract compatibility declaration. An operator-configured block is
correct behavior, not a defect.

Operators who choose coarse gating configure policies using the canonical
policy IDs, which bind to the **dispatchable snake_case tool names**:

| Canonical policy ID | Dispatchable tool name |
|---|---|
| `plugin:neuro_core_2:neuro_core_2_capture` | `neuro_core_2_capture` |
| `plugin:neuro_core_2:neuro_core_2_retrieve` | `neuro_core_2_retrieve` |
| `plugin:neuro_core_2:neuro_core_2_validate` | `neuro_core_2_validate` |

### Known constraint: declared-name dispatch mismatch

The declared tool names (`NeuroCore2Capture`, `NeuroCore2Retrieve`,
`NeuroCore2Validate`) are **not resolvable** through the host's
filename-based tool dispatch. Tools are reachable only under their
snake_case, file-derived names (`neuro_core_2_capture`,
`neuro_core_2_retrieve`, `neuro_core_2_validate`), and authorization binds
those dispatchable names. Remediation of the dispatch mismatch itself is
out of scope for this redesign and is recorded as a known constraint, not
a defect introduced by this ADR.

### Authorization audit

Every authorization decision (allow or deny) is appended to the activity
ledger as an `authorization_decided` event recording: the derived scope
values (`caller_project`, agent factor), the `identity_source` marker, the
requested scope, target `memory_id` (if any), outcome (allow/deny), and
the **denial reason**. Denial events record scope values and denial
reasons only — no credentials, secrets, tokens, or identity material
beyond project name, `agent_name`, and profile are logged (ARC Condition
7). This is consistent with ADR-0004's audit-durability principle.

### Enforcement status and staged re-enable (ARC Condition 6)

- **Implemented:** derivation, sentinel binding, audited fallback, denial
  auditing, and flag-off rollback behavior are implemented in
  `caller_identity.py`, the three tools, and `neuro_core_2_service.py`,
  covered by the authorization test modules (154 tests passing at
  sub-step C).
- **Rollback:** setting `AUTHORIZATION_ENFORCEMENT_ACTIVE = False` in
  all three tools restores the P0 hotfix state — functional, with zero
  authorization enforcement on the real dispatch path. This one-flag
  rollback remains available at any time.
- **Staged re-enable (completed):** VAL passed integration-level
  validation on the real host dispatch path (validation-report.yaml
  rev 1, 10/10 required scenarios, including the fallback and denial
  scenarios), satisfying the VAL prerequisite. The flag was then set
  `True` as a separate ORC-authorized sub-step
  (`WI-2026-08-31-AUTHZ-ENFORCEMENT-REENABLE-VALIDATION`), and VAL
  passed host-level flag-enabled validation (validation-report.yaml
  rev 1, decision: pass, required_level: host, 5/5 ARC Condition 5
  scenarios on the real dispatch path).

### Explicit non-claims

The following non-claims must appear in any documentation or claim that
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
- Authorization-event evidence (`identity_source`, `denial_reason`) is
  recorded on the in-memory ActivityLedger and is **NOT** durably
  persisted across restart (no evidence column in the `activity_events`
  table; pre-existing ledger design per ADR-0004/ADR-0006).

### Maturity limit

The maturity-limit language **"authorization is unproven"** remains in
Project Instructions §1. Implementing the redesigned mechanism does not
retire the maturity limit; only VAL-confirmed real-dispatch evidence plus
a future claim-escalation work item could do that.

## Consequences

### Positive

- Authorization no longer depends on a falsified host contract. Every
  identity input is verified to exist on the real dispatch path.
- The fail-closed non-functional state (3 of 3 tools denying 100% of real
  dispatches) is cured without abandoning enforcement: binding still
  requires the requested scope to match host/plugin-derived identity.
- Fallback identity is fully auditable via the `identity_source` marker;
  fallback never widens beyond the configured default scope.
- The `agent:None` sentinel closes what would otherwise be an unenforced
  path for top-level A0 callers.
- One-flag rollback (`AUTHORIZATION_ENFORCEMENT_ACTIVE = False`) to the
  known-good P0 hotfix state at any time.
- Authorization decisions remain fully inspectable via the existing audit
  tool, consistent with ADR-0004's audit-durability principle.

### Negative
- Enforcement is now active (`AUTHORIZATION_ENFORCEMENT_ACTIVE = True`
  in all three tools) following the completed ORC-authorized re-enable
  and VAL's host-level pass (validation-report.yaml rev 1, decision:
  pass, required_level: host, 5/5 ARC Condition 5 scenarios), but
  concurrency and performance under enforcement remain untested, and
  the one-flag rollback to the unenforced P0 hotfix posture remains
  available.
- The declared-name dispatch mismatch persists as a known constraint;
  documentation and Layer 0 policy IDs must use the dispatchable
  snake_case names.
- Binding is not authentication: the model provides no resistance to a
  caller that can influence host-derived identity inputs, and no
  security-assurance claim may be made.
- The maturity limit remains until separately escalated with evidence.

### Neutral
- No change to tool argument schemas, tool names, config keys, database
  paths, plugin manifest fields, or lifecycle hook signatures.
- No Agent Zero framework source is modified; the design consumes
  existing mechanisms only (`helpers/tool_policy.py` via the existing
  `_tool_access` extension, `helpers/projects.py`).
- Retrieval scoring semantics, the explanation contract, lifecycle
  states, and storage schema are unchanged (the `authorization_decided`
  event kind from ADR-0007 is retained).
- The predecessor plugin `neuro_core` is untouched.

## Supersession record

This ADR supersedes
[0007-authorization-policy.md](0007-authorization-policy.md) **in full**,
including its Layers 1–5 and its ARC conditions. ADR-0007's Layer 1 host
contract (host-populated `caller_project`/`caller_agent`) was empirically
falsified by the evidence above; its Layers 2–5 are restated here against
the derivation-based model (scope binding with sentinel semantics,
service-layer re-check, audited decisions). ADR-0007's content is
preserved unmodified as the historical record; only its Status section is
annotated as superseded. The falsification evidence and the supersession
of the prior design approval are recorded in the work items
`WI-2026-08-30-AUTHZ-HOST-VERIFICATION`,
`WI-2026-08-31-AUTHZ-HOTFIX`, and
`WI-2026-08-31-AUTHORIZATION-POLICY-REDESIGN`.

## References

- `docs/decisions/0007-authorization-policy.md` — superseded predecessor
  ADR (content preserved, status annotated).
- `docs/decisions/0001-product-and-architecture.md` — Scope as a core
  type; this ADR enforces scope at the tool boundary.
- `docs/decisions/0004-audit-durability-and-migration-policy.md` — audit
  durability; authorization decisions are audited activity events.
- `docs/AGENT_ZERO_CONTRACT_BASELINE.md` — "Authorization contract"
  section; authoritative newcomer-facing contract description.
- `/a0/helpers/tool_policy.py` and its dox — the host policy substrate
  reused by Layer 0 (operator-optional).
- `/a0/helpers/projects.py` (`get_context_project_name`) — the
  active-project identity input, shared with the host's own policy check.
- `/a0/agent.py:381` — host-assigned `agent_name`.
- `/a0/usr/plugins/neuro_core_2/caller_identity.py` — Layer 1 derivation
  and Layer 2 binding implementation.
- `/a0/usr/plugins/neuro_core_2/neuro_core_2_service.py` — service-layer
  scope check and `authorization_decided` event recording.
- `.a0proj/team/work-items/WI-2026-08-31-AUTHORIZATION-POLICY-REDESIGN/design-request.yaml`
  and `steward-design-decision.yaml` — design request and ARC's
  approved-with-conditions decision (seven conditions).
- `.a0proj/notepad_temp/val/20260830T1137-AUTHZ-HOST-VERIFICATION/substep-a-injection-path.md`
  and `.a0proj/notepad_temp/val/20260831T0910-AUTHZ-BLAST-RADIUS/blast-radius.md`
  — falsification evidence for ADR-0007's Layer 1.
- `.a0proj/decision_log/decisions.md` — non-negotiable decision #2
  (Scope isolation is a hard boundary).
- `.a0proj/instructions/01-PROJECT-INSTRUCTIONS.md` §1 — maturity limits,
  including "authorization is unproven" (preserved).
