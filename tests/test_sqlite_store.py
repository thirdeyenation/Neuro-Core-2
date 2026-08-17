import os
import tempfile
import unittest

from memory_lifecycle import ValidationState
from neuro_core_2 import Memory, Scope
from neuro_core_2_service import NeuroCoreService
from sqlite_store import SQLiteStore


class SQLiteStoreTests(unittest.TestCase):
    def test_memory_survives_reopen_and_scopes_remain_isolated(self):
        descriptor, path = tempfile.mkstemp()
        os.close(descriptor)
        try:
            alpha, beta = Scope("alpha"), Scope("beta")
            memory = Memory("persist this decision", "fixture", alpha)
            store = SQLiteStore(path)
            store.put(memory)
            store.put(Memory("other project", "fixture", beta))
            store.close()

            reopened = SQLiteStore(path)
            self.assertEqual(reopened.get(memory.memory_id), memory)
            self.assertEqual(reopened.list(alpha), (memory,))
            reopened.close()
        finally:
            os.unlink(path)

    def test_schema_survives_restart_and_additive_activity_writes(self):
        descriptor, path = tempfile.mkstemp()
        os.close(descriptor)
        try:
            alpha = Scope("alpha")
            store = SQLiteStore(path)
            service = NeuroCoreService(store)
            memory = service.capture(Memory("schema check memory", "fixture", alpha))
            updated = service.validate(memory.memory_id, ValidationState.VALIDATED)
            store.close()

            reopened = SQLiteStore(path)
            service = NeuroCoreService(reopened)
            self.assertEqual(reopened.get(memory.memory_id), updated)
            events = service.list_activity(alpha)
            self.assertEqual([event.kind for event in events], ["captured", "validation_changed"])

            second = service.capture(Memory("schema check memory 2", "fixture", alpha))
            self.assertEqual(service.retrieve("schema check memory 2", alpha)[0]["memory"], second)
            # Use a unique query that only matches the second memory to avoid
            # lexical overlap with the first memory ("schema check memory").
            self.assertEqual(service.retrieve("unique_marker_xyz", alpha), [])
            self.assertEqual([event.kind for event in service.list_activity(alpha)], ["captured", "validation_changed", "captured", "retrieved", "retrieved"])
            reopened.close()
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
