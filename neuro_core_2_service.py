"""Application service composing Neuro Core domain capabilities.

Per ADR-0007 (authorization policy), the service implements:
- Layer 3: service-layer scope check (defense-in-depth) — returns structured
  error dict on scope mismatch (not a hard raise).
- Layer 4: memory-bound scope check for validate — verifies caller context
  matches the memory's stored scope before applying lifecycle transition.
- Layer 5: authorization audit — every authorization decision (allow or deny)
  is appended to the activity ledger as an authorization_decided event with
  caller context, requested scope, target memory_id, outcome, and denial reason.
"""
from activity_ledger import ActivityEvent, ActivityLedger
from memory_lifecycle import ValidationState, transition
from memory_store import MemoryStore
from neuro_core_2 import Memory, Scope, retrieve


class AuthorizationError(Exception):
    """Raised when authorization fails at the tool boundary (Layer 2).

    Per ADR-0007, the tool-layer scope check hard raises on scope mismatch
    (fail closed, no silent fallback). The service-layer check (Layer 3)
    returns a structured error dict instead, so the service can return a
    structured response to the tool.
    """

    pass


class NeuroCoreService:
    def __init__(self, store: MemoryStore, ledger: ActivityLedger | None = None) -> None:
        self.store = store
        self.ledger = ledger or ActivityLedger()

    def _identity_binding_denial(
        self,
        caller_context: dict,
        requested_project: str | None,
        requested_agent: str | None,
    ) -> str | None:
        """Bind a requested scope against a derived caller identity tuple.

        Used when caller_context carries an identity_source marker (the revised
        Layer 1 derivation from caller_identity.derive_caller_identity). The
        requested Scope(project, agent) must match the derived identity tuple
        (caller_project, agent_factor) per the implementation contract's
        sentinel semantics; returns a denial reason or None on success.
        """
        from caller_identity import scope_binding_denial

        return scope_binding_denial(caller_context, requested_project, requested_agent)

    def record_tool_layer_denial(
        self,
        identity: dict,
        requested_project: str | None,
        requested_agent: str | None,
        denial_reason: str,
        memory_id: str | None = None,
    ) -> None:
        """Record a tool-layer (Layer 2) authorization denial as an audited event.

        Called by the tools when the Layer 2 binding denies a request so the
        denial is inspectable in the activity ledger. Records scope values
        (project, agent factor, identity_source) and the denial reason only —
        never credentials, secrets, or identity material beyond project name,
        agent_name, and profile (ARC condition 7).
        """
        evidence: dict[str, str] = {
            "caller_project": str(identity.get("caller_project", "")),
            "agent_factor": str(identity.get("agent_factor", "") or ""),
            "identity_source": str(identity.get("identity_source", "")),
            "requested_project": str(requested_project),
            "requested_agent": (
                str(requested_agent) if requested_agent is not None else ""
            ),
            "outcome": "deny",
            "denial_reason": denial_reason,
            "layer": "tool-layer",
        }
        if memory_id:
            evidence["memory_id"] = memory_id
        event = ActivityEvent(
            kind="authorization_decided",
            scope=Scope(requested_project, requested_agent),
            targets=(memory_id,) if memory_id else ("authorization",),
            outcome="deny",
            evidence=evidence,
        )
        self.ledger.append(event)
        append_event = getattr(self.store, "append_event", None)
        if callable(append_event):
            append_event(event)

    def capture(self, memory: Memory | None = None, *, text: str | None = None, project: str | None = None, agent: str | None = None, importance: float = 0.5, confidence: float = 0.5, source: str = "service", caller_context: dict | None = None) -> Memory | dict:
        """Capture a memory into the store.

        Two calling modes are supported:

        1. Positional Memory object (existing behavior, preserved):
           ``service.capture(Memory(text, source, scope, importance, confidence))``
           returns the stored ``Memory`` object.

        2. Keyword arguments (new mode, added to align with the hook caller
           in ``on_plugin_load`` and the public tool contract):
           ``service.capture(text=..., project=..., agent=...)``
           constructs a ``Memory`` internally, stores it, and returns a dict
           with ``memory_id``, ``text``, ``scope``, ``importance``,
           ``confidence``, and ``validation`` fields — matching the shape
           returned by ``tools/neuro_core_2_capture.py``.

        The two modes are mutually exclusive: passing both a positional
        ``Memory`` and keyword arguments raises ``TypeError``. Passing
        neither raises ``TypeError``.

        caller_context (Layer 3, optional): dict with ``caller_project`` and
        ``caller_agent``. If provided, the service re-checks scope at the
        service boundary (defense-in-depth). On mismatch, returns a
        structured error dict (not a hard raise).
        """
        if memory is not None and text is not None:
            raise TypeError(
                "NeuroCoreService.capture() received both a positional Memory "
                "and keyword arguments; pass exactly one of the two modes."
            )
        if memory is None and text is None:
            raise TypeError(
                "NeuroCoreService.capture() requires either a positional Memory "
                "argument or keyword arguments (text=, project=, agent=)."
            )

        # Determine effective scope for Layer 3 check.
        if memory is not None:
            eff_project = memory.scope.project
            eff_agent = memory.scope.agent
        else:
            eff_project = project
            eff_agent = agent

        # Layer 3: service-layer scope check (defense-in-depth).
        # Only fires when caller_context is provided. If a tool forgot to
        # check, or a future tool bypasses the check, the service catches it.
        if caller_context is not None and "identity_source" in caller_context:
            # Revised binding (WI-2026-08-31-AUTHORIZATION-POLICY-REDESIGN):
            # bind the requested scope against the derived identity tuple
            # (caller_project, agent_factor) with sentinel semantics.
            denial = self._identity_binding_denial(caller_context, eff_project, eff_agent)
            if denial is not None:
                self._audit_authorization(
                    caller_context, eff_project, eff_agent, None,
                    "deny", denial,
                )
                return {
                    "error": "authorization_denied",
                    "reason": denial,
                    "caller_project": caller_context.get("caller_project"),
                    "caller_agent": caller_context.get("caller_agent"),
                    "requested_project": eff_project,
                    "requested_agent": eff_agent,
                }
            self._audit_authorization(
                caller_context, eff_project, eff_agent, None,
                "allow", None,
            )
        elif caller_context is not None:
            cp = caller_context.get("caller_project")
            ca = caller_context.get("caller_agent")
            if cp is None:
                self._audit_authorization(
                    caller_context, eff_project, eff_agent, None,
                    "deny", "missing caller_project",
                )
                return {
                    "error": "authorization_denied",
                    "reason": "missing caller_project",
                    "caller_project": cp,
                    "caller_agent": ca,
                    "requested_project": eff_project,
                    "requested_agent": eff_agent,
                }
            if cp != eff_project or ca != eff_agent:
                self._audit_authorization(
                    caller_context, eff_project, eff_agent, None,
                    "deny", "scope mismatch",
                )
                return {
                    "error": "authorization_denied",
                    "reason": "scope mismatch",
                    "caller_project": cp,
                    "caller_agent": ca,
                    "requested_project": eff_project,
                    "requested_agent": eff_agent,
                }
            self._audit_authorization(
                caller_context, eff_project, eff_agent, None,
                "allow", None,
            )

        if memory is None:
            # Keyword-argument mode: construct Memory, store, return dict.
            if project is None:
                raise TypeError(
                    "NeuroCoreService.capture() keyword mode requires project=."
                )
            memory = Memory(
                text=text,
                source=source,
                scope=Scope(project, agent),
                importance=importance,
                confidence=confidence,
            )
            self.store.put(memory)
            self._event("captured", memory, "stored")
            return {
                "memory_id": memory.memory_id,
                "text": memory.text,
                "scope": {
                    "project": memory.scope.project,
                    "agent": memory.scope.agent,
                },
                "importance": memory.importance,
                "confidence": memory.confidence,
                "validation": memory.validation.value,
            }
        # Positional Memory mode: existing behavior, unchanged.
        self.store.put(memory)
        self._event("captured", memory, "stored")
        return memory

    def retrieve(self, query: str | None = None, scope: Scope | None = None, *, project: str | None = None, agent: str | None = None, max_results: int | None = None, caller_context: dict | None = None) -> list[dict] | dict:
        """Backward-compatible retrieve returning the ranked result list.

        Two calling modes are supported:

        1. Positional Scope (existing behavior, preserved):
           ``service.retrieve(query, scope, max_results=...)``
           returns the ranked result list.

        2. Keyword arguments (new mode, added to align with the test caller
           in ``host_lifecycle_scenarios.py`` scenario_b_on_plugin_load):
           ``service.retrieve(query=..., project=..., agent=...)``
           constructs a ``Scope`` internally and returns the ranked result
           list.

        The two modes are mutually exclusive: passing both a positional
        ``scope`` and keyword ``project=`` raises ``TypeError``. Passing
        neither raises ``TypeError``. ``query`` is required in both modes.

        Uses candidate_ids as a pure candidate pre-filter before domain
        scoring, then applies the result cap after scoring and sorting.
        Returns only the result list (no cap metadata) for compatibility
        with existing callers; use retrieve_with_meta() for the full
        payload including count_exceeded and total_matches.

        caller_context (Layer 3, optional): dict with ``caller_project`` and
        ``caller_agent``. If provided, the service re-checks scope at the
        service boundary (defense-in-depth). On mismatch, returns a
        structured error dict.
        """
        if scope is not None and project is not None:
            raise TypeError(
                "NeuroCoreService.retrieve() received both a positional scope "
                "and keyword project=; pass exactly one of the two modes."
            )
        if scope is None and project is None:
            raise TypeError(
                "NeuroCoreService.retrieve() requires either a positional scope "
                "argument or keyword arguments (project=, agent=)."
            )
        if query is None:
            raise TypeError(
                "NeuroCoreService.retrieve() requires a query."
            )
        if scope is None:
            # Keyword-argument mode: construct Scope internally.
            scope = Scope(project, agent)
        meta = self.retrieve_with_meta(query, scope, max_results, caller_context=caller_context)
        # If retrieve_with_meta returned an error dict, propagate it.
        if isinstance(meta, dict) and meta.get("error"):
            return meta
        return meta["results"]

    def retrieve_with_meta(self, query: str, scope: Scope, max_results: int | None = None, caller_context: dict | None = None) -> dict:
        """Retrieve with cap metadata.

        Returns a dict with:
          - results: ranked result list (same shape as domain retrieve())
          - count_exceeded: True when the full match count exceeds max_results
          - total_matches: the full match count before the cap

        The index is a pure candidate pre-filter: candidate_ids(terms, scope)
        returns exactly the memories within scope whose text.lower().split()
        has non-empty intersection with query.lower().split(). Scoring,
        ranking, and the factors dict remain in the domain retrieve()
        function and are unchanged. The cap is applied AFTER scoring and
        sorting (top-K selection), never before. Silent truncation is
        prohibited: callers receive count_exceeded and total_matches.

        caller_context (Layer 3, optional): dict with ``caller_project`` and
        ``caller_agent``. If provided, the service re-checks scope at the
        service boundary (defense-in-depth). On mismatch, returns a
        structured error dict.
        """
        # Layer 3: service-layer scope check (defense-in-depth).
        if caller_context is not None and "identity_source" in caller_context:
            # Revised binding (WI-2026-08-31-AUTHORIZATION-POLICY-REDESIGN):
            # bind the requested scope against the derived identity tuple
            # (caller_project, agent_factor) with sentinel semantics.
            denial = self._identity_binding_denial(caller_context, scope.project, scope.agent)
            if denial is not None:
                self._audit_authorization(
                    caller_context, scope.project, scope.agent, None,
                    "deny", denial,
                )
                return {
                    "error": "authorization_denied",
                    "reason": denial,
                    "caller_project": caller_context.get("caller_project"),
                    "caller_agent": caller_context.get("caller_agent"),
                    "requested_project": scope.project,
                    "requested_agent": scope.agent,
                }
            self._audit_authorization(
                caller_context, scope.project, scope.agent, None,
                "allow", None,
            )
        elif caller_context is not None:
            cp = caller_context.get("caller_project")
            ca = caller_context.get("caller_agent")
            if cp is None:
                self._audit_authorization(
                    caller_context, scope.project, scope.agent, None,
                    "deny", "missing caller_project",
                )
                return {
                    "error": "authorization_denied",
                    "reason": "missing caller_project",
                    "caller_project": cp,
                    "caller_agent": ca,
                    "requested_project": scope.project,
                    "requested_agent": scope.agent,
                }
            if cp != scope.project or ca != scope.agent:
                self._audit_authorization(
                    caller_context, scope.project, scope.agent, None,
                    "deny", "scope mismatch",
                )
                return {
                    "error": "authorization_denied",
                    "reason": "scope mismatch",
                    "caller_project": cp,
                    "caller_agent": ca,
                    "requested_project": scope.project,
                    "requested_agent": scope.agent,
                }
            self._audit_authorization(
                caller_context, scope.project, scope.agent, None,
                "allow", None,
            )

        terms = set(query.lower().split())
        candidate_ids = getattr(self.store, "candidate_ids", None)
        if callable(candidate_ids):
            ids = candidate_ids(terms, scope)
            memories = [self.store.get(mid) for mid in ids]
            memories = [m for m in memories if m is not None]
        else:
            memories = list(self.store.list(scope))
        results = retrieve(query, scope, memories)
        total_matches = len(results)
        count_exceeded = False
        if max_results is not None and total_matches > max_results:
            results = results[:max_results]
            count_exceeded = True
        for item in results:
            self._event("retrieved", item["memory"], "selected")
        return {
            "results": results,
            "count_exceeded": count_exceeded,
            "total_matches": total_matches,
        }

    def validate(self, memory_id: str, target: ValidationState, caller_context: dict | None = None) -> Memory | dict:
        """Validate a memory's lifecycle state.

        caller_context (Layer 4, optional): dict with ``caller_project`` and
        ``caller_agent``. If provided, the service verifies that the caller
        context matches the memory's stored scope before applying the
        lifecycle transition (memory-bound scope check). On mismatch,
        returns a structured error dict.
        """
        current = self.store.get(memory_id)
        if current is None:
            raise KeyError(memory_id)

        # Layer 4: memory-bound scope check for validate.
        # Closes the prior hole where validate() accepted only memory_id
        # with no scope check whatsoever.
        if caller_context is not None and "identity_source" in caller_context:
            # Revised binding (WI-2026-08-31-AUTHORIZATION-POLICY-REDESIGN):
            # bind the memory's stored scope against the derived identity
            # tuple (caller_project, agent_factor) with sentinel semantics.
            denial = self._identity_binding_denial(
                caller_context, current.scope.project, current.scope.agent,
            )
            if denial is not None:
                self._audit_authorization(
                    caller_context,
                    current.scope.project, current.scope.agent,
                    memory_id,
                    "deny", denial,
                )
                return {
                    "error": "authorization_denied",
                    "reason": denial,
                    "caller_project": caller_context.get("caller_project"),
                    "caller_agent": caller_context.get("caller_agent"),
                    "memory_scope": {
                        "project": current.scope.project,
                        "agent": current.scope.agent,
                    },
                }
            self._audit_authorization(
                caller_context,
                current.scope.project, current.scope.agent,
                memory_id,
                "allow", None,
            )
        elif caller_context is not None:
            cp = caller_context.get("caller_project")
            ca = caller_context.get("caller_agent")
            if cp is None:
                self._audit_authorization(
                    caller_context,
                    current.scope.project, current.scope.agent,
                    memory_id,
                    "deny", "missing caller_project",
                )
                return {
                    "error": "authorization_denied",
                    "reason": "missing caller_project",
                    "caller_project": cp,
                    "caller_agent": ca,
                    "memory_scope": {
                        "project": current.scope.project,
                        "agent": current.scope.agent,
                    },
                }
            if cp != current.scope.project or ca != current.scope.agent:
                self._audit_authorization(
                    caller_context,
                    current.scope.project, current.scope.agent,
                    memory_id,
                    "deny", "scope mismatch",
                )
                return {
                    "error": "authorization_denied",
                    "reason": "scope mismatch",
                    "caller_project": cp,
                    "caller_agent": ca,
                    "memory_scope": {
                        "project": current.scope.project,
                        "agent": current.scope.agent,
                    },
                }
            self._audit_authorization(
                caller_context,
                current.scope.project, current.scope.agent,
                memory_id,
                "allow", None,
            )

        updated = Memory(current.text, current.source, current.scope, current.importance, current.confidence, transition(current.validation, target), current.memory_id)
        self.store.put(updated)
        self._event("validation_changed", updated, target.value)
        return updated

    def list_activity(self, scope: Scope | None = None) -> tuple[tuple, ...] | tuple[ActivityEvent, ...]:
        list_events = getattr(self.store, "list_events", None)
        if callable(list_events):
            return list_events(scope)
        return self.ledger.for_scope(scope) if scope is not None else self.ledger.all()

    def _event(self, kind: str, memory: Memory, outcome: str) -> None:
        event = ActivityEvent(kind, memory.scope, (memory.memory_id,), outcome, {"source": memory.source})
        self.ledger.append(event)
        append_event = getattr(self.store, "append_event", None)
        if callable(append_event):
            append_event(event)

    def _audit_authorization(
        self,
        caller_context: dict,
        requested_project: str,
        requested_agent: str | None,
        memory_id: str | None,
        outcome: str,
        denial_reason: str | None,
    ) -> None:
        """Append an authorization_decided event to the activity ledger (Layer 5).

        Per ADR-0007, every authorization decision (allow or deny) is appended
        to the activity ledger as an authorization_decided event with caller
        context, requested scope, target memory_id (if any), outcome
        (allow/deny), and denial reason (e.g., "scope mismatch", "missing
        caller_project"). This makes authorization decisions fully
        inspectable via the existing audit tool and is consistent with
        ADR-0004's audit-durability principle.
        """
        scope = Scope(requested_project, requested_agent)
        targets = (memory_id,) if memory_id else ("authorization",)
        evidence: dict[str, str] = {
            "caller_project": str(caller_context.get("caller_project", "")),
            "caller_agent": (
                str(caller_context.get("caller_agent", ""))
                if caller_context.get("caller_agent") is not None
                else ""
            ),
            "requested_project": str(requested_project),
            "requested_agent": (
                str(requested_agent) if requested_agent is not None else ""
            ),
            "outcome": outcome,
        }
        # Revised identity model (WI-2026-08-31-AUTHORIZATION-POLICY-REDESIGN,
        # ARC condition 1): record the identity_source marker and the bound
        # agent factor so fallback-derived identity and sentinel-bound
        # decisions are distinguishable in the audit trail. Scope values and
        # denial reasons only — no credentials, secrets, or identity material
        # beyond project name, agent_name, and profile (ARC condition 7).
        if "identity_source" in caller_context:
            evidence["identity_source"] = str(
                caller_context.get("identity_source", "")
            )
            evidence["agent_factor"] = str(
                caller_context.get("agent_factor", "") or ""
            )
        if denial_reason:
            evidence["denial_reason"] = denial_reason
        if memory_id:
            evidence["memory_id"] = memory_id
        event = ActivityEvent(
            kind="authorization_decided",
            scope=scope,
            targets=targets,
            outcome=outcome,
            evidence=evidence,
        )
        self.ledger.append(event)
        append_event = getattr(self.store, "append_event", None)
        if callable(append_event):
            append_event(event)
