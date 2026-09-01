"""Layer 1 caller-identity derivation for Neuro Core 2 (WI-2026-08-31-AUTHORIZATION-POLICY-REDESIGN).

Supersedes the falsified ADR-0007 Layer 1 premise (host-populated
agent.context.caller_project/caller_agent, empirically proven absent on the
real dispatch path). This module derives caller identity exclusively from
host inputs that verifiably exist at dispatch time:

- caller_project: helpers.projects.get_context_project_name(agent.context)
  (the same active-project identity input helpers/tool_policy.py consumes),
  with an audited fallback to the plugin's configured default_scope.project
  when no active project exists. The fallback is always distinguishable via
  the returned identity_source marker.
- agent_name: self.agent.agent_name (host-assigned at Agent construction).
- profile: agent.config.profile (host configuration).

agent_name and profile are host-controlled scope-BINDING factors, not
authenticated caller identity. No caller-authentication, adversarial-
bypass-resistance, or security-assurance property is claimed or implied.

None/unmapped agent-factor semantics (implementation contract,
none_agent_factor_semantics): when the derived agent_name is None/empty, or
does not match any configured agent-factor mapping, the agent factor binds
as the distinct sentinel value 'agent:None'. The sentinel is derived from
the absence of a host-provided agent mapping, never from caller input.
"""
from __future__ import annotations

from typing import Any

# Distinct identity value for a None/unmapped agent factor (implementation
# contract clause none_agent_factor_semantics).
AGENT_NONE_SENTINEL = "agent:None"

# identity_source marker values (ARC condition 1).
IDENTITY_SOURCE_ACTIVE_PROJECT = "active-project"
IDENTITY_SOURCE_DEFAULT_SCOPE_FALLBACK = "default-scope-fallback"


def resolve_agent_factor(
    agent_name: str | None,
    configured_agent_factors: set[str] | None = None,
) -> str:
    """Resolve the derived agent_name into a scope-binding agent factor.

    Returns AGENT_NONE_SENTINEL when agent_name is None/empty, or when a
    non-empty configured_agent_factors set is supplied and agent_name is not
    a member of it (unmapped agent factor). Otherwise returns agent_name
    unchanged.
    """
    if agent_name is None or str(agent_name).strip() == "":
        return AGENT_NONE_SENTINEL
    if configured_agent_factors is not None and agent_name not in configured_agent_factors:
        return AGENT_NONE_SENTINEL
    return agent_name


def _active_project_name(agent: Any) -> str | None:
    """Read the active project name from host-populated context data.

    Mirrors the identity input consumed by helpers/tool_policy.py. Returns
    None when there is no agent, no context, no reachable helpers.projects,
    or no active project set — the caller then applies the audited fallback.
    """
    if agent is None:
        return None
    ctx = getattr(agent, "context", None)
    if ctx is None:
        return None
    try:
        from helpers import projects  # lazy import, mirrors helpers/tool_policy.py
    except ImportError:
        return None
    try:
        return projects.get_context_project_name(ctx)
    except Exception:
        return None


def derive_caller_identity(
    agent: Any,
    default_scope_project: str,
    configured_agent_factors: set[str] | None = None,
) -> dict:
    """Derive the Layer 1 caller identity from host-provided inputs.

    Args:
        agent: the host-injected agent instance (self.agent on the real
            dispatch path).
        default_scope_project: the plugin's configured default_scope.project
            (operator-controlled, never caller-supplied); used only when no
            active project exists.
        configured_agent_factors: optional set of agent factors with a
            configured scope mapping; agent_name outside this set binds as
            AGENT_NONE_SENTINEL. None means no mapping restriction is
            configured.

    Returns a dict with:
        caller_project: active project name, or the default_scope project
            under fallback.
        identity_source: 'active-project' or 'default-scope-fallback'.
        agent_name: the host-assigned agent name (or None).
        profile: agent.config.profile (or '' when unavailable).
        agent_factor: agent_name, or AGENT_NONE_SENTINEL for a None/unmapped
            agent factor.
    """
    project = _active_project_name(agent)
    if project:
        identity_source = IDENTITY_SOURCE_ACTIVE_PROJECT
    else:
        project = default_scope_project
        identity_source = IDENTITY_SOURCE_DEFAULT_SCOPE_FALLBACK

    agent_name = getattr(agent, "agent_name", None) if agent is not None else None
    config = getattr(agent, "config", None) if agent is not None else None
    profile = str(getattr(config, "profile", "") or "") if config is not None else ""

    return {
        "caller_project": project,
        "identity_source": identity_source,
        "agent_name": agent_name,
        "profile": profile,
        "agent_factor": resolve_agent_factor(agent_name, configured_agent_factors),
    }


def requested_agent_factor(agent: str | None) -> str:
    """Normalize a requested scope's agent factor for binding.

    A None/empty requested agent factor binds as AGENT_NONE_SENTINEL (the
    distinct identity value), never as an unrestricted wildcard.
    """
    if agent is None or str(agent).strip() == "":
        return AGENT_NONE_SENTINEL
    return agent


def scope_binding_denial(
    identity: dict,
    requested_project: str | None,
    requested_agent: str | None,
) -> str | None:
    """Bind a requested Scope(project, agent) against a derived caller identity.

    Layer 2 binding (WI-2026-08-31-AUTHORIZATION-POLICY-REDESIGN): the requested
    scope must MATCH the host/plugin-derived identity tuple
    (caller_project, agent_factor); a caller-supplied scope value can only
    match the derived value, never define it.

    Sentinel semantics (implementation contract, none_agent_factor_semantics):
    when the derived agent factor is AGENT_NONE_SENTINEL, the binding succeeds
    only if the requested agent factor is also None/AGENT_NONE_SENTINEL (or
    explicitly equals the derived agent_name when one exists); any
    caller-supplied concrete agent value is a mismatch.

    Returns None when the binding succeeds, or a denial-reason string naming
    the mismatched scope values only (no credentials, secrets, or identity
    material beyond project name and agent factor — ARC condition 7).
    """
    caller_project = identity.get("caller_project")
    if caller_project != requested_project:
        return (
            "scope mismatch: project "
            f"(caller={caller_project!r}, requested={requested_project!r})"
        )
    derived_factor = identity.get("agent_factor") or AGENT_NONE_SENTINEL
    req_factor = requested_agent_factor(requested_agent)
    agent_name = identity.get("agent_name")
    if req_factor != derived_factor and not (
        agent_name and requested_agent == agent_name
    ):
        return (
            "scope mismatch: agent factor "
            f"(caller={derived_factor!r}, requested={req_factor!r})"
        )
    return None
