"""Neuro Core 2 capture tool.

Per ADR-0007 (authorization policy), this tool implements Layer 2
(tool-layer scope check): hard raise on scope mismatch.

Caller identity is derived from self.agent.context (Layer 1 — caller-context
binding). The host is responsible for populating self.agent.context with
the authenticated caller's identity (caller_project, caller_agent).

On scope mismatch, the tool hard raises AuthorizationError (fail closed,
no silent fallback) and does not invoke the service.
"""
import logging
import sys
from pathlib import Path

from helpers.tool import Response, Tool

_PLUGIN_DIR = Path(__file__).resolve().parent.parent
if str(_PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_DIR))

from neuro_core_2 import Memory, Scope
from neuro_core_2_service import AuthorizationError, NeuroCoreService
from sqlite_store import SQLiteStore
from tools._config import load_config
from caller_identity import derive_caller_identity, scope_binding_denial

# P0 hotfix (WI-2026-08-31-AUTHZ-HOTFIX): Layer 2 authorization enforcement
# is INACTIVE pending redesign (WI-2026-08-31-AUTHORIZATION-POLICY-REDESIGN).
# Empirical finding (VAL blast-radius, 2026-08-31): the host never populates
# agent.context.caller_project/caller_agent, so Layer 2 failed closed on 100%
# of legitimate real-host dispatches. All Layer 2 code below remains intact;
# re-enabling enforcement is a one-line change (set this flag to True).
AUTHORIZATION_ENFORCEMENT_ACTIVE = True

logger = logging.getLogger(__name__)


class NeuroCore2Capture(Tool):
    """Capture a memory into Neuro Core 2.

    Layer 2 (tool-layer scope check): hard raises AuthorizationError if
    self.agent.context.caller_project / caller_agent do not match the
    project / agent arguments supplied to the tool.
    """

    async def execute(self, **kwargs) -> Response:
        text = self.args.get("text")
        project = self.args.get("project")
        agent = self.args.get("agent")
        importance = float(self.args.get("importance", 0.5))
        confidence = float(self.args.get("confidence", 0.5))

        # Layer 1 (revised, WI-2026-08-31-AUTHORIZATION-POLICY-REDESIGN):
        # derive caller identity from host inputs that verifiably exist at
        # dispatch time (active project via helpers.projects, audited
        # default_scope fallback with identity_source marker, host-assigned
        # agent_name as a scope-BINDING factor — not authenticated identity).
        identity = self._derive_caller_identity()

        # Layer 2 (re-based): bind the requested Scope(project, agent) against
        # the derived identity tuple (caller_project, agent_factor) with the
        # contract's 'agent:None' sentinel semantics. Gated behind
        # AUTHORIZATION_ENFORCEMENT_ACTIVE: when inactive, behavior is
        # unchanged (warning log, no enforcement).
        denial = self._binding_denial_or_none(identity, project, agent)
        if denial is not None:
            self._record_denial_event(identity, project, agent, denial)
            raise AuthorizationError(f"Authorization denied: {denial}")

        # P0 hotfix gate: when enforcement is inactive, forward no
        # caller_context so the service uses its backward-compatible path.
        # When active, forward the derived identity so the service re-binds
        # against the identity tuple (defense-in-depth) and records
        # identity_source in the authorization event.
        caller_context = self._effective_caller_context(dict(identity))

        db_path = load_config()["database_path"]
        store = SQLiteStore(db_path)
        service = NeuroCoreService(store)
        memory = service.capture(
            Memory(text, "tool", Scope(project, agent), importance, confidence),
            caller_context=caller_context,
        )
        # If service-layer check (defense-in-depth) returned an error dict,
        # surface it as a structured response.
        if isinstance(memory, dict) and memory.get("error"):
            return Response(
                message=f"Authorization denied: {memory.get('reason')}",
                break_loop=False,
                additional=memory,
            )
        return Response(
            message=f"Captured memory {memory.memory_id}",
            break_loop=False,
            additional={
                "memory_id": memory.memory_id,
                "text": memory.text,
                "scope": {"project": memory.scope.project, "agent": memory.scope.agent},
                "importance": memory.importance,
                "confidence": memory.confidence,
                "validation": memory.validation.value,
            },
        )

    def _derive_caller_identity(self) -> dict:
        """Layer 1 (revised): derive caller identity from host inputs.

        Uses caller_identity.derive_caller_identity: active project via
        helpers.projects.get_context_project_name, audited default_scope
        fallback with identity_source marker, host-assigned agent_name and
        agent.config.profile as scope-BINDING factors (not authenticated
        caller identity).
        """
        agent = getattr(self, "agent", None)
        config = load_config()
        default_scope = config.get("default_scope", {}) or {}
        return derive_caller_identity(
            agent,
            default_scope_project=default_scope.get("project", "default"),
        )

    def _binding_denial_or_none(
        self,
        identity: dict,
        project: str | None,
        agent: str | None,
    ) -> str | None:
        """Layer 2 (re-based): bind requested scope against derived identity.

        Returns a denial reason when the binding fails, or None when the
        binding succeeds or enforcement is inactive (flag False: behavior
        unchanged, warning logged — no enforcement).
        """
        if not AUTHORIZATION_ENFORCEMENT_ACTIVE:
            logger.warning(
                "authorization enforcement inactive pending redesign — see "
                "WI-2026-08-31-AUTHORIZATION-POLICY-REDESIGN"
            )
            return None
        return scope_binding_denial(identity, project, agent)

    def _record_denial_event(
        self,
        identity: dict,
        project: str | None,
        agent: str | None,
        denial_reason: str,
    ) -> None:
        """Record an audited tool-layer denial event (ARC conditions 1 and 7)."""
        try:
            db_path = load_config()["database_path"]
            store = SQLiteStore(db_path)
            service = NeuroCoreService(store)
            service.record_tool_layer_denial(identity, project, agent, denial_reason)
        except Exception:
            logger.exception("failed to record tool-layer authorization denial event")

    def _effective_caller_context(self, caller_context: dict | None) -> dict | None:
        """Return the caller_context to forward to the service.

        P0 hotfix (WI-2026-08-31-AUTHZ-HOTFIX): when enforcement is
        inactive, return None so the service uses its documented
        backward-compatible path (no caller-context check). When
        enforcement is active, forward caller_context unchanged.
        """
        if not AUTHORIZATION_ENFORCEMENT_ACTIVE:
            return None
        return caller_context

    def _derive_caller_context(self) -> dict | None:
        """Derive caller identity from self.agent.context (Layer 1).

        Returns a dict with caller_project and caller_agent, or None if
        self.agent.context is not populated. The host is responsible for
        populating self.agent.context.
        """
        agent = getattr(self, "agent", None)
        if agent is None:
            return None
        ctx = getattr(agent, "context", None)
        if ctx is None:
            return None
        return {
            "caller_project": getattr(ctx, "caller_project", None),
            "caller_agent": getattr(ctx, "caller_agent", None),
        }

    def _check_scope_or_raise(
        self,
        caller_context: dict | None,
        project: str,
        agent: str | None,
    ) -> None:
        """Layer 2: hard raise on scope mismatch (fail closed)."""
        # P0 hotfix (WI-2026-08-31-AUTHZ-HOTFIX): Layer 2 enforcement is
        # gated behind AUTHORIZATION_ENFORCEMENT_ACTIVE. When inactive,
        # proceed with caller_context as-is (None/None) and log a warning.
        if not AUTHORIZATION_ENFORCEMENT_ACTIVE:
            logger.warning(
                "authorization enforcement inactive pending redesign — see "
                "WI-2026-08-31-AUTHORIZATION-POLICY-REDESIGN"
            )
            return
        if caller_context is None:
            raise AuthorizationError(
                "Authorization denied: missing caller context (self.agent.context not populated)"
            )
        cp = caller_context.get("caller_project")
        ca = caller_context.get("caller_agent")
        if cp is None:
            raise AuthorizationError(
                "Authorization denied: missing caller_project in self.agent.context"
            )
        if cp != project or ca != agent:
            raise AuthorizationError(
                f"Authorization denied: scope mismatch "
                f"(caller={cp}/{ca}, requested={project}/{agent})"
            )
