# 0007: Authorization Policy

## Status

**Superseded by [0008-authorization-policy.md](0008-authorization-policy.md) (ADR-0008) — 2026-08-31.**

> **SUPERSEDED (2026-08-31):** This ADR is superseded **in full** by
> [ADR-0008](0008-authorization-policy.md), the durable policy record of
> `WI-2026-08-31-AUTHORIZATION-POLICY-REDESIGN` (S2). ADR-0007's Layer 1
> host contract (host-populated `agent.context.caller_project`/`caller_agent`)
> was empirically falsified on the real Agent Zero dispatch path; the
> redesign inverts it into plugin-side derivation from host inputs that
> verifiably exist at dispatch. The design content below is preserved
> unmodified as the historical record and is annotated, not rewritten.
> Historical notice (2026-08-31, pre-supersession): authorization
> enforcement was disabled pending redesign — see
> `WI-2026-08-31-AUTHORIZATION-POLICY-REDESIGN`, which supersedes
> `WI-2026-08-28-AUTHORIZATION-POLICY-DESIGN`. The host does not populate
> caller identity (`agent.context.caller_project`/`caller_agent`), so the
> five-layer mechanism (including Layers 3–5) was inactive on the real
> host dispatch path, and tools operated without authorization
> enforcement. That notice was superseded by any statement below
> describing the mechanism as functional only as a historical record.

## Context

Neuro Core 2's non-negotiable decision #2 states that `Scope(project, agent)`
is a hard isolation boundary. At the tool-invocation level, that boundary
is currently unenforced: tools accept `project` and optional `agent` as
caller-supplied arguments and construct `Scope(project, agent)` from those
arguments without verifying that the caller is authorized to act in that
scope. The service layer trusts whatever scope is passed. `neuro_core_2_validate`
is the worst case — it accepts only `memory_id` and `target`, with no scope
argument at all, so any caller can mutate any memory's lifecycle state
regardless of which scope the memory belongs to.

Project Instructions §1 explicitly lists "authorization" among Neuro Core 2's
unproven maturity limits. The activity ledger records captured, retrieved,
and validation-changed events but does not record authorization decisions.
A competition judge comparing against the predecessor plugin would
reasonably scrutinize exactly this surface.

This ADR establishes a minimal, honest authorization model that makes the
scope isolation boundary enforceable rather than aspirational, while
remaining explicit about what it does and does not prove.

## Decision

Neuro Core 2 adopts a **five-layer minimal authorization model** for
`Scope(project, agent)` enforcement at the tool-invocation level. Each
layer is independently testable and the layers compose as defense-in-depth.

### Layer 1 — Caller-context binding (host contract)

Tools derive caller identity from the Agent Zero host's tool instance —
`self.agent` and `self.agent.context` — rather than from a pre-packaged
`caller_context` parameter. This is the single source of truth for
"who is calling." The host is responsible for populating `self.agent` /
`self.agent.context` with the authenticated caller's identity
(`caller_project`, `caller_agent`).

**Wording adjustment from the original design-request:** the design-request
described Layer 1 as "Tools receive a `caller_context` parameter from the
Agent Zero host." The actual implementation derives caller identity from
`self.agent` / `self.agent.context` (the standard Agent Zero tool instance
attributes), not from a separately pre-packaged `caller_context` parameter.
This is a refinement of the wording, not a change of policy: the host
remains the single source of truth for caller identity, and the tool
remains the binding point.

### Layer 2 — Tool-layer scope check

Each tool compares the caller identity derived in Layer 1
(`self.agent.context.caller_project`, `self.agent.context.caller_agent`)
against the `project` / `agent` arguments supplied to the tool. If they do
not match, the tool **hard raises an exception** (fail closed, no silent
fallback) and does not invoke the service. The hard-raise shape is
mandatory: silent fallback to "trust the caller" would re-introduce the
gap this ADR closes.

### Layer 3 — Service-layer scope check (defense-in-depth)

`NeuroCoreService.capture()`, `retrieve()`, and `validate()` accept a
caller-context parameter and re-check scope at the service boundary. This
catches any tool that forgot to check, and any future tool that bypasses
the check. The service-layer check returns a **structured error dict**
(not a hard raise) so the service can return a structured response to the
tool, which can then surface the denial reason to the caller. The
service-layer check is the same comparison as the tool-layer check; it is
not a different policy.

### Layer 4 — Memory-bound scope check for validate

`NeuroCoreService.validate()` looks up the memory by `memory_id`, then
verifies that the caller context matches the memory's stored scope before
applying the lifecycle transition. This closes the current hole where
`validate()` accepts only `memory_id` with no scope check whatsoever.

### Layer 5 — Authorization audit

Every authorization decision (allow or deny) is appended to the activity
ledger as an `authorization_decided` event with caller context, requested
scope, target `memory_id` (if any), outcome (allow/deny), and **denial
reason** (e.g., "scope mismatch", "missing caller context"). This makes
authorization decisions fully inspectable via the existing audit tool and
is consistent with ADR-0004's audit-durability principle.

### Explicit non-claims

The following non-claims must appear in any documentation or claim that
references this model:

- This is **NOT** a security boundary against a malicious Agent Zero host.
  The host is trusted.
- This is **NOT** authentication. The host authenticates; Neuro Core 2
  verifies the host's claim.
- This is **NOT** a defense against a compromised tool implementation.
  It is a defense against a misbehaving or buggy tool.
- This does **NOT** prove authorization is "complete" or "production-grade."
  It establishes a minimal, honest baseline that addresses the maturity
  limit listed in Project Instructions §1.

### Maturity limit

The maturity-limit language "authorization is unproven" **remains in
Project Instructions §1** until a future work item escalates the claim
with new evidence. This ADR establishes a baseline; it does not retire
the maturity limit.

### Scope of this ADR

The model is bounded: it does not introduce cryptographic tokens, does
not duplicate authentication, and does not change the storage schema
beyond adding one new activity event kind (`authorization_decided`).

## Consequences

### Positive

- The scope isolation boundary becomes enforceable at the tool-invocation
  level rather than aspirational.
- Defense-in-depth: three independent enforcement points (tool, service,
  memory-bound for validate) catch any single layer that fails or is
  bypassed.
- Authorization decisions are inspectable via the existing audit tool
  with one new event kind (`authorization_decided`).
- The worst-case hole (`validate()` accepting only `memory_id` with no
  scope check) is closed by Layer 4.
- The model is minimal, honest, and bounded — consistent with the
  project's discipline of bounded claims.

### Negative

- The public tool contract gains a new requirement: tools must be
  invoked with a tool instance whose `self.agent` / `self.agent.context`
  is populated by the host. This is a **breaking-additive** contract
  change. Existing callers that do not supply a populated
  `self.agent.context` will fail closed (authorization error). The
  breaking nature must be reflected in `docs/AGENT_ZERO_CONTRACT_BASELINE.md`
  and any release notes produced under a future implementation work item.
- The model depends on the Agent Zero host providing a populated
  `self.agent` / `self.agent.context`. If the host does not provide it,
  the model cannot be implemented as designed (see ARC Condition 1).
- The model does not eliminate the maturity limit. Documentation must
  continue to state that "authorization is unproven" until a future work
  item escalates the claim with new evidence.

### Neutral

- The SQLite database schema gains one new activity event kind
  (`authorization_decided`); no other schema change is required.
- Retrieval scoring semantics and the explanation contract are unchanged.
- Lifecycle states and transitions are unchanged.
- Plugin identity, manifest, tool names, and config contract are
  unchanged (modulo the additive caller-context requirement).

## ARC Conditions (from steward-design-decision.yaml)

This ADR is required by ARC Condition 2 of the steward-design-decision
for `WI-2026-08-28-AUTHORIZATION-POLICY-DESIGN`. The full set of ARC
conditions governing the implementation work item is recorded here for
traceability:

1. **Precondition (host capability):** Before implementation begins, INT
   must verify that Agent Zero v2.8+ provides a caller-context primitive
   that tools can receive (via `self.agent` / `self.agent.context`). If
   the host does not provide it, INT must report this via
   `impact-discovery.yaml` and ORC must escalate to HITL with a
   recommendation (either request host capability, or fall back to a
   documented "host-trust-without-verification" model with explicit
   non-claims). The design is correct in principle but cannot be
   implemented without this host capability. This is the single
   highest-risk dependency in the design.
2. **ADR required:** This ADR (`0007-authorization-policy`) is the
   durable record of the authorization policy. It references ADR-0001
   (Scope as core type), non-negotiable decision #2 (Scope isolation is
   a hard boundary), and the explicit non-claims.
3. **AGENT_ZERO_CONTRACT_BASELINE.md update:** The baseline must be
   updated to reflect the breaking-additive contract change. The current
   text states "Tools are invoked with explicit `project` and optional
   `agent` scope arguments." After this change, tools will additionally
   require a populated `self.agent` / `self.agent.context`. The baseline
   must state the new requirement, the failure mode (authorization
   error, fail closed), and the explicit non-claims.
4. **Denial error shape:** Tool-layer check (Layer 2) must hard raise an
   exception (fail closed, no silent fallback). Service-layer check
   (Layer 3) must return a structured error dict so the service can
   return a structured response to the tool. Hard raise at the tool
   boundary prevents any caller from accidentally proceeding past a
   denial; structured error at the service boundary allows the tool to
   surface the denial reason to the caller.
5. **Audit event content:** The `authorization_decided` audit event must
   include the denial reason (e.g., "scope mismatch", "missing caller
   context"), not only the outcome (allow/deny). This is consistent
   with ADR-0004's audit-durability principle and makes authorization
   decisions fully inspectable via the existing audit tool.
6. **Maturity limit preserved:** The maturity limit ("authorization is
   unproven") remains in Project Instructions §1 until a future work
   item escalates the claim with new evidence. PRD claim-review must
   verify that any documentation referencing the authorization model
   includes the explicit non-claims and does not claim authorization is
   "complete" or "production-grade." The model is a minimal, honest
   baseline, not a security guarantee.
7. **HITL authorization gate:** No implementation proceeds without
   explicit HITL authorization. This is per the intake's explicit
   checkpoint ("STOP after ARC decision, report to HITL"). The design
   is approved, but implementation is gated on HITL authorization. ORC
   must report this decision and rationale to HITL and await
   authorization before delegating implementation.

## Alternatives Considered

### Leave authorization unenforced and document the maturity limit

- **Benefits:** No code change. Honest about the current state. Aligns
  with the project's discipline of bounded claims.
- **Rejected because:** Non-negotiable decision #2 states that Scope
  isolation is a hard boundary. Leaving it unenforced contradicts that
  decision. The maturity limit is a known gap, not a permanent design
  choice. A minimal, honest authorization model is required to make the
  boundary enforceable rather than aspirational.

### Implement authentication inside Neuro Core 2

(e.g., a separate API key per scope, validated by the service.)

- **Benefits:** Defense-in-depth even against a misbehaving host. No
  dependency on host-provided caller context.
- **Rejected because:** Authentication is the host's responsibility.
  Duplicating it inside Neuro Core 2 creates two sources of truth for
  caller identity and increases the surface area for misconfiguration.
  The host-trust model is sufficient and honest for v1; cryptographic
  or key-based authentication is over-engineering for the stated
  maturity limit.

### Per-tool scope check only, no service-layer re-check

- **Benefits:** Smaller change surface. One layer to test.
- **Rejected because:** Lacks defense-in-depth. A single buggy or
  future tool that bypasses the tool-layer check would compromise the
  entire boundary. The service-layer re-check is the same comparison
  repeated; the cost is small and the safety gain is real.

### Cryptographic scope tokens

(Signed by the host, verified by Neuro Core 2 on each tool call.)

- **Benefits:** Strongest available guarantee short of full
  authentication. Tamper-evident.
- **Rejected because:** Over-engineered for v1. The host-trust model
  is sufficient and honest. Cryptographic tokens introduce a new
  key-management surface, a new failure mode (key rotation, expiry),
  and a new claim surface that would need its own validation evidence.
  This is a candidate for a future work item if the maturity limit
  escalates, but not for the current design.

## References

- `docs/decisions/0001-product-and-architecture.md` — Scope as a core
  type; this ADR enforces scope at the tool boundary.
- `docs/decisions/0003-neuro-core-2-identity-and-host-validation.md` —
  Plugin identity is fixed; this ADR does not change identity.
- `docs/decisions/0004-audit-durability-and-migration-policy.md` —
  Audit durability, additive changes preferred; Layer 5 is additive
  (one new event kind).
- `docs/decisions/0005-concurrency-and-migration-policy.md` —
  Single-writer SQLite; this ADR does not change concurrency.
- `docs/decisions/0006-implementation-rules-for-sqlite-durability.md` —
  Restart survival; this ADR does not change persistence.
- `docs/AGENT_ZERO_CONTRACT_BASELINE.md` — must be updated to reflect
  the breaking-additive contract change (ARC Condition 3).
- `docs/PROJECT_CONTINUITY.md` — current state and known debt.
- `docs/COMPETITION_CHARTER.md` — claims and evidence boundaries.
- `.a0proj/decision_log/decisions.md` — non-negotiable decisions log
  maintained by ORC (specifically non-negotiable decision #2: Scope
  isolation is a hard boundary).
- `.a0proj/team/work-items/WI-2026-08-28-AUTHORIZATION-POLICY-DESIGN/design-request.yaml`
  — INT's design request for this ADR.
- `.a0proj/team/work-items/WI-2026-08-28-AUTHORIZATION-POLICY-DESIGN/steward-design-decision.yaml`
  — ARC's pre-design decision (approved-with-conditions) and the seven
  conditions recorded above.
- `.a0proj/instructions/01-PROJECT-INSTRUCTIONS.md` §1 — maturity
  limits, including "authorization is unproven" (preserved by this
  ADR per ARC Condition 6).
- `.a0proj/instructions/01-PROJECT-INSTRUCTIONS.md` §6 — classification
  system (this ADR is S2-classified: durable authorization policy).
