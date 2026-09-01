"""Layer 2 identity-binding tests (sub-step C of WI-2026-08-31-AUTHORIZATION-POLICY-REDESIGN).

Covers the re-based Layer 2 scope binding in the three tools and the service
layer onto caller_identity.derive_caller_identity, with audited
authorization/denial events:

- scope-match allow (identity-tuple binding)
- scope-mismatch deny with audited denial event (identity_source + denial_reason)
- sentinel 'agent:None' binding: allow when requested agent factor is None;
  deny on a caller-supplied concrete agent value
- validate target-scope derivation (active-project and fallback paths);
  validate never accepts an unrestricted caller-supplied scope
- flag-False behavior unchanged (AUTHORIZATION_ENFORCEMENT_ACTIVE stays False
  in all 3 tools; the binding path is exercised via flag=True in fixtures only)

Binding-not-authentication: these tests verify scope BINDING against
host-derived identity factors, not caller authentication. No
security-assurance property is claimed.
"""
from __future__ import annotations

import asyncio
import contextlib
import sys
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

HERE = Path(__file__).resolve().parent
PLUGIN_DIR = HERE.parent
sys.path.insert(0, str(PLUGIN_DIR))
sys.path.insert(0, "/a0")  # for helpers.tool / helpers.projects (framework)

from activity_ledger import ActivityLedger
from caller_identity import (
    AGENT_NONE_SENTINEL,
    IDENTITY_SOURCE_ACTIVE_PROJECT,
    IDENTITY_SOURCE_DEFAULT_SCOPE_FALLBACK,
    derive_caller_identity,
)
from memory_lifecycle import ValidationState
from memory_store import MemoryStore
from neuro_core_2 import Memory, Scope
from neuro_core_2_service import AuthorizationError, NeuroCoreService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class InMemoryStore(MemoryStore):
    """Minimal in-memory MemoryStore with inspectable activity events."""

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
            if terms & set(m.text.lower().split()):
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
    return NeuroCoreService(store, ledger), store


def _identity(
    project: str = "projA",
    agent_name: str | None = "agent1",
    source: str = IDENTITY_SOURCE_ACTIVE_PROJECT,
) -> dict:
    return {
        "caller_project": project,
        "identity_source": source,
        "agent_name": agent_name,
        "profile": "test-profile",
        "agent_factor": agent_name if agent_name else AGENT_NONE_SENTINEL,
    }


def _auth_events(store: InMemoryStore) -> list:
    return [
        e for e in store.list_events() if e.kind == "authorization_decided"
    ]


@contextlib.contextmanager
def _enforcement(module, active: bool):
    """Temporarily set a tool module's AUTHORIZATION_ENFORCEMENT_ACTIVE flag."""
    original = module.AUTHORIZATION_ENFORCEMENT_ACTIVE
    module.AUTHORIZATION_ENFORCEMENT_ACTIVE = active
    try:
        yield
    finally:
        module.AUTHORIZATION_ENFORCEMENT_ACTIVE = original


def _make_tool(tool_cls, agent_name: str | None = "agent1", profile: str = "test"):
    """Construct a tool instance with a mock agent (no caller-context fields)."""
    tool = tool_cls.__new__(tool_cls)
    tool.agent = MagicMock()
    tool.agent.agent_name = agent_name
    tool.agent.config.profile = profile
    tool.agent.context = MagicMock()  # host context object (no caller_* fields)
    return tool


@contextlib.contextmanager
def _active_project(project: str | None):
    """Patch helpers.projects.get_context_project_name for identity derivation."""
    from helpers import projects

    original = projects.get_context_project_name
    if project is None:
        projects.get_context_project_name = lambda ctx: None
    else:
        projects.get_context_project_name = lambda ctx: project
    try:
        yield
    finally:
        projects.get_context_project_name = original


@contextlib.contextmanager
def _tmp_config(module, tmpdir: str | None = None, default_project: str = "default"):
    """Patch a tool module's load_config to a temp database + default_scope."""
    import tempfile as _tempfile

    cleanup_dir = False
    if tmpdir is None:
        tmpdir = _tempfile.mkdtemp(prefix="nc2-test-")
        cleanup_dir = True
    original = module.load_config

    def fake_config():
        return {
            "database_path": str(Path(tmpdir) / "neuro_core_2.db"),
            "default_scope": {"project": default_project},
            "max_results": 100,
        }

    module.load_config = fake_config
    try:
        yield tmpdir
    finally:
        module.load_config = original
        if cleanup_dir:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Service Layer 3: identity-tuple binding (identity_source present)
# ---------------------------------------------------------------------------

def test_layer3_identity_binding_allow_on_scope_match():
    """Identity-tuple binding: matching scope allows capture and audits allow."""
    service, store = _make_service()
    ctx = _identity("projA", "agent1")
    result = service.capture(
        Memory("hello world", "test", Scope("projA", "agent1"), 0.5, 0.5),
        caller_context=ctx,
    )
    assert isinstance(result, Memory)
    events = [e for e in store.list_events() if e.kind == "authorization_decided"]
    assert len(events) == 1
    assert events[0].outcome == "allow"
    assert events[0].evidence["identity_source"] == "active-project"
    assert events[0].evidence["agent_factor"] == "agent1"
    print("PASS: test_layer3_identity_binding_allow_on_scope_match")


def test_layer3_identity_binding_deny_on_project_mismatch_with_audited_event():
    """Mismatch deny returns structured error and audits identity_source + reason."""
    service, store = _make_service()
    ctx = _identity("projA", "agent1")
    result = service.capture(
        Memory("hello world", "test", Scope("projB", "agent1"), 0.5, 0.5),
        caller_context=ctx,
    )
    assert isinstance(result, dict) and result.get("error") == "authorization_denied"
    assert "scope mismatch" in result["reason"]
    events = [e for e in store.list_events() if e.kind == "authorization_decided"]
    assert len(events) == 1
    assert events[0].outcome == "deny"
    assert events[0].evidence["identity_source"] == "active-project"
    assert events[0].evidence["denial_reason"]
    assert events[0].evidence["requested_project"] == "projB"
    print("PASS: test_layer3_identity_binding_deny_on_project_mismatch_with_audited_event")


def test_layer3_identity_binding_deny_on_agent_factor_mismatch_with_audited_event():
    """Agent-factor mismatch denies with audited denial event."""
    service, store = _make_service()
    ctx = _identity("projA", "agent1")
    result = service.capture(
        Memory("hello world", "test", Scope("projA", "agent2"), 0.5, 0.5),
        caller_context=ctx,
    )
    assert isinstance(result, dict) and result.get("error") == "authorization_denied"
    events = [e for e in store.list_events() if e.kind == "authorization_decided"]
    assert len(events) == 1
    assert events[0].outcome == "deny"
    assert events[0].evidence["identity_source"] == "active-project"
    assert "agent factor" in events[0].evidence["denial_reason"]
    print("PASS: test_layer3_identity_binding_deny_on_agent_factor_mismatch_with_audited_event")


def test_layer3_sentinel_binding_allows_none_requested_agent():
    """Sentinel: derived agent:None + requested agent None binds (allow)."""
    service, store = _make_service()
    ctx = _identity("projA", agent_name=None)
    assert ctx["agent_factor"] == AGENT_NONE_SENTINEL
    result = service.capture(
        Memory("hello world", "test", Scope("projA", None), 0.5, 0.5),
        caller_context=ctx,
    )
    assert isinstance(result, Memory)
    events = [e for e in store.list_events() if e.kind == "authorization_decided"]
    assert len(events) == 1 and events[0].outcome == "allow"
    assert events[0].evidence["agent_factor"] == AGENT_NONE_SENTINEL
    print("PASS: test_layer3_sentinel_binding_allows_none_requested_agent")


def test_layer3_sentinel_binding_denies_caller_supplied_concrete_agent():
    """Sentinel: derived agent:None + caller-supplied concrete agent denies."""
    service, store = _make_service()
    ctx = _identity("projA", agent_name=None)
    result = service.capture(
        Memory("hello world", "test", Scope("projA", "agent1"), 0.5, 0.5),
        caller_context=ctx,
    )
    assert isinstance(result, dict) and result.get("error") == "authorization_denied"
    events = [e for e in store.list_events() if e.kind == "authorization_decided"]
    assert len(events) == 1
    assert events[0].outcome == "deny"
    assert "agent factor" in events[0].evidence["denial_reason"]
    print("PASS: test_layer3_sentinel_binding_denies_caller_supplied_concrete_agent")


def test_layer3_fallback_identity_recorded_in_audit_event():
    """Fallback identity (default-scope-fallback) is recorded in the audit event."""
    service, store = _make_service()
    ctx = _identity("default", "agent1", source=IDENTITY_SOURCE_DEFAULT_SCOPE_FALLBACK)
    result = service.capture(
        Memory("hello world", "test", Scope("default", "agent1"), 0.5, 0.5),
        caller_context=ctx,
    )
    assert isinstance(result, Memory)
    events = [e for e in store.list_events() if e.kind == "authorization_decided"]
    assert events[0].evidence["identity_source"] == "default-scope-fallback"
    print("PASS: test_layer3_fallback_identity_recorded_in_audit_event")


def test_layer4_validate_identity_binding_allow_and_deny():
    """Layer 4 memory-bound check binds the memory scope against identity."""
    service, store = _make_service()
    mem = service.capture(
        Memory("to validate", "test", Scope("projA", "agent1"), 0.5, 0.5)
    )
    # Matching identity: transition applies.
    ctx = _identity("projA", "agent1")
    updated = service.validate(
        mem.memory_id, ValidationState("validated"), caller_context=ctx
    )
    assert not isinstance(updated, dict)
    assert updated.validation.value == "validated"
    # Mismatching identity: structured denial, memory unchanged.
    ctx_bad = _identity("projB", "agent1")
    result = service.validate(
        mem.memory_id, ValidationState("disputed"), caller_context=ctx_bad
    )
    assert isinstance(result, dict) and result.get("error") == "authorization_denied"
    events = [e for e in store.list_events() if e.kind == "authorization_decided"]
    assert events[-1].outcome == "deny"
    assert events[-1].evidence["identity_source"] == "active-project"
    print("PASS: test_layer4_validate_identity_binding_allow_and_deny")


def test_record_tool_layer_denial_event_shape():
    """record_tool_layer_denial records identity_source + reason, no credentials."""
    service, store = _make_service()
    identity = _identity("projA", "agent1")
    service.record_tool_layer_denial(
        identity, "projB", "agent2", "scope mismatch: project"
    )
    events = [e for e in store.list_events() if e.kind == "authorization_decided"]
    assert len(events) == 1
    ev = events[0]
    assert ev.outcome == "deny"
    assert ev.evidence["identity_source"] == "active-project"
    assert ev.evidence["denial_reason"] == "scope mismatch: project"
    assert ev.evidence["layer"] == "tool-layer"
    # ARC condition 7: no credential/secret material in evidence.
    blob = str(ev.evidence)
    for forbidden in ("password", "token", "secret", "api_key"):
        assert forbidden not in blob.lower()
    print("PASS: test_record_tool_layer_denial_event_shape")


# ---------------------------------------------------------------------------
# Tool Layer 2: re-based binding (flag=True in fixtures only)
# ---------------------------------------------------------------------------

def test_layer2_capture_identity_binding_allow():
    """Capture (flag=True): matching derived identity allows dispatch."""
    from tools import neuro_core_2_capture as mod

    assert mod.AUTHORIZATION_ENFORCEMENT_ACTIVE is False  # unchanged default
    with _tmp_config(mod) as tmpdb:
        tool = _make_tool(mod.NeuroCore2Capture, agent_name="agent1")
        tool.args = {"text": "hello", "project": "projA", "agent": "agent1"}
        with _enforcement(mod, True), _active_project("projA"):
            resp = asyncio.get_event_loop().run_until_complete(tool.execute())
    assert resp.break_loop is False
    print("PASS: test_layer2_capture_identity_binding_allow")


def test_layer2_capture_identity_binding_deny_audited():
    """Capture (flag=True): mismatched requested project denies with audited event."""
    from tools import neuro_core_2_capture as mod

    with _tmp_config(mod) as tmpdb:
        tool = _make_tool(mod.NeuroCore2Capture, agent_name="agent1")
        tool.args = {"text": "hello", "project": "projB", "agent": "agent1"}
        recorded = []
        tool._record_denial_event = (
            lambda identity, project, agent, reason: recorded.append(
                (identity, project, agent, reason)
            )
        )
        with _enforcement(mod, True), _active_project("projA"):
            try:
                asyncio.get_event_loop().run_until_complete(tool.execute())
                assert False, "expected AuthorizationError"
            except AuthorizationError as e:
                assert "scope mismatch" in str(e)
        assert len(recorded) == 1
        identity, project, agent, reason = recorded[0]
        assert identity["identity_source"] == "active-project"
        assert identity["caller_project"] == "projA"
        assert project == "projB"
        assert "scope mismatch" in reason
    print("PASS: test_layer2_capture_identity_binding_deny_audited")


def test_layer2_capture_sentinel_denies_concrete_agent():
    """Capture (flag=True): agent:None sentinel denies caller-supplied agent."""
    from tools import neuro_core_2_capture as mod

    with _tmp_config(mod) as tmpdb:
        tool = _make_tool(mod.NeuroCore2Capture, agent_name=None)
        tool.args = {"text": "hello", "project": "projA", "agent": "agent1"}
        with _enforcement(mod, True), _active_project("projA"):
            try:
                asyncio.get_event_loop().run_until_complete(tool.execute())
                assert False, "expected AuthorizationError"
            except AuthorizationError as e:
                assert "agent factor" in str(e)
    print("PASS: test_layer2_capture_sentinel_denies_concrete_agent")


def test_layer2_retrieve_identity_binding_allow_and_deny():
    """Retrieve (flag=True): allow on match, deny with audited event on mismatch."""
    from tools import neuro_core_2_retrieve as mod

    assert mod.AUTHORIZATION_ENFORCEMENT_ACTIVE is False  # unchanged default
    with _tmp_config(mod) as tmpdb:
        # Allow path.
        tool = _make_tool(mod.NeuroCore2Retrieve, agent_name="agent1")
        tool.args = {"query": "hello", "project": "projA", "agent": "agent1"}
        with _enforcement(mod, True), _active_project("projA"):
            resp = asyncio.get_event_loop().run_until_complete(tool.execute())
        assert resp.break_loop is False
        # Deny path.
        tool2 = _make_tool(mod.NeuroCore2Retrieve, agent_name="agent1")
        tool2.args = {"query": "hello", "project": "projB", "agent": "agent1"}
        recorded = []
        tool2._record_denial_event = (
            lambda identity, project, agent, reason: recorded.append(reason)
        )
        with _enforcement(mod, True), _active_project("projA"):
            try:
                asyncio.get_event_loop().run_until_complete(tool2.execute())
                assert False, "expected AuthorizationError"
            except AuthorizationError as e:
                assert "scope mismatch" in str(e)
        assert len(recorded) == 1
    print("PASS: test_layer2_retrieve_identity_binding_allow_and_deny")


def test_layer2_validate_rejects_caller_supplied_scope():
    """Validate (flag=True): caller-supplied project/agent args are rejected."""
    from tools import neuro_core_2_validate as mod

    with _tmp_config(mod) as tmpdb:
        tool = _make_tool(mod.NeuroCore2Validate, agent_name="agent1")
        tool.args = {
            "memory_id": "abc", "target": "validated",
            "project": "projZ", "agent": "agentZ",
        }
        recorded = []
        tool._record_denial_event = (
            lambda identity, project, agent, reason: recorded.append(reason)
        )
        with _enforcement(mod, True), _active_project("projA"):
            try:
                asyncio.get_event_loop().run_until_complete(tool.execute())
                assert False, "expected AuthorizationError"
            except AuthorizationError as e:
                assert "caller-supplied scope" in str(e)
        assert len(recorded) == 1
    print("PASS: test_layer2_validate_rejects_caller_supplied_scope")


def test_layer2_validate_target_scope_derivation_active_project():
    """Validate derives target scope from active-project identity (flag=True)."""
    from tools import neuro_core_2_validate as mod

    with _tmp_config(mod, default_project="default") as tmpdb:
        tool = _make_tool(mod.NeuroCore2Validate, agent_name="agent1")
        tool.args = {"memory_id": "abc", "target": "validated"}
        with _enforcement(mod, True), _active_project("projA"):
            identity = tool._derive_caller_identity()
        assert identity["identity_source"] == "active-project"
        assert identity["caller_project"] == "projA"
        # Binding against the derived scope succeeds; any other project fails.
        from caller_identity import scope_binding_denial
        assert scope_binding_denial(identity, "projA", "agent1") is None
        assert scope_binding_denial(identity, "projB", "agent1") is not None
    print("PASS: test_layer2_validate_target_scope_derivation_active_project")


def test_layer2_validate_target_scope_derivation_fallback():
    """Validate under fallback identity binds at most to default_scope (flag=True)."""
    from tools import neuro_core_2_validate as mod

    with _tmp_config(mod, default_project="default") as tmpdb:
        tool = _make_tool(mod.NeuroCore2Validate, agent_name="agent1")
        tool.args = {"memory_id": "abc", "target": "validated"}
        with _enforcement(mod, True), _active_project(None):
            identity = tool._derive_caller_identity()
        assert identity["identity_source"] == "default-scope-fallback"
        assert identity["caller_project"] == "default"
        from caller_identity import scope_binding_denial
        # Binds to the configured default_scope only — never a caller value.
        assert scope_binding_denial(identity, "default", "agent1") is None
        assert scope_binding_denial(identity, "other", "agent1") is not None
    print("PASS: test_layer2_validate_target_scope_derivation_fallback")


# ---------------------------------------------------------------------------
# Flag-False behavior unchanged (default state)
# ---------------------------------------------------------------------------

def test_flag_false_all_tools_behavior_unchanged():
    """Flag False (default): no enforcement, warning logged, dispatch proceeds."""
    from tools import neuro_core_2_capture as cap_mod
    from tools import neuro_core_2_retrieve as ret_mod
    from tools import neuro_core_2_validate as val_mod

    for mod in (cap_mod, ret_mod, val_mod):
        assert mod.AUTHORIZATION_ENFORCEMENT_ACTIVE is False

    with _tmp_config(cap_mod) as tmpdb:
        tool = _make_tool(cap_mod.NeuroCore2Capture, agent_name="agent1")
        tool.args = {"text": "hello", "project": "projB", "agent": "agent2"}
        recorded = []
        tool._record_denial_event = (
            lambda identity, project, agent, reason: recorded.append(reason)
        )
        with _active_project("projA"):
            # Flag False: mismatched requested scope does NOT deny.
            resp = asyncio.get_event_loop().run_until_complete(tool.execute())
        assert resp.break_loop is False
        assert recorded == []

    # Validate with flag False: caller-supplied scope args are ignored (no deny).
    with _tmp_config(val_mod) as tmpdb:
        # Pre-create a real memory so the not-found path is not exercised here.
        from sqlite_store import SQLiteStore

        db_path = str(Path(tmpdb) / "neuro_core_2.db")
        seed_store = SQLiteStore(db_path)
        seed_mem = Memory("seed memory", "test", Scope("projA", "agent1"), 0.5, 0.5)
        seed_store.put(seed_mem)

        tool = _make_tool(val_mod.NeuroCore2Validate, agent_name="agent1")
        tool.args = {
            "memory_id": seed_mem.memory_id, "target": "validated",
            "project": "projZ", "agent": "agentZ",
        }
        recorded = []
        tool._record_denial_event = (
            lambda identity, project, agent, reason: recorded.append(reason)
        )
        with _active_project("projA"):
            resp = asyncio.get_event_loop().run_until_complete(tool.execute())
        # No tool-layer denial recorded; validation succeeds (flag False =
        # unchanged behavior, caller-supplied scope args not bound).
        assert recorded == []
        assert "Validated memory" in resp.message
    print("PASS: test_flag_false_all_tools_behavior_unchanged")


def test_flag_false_forwards_no_caller_context():
    """Flag False: tools forward no caller_context (service legacy path)."""
    from tools import neuro_core_2_capture as mod

    with _tmp_config(mod) as tmpdb:
        tool = _make_tool(mod.NeuroCore2Capture, agent_name="agent1")
        forwarded = {}
        original = mod.NeuroCoreService.capture

        def spy_capture(self, *args, **kwargs):
            forwarded["caller_context"] = kwargs.get("caller_context")
            return original(self, *args, **kwargs)

        mod.NeuroCoreService.capture = spy_capture
        try:
            tool.args = {"text": "hello", "project": "projA", "agent": "agent1"}
            with _active_project("projA"):
                asyncio.get_event_loop().run_until_complete(tool.execute())
        finally:
            mod.NeuroCoreService.capture = original
        assert forwarded["caller_context"] is None
    print("PASS: test_flag_false_forwards_no_caller_context")


if __name__ == "__main__":
    test_layer3_identity_binding_allow_on_scope_match()
    test_layer3_identity_binding_deny_on_project_mismatch_with_audited_event()
    test_layer3_identity_binding_deny_on_agent_factor_mismatch_with_audited_event()
    test_layer3_sentinel_binding_allows_none_requested_agent()
    test_layer3_sentinel_binding_denies_caller_supplied_concrete_agent()
    test_layer3_fallback_identity_recorded_in_audit_event()
    test_layer4_validate_identity_binding_allow_and_deny()
    test_record_tool_layer_denial_event_shape()
    test_layer2_capture_identity_binding_allow()
    test_layer2_capture_identity_binding_deny_audited()
    test_layer2_capture_sentinel_denies_concrete_agent()
    test_layer2_retrieve_identity_binding_allow_and_deny()
    test_layer2_validate_rejects_caller_supplied_scope()
    test_layer2_validate_target_scope_derivation_active_project()
    test_layer2_validate_target_scope_derivation_fallback()
    test_flag_false_all_tools_behavior_unchanged()
    test_flag_false_forwards_no_caller_context()
    print("ALL LAYER 2 IDENTITY-BINDING TESTS PASSED")
