# Calibration & routing

The model's raw probabilities are rarely calibrated. tydex provides two layers, plus escalation routing and a feedback loop.

## Temperature scaling

```python
from tydex.calibration import tune_temperature

probs = [{"refund": 0.95, "replace": 0.05}]   # list of predicted distributions
labels = ["refund"]                            # ground truth labels
result = tune_temperature(probs, labels)       # sweeps T to minimize ECE
print(result.temperature, result.metrics.ece)  # e.g. 2.1, 0.060
```

## Calibration system (isotonic + temperature)

Fit per-primitive isotonic (PAV) recalibration with a blend toward identity for small samples, plus per-primitive tuned temperature:

```python
from tydex import CalibrationSystem, Recorder

system = CalibrationSystem(Recorder("tydex-feedback.jsonl"), min_samples=8).fit()
calibrated = system.apply_to(tdex)

r = await calibrated.choice({"x": 1}, ["a", "b"])     # source becomes "logprobs+cal"
```

Results persist via `system.save("tydex-calibration.json")` / `system.load(...)`.

## Escalation routing

Route across tiers of cost: a cheap local model first, escalate to frontier when confidence is too low, and finally to a human:

```python
from tydex import RoutedTydex, Tier, Tydex
from tydex.backends import MockBackend

weak = Tydex(MockBackend({"0": 0.55, "1": 0.45}), model="local")
routed = RoutedTydex([
    Tier(weak, threshold=0.8, label="local-llama", cost=0.1),
    Tier(Tydex(MockBackend({"0": 0.92, "1": 0.08}), model="gpt-4o"), threshold=None, label="frontier", cost=1.0),
])

rr = await routed.choice({"q": 1}, ["a", "b"])
print(rr.tier, rr.escalations, rr.total_cost)   # e.g. "frontier" ["local-llama"] 1.1
```

A tier with `action="human"` raises `RequiresHuman` (with the full request context) when confidence never reaches the threshold.

## Feedback loop & auto-calibration

`Recorder` logs every prediction (`tydex-feedback.jsonl`); label them and `AutoCalibrator` re-fits and saves the calibration live.

```python
from tydex import AutoCalibrator, Recorder

auto = AutoCalibrator(Recorder(), refit_every=20, min_samples=8)
calibrated = auto.apply_to(tdex)

entry = auto.recorder.choice({"x": 1}, ["a", "b"], await tdex.choice({"x": 1}, ["a", "b"]))
auto.label(entry.id, "a")          # logs the ground truth
auto.maybe_refit()                 # refits when refit_every pending samples accumulate
print(auto.status())               # pending, temperatures, history, labeled_total
```

## Benchmark

`bench.py` runs the labeled dataset (`data/tickets.jsonl`: 60 samples — 24 choice, 21 noul, 15 score) against a real backend:

```bash
python bench.py --model gemma4:31b --base-url https://ollama.com/v1 --reset-recorder
```

Latest run (`gemma4:31b`, Ollama cloud, 2026-09):

| primitive | n | accuracy | ECE before | best T | ECE after |
|---|---|---|---|---|---|
| choice | 24 | 0.58 | 0.350 | 2.7 | 0.023 |
| score | 15 | 0.60 | 0.313 | 2.1 | 0.057 |
| noul | 21 | 0.71 | 0.161 | 1.4 | 0.158 |