import unittest

from memory_store import InMemoryStore
from neuro_core_2 import Memory, Scope


class StoreTests(unittest.TestCase):
    def test_duplicate_content_coexists_by_id_and_scope_isolation_holds(self):
        alpha, beta = Scope("alpha"), Scope("beta")
        first = Memory("same text", "fixture", alpha)
        second = Memory("same text", "fixture", alpha)
        other = Memory("same text", "fixture", beta)
        store = InMemoryStore()
        for item in (first, second, other):
            store.put(item)
        self.assertNotEqual(first.memory_id, second.memory_id)
        self.assertIs(store.get(first.memory_id), first)
        self.assertEqual(set(store.list(alpha)), {first, second})


if __name__ == "__main__":
    unittest.main()
