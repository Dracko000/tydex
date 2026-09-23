from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .core import Tydex


@dataclass
class Metrics:
    ece: float
    brier: float
    accuracy: float
    mean_confidence: float


@dataclass
class CalibrationResult:
    temperature: float
    metrics: Metrics
    baseline: Metrics


def _metrics(probabilities: list[dict[str, float]], correct: list[str], n_bins: int = 10) -> Metrics:
    total = len(probabilities)
    bins: list[list[tuple[float, bool]]] = [[] for _ in range(n_bins)]
    brier_sum = 0.0
    correct_count = 0
    for probs, label in zip(probabilities, correct, strict=True):
        chosen = max(probs, key=lambda k: probs[k])
        confidence = probs[chosen]
        ok = chosen == label
        correct_count += int(ok)
        brier_sum += (1.0 - confidence) ** 2 if ok else confidence**2
        bins[min(n_bins - 1, int(confidence * n_bins))].append((confidence, ok))
    if total == 0:
        return Metrics(ece=0.0, brier=0.0, accuracy=0.0, mean_confidence=0.0)
    ece = 0.0
    weight = sum(len(b) for b in bins)
    for b in bins:
        if not b:
            continue
        acc = sum(1 for _, ok in b if ok) / len(b)
        conf = sum(c for c, _ in b) / len(b)
        ece += (len(b) / weight) * abs(acc - conf)
    return Metrics(
        ece=ece,
        brier=brier_sum / total,
        accuracy=correct_count / total,
        mean_confidence=sum(max(p.values()) for p in probabilities) / total,
    )


def _rescale_all(probabilities: list[dict[str, float]], temperature: float) -> list[dict[str, float]]:
    if temperature == 1.0:
        return probabilities
    exponent = 1.0 / temperature
    rescaled = []
    for probs in probabilities:
        powered = {key: value**exponent for key, value in probs.items()}
        total = sum(powered.values())
        rescaled.append({key: value / total for key, value in powered.items()} if total else probs)
    return rescaled


def tune_temperature(
    probabilities: list[dict[str, float]],
    correct: list[str],
    *,
    temperature_grid: Sequence[float] | None = None,
) -> CalibrationResult:
    baseline = _metrics(probabilities, correct)
    if temperature_grid is None:
        temperature_grid = [x / 10 for x in range(5, 51)]
    best_t, best_ece = 1.0, baseline.ece
    for t in temperature_grid:
        if t <= 0:
            continue
        scaled = _rescale_all(probabilities, t)
        ece = _metrics(scaled, correct).ece
        if ece < best_ece:
            best_t, best_ece = t, ece
    scaled = _rescale_all(probabilities, best_t)
    return CalibrationResult(temperature=best_t, metrics=_metrics(scaled, correct), baseline=baseline)


async def calibrate_temperature(
    tdex: Tydex,
    samples: Sequence[tuple[object, Sequence[str], str, str]],
    *,
    temperature_grid: Sequence[float] | None = None,
) -> CalibrationResult:
    probabilities: list[dict[str, float]] = []
    correct: list[str] = []
    for state, options, question, label in samples:
        result = await tdex.choice(state, options, question=question)
        probabilities.append(result.probabilities)
        correct.append(label)
    return tune_temperature(probabilities, correct, temperature_grid=temperature_grid)