"""Tests for the five-layer authorization policy (ADR-0007).

This test file covers sub-step D of WI-2026-08-28-AUTHORIZATION-POLICY-DESIGN:
- Layer 2: tool-layer scope check (hard raise on scope mismatch)
- Layer 3: service-layer scope check (structured error dict on scope mismatch)
- Layer 5: authorization audit (authorization_decided event with denial reason)

Layer 1 (caller-context binding) and Layer 4 (memory-bound scope check for
validate) are also exercised as part of the Layer 3/4 service tests.
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

HERE = Path(__file__).resolve().parent
PLUGIN_DIR = HERE.parent
sys.path.insert(0, str(PLUGIN_DIR))
sys.path.insert(0, "/a0")  # for helpers.tool (Agent Zero framework)

from activity_ledger import ActivityLedger
from memory_lifecycle import ValidationState
from memory_store import MemoryStore
from neuro_core_2 import Memory, Scope
from neuro_core_2_service import AuthorizationError, NeuroCoreService


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

class InMemoryStore(MemoryStore):
    """Minimal in-memory MemoryStore for tests.

    Implements only the methods NeuroCoreService actually calls. Activity
    events are stored in a parallel list so the audit assertions can inspect
    them directly.
    """

    def __init__(self) -> None:
        self._memories: dict[str, Memory] = {}
        self._events: list = []

    def put(self, memory: Memory) -> None:
        self._memories[memory.memory_id] = memory

    def get(self, memory_id: str) -> Memory | None:
        return self._memories.get(memory_id)

    def list(self, scope: Scope) -> list[Memory]:
        return [m for m in self._memories.values() if m.scope == scope]

    def candidate_ids(self, terms: set, scope: Scope) -> list[str]:
        result = []
        for mid, m in self._memories.items():
            if m.scope != scope:
                continue
            text_terms = set(m.text.lower().split())
            if terms & text_terms:
                result.append(mid)
        return result

    def append_event(self, event) -> None:
        self._events.append(event)

    def list_events(self, scope: Scope | None = None):
        if scope is None:
            return tuple(self._events)
        return tuple(e for e in self._events if e.scope == scope)


def _make_service() -> tuple[NeuroCoreService, InMemoryStore]:
    store = InMemoryStore()
    ledger = ActivityLedger()
    service = NeuroCoreService(store, ledger)
    return service, store


def _make_caller_context(project: str = "projA", agent: str = "agent1") -> dict:
    return {"caller_project": project, "caller_agent": agent}


# ---------------------------------------------------------------------------
# Layer 3 tests: service-layer scope check (structured error dict)
# ---------------------------------------------------------------------------

def test_layer3_capture_valid_scope_passes():
    """Layer 3: valid scope passes — service stores memory normally."""
    service, store = _make_service()
    ctx = _make_caller_context("projA", "agent1")
    result = service.capture(
        Memory("hello world", "test", Scope("projA", "agent1"), 0.5, 0.5),
        caller_context=ctx,
    )
    assert isinstance(result, Memory), f"expected Memory, got {type(result).__name__}"
    assert result.text == "hello world"
    print("PASS: test_layer3_capture_valid_scope_passes")


def test_layer3_capture_scope_mismatch_returns_error_dict():
    """Layer 3: scope mismatch returns structured error dict (not hard raise)."""
    service, store = _make_service()
    ctx = _make_caller_context("projA", "agent1")
    result = service.capture(
        Memory("hello world", "test", Scope("projB", "agent2"), 0.5, 0.5),
        caller_context=ctx,
    )
    assert isinstance(result, dict), f"expected dict, got {type(result).__name__}"
    assert result["error"] == "authorization_denied"
    assert result["reason"] == "scope mismatch"
    assert result["caller_project"] == "projA"
    assert result["caller_agent"] == "agent1"
    assert result["requested_project"] == "projB"
    assert result["requested_agent"] == "agent2"
    # Memory must NOT have been stored.
    assert len(store._memories) == 0, "memory should not be stored on denial"
    print("PASS: test_layer3_capture_scope_mismatch_returns_error_dict")


def test_layer3_capture_missing_caller_project_returns_error_dict():
    """Layer 3: missing caller_project returns structured error dict."""
    service, store = _make_service()
    ctx = {"caller_agent": "agent1"}  # caller_project missing
    result = service.capture(
        Memory("hello world", "test", Scope("projA", "agent1"), 0.5, 0.5),
        caller_context=ctx,
    )
    assert isinstance(result, dict)
    assert result["error"] == "authorization_denied"
    assert result["reason"] == "missing caller_project"
    print("PASS: test_layer3_capture_missing_caller_project_returns_error_dict")


def test_layer3_retrieve_valid_scope_passes():
    """Layer 3: valid scope passes — service returns results."""
    service, store = _make_service()
    ctx = _make_caller_context("projA", "agent1")
    service.capture(
        Memory("hello world", "test", Scope("projA", "agent1"), 0.5, 0.5),
        caller_context=ctx,
    )
    result = service.retrieve("hello", Scope("projA", "agent1"), caller_context=ctx)
    assert isinstance(result, list)
    assert len(result) == 1
    print("PASS: test_layer3_retrieve_valid_scope_passes")


def test_layer3_retrieve_scope_mismatch_returns_error_dict():
    """Layer 3: retrieve scope mismatch returns structured error dict."""
    service, store = _make_service()
    ctx = _make_caller_context("projA", "agent1")
    service.capture(
        Memory("hello world", "test", Scope("projA", "agent1"), 0.5, 0.5),
        caller_context=ctx,
    )
    result = service.retrieve("hello", Scope("projB", "agent2"), caller_context=ctx)
    assert isinstance(result, dict)
    assert result["error"] == "authorization_denied"
    assert result["reason"] == "scope mismatch"
    print("PASS: test_layer3_retrieve_scope_mismatch_returns_error_dict")


def test_layer4_validate_memory_bound_scope_check():
    """Layer 4: validate checks caller context against memory's stored scope."""
    service, store = _make_service()
    ctx = _make_caller_context("projA", "agent1")
    memory = service.capture(
        Memory("hello world", "test", Scope("projA", "agent1"), 0.5, 0.5),
        caller_context=ctx,
    )
    # Valid caller context — validate succeeds.
    updated = service.validate(memory.memory_id, ValidationState.VALIDATED, caller_context=ctx)
    assert isinstance(updated, Memory)
    assert updated.validation == ValidationState.VALIDATED
    # Mismatched caller context — validate returns error dict.
    wrong_ctx = _make_caller_context("projB", "agent2")
    result = service.validate(memory.memory_id, ValidationState.DISPUTED, caller_context=wrong_ctx)
    assert isinstance(result, dict)
    assert result["error"] == "authorization_denied"
    assert result["reason"] == "scope mismatch"
    assert result["memory_scope"] == {"project": "projA", "agent": "agent1"}
    # Memory must NOT have been updated to DISPUTED.
    current = store.get(memory.memory_id)
    assert current.validation == ValidationState.VALIDATED, "memory should not be updated on denial"
    print("PASS: test_layer4_validate_memory_bound_scope_check")


# ---------------------------------------------------------------------------
# Layer 5 tests: authorization audit (authorization_decided event)
# ---------------------------------------------------------------------------

def test_layer5_audit_event_on_allow():
    """Layer 5: allow decision appends authorization_decided event."""
    service, store = _make_service()
    ctx = _make_caller_context("projA", "agent1")
    service.capture(
        Memory("hello world", "test", Scope("projA", "agent1"), 0.5, 0.5),
        caller_context=ctx,
    )
    # Find the authorization_decided event.
    auth_events = [e for e in store._events if e.kind == "authorization_decided"]
    assert len(auth_events) == 1, f"expected 1 auth event, got {len(auth_events)}"
    event = auth_events[0]
    assert event.outcome == "allow"
    assert event.evidence["caller_project"] == "projA"
    assert event.evidence["caller_agent"] == "agent1"
    assert event.evidence["requested_project"] == "projA"
    assert event.evidence["requested_agent"] == "agent1"
    assert event.evidence["outcome"] == "allow"
    # Allow events MUST NOT include denial_reason.
    assert "denial_reason" not in event.evidence, "allow event should not have denial_reason"
    print("PASS: test_layer5_audit_event_on_allow")


def test_layer5_audit_event_on_deny_includes_reason():
    """Layer 5: deny decision appends authorization_decided event WITH denial_reason."""
    service, store = _make_service()
    ctx = _make_caller_context("projA", "agent1")
    service.capture(
        Memory("hello world", "test", Scope("projB", "agent2"), 0.5, 0.5),
        caller_context=ctx,
    )
    auth_events = [e for e in store._events if e.kind == "authorization_decided"]
    assert len(auth_events) == 1
    event = auth_events[0]
    assert event.outcome == "deny"
    assert event.evidence["caller_project"] == "projA"
    assert event.evidence["caller_agent"] == "agent1"
    assert event.evidence["requested_project"] == "projB"
    assert event.evidence["requested_agent"] == "agent2"
    assert event.evidence["outcome"] == "deny"
    # CRITICAL: deny event MUST include denial_reason.
    assert "denial_reason" in event.evidence, "deny event MUST include denial_reason"
    assert event.evidence["denial_reason"] == "scope mismatch"
    print("PASS: test_layer5_audit_event_on_deny_includes_reason")


def test_layer5_audit_event_on_missing_caller_project():
    """Layer 5: missing caller_project produces deny event with denial_reason."""
    service, store = _make_service()
    ctx = {"caller_agent": "agent1"}  # caller_project missing
    service.capture(
        Memory("hello world", "test", Scope("projA", "agent1"), 0.5, 0.5),
        caller_context=ctx,
    )
    auth_events = [e for e in store._events if e.kind == "authorization_decided"]
    assert len(auth_events) == 1
    event = auth_events[0]
    assert event.outcome == "deny"
    assert event.evidence["denial_reason"] == "missing caller_project"
    print("PASS: test_layer5_audit_event_on_missing_caller_project")


def test_layer5_audit_event_for_validate_includes_memory_id():
    """Layer 5: validate authorization event includes target memory_id."""
    service, store = _make_service()
    ctx = _make_caller_context("projA", "agent1")
    memory = service.capture(
        Memory("hello world", "test", Scope("projA", "agent1"), 0.5, 0.5),
        caller_context=ctx,
    )
    # Wrong context — should produce deny event with memory_id.
    wrong_ctx = _make_caller_context("projB", "agent2")
    service.validate(memory.memory_id, ValidationState.DISPUTED, caller_context=wrong_ctx)
    auth_events = [e for e in store._events if e.kind == "authorization_decided"]
    # Two auth events: one allow (capture), one deny (validate).
    assert len(auth_events) == 2
    deny_event = [e for e in auth_events if e.outcome == "deny"][0]
    assert deny_event.evidence["memory_id"] == memory.memory_id
    assert deny_event.evidence["denial_reason"] == "scope mismatch"
    print("PASS: test_layer5_audit_event_for_validate_includes_memory_id")


# ---------------------------------------------------------------------------
# Layer 2 tests: tool-layer scope check (hard raise)
# ---------------------------------------------------------------------------

def _make_tool_with_context(tool_cls, caller_project: str | None, caller_agent: str | None):
    """Construct a tool instance with a mock agent.context."""
    tool = tool_cls.__new__(tool_cls)
    tool.agent = MagicMock()
    if caller_project is None and caller_agent is None:
        tool.agent.context = None
    else:
        tool.agent.context = MagicMock()
        tool.agent.context.caller_project = caller_project
        tool.agent.context.caller_agent = caller_agent
    return tool


def test_layer2_capture_hard_raises_on_scope_mismatch():
    """Layer 2: capture tool hard raises AuthorizationError on scope mismatch."""
    from tools.neuro_core_2_capture import NeuroCore2Capture
    tool = _make_tool_with_context(NeuroCore2Capture, "projA", "agent1")
    tool.args = {"text": "hello", "project": "projB", "agent": "agent2"}
    try:
        tool._check_scope_or_raise(tool._derive_caller_context(), "projB", "agent2")
        assert False, "expected AuthorizationError"
    except AuthorizationError as e:
        assert "scope mismatch" in str(e)
    print("PASS: test_layer2_capture_hard_raises_on_scope_mismatch")


def test_layer2_capture_hard_raises_on_missing_caller_context():
    """Layer 2: capture tool hard raises when self.agent.context is None."""
    from tools.neuro_core_2_capture import NeuroCore2Capture
    tool = _make_tool_with_context(NeuroCore2Capture, None, None)
    tool.args = {"text": "hello", "project": "projA", "agent": "agent1"}
    try:
        tool._check_scope_or_raise(tool._derive_caller_context(), "projA", "agent1")
        assert False, "expected AuthorizationError"
    except AuthorizationError as e:
        assert "missing caller context" in str(e)
    print("PASS: test_layer2_capture_hard_raises_on_missing_caller_context")


def test_layer2_capture_passes_on_valid_scope():
    """Layer 2: capture tool passes when caller scope matches requested scope."""
    from tools.neuro_core_2_capture import NeuroCore2Capture
    tool = _make_tool_with_context(NeuroCore2Capture, "projA", "agent1")
    tool.args = {"text": "hello", "project": "projA", "agent": "agent1"}
    # Should not raise.
    tool._check_scope_or_raise(tool._derive_caller_context(), "projA", "agent1")
    print("PASS: test_layer2_capture_passes_on_valid_scope")


def test_layer2_retrieve_hard_raises_on_scope_mismatch():
    """Layer 2: retrieve tool hard raises AuthorizationError on scope mismatch."""
    from tools.neuro_core_2_retrieve import NeuroCore2Retrieve
    tool = _make_tool_with_context(NeuroCore2Retrieve, "projA", "agent1")
    tool.args = {"query": "hello", "project": "projB", "agent": "agent2"}
    try:
        tool._check_scope_or_raise(tool._derive_caller_context(), "projB", "agent2")
        assert False, "expected AuthorizationError"
    except AuthorizationError as e:
        assert "scope mismatch" in str(e)
    print("PASS: test_layer2_retrieve_hard_raises_on_scope_mismatch")


def test_layer2_retrieve_passes_on_valid_scope():
    """Layer 2: retrieve tool passes when caller scope matches requested scope."""
    from tools.neuro_core_2_retrieve import NeuroCore2Retrieve
    tool = _make_tool_with_context(NeuroCore2Retrieve, "projA", "agent1")
    tool.args = {"query": "hello", "project": "projA", "agent": "agent1"}
    tool._check_scope_or_raise(tool._derive_caller_context(), "projA", "agent1")
    print("PASS: test_layer2_retrieve_passes_on_valid_scope")


def test_layer2_validate_hard_raises_on_missing_caller_context():
    """Layer 2: validate tool hard raises when self.agent.context is None."""
    from tools.neuro_core_2_validate import NeuroCore2Validate
    tool = _make_tool_with_context(NeuroCore2Validate, None, None)
    tool.args = {"memory_id": "abc", "target": "validated"}
    try:
        tool._check_caller_context_or_raise(tool._derive_caller_context())
        assert False, "expected AuthorizationError"
    except AuthorizationError as e:
        assert "missing caller context" in str(e)
    print("PASS: test_layer2_validate_hard_raises_on_missing_caller_context")


def test_layer2_validate_hard_raises_on_missing_caller_project():
    """Layer 2: validate tool hard raises when caller_project is None."""
    from tools.neuro_core_2_validate import NeuroCore2Validate
    tool = _make_tool_with_context(NeuroCore2Validate, None, "agent1")
    tool.args = {"memory_id": "abc", "target": "validated"}
    try:
        tool._check_caller_context_or_raise(tool._derive_caller_context())
        assert False, "expected AuthorizationError"
    except AuthorizationError as e:
        assert "missing caller_project" in str(e)
    print("PASS: test_layer2_validate_hard_raises_on_missing_caller_project")


def test_layer2_validate_passes_on_populated_caller_context():
    """Layer 2: validate tool passes when caller context is populated."""
    from tools.neuro_core_2_validate import NeuroCore2Validate
    tool = _make_tool_with_context(NeuroCore2Validate, "projA", "agent1")
    tool.args = {"memory_id": "abc", "target": "validated"}
    tool._check_caller_context_or_raise(tool._derive_caller_context())
    print("PASS: test_layer2_validate_passes_on_populated_caller_context")


# ---------------------------------------------------------------------------
# Backward compatibility: existing service behavior preserved
# ---------------------------------------------------------------------------

def test_backward_compat_capture_without_caller_context():
    """Existing callers that don't pass caller_context still work."""
    service, store = _make_service()
    result = service.capture(
        Memory("hello world", "test", Scope("projA", "agent1"), 0.5, 0.5),
    )
    assert isinstance(result, Memory)
    assert result.text == "hello world"
    print("PASS: test_backward_compat_capture_without_caller_context")


def test_backward_compat_retrieve_without_caller_context():
    """Existing callers that don't pass caller_context still work."""
    service, store = _make_service()
    service.capture(
        Memory("hello world", "test", Scope("projA", "agent1"), 0.5, 0.5),
    )
    result = service.retrieve("hello", Scope("projA", "agent1"))
    assert isinstance(result, list)
    assert len(result) == 1
    print("PASS: test_backward_compat_retrieve_without_caller_context")


def test_backward_compat_validate_without_caller_context():
    """Existing callers that don't pass caller_context still work."""
    service, store = _make_service()
    memory = service.capture(
        Memory("hello world", "test", Scope("projA", "agent1"), 0.5, 0.5),
    )
    updated = service.validate(memory.memory_id, ValidationState.VALIDATED)
    assert isinstance(updated, Memory)
    assert updated.validation == ValidationState.VALIDATED
    print("PASS: test_backward_compat_validate_without_caller_context")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main():
    tests = [
        # Layer 3
        test_layer3_capture_valid_scope_passes,
        test_layer3_capture_scope_mismatch_returns_error_dict,
        test_layer3_capture_missing_caller_project_returns_error_dict,
        test_layer3_retrieve_valid_scope_passes,
        test_layer3_retrieve_scope_mismatch_returns_error_dict,
        test_layer4_validate_memory_bound_scope_check,
        # Layer 5
        test_layer5_audit_event_on_allow,
        test_layer5_audit_event_on_deny_includes_reason,
        test_layer5_audit_event_on_missing_caller_project,
        test_layer5_audit_event_for_validate_includes_memory_id,
        # Layer 2
        test_layer2_capture_hard_raises_on_scope_mismatch,
        test_layer2_capture_hard_raises_on_missing_caller_context,
        test_layer2_capture_passes_on_valid_scope,
        test_layer2_retrieve_hard_raises_on_scope_mismatch,
        test_layer2_retrieve_passes_on_valid_scope,
        test_layer2_validate_hard_raises_on_missing_caller_context,
        test_layer2_validate_hard_raises_on_missing_caller_project,
        test_layer2_validate_passes_on_populated_caller_context,
        # Backward compat
        test_backward_compat_capture_without_caller_context,
        test_backward_compat_retrieve_without_caller_context,
        test_backward_compat_validate_without_caller_context,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {passed + failed} total")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
