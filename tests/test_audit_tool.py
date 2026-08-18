"""Unit tests for NeuroCore2Audit tool."""
import sys
import os
import tempfile
from pathlib import Path

# Add tools directory to sys.path for sibling imports
HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(HERE.parent))

import yaml
from neuro_core_2_audit import neuro_core_2_audit, MAX_LIMIT, DEFAULT_LIMIT
from neuro_core_2_service import NeuroCoreService
from sqlite_store import SQLiteStore
from neuro_core_2 import Memory, Scope
from memory_lifecycle import ValidationState


def _make_temp_db():
    """Create a temporary SQLite database."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    return tmp.name


def _write_config(db_path: str) -> str:
    """Write a temporary default_config.yaml pointing to db_path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w")
    yaml.safe_dump({"neuro_core_2": {"database_path": db_path}}, tmp)
    tmp.close()
    return tmp.name


def _patch_config(config_path: str):
    """Patch _config to use our temp config."""
    import _config
    original_path = _config._CONFIG_PATH
    _config._CONFIG_PATH = Path(config_path)
    return original_path


def test_scope_isolation_across_projects():
    """Events from project A must not appear in project B queries."""
    db_path = _make_temp_db()
    config_path = _write_config(db_path)
    original_path = _patch_config(config_path)
    
    try:
        store = SQLiteStore(db_path)
        service = NeuroCoreService(store)
        
        service.capture(Memory("alpha event", "tool", Scope("projA", "agent1"), 0.5, 0.5))
        service.capture(Memory("beta event", "tool", Scope("projB", "agent1"), 0.5, 0.5))
        
        result_a = neuro_core_2_audit(project="projA", agent="agent1")
        assert "events" in result_a
        assert len(result_a["events"]) == 1
        assert result_a["events"][0]["scope"]["project"] == "projA"
        
        result_b = neuro_core_2_audit(project="projB", agent="agent1")
        assert "events" in result_b
        assert len(result_b["events"]) == 1
        assert result_b["events"][0]["scope"]["project"] == "projB"
        
        print("test_scope_isolation_across_projects ... ok")
    finally:
        import _config
        _config._CONFIG_PATH = original_path
        os.unlink(db_path)
        os.unlink(config_path)


def test_agent_none_means_project_level_scope():
    """agent=None must return project-level events only, not all agents."""
    db_path = _make_temp_db()
    config_path = _write_config(db_path)
    original_path = _patch_config(config_path)
    
    try:
        store = SQLiteStore(db_path)
        service = NeuroCoreService(store)
        
        service.capture(Memory("project level", "tool", Scope("projA", None), 0.5, 0.5))
        service.capture(Memory("agent level", "tool", Scope("projA", "agent1"), 0.5, 0.5))
        
        result = neuro_core_2_audit(project="projA", agent=None)
        assert "events" in result
        assert len(result["events"]) == 1
        assert result["events"][0]["scope"]["agent"] is None
        
        print("test_agent_none_means_project_level_scope ... ok")
    finally:
        import _config
        _config._CONFIG_PATH = original_path
        os.unlink(db_path)
        os.unlink(config_path)


def test_event_type_filter():
    """event_type filter must return only matching events."""
    db_path = _make_temp_db()
    config_path = _write_config(db_path)
    original_path = _patch_config(config_path)
    
    try:
        store = SQLiteStore(db_path)
        service = NeuroCoreService(store)
        
        mem = service.capture(Memory("test", "tool", Scope("projA", "agent1"), 0.5, 0.5))
        service.validate(mem.memory_id, ValidationState.VALIDATED)
        
        result_captured = neuro_core_2_audit(project="projA", agent="agent1", event_type="captured")
        assert len(result_captured["events"]) == 1
        assert result_captured["events"][0]["kind"] == "captured"
        
        result_validated = neuro_core_2_audit(project="projA", agent="agent1", event_type="validation_changed")
        assert len(result_validated["events"]) == 1
        assert result_validated["events"][0]["kind"] == "validation_changed"
        
        print("test_event_type_filter ... ok")
    finally:
        import _config
        _config._CONFIG_PATH = original_path
        os.unlink(db_path)
        os.unlink(config_path)


def test_memory_id_filter():
    """memory_id filter must return only events targeting that memory."""
    db_path = _make_temp_db()
    config_path = _write_config(db_path)
    original_path = _patch_config(config_path)
    
    try:
        store = SQLiteStore(db_path)
        service = NeuroCoreService(store)
        
        mem1 = service.capture(Memory("first", "tool", Scope("projA", "agent1"), 0.5, 0.5))
        mem2 = service.capture(Memory("second", "tool", Scope("projA", "agent1"), 0.5, 0.5))
        
        result = neuro_core_2_audit(project="projA", agent="agent1", memory_id=mem1.memory_id)
        assert len(result["events"]) == 1
        assert mem1.memory_id in result["events"][0]["targets"]
        
        print("test_memory_id_filter ... ok")
    finally:
        import _config
        _config._CONFIG_PATH = original_path
        os.unlink(db_path)
        os.unlink(config_path)


def test_ordering_desc_by_occurred_at():
    """Results must be ordered by occurred_at DESC (most recent first)."""
    db_path = _make_temp_db()
    config_path = _write_config(db_path)
    original_path = _patch_config(config_path)
    
    try:
        store = SQLiteStore(db_path)
        service = NeuroCoreService(store)
        
        service.capture(Memory("first", "tool", Scope("projA", "agent1"), 0.5, 0.5))
        service.capture(Memory("second", "tool", Scope("projA", "agent1"), 0.5, 0.5))
        service.capture(Memory("third", "tool", Scope("projA", "agent1"), 0.5, 0.5))
        
        result = neuro_core_2_audit(project="projA", agent="agent1")
        events = result["events"]
        assert len(events) == 3
        timestamps = [e["occurred_at"] for e in events]
        assert timestamps == sorted(timestamps, reverse=True), f"Not DESC: {timestamps}"
        
        print("test_ordering_desc_by_occurred_at ... ok")
    finally:
        import _config
        _config._CONFIG_PATH = original_path
        os.unlink(db_path)
        os.unlink(config_path)


def test_limit_default_and_max():
    """Default limit is 100, max is 1000, exceeding max returns error."""
    assert DEFAULT_LIMIT == 100
    assert MAX_LIMIT == 1000
    
    db_path = _make_temp_db()
    config_path = _write_config(db_path)
    original_path = _patch_config(config_path)
    
    try:
        result = neuro_core_2_audit(project="projA", agent="agent1", limit=2000)
        assert "error" in result
        assert result["max_limit"] == 1000
        
        print("test_limit_default_and_max ... ok")
    finally:
        import _config
        _config._CONFIG_PATH = original_path
        os.unlink(db_path)
        os.unlink(config_path)


def test_all_fields_serialized():
    """Each event must have all 7 fields."""
    db_path = _make_temp_db()
    config_path = _write_config(db_path)
    original_path = _patch_config(config_path)
    
    try:
        store = SQLiteStore(db_path)
        service = NeuroCoreService(store)
        
        service.capture(Memory("test", "tool", Scope("projA", "agent1"), 0.5, 0.5))
        
        result = neuro_core_2_audit(project="projA", agent="agent1")
        event = result["events"][0]
        required_fields = ["event_id", "kind", "occurred_at", "scope", "targets", "outcome", "evidence"]
        for field in required_fields:
            assert field in event, f"Missing field: {field}"
        
        print("test_all_fields_serialized ... ok")
    finally:
        import _config
        _config._CONFIG_PATH = original_path
        os.unlink(db_path)
        os.unlink(config_path)


if __name__ == "__main__":
    test_scope_isolation_across_projects()
    test_agent_none_means_project_level_scope()
    test_event_type_filter()
    test_memory_id_filter()
    test_ordering_desc_by_occurred_at()
    test_limit_default_and_max()
    test_all_fields_serialized()
    print("\nAll audit tool tests passed!")
