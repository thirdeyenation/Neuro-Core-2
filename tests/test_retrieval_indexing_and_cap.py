"""Tests for retrieval indexing and result cap (WI-2026-08-24-RETRIEVAL-INDEXING-AND-RESULT-CAP)."""
import os
import sqlite3
import tempfile
import unittest

from memory_lifecycle import ValidationState
from memory_store import InMemoryStore
from neuro_core_2 import Memory, Scope, retrieve
from neuro_core_2_service import NeuroCoreService
from sqlite_store import SQLiteStore


def _temp_db() -> str:
    descriptor, path = tempfile.mkstemp(suffix=".db")
    os.close(descriptor)
    return path


def _seed_corpus(store) -> tuple[Scope, list[Memory]]:
    alpha = Scope("alpha")
    beta = Scope("beta")
    memories = [
        Memory("activity ledger decision", "fixture", alpha, 0.8, 0.9),
        Memory("activity ledger decision", "fixture", beta, 0.7, 0.8),
        Memory("schema check memory", "fixture", alpha, 0.6, 0.7),
        Memory("unique_marker_xyz", "fixture", alpha, 0.5, 0.6),
        Memory("activity ledger", "fixture", alpha, 0.9, 0.5),
        Memory("ledger decision", "fixture", alpha, 0.4, 0.4),
    ]
    for memory in memories:
        store.put(memory)
    return alpha, memories


class IndexedRetrievalEquivalenceTests(unittest.TestCase):
    """(a) Exact-equivalence of indexed retrieval vs unindexed baseline."""

    def test_indexed_retrieval_matches_unindexed_baseline_inmemory(self):
        store = InMemoryStore()
        alpha, _ = _seed_corpus(store)
        service = NeuroCoreService(store)
        for query in ("activity ledger", "schema", "unique_marker_xyz", "decision", "nonexistent"):
            baseline = retrieve(query, alpha, list(store.list(alpha)))
            indexed = service.retrieve(query, alpha)
            self.assertEqual(indexed, baseline, f"query={query}")

    def test_indexed_retrieval_matches_unindexed_baseline_sqlite(self):
        path = _temp_db()
        try:
            store = SQLiteStore(path)
            alpha, _ = _seed_corpus(store)
            service = NeuroCoreService(store)
            for query in ("activity ledger", "schema", "unique_marker_xyz", "decision", "nonexistent"):
                baseline = retrieve(query, alpha, list(store.list(alpha)))
                indexed = service.retrieve(query, alpha)
                self.assertEqual(indexed, baseline, f"query={query}")
            store.close()
        finally:
            os.unlink(path)


class ResultCapTests(unittest.TestCase):
    """(b) Cap behavior: count_exceeded/total_matches and cap applied after scoring."""

    def test_cap_returns_top_k_after_scoring(self):
        store = InMemoryStore()
        scope = Scope("alpha")
        for i in range(105):
            store.put(Memory("shared term", "fixture", scope, importance=0.01 * i, confidence=0.5))
        service = NeuroCoreService(store)

        payload = service.retrieve_with_meta("shared", scope, max_results=100)
        self.assertEqual(len(payload["results"]), 100)
        self.assertTrue(payload["count_exceeded"])
        self.assertEqual(payload["total_matches"], 105)

        # Cap applied AFTER scoring and sorting: returned results are exactly
        # the top-100 by score from the full ranked result set.
        baseline = retrieve("shared", scope, list(store.list(scope)))
        self.assertEqual(payload["results"], baseline[:100])
        self.assertGreaterEqual(payload["results"][-1]["score"], baseline[100]["score"])

    def test_no_cap_when_matches_below_limit(self):
        store = InMemoryStore()
        scope = Scope("alpha")
        for _ in range(3):
            store.put(Memory("shared term", "fixture", scope))
        service = NeuroCoreService(store)

        payload = service.retrieve_with_meta("shared", scope, max_results=100)
        self.assertEqual(len(payload["results"]), 3)
        self.assertFalse(payload["count_exceeded"])
        self.assertEqual(payload["total_matches"], 3)

    def test_cap_bounds_retrieved_activity_events(self):
        store = InMemoryStore()
        scope = Scope("alpha")
        for _ in range(150):
            store.put(Memory("shared term", "fixture", scope))
        service = NeuroCoreService(store)

        service.retrieve_with_meta("shared", scope, max_results=100)
        retrieved_events = [event for event in service.ledger.all() if event.kind == "retrieved"]
        self.assertEqual(len(retrieved_events), 100)


class MigrationConvergenceTests(unittest.TestCase):
    """(c) Fresh and legacy DBs converge to version 2 with data preserved."""

    def test_fresh_db_converges_to_version_2(self):
        path = _temp_db()
        try:
            store = SQLiteStore(path)
            self.assertEqual(store.schema_version(), 2)
            tables = {
                row[0]
                for row in store.connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            self.assertIn("memory_terms", tables)
            memory = Memory("fresh memory", "fixture", Scope("alpha"))
            store.put(memory)
            self.assertEqual(store.candidate_ids(["fresh"], Scope("alpha")), (memory.memory_id,))
            store.close()
        finally:
            os.unlink(path)

    def test_legacy_db_converges_to_version_2_with_data_preserved(self):
        path = _temp_db()
        try:
            conn = sqlite3.connect(path)
            conn.execute(
                "CREATE TABLE memories (id TEXT PRIMARY KEY, text TEXT, source TEXT, project TEXT, agent TEXT, importance REAL, confidence REAL, validation TEXT)"
            )
            conn.execute(
                "CREATE TABLE activity_events (event_id TEXT PRIMARY KEY, kind TEXT, project TEXT, agent TEXT, targets TEXT, outcome TEXT, source TEXT, occurred_at TEXT)"
            )
            conn.execute(
                "INSERT INTO memories VALUES ('legacy-1', 'legacy memory', 'fixture', 'alpha', NULL, 0.5, 0.5, 'unreviewed')"
            )
            conn.execute(
                "INSERT INTO activity_events VALUES ('evt-1', 'captured', 'alpha', NULL, 'legacy-1', 'stored', 'fixture', '2026-08-18T00:00:00+00:00')"
            )
            conn.commit()
            conn.close()

            store = SQLiteStore(path)
            self.assertEqual(store.schema_version(), 2)
            self.assertEqual(store.get("legacy-1").text, "legacy memory")
            self.assertEqual(len(store.list_events(Scope("alpha"))), 1)
            # Backfill from existing memories.text using exact tokenization.
            self.assertEqual(store.candidate_ids(["legacy"], Scope("alpha")), ("legacy-1",))
            self.assertEqual(store.candidate_ids(["memory"], Scope("alpha")), ("legacy-1",))
            self.assertEqual(store.candidate_ids(["missing"], Scope("alpha")), ())
            store.close()
        finally:
            os.unlink(path)


class RestartPersistenceTests(unittest.TestCase):
    """(d) Restart persistence of index correctness."""

    def test_index_remains_consistent_after_reopen(self):
        path = _temp_db()
        try:
            store = SQLiteStore(path)
            alpha = Scope("alpha")
            memory = Memory("persist this decision", "fixture", alpha)
            store.put(memory)
            store.close()

            reopened = SQLiteStore(path)
            self.assertEqual(reopened.schema_version(), 2)
            self.assertEqual(reopened.candidate_ids(["persist"], alpha), (memory.memory_id,))
            self.assertEqual(reopened.candidate_ids(["decision"], alpha), (memory.memory_id,))
            service = NeuroCoreService(reopened)
            self.assertEqual(service.retrieve("persist decision", alpha)[0]["memory"], memory)
            reopened.close()
        finally:
            os.unlink(path)

    def test_put_updates_index_terms(self):
        path = _temp_db()
        try:
            store = SQLiteStore(path)
            alpha = Scope("alpha")
            memory = Memory("old term", "fixture", alpha)
            store.put(memory)
            self.assertEqual(store.candidate_ids(["old"], alpha), (memory.memory_id,))
            self.assertEqual(store.candidate_ids(["new"], alpha), ())

            updated = Memory("new term", "fixture", alpha, memory_id=memory.memory_id)
            store.put(updated)
            self.assertEqual(store.candidate_ids(["old"], alpha), ())
            self.assertEqual(store.candidate_ids(["new"], alpha), (memory.memory_id,))
            store.close()
        finally:
            os.unlink(path)


class SupersededExclusionTests(unittest.TestCase):
    """(e) Superseded-memory exclusion still holds through the index path."""

    def test_superseded_excluded_through_index_path_inmemory(self):
        store = InMemoryStore()
        scope = Scope("alpha")
        service = NeuroCoreService(store)
        memory = service.capture(Memory("activity ledger", "fixture", scope))
        self.assertEqual(len(service.retrieve("activity", scope)), 1)
        # candidate_ids is a pure pre-filter: superseded memories remain candidates.
        self.assertIn(memory.memory_id, store.candidate_ids(["activity"], scope))
        service.validate(memory.memory_id, ValidationState.SUPERSEDED)
        self.assertEqual(service.retrieve("activity", scope), [])

    def test_superseded_excluded_through_index_path_sqlite(self):
        path = _temp_db()
        try:
            store = SQLiteStore(path)
            scope = Scope("alpha")
            service = NeuroCoreService(store)
            memory = service.capture(Memory("activity ledger", "fixture", scope))
            self.assertEqual(len(service.retrieve("activity", scope)), 1)
            self.assertIn(memory.memory_id, store.candidate_ids(["activity"], scope))
            service.validate(memory.memory_id, ValidationState.SUPERSEDED)
            self.assertEqual(service.retrieve("activity", scope), [])
            store.close()
        finally:
            os.unlink(path)


class ScopeIsolationTests(unittest.TestCase):
    """(f) Scope isolation via candidate_ids."""

    def test_candidate_ids_filters_by_scope_sqlite(self):
        path = _temp_db()
        try:
            store = SQLiteStore(path)
            alpha = Scope("alpha")
            beta = Scope("beta")
            alpha_agent1 = Scope("alpha", "agent1")
            alpha_agent2 = Scope("alpha", "agent2")
            m_alpha = Memory("shared term", "fixture", alpha)
            m_beta = Memory("shared term", "fixture", beta)
            m_agent1 = Memory("shared term", "fixture", alpha_agent1)
            m_agent2 = Memory("shared term", "fixture", alpha_agent2)
            for memory in (m_alpha, m_beta, m_agent1, m_agent2):
                store.put(memory)

            self.assertEqual(set(store.candidate_ids(["shared"], alpha)), {m_alpha.memory_id})
            self.assertEqual(set(store.candidate_ids(["shared"], beta)), {m_beta.memory_id})
            self.assertEqual(set(store.candidate_ids(["shared"], alpha_agent1)), {m_agent1.memory_id})
            self.assertEqual(set(store.candidate_ids(["shared"], alpha_agent2)), {m_agent2.memory_id})
            store.close()
        finally:
            os.unlink(path)

    def test_candidate_ids_filters_by_scope_inmemory(self):
        store = InMemoryStore()
        alpha = Scope("alpha")
        beta = Scope("beta")
        m_alpha = Memory("shared term", "fixture", alpha)
        m_beta = Memory("shared term", "fixture", beta)
        store.put(m_alpha)
        store.put(m_beta)

        self.assertEqual(store.candidate_ids(["shared"], alpha), (m_alpha.memory_id,))
        self.assertEqual(store.candidate_ids(["shared"], beta), (m_beta.memory_id,))


if __name__ == "__main__":
    unittest.main()
