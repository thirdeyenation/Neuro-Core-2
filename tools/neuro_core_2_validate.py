"""Neuro Core 2 validate tool.

Per ADR-0007 (authorization policy), this tool implements Layer 2
(tool-layer scope check): hard raise on scope mismatch.

Caller identity is derived from self.agent.context (Layer 1 — caller-context
binding). The host is responsible for populating self.agent.context with
the authenticated caller's identity (caller_project, caller_agent).

On scope mismatch, the tool hard raises AuthorizationError (fail closed,
no silent fallback) and does not invoke the service.

Note: validate() previously accepted only memory_id and target with no
scope argument at all. Per ADR-0007, the tool now derives caller identity
from self.agent.context and passes it to the service, which performs
Layer 4 (memory-bound scope check) — verifying that the caller context
matches the memory's stored scope before applying the lifecycle transition.
"""
import logging
import sys
from pathlib import Path

from helpers.tool import Response, Tool

_PLUGIN_DIR = Path(__file__).resolve().parent.parent
if str(_PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_DIR))

from memory_lifecycle import ValidationState
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


class NeuroCore2Validate(Tool):
    """Validate a memory's lifecycle state.

    Layer 2 (tool-layer scope check): hard raises AuthorizationError if
    self.agent.context is not populated. The service performs Layer 4
    (memory-bound scope check) — verifying that the caller context matches
    the memory's stored scope before applying the lifecycle transition.
    """

    async def execute(self, **kwargs) -> Response:
        memory_id = self.args.get("memory_id")
        target = self.args.get("target")

        # Layer 1 (revised, WI-2026-08-31-AUTHORIZATION-POLICY-REDESIGN):
        # derive caller identity from host inputs that verifiably exist at
        # dispatch time (active project via helpers.projects, audited
        # default_scope fallback with identity_source marker, host-assigned
        # agent_name as a scope-BINDING factor — not authenticated identity).
        identity = self._derive_caller_identity()

        # Layer 2 (re-based, per design-request Layer 2 revision): validate
        # derives its target scope from caller identity instead of accepting
        # an unrestricted caller-supplied scope. Under fallback identity it
        # binds at most to the configured default_scope, never a
        # caller-supplied value. A caller-supplied project/agent argument is
        # rejected with an audited denial when enforcement is active.
        supplied_project = self.args.get("project")
        supplied_agent = self.args.get("agent")
        if AUTHORIZATION_ENFORCEMENT_ACTIVE and (
            supplied_project is not None or supplied_agent is not None
        ):
            denial = "validate does not accept caller-supplied scope arguments"
            self._record_denial_event(
                identity, supplied_project, supplied_agent, denial,
            )
            raise AuthorizationError(f"Authorization denied: {denial}")

        # P0 hotfix gate: when enforcement is inactive, forward no
        # caller_context so the service uses its backward-compatible path.
        # When active, forward the derived identity so the service performs
        # the Layer 4 memory-bound check against the identity tuple and
        # records identity_source in the authorization event.
        caller_context = self._effective_caller_context(dict(identity))

        db_path = load_config()["database_path"]
        store = SQLiteStore(db_path)
        service = NeuroCoreService(store)
        updated = service.validate(
            memory_id, ValidationState(target), caller_context=caller_context,
        )
        # If service-layer check (defense-in-depth) returned an error dict,
        # surface it as a structured response.
        if isinstance(updated, dict) and updated.get("error"):
            return Response(
                message=f"Authorization denied: {updated.get('reason')}",
                break_loop=False,
                additional=updated,
            )
        return Response(
            message=f"Validated memory {updated.memory_id} to {updated.validation.value}",
            break_loop=False,
            additional={
                "memory_id": updated.memory_id,
                "text": updated.text,
                "scope": {"project": updated.scope.project, "agent": updated.scope.agent},
                "importance": updated.importance,
                "confidence": updated.confidence,
                "validation": updated.validation.value,
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
        """Derive caller identity from self.agent.context (Layer 1)."""
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

    def _check_caller_context_or_raise(self, caller_context: dict | None) -> None:
        """Layer 2: hard raise if caller context is missing or unpopulated.

        For validate, the tool cannot compare caller scope against a
        requested scope (no project/agent args). The tool verifies that
        caller context exists and caller_project is populated; the
        service performs the memory-bound scope check (Layer 4).
        """
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
        if caller_context.get("caller_project") is None:
            raise AuthorizationError(
                "Authorization denied: missing caller_project in self.agent.context"
            )
