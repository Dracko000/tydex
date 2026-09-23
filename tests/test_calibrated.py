import os
import tempfile
import unittest

from tydex import ChoiceResult, MockBackend, NoulResult, Recorder, Tydex
from tydex.calibrated import CalibrationSystem, IsotonicCalibrator


def seed_recorder(rec, n=12, p=0.8):
    for i in range(n):
        e = rec.noul({"i": i}, f"true {i}", NoulResult(p, p, "self"))
        rec.label(e.id, "true")
    for i in range(n):
        e = rec.noul({"i": i}, f"false {i}", NoulResult(p, p, "self"))
        rec.label(e.id, "false")


class TestCalibrationSystem(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.rec = Recorder(os.path.join(self.dir, "fb.jsonl"))
        seed_recorder(self.rec)

    def test_fit_and_transform_applies(self):
        system = CalibrationSystem(self.rec, min_samples=4).fit()
        self.assertIn("noul", system.calibrators)
        probs = system.transform("noul", {"true": 0.8, "false": 0.2})
        self.assertLess(probs["true"], 0.8)

    def test_below_min_samples_untouched(self):
        system = CalibrationSystem(self.rec, min_samples=1000).fit(force=False)
        self.assertNotIn("noul", system.calibrators)
        self.assertEqual(system.transform("noul", {"true": 0.8, "false": 0.2}), {"true": 0.8, "false": 0.2})

    def test_save_load_roundtrip(self):
        system = CalibrationSystem(self.rec, min_samples=4).fit()
        path = os.path.join(self.dir, "c.json")
        system.save(path)

        loaded = CalibrationSystem(Recorder(os.path.join(self.dir, "empty.jsonl"))).load(path)
        self.assertEqual(set(loaded.temperatures), set(system.temperatures))
        self.assertAlmostEqual(loaded.transform("noul", {"true": 0.8, "false": 0.2})["true"], system.transform("noul", {"true": 0.8, "false": 0.2})["true"])

    async def test_apply_to_wraps_choice(self):
        system = CalibrationSystem(self.rec, min_samples=4).fit()
        tdex = system.apply_to(Tydex(MockBackend(), model="mock"))
        result = await tdex.choice({}, ["a", "b"])
        self.assertIsInstance(result, ChoiceResult)
        self.assertIn("+cal", result.source)

    def test_no_ref_fit_guard(self):
        system = CalibrationSystem(self.rec, min_samples=2).fit()
        meta = system.meta["noul"]
        n = meta["n"]
        self.assertEqual(meta["n"], n)
        self.assertLessEqual(meta["ece_after_calibrator"], meta["ece_before"] + 1e-9)


class TestIsotonicBlend(unittest.TestCase):
    def test_blend_towards_identity_with_few_samples(self):
        data = (
            [0.9] * 3 + [0.4] * 1,
            [True, True, True, False],
        )
        pure = IsotonicCalibrator().fit(*data, blend=1.0)
        blended = IsotonicCalibrator().fit(*data, blend=0.2)
        self.assertLess(blended.transform(0.9), pure.transform(0.9))

    def test_medium_domain_perfect_preserved(self):
        cal = IsotonicCalibrator().fit([0.0, 0.5, 1.0], [False, False, True], blend=0.5)
        self.assertEqual(cal.transform(1.0), 1.0)
        self.assertEqual(cal.transform(0.0), 0.0)


if __name__ == "__main__":
    unittest.main()