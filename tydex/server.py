from __future__ import annotations

import argparse
import hmac
import json
import logging
import os
import time
from collections import defaultdict
from typing import Any

# ... (existing imports)
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"ts": "%(asctime)s", "level": "%(levelname)s", "msg": "%(message)s", "module": "%(module)s"}'
)
logger = logging.getLogger("tydex")

# Simple in-memory rate limiter
class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self.history = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        # Clean old timestamps
        self.history[client_id] = [ts for ts in self.history[client_id] if now - ts < 60]
        if len(self.history[client_id]) >= self.rpm:
            return False
        self.history[client_id].append(now)
        return True

limiter = RateLimiter(requests_per_minute=100)

# --- Schemas ---
# ... (rest of the file)

from .autocal import AutoCalibrator
from .backends import AnthropicCompatibleBackend, MockBackend, OllamaBackend, OpenAIBackend
from .calibrated import CalibratedTydex, CalibrationSystem
from .config import load_env
from .core import SchemaError, Tydex
from .routing import RequiresHuman, RoutedTydex

# --- Schemas ---

class Question(BaseModel):
    id: str | None = None
    type: str # choice, score, noul
    options: list[str] | None = None
    levels: list[str] | None = None
    statement: str | None = None
    question: str | None = None
    temperature: float = 1.0

class EvaluateRequest(BaseModel):
    state: Any = None
    questions: list[Question]

class LabelRequest(BaseModel):
    log_id: str
    label: str

# --- Server Logic ---

class TydexServer:
    def __init__(self, tdex: Tydex | CalibratedTydex, *, raw: Tydex | None = None, auto: AutoCalibrator | None = None, api_key: str | None = None, cors: bool = False):
        self.tdex = tdex
        self.raw = raw or tdex
        self.auto = auto
        self.api_key = api_key
        self.cors = cors

    async def evaluate(self, request: EvaluateRequest) -> dict[str, Any]:
        state = request.state
        questions = request.questions
        results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        start_time = time.time()

        for idx, q in enumerate(questions):
            try:
                res = await self._answer(state, q)
                results.append(res)
            except (SchemaError, ValueError, KeyError) as exc:
                errors.append({"id": q.id or idx, "error": str(exc)})

        duration = time.time() - start_time
        logger.info(json.dumps({
            "event": "evaluate",
            "count": len(questions),
            "errors": len(errors),
            "duration_ms": duration * 1000,
            "avg_latency_ms": (duration * 1000 / len(questions)) if questions else 0
        }))

        return {"results": results, "errors": errors}

    async def _log(self, primitive: str, state: Any, request_data: dict, result: Any) -> str | None:
        if self.auto is None:
            return None
        raw = self.raw
        temperature = float(request_data.get("temperature", 1.0))

        if raw is not self.tdex:
            # We need a way to get raw results async. Since Tydex methods are now async:
            raw_result = await self._raw_result(raw, primitive, state, request_data)
        else:
            raw_result = result

        if primitive == "choice":
            return self.auto.recorder.choice(state, request_data["options"], raw_result, question=request_data.get("question"), temperature=temperature).id
        if primitive == "score":
            return self.auto.recorder.score(state, request_data["levels"], raw_result, question=request_data.get("question"), temperature=temperature).id
        return self.auto.recorder.noul(state, request_data["statement"], raw_result, temperature=temperature).id

    async def _raw_result(self, raw: Tydex | CalibratedTydex, primitive: str, state: Any, request_data: dict) -> Any:
        if primitive == "choice":
            return await raw.choice(state, request_data["options"], question=request_data.get("question", "Choose the best option."), temperature=float(request_data.get("temperature", 1.0)))
        if primitive == "score":
            return await raw.score(state, request_data["levels"], question=request_data.get("question", "Rate the state against the levels."), temperature=float(request_data.get("temperature", 1.0)))
        return await raw.noul(state, request_data["statement"], temperature=float(request_data.get("temperature", 1.0)))

    async def _answer(self, state: Any, q: Question) -> dict[str, Any]:
        qid = q.id
        qtype = q.type
        temp = q.temperature

        if qtype == "choice":
            options = q.options
            if not isinstance(options, list) or len(options) < 2:
                raise ValueError("choice requires 'options' as a list of >= 2 items")
            res = await self.tdex.choice(state, options, question=q.question or "Choose the best option.", temperature=temp)
            log_id = await self._log("choice", state, {"options": options, "question": q.question}, res)
            body = {"id": qid, "type": "choice", "choice": res.choice, "probabilities": res.probabilities, "confidence": res.confidence}
            if log_id:
                body["log_id"] = log_id
            return body
        if qtype == "score":
            levels = q.levels
            if not isinstance(levels, list) or len(levels) < 2:
                raise ValueError("score requires 'levels' as a list of >= 2 items")
            res = await self.tdex.score(state, levels, question=q.question or "Rate the state against the levels.", temperature=temp)
            log_id = await self._log("score", state, {"levels": levels, "question": q.question}, res)
            body = {"id": qid, "type": "score", "score": res.score, "probabilities": res.probabilities, "confidence": res.confidence}
            if log_id:
                body["log_id"] = log_id
            return body
        if qtype == "noul":
            statement = q.statement
            if not isinstance(statement, str) or not statement:
                raise ValueError("noul requires a non-empty 'statement'")
            res = await self.tdex.noul(state, statement, temperature=temp)
            log_id = await self._log("noul", state, {"statement": statement}, res)
            body = {"id": qid, "type": "noul", "probability": res.probability, "bool_value": res.bool_value, "confidence": res.confidence}
            if log_id:
                body["log_id"] = log_id
            return body
        raise ValueError(f"unknown question type: {qtype!r}")

class RoutedTydexServer:
    def __init__(self, routed: RoutedTydex, *, api_key: str | None = None, cors: bool = False):
        self.routed = routed
        self.api_key = api_key
        self.cors = cors

    async def evaluate(self, request: EvaluateRequest) -> dict[str, Any]:
        state = request.state
        questions = request.questions
        results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        for idx, q in enumerate(questions):
            try:
                results.append(await self._answer(state, q))
            except (SchemaError, ValueError, KeyError) as exc:
                errors.append({"id": q.id or idx, "error": str(exc)})
            except RequiresHuman as exc:
                errors.append({"id": q.id or idx, "requires_human": True, "escalations": exc.escalations, "tier": exc.tier, "error": str(exc)})
        return {"results": results, "errors": errors}

    async def _answer(self, state: Any, q: Question) -> dict[str, Any]:
        qid = q.id
        qtype = q.type
        # min_confidence is not in Question schema but might be passed in raw request
        # To keep it clean, we could add it to Question or handle via request.json()
        # For now, we'll assume 0.0 or pass it if we update the schema
        min_conf = 0.0

        if qtype == "choice":
            options = q.options
            if not isinstance(options, list) or len(options) < 2:
                raise ValueError("choice requires 'options' as a list of >= 2 items")
            rr = await self.routed.choice(state, options, question=q.question or "Choose the best option.", min_confidence=min_conf)
            res = rr.result
            return {
                "id": qid,
                "type": "choice",
                "choice": res.choice,
                "probabilities": res.probabilities,
                "confidence": rr.confidence,
                "tier": rr.tier,
                "escalations": rr.escalations,
                "total_cost": rr.total_cost,
            }
        if qtype == "score":
            levels = q.levels
            if not isinstance(levels, list) or len(levels) < 2:
                raise ValueError("score requires 'levels' as a list of >= 2 items")
            rr = await self.routed.score(state, levels, question=q.question or "Rate the state against the levels.", min_confidence=min_conf)
            res = rr.result
            return {
                "id": qid,
                "type": "score",
                "score": res.score,
                "probabilities": res.probabilities,
                "confidence": rr.confidence,
                "tier": rr.tier,
                "escalations": rr.escalations,
                "total_cost": rr.total_cost,
            }
        if qtype == "noul":
            statement = q.statement
            if not isinstance(statement, str) or not statement:
                raise ValueError("noul requires a non-empty 'statement'")
            rr = await self.routed.noul(state, statement, min_confidence=min_conf)
            res = rr.result
            return {
                "id": qid,
                "type": "noul",
                "probability": res.probability,
                "bool_value": res.bool_value,
                "confidence": rr.confidence,
                "tier": rr.tier,
                "escalations": rr.escalations,
                "total_cost": rr.total_cost,
            }
        raise ValueError(f"unknown question type: {qtype!r}")

# --- FastAPI Application ---

def build_app(
    backend=None,
    model: str = "default",
    routed: RoutedTydex | None = None,
    calibration: CalibrationSystem | None = None,
    auto: AutoCalibrator | None = None,
    api_key: str | None = None,
    cors: bool = False,
) -> FastAPI:
    app = FastAPI(title="Tydex")

    if cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

    if routed is not None:
        server = RoutedTydexServer(routed, api_key=api_key, cors=cors)
    else:
        if backend is None:
            if os.environ.get("OPENAI_API_KEY"):
                backend = OpenAIBackend(model=os.environ.get("OPENAI_MODEL") or "gpt-4o-mini", api_key=os.environ.get("OPENAI_API_KEY"))
            elif os.environ.get("ANTHROPIC_API_KEY"):
                backend = AnthropicCompatibleBackend(model=os.environ.get("ANTHROPIC_MODEL") or "claude-3-5-haiku-latest", api_key=os.environ.get("ANTHROPIC_API_KEY"))
            elif os.environ.get("OLLAMA_HOST"):
                backend = OllamaBackend(model=os.environ.get("OLLAMA_MODEL") or "llama3.1:8b")
            else:
                backend = MockBackend()

        if model == "default":
            model = getattr(backend, "model", "default")

        raw = Tydex(backend, model=model)
        tdex = raw
        if calibration is not None:
            tdex = calibration.apply_to(raw)
        server = TydexServer(tdex, raw=raw if auto is not None else None, auto=auto, api_key=api_key, cors=cors)

    async def verify_auth(request: Request, authorization: str = Header(None), x_api_key: str = Header(None)):
        # Rate Limiting
        client_ip = request.client.host if request.client else "unknown"
        if not limiter.is_allowed(client_ip):
            raise HTTPException(status_code=429, detail="Too many requests. Rate limit exceeded.")

        if not server.api_key:
            return
        supplied = ""
        if authorization and authorization.startswith("Bearer "):
            supplied = authorization[len("Bearer "):].strip()
        elif x_api_key:
            supplied = x_api_key

        if not supplied or not hmac.compare_digest(supplied, server.api_key):
            raise HTTPException(status_code=401, detail="unauthorized")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/calibration", dependencies=[Depends(verify_auth)])
    async def get_calibration():
        if not getattr(server, "auto", None):
            raise HTTPException(status_code=404, detail="no calibration system attached")
        return server.auto.status()

    @app.get("/suggest", dependencies=[Depends(verify_auth)])
    async def suggest(x_primitive: str = Header("choice"), x_limit: int = Header(10)):
        if not getattr(server, "auto", None):
            raise HTTPException(status_code=404, detail="no calibration system attached")
        ids = server.auto.recorder.suggest_labels(x_primitive, x_limit)
        return {"suggested_ids": ids}

    @app.post("/evaluate", dependencies=[Depends(verify_auth)])
    async def evaluate(req: EvaluateRequest):
        return await server.evaluate(req)

    @app.post("/label", dependencies=[Depends(verify_auth)])
    async def label(req: LabelRequest):
        if not getattr(server, "auto", None):
            raise HTTPException(status_code=404, detail="no calibration system attached")
        try:
            server.auto.label(req.log_id, req.label)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"unknown log_id {req.log_id}") from None
        refitted = server.auto.maybe_refit()
        return {"ok": True, "refitted": refitted, **server.auto.status()}

    @app.post("/refit", dependencies=[Depends(verify_auth)])
    async def refit():
        if not getattr(server, "auto", None):
            raise HTTPException(status_code=404, detail="no calibration system attached")
        refitted = server.auto.refit()
        return {"ok": True, "refitted": refitted, **server.auto.status()}

    return app

def run(
    host: str = "127.0.0.1",
    port: int = 8000,
    backend=None,
    model: str = "default",
    routed: RoutedTydex | None = None,
    calibration: CalibrationSystem | None = None,
    auto: AutoCalibrator | None = None,
    api_key: str | None = None,
    cors: bool = False,
) -> None:
    import uvicorn
    app = build_app(backend=backend, model=model, routed=routed, calibration=calibration, auto=auto, api_key=api_key, cors=cors)
    print(f"Tydex server on http://{host}:{port} (FastAPI)")
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Tydex evaluation HTTP server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--backend", choices=["openai", "anthropic", "ollama", "mock"], default="auto")
    parser.add_argument("--model", default="default")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--cors", action="store_true")
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

    run(
        host=args.host,
        port=args.port,
        backend=backend,
        model=args.model,
        api_key=args.api_key or os.environ.get("TYDEX_API_KEY"),
        cors=args.cors,
    )
