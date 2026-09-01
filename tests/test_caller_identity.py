"""Tests for Layer 1 caller-identity derivation (WI-2026-08-31-AUTHORIZATION-POLICY-REDESIGN).

Covers the revised Layer 1 derivation in caller_identity.py:
- active-project path (helpers.projects.get_context_project_name)
- audited fallback to default_scope.project with identity_source marker
- None-context / None-agent path
- None/unmapped agent-factor 'agent:None' sentinel semantics
- profile inclusion as a binding factor

These are unit tests for the derivation module only. Tool rewiring (Layer 2
re-base) is a later sub-step and is intentionally not exercised here.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

HERE = Path(__file__).resolve().parent
PLUGIN_DIR = HERE.parent
sys.path.insert(0, str(PLUGIN_DIR))
sys.path.insert(0, "/a0")  # for helpers.projects (Agent Zero framework)

from caller_identity import (
    AGENT_NONE_SENTINEL,
    IDENTITY_SOURCE_ACTIVE_PROJECT,
    IDENTITY_SOURCE_DEFAULT_SCOPE_FALLBACK,
    derive_caller_identity,
    resolve_agent_factor,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_agent(
    project_name: str | None,
    agent_name: str | None = "A0",
    profile: str | None = "nc2-integrator",
    with_context: bool = True,
) -> MagicMock:
    """Build a mock agent whose context.get_data returns the given project name.

    Mirrors the real host contract: helpers.projects.get_context_project_name
    reads context.get_data(CONTEXT_DATA_KEY_PROJECT).
    """
    agent = MagicMock()
    agent.agent_name = agent_name
    agent.config.profile = profile
    if with_context:
        agent.context.get_data.return_value = project_name
    else:
        agent.context = None
    return agent


# ---------------------------------------------------------------------------
# Active-project path
# ---------------------------------------------------------------------------

def test_active_project_path_derives_project_and_source():
    """Active project set: caller_project comes from context data, source is 'active-project'."""
    agent = _make_agent("my-project", agent_name="A3", profile="developer")
    identity = derive_caller_identity(agent, default_scope_project="default")
    assert identity["caller_project"] == "my-project"
    assert identity["identity_source"] == IDENTITY_SOURCE_ACTIVE_PROJECT
    assert identity["agent_name"] == "A3"
    assert identity["profile"] == "developer"
    assert identity["agent_factor"] == "A3"
    print("PASS: test_active_project_path_derives_project_and_source")


def test_active_project_path_does_not_use_default_scope():
    """Active project set: default_scope.project is not consulted."""
    agent = _make_agent("projA")
    identity = derive_caller_identity(agent, default_scope_project="fallback-proj")
    assert identity["caller_project"] == "projA"
    assert identity["identity_source"] == IDENTITY_SOURCE_ACTIVE_PROJECT
    print("PASS: test_active_project_path_does_not_use_default_scope")


# ---------------------------------------------------------------------------
# Fallback path (identity_source recorded)
# ---------------------------------------------------------------------------

def test_fallback_path_uses_default_scope_and_records_source():
    """No active project: caller_project falls back to default_scope.project,
    identity_source is 'default-scope-fallback'."""
    agent = _make_agent(None, agent_name="A1", profile="researcher")
    identity = derive_caller_identity(agent, default_scope_project="default")
    assert identity["caller_project"] == "default"
    assert identity["identity_source"] == IDENTITY_SOURCE_DEFAULT_SCOPE_FALLBACK
    assert identity["agent_name"] == "A1"
    assert identity["profile"] == "researcher"
    print("PASS: test_fallback_path_uses_default_scope_and_records_source")


def test_fallback_and_active_sources_are_distinguishable():
    """The two identity_source values are distinct, non-empty markers."""
    assert IDENTITY_SOURCE_ACTIVE_PROJECT != IDENTITY_SOURCE_DEFAULT_SCOPE_FALLBACK
    assert IDENTITY_SOURCE_ACTIVE_PROJECT == "active-project"
    assert IDENTITY_SOURCE_DEFAULT_SCOPE_FALLBACK == "default-scope-fallback"
    active = derive_caller_identity(_make_agent("projA"), "default")
    fallback = derive_caller_identity(_make_agent(None), "default")
    assert active["identity_source"] != fallback["identity_source"]
    print("PASS: test_fallback_and_active_sources_are_distinguishable")


def test_fallback_project_is_plugin_configured_not_caller_supplied():
    """Fallback binds exactly the configured default_scope.project value passed
    by the plugin — the derivation never accepts a caller-supplied project."""
    agent = _make_agent(None)
    identity = derive_caller_identity(agent, default_scope_project="operator-configured")
    assert identity["caller_project"] == "operator-configured"
    print("PASS: test_fallback_project_is_plugin_configured_not_caller_supplied")


# ---------------------------------------------------------------------------
# None-context / None-agent path
# ---------------------------------------------------------------------------

def test_none_context_path_falls_back():
    """agent.context is None: derivation falls back to default_scope.project."""
    agent = _make_agent(None, with_context=False, agent_name="A2", profile="default")
    identity = derive_caller_identity(agent, default_scope_project="default")
    assert identity["caller_project"] == "default"
    assert identity["identity_source"] == IDENTITY_SOURCE_DEFAULT_SCOPE_FALLBACK
    assert identity["agent_name"] == "A2"
    print("PASS: test_none_context_path_falls_back")


def test_none_agent_path_falls_back_and_sentinels_agent_factor():
    """agent is None entirely: fallback project, empty profile, sentinel agent factor."""
    identity = derive_caller_identity(None, default_scope_project="default")
    assert identity["caller_project"] == "default"
    assert identity["identity_source"] == IDENTITY_SOURCE_DEFAULT_SCOPE_FALLBACK
    assert identity["agent_name"] is None
    assert identity["profile"] == ""
    assert identity["agent_factor"] == AGENT_NONE_SENTINEL
    print("PASS: test_none_agent_path_falls_back_and_sentinels_agent_factor")


# ---------------------------------------------------------------------------
# None/unmapped agent-factor sentinel
# ---------------------------------------------------------------------------

def test_none_agent_name_binds_sentinel():
    """agent_name None: agent factor is the 'agent:None' sentinel."""
    assert resolve_agent_factor(None) == AGENT_NONE_SENTINEL
    assert resolve_agent_factor(None, configured_agent_factors={"A0"}) == AGENT_NONE_SENTINEL
    print("PASS: test_none_agent_name_binds_sentinel")


def test_empty_agent_name_binds_sentinel():
    """agent_name empty/whitespace: agent factor is the sentinel."""
    assert resolve_agent_factor("") == AGENT_NONE_SENTINEL
    assert resolve_agent_factor("   ") == AGENT_NONE_SENTINEL
    print("PASS: test_empty_agent_name_binds_sentinel")


def test_unmapped_agent_name_binds_sentinel():
    """agent_name outside the configured factor set: sentinel (unmapped agent factor)."""
    assert resolve_agent_factor("A9", configured_agent_factors={"A0", "A1"}) == AGENT_NONE_SENTINEL
    print("PASS: test_unmapped_agent_name_binds_sentinel")


def test_mapped_agent_name_binds_unchanged():
    """agent_name inside the configured factor set (or no set configured): unchanged."""
    assert resolve_agent_factor("A0", configured_agent_factors={"A0", "A1"}) == "A0"
    assert resolve_agent_factor("A0") == "A0"
    print("PASS: test_mapped_agent_name_binds_unchanged")


def test_sentinel_is_distinct_identity_value():
    """The sentinel is the exact contract value and can never collide with a
    host-assigned agent name (host assigns names like 'A<number>')."""
    assert AGENT_NONE_SENTINEL == "agent:None"
    assert resolve_agent_factor(AGENT_NONE_SENTINEL) == AGENT_NONE_SENTINEL
    print("PASS: test_sentinel_is_distinct_identity_value")


def test_derived_sentinel_in_full_identity():
    """End-to-end: a top-level A0 caller with no configured mapping derives
    caller_project + sentinel agent_factor from host/plugin inputs only."""
    agent = _make_agent("projA", agent_name="A0", profile="agent0")
    identity = derive_caller_identity(agent, default_scope_project="default", configured_agent_factors=set())
    assert identity["caller_project"] == "projA"
    assert identity["identity_source"] == IDENTITY_SOURCE_ACTIVE_PROJECT
    assert identity["agent_factor"] == AGENT_NONE_SENTINEL
    print("PASS: test_derived_sentinel_in_full_identity")


# ---------------------------------------------------------------------------
# Profile inclusion
# ---------------------------------------------------------------------------

def test_profile_included_as_binding_factor():
    """agent.config.profile is included in the derived identity."""
    agent = _make_agent("projA", profile="researcher")
    identity = derive_caller_identity(agent, default_scope_project="default")
    assert identity["profile"] == "researcher"
    print("PASS: test_profile_included_as_binding_factor")


def test_missing_config_yields_empty_profile():
    """agent without config: profile is '' (never None, never an exception)."""
    agent = MagicMock()
    agent.agent_name = "A1"
    del agent.config  # attribute absent
    agent.context.get_data.return_value = "projA"
    identity = derive_caller_identity(agent, default_scope_project="default")
    assert identity["profile"] == ""
    assert identity["caller_project"] == "projA"
    print("PASS: test_missing_config_yields_empty_profile")


def test_none_profile_value_normalized_to_empty_string():
    """agent.config.profile = None is normalized to '' (mirrors tool_policy's
    str(getattr(agent.config, 'profile', '') or '') pattern)."""
    agent = _make_agent("projA", profile=None)
    identity = derive_caller_identity(agent, default_scope_project="default")
    assert identity["profile"] == ""
    print("PASS: test_none_profile_value_normalized_to_empty_string")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main():
    tests = [
        test_active_project_path_derives_project_and_source,
        test_active_project_path_does_not_use_default_scope,
        test_fallback_path_uses_default_scope_and_records_source,
        test_fallback_and_active_sources_are_distinguishable,
        test_fallback_project_is_plugin_configured_not_caller_supplied,
        test_none_context_path_falls_back,
        test_none_agent_path_falls_back_and_sentinels_agent_factor,
        test_none_agent_name_binds_sentinel,
        test_empty_agent_name_binds_sentinel,
        test_unmapped_agent_name_binds_sentinel,
        test_mapped_agent_name_binds_unchanged,
        test_sentinel_is_distinct_identity_value,
        test_derived_sentinel_in_full_identity,
        test_profile_included_as_binding_factor,
        test_missing_config_yields_empty_profile,
        test_none_profile_value_normalized_to_empty_string,
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
