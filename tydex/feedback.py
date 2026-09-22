from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .calibration import tune_temperature
from .core import ChoiceResult, NoulResult, ScoreResult


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class LogEntry:
    id: str
    ts: str
    primitive: str
    state: Any
    question: str | None = None
    options: list[str] | None = None
    levels: list[str] | None = None
    statement: str | None = None
    temperature: float = 1.0
    choice: str | None = None
    score: str | None = None
    probability: float | None = None
    probabilities: dict[str, float] | None = None
    confidence: float | None = None
    source: str = ""
    tier: str | None = None
    escalations: list[str] = field(default_factory=list)
    cost: float | None = None
    label: str | None = None

    @property
    def predicted(self) -> str | float | bool | None:
        if self.primitive == "noul":
            return bool(self.probability is not None and self.probability >= 0.5)
        return self.choice if self.primitive == "choice" else self.score

    @property
    def correct(self) -> bool | None:
        if self.label is None or self.predicted is None:
            return None
        if self.primitive == "noul":
            return self.predicted == (str(self.label).lower() in {"true", "1", "yes"})
        return self.predicted == self.label


class Recorder:
    def __init__(self, path: str = "tydex-feedback.jsonl"):
        self.path = path
        self._lock = threading.RLock()
        self._entries: list[LogEntry] = []
        self.load()

    def _make(self, primitive: str, state: Any, **extra: Any) -> LogEntry:
        entry = LogEntry(
            id=uuid.uuid4().hex[:8],
            ts=_now(),
            primitive=primitive,
            state=state,
            **extra,
        )
        with self._lock:
            self._entries.append(entry)
            self.save()
        return entry

    def choice(
        self,
        state: Any,
        options: list[str],
        result: ChoiceResult,
        *,
        question: str | None = None,
        temperature: float = 1.0,
        tier: str | None = None,
        escalations: list[str] | None = None,
        cost: float | None = None,
    ) -> LogEntry:
        return self._make(
            "choice",
            state,
            question=question,
            options=options,
            temperature=temperature,
            choice=result.choice,
            probabilities=result.probabilities,
            confidence=result.confidence,
            source=result.source,
            tier=tier,
            escalations=list(escalations or []),
            cost=cost,
        )

    def score(
        self,
        state: Any,
        levels: list[str],
        result: ScoreResult,
        *,
        question: str | None = None,
        temperature: float = 1.0,
        tier: str | None = None,
        escalations: list[str] | None = None,
        cost: float | None = None,
    ) -> LogEntry:
        return self._make(
            "score",
            state,
            question=question,
            levels=levels,
            temperature=temperature,
            score=result.score,
            probabilities=result.probabilities,
            confidence=result.confidence,
            source=result.source,
            tier=tier,
            escalations=list(escalations or []),
            cost=cost,
        )

    def noul(
        self,
        state: Any,
        statement: str,
        result: NoulResult,
        *,
        temperature: float = 1.0,
        tier: str | None = None,
        escalations: list[str] | None = None,
        cost: float | None = None,
    ) -> LogEntry:
        return self._make(
            "noul",
            state,
            statement=statement,
            temperature=temperature,
            probability=result.probability,
            confidence=result.confidence,
            source=result.source,
            tier=tier,
            escalations=list(escalations or []),
            cost=cost,
        )

    def label(self, entry_id: str, label: str) -> None:
        with self._lock:
            for entry in self._entries:
                if entry.id == entry_id:
                    entry.label = label
                    self.save()
                    return
        raise KeyError(f"no entry with id {entry_id}")

    def labeled(self) -> list[LogEntry]:
        with self._lock:
            return [e for e in self._entries if e.label is not None]

    def save(self) -> None:
        with self._lock:
            directory = os.path.dirname(self.path) or "."
            os.makedirs(directory, exist_ok=True)
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, delete=False) as fh:
                for entry in self._entries:
                    fh.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
                tmp = fh.name
            os.replace(tmp, self.path)

    def load(self) -> None:
        with self._lock:
            try:
                with open(self.path, encoding="utf-8") as fh:
                    self._entries = [LogEntry(**json.loads(line)) for line in fh if line.strip()]
            except FileNotFoundError:
                self._entries = []

    def reset(self, *, keep_file: bool = False) -> None:
        with self._lock:
            self._entries = []
            if not keep_file:
                try:
                    os.remove(self.path)
                except FileNotFoundError:
                    pass

    def _calibration_bundle(self, primitive: str) -> tuple[list[dict[str, float]], list[str]]:
        probs: list[dict[str, float]] = []
        labels: list[str] = []
        for entry in self.labeled():
            if entry.primitive != primitive:
                continue
            if primitive == "noul":
                p = entry.probability
                if p is None:
                    continue
                probs.append({"true": p, "false": 1.0 - p})
                labels.append("true" if str(entry.label).lower() in {"true", "1", "yes"} else "false")
            elif entry.probabilities:
                probs.append(entry.probabilities)
                labels.append(entry.label or "")
        return probs, labels

    def best_temperature(self, primitive: str) -> float:
        probs, labels = self._calibration_bundle(primitive)
        if len(probs) < 3:
            return 1.0
        return tune_temperature(probs, labels).temperature

    def report(self) -> dict[str, Any]:
        entries = self._entries
        labeled = self.labeled()
        routed = [e for e in entries if e.escalations]
        used_tiers = [e for e in entries if e.tier]
        report: dict[str, Any] = {
            "total": len(entries),
            "by_primitive": {p: sum(1 for e in entries if e.primitive == p) for p in ("choice", "score", "noul")},
            "labeled": len(labeled),
            "per_primitive": {},
            "routing": {
                "escalation_rate": (len(routed) / len(used_tiers)) if used_tiers else None,
                "avg_cost": (sum(float(e.cost or 0.0) for e in used_tiers) / len(used_tiers)) if used_tiers else None,
                "total_cost": sum(float(e.cost or 0.0) for e in used_tiers),
                "tiers_seen": sorted({t for e in entries if (t := e.tier)}),
            },
        }
        for primitive in ("choice", "score", "noul"):
            probs, labels = self._calibration_bundle(primitive)
            if not probs:
                continue
            calibrated = tune_temperature(probs, labels)
            report["per_primitive"][primitive] = {
                "n": len(probs),
                "accuracy": float(sum(1 for p, label in zip(probs, labels, strict=True) if _argmax_label(p) == label) / len(probs)),
                "ece_before": calibrated.baseline.ece,
                "ece_after": calibrated.metrics.ece,
                "best_temperature": calibrated.temperature,
                "mean_confidence": calibrated.baseline.mean_confidence,
            }
        return report


def _argmax_label(probs: dict[str, float]) -> str:
    return max(probs, key=lambda k: probs[k])