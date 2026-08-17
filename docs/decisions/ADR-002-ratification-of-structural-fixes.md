# ADR-002: Ratification of Structural Fixes (Tool Identity and SqliteStore Export)

## Status

Accepted (retroactive) — 2026-08-17.

## Context

The tool-identity and SqliteStore-export fixes were implemented under
WI-2026-08-16-PLUGIN-REVIEW-AND-ORGANIZATION without prior ARC pre-design
review. That work item closed as R2, but the actual content of the
fixes — restoring the NeuroCore2Capture, NeuroCore2Retrieve, and
NeuroCore2Validate tool identities and fixing the SqliteStore export —
meets the structural (S1) threshold defined in Project Instructions §6
(plugin identity, tool names, storage schema, serialization).

WI-2026-08-16-RATIFY-STRUCTURAL-FIXES was created to retroactively
classify and ratify those fixes. ARC reviewed the retroactive Design
Request and issued an `approved-as-proposed` decision, confirming the
S1 classification and recording a `conformant` conformance decision
against the current plugin-directory state.

This ADR exists to capture the ratification decision in the durable
product-plane decision record, so that future structural reviews can
check it against established decisions rather than re-litigating the
gap from scratch.

## Decision

The retroactive S1 classification of the tool-identity and
SqliteStore-export fixes is accepted. The change restores, rather than
amends, the identity, tool names, and storage export already specified
in Project Instructions §1 (product identity: tool names
NeuroCore2Capture / NeuroCore2Retrieve / NeuroCore2Validate, plugin
folder `/a0/usr/plugins/neuro_core_2/`, database path
`plugins/neuro_core_2/neuro_core_2.db`).

This is a one-time correction for the specific gap in
WI-2026-08-16-PLUGIN-REVIEW-AND-ORGANIZATION and does NOT establish a
precedent for future structural changes to proceed without pre-design
review. Future S1/S2/X work must continue to follow the normal
pre-design-review path described in Project Instructions §8.

Direct HITL edits to product-plane content follow the review-and-ratify
requirement added to Project Instructions §12: the next agent session
must not assume such an edit is automatically R0/R1/R2 by default;
ORC must create a review-and-ratify work item, classify it per §6
based on the actual content of the change, and route it through the
applicable gates — including a retroactive Design Request and ARC
review if the change meets the structural (S1/S2) threshold — before
treating the edited state as canonical.

## Consequences

- The retroactive ratification is recorded as a durable architectural
  decision. Future structural reviews can reference this ADR instead of
  re-deriving the classification from scratch.
- Future structural changes must follow the normal pre-design review
  process described in Project Instructions §8. Retroactive
  ratification is not a general-purpose escape hatch.
- Direct HITL edits to product-plane content are subject to the
  review-and-ratify requirement in Project Instructions §12. Such
  edits are not silently treated as R0/R1/R2.
- The minor casing observation recorded in ARC's design and
  conformance decisions (actual class name `SQLiteStore` vs the
  `SqliteStore` reference in the Design Request and prior decisions
  log) remains a non-blocking documentation observation. The
  structural fix is the export itself, not the exact casing.
- Remaining gaps surfaced by conformance (hooks.py and extensions/
  directory still absent) are out of scope for this ratification and
  are tracked as separate remediation work items (e.g.,
  WI-2026-08-16-RESTORE-INSTALL-HOOKS) rather than blocking this
  ratification.

## References

- `WI-2026-08-16-RATIFY-STRUCTURAL-FIXES` — retroactive classification
  and ratification work item (intake, impact-assessment, design-request,
  steward-design-decision, steward-conformance-decision, closure).
- `WI-2026-08-16-PLUGIN-REVIEW-AND-ORGANIZATION` — original work item
  under which the fixes were implemented without prior ARC pre-design
  review.
- Project Instructions §1 — product identity (tool names, plugin
  folder, database path).
- Project Instructions §6 — classification system and the structural
  (S1/S2) threshold.
- Project Instructions §8 — end-to-end routing logic and the normal
  pre-design-review path for structural work.
- Project Instructions §12 — canonical artifact promotion protocol,
  including the review-and-ratify requirement for direct HITL edits to
  product-plane content.
- `docs/decisions/ADR-001-record-format.md` — ADR record format.
