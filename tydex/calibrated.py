from __future__ import annotations

import bisect
import json
import os
from datetime import datetime, timezone
from typing import Any

from .calibration import _metrics, tune_temperature
from .core import ChoiceResult, NoulResult, ScoreResult, Tydex
from .feedback import Recorder


def _age_days(ts: str) -> float:
    try:
        parsed = datetime.fromisoformat(ts)
    except ValueError:
        return 0.0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds() / 86400.0)


def _pav(xs: list[float], ys: list[float], ws: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    xs = [xs[i] for i in order]
    ys = [ys[i] for i in order]
    ws = [ws[i] for i in order]
    starts = list(range(len(xs)))
    ends = list(range(len(xs)))
    means = list(ys)
    sums_w = [y * w for y, w in zip(ys, ws, strict=True)]
    cnts = list(ws)
    idx = 0
    while idx < len(means) - 1:
        if means[idx] > means[idx + 1]:
            new_sum = sums_w[idx] + sums_w[idx + 1]
            new_cnt = cnts[idx] + cnts[idx + 1]
            ends[idx] = ends[idx + 1]
            sums_w[idx] = new_sum
            cnts[idx] = new_cnt
            means[idx] = new_sum / new_cnt if new_cnt > 0 else means[idx]
            del starts[idx + 1], ends[idx + 1], sums_w[idx + 1], cnts[idx + 1], means[idx + 1]
            if idx > 0:
                idx -= 1
        else:
            idx += 1
    out = [0.0] * len(xs)
    for s, e, m in zip(starts, ends, means, strict=True):
        for j in range(s, e + 1):
            out[j] = max(0.0, min(1.0, m))
    return out


class IsotonicCalibrator:
    def __init__(self) -> None:
        self.xs: list[float] = []
        self.ys: list[float] = []

    def fit(self, confidences: list[float], correctness: list[bool], weights: list[float] | None = None, blend: float = 0.25) -> IsotonicCalibrator:
        if not confidences:
            return self
        ws = weights or [1.0] * len(confidences)
        pav = _pav(confidences, [1.0 if ok else 0.0 for ok in correctness], ws)
        xs = sorted(confidences)
        ys = [max(0.0, min(1.0, blend * y + (1.0 - blend) * x)) for x, y in zip(xs, pav, strict=True)]
        self.xs = xs
        self.ys = ys
        return self

    def transform(self, p: float) -> float:
        if not self.xs:
            return p
        if p <= self.xs[0]:
            return self.ys[0]
        if p >= self.xs[-1]:
            return self.ys[-1]
        i = bisect.bisect_left(self.xs, p)
        if i == 0:
            return self.ys[0]
        x0, x1 = self.xs[i - 1], self.xs[i]
        y0, y1 = self.ys[i - 1], self.ys[i]
        if x1 == x0:
            return y1
        return y0 + (y1 - y0) * (p - x0) / (x1 - x0)

    def transform_probs(self, probabilities: dict[str, float]) -> dict[str, float]:
        if not self.xs:
            return probabilities
        chosen = max(probabilities, key=lambda k: probabilities[k])
        p0 = probabilities[chosen]
        p1 = max(0.0, min(1.0, self.transform(p0)))
        denom = max(1e-9, 1.0 - p0)
        out = {key: (p1 if key == chosen else value * (1.0 - p1) / denom) for key, value in probabilities.items()}
        total = sum(out.values())
        return {key: value / total for key, value in out.items()} if total > 0 else probabilities

    def to_dict(self) -> dict[str, list[float]]:
        return {"xs": self.xs, "ys": self.ys}

    def from_dict(self, data: dict[str, list[float]]) -> IsotonicCalibrator:
        self.xs = list(data.get("xs", []))
        self.ys = list(data.get("ys", []))
        return self


def _entry_probs_label(entry) -> tuple[dict[str, float], str] | None:
    if entry.probability is None and not entry.probabilities:
        return None
    if entry.primitive == "noul":
        probs = {"true": entry.probability, "false": 1.0 - entry.probability}
        label = "true" if str(entry.label).lower() in {"true", "1", "yes"} else "false"
        return probs, label
    if entry.probabilities:
        return entry.probabilities, str(entry.label)
    return None


class CalibrationSystem:
    def __init__(self, recorder: Recorder | None = None, *, min_samples: int = 8, min_ref: int = 30, recency_half_life_days: float | None = None):
        self.recorder = recorder or Recorder()
        self.min_samples = min_samples
        self.min_ref = min_ref
        self.recency_half_life_days = recency_half_life_days
        self.calibrators: dict[str, IsotonicCalibrator] = {}
        self.temperatures: dict[str, float] = {}
        self.meta: dict[str, dict[str, Any]] = {}

    def fit(self, primitive: str | None = None, force: bool = False) -> CalibrationSystem:
        primitives = ("choice", "score", "noul") if primitive is None else (primitive,)
        samples: dict[str, list] = {p: [] for p in primitives}
        for entry in self.recorder.labeled():
            if entry.primitive not in primitives:
                continue
            bundle = _entry_probs_label(entry)
            if bundle is None:
                continue
            probs, label = bundle
            confidence = probs[max(probs, key=lambda k: probs[k])]
            correct = entry.correct
            if correct is None:
                continue
            weight = 1.0
            if self.recency_half_life_days:
                weight = 0.5 ** (_age_days(entry.ts) / self.recency_half_life_days)
            samples[entry.primitive].append((confidence, correct, weight, probs, label))
        for prim in primitives:
            rows = samples[prim]
            n = len(rows)
            if n < self.min_samples and not force:
                continue
            confs = [r[0] for r in rows]
            oks = [r[1] for r in rows]
            ws = [r[2] for r in rows]
            prob_list = [r[3] for r in rows]
            label_list = [r[4] for r in rows]
            alpha = min(1.0, n / max(1, self.min_ref))
            calibrator = IsotonicCalibrator().fit(confs, oks, ws, blend=0.5 * alpha)
            tuned = tune_temperature(prob_list, label_list)
            calibrated_probs = [calibrator.transform_probs(p) for p in prob_list]
            self.calibrators[prim] = calibrator
            self.temperatures[prim] = tuned.temperature
            self.meta[prim] = {
                "n": n,
                "accuracy": float(sum(1 for _, ok, *_ in rows if ok) / n),
                "mean_confidence": tuned.baseline.mean_confidence,
                "ece_before": tuned.baseline.ece,
                "ece_after_calibrator": _metrics(calibrated_probs, label_list).ece,
                "temperature": tuned.temperature,
            }
        return self

    def transform(self, primitive: str, probabilities: dict[str, float]) -> dict[str, float]:
        calibrator = self.calibrators.get(primitive)
        if calibrator is not None:
            return calibrator.transform_probs(probabilities)
        return probabilities

    def apply_to(self, tdex: Tydex) -> CalibratedTydex:
        return CalibratedTydex(tdex, self)

    def config(self) -> dict[str, Any]:
        return {
            "calibrators": {prim: cal.to_dict() for prim, cal in self.calibrators.items()},
            "temperatures": self.temperatures,
            "meta": self.meta,
        }

    def save(self, path: str = "tydex-calibration.json") -> None:
        directory = os.path.dirname(path) or "."
        os.makedirs(directory, exist_ok=True)
        import tempfile

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, delete=False) as fh:
            json.dump(self.config(), fh, ensure_ascii=False, indent=2)
            tmp = fh.name
        os.replace(tmp, path)

    def load(self, path: str = "tydex-calibration.json") -> CalibrationSystem:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        for prim, raw in data.get("calibrators", {}).items():
            calibrator = IsotonicCalibrator()
            calibrator.from_dict(raw)
            self.calibrators[prim] = calibrator
        self.temperatures = {k: float(v) for k, v in data.get("temperatures", {}).items()}
        self.meta = data.get("meta", {})
        return self


class CalibratedTydex:
    def __init__(self, tdex: Tydex, system: CalibrationSystem):
        self.tdex = tdex
        self.system = system
        self.backend = getattr(tdex, "backend", None)
        self.model = getattr(tdex, "model", "calibrated")

    def _apply(self, primitive: str, result: Any) -> Any:
        if primitive == "noul":
            probs = {"true": result.probability, "false": 1.0 - result.probability}
            probs = self.system.transform(primitive, probs)
            p = probs["true"]
            return NoulResult(probability=p, confidence=max(p, 1.0 - p), source=f"{result.source}+cal")
        probs = self.system.transform(primitive, result.probabilities)
        chosen = max(probs, key=lambda k: probs[k])
        confidence = probs[chosen]
        source = f"{result.source}+cal"
        if primitive == "choice":
            return ChoiceResult(choice=chosen, probabilities=probs, confidence=confidence, source=source)
        return ScoreResult(score=chosen, probabilities=probs, confidence=confidence, source=source)

    def choice(self, state, options, *, question="Choose the best option.", temperature=1.0, **kwargs):
        return self._apply("choice", self.tdex.choice(state, options, question=question, temperature=temperature))

    def score(self, state, levels, *, question="Rate the state against the levels.", temperature=1.0, **kwargs):
        return self._apply("score", self.tdex.score(state, levels, question=question, temperature=temperature))

    def noul(self, state, statement, *, temperature=1.0, **kwargs):
        return self._apply("noul", self.tdex.noul(state, statement, temperature=temperature))