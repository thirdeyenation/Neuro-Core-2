"""test_capture_signature_fix.py — Regression test for WI-2026-08-28-CAPTURE-SIGNATURE-FIX.

Verifies that NeuroCoreService.capture() accepts BOTH calling modes:
1. Positional Memory object (existing behavior, preserved).
2. Keyword arguments (new mode, added to align with the hook caller
   in on_plugin_load and the public tool contract).

Also verifies the mutual-exclusion guard and the missing-argument guard.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Plugin root for plugin module imports.
_PLUGIN_DIR = str(Path(__file__).resolve().parent.parent)
if _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)

from neuro_core_2 import Memory, Scope
from neuro_core_2_service import NeuroCoreService
from sqlite_store import SQLiteStore


class CaptureSignatureFixTests(unittest.TestCase):
    def setUp(self):
        fd, self._db_path = tempfile.mkstemp()
        os.close(fd)
        os.unlink(self._db_path)
        self.store = SQLiteStore(self._db_path)
        self.service = NeuroCoreService(self.store)

    def tearDown(self):
        try:
            self.store.close()
        except Exception:
            pass
        if os.path.exists(self._db_path):
            os.unlink(self._db_path)

    def test_capture_accepts_keyword_arguments(self):
        """The hook caller passes text=... as a keyword argument; capture() must accept it."""
        result = self.service.capture(
            text="host lifecycle test memory",
            project="host_val",
            agent="agent_a",
        )
        self.assertIsInstance(result, dict)
        self.assertIn("memory_id", result)
        self.assertEqual(result["text"], "host lifecycle test memory")
        self.assertEqual(result["scope"]["project"], "host_val")
        self.assertEqual(result["scope"]["agent"], "agent_a")
        self.assertEqual(result["importance"], 0.5)
        self.assertEqual(result["confidence"], 0.5)
        self.assertEqual(result["validation"], "unreviewed")

    def test_capture_keyword_mode_persists_memory(self):
        """Keyword-mode capture must actually persist the memory to the store."""
        result = self.service.capture(
            text="persistence check",
            project="host_val",
            agent="agent_a",
        )
        stored = self.store.get(result["memory_id"])
        self.assertIsNotNone(stored)
        self.assertEqual(stored.text, "persistence check")
        self.assertEqual(stored.scope.project, "host_val")
        self.assertEqual(stored.scope.agent, "agent_a")

    def test_capture_keyword_mode_emits_activity_event(self):
        """Keyword-mode capture must emit a 'captured' activity event."""
        self.service.capture(
            text="activity check",
            project="host_val",
            agent="agent_a",
        )
        events = self.service.list_activity(Scope("host_val", "agent_a"))
        kinds = [e.kind for e in events]
        self.assertIn("captured", kinds)

    def test_capture_keyword_mode_with_optional_fields(self):
        """Keyword-mode capture must accept importance and confidence overrides."""
        result = self.service.capture(
            text="weighted memory",
            project="host_val",
            agent="agent_a",
            importance=0.9,
            confidence=0.8,
        )
        self.assertEqual(result["importance"], 0.9)
        self.assertEqual(result["confidence"], 0.8)

    def test_capture_positional_memory_mode_preserved(self):
        """Existing positional-Memory mode must continue to work unchanged."""
        memory = Memory("positional mode", "test", Scope("host_val", "agent_a"))
        result = self.service.capture(memory)
        self.assertIsInstance(result, Memory)
        self.assertEqual(result.text, "positional mode")
        self.assertEqual(result.memory_id, memory.memory_id)

    def test_capture_rejects_both_modes(self):
        """Passing both a positional Memory and keyword arguments must raise TypeError."""
        memory = Memory("both modes", "test", Scope("host_val", "agent_a"))
        with self.assertRaises(TypeError):
            self.service.capture(memory, text="both modes")

    def test_capture_rejects_neither_mode(self):
        """Passing neither a positional Memory nor keyword arguments must raise TypeError."""
        with self.assertRaises(TypeError):
            self.service.capture()

    def test_capture_keyword_mode_requires_project(self):
        """Keyword-mode capture without project= must raise TypeError."""
        with self.assertRaises(TypeError):
            self.service.capture(text="no project", agent="agent_a")


if __name__ == "__main__":
    unittest.main()
