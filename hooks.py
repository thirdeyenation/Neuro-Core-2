"""hooks.py — Neuro Core 2 plugin lifecycle hooks.

Implements the Agent Zero plugin lifecycle contract for Neuro Core 2:
- register_plugin(plugin_info): registers plugin metadata with the host.
- on_plugin_load(): initializes the Neuro Core 2 service from
  default_config.yaml and registers the lifecycle extension.
- on_plugin_activate(): verifies database accessibility, runs startup
  validation, and logs activation status.

Work item: WI-2026-08-21-HOOK-EXTENSION-LOGIC
ARC decision: approved-with-conditions (S1)
"""
import sys
from pathlib import Path

import yaml

_PLUGIN_DIR = Path(__file__).resolve().parent
if str(_PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_DIR))

from neuro_core_2_service import NeuroCoreService
from sqlite_store import SQLiteStore

_service = None
_store = None
_config = None


def _load_config() -> dict:
    """Load default_config.yaml and resolve the database path."""
    with (_PLUGIN_DIR / "default_config.yaml").open() as f:
        cfg = yaml.safe_load(f)
    nc2 = cfg["neuro_core_2"]
    resolved = dict(nc2)
    if "database_path" in nc2:
        p = Path(nc2["database_path"])
        resolved["database_path"] = str(
            p if p.is_absolute() else (_PLUGIN_DIR / p).resolve()
        )
    return resolved


def register_plugin(plugin_info):
    """Register Neuro Core 2 plugin metadata with the Agent Zero host.

    Parameters
    ----------
    plugin_info : dict or object
        Plugin metadata container supplied by the Agent Zero host.

    Returns
    -------
    dict or object
        The same container with metadata registered, or the metadata
        dict when plugin_info is None.
    """
    metadata = {
        "name": "neuro_core_2",
        "version": "0.1.0",
        "tools": [
            "NeuroCore2Capture",
            "NeuroCore2Retrieve",
            "NeuroCore2Validate",
        ],
    }
    if plugin_info is None:
        return metadata
    if isinstance(plugin_info, dict):
        plugin_info.update(metadata)
    else:
        for key, value in metadata.items():
            setattr(plugin_info, key, value)
    return plugin_info


def on_plugin_load():
    """Initialize the Neuro Core 2 service and register lifecycle extensions.

    Returns
    -------
    NeuroCoreService
        The initialized service, ready to accept tool calls.
    """
    global _service, _store, _config
    if _store is not None:
        try:
            _store.close()
        except Exception:
            pass
    _config = _load_config()
    _store = SQLiteStore(
        _config["database_path"],
        busy_timeout_ms=_config.get("busy_timeout_ms"),
    )
    _service = NeuroCoreService(_store)
    from extensions import register_extension

    register_extension()
    return _service


def on_plugin_activate():
    """Activate the Neuro Core 2 plugin.

    Verifies the database is accessible, runs startup validation, and
    logs activation status. Performs no destructive operations.

    Returns
    -------
    dict
        Activation status.
    """
    if _service is None or _store is None:
        on_plugin_load()
    _store.connection.execute("SELECT 1").fetchone()
    schema_version = _store.schema_version()
    status = {
        "active": True,
        "database_accessible": True,
        "schema_version": schema_version,
    }
    print(f"[neuro_core_2] activation status: {status}")
    return status
