"""Shared config loader for Neuro Core 2 tools.

Centralizes reading of default_config.yaml and resolution of plugin-local
paths. All three tools (capture, retrieve, validate) source their database
path through this helper instead of duplicating the logic.
"""
from pathlib import Path
from typing import Any

import yaml


_CONFIG_PATH = Path(__file__).resolve().parent.parent / "default_config.yaml"


def _resolve_path(raw: str) -> str:
    """Resolve a path string against the config file's parent directory
    if it is not already absolute.
    """
    p = Path(raw)
    if p.is_absolute():
        return raw
    return str((_CONFIG_PATH.parent / p).resolve())


def load_config() -> dict[str, Any]:
    """Load and return the resolved Neuro Core 2 configuration.

    Reads default_config.yaml relative to the plugin root and resolves
    any path values against the config file's parent directory.
    """
    with _CONFIG_PATH.open() as f:
        cfg = yaml.safe_load(f)

    nc2 = cfg["neuro_core_2"]
    resolved = dict(nc2)
    if "database_path" in nc2:
        resolved["database_path"] = _resolve_path(nc2["database_path"])
    return resolved
