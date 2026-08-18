"""Tests for the Neuro Core 2 schema migration runner and concurrency model."""
import multiprocessing
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from migrations import run_migrations
from neuro_core_2 import Memory, Scope
from sqlite_store import SQLiteStore


def _concurrent_write_worker(db_path: str, barrier, row_id: str, text: str) -> None:
    """Open a store, wait at the barrier, then write a distinct row.

    The barrier guarantees both processes are ready before either attempts
    its write, so the test reliably exercises the SQLite write-serialization
    path (BEGIN IMMEDIATE + busy_timeout) rather than racing by chance.
    """
    store = SQLiteStore(db_path)
    try:
        barrier.wait()
        store.put(Memory(text, "concurrency", Scope("concurrency"), 0.5, 0.5, memory_id=row_id))
    finally:
        store.close()


class MigrationTests(unittest.TestCase):
    def _temp_db(self) -> str:
        descriptor, path = tempfile.mkstemp(suffix=".db")
        os.close(descriptor)
        return path

    def test_fresh_db_migrates_to_version_1_and_is_writable(self):
        path = self._temp_db()
        try:
            store = SQLiteStore(path)
            self.assertEqual(store.schema_version(), 1)
            tables = {
                row[0]
                for row in store.connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            self.assertIn("memories", tables)
            self.assertIn("activity_events", tables)
            memory = Memory("fresh db", "fixture", Scope("alpha"))
            store.put(memory)
            self.assertEqual(store.get(memory.memory_id), memory)
            store.close()
        finally:
            os.unlink(path)

    def test_legacy_db_upgrade_preserves_rows_and_records_version(self):
        path = self._temp_db()
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
            self.assertEqual(store.schema_version(), 1)
            memory = store.get("legacy-1")
            self.assertIsNotNone(memory)
            self.assertEqual(memory.text, "legacy memory")
            events = store.list_events(Scope("alpha"))
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].event_id, "evt-1")
            store.close()
        finally:
            os.unlink(path)

    def test_migration_runner_is_idempotent(self):
        path = self._temp_db()
        try:
            store = SQLiteStore(path)
            memory = Memory("idempotent", "fixture", Scope("alpha"))
            store.put(memory)
            store.close()

            conn = sqlite3.connect(path)
            run_migrations(conn)
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 1)
            conn.close()

            store = SQLiteStore(path)
            self.assertEqual(store.schema_version(), 1)
            self.assertEqual(store.get(memory.memory_id), memory)
            store.close()
        finally:
            os.unlink(path)

    def test_newer_version_database_is_rejected(self):
        path = self._temp_db()
        try:
            conn = sqlite3.connect(path)
            conn.execute("PRAGMA user_version = 2")
            conn.commit()
            conn.close()

            with self.assertRaises(RuntimeError) as ctx:
                SQLiteStore(path)
            self.assertIn("newer than this code", str(ctx.exception))

            # No corruption: the version marker is untouched.
            conn = sqlite3.connect(path)
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 2)
            conn.close()
        finally:
            os.unlink(path)

    def test_concurrent_writers_serialize_without_lock_error(self):
        path = self._temp_db()
        try:
            store = SQLiteStore(path)
            store.close()

            ctx = multiprocessing.get_context("fork")
            barrier = ctx.Barrier(2)
            p1 = ctx.Process(
                target=_concurrent_write_worker,
                args=(path, barrier, "row-1", "concurrent memory one"),
            )
            p2 = ctx.Process(
                target=_concurrent_write_worker,
                args=(path, barrier, "row-2", "concurrent memory two"),
            )
            p1.start()
            p2.start()
            p1.join(timeout=60)
            p2.join(timeout=60)
            self.assertEqual(
                p1.exitcode, 0, f"worker 1 failed with exit code {p1.exitcode}"
            )
            self.assertEqual(
                p2.exitcode, 0, f"worker 2 failed with exit code {p2.exitcode}"
            )

            store = SQLiteStore(path)
            self.assertIsNotNone(store.get("row-1"))
            self.assertIsNotNone(store.get("row-2"))
            store.close()
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
