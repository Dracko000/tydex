# tydex

[![PyPI version](https://img.shields.io/pypi/v/tydex.svg)](https://pypi.org/project/tydex/)
[![Python versions](https://img.shields.io/pypi/pyversions/tydex.svg)](https://pypi.org/project/tydex/)
[![PyPI format](https://img.shields.io/pypi/format/tydex.svg)](https://pypi.org/project/tydex/)
[![License: MIT](https://img.shields.io/pypi/l/tydex.svg)](https://opensource.org/licenses/MIT)
[![CI](https://img.shields.io/github/actions/workflow/status/Dracko000/tydex/ci.yml?branch=main&label=CI)](https://github.com/Dracko000/tydex/actions)

Typed decision primitives for LLMs — `choice`, `score`, and `noul` (yes/no) — returned as **data with probabilities**, not prose. Built on top of a single model call with greedy decoding, plus calibration, confidence-based escalation, and an iterative re-calibration loop.

tydex is designed as a decision *engine*: consume it via the Python API or the HTTP server. There is no chat UI.

## Why

A decision workflow built on chat completions has to parse free text and guess how sure the model is. tydex instead asks the model for a **single typed token**, reads its probability mass directly, and lets you push that raw distribution through:

- **Temperature scaling** (`p^(1/T)`) to trade confidence against calibration.
- **Isotonic recalibration** against your own labeled samples (with a blend toward identity when data is scarce).
- **Routing/escalation** — cheap model by default, escalate to a frontier model (or a human) when confidence is too low.
- **Feedback loop** — label predictions and auto-refit the calibration as samples accumulate.

## tydex vs Jev

tydex is an open-source behavioural clone of **Jev**, the decision engine that inspired it. The primitive semantics (`choice`/`score`/`noul`) are modelled after Jev; the engineering tradeoffs favour openness and self-hosting.

```
Capability                          tydex                          Jev (original, closed)
-------------------------------------------------------------------------------------------
Source code                         open (GitHub)                  proprietary / closed
Install                             pip install . / py -m tydex     closed SaaS
Models & providers                  any: OpenAI, Anthropic,        fixed internal vendor set
                                    Ollama, OpenAI-compat, mock
No vendor lock-in                   yes                            no
Probabilities                       raw token logprobs or          internal estimate, not
                                    self-estimate JSON; auditable  documented
Calibration                         temperature + isotonic PAV     internal, not open
                                    + auto temperature, ECE report
Confidence escalation               tiered routing + human         yes (clone target)
                                    fallback
Feedback / auto-refit               Recorder + AutoCalibrator      internal
Interfaces                          Python API, HTTP, CLI, bench   limited HTTP/SDK
Self-hosting & data                 yes, all files on your side    no, data on their servers
Verification                        89 tests + CI + e2e            not published
```

Implementation openness (illustrative, 0–10):

```
tydex      ██████████  10  — your code, data, and calibration pipeline
Jev (orig) ██           2  — black-box SaaS
```

Primitive behaviour parity vs Jev:

```
choice  ██████████  100%  (logprobs + self mode, temperature scaling)
score   ██████████  100%  (ordered levels, per-primitive calibration)
noul    ██████████  100%  (probability + bool_value)
```

> The **Jev** column describes the behaviour that tydex *clones* when it applies to primitives or features that are not publicly documented — it is not a claim about Jev's internal implementation.

## Install

```bash
pip install tydex
```

From a source checkout: `pip install .`. Python `>= 3.10`. No third-party runtime dependencies (HTTP backends use stdlib `urllib`).

## Quick start

```python
from tydex import Tydex, MockBackend

tdex = Tydex(MockBackend(), model="mock")

r = tdex.choice(
    {"topic": "refund"},
    ["refund", "replace", "no_action"],
    question="How should we resolve this ticket?",
)
print(r.choice)              # "refund"
print(r.probabilities)       # {"refund": 0.6, "replace": 0.3, "no_action": 0.1}
print(r.confidence)          # 0.6
print(r.source)              # "logprobs"
```

### The three primitives

| Primitive | Returns | When |
|---|---|---|
| `choice` | one of your options + full probability distribution | single/multi-class selection |
| `score` | a level from an ordered set (wraps `choice`) | prioritize/triage (critical → low) |
| `noul` | probability of a statement being true + `bool_value` | yes/no gates, claim validation |

```python
n = tdex.noul({"priority": "P0"}, "This incident violates the SLA.")
print(n.probability)   # 0.9
print(n.bool_value)    # True
```

### Modes

Two ways to obtain probabilities; chosen automatically via `mode="auto"`:

- **`logprobs`** — read the actual token probability from the model (`supports_logprobs` backend). Exact and cheap, but needs backend support.
- **`self`** — ask the model for JSON (`{"choice": ..., "probability": ...}`) and parse it. Works with every backend, including the Ollama cloud API that exposes no logprobs.

```python
tdex.choice(state, options, mode="self")          # force JSON estimate
tdex.choice(state, options, temperature=2.0)      # sharpen/soften via p^(1/T)
```

## Backends

All backends speak plain HTTP to a chat-completions-style or Messages-style API.

| Backend | Family | logprobs | CLI provider |
|---|---|---|---|
| `MockBackend` | — | yes | `mock` |
| `OpenAIBackend` | OpenAI | yes | `openai` |
| `OpenAICompatibleBackend` | any `/v1/chat/completions` | toggle | `openai_compatible_cloud` / `openai_compatible_local` |
| `LocalOpenAIBackend` | OpenAI-compatible | toggle | — |
| `OllamaBackend` | Ollama `/api/chat` | no | `ollama` |
| `AnthropicCompatibleBackend` | Messages `/v1/messages` | no | `anthropic` |

`openai_compatible_cloud` defaults to `https://api.openai.com/v1` (override with `OPENAI_BASE_URL` or `--base-url`) and reads `OPENAI_API_KEY`/`OLLAMA_API_KEY`; `openai_compatible_local` targets a server on your machine — `http://localhost:8000/v1` by default (override with `OLLAMA_HOST`) — and accepts the same two key vars.

```python
from tydex import AnthropicCompatibleBackend, Tydex

tdex = Tydex(
    AnthropicCompatibleBackend(
        model="claude-3-5-haiku-latest",
        api_key="...",
        base_url="https://api.anthropic.com",
    ),
    model="claude-3-5-haiku-latest",
)
```

The OpenAI SDK is **not** required; every backend uses stdlib HTTP.

## Calibration

The model's raw probabilities are rarely calibrated. tydex provides two layers.

### Temperature scaling

```python
from tydex.calibration import tune_temperature

probs = [{"refund": 0.95, "replace": 0.05}]   # list of predicted distributions
labels = ["refund"]                            # ground truth labels
result = tune_temperature(probs, labels)       # sweeps T to minimize ECE
print(result.temperature, result.metrics.ece)  # e.g. 2.1, 0.060
```

### Calibration system (isotonic + temperature)

Fit per-primitive isotonic (PAV) recalibration with a blend toward identity for small samples, plus per-primitive tuned temperature:

```python
from tydex import CalibrationSystem, Recorder

system = CalibrationSystem(Recorder("tydex-feedback.jsonl"), min_samples=8).fit()
calibrated = system.apply_to(tdex)

r = calibrated.choice({"x": 1}, ["a", "b"])     # source becomes "logprobs+cal"
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

rr = routed.choice({"q": 1}, ["a", "b"])
print(rr.tier, rr.escalations, rr.total_cost)   # e.g. "frontier" ["local-llama"] 1.1
```

A tier with `action="human"` raises `RequiresHuman` (with the full request context) when confidence never reaches the threshold.

## Feedback loop & auto-calibration

`Recorder` logs every prediction (`tydex-feedback.jsonl`); label them and `AutoCalibrator` re-fits and saves the calibration live.

```python
from tydex import AutoCalibrator, Recorder

auto = AutoCalibrator(Recorder(), refit_every=20, min_samples=8)
calibrated = auto.apply_to(tdex)

entry = auto.recorder.choice({"x": 1}, ["a", "b"], tdex.choice({"x": 1}, ["a", "b"]))
auto.label(entry.id, "a")          # logs the ground truth
auto.maybe_refit()                 # refits when refit_every pending samples accumulate
print(auto.status())               # pending, temperatures, history, labeled_total
```

## HTTP server

Run the decision engine behind a tiny JSON API. The server shares the same `AutoCalibrator`, so labels submitted over HTTP update the live calibration automatically.

```bash
python -m tydex.server --backend mock --port 8000
python -m tydex.server --backend anthropic --model claude-3-5-haiku-latest
python -m tydex.server --backend openai --model gpt-4o-mini
python -m tydex.server --backend ollama --model llama3.1:8b
python -m tydex.server --api-key <key>          # require auth (env: TYDEX_API_KEY)
python -m tydex.server --cors                    # allow cross-origin browser calls
```

Endpoints:

- `POST /evaluate` — run a batch of questions:
  ```json
  {
    "state": {"ticket": "wrong item shipped"},
    "questions": [
      {"id": "q1", "type": "choice", "options": ["refund", "replace"]},
      {"id": "q2", "type": "noul", "statement": "This needs agent approval"},
      {"id": "q3", "type": "score", "levels": ["critical", "high", "low"]}
    ]
  }
  ```
  Each result carries an `id`, `type`, its value, `probabilities`/`probability`, `confidence` — and a `log_id` when auto-calibration is attached.
- `POST /label` — attach ground truth to a `log_id`; triggers `maybe_refit()`.
- `POST /refit` — force a manual recalibration.
- `GET /calibration` — current status: pending count, temperatures, per-primitive meta, refit history.
- `GET /health` — liveness.
- `GET /openapi.json` — OpenAPI 3.0 spec of the API.

Security: with `--api-key` (or env `TYDEX_API_KEY`) every route except `/health` and `/openapi.json` requires `Authorization: Bearer <key>` or `X-Api-Key: <key>`. `--cors` enables browser preflight (`OPTIONS`) and `Access-Control-Allow-Origin` headers.

### Run with Docker

```bash
docker build -t tydex .
docker run -p 8000:8000 --env-file .env tydex
```

Environment-driven defaults (`--backend auto`): `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OLLAMA_HOST` (plus `OPENAI_MODEL`, `ANTHROPIC_MODEL`, `OLLAMA_MODEL`). A `.env` file is loaded automatically (supports both `KEY=value` and `KEY: value`); a filled-in template lives at [`.env.example`](.env.example).

## CLI

`pip install .` provides a `tydex` command (also runnable as `py -m tydex`). It connects to any AI provider from the shell and runs a single typed decision:

```bash
tydex providers                      # show providers, endpoints, key vars, configured status
tydex ask --type noul --statement "A week has seven days"
tydex ask --provider openai --type choice \
       --options "refund,replace" --state '{"ticket": "wrong item shipped"}'
tydex ask --provider openai_compatible_cloud --base-url https://ollama.com/v1 \
       --model gemma4:31b --no-logprobs --type noul --statement "..."
```

`--provider` defaults to `auto` and picks from the environment (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OLLAMA_API_KEY`, `OLLAMA_HOST`); `--mode self`/`--no-logprobs` force the JSON self-estimate path when the endpoint exposes no token logprobs. Add `--json` for machine-readable output.

## CLI tooling

- `demo.py` — end-to-end walkthrough: mock execution, calibration, escalation, calibration system.
- `bench.py` — run the labeled dataset (`data/tickets.jsonl`: 40 samples — 16 choice, 14 noul, 10 score) against a real backend and report accuracy + ECE before/after temperature tuning:
  ```bash
  python bench.py --model gemma4:31b --base-url https://ollama.com/v1
  python bench.py --model gemma4:31b --base-url https://ollama.com/v1 --reset-recorder
  ```
  Requires an Ollama cloud API key in `OLLAMA_API_KEY` (or `OPENAI_API_KEY`).

## Development

```bash
python -m unittest discover -s tests     # 90+ tests, incl. local HTTP fakes for both API families
python -m ruff check .                   # lint (ruff config in pyproject.toml)
python -m mypy tydex                     # optional static typing
```

CI (`.github/workflows/ci.yml`) runs lint + the full suite on Python 3.10–3.13.

## Project layout

```
tydex/
  core.py          # Tydex + choice/score/noul primitives, logprobs & self modes
  backends.py      # OpenAI-compatible, Anthropic-compatible, Ollama, Mock
  calibration.py   # ECE/Brier metrics, temperature tuning
  calibrated.py    # CalibrationSystem, isotonic PAV + identity blend
  routing.py       # RoutedTydex tiers, escalation, RequiresHuman
  feedback.py      # Recorder (thread-safe, atomic writes) + reports
  autocal.py       # AutoCalibrator live refit loop
  server.py        # HTTP API + CLI
  config.py        # .env helper
data/tickets.jsonl # labeled ticket-classification benchmark
```