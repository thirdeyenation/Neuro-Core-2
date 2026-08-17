import unittest

from neuro_core_2 import Memory, Scope, retrieve


class RetrievalTests(unittest.TestCase):
    def test_scope_isolation_and_explanation_factors(self):
        scope = Scope("alpha")
        matching = Memory("activity ledger decision", "fixture", scope, .8, .9)
        other = Memory("activity ledger decision", "fixture", Scope("beta"))

        result = retrieve("activity ledger", scope, [other, matching])

        self.assertEqual([item["memory"] for item in result], [matching])
        self.assertGreater(result[0]["factors"]["overlap"], 0)
        self.assertEqual(result[0]["factors"]["importance"], .8)
        self.assertEqual(result[0]["factors"]["confidence"], .9)


if __name__ == "__main__":
    unittest.main()
