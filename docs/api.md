# API reference

Every public name is importable from `tydex` (server entry points are lazily loaded on first access).

## Core

### `tydex.Tydex`

```python
Tydex(backend: Backend, *, model: str | None = None)
```

Typed decision engine over a backend.

- `choice(state, options, *, question=None, mode="auto", temperature=1.0) -> ChoiceResult` — pick one of `options`; `options` must not be empty or duplicated.
- `score(state, levels, *, question=None, mode="auto", temperature=1.0) -> ScoreResult` — pick an ordered level (wraps `choice`, validates against `levels`).
- `noul(state, statement, *, mode="auto", temperature=1.0) -> NoulResult` — yes/no gate.

Results are dataclasses:

| Result | Fields |
|---|---|
| `ChoiceResult` | `choice`, `probabilities: dict[str, float]`, `confidence`, `source` |
| `ScoreResult` | `score`, `probabilities: dict[str, float]`, `confidence`, `source` |
| `NoulResult` | `probability`, `bool_value`, `confidence`, `source` |
| `RoutedResult` | `result`, `escalations`, `tier`, `total_cost` |

`source` is one of `logprobs`, `self`, `logprobs+cal`, `self+cal`, or `mock`.

Raises `tydex.SchemaError` for invalid state/options/levels inputs.

### `tydex.backends`

| Backend | Family | `supports_logprobs` |
|---|---|---|
| `MockBackend` | deterministic fixture | yes |
| `OpenAIBackend` | OpenAI cloud | yes |
| `OpenAICompatibleBackend` | any `/v1/chat/completions` | construct-time |
| `LocalOpenAIBackend` | OpenAI-compatible convenience | construct-time |
| `OllamaBackend` | Ollama native `/api/chat` | no |
| `AnthropicCompatibleBackend` | Messages `/v1/messages` | no |

All backends accept `model`, `api_key`, and (where relevant) `base_url`; all speak plain HTTP.

## Calibration

- `tydex.calibration.tune_temperature(probs, labels) -> CalibrationResult` — sweep `T` to minimize ECE; returns `.temperature`, `.baseline.ece`, `.metrics.ece`.
- `tydex.calibration.calibrate_temperature(probs, labels, temperature=None)` — scale probabilities by `p^(1/T)` and score.
- `tydex.CalibrationSystem(recorder, min_samples=8) -> .fit()` then `.apply_to(tydex) -> CalibratedTydex` — per-primitive isotonic (PAV) + temperature; `.save(path)` / `.load(path)`.
- `tydex.CalibratedTydex` — like `Tydex` (`choice`/`score`/`noul`), but applies calibration.
- `tydex.IsotonicCalibrator` — PAV monotone recalibration with an identity blend.

## Routing & feedback

- `tydex.RoutedTydex(tiers) -> .choice/.score/.noul -> RoutedResult` — route through `Tier(tdex, *, threshold=1.0, label=None, cost=1.0, action="model")`; a tier with `action="human"` raises `RequiresHuman` (carries `.request`, `.escalations`, `.tier`), and `on_escalation(label, confidence, threshold, total_cost)` fires on each escalation.
- `tydex.Recorder(path="tydex-feedback.jsonl")` — thread-safe, atomic-write log. `.choice/.score/.noul(...)` record entries, `.label(entry_id, label)` attaches ground truth, `.reset()`; reports via `.status()`.
- `tydex.AutoCalibrator(recorder, refit_every, min_samples)` — `.apply_to(tydex)`, `.label(id, label)`, `.maybe_refit()`, `.status()`.

## Config & misc

- `tydex.SchemaError`, `tydex.RequiresHuman`, `tydex.__version__`.
- `tydex.config.env_api_key(*names)` — first non-empty env var (auto-loads `.env`; supports `KEY=value` and `KEY: value`).

## Server

- `tydex.TydexServer` / `tydex.RoutedTydexServer` — `ThreadingHTTPServer` subclasses exposing `/evaluate`, `/label`, `/refit`, `/calibration`, `/health`, `/openapi.json`.
- `tydex.build_server(backend=None, *, model="default", routed=None, calibration=None, auto=None, api_key=None, cors=False) -> TydexServer | RoutedTydexServer` — `routed` is a `RoutedTydex`, `calibration` a `CalibrationSystem`, `auto` an `AutoCalibrator`. Pass `auto` to share the live calibrator (labels submitted over HTTP refit it).
- `tydex.run(host="127.0.0.1", port=8000, backend=None, *, model="default", routed=None, calibration=None, auto=None, api_key=None, cors=False)` — alias of `build_server(...)` + `serve_forever()` with graceful shutdown.