import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tydex import AutoCalibrator, MockBackend, Recorder
from tydex.server import TydexHttpHandler, build_server


class HttpBase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.backend = MockBackend()
        server = self._make_server()
        self.httpd = server
        self.port = server.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def _make_server(self):
        raise NotImplementedError

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def get(self, path):
        try:
            with urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=10) as resp:
                return resp.status, json.loads(resp.read().decode())
        except HTTPError as exc:
            return exc.code, json.loads(exc.read().decode())

    def post(self, path, payload=None):
        req = Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=json.dumps(payload or {}).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read().decode())
        except HTTPError as exc:
            return exc.code, json.loads(exc.read().decode())


class TestBasicServer(HttpBase):
    def _make_server(self):
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), TydexHttpHandler)
        httpd.tydex_server = build_server(backend=self.backend, model="mock")
        return httpd

    def test_health(self):
        status, body = self.get("/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

    def test_evaluate(self):
        status, body = self.post("/evaluate", {"state": {}, "questions": [{"id": "q", "type": "choice", "options": ["a", "b"]}]})
        self.assertEqual(status, 200)
        self.assertEqual(body["results"][0]["id"], "q")
        self.assertAlmostEqual(sum(body["results"][0]["probabilities"].values()), 1.0)

    def test_invalid_json(self):
        status, _ = self.post("/evaluate", "{{{")
        self.assertEqual(status, 400)

    def test_unknown_question_type(self):
        status, body = self.post("/evaluate", {"state": {}, "questions": [{"id": "q", "type": "bogus"}]})
        self.assertEqual(status, 200)
        self.assertEqual(len(body["errors"]), 1)

    def test_missing_questions_list(self):
        status, body = self.post("/evaluate", {"state": {}})
        self.assertEqual(status, 200)
        self.assertIn("errors", body)

    def test_label_without_calibration(self):
        status, _ = self.post("/label", {"log_id": "x", "label": "y"})
        self.assertEqual(status, 404)

    def test_calibration_without_system(self):
        status, _ = self.get("/calibration")
        self.assertEqual(status, 404)


class TestAutoLoopServer(HttpBase):
    def _make_server(self):
        self.cal_path = os.path.join(self.dir, "cal.json")
        self.auto = AutoCalibrator(
            Recorder(os.path.join(self.dir, "fb.jsonl")),
            refit_every=2,
            config_path=self.cal_path,
            min_samples=2,
        )
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), TydexHttpHandler)
        httpd.tydex_server = build_server(backend=self.backend, model="mock", auto=self.auto)
        return httpd

    def test_label_and_refit_loop(self):
        payload = {"state": {"t": 1}, "questions": [{"id": "q1", "type": "choice", "options": ["a", "b"]}]}
        status, body = self.post("/evaluate", payload)
        log_id_1 = body["results"][0]["log_id"]
        self.assertTrue(log_id_1)

        status, body = self.post("/label", {"log_id": log_id_1, "label": "a"})
        self.assertEqual(status, 200)
        self.assertEqual(body["pending"], 1)
        self.assertFalse(body["refitted"])

        payload["questions"][0]["id"] = "q2"
        status, body = self.post("/evaluate", payload)
        log_id_2 = body["results"][0]["log_id"]

        status, body = self.post("/label", {"log_id": log_id_2, "label": "b"})
        self.assertEqual(status, 200)
        self.assertTrue(body["refitted"])
        self.assertEqual(body["pending"], 0)

        status, body = self.get("/calibration")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(body["history"]), 1)
        self.assertIn("choice", body["temperatures"])

    def test_unknown_log_id(self):
        status, _ = self.post("/label", {"log_id": "bogus", "label": "a"})
        self.assertEqual(status, 404)

    def test_manual_refit(self):
        payload = {"state": {}, "questions": [{"id": "q", "type": "choice", "options": ["a", "b"]}]}
        status, body = self.post("/evaluate", payload)
        log_id = body["results"][0]["log_id"]
        self.post("/label", {"log_id": log_id, "label": "a"})

        status, body = self.post("/refit")
        self.assertEqual(status, 200)
        self.assertTrue(body["refitted"])
        self.assertEqual(body["pending"], 0)


class TestNoAutoRefit(unittest.TestCase):
    def setUp(self):
        from http.server import ThreadingHTTPServer

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), TydexHttpHandler)
        self.httpd.tydex_server = build_server(backend=MockBackend(), model="mock")
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def test_refit_without_auto_404(self):
        status, _ = HttpBase.post(self, "/refit")
        self.assertEqual(status, 404)

    def test_evaluate_without_auto_no_log_id(self):
        status, body = HttpBase.post(self, "/evaluate", {"state": {}, "questions": [{"id": "q", "type": "choice", "options": ["a", "b"]}]})
        self.assertEqual(status, 200)
        self.assertNotIn("log_id", body["results"][0])


if __name__ == "__main__":
    unittest.main()