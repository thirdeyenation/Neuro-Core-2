"""Agent Zero tool for Neuro Core memory lifecycle transitions."""
from pathlib import Path
from helpers.tool import Tool

from memory_lifecycle import ValidationState
from neuro_service import NeuroCoreService
from sqlite_store import SQLiteStore


def _load_config() -> dict[str, str]:
    path = Path(__file__).resolve().parents[1] / "default_config.yaml"
    config: dict[str, str] = {}
    if path.exists():
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, value = line.split(":", 1)
            config[key.strip()] = value.strip()
    return config


def _db_path() -> str:
    return _load_config().get("database_path", "/a0/usr/plugins/neuro_core_2/neuro_core.db")


class NeuroValidate(Tool):
    async def execute(self, memory_id="", state="", **kwargs):
        if not memory_id or not state:
            raise ValueError("memory_id and state are required")
        try:
            target = ValidationState(state)
        except ValueError as error:
            raise ValueError("state must be unreviewed, validated, disputed, or superseded") from error
        store = SQLiteStore(_db_path())
        try:
            memory = NeuroCoreService(store).validate(memory_id, target)
            return {"memory_id": memory.memory_id, "validation": memory.validation.value, "outcome": "updated"}
        finally:
            store.close()
