import json
import math
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from tydex import AnthropicCompatibleBackend, LocalOpenAIBackend, OpenAIBackend, OpenAICompatibleBackend, Tydex


class FakeLLMServer:
    def __init__(self, responder):
        self.records = []
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(responder, self.records))
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.port}"

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def _make_handler(responder, records):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length).decode())
            records.append(
                {
                    "path": self.path,
                    "headers": {k.lower(): v for k, v in self.headers.items()},
                    "body": body,
                }
            )
            status, payload = responder(body)
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, fmt, *args):
            pass

    return Handler


def openai_responder(body):
    if body.get("logprobs"):
        system = body["messages"][0]["content"]
        if "Yes or No" in system:
            tokens = {"Yes": -0.1, "No": -0.9}
        else:
            tokens = {"0": -0.1, "1": -0.5}
        top = [{"token": t, "logprob": lp, "bytes": None} for t, lp in tokens.items()]
        winner = max(tokens, key=tokens.get)
        content = [{"token": winner, "logprob": tokens[winner], "bytes": None, "top_logprobs": top}]
        return 200, {"choices": [{"message": {"role": "assistant", "content": winner}, "logprobs": {"content": content}}]}
    last = body["messages"][-1]["content"]
    if "STATEMENT" in last:
        return 200, {"choices": [{"message": {"role": "assistant", "content": '{"probability": 0.72}'}, "logprobs": None}]}
    return 200, {"choices": [{"message": {"role": "assistant", "content": '{"choice": "b", "probability": 0.88}'}, "logprobs": None}]}


def anthropic_responder(body):
    last = body["messages"][-1]["content"]
    text = '{"probability": 0.72}' if "STATEMENT" in last else '{"choice": "a", "probability": 0.85}'
    return 200, {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
        "model": body["model"],
        "usage": {"input_tokens": 10, "output_tokens": 8},
    }


def _softmax_lp(lps):
    vals = {k: math.exp(v) for k, v in lps.items()}
    total = sum(vals.values())
    return {k: v / total for k, v in vals.items()}


OPENAI_URL = None
ANTHROPIC_URL = None
SERVERS = []


def setUpModule():
    global OPENAI_URL, ANTHROPIC_URL
    openai = FakeLLMServer(openai_responder)
    anthropic = FakeLLMServer(anthropic_responder)
    SERVERS.extend([openai, anthropic])
    OPENAI_URL = openai.url
    ANTHROPIC_URL = anthropic.url


def tearDownModule():
    for srv in SERVERS:
        srv.close()


class TestOpenAICompatible(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.httpd = SERVERS[0]

    async def test_logprobs_choice(self):
        backend = OpenAICompatibleBackend("gpt-test", api_key="sk-123", base_url=OPENAI_URL)
        result = await Tydex(backend, model="gpt-test").choice({}, ["a", "b"])
        self.assertEqual(result.choice, "a")
        self.assertEqual(result.source, "logprobs")
        expected = _softmax_lp({"0": -0.1, "1": -0.5})["0"]
        self.assertAlmostEqual(result.probabilities["a"], expected)
        rec = self.httpd.records[-1]
        self.assertTrue(rec["path"].endswith("/chat/completions"))
        self.assertEqual(rec["headers"]["authorization"], "Bearer sk-123")
        self.assertTrue(rec["body"]["logprobs"])

    async def test_logprobs_noul(self):
        backend = OpenAICompatibleBackend("gpt-test", base_url=OPENAI_URL)
        result = await Tydex(backend, model="gpt-test").noul({}, "some claim")
        self.assertGreater(result.probability, 0.5)
        expected = math.exp(-0.1) / (math.exp(-0.1) + math.exp(-0.9))
        self.assertAlmostEqual(result.probability, expected)

    async def test_self_path_when_logprobs_off(self):
        backend = OpenAICompatibleBackend("gpt-test", base_url=OPENAI_URL, supports_logprobs=False)
        result = await Tydex(backend, model="gpt-test").choice({}, ["a", "b"])
        self.assertEqual(result.choice, "b")
        self.assertEqual(result.confidence, 0.88)
        self.assertEqual(result.source, "self")

    async def test_self_noul(self):
        backend = OpenAICompatibleBackend("gpt-test", base_url=OPENAI_URL, supports_logprobs=False)
        result = await Tydex(backend, model="gpt-test").noul({}, "STATEMENT here")
        self.assertAlmostEqual(result.probability, 0.72)

    def test_openai_backend_subclass(self):
        self.assertTrue(issubclass(OpenAIBackend, OpenAICompatibleBackend))
        backend = LocalOpenAIBackend("local", "http://localhost:8000", supports_logprobs=False)
        self.assertFalse(backend.supports_logprobs)
        self.assertEqual(backend.model, "local")


class TestAnthropicCompatible(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.httpd = SERVERS[1]

    async def test_request_shape(self):
        backend = AnthropicCompatibleBackend("claude-test", api_key="sk-ant-key", base_url=ANTHROPIC_URL)
        backend.supports_logprobs = False
        result = await Tydex(backend, model="claude-test").choice({}, ["a", "b"])
        self.assertEqual(result.choice, "a")
        self.assertEqual(result.confidence, 0.85)
        self.assertEqual(result.source, "self")
        rec = self.httpd.records[-1]
        self.assertEqual(rec["path"], "/v1/messages")
        self.assertEqual(rec["headers"]["x-api-key"], "sk-ant-key")
        self.assertEqual(rec["headers"]["anthropic-version"], "2023-06-01")
        self.assertEqual(rec["body"]["model"], "claude-test")
        self.assertIn("system", rec["body"])
        self.assertGreater(rec["body"]["max_tokens"], 0)
        self.assertNotIn("logprobs", rec["body"])
        self.assertTrue(rec["body"]["messages"][-1]["content"].startswith("STATE:"))

    async def test_system_is_split_out(self):
        backend = AnthropicCompatibleBackend("claude-test", api_key="k", base_url=ANTHROPIC_URL)
        await Tydex(backend, model="claude-test").noul({}, "STATEMENT thing")
        rec = self.httpd.records[-1]
        self.assertTrue(any(m["role"] != "system" for m in rec["body"]["messages"]))
        self.assertIn("You are a decision engine", rec["body"]["system"])

    async def test_no_api_key_header_when_missing(self):
        backend = AnthropicCompatibleBackend("claude-test", base_url=ANTHROPIC_URL)
        await Tydex(backend, model="claude-test").noul({}, "x", mode="self")
        rec = self.httpd.records[-1]
        self.assertNotIn("x-api-key", rec["headers"])

    async def test_noul_self(self):
        backend = AnthropicCompatibleBackend("claude-test", base_url=ANTHROPIC_URL)
        result = await Tydex(backend, model="claude-test").noul({}, "STATEMENT claim")
        self.assertAlmostEqual(result.probability, 0.72)


if __name__ == "__main__":
    unittest.main()