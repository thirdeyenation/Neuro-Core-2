"""Neuro Core 2 capture tool.

Per ADR-0007 (authorization policy), this tool implements Layer 2
(tool-layer scope check): hard raise on scope mismatch.

Caller identity is derived from self.agent.context (Layer 1 — caller-context
binding). The host is responsible for populating self.agent.context with
the authenticated caller's identity (caller_project, caller_agent).

On scope mismatch, the tool hard raises AuthorizationError (fail closed,
no silent fallback) and does not invoke the service.
"""
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

        # Layer 1: caller-context binding from self.agent.context.
        caller_context = self._derive_caller_context()

        # Layer 2: tool-layer scope check (hard raise on mismatch).
        self._check_scope_or_raise(caller_context, project, agent)

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
