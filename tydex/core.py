from __future__ import annotations

import json
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


def _gather(backend: Backend, system: str, user: str, model: str, *, json_mode: bool, max_tokens: int) -> tuple[str, dict[str, float] | None]:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    resp = backend.complete(
        messages=messages,
        max_tokens=max_tokens,
        logprobs=not json_mode,
        top_logprobs=20 if not json_mode else 0,
        json_mode=json_mode,
    )
    return resp.text.strip(), resp.logprobs


def _logprob_choice(backend: Backend, model: str, system: str, user: str, labels: list[str], temperature: float = 1.0) -> tuple[str, dict[str, float]]:
    text, lp = _gather(backend, system, user, model, json_mode=False, max_tokens=1)
    if lp is None:
        raise SchemaError("backend did not return logprobs")
    index_tokens = [str(i) for i in range(len(labels))]
    picked = {}
    for token, prob in lp.items():
        key = token.strip().split()[-1] if token.strip() else token
        if key in index_tokens:
            picked[key] = picked.get(key, 0.0) + prob
    if not picked:
        raise SchemaError(f"no candidate token matched option indices; model said: {text!r}")
    picked = _normalize(picked)
    if temperature != 1.0:
        picked = _rescale(picked, temperature)
    chosen_key = max(picked, key=picked.get)
    return labels[int(chosen_key)], picked


def _logprob_noul(backend: Backend, model: str, system: str, user: str, temperature: float = 1.0) -> tuple[float, dict[str, float]]:
    text, lp = _gather(backend, system, user, model, json_mode=False, max_tokens=1)
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
    def __init__(self, backend: Backend, model: str = "default"):
        self.backend = backend
        self.model = model

    def choice(
        self,
        state: object,
        options: Sequence[str],
        *,
        question: str = "Choose the best option.",
        mode: Mode = "auto",
        temperature: float = 1.0,
    ) -> ChoiceResult:
        options = list(options)
        if len(options) < 2:
            raise ValueError("choice requires at least 2 options")
        if len(options) > 20:
            raise ValueError("choice supports at most 20 options")
        use_logprobs = _resolve_mode(self.backend, mode, allowed={"logprobs", "self"}) == "logprobs"
        enumerated = "\n".join(f"{i}. {opt}" for i, opt in enumerate(options))
        if use_logprobs:
            system = "You are a decision engine. Given state and question, output ONLY the index (single digit) of the correct option. No explanation."
            chosen, index_probs = _logprob_choice(
                self.backend,
                self.model,
                system,
                f"STATE:\n{_as_text(state)}\n\nQUESTION:\n{question}\n\nOPTIONS:\n{enumerated}",
                options,
                temperature=temperature,
            )
            probs = {opt: index_probs.get(str(i), 0.0) for i, opt in enumerate(options)}
            return ChoiceResult(choice=chosen, probabilities=probs, confidence=probs[chosen], source="logprobs")
        prompt = f"Return JSON with 'choice' set to EXACTLY one of {options} and 'probability' a self-estimated confidence in [0,1]."
        user = f"STATE:\n{_as_text(state)}\n\nQUESTION:\n{question}\n\nOPTIONS:\n{enumerated}\n\n{prompt}"
        text, _ = _gather(self.backend, "You are a decision engine. Return valid JSON only.", user, self.model, json_mode=True, max_tokens=200)
        return self._self_choice_result(text, options)

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

    def score(
        self,
        state: object,
        levels: Sequence[str],
        *,
        question: str = "Rate the state against the levels.",
        mode: Mode = "auto",
        temperature: float = 1.0,
    ) -> ScoreResult:
        result = self.choice(state, levels, question=question, mode=mode, temperature=temperature)
        return ScoreResult(score=result.choice, probabilities=result.probabilities, confidence=result.confidence, source=result.source)

    def noul(
        self,
        state: object,
        statement: str,
        *,
        mode: Mode = "auto",
        temperature: float = 1.0,
    ) -> NoulResult:
        use_logprobs = _resolve_mode(self.backend, mode, allowed={"logprobs", "self"}) == "logprobs"
        if use_logprobs:
            system = "You are a decision engine. Answer only with Yes or No. No explanation."
            probability, _ = _logprob_noul(self.backend, self.model, system, f"STATE:\n{_as_text(state)}\n\nSTATEMENT (is it TRUE?):\n{statement}", temperature=temperature)
            return NoulResult(probability=probability, confidence=max(probability, 1.0 - probability), source="logprobs")
        text, _ = _gather(
            self.backend,
            "You are a decision engine. Return valid JSON only.",
            f"STATE:\n{_as_text(state)}\n\nSTATEMENT (is it TRUE?):\n{statement}\n\nReturn JSON: {{\"probability\": <0.0..1.0>}}",
            self.model,
            json_mode=True,
            max_tokens=100,
        )
        try:
            data = _parse_json(text)
        except json.JSONDecodeError as exc:
            raise SchemaError(f"invalid JSON from model: {text!r}") from exc
        probability = float(data.get("probability", 0.5))
        probability = min(1.0, max(0.0, probability))
        return NoulResult(probability=probability, confidence=max(probability, 1.0 - probability), source="self")