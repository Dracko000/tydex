import logging
import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from tydex import AutoCalibrator, MockBackend, Recorder
from tydex.server import build_app

logging.getLogger("httpx").setLevel(logging.WARNING)


class TestServer(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.auto = AutoCalibrator(
            Recorder(os.path.join(self.dir, "feedback.db")),
            refit_every=5,
            config_path=os.path.join(self.dir, "calibration.json"),
            min_samples=2,
        )
        self.backend = MockBackend({"0": 0.95, "1": 0.05, "Yes": 0.9, "No": 0.1})
        self.app = build_app(backend=self.backend, model="mock", auto=self.auto)
        self.client = TestClient(self.app)

    def test_health(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    def test_evaluate_no_auth_required(self):
        payload = {
            "state": {"ticket": "1"},
            "questions": [
                {"id": "q1", "type": "choice", "options": ["refund", "replace"]},
                {"id": "q2", "type": "noul", "statement": "This needs review"},
            ],
        }
        resp = self.client.post("/evaluate", json=payload)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body["results"]), 2)
        self.assertEqual(body["errors"], [])
        choice = body["results"][0]
        self.assertEqual(choice["choice"], "refund")
        self.assertTrue(choice["log_id"])
        self.assertTrue(body["results"][1]["log_id"])

    def test_evaluate_error_isolated(self):
        payload = {
            "state": {},
            "questions": [
                {"id": "bad", "type": "choice", "options": ["only-one"]},
                {"id": "ok", "type": "score", "levels": ["low", "high"]},
            ],
        }
        resp = self.client.post("/evaluate", json=payload)
        body = resp.json()
        self.assertEqual(len(body["results"]), 1)
        self.assertEqual(len(body["errors"]), 1)
        self.assertEqual(body["errors"][0]["id"], "bad")

    def test_label_and_suggest(self):
        evaluate = self.client.post(
            "/evaluate",
            json={"state": {}, "questions": [{"id": "q", "type": "choice", "options": ["a", "b"]}]},
        )
        log_id = evaluate.json()["results"][0]["log_id"]
        suggest = self.client.get("/suggest")
        self.assertEqual(suggest.status_code, 200)
        self.assertIn(log_id, suggest.json()["suggested_ids"])

        label = self.client.post("/label", json={"log_id": log_id, "label": "a"})
        self.assertEqual(label.status_code, 200)
        self.assertIn("refitted", label.json())

        status = self.client.get("/calibration")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["pending"], 1)

        miss = self.client.post("/label", json={"log_id": "nope", "label": "x"})
        self.assertEqual(miss.status_code, 404)

    def test_refit(self):
        self.client.post(
            "/evaluate",
            json={"state": {}, "questions": [{"id": "1", "type": "choice", "options": ["a", "b"]}]},
        )
        resp = self.client.post("/refit")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("refitted", resp.json())

    def test_routed_evaluate(self):
        from tydex import RoutedTydex, Tier, Tydex

        weak = Tydex(MockBackend({"0": 0.55, "1": 0.45}), model="weak")
        strong = Tydex(MockBackend({"0": 0.95, "1": 0.05}), model="strong")
        routed = RoutedTydex([Tier(weak, threshold=0.8, label="weak", cost=0.1), Tier(strong, threshold=None, label="strong", cost=1.0)])
        app = build_app(routed=routed)
        with TestClient(app) as client:
            resp = client.post(
                "/evaluate",
                json={"state": {}, "questions": [{"id": "q", "type": "choice", "options": ["a", "b"], "min_confidence": 0.9}]},
            )
        self.assertEqual(resp.status_code, 200)
        result = resp.json()["results"][0]
        self.assertEqual(result["choice"], "a")
        self.assertEqual(result["tier"], "strong")
        self.assertEqual(result["escalations"], ["weak"])
        self.assertAlmostEqual(result["total_cost"], 1.1)

    def test_api_key_required(self):
        app = build_app(backend=MockBackend(), model="mock", api_key="secret")
        client = TestClient(app)
        self.assertEqual(client.get("/calibration").status_code, 401)
        self.assertEqual(client.get("/health").status_code, 200)
        self.assertEqual(client.get("/calibration", headers={"X-Api-Key": "wrong"}).status_code, 401)
        self.assertEqual(client.get("/calibration", headers={"Authorization": "Bearer secret"}).status_code, 404)


if __name__ == "__main__":
    unittest.main()