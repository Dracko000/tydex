import unittest

from tydex import MockBackend, RequiresHuman, RoutedTydex, Tier, Tydex


def make_weak():
    return MockBackend({"0": 0.55, "1": 0.45, "Yes": 0.6, "No": 0.4})


def make_strong():
    return MockBackend({"0": 0.92, "1": 0.08, "Yes": 0.88, "No": 0.12})


class TestRouting(unittest.IsolatedAsyncioTestCase):
    async def test_no_escalation_when_confident(self):
        routed = RoutedTydex([Tier(Tydex(make_strong()), threshold=0.8, label="strong", cost=1.0)])
        r = await routed.choice({}, ["a", "b"])
        self.assertEqual(r.escalations, [])
        self.assertEqual(r.tier, "strong")
        self.assertEqual(r.total_cost, 1.0)

    async def test_escalation_and_cost(self):
        routed = RoutedTydex(
            [
                Tier(Tydex(make_weak()), threshold=0.8, label="weak", cost=0.1),
                Tier(Tydex(make_strong()), threshold=None, label="strong", cost=1.0),
            ]
        )
        r = await routed.choice({}, ["a", "b"])
        self.assertEqual(r.escalations, ["weak"])
        self.assertEqual(r.tier, "strong")
        self.assertAlmostEqual(r.total_cost, 1.1)

    async def test_per_call_min_confidence_override(self):
        routed = RoutedTydex([Tier(Tydex(make_weak()), threshold=0.4, label="weak")])
        r = await routed.choice({}, ["a", "b"], min_confidence=0.9)
        self.assertEqual(r.escalations, ["weak"])
        self.assertEqual(r.tier, "weak")

    async def test_human_fallback(self):
        routed = RoutedTydex([Tier(Tydex(make_weak()), threshold=0.9, label="weak"), Tier(action="human", label="human")])
        with self.assertRaises(RequiresHuman) as ctx:
            await routed.noul({}, "statement")
        self.assertEqual(ctx.exception.escalations, ["weak"])
        self.assertIn("state", ctx.exception.request)

    async def test_human_tier_requires_request_context(self):
        with self.assertRaises(RequiresHuman) as ctx:
            await RoutedTydex([Tier(action="human")]).choice({"x": 1}, ["a", "b"])
        self.assertEqual(ctx.exception.request["state"], {"x": 1})

    def test_requires_at_least_one_tier(self):
        with self.assertRaises(ValueError):
            RoutedTydex([])

    def test_tier_label_defaults_to_model(self):
        tier = Tier(Tydex(make_weak(), model="my-model"))
        self.assertEqual(tier.label, "my-model")


if __name__ == "__main__":
    unittest.main()