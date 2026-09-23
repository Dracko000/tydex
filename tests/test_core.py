import unittest

from tydex import MockBackend, SchemaError, Tydex
from tydex.core import _parse_json, _rescale


class FakeJsonBackend:
    supports_logprobs = True

    def __init__(self, text):
        self._text = text

    async def complete(self, *, messages, temperature=0.0, max_tokens=1, logprobs=False, top_logprobs=0, json_mode=False):
        return type("R", (), {"text": self._text, "logprobs": None})()


class TestParseJson(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(_parse_json('{"a": 1}'), {"a": 1})

    def test_code_fence(self):
        self.assertEqual(_parse_json('```json\n{"probability": 0.95}\n```'), {"probability": 0.95})

    def test_trailing_text(self):
        self.assertEqual(_parse_json('Here: {"a": {"b": 1}} done'), {"a": {"b": 1}})

    def test_nested_braces(self):
        self.assertEqual(_parse_json('{"x": {"y": [1, 2]}}'), {"x": {"y": [1, 2]}})


class TestRescale(unittest.TestCase):
    def test_identity(self):
        probs = {"a": 0.6, "b": 0.4}
        self.assertEqual(_rescale(probs, 1.0), probs)

    def test_sharpening_sums_to_one(self):
        probs = _rescale({"a": 0.6, "b": 0.4}, 0.5)
        self.assertAlmostEqual(sum(probs.values()), 1.0)
        self.assertGreater(probs["a"], 0.6)

    def test_zero_temperature_rejected(self):
        with self.assertRaises(ValueError):
            _rescale({"a": 0.5, "b": 0.5}, 0.0)


class TestChoiceLogprobs(unittest.IsolatedAsyncioTestCase):
    async def test_normalization_and_full_mapping(self):
        backend = MockBackend({"0": 0.6, "1": 0.3, "2": 0.1, "Yes": 0.7, "No": 0.3})
        result = await Tydex(backend).choice({}, ["a", "b", "c", "d"])
        self.assertEqual(result.choice, "a")
        self.assertAlmostEqual(sum(result.probabilities.values()), 1.0)
        self.assertEqual(result.probabilities["d"], 0.0)
        self.assertEqual(result.source, "logprobs")

    async def test_temperature_parameter(self):
        backend = MockBackend({"0": 0.6, "1": 0.4})
        hot = await Tydex(backend).choice({}, ["a", "b"], temperature=5.0)
        flat = await Tydex(backend).choice({}, ["a", "b"], temperature=0.5)
        self.assertLess(hot.confidence, flat.confidence)

    async def test_requires_two_options(self):
        with self.assertRaises(ValueError):
            await Tydex(MockBackend()).choice({}, ["only"])


class TestNoulLogprobs(unittest.IsolatedAsyncioTestCase):
    async def test_yes_no(self):
        backend = MockBackend({"Yes": 0.7, "No": 0.3})
        result = await Tydex(backend).noul({}, "some statement")
        self.assertAlmostEqual(result.probability, 0.7)
        self.assertTrue(result.bool_value)

    async def test_temperature_flattens(self):
        backend = MockBackend({"Yes": 0.95, "No": 0.05})
        r = await Tydex(backend).noul({}, "s", temperature=4.0)
        self.assertLess(r.probability, 0.95)


class TestChoiceSelf(unittest.IsolatedAsyncioTestCase):
    async def test_fenced_json_outside_schema_rejected(self):
        backend = FakeJsonBackend('```json\n{"choice": "bogus", "probability": 0.9}\n```')
        with self.assertRaises(SchemaError):
            await Tydex(backend).choice({}, ["a", "b"], mode="self")

    async def test_valid_choice_residual_spread(self):
        backend = FakeJsonBackend('{"choice": "b", "probability": 0.82}')
        result = await Tydex(backend).choice({}, ["a", "b", "c"], mode="self")
        self.assertEqual(result.choice, "b")
        self.assertAlmostEqual(sum(result.probabilities.values()), 1.0)
        self.assertAlmostEqual(result.probabilities["a"], result.probabilities["c"])

    async def test_probability_clamped(self):
        backend = FakeJsonBackend('{"choice": "a", "probability": 3.0}')
        result = await Tydex(backend).choice({}, ["a", "b"], mode="self")
        self.assertEqual(result.confidence, 1.0)

    async def test_noul_self_clamps(self):
        backend = FakeJsonBackend('{"probability": -2.0}')
        result = await Tydex(backend).noul({}, "s", mode="self")
        self.assertEqual(result.probability, 0.0)


if __name__ == "__main__":
    unittest.main()