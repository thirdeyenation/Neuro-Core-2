import unittest

from memory_lifecycle import ValidationState
from memory_store import InMemoryStore
from neuro_core import Memory, Scope
from neuro_service import NeuroCoreService


class NeuroCoreServiceTests(unittest.TestCase):
    def test_capture_retrieve_supersede_and_audit(self):
        scope = Scope("alpha")
        service = NeuroCoreService(InMemoryStore())
        memory = service.capture(Memory("use activity ledger", "fixture", scope))

        self.assertEqual(service.retrieve("activity ledger", scope)[0]["memory"], memory)
        superseded = service.validate(memory.memory_id, ValidationState.SUPERSEDED)
        self.assertEqual(superseded.validation, ValidationState.SUPERSEDED)
        self.assertEqual(service.retrieve("activity ledger", scope), [])
        self.assertEqual([event.kind for event in service.ledger.for_scope(scope)], ["captured", "retrieved", "validation_changed"])


if __name__ == "__main__":
    unittest.main()
