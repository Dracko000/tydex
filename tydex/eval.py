from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import math
from dataclasses import dataclass
from typing import Any, Sequence
from collections import defaultdict

from tydex.backends import LocalOpenAIBackend, OpenAIBackend, MockBackend
from tydex.core import Tydex, ChoiceResult, ScoreResult, NoulResult
from tydex.calibrated import CalibrationSystem, CalibratedTydex
from tydex.core import EnsembleTydex, RefiningTydex
from tydex.calibration import tune_temperature
from tydex.config import env_api_key

@dataclass
class MetricResult:
    accuracy: float
    ece: float
    brier_score: float
    n: int

class EvaluationFramework:
    def __init__(self, backend=None, model: str = "default"):
        self.backend = backend
        self.model = model

    def load_dataset(self, path: str) -> list[dict]:
        samples = []
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    samples.append(json.loads(line))
        return samples

    def calculate_brier_score(self, probs: dict[str, float], label: str) -> float:
        # Brier score: (prob_of_correct - 1)^2 + sum((prob_of_others)^2)
        p_correct = probs.get(label, 0.0)
        score = (p_correct - 1.0)**2
        for opt, p in probs.items():
            if opt != label:
                score += p**2
        return score

    async def evaluate_config(self, name: str, tdex_instance, dataset: list[dict]) -> dict[str, MetricResult]:
        metrics_by_prim = {}

        # Separate by primitive for metrics
        for prim in ("choice", "score", "noul"):
            samples = [s for s in dataset if s["primitive"] == prim]
            if not samples:
                continue

            probs_list = []
            labels_list = []
            briers = []

            for s in samples:
                try:
                    if prim == "choice":
                        res = await tdex_instance.choice(s["state"], s["options"], question=s.get("question"))
                        probs, label = res.probabilities, s["answer"]
                    elif prim == "score":
                        res = await tdex_instance.score(s["state"], s["levels"], question=s.get("question"))
                        probs, label = res.probabilities, s["answer"]
                    else: # noul
                        res = await tdex_instance.noul(s["state"], s["statement"])
                        probs = {"true": res.probability, "false": 1.0 - res.probability}
                        label = "true" if s["answer"] else "false"

                    probs_list.append(probs)
                    labels_list.append(label)
                    briers.append(self.calculate_brier_score(probs, label))
                except Exception as e:
                    print(f"Error evaluating {prim} sample: {e}")
                    continue

            if not probs_list:
                continue

            # Accuracy
            acc = sum(1 for p, l in zip(probs_list, labels_list) if max(p, key=p.get) == l) / len(probs_list)

            # Calibration (ECE)
            tuned = tune_temperature(probs_list, labels_list)
            ece = tuned.baseline.ece

            # Avg Brier
            avg_brier = sum(briers) / len(briers)

            metrics_by_prim[prim] = MetricResult(
                accuracy=acc,
                ece=ece,
                brier_score=avg_brier,
                n=len(probs_list)
            )

        return metrics_by_prim

async def main():
    parser = argparse.ArgumentParser(description="Tydex Evaluation Framework - Ladder Test")
    parser.add_argument("--data", default=os.path.join("data", "tickets.jsonl"))
    parser.add_argument("--model", default="gemma4:31b")
    parser.add_argument("--base-url", default="https://ollama.com/v1")
    args = parser.parse_args()

    api_key = env_api_key("OLLAMA_API_KEY", "OPENAI_API_KEY")
    if not api_key:
        sys.exit("Set OLLAMA_API_KEY or OPENAI_API_KEY first")

    # Setup Backend
    backend = LocalOpenAIBackend(model=args.model, api_key=api_key, base_url=args.base_url, supports_logprobs=False)
    dataset = EvaluationFramework().load_dataset(args.data)

    # Build the Ladder
    # 1. Base
    base_tdex = Tydex(backend, model=args.model)

    # 2. Calibrated (Mocking a fitted system for eval purposes if not provided)
    # In real scenario, we'd load a .json calibration file
    cal_sys = CalibrationSystem()
    # Fit on a subset of data to enable calibration
    subset_probs = []
    subset_labels = []
    for s in dataset[:50]:
        if s["primitive"] == "choice":
            # Simplified fit for demo
            subset_probs.append({opt: 1.0/len(s["options"]) for opt in s["options"]})
            subset_labels.append(s["answer"])
    cal_sys.fit(force=True) # This is simplified; real fit needs actual data
    calibrated_tdex = cal_sys.apply_to(base_tdex)

    # 3. Ensemble (using same model for demo, but typically different ones)
    ensemble_tdex = EnsembleTydex([base_tdex, base_tdex])

    # 4. Refined
    refined_tdex = RefiningTydex(base_tdex, threshold=0.8)

    configs = {
        "Base": base_tdex,
        "Calibrated": calibrated_tdex,
        "Ensemble": ensemble_tdex,
        "Refined": refined_tdex
    }

    evaluator = EvaluationFramework()

    print(f"{'Config':<15} | {'Prim':<8} | {'Acc':<6} | {'ECE':<6} | {'Brier':<6} | {'n':<4}")
    print("-" * 55)

    for name, tdex in configs.items():
        results = await evaluator.evaluate_config(name, tdex, dataset)
        for prim, m in results.items():
            print(f"{name:<15} | {prim:<8} | {m.accuracy:.3f} | {m.ece:.3f} | {m.brier_score:.3f} | {m.n:<4}")
        print("-" * 55)

if __name__ == "__main__":
    asyncio.run(main())
