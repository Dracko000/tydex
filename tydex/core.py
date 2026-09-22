from __future__ import annotations

import json
import asyncio
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from .backends import Backend

Mode = Literal["auto", "logprobs", "self"]


class SchemaError(ValueError):
    pass


def _as_text(state: object) -> str:
    if isinstance(state, str):
        return state
    return json.dumps(state, ensure_ascii=False, indent=2)


def _parse_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].lstrip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def _normalize(probs: dict[str, float]) -> dict[str, float]:
    total = sum(probs.values())
    if total <= 0:
        raise SchemaError("no valid probability candidates")
    return {key: value / total for key, value in probs.items()}


def _rescale(probs: dict[str, float], temperature: float) -> dict[str, float]:
    if temperature == 1.0:
        return probs
    if temperature <= 0:
        raise ValueError("temperature must be > 0")
    exponent = 1.0 / temperature
    powered = {key: value**exponent for key, value in probs.items()}
    return _normalize(powered)


@dataclass
class ChoiceResult:
    choice: str
    probabilities: dict[str, float]
    confidence: float
    source: str


@dataclass
class ScoreResult:
    score: str
    probabilities: dict[str, float]
    confidence: float
    source: str


@dataclass
class NoulResult:
    probability: float
    confidence: float
    source: str

    @property
    def bool_value(self) -> bool:
        return self.probability >= 0.5


def _resolve_mode(backend: Backend, mode: Mode, *, allowed: set[str]) -> str:
    if mode == "auto":
        return "logprobs" if backend.supports_logprobs else "self"
    if mode not in allowed:
        raise ValueError(f"unsupported mode: {mode}")
    return mode


async def _gather(backend: Backend, system: str, user: str, model: str, *, json_mode: bool, max_tokens: int) -> tuple[str, dict[str, float] | None]:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    resp = await backend.complete(
        messages=messages,
        max_tokens=max_tokens,
        logprobs=not json_mode,
        top_logprobs=20 if not json_mode else 0,
        json_mode=json_mode,
    )
    return resp.text.strip(), resp.logprobs


async def _logprob_choice(backend: Backend, model: str, system: str, user: str, labels: list[str], temperature: float = 1.0) -> tuple[str, dict[str, float]]:
    text, lp = await _gather(backend, system, user, model, json_mode=False, max_tokens=1)
    if lp is None:
        raise SchemaError("backend did not return logprobs")
    index_tokens = [str(i) for i in range(len(labels))]
    picked: dict[str, float] = {}
    for token, prob in lp.items():
        key = token.strip().split()[-1] if token.strip() else token
        if key in index_tokens:
            picked[key] = picked.get(key, 0.0) + prob
    if not picked:
        raise SchemaError(f"no candidate token matched option indices; model said: {text!r}")
    picked = _normalize(picked)
    if temperature != 1.0:
        picked = _rescale(picked, temperature)
    chosen_key = max(picked, key=lambda k: picked[k])
    return labels[int(chosen_key)], picked


async def _logprob_noul(backend: Backend, model: str, system: str, user: str, temperature: float = 1.0) -> tuple[float, dict[str, float]]:
    text, lp = await _gather(backend, system, user, model, json_mode=False, max_tokens=1)
    if lp is None:
        raise SchemaError("backend did not return logprobs")
    probs = {"yes": lp.get("Yes", 0.0), "no": lp.get("No", 0.0)}
    if probs["yes"] + probs["no"] <= 0:
        raise SchemaError(f"no Yes/No candidate token found; model said: {text!r}")
    probability = probs["yes"] / (probs["yes"] + probs["no"])
    if temperature != 1.0:
        rescaled = _rescale(probs, temperature)
        probability = rescaled["yes"] / (rescaled["yes"] + rescaled["no"])
    return probability, probs


class Tydex:
    def __init__(self, backend: Backend, model: str = "default", cache_ttl: int = 3600):
        self.backend = backend
        self.model = model
        self.cache_ttl = cache_ttl
        self._cache: dict[tuple, tuple[float, Any]] = {}

    def _get_cache_key(self, method: str, *args, **kwargs) -> tuple:
        # Simple cache key based on arguments
        return (method, args, frozenset(kwargs.items()))

    async def _with_cache(self, method: str, coro, *args, **kwargs):
        key = self._get_cache_key(method, *args, **kwargs)
        if key in self._cache:
            ts, result = self._cache[key]
            if time.time() - ts < self.cache_ttl:
                return result

        result = await coro
        self._cache[key] = (time.time(), result)
        return result

    async def choice(
        self,
        state: object,
        options: Sequence[str],
        *,
        question: str = "Choose the best option.",
        mode: Mode = "auto",
        temperature: float = 1.0,
        reasoning: bool = False,
    ) -> ChoiceResult:
        options = list(options)
        if len(options) < 2:
            raise ValueError("choice requires at least 2 options")
        if len(options) > 20:
            raise ValueError("choice supports at most 20 options")

        async def _do_choice():
            use_logprobs = _resolve_mode(self.backend, mode, allowed={"logprobs", "self"}) == "logprobs"

            if use_logprobs:
                try:
                    enumerated = "\n".join(f"{i}. {opt}" for i, opt in enumerate(options))
                    system = "You are a decision engine. Given state and question, output ONLY the index (single digit) of the correct option. No explanation."
                    if reasoning:
                        use_logprobs = False
                    else:
                        chosen, index_probs = await _logprob_choice(
                            self.backend,
                            self.model,
                            system,
                            f"STATE:\n{_as_text(state)}\n\nQUESTION:\n{question}\n\nOPTIONS:\n{enumerated}",
                            options,
                            temperature=temperature,
                        )
                        probs = {opt: index_probs.get(str(i), 0.0) for i, opt in enumerate(options)}
                        return ChoiceResult(choice=chosen, probabilities=probs, confidence=probs[chosen], source="logprobs")
                except (SchemaError, RuntimeError):
                    use_logprobs = False

            enumerated = "\n".join(f"{i}. {opt}" for i, opt in enumerate(options))
            prompt = f"Return JSON with 'choice' set to EXACTLY one of {options} and 'probability' a self-estimated confidence in [0,1]."
            if reasoning:
                prompt = (
                    "First, provide a detailed 'reasoning' field explaining your thought process and analysis of the state. "
                    f"Then, return JSON with 'choice' set to EXACTLY one of {options} and 'probability' a self-estimated confidence in [0,1].\n"
                    "JSON format: {\"reasoning\": \"...\", \"choice\": \"...\", \"probability\": 0.X}"
                )

            user = f"STATE:\n{_as_text(state)}\n\nQUESTION:\n{question}\n\nOPTIONS:\n{enumerated}\n\n{prompt}"
            text, _ = await _gather(self.backend, "You are a decision engine. Return valid JSON only.", user, self.model, json_mode=True, max_tokens=500 if reasoning else 200)
            return self._self_choice_result(text, options)

        return await self._with_cache("choice", _do_choice(), state, options, question=question, mode=mode, temperature=temperature, reasoning=reasoning)

    def _self_choice_result(self, text: str, options: list[str]) -> ChoiceResult:
        try:
            data = _parse_json(text)
        except json.JSONDecodeError as exc:
            raise SchemaError(f"invalid JSON from model: {text!r}") from exc
        raw_choice = data.get("choice")
        if raw_choice not in options:
            raise SchemaError(f"choice {raw_choice!r} outside schema (allowed: {options})")
        probability = float(data.get("probability", 0.0))
        probability = min(1.0, max(0.0, probability))
        residual = (1.0 - probability) / max(1, len(options) - 1)
        probs = {opt: residual for opt in options}
        probs[raw_choice] = probability
        return ChoiceResult(choice=raw_choice, probabilities=probs, confidence=probability, source="self")

    async def score(
        self,
        state: object,
        levels: Sequence[str],
        *,
        question: str = "Rate the state against the levels.",
        mode: Mode = "auto",
        temperature: float = 1.0,
        reasoning: bool = False,
    ) -> ScoreResult:
        result = await self.choice(state, levels, question=question, mode=mode, temperature=temperature, reasoning=reasoning)
        return ScoreResult(score=result.choice, probabilities=result.probabilities, confidence=result.confidence, source=result.source)

    async def noul(
        self,
        state: object,
        statement: str,
        *,
        mode: Mode = "auto",
        temperature: float = 1.0,
        reasoning: bool = False,
    ) -> NoulResult:
        async def _do_noul():
            use_logprobs = _resolve_mode(self.backend, mode, allowed={"logprobs", "self"}) == "logprobs"
            if use_logprobs:
                if reasoning:
                    use_logprobs = False
                else:
                    try:
                        system = "You are a decision engine. Answer only with Yes or No. No explanation."
                        probability, _ = await _logprob_noul(self.backend, self.model, system, f"STATE:\n{_as_text(state)}\n\nSTATEMENT (is it TRUE?):\n{statement}", temperature=temperature)
                        return NoulResult(probability=probability, confidence=max(probability, 1.0 - probability), source="logprobs")
                    except (SchemaError, RuntimeError):
                        use_logprobs = False

            prompt = "Return JSON: {\"probability\": <0.0..1.0>}"
            if reasoning:
                prompt = (
                    "First, provide a detailed 'reasoning' field explaining your analysis of the statement against the state. "
                    "Then, return JSON: {\"reasoning\": \"...\", \"probability\": <0.0..1.0>}"
                )

            text, _ = await _gather(
                self.backend,
                "You are a decision engine. Return valid JSON only.",
                f"STATE:\n{_as_text(state)}\n\nSTATEMENT (is it TRUE?):\n{statement}\n\n{prompt}",
                self.model,
                json_mode=True,
                max_tokens=500 if reasoning else 100,
            )
            try:
                data = _parse_json(text)
            except json.JSONDecodeError as exc:
                raise SchemaError(f"invalid JSON from model: {text!r}") from exc
            probability = float(data.get("probability", 0.5))
            probability = min(1.0, max(0.0, probability))
            return NoulResult(probability=probability, confidence=max(probability, 1.0 - probability), source="self")

        return await self._with_cache("noul", _do_noul(), state, statement, mode=mode, temperature=temperature, reasoning=reasoning)


class EnsembleTydex:
    def __init__(self, members: Sequence[Tydex], weights: Sequence[float] | None = None, tuner: Any = None):
        self.members = list(members)
        self.tuner = tuner
        if weights is None:
            self.weights = [1.0 / len(self.members)] * len(self.members)
        else:
            self.weights = list(weights)
            total = sum(self.weights)
            self.weights = [w / total for w in self.weights]

    async def _update_weights(self):
        if self.tuner:
            self.weights = self.tuner.get_weights(self.members)

    async def choice(
        self,
        state: object,
        options: Sequence[str],
        *,
        question: str = "Choose the best option.",
        temperature: float = 1.0,
    ) -> ChoiceResult:
        await self._update_weights()
        results = await asyncio.gather(
            *[m.choice(state, options, question=question, temperature=temperature) for m in self.members]
        )

        agg_probs: dict[str, float] = {opt: 0.0 for opt in options}
        for res, w in zip(results, self.weights):
            for opt, prob in res.probabilities.items():
                agg_probs[opt] += prob * w

        chosen = max(agg_probs, key=lambda k: agg_probs[k])
        return ChoiceResult(
            choice=chosen,
            probabilities=agg_probs,
            confidence=agg_probs[chosen],
            source=f"ensemble({len(self.members)})"
        )

    async def score(
        self,
        state: object,
        levels: Sequence[str],
        *,
        question: str = "Rate the state against the levels.",
        temperature: float = 1.0,
    ) -> ScoreResult:
        res = await self.choice(state, levels, question=question, temperature=temperature)
        return ScoreResult(score=res.choice, probabilities=res.probabilities, confidence=res.confidence, source=res.source)

    async def noul(
        self,
        state: object,
        statement: str,
        *,
        temperature: float = 1.0,
    ) -> NoulResult:
        await self._update_weights()
        results = await asyncio.gather(
            *[m.noul(state, statement, temperature=temperature) for m in self.members]
        )

        avg_prob = sum(r.probability * w for r, w in zip(results, self.weights))
        return NoulResult(
            probability=avg_prob,
            confidence=max(avg_prob, 1.0 - avg_prob),
            source=f"ensemble({len(self.members)})"
        )


class RefiningTydex:
    def __init__(self, tdex: Tydex, threshold: float = 0.8):
        self.tdex = tdex
        self.threshold = threshold

    async def choice(
        self,
        state: object,
        options: Sequence[str],
        *,
        question: str = "Choose the best option.",
        temperature: float = 1.0,
    ) -> ChoiceResult:
        res = await self.tdex.choice(state, options, question=question, temperature=temperature)
        if res.confidence >= self.threshold:
            return res

        ref_question = (
            f"You previously chose '{res.choice}' with {res.confidence:.2f} confidence. "
            f"Review the state and options again. Is this correct? "
            f"Provide a revised probability distribution."
        )
        refined = await self.tdex.choice(state, options, question=ref_question, temperature=temperature)

        agg_probs: dict[str, float] = {}
        for opt in options:
            agg_probs[opt] = (res.probabilities.get(opt, 0.0) + refined.probabilities.get(opt, 0.0)) / 2

        chosen = max(agg_probs, key=lambda k: agg_probs[k])
        return ChoiceResult(
            choice=chosen,
            probabilities=agg_probs,
            confidence=agg_probs[chosen],
            source=f"{res.source}+refined"
        )

    async def score(
        self,
        state: object,
        levels: Sequence[str],
        *,
        question: str = "Rate the state against the levels.",
        temperature: float = 1.0,
    ) -> ScoreResult:
        res = await self.choice(state, levels, question=question, temperature=temperature)
        return ScoreResult(score=res.choice, probabilities=res.probabilities, confidence=res.confidence, source=res.source)

    async def noul(
        self,
        state: object,
        statement: str,
        *,
        temperature: float = 1.0,
    ) -> NoulResult:
        res = await self.tdex.noul(state, statement, temperature=temperature)
        if res.confidence >= self.threshold:
            return res

        ref_statement = f"You previously estimated a probability of {res.probability:.2f} for this statement. Review the state again and provide a corrected probability."
        refined = await self.tdex.noul(state, ref_statement, temperature=temperature)

        avg_prob = (res.probability + refined.probability) / 2
        return NoulResult(
            probability=avg_prob,
            confidence=max(avg_prob, 1.0 - avg_prob),
            source=f"{res.source}+refined"
        )
