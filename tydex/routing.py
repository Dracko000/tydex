from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from .core import ChoiceResult, NoulResult, ScoreResult, Tydex

Primitive = Literal["choice", "score", "noul"]
PrimitiveResult = ChoiceResult | ScoreResult | NoulResult


@dataclass
class Tier:
    tdex: Tydex | None = None
    threshold: float | None = 1.0
    label: str | None = None
    cost: float = 1.0
    action: Literal["model", "human"] = "model"

    def __post_init__(self) -> None:
        if self.action == "model" and self.tdex is None:
            raise ValueError("model tier requires a Tydex instance")
        if self.action == "human" and self.tdex is not None:
            raise ValueError("human tier must not have a Tydex instance")
        if self.label is None:
            if self.action == "human":
                self.label = "human"
            else:
                assert self.tdex is not None
                self.label = getattr(self.tdex, "model", None) or getattr(self.tdex.backend, "model", None) or type(self.tdex.backend).__name__


class RequiresHuman(RuntimeError):
    def __init__(self, request: dict, escalations: list[str], tier: str) -> None:
        self.request = request
        self.escalations = escalations
        self.tier = tier
        super().__init__(f"human review required after tiers {escalations} -> {tier}")


@dataclass
class RoutedResult:
    result: PrimitiveResult
    escalations: list[str]
    tier: str
    total_cost: float

    @property
    def confidence(self) -> float:
        return self.result.confidence


class RoutedTydex:
    def __init__(self, tiers: Sequence[Tier], *, on_escalation: Callable[[str, float, float, float], None] | None = None):
        if not tiers:
            raise ValueError("need at least one tier")
        self.tiers = list(tiers)
        self.on_escalation = on_escalation

    async def _route(self, primitive: Primitive, request: dict, min_confidence: float | None) -> RoutedResult:
        escalations: list[str] = []
        total_cost = 0.0
        last: tuple[PrimitiveResult, str] | None = None
        for tier in self.tiers:
            if tier.action == "human":
                raise RequiresHuman(request=request, escalations=escalations, tier=tier.label or "human")
            assert tier.tdex is not None
            result = await self._call(tier.tdex, primitive, request)
            tier_label = tier.label or "model"
            total_cost += tier.cost
            last = (result, tier_label)
            threshold = min_confidence if min_confidence is not None else tier.threshold
            if threshold is None or result.confidence >= threshold:
                return RoutedResult(result=result, escalations=escalations, tier=tier_label, total_cost=total_cost)
            escalations.append(tier_label)
            if self.on_escalation:
                self.on_escalation(tier_label, result.confidence, threshold, total_cost)
        if last is not None:
            result, tier_label = last
            return RoutedResult(result=result, escalations=escalations, tier=tier_label, total_cost=total_cost)
        raise RuntimeError("no tier produced a result")

    async def _call(self, tdex: Tydex, primitive: Primitive, request: dict) -> PrimitiveResult:
        if primitive == "choice":
            return await tdex.choice(
                state=request["state"],
                options=request["options"],
                question=request.get("question", "Choose the best option."),
                temperature=request.get("temperature", 1.0),
            )
        if primitive == "score":
            return await tdex.score(
                state=request["state"],
                levels=request["levels"],
                question=request.get("question", "Rate the state against the levels."),
                temperature=request.get("temperature", 1.0),
            )
        return await tdex.noul(
            state=request["state"],
            statement=request["statement"],
            temperature=request.get("temperature", 1.0),
        )

    async def choice(self, state: object, options: Sequence[str], *, question: str = "Choose the best option.", min_confidence: float | None = None, temperature: float = 1.0) -> RoutedResult:
        return await self._route("choice", {"state": state, "options": list(options), "question": question, "temperature": temperature}, min_confidence)

    async def score(self, state: object, levels: Sequence[str], *, question: str = "Rate the state against the levels.", min_confidence: float | None = None, temperature: float = 1.0) -> RoutedResult:
        return await self._route("score", {"state": state, "levels": list(levels), "question": question, "temperature": temperature}, min_confidence)

    async def noul(self, state: object, statement: str, *, min_confidence: float | None = None, temperature: float = 1.0) -> RoutedResult:
        return await self._route("noul", {"state": state, "statement": statement, "temperature": temperature}, min_confidence)