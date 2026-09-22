from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
import math
import sqlite3
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
    def __init__(self, path: str = "tydex-feedback.db"):
        self.path = path
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self) -> None:
        with self._lock:
            with sqlite3.connect(self.path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS logs (
                        id TEXT PRIMARY KEY,
                        ts TEXT,
                        primitive TEXT,
                        state TEXT,
                        question TEXT,
                        options TEXT,
                        levels TEXT,
                        statement TEXT,
                        temperature REAL,
                        choice TEXT,
                        score TEXT,
                        probability REAL,
                        probabilities TEXT,
                        confidence REAL,
                        source TEXT,
                        tier TEXT,
                        escalations TEXT,
                        cost REAL,
                        label TEXT
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_prim_label ON logs(primitive, label)")
                conn.commit()

    def _make(self, primitive: str, state: Any, **extra: Any) -> LogEntry:
        entry = LogEntry(
            id=uuid.uuid4().hex[:8],
            ts=_now(),
            primitive=primitive,
            state=state,
            **extra,
        )
        with self._lock:
            self.save_entry(entry)
        return entry

    def save_entry(self, entry: LogEntry) -> None:
        # This replaces the old self.save() which wrote the whole list
        with self._lock:
            with sqlite3.connect(self.path) as conn:
                conn.execute("""
                    INSERT INTO logs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    entry.id, entry.ts, entry.primitive, json.dumps(entry.state),
                    entry.question, json.dumps(entry.options), json.dumps(entry.levels),
                    entry.statement, entry.temperature, entry.choice, entry.score,
                    entry.probability, json.dumps(entry.probabilities), entry.confidence,
                    entry.source, entry.tier, json.dumps(entry.escalations),
                    entry.cost, entry.label
                ))
                conn.commit()

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
            with sqlite3.connect(self.path) as conn:
                cur = conn.execute("UPDATE logs SET label = ? WHERE id = ?", (label, entry_id))
                if cur.rowcount == 0:
                    raise KeyError(f"no entry with id {entry_id}")
                conn.commit()

    def labeled(self) -> list[LogEntry]:
        with self._lock:
            with sqlite3.connect(self.path) as conn:
                cur = conn.execute("SELECT * FROM logs WHERE label IS NOT NULL")
                return [self._row_to_entry(row) for row in cur.fetchall()]

    def _row_to_entry(self, row: tuple) -> LogEntry:
        return LogEntry(
            id=row[0], ts=row[1], primitive=row[2], state=json.loads(row[3]),
            question=row[4], options=json.loads(row[5]) if row[5] else None,
            levels=json.loads(row[6]) if row[6] else None, statement=row[7],
            temperature=row[8], choice=row[9], score=row[10],
            probability=row[11], probabilities=json.loads(row[12]) if row[12] else None,
            confidence=row[13], source=row[14], tier=row[15],
            escalations=json.loads(row[16]) if row[16] else [],
            cost=row[17], label=row[18]
        )

    def save(self) -> None:
        pass

    def load(self) -> None:
        pass

    def reset(self, *, keep_file: bool = False) -> None:
        with self._lock:
            if not keep_file:
                try:
                    os.remove(self.path)
                    self._init_db()
                except FileNotFoundError:
                    pass

    def monitor_drift(self, primitive: str, window_size: int = 100) -> bool:
        with self._lock:
            entries = [e for e in self._entries if e.primitive == primitive]
            if len(entries) < window_size * 2:
                return False

            recent = entries[-window_size:]
            baseline = entries[:window_size]

            def get_conf(e):
                return e.confidence if e.confidence is not None else 0.0

            mean_recent = sum(get_conf(e) for e in recent) / window_size
            mean_base = sum(get_conf(e) for e in baseline) / window_size

            # Simple shift detection: > 15% relative difference
            return abs(mean_recent - mean_base) > 0.15

    def suggest_labels(self, primitive: str, n: int = 10) -> list[str]:
        with self._lock:
            unlabeled = [e for e in self._entries if e.primitive == primitive and e.label is None]
            if not unlabeled:
                return []

            def score_uncertainty(e):
                if primitive == "noul":
                    return abs((e.probability or 0.5) - 0.5)
                if e.probabilities:
                    sorted_probs = sorted(e.probabilities.values(), reverse=True)
                    if len(sorted_probs) < 2:
                        return 0.0
                    return sorted_probs[0] - sorted_probs[1]
                return 1.0

            unlabeled.sort(key=score_uncertainty)
            return [e.id for e in unlabeled[:n]]

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

def get_model_accuracy(recorder: Recorder, model_name: str, primitive: str | None = None) -> float:
    with recorder._lock:
        with sqlite3.connect(recorder.path) as conn:
            query = "SELECT label, choice, score, probability FROM logs WHERE source = ? AND label IS NOT NULL"
            params = [model_name]
            if primitive:
                query += " AND primitive = ?"
                params.append(primitive)

            rows = conn.execute(query, params).fetchall()
            if not rows:
                return 0.0

            correct = 0
            for row in rows:
                label, choice, score, prob = row
                pred = choice or score or (str(prob == 1.0) if prob is not None else None)
                if str(pred) == str(label):
                    correct += 1

            return correct / len(rows)

class WeightTuner:
    def __init__(self, recorder: Recorder):
        self.recorder = recorder

    def get_weights(self, models: Sequence[Tydex]) -> list[float]:
        weights = []
        for m in models:
            name = getattr(m, "model", "unknown")
            acc = get_model_accuracy(self.recorder, name)
            weights.append(max(0.1, acc))

        total = sum(weights)
        return [w / total for w in weights]
