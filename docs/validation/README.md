# Neuro Core 2 Validation Artifacts

This directory (`docs/validation/`) holds dated evidence that Neuro
Core 2 works as claimed in a real Agent Zero host.

This file is the **required entry point** for the validation evidence
index. It must not be replaced with the bare directory path
`docs/validation/`. Newcomers and operators should read this file
first to locate and interpret validation evidence.

---

## Baseline evidence status

**No validation evidence dated prior to 2026-08-16 is available in
this repository.** The original Phase B regression run
(`RG-2026-08-15-HOST-BASELINE-VALIDATION`) referenced dated evidence
files at `docs/validation/2026-08-05-agent-zero-host-validation.md`
and `docs/validation/2026-08-05-post-restart-persistence-check.md`.
Those files do not exist in the current tree, in any subdirectory,
or in recoverable git history. The original regression run recorded
this honestly as `comparison_result: baseline-unavailable`.

**`RG-2026-08-16-HOST-BASELINE-REVALIDATION` now constitutes the
authoritative baseline going forward.** This is the legitimate
outcome of a long-overdue first agent-run validation, not an
unresolved gap. Two of three required scenarios pass at host level
(tool availability, SQLite behavior); the third (install/activation
flow) is correctly routed to `WI-2026-08-16-RESTORE-INSTALL-HOOKS`
and is not unaddressed.

The canonical artifacts for the new baseline are:

- `.a0proj/team/assurance/regressions/RG-2026-08-16-HOST-BASELINE-REVALIDATION/regression-plan.yaml`
- `.a0proj/team/assurance/regressions/RG-2026-08-16-HOST-BASELINE-REVALIDATION/regression-report.yaml`
- `.a0proj/team/assurance/regressions/RG-2026-08-16-HOST-BASELINE-REVALIDATION/closure.yaml`

---

## Contents

The `docs/validation/` directory contains:

- `README.md` — this file (required entry point for the validation
  evidence index).

The following files were referenced by prior regression runs but
are **not present** in the current tree:

- `2026-08-05-agent-zero-host-validation.md` — referenced by
  `RG-2026-08-15-HOST-BASELINE-VALIDATION` as a baseline evidence
  file. Not present; see "Baseline evidence status" above.
- `2026-08-05-post-restart-persistence-check.md` — referenced by
  `RG-2026-08-15-HOST-BASELINE-VALIDATION` as a baseline evidence
  file. Not present; see "Baseline evidence status" above.
- `SCHEMA_TEST_SKETCH.md` — notes leading to the schema
  compatibility regression test. Not present in the current tree.

For current baseline evidence, see the canonical artifacts listed
under "Baseline evidence status" above.

---

## Integration-level validation: authorization policy redesign (2026-08-31)

**Work item:** `WI-2026-08-31-AUTHORIZATION-POLICY-REDESIGN` (S2)
**Canonical evidence:**
`.a0proj/team/work-items/WI-2026-08-31-AUTHORIZATION-POLICY-REDESIGN/validation-report.yaml`
(rev 1, decision: **pass**, integration level)
**Raw probe evidence:**
`.a0proj/notepad_temp/val/20260831T1625-AUTHZ-REDESIGN-INTEGRATION-VAL/`
(`probe_run4.log`, `probe_b6_run2.log`, `pytest_full.log`)

**What this evidence supports (integration level only):**

- Real host dispatch path (`AgentConfig` → `AgentContext` →
  `ctx.agent0` → `agent.get_tool`) functions for all three tools with
  `AUTHORIZATION_ENFORCEMENT_ACTIVE` at its shipped value `False`
  (flag-off unchanged behavior, scenarios A1–A3).
- Under flag-on in-memory fixtures: active-project identity scope
  match allows and mismatch denies with audited events (B1/B2);
  sentinel `agent:None` semantics (B3); fallback binding to
  `default_scope` with mismatch denial (B4); validate caller-scope
  rejection and clean-validate success (B5); fallback validate never
  widening beyond `default_scope` (B6); denial-event content limited to
  scope values and denial reasons with `identity_source` present (B7).
- All 154 plugin tests pass under the framework runtime with the flag
  at its shipped value `False`.

**What this evidence does NOT support:**

- Performance, concurrency, adversarial resistance, or caller
  authentication (binding-not-authentication; no security claims).
- Full authorization-event evidence durability across restart.

Do not extrapolate these results into security or performance claims.
Host-level flag-enabled behavior is now covered by the dedicated entry
below (2026-09-01).

---

## Host-level validation: authorization enforcement re-enable (2026-09-01)

**Work item:** `WI-2026-08-31-AUTHZ-ENFORCEMENT-REENABLE-VALIDATION` (R2)
**Canonical evidence:**
`.a0proj/team/work-items/WI-2026-08-31-AUTHZ-ENFORCEMENT-REENABLE-VALIDATION/validation-report.yaml`
(rev 1, decision: **pass**, required_level: **host**)
**Raw probe evidence:**
`.a0proj/notepad_temp/val/20260901T0910-AUTHZ-REENABLE-VALIDATION/`
(`pre-change-snapshot.txt`, `post-change-flag-state.txt`,
`probe_flag_on_run1.log`, `probe_s4_diagnostic2.log`,
`probe_flag_on_run2.log`, `probe_identity_source_intercept.log`)

**What this evidence supports (host level, flag enabled):**

- `AUTHORIZATION_ENFORCEMENT_ACTIVE = True` in all three tools
  (capture.py:35, retrieve.py:35, validate.py:41); enforcement is
  ACTIVE on the real host dispatch path (`AgentConfig` →
  `AgentContext` → `ctx.agent0` → `agent.get_tool` → `execute`).
- All 5 ARC Condition 5 scenarios pass with the flag enabled:
  active-project allow with audited event; active-project deny with
  audited event limited to scope values and denial reason (ARC
  Condition 7); fallback identity with `identity_source`
  (`default-scope-fallback`) marker; fallback non-widening (capture and
  validate); validate-caller-scope rejection with clean validate
  succeeding.

**What this evidence does NOT support:**

- Security assurance, adversarial resistance, or caller authentication
  (binding-not-authentication; `agent_name` and `profile` are
  host-controlled binding factors, not credentials).
- Concurrency or performance under enforcement (explicitly not tested).
- Durability of authorization-event evidence across restart
  (`identity_source`, `denial_reason` live on the in-memory
  ActivityLedger; not persisted in the `activity_events` table —
  pre-existing ledger design per ADR-0004/ADR-0006).
- Production config resolution (harness used an in-memory `load_config`
  fixture with a disposable temp DB).

Do not extrapolate these results into security, concurrency,
performance, or production-grade claims.

---

## How to add a new validation log

1. Create a new file named `YYYY-MM-DD-<short-description>.md` in
   `docs/validation/`.
2. Record:
   - Agent Zero version/commit and environment details.
   - Install command (e.g.
     `python /a0/usr/plugins/neuro_core_2/install.py`).
   - Plugin discovery result and tool names observed.
   - Concrete capture/retrieve/validate inputs and outputs.
   - Database path and any schema notes.
   - Test output and any deviations from expected behavior.
3. Link the new file from this README.

---

## Use in competition

When citing evidence, reference the specific dated log and the exact
claims it supports (e.g. "restart survival" or "supersession
behavior"). Do not extrapolate beyond what the log demonstrates.

For the current authoritative baseline, cite the canonical artifacts
under "Baseline evidence status" above rather than dated log files
that do not exist.

---

## References

- `README.md` — project entry point.
- `docs/AGENT_ZERO_CONTRACT_BASELINE.md` — host contract and
  validation checklist.
- `docs/PROJECT_CONTINUITY.md` — current state and known debt.
- `docs/decisions/ADR-001-record-format.md` — durable decision records.
- `.a0proj/team/assurance/regressions/RG-2026-08-16-HOST-BASELINE-REVALIDATION/`
  — canonical artifacts for the current authoritative baseline.
