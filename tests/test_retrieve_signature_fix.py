"""test_retrieve_signature_fix.py — Regression test for WI-2026-08-29-RETRIEVE-SIGNATURE-FIX.

Verifies that NeuroCoreService.retrieve() accepts BOTH calling modes:
1. Positional Scope (existing behavior, preserved).
2. Keyword arguments (new mode, added to align with the test caller
   in host_lifecycle_scenarios.py scenario_b_on_plugin_load).

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


class RetrieveSignatureFixTests(unittest.TestCase):
    def setUp(self):
        fd, self._db_path = tempfile.mkstemp()
        os.close(fd)
        os.unlink(self._db_path)
        self.store = SQLiteStore(self._db_path)
        self.service = NeuroCoreService(self.store)
        # Seed a memory in scope so retrieve has something to find.
        self.service.capture(
            text="host lifecycle test memory",
            project="host_val",
            agent="agent_a",
        )

    def tearDown(self):
        try:
            self.store.close()
        except Exception:
            pass
        if os.path.exists(self._db_path):
            os.unlink(self._db_path)

    def test_retrieve_accepts_keyword_arguments(self):
        """The test caller passes query=, project=, agent= as kwargs; retrieve() must accept them."""
        results = self.service.retrieve(
            query="lifecycle",
            project="host_val",
            agent="agent_a",
        )
        self.assertIsInstance(results, list)
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["memory"].text, "host lifecycle test memory")
        self.assertEqual(results[0]["memory"].scope.project, "host_val")
        self.assertEqual(results[0]["memory"].scope.agent, "agent_a")

    def test_retrieve_keyword_mode_without_agent(self):
        """Keyword-mode retrieve must accept agent=None (project-only scope)."""
        self.service.capture(
            text="project-only memory",
            project="host_val",
            agent=None,
        )
        results = self.service.retrieve(
            query="project-only",
            project="host_val",
        )
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["memory"].text, "project-only memory")

    def test_retrieve_keyword_mode_with_max_results(self):
        """Keyword-mode retrieve must accept max_results kwarg."""
        results = self.service.retrieve(
            query="lifecycle",
            project="host_val",
            agent="agent_a",
            max_results=10,
        )
        self.assertGreaterEqual(len(results), 1)

    def test_retrieve_positional_scope_mode_preserved(self):
        """Existing positional-Scope mode must continue to work unchanged."""
        results = self.service.retrieve("lifecycle", Scope("host_val", "agent_a"))
        self.assertIsInstance(results, list)
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["memory"].text, "host lifecycle test memory")

    def test_retrieve_positional_scope_mode_with_max_results(self):
        """Existing positional-Scope mode with max_results must continue to work."""
        results = self.service.retrieve("lifecycle", Scope("host_val", "agent_a"), max_results=10)
        self.assertGreaterEqual(len(results), 1)

    def test_retrieve_rejects_both_modes(self):
        """Passing both a positional scope and keyword project= must raise TypeError."""
        with self.assertRaises(TypeError):
            self.service.retrieve("lifecycle", Scope("host_val", "agent_a"), project="host_val")

    def test_retrieve_rejects_neither_mode(self):
        """Passing neither a positional scope nor keyword project= must raise TypeError."""
        with self.assertRaises(TypeError):
            self.service.retrieve("lifecycle")

    def test_retrieve_requires_query(self):
        """retrieve() without a query must raise TypeError."""
        with self.assertRaises(TypeError):
            self.service.retrieve(project="host_val", agent="agent_a")

    def test_retrieve_keyword_mode_scope_isolation(self):
        """Keyword-mode retrieve must respect scope isolation (different project returns nothing)."""
        results = self.service.retrieve(
            query="lifecycle",
            project="other_project",
            agent="agent_a",
        )
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
