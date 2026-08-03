import unittest

from memory_lifecycle import ValidationState, transition
from neuro_core import Memory, Scope, retrieve


class LifecycleTests(unittest.TestCase):
    def test_superseded_memory_is_excluded(self):
        scope = Scope("alpha")
        live = Memory("use activity ledger", "fixture", scope)
        old = Memory("use activity ledger", "fixture", scope, validation=ValidationState.SUPERSEDED)
        result = retrieve("activity ledger", scope, [old, live])
        self.assertEqual([item["memory"] for item in result], [live])

    def test_terminal_state_rejects_transition(self):
        with self.assertRaises(ValueError):
            transition(ValidationState.SUPERSEDED, ValidationState.VALIDATED)

    def test_disputed_item_can_be_validated(self):
        self.assertEqual(transition(ValidationState.DISPUTED, ValidationState.VALIDATED), ValidationState.VALIDATED)


if __name__ == "__main__":
    unittest.main()
