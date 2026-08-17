"""extensions — Neuro Core 2 lifecycle extensions (no-op stub).

This package restores the install/activation contract for Agent Zero
extension discovery. It defines the minimum extension registration
function Agent Zero expects for lifecycle extension discovery as a
no-op. No new behavior, schema, lifecycle state, retrieval semantics,
or public contract is introduced.

Work item: WI-2026-08-16-RESTORE-INSTALL-HOOKS
ARC decision: approved-with-conditions (S1)
"""


def register_extension():
    """No-op extension registration function called by Agent Zero.

    Returns
    -------
    None
    """
    return None
