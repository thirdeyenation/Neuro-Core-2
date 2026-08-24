import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

# Framework root for helpers.* imports.
_A0_ROOT = "/a0"
if _A0_ROOT not in sys.path:
    sys.path.insert(0, _A0_ROOT)

# Plugin root for plugin module imports.
_PLUGIN_DIR = str(Path(__file__).resolve().parent.parent)
if _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)

import hooks
import extensions
from helpers.extension import Extension
from neuro_core_2 import Memory, Scope
from neuro_core_2_service import NeuroCoreService
from sqlite_store import SQLiteStore


class HookTests(unittest.TestCase):
    def setUp(self):
        fd, self._db_path = tempfile.mkstemp()
        os.close(fd)
        os.unlink(self._db_path)
        self._original_load_config = hooks._load_config
        hooks._load_config = lambda: {
            "database_path": self._db_path,
            "busy_timeout_ms": 5000,
            "default_scope": {"project": "default", "agent": None},
        }

    def tearDown(self):
        hooks._load_config = self._original_load_config
        if hooks._store is not None:
            try:
                hooks._store.close()
            except Exception:
                pass
        hooks._store = None
        hooks._service = None
        hooks._config = None
        if os.path.exists(self._db_path):
            os.unlink(self._db_path)

    def test_register_plugin_registers_metadata_on_dict(self):
        info = {}
        result = hooks.register_plugin(info)
        self.assertIs(result, info)
        self.assertEqual(info["name"], "neuro_core_2")
        self.assertEqual(info["version"], "0.1.0")
        self.assertEqual(
            info["tools"],
            ["NeuroCore2Capture", "NeuroCore2Retrieve", "NeuroCore2Validate"],
        )

    def test_register_plugin_registers_metadata_on_object(self):
        info = types.SimpleNamespace()
        result = hooks.register_plugin(info)
        self.assertIs(result, info)
        self.assertEqual(info.name, "neuro_core_2")
        self.assertEqual(info.version, "0.1.0")
        self.assertEqual(
            info.tools,
            ["NeuroCore2Capture", "NeuroCore2Retrieve", "NeuroCore2Validate"],
        )

    def test_register_plugin_returns_metadata_when_info_none(self):
        metadata = hooks.register_plugin(None)
        self.assertEqual(metadata["name"], "neuro_core_2")
        self.assertEqual(metadata["version"], "0.1.0")
        self.assertEqual(len(metadata["tools"]), 3)

    def test_on_plugin_load_initializes_service_and_db(self):
        service = hooks.on_plugin_load()
        self.assertIsInstance(service, NeuroCoreService)
        self.assertIsInstance(hooks._store, SQLiteStore)
        self.assertTrue(os.path.exists(self._db_path))
        # Service is ready to accept tool calls immediately after load.
        memory = service.capture(Memory("hook load check", "test", Scope("default")))
        self.assertEqual(
            service.retrieve("hook load check", Scope("default"))[0]["memory"],
            memory,
        )

    def test_on_plugin_activate_verifies_db_and_returns_status(self):
        hooks.on_plugin_load()
        status = hooks.on_plugin_activate()
        self.assertTrue(status["active"])
        self.assertTrue(status["database_accessible"])
        self.assertGreaterEqual(status["schema_version"], 1)

    def test_on_plugin_activate_initializes_if_not_loaded(self):
        hooks._service = None
        hooks._store = None
        status = hooks.on_plugin_activate()
        self.assertTrue(status["active"])
        self.assertTrue(status["database_accessible"])


class ExtensionTests(unittest.TestCase):
    def setUp(self):
        fd, self._db_path = tempfile.mkstemp()
        os.close(fd)
        os.unlink(self._db_path)
        self._original_load_config = hooks._load_config
        hooks._load_config = lambda: {
            "database_path": self._db_path,
            "busy_timeout_ms": 5000,
            "default_scope": {"project": "default", "agent": None},
        }
        hooks.on_plugin_load()

    def tearDown(self):
        hooks._load_config = self._original_load_config
        if hooks._store is not None:
            try:
                hooks._store.close()
            except Exception:
                pass
        hooks._store = None
        hooks._service = None
        hooks._config = None
        if os.path.exists(self._db_path):
            os.unlink(self._db_path)

    def test_register_extension_registers_functional_extension(self):
        cls = extensions.register_extension()
        self.assertIs(cls, extensions.SessionLifecycleExtension)
        self.assertTrue(issubclass(cls, Extension))

    def test_extension_execute_logs_session_initialized_event(self):
        extensions.register_extension()
        instance = extensions.SessionLifecycleExtension(agent=None)
        instance.execute()
        events = hooks._service.list_activity()
        kinds = [event.kind for event in events]
        self.assertIn("session_initialized", kinds)
        event = next(e for e in events if e.kind == "session_initialized")
        self.assertEqual(event.outcome, "started")
        self.assertEqual(event.evidence.get("source"), "lifecycle_extension")

    def test_register_extension_is_idempotent(self):
        extensions.register_extension()
        extensions.register_extension()
        from helpers import extension as ext_helpers

        classes = ext_helpers._get_extension_classes("agent_init", None)
        self.assertEqual(classes.count(extensions.SessionLifecycleExtension), 1)


if __name__ == "__main__":
    unittest.main()
