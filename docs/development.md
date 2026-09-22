# Development

## Set up

```bash
git clone https://github.com/Dracko000/tydex
cd tydex
pip install .            # or editable: pip install -e .
pip install .[tests]     # ruff + mypy for the checks below
```

## Checks

```bash
python -m unittest discover -s tests     # 91 tests, incl. local HTTP fakes for both API families
python -m ruff check .                   # lint (ruff config in pyproject.toml)
python -m mypy tydex                     # optional static typing (must stay clean)
```

CI (`.github/workflows/ci.yml`) runs lint + the full suite on Python 3.10–3.13. Release history is kept in [`CHANGELOG.md`](https://github.com/Dracko000/tydex/blob/main/CHANGELOG.md).

## Contributing

1. **Run the checks before pushing** — code is linted with ruff (line length 200, target py310), type-checked with mypy (the `tydex/` package must stay clean), and covered by the unittest suite.
2. **Keep the primitives typed** — `choice`/`score`/`noul` return dataclasses; new backends must speak plain HTTP (no SDKs) and declare `supports_logprobs`.
3. **No code comments** — tydex is written comment-free by design; explain non-obvious decisions in the commit message.
4. **Labeled samples** — dataset additions belong in `data/tickets.jsonl` (`primitive`, `state`, `options`/`levels`/`statement`, `answer`); rerun `bench.py` and update the results table.
5. **Releases** — bump `version` in `pyproject.toml`, add a `CHANGELOG.md` entry, then tag `vX.Y.Z`; CI publishes wheel/sdist to PyPI and the image to GHCR. Sign off by running `python -m build` + `twine check dist/*`.

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
  _version.py      # single source of the package version
data/tickets.jsonl # labeled ticket-classification benchmark
```