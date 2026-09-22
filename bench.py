from __future__ import annotations

import argparse
import json
import os
import sys

from tydex import LocalOpenAIBackend, Recorder, Tydex
from tydex.calibration import tune_temperature
from tydex.config import env_api_key


def normalize_model(model: str) -> str:
    return model.split("/")[-1].lower()


def load_samples(path: str, limit: int | None) -> list[dict]:
    samples = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                samples.append(json.loads(line))
    if limit:
        samples = samples[:limit]
    return samples


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the labeled ticket dataset through a Tydex backend and report calibration.")
    parser.add_argument("--model", default="gemma4:31b")
    parser.add_argument("--base-url", default="https://ollama.com/v1")
    parser.add_argument("--data", default=os.path.join("data", "tickets.jsonl"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--log", default="tydex-feedback.jsonl")
    parser.add_argument("--reset-recorder", action="store_true", help="clear the feedback log before running")
    args = parser.parse_args()

    args.model = normalize_model(args.model)
    api_key = env_api_key("OLLAMA_API_KEY", "OPENAI_API_KEY")
    if not api_key:
        sys.exit("set OLLAMA_API_KEY (or OPENAI_API_KEY) first")
    samples = load_samples(args.data, args.limit)

    backend = LocalOpenAIBackend(model=args.model, api_key=api_key, base_url=args.base_url, supports_logprobs=False)
    tdex = Tydex(backend, model=args.model)
    recorder = Recorder(args.log)
    if args.reset_recorder:
        recorder.reset()
        recorder = Recorder(args.log)

    probs_by: dict[str, list[dict[str, float]]] = {p: [] for p in ("choice", "score", "noul")}
    labels_by: dict[str, list[str]] = {p: [] for p in ("choice", "score", "noul")}

    for sample in samples:
        primitive = sample["primitive"]
        state = sample["state"]
        answer = sample["answer"]
        if primitive == "choice":
            result = tdex.choice(state, sample["options"], question=sample.get("question"))
            entry = recorder.choice(state, sample["options"], result, question=sample.get("question"))
            probs_by["choice"].append(result.probabilities)
            labels_by["choice"].append(answer)
        elif primitive == "score":
            result = tdex.score(state, sample["levels"], question=sample.get("question"))
            entry = recorder.score(state, sample["levels"], result, question=sample.get("question"))
            probs_by["score"].append(result.probabilities)
            labels_by["score"].append(answer)
        else:
            result = tdex.noul(state, sample["statement"])
            entry = recorder.noul(state, sample["statement"], result)
            probs_by["noul"].append({"true": result.probability, "false": 1.0 - result.probability})
            labels_by["noul"].append("true" if answer else "false")
        recorder.label(entry.id, str(answer))
        print(f"[{primitive:6}] pred={entry.predicted!r} conf={entry.confidence:.2f} label={answer}  {'OK' if entry.correct else 'MISS'}")

    for primitive in ("choice", "score", "noul"):
        if not probs_by[primitive]:
            continue
        tuned = tune_temperature(probs_by[primitive], labels_by[primitive])
        acc = sum(1 for p, label in zip(probs_by[primitive], labels_by[primitive], strict=True) if max(p, key=p.get) == label) / len(labels_by[primitive])
        print(f"\n[{primitive}] n={len(probs_by[primitive])}  acc={acc:.2f}")
        print(f"    ECE before={tuned.baseline.ece:.3f} (mean conf {tuned.baseline.mean_confidence:.2f})")
        print(f"    best T={tuned.temperature:.1f}  ECE after={tuned.metrics.ece:.3f}")


if __name__ == "__main__":
    main()