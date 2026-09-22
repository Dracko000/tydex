import unittest

from tydex import IsotonicCalibrator
from tydex.calibration import _metrics, _rescale_all, tune_temperature


class TestMetrics(unittest.TestCase):
    def test_perfect_calibration(self):
        probs = [{"a": 1.0, "b": 1e-9}, {"b": 1.0, "a": 1e-9}]
        labels = ["a", "b"]
        m = _metrics(probs, labels)
        self.assertAlmostEqual(m.ece, 0.0)
        self.assertAlmostEqual(m.accuracy, 1.0)

    def test_brier_known_case(self):
        probs = [{"a": 0.8, "b": 0.2}]
        m = _metrics(probs, ["a"])
        self.assertAlmostEqual(m.brier, (1 - 0.8) ** 2)


class TestTuneTemperature(unittest.TestCase):
    def test_returns_calibration_result(self):
        probs = [{"a": 0.95, "b": 0.05}, {"a": 0.92, "b": 0.08}, {"a": 0.3, "b": 0.7}, {"a": 0.25, "b": 0.75}]
        labels = ["a", "a", "b", "b"]
        result = tune_temperature(probs, labels, temperature_grid=[x / 10 for x in range(5, 51)])
        self.assertGreaterEqual(result.temperature, 0.5)
        self.assertLessEqual(result.metrics.ece, result.baseline.ece + 1e-9)


class TestIsotonic(unittest.TestCase):
    def test_monotonic_non_decreasing_after_fit(self):
        cal = IsotonicCalibrator().fit(
            [0.3, 0.5, 0.7, 0.9, 0.4, 0.6, 0.8],
            [False, True, True, True, False, False, True],
            blend=1.0,
        )
        xs = sorted(set(cal.xs))
        last = -1.0
        for x in xs:
            y = cal.transform(x)
            self.assertGreaterEqual(y + 1e-12, last)
            last = y

    def test_transform_clamps_ends(self):
        cal = IsotonicCalibrator().fit([0.2, 0.8], [False, True], blend=1.0)
        self.assertEqual(cal.transform(0.0), cal.transform(0.2))
        self.assertEqual(cal.transform(1.0), cal.transform(0.8))

    def test_transform_probs_preserves_argmax_domain(self):
        cal = IsotonicCalibrator().fit([0.3, 0.6, 0.9], [False, True, True], blend=1.0)
        out = cal.transform_probs({"a": 0.6, "b": 0.4})
        self.assertAlmostEqual(sum(out.values()), 1.0)
        self.assertGreater(out["a"], out["b"])

    def test_empty_fit_is_identity(self):
        out = IsotonicCalibrator().transform_probs({"a": 0.6, "b": 0.4})
        self.assertEqual(out, {"a": 0.6, "b": 0.4})


class TestRescaleAll(unittest.TestCase):
    def test_unchanged_at_t1(self):
        probs = [{"a": 0.6, "b": 0.4}]
        self.assertEqual(_rescale_all(probs, 1.0), probs)


if __name__ == "__main__":
    unittest.main()