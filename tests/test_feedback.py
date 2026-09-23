import os
import tempfile
import unittest

from tydex import ChoiceResult, NoulResult, Recorder


class TestRecorderRoundTrip(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "log.jsonl")

    def test_roundtrip_labels(self):
        rec = Recorder(self.path)
        r = ChoiceResult(choice="refund", probabilities={"refund": 0.6, "replace": 0.4}, confidence=0.6, source="logprobs")
        entry = rec.choice({"ticket": "1"}, ["refund", "replace"], r)
        self.assertIsNone(entry.label)
        rec.label(entry.id, "refund")

        other = Recorder(self.path)
        self.assertEqual(len(other._entries), 1)
        self.assertEqual(other._entries[0].label, "refund")
        self.assertEqual(other.labeled()[0].choice, "refund")

    def test_unknown_label_raises(self):
        rec = Recorder(self.path)
        with self.assertRaises(KeyError):
            rec.label("nope", "x")

    def test_noul_correct(self):
        rec = Recorder(self.path)
        r = NoulResult(probability=0.9, confidence=0.9, source="self")
        entry = rec.noul({"x": 1}, "t", r)
        rec.label(entry.id, "true")
        self.assertTrue(entry.correct)

    def test_reset(self):
        rec = Recorder(self.path)
        rec.choice({"x": 1}, ["a", "b"], ChoiceResult("a", {"a": 0.5, "b": 0.5}, 0.5, "m"))
        rec.reset()
        self.assertEqual(len(rec._entries), 0)
        other = Recorder(self.path)
        self.assertEqual(other.labeled(), [])

    def test_report_fields(self):
        rec = Recorder(self.path)
        rec.choice({"x": 1}, ["a", "b"], ChoiceResult("a", {"a": 0.9, "b": 0.1}, 0.9, "m"))
        report = rec.report()
        self.assertIn("per_primitive", report)
        self.assertIn("routing", report)


if __name__ == "__main__":
    unittest.main()