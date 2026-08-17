"""hooks.py — Neuro Core 2 plugin hooks (no-op stub).

This module restores the install/activation contract for Agent Zero plugin
discovery. It defines the minimum hook signatures Agent Zero expects for
plugin discovery and activation as no-op functions. No new behavior,
schema, lifecycle state, retrieval semantics, or public contract is
introduced.

Work item: WI-2026-08-16-RESTORE-INSTALL-HOOKS
ARC decision: approved-with-conditions (S1)
"""


def register_plugin(plugin_info):
    """No-op hook called by Agent Zero during plugin discovery.

    Parameters
    ----------
    plugin_info : object
        Plugin metadata object supplied by the Agent Zero host. Accepted
        but not used; this stub performs no work.

    Returns
    -------
    None
    """
    return None


def on_plugin_load():
    """No-op hook called by Agent Zero when the plugin is loaded.

    Returns
    -------
    None
    """
    return None


def on_plugin_activate():
    """No-op hook called by Agent Zero when the plugin is activated.

    Returns
    -------
    None
    """
    return None
