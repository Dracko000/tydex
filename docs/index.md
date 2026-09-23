# tydex

[![PyPI version](https://img.shields.io/pypi/v/tydex.svg)](https://pypi.org/project/tydex/)
[![Python versions](https://img.shields.io/pypi/pyversions/tydex.svg)](https://pypi.org/project/tydex/)
[![License: MIT](https://img.shields.io/pypi/l/tydex.svg)](https://opensource.org/licenses/MIT)
[![CI](https://img.shields.io/github/actions/workflow/status/Dracko000/tydex/ci.yml?branch=main&label=CI)](https://github.com/Dracko000/tydex/actions)
[![GitHub release](https://img.shields.io/github/v/release/Dracko000/tydex)](https://github.com/Dracko000/tydex/releases)

Typed decision primitives for LLMs — `choice`, `score`, and `noul` (yes/no) — returned as **data with probabilities**, not prose. Built on top of a single model call with greedy decoding, plus calibration, confidence-based escalation, and an iterative re-calibration loop.

tydex is designed as a decision *engine*: consume it via the Python API or the HTTP server. There is no chat UI.

## Why

A decision workflow built on chat completions has to parse free text and guess how sure the model is. tydex instead asks the model for a **single typed token**, reads its probability mass directly, and lets you push that raw distribution through:

- **Temperature scaling** (`p^(1/T)`) to trade confidence against calibration.
- **Isotonic recalibration** against your own labeled samples (with a blend toward identity when data is scarce).
- **Routing/escalation** — cheap model by default, escalate to a frontier model (or a human) when confidence is too low.
- **Feedback loop** — label predictions and auto-refit the calibration as samples accumulate.

## Install

```bash
pip install tydex
```

Python `>= 3.10`. The only runtime dependency is `httpx` (async HTTP transports); the HTTP server needs the optional `server` extra (`fastapi` + `uvicorn`).

## Quick start

```python
import asyncio
from tydex import Tydex, MockBackend

async def main():
    tdex = Tydex(MockBackend(), model="mock")

    r = await tdex.choice(
        {"topic": "refund"},
        ["refund", "replace", "no_action"],
        question="How should we resolve this ticket?",
    )
    print(r.choice)              # "refund"
    print(r.probabilities)       # {"refund": 0.6, "replace": 0.3, "no_action": 0.1}
    print(r.confidence)          # 0.6
    print(r.source)              # "logprobs"

asyncio.run(main())
```

## The three primitives

| Primitive | Returns | When |
|---|---|---|
| `choice` | one of your options + full probability distribution | single/multi-class selection |
| `score` | a level from an ordered set (wraps `choice`) | prioritize/triage (critical → low) |
| `noul` | probability of a statement being true + `bool_value` | yes/no gates, claim validation |

```python
n = await tdex.noul({"priority": "P0"}, "This incident violates the SLA.")
print(n.probability)   # 0.9
print(n.bool_value)    # True
```

## Modes

Two ways to obtain probabilities; chosen automatically via `mode="auto"`:

- **`logprobs`** — read the actual token probability from the model (`supports_logprobs` backend). Exact and cheap, but needs backend support.
- **`self`** — ask the model for JSON (`{"choice": ..., "probability": ...}`) and parse it. Works with every backend, including APIs that expose no logprobs.

```python
await tdex.choice(state, options, mode="self")          # force JSON estimate
await tdex.choice(state, options, temperature=2.0)      # sharpen/soften via p^(1/T)
```