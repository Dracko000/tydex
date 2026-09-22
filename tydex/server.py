from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .autocal import AutoCalibrator
from .backends import AnthropicCompatibleBackend, MockBackend, OllamaBackend, OpenAIBackend
from .calibrated import CalibratedTydex, CalibrationSystem
from .config import load_env
from .core import SchemaError, Tydex
from .routing import RequiresHuman, RoutedTydex


class TydexHttpHandler(BaseHTTPRequestHandler):
    server_version = "TydexServer/0.1"

    def do_GET(self) -> None:
        path = self.path.split("?")[0].rstrip("/")
        if path == "/health":
            self._json(200, {"status": "ok"})
            return
        if path == "/calibration":
            auto = self.server.tydex_server.auto
            if auto is None:
                self._json(404, {"error": "no calibration system attached"})
                return
            self._json(200, auto.status())
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        path = self.path.split("?")[0].rstrip("/")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(400, {"error": "invalid Content-Length"})
            return
        if length < 0 or length > 64 * 1024 * 1024:
            self._json(400, {"error": "Content-Length out of range"})
            return
        try:
            raw = self.rfile.read(length) if length else b""
        except (ConnectionError, OSError):
            self._json(500, {"error": "read failed"})
            return
        try:
            payload = json.loads(raw.decode() or "{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid JSON body"})
            return
        if not isinstance(payload, dict):
            self._json(400, {"error": "body must be a JSON object"})
            return
        if path == "/evaluate":
            self._json(200, self.server.tydex_server.evaluate(payload))
            return
        if path == "/label":
            auto = self.server.tydex_server.auto
            if auto is None:
                self._json(404, {"error": "no calibration system attached"})
                return
            entry_id = payload.get("log_id")
            label = payload.get("label")
            try:
                auto.label(str(entry_id), str(label))
            except KeyError:
                self._json(404, {"error": f"unknown log_id {entry_id}"})
                return
            refitted = auto.maybe_refit()
            self._json(200, {"ok": True, "refitted": refitted, **auto.status()})
            return
        if path == "/refit":
            auto = self.server.tydex_server.auto
            if auto is None:
                self._json(404, {"error": "no calibration system attached"})
                return
            refitted = auto.refit()
            self._json(200, {"ok": True, "refitted": refitted, **auto.status()})
            return
        self._json(404, {"error": "not found"})

    def _json(self, status: int, body: dict[str, Any]) -> None:
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[tydexsrv] {self.address_string()} {fmt % args}")


class TydexServer:
    def __init__(self, tdex: Tydex | CalibratedTydex, *, raw: Tydex | None = None, auto: AutoCalibrator | None = None):
        self.tdex = tdex
        self.raw = raw or tdex
        self.auto = auto

    def evaluate(self, request: dict[str, Any]) -> dict[str, Any]:
        state = request.get("state")
        questions = request.get("questions")
        if not isinstance(questions, list):
            return {"results": [], "errors": [{"error": "'questions' must be a list"}]}
        results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        for idx, question in enumerate(questions):
            if not isinstance(question, dict):
                errors.append({"id": idx, "error": "question must be an object"})
                continue
            try:
                results.append(self._answer(state, question))
            except (SchemaError, ValueError, KeyError) as exc:
                errors.append({"id": question.get("id", idx), "error": str(exc)})
        return {"results": results, "errors": errors}

    def _log(self, primitive: str, state: Any, request: dict, result: Any) -> str | None:
        if self.auto is None:
            return None
        raw = self.raw
        temperature = float(request.get("temperature", 1.0))
        if raw is not self.tdex:
            raw_result = self._raw_result(raw, primitive, state, request)
        else:
            raw_result = result
        if primitive == "choice":
            return self.auto.recorder.choice(state, request["options"], raw_result, question=request.get("question"), temperature=temperature).id
        if primitive == "score":
            return self.auto.recorder.score(state, request["levels"], raw_result, question=request.get("question"), temperature=temperature).id
        return self.auto.recorder.noul(state, request["statement"], raw_result, temperature=temperature).id

    def _raw_result(self, raw: Tydex, primitive: str, state: Any, request: dict) -> Any:
        if primitive == "choice":
            return raw.choice(state, request["options"], question=request.get("question", "Choose the best option."), temperature=float(request.get("temperature", 1.0)))
        if primitive == "score":
            return raw.score(state, request["levels"], question=request.get("question", "Rate the state against the levels."), temperature=float(request.get("temperature", 1.0)))
        return raw.noul(state, request["statement"], temperature=float(request.get("temperature", 1.0)))

    def _answer(self, state: Any, question: dict[str, Any]) -> dict[str, Any]:
        qid = question.get("id")
        qtype = question.get("type")
        temperature = float(question.get("temperature", 1.0))

        if qtype == "choice":
            options = question.get("options")
            if not isinstance(options, list) or len(options) < 2:
                raise ValueError("choice requires 'options' as a list of >= 2 items")
            result = self.tdex.choice(
                state,
                options,
                question=question.get("question", "Choose the best option."),
                temperature=temperature,
            )
            log_id = self._log("choice", state, {"options": options, "question": question.get("question")}, result)
            body = {"id": qid, "type": "choice", "choice": result.choice, "probabilities": result.probabilities, "confidence": result.confidence}
            if log_id:
                body["log_id"] = log_id
            return body
        if qtype == "score":
            levels = question.get("levels")
            if not isinstance(levels, list) or len(levels) < 2:
                raise ValueError("score requires 'levels' as a list of >= 2 items")
            result = self.tdex.score(
                state,
                levels,
                question=question.get("question", "Rate the state against the levels."),
                temperature=temperature,
            )
            log_id = self._log("score", state, {"levels": levels, "question": question.get("question")}, result)
            body = {"id": qid, "type": "score", "score": result.score, "probabilities": result.probabilities, "confidence": result.confidence}
            if log_id:
                body["log_id"] = log_id
            return body
        if qtype == "noul":
            statement = question.get("statement")
            if not isinstance(statement, str) or not statement:
                raise ValueError("noul requires a non-empty 'statement'")
            result = self.tdex.noul(state, statement, temperature=temperature)
            log_id = self._log("noul", state, {"statement": statement}, result)
            body = {"id": qid, "type": "noul", "probability": result.probability, "bool_value": result.bool_value, "confidence": result.confidence}
            if log_id:
                body["log_id"] = log_id
            return body
        raise ValueError(f"unknown question type: {qtype!r} (expected choice|score|noul)")


class RoutedTydexServer:
    def __init__(self, routed: RoutedTydex):
        self.routed = routed

    def evaluate(self, request: dict[str, Any]) -> dict[str, Any]:
        state = request.get("state")
        questions = request.get("questions")
        if not isinstance(questions, list):
            return {"results": [], "errors": [{"error": "'questions' must be a list"}]}
        results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        for idx, question in enumerate(questions):
            if not isinstance(question, dict):
                errors.append({"id": idx, "error": "question must be an object"})
                continue
            try:
                results.append(self._answer(state, question))
            except (SchemaError, ValueError, KeyError) as exc:
                errors.append({"id": question.get("id", idx), "error": str(exc)})
            except RequiresHuman as exc:
                errors.append({"id": question.get("id", idx), "requires_human": True, "escalations": exc.escalations, "tier": exc.tier, "error": str(exc)})
        return {"results": results, "errors": errors}

    def _answer(self, state: Any, question: dict[str, Any]) -> dict[str, Any]:
        qid = question.get("id")
        qtype = question.get("type")
        min_confidence = question.get("min_confidence")
        if min_confidence is not None:
            min_confidence = float(min_confidence)
        if qtype == "choice":
            options = question.get("options")
            if not isinstance(options, list) or len(options) < 2:
                raise ValueError("choice requires 'options' as a list of >= 2 items")
            rr = self.routed.choice(state, options, question=question.get("question", "Choose the best option."), min_confidence=min_confidence)
            return {
                "id": qid,
                "type": "choice",
                "choice": rr.result.choice,
                "probabilities": rr.result.probabilities,
                "confidence": rr.confidence,
                "tier": rr.tier,
                "escalations": rr.escalations,
                "total_cost": rr.total_cost,
            }
        if qtype == "score":
            levels = question.get("levels")
            if not isinstance(levels, list) or len(levels) < 2:
                raise ValueError("score requires 'levels' as a list of >= 2 items")
            rr = self.routed.score(state, levels, question=question.get("question", "Rate the state against the levels."), min_confidence=min_confidence)
            return {
                "id": qid,
                "type": "score",
                "score": rr.result.score,
                "probabilities": rr.result.probabilities,
                "confidence": rr.confidence,
                "tier": rr.tier,
                "escalations": rr.escalations,
                "total_cost": rr.total_cost,
            }
        if qtype == "noul":
            statement = question.get("statement")
            if not isinstance(statement, str) or not statement:
                raise ValueError("noul requires a non-empty 'statement'")
            rr = self.routed.noul(state, statement, min_confidence=min_confidence)
            return {
                "id": qid,
                "type": "noul",
                "probability": rr.result.probability,
                "bool_value": rr.result.bool_value,
                "confidence": rr.confidence,
                "tier": rr.tier,
                "escalations": rr.escalations,
                "total_cost": rr.total_cost,
            }
        raise ValueError(f"unknown question type: {qtype!r} (expected choice|score|noul)")


def _default_backend() -> OpenAIBackend | OllamaBackend | MockBackend | AnthropicCompatibleBackend:
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAIBackend(model=os.environ.get("OPENAI_MODEL") or "gpt-4o-mini", api_key=os.environ.get("OPENAI_API_KEY"))
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicCompatibleBackend(model=os.environ.get("ANTHROPIC_MODEL") or "claude-3-5-haiku-latest", api_key=os.environ.get("ANTHROPIC_API_KEY"))
    if os.environ.get("OLLAMA_HOST"):
        return OllamaBackend(model=os.environ.get("OLLAMA_MODEL") or "llama3.1:8b")
    return MockBackend()


def build_server(
    backend=None,
    model: str = "default",
    routed: RoutedTydex | None = None,
    calibration: CalibrationSystem | None = None,
    auto: AutoCalibrator | None = None,
) -> TydexServer | RoutedTydexServer:
    if routed is not None:
        return RoutedTydexServer(routed)
    backend = backend or _default_backend()
    if model == "default":
        model = getattr(backend, "model", "default")
    raw = Tydex(backend, model=model)
    tdex: Tydex | CalibratedTydex = raw
    if calibration is not None:
        tdex = calibration.apply_to(raw)
    return TydexServer(tdex, raw=raw if auto is not None else None, auto=auto)


def run(
    host: str = "127.0.0.1",
    port: int = 8000,
    backend=None,
    model: str = "default",
    routed: RoutedTydex | None = None,
    calibration: CalibrationSystem | None = None,
    auto: AutoCalibrator | None = None,
) -> None:
    tydex_server = build_server(backend=backend, model=model, routed=routed, calibration=calibration, auto=auto)
    httpd = ThreadingHTTPServer((host, port), TydexHttpHandler)
    httpd.tydex_server = tydex_server
    print(f"Tydex server on http://{host}:{port}  (POST /evaluate)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
        httpd.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Tydex evaluation HTTP server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--backend", choices=["openai", "anthropic", "ollama", "mock"], default="auto")
    parser.add_argument("--model", default="default")
    args = parser.parse_args()
    load_env()
    backend = None
    if args.backend == "openai":
        backend = OpenAIBackend(model=args.model if args.model != "default" else "gpt-4o-mini", api_key=os.environ.get("OPENAI_API_KEY"))
    elif args.backend == "anthropic":
        backend = AnthropicCompatibleBackend(model=args.model if args.model != "default" else "claude-3-5-haiku-latest", api_key=os.environ.get("ANTHROPIC_API_KEY"))
    elif args.backend == "ollama":
        backend = OllamaBackend(model=args.model if args.model != "default" else os.environ.get("OLLAMA_MODEL") or "llama3.1:8b")
    elif args.backend == "mock":
        backend = MockBackend()
    run(host=args.host, port=args.port, backend=backend, model=args.model)