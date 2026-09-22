import os
import tempfile
import unittest

from tydex import AutoCalibrator, MockBackend, NoulResult, Recorder, Tydex


class FakeJsonBackend:
    supports_logprobs = True

    def __init__(self, text):
        self._text = text

    def complete(self, *, messages, temperature=0.0, max_tokens=1, logprobs=False, top_logprobs=0, json_mode=False):
        return type("R", (), {"text": self._text, "logprobs": None})()


class TestAutoCalibrator(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.rec = Recorder(os.path.join(self.dir, "fb.jsonl"))

    def _seed(self, n_true, n_false):
        p = 0.85
        for _ in range(n_true):
            entry = self.rec.noul({"i": _}, "is true", NoulResult(p, p, "self"))
            self.rec.label(entry.id, "true")
        for _ in range(n_false):
            entry = self.rec.noul({"i": _}, "is false", NoulResult(p, p, "self"))
            self.rec.label(entry.id, "false")

    def test_pending_and_refit_trigger(self):
        auto = AutoCalibrator(self.rec, refit_every=3, config_path=os.path.join(self.dir, "c.json"), min_samples=2)
        self._seed(2, 0)
        self.assertFalse(auto.maybe_refit())
        self._seed(1, 0)
        self.assertTrue(auto.maybe_refit())
        self.assertEqual(auto.pending, 0)

    def test_live_update_after_refit(self):
        auto = AutoCalibrator(self.rec, refit_every=4, config_path=os.path.join(self.dir, "c.json"), min_samples=2)
        cal = auto.apply_to(Tydex(MockBackend(), model="mock"))
        before = cal.noul({}, "x").confidence
        self._seed(2, 2)
        auto.maybe_refit()
        after = cal.noul({}, "x").confidence
        self.assertNotEqual(before, after)
        self.assertLessEqual(after, 0.95)


if __name__ == "__main__":
    unittest.main()