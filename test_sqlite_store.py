import os
import tempfile
import unittest

from neuro_core import Memory, Scope
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


if __name__ == "__main__":
    unittest.main()
