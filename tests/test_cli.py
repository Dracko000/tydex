import contextlib
import io
import json
import os
import unittest

from tydex.backends import AnthropicCompatibleBackend, MockBackend, OllamaBackend, OpenAIBackend, OpenAICompatibleBackend
from tydex.cli import CliError, _auto_provider, cmd_providers, main, resolve_backend


class AutoProviderTest(unittest.TestCase):
    def setUp(self):
        self._env = {k: os.environ.get(k) for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OLLAMA_API_KEY", "OLLAMA_HOST")}

    def tearDown(self):
        for key, value in self._env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_priority(self):
        os.environ["OPENAI_API_KEY"] = "k"
        self.assertEqual(_auto_provider(), "openai")
        os.environ.pop("OPENAI_API_KEY")
        os.environ["ANTHROPIC_API_KEY"] = "k"
        self.assertEqual(_auto_provider(), "anthropic")
        os.environ.pop("ANTHROPIC_API_KEY")
        os.environ["OLLAMA_API_KEY"] = "k"
        self.assertEqual(_auto_provider(), "openai-compatible")
        os.environ.pop("OLLAMA_API_KEY")
        os.environ["OLLAMA_HOST"] = "http://x"
        self.assertEqual(_auto_provider(), "ollama")
        os.environ.pop("OLLAMA_HOST")
        self.assertEqual(_auto_provider(), "mock")


class ResolveBackendTest(unittest.TestCase):
    def tearDown(self):
        for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OLLAMA_API_KEY", "OLLAMA_HOST"):
            os.environ.pop(key, None)

    def test_mock_and_ollama_need_no_key(self):
        self.assertIsInstance(resolve_backend("mock"), MockBackend)
        self.assertIsInstance(resolve_backend("ollama"), OllamaBackend)

    def test_openai_requires_key(self):
        with self.assertRaises(CliError):
            resolve_backend("openai")
        backend = resolve_backend("openai", api_key="k", model="gpt-x")
        self.assertIsInstance(backend, OpenAIBackend)
        self.assertEqual(backend.model, "gpt-x")

    def test_anthropic_requires_key(self):
        with self.assertRaises(CliError):
            resolve_backend("anthropic")
        backend = resolve_backend("anthropic", api_key="k")
        self.assertIsInstance(backend, AnthropicCompatibleBackend)

    def test_openai_compatible(self):
        backend = resolve_backend("openai-compatible", api_key="k", base_url="http://x/v1", model="m", supports_logprobs=False)
        self.assertIsInstance(backend, OpenAICompatibleBackend)
        self.assertFalse(backend.supports_logprobs)


class CliIntegrationTest(unittest.TestCase):
    def test_main_mock_choice_human(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = main(["ask", "--provider", "mock", "--type", "choice", "--options", "refund,replace", "--state", '{"t":"x"}'])
        self.assertEqual(rc, 0)
        self.assertIn("choice=", out.getvalue())
        self.assertIn("[logprobs]", out.getvalue())

    def test_main_mock_choice_json(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = main(["ask", "--provider", "mock", "--type", "choice", "--options", "a,b,c", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["type"], "choice")
        self.assertIn(payload["choice"], {"a", "b", "c"})
        self.assertAlmostEqual(sum(payload["probabilities"].values()), 1.0)

    def test_main_mock_noul(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = main(["ask", "--provider", "mock", "--type", "noul", "--statement", "The sky is blue"])
        self.assertEqual(rc, 0)
        self.assertIn("bool_value=", out.getvalue())

    def test_main_mock_score(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = main(["ask", "--provider", "mock", "--type", "score", "--levels", "low,med,high"])
        self.assertEqual(rc, 0)
        self.assertIn("score=", out.getvalue())

    def test_missing_required_argument(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = main(["ask", "--provider", "mock", "--type", "noul"])
        self.assertEqual(rc, 1)
        self.assertIn("error:", err.getvalue())

    def test_bad_state_json(self):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = main(["ask", "--provider", "mock", "--type", "choice", "--options", "a,b", "--state", "{bad"])
        self.assertEqual(rc, 1)
        self.assertIn("error:", err.getvalue())

    def test_providers(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = cmd_providers(type("NS", (), {})())
        self.assertEqual(rc, 0)
        for name in ("openai", "openai-compatible", "anthropic", "ollama", "mock"):
            self.assertIn(name, out.getvalue())

    def test_no_key_runtime_error(self):
        os.environ.pop("OPENAI_API_KEY", None)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = main(["ask", "--provider", "openai", "--type", "choice", "--options", "a,b"])
        self.assertEqual(rc, 1)
        self.assertIn("needs an API key", err.getvalue())


if __name__ == "__main__":
    unittest.main()