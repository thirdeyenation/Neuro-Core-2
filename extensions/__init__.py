"""extensions — Neuro Core 2 lifecycle extensions.

Registers a functional session-lifecycle extension with Agent Zero's
extension system. The extension logs a session-initialized activity
event through the Neuro Core 2 service when an agent session starts.

Work item: WI-2026-08-21-HOOK-EXTENSION-LOGIC
ARC decision: approved-with-conditions (S1)
"""
from helpers import cache as _cache
from helpers.extension import Extension as _Extension

_CLASSES_CACHE_AREA = "extension_classes(extensions)"
_AGENT_INIT_POINT = "agent_init"


class SessionLifecycleExtension(_Extension):
    """Log a session-initialized activity event for Neuro Core 2."""

    def execute(self, **kwargs):
        import hooks

        service = getattr(hooks, "_service", None)
        if service is None:
            return

        config = getattr(hooks, "_config", None) or {}
        default_scope = config.get("default_scope") or {}
        project = default_scope.get("project", "default")
        agent = default_scope.get("agent")

        from activity_ledger import ActivityEvent
        from neuro_core_2 import Scope

        agent_name = self.agent.agent_name if self.agent else (agent or "session")
        event = ActivityEvent(
            kind="session_initialized",
            scope=Scope(project, agent),
            targets=(agent_name,),
            outcome="started",
            evidence={"source": "lifecycle_extension"},
        )
        service.ledger.append(event)
        append_event = getattr(service.store, "append_event", None)
        if callable(append_event):
            append_event(event)


def register_extension():
    """Register the Neuro Core 2 session-lifecycle extension.

    Merges SessionLifecycleExtension into the framework's extension
    class cache for the agent_init session-lifecycle point, preserving
    any folder-scanned extensions already present for that key.

    Returns
    -------
    type
        The registered SessionLifecycleExtension class.
    """
    from helpers import extension as _extension

    key = _cache.determine_cache_key(None, _AGENT_INIT_POINT)
    existing = _extension._get_extension_classes(_AGENT_INIT_POINT, None)
    if SessionLifecycleExtension not in existing:
        _cache.add(_CLASSES_CACHE_AREA, key, [*existing, SessionLifecycleExtension])
    return SessionLifecycleExtension
