# Interfaces

Consume tydex three ways: the Python API, the HTTP server, or the CLI.

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

### Endpoints

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

### Docker

```bash
docker run --rm -p 8000:8000 --env-file .env ghcr.io/dracko000/tydex:latest
```

Images are built and published to the GitHub Container Registry on every `v*` tag (`ghcr.io/dracko000/tydex:<tag>` and `:latest`). To build locally: `docker build -t tydex .` then `docker run -p 8000:8000 --env-file .env tydex`.

Environment-driven defaults (`--backend auto`): `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OLLAMA_HOST` (plus `OPENAI_MODEL`, `ANTHROPIC_MODEL`, `OLLAMA_MODEL`). A `.env` file is loaded automatically (supports both `KEY=value` and `KEY: value`); a filled-in template lives at `.env.example`.

## CLI

`pip install tydex` provides a `tydex` command (also runnable as `py -m tydex`). It connects to any AI provider from the shell and runs a single typed decision:

```bash
tydex --version                      # print version and exit
tydex providers                      # show providers, endpoints, key vars, configured status
tydex ask --type noul --statement "A week has seven days"
tydex ask --provider openai --type choice \
       --options "refund,replace" --state '{"ticket": "wrong item shipped"}'
tydex ask --provider openai_compatible_cloud --base-url https://ollama.com/v1 \
       --model gemma4:31b --no-logprobs --type noul --statement "..."
```

`--provider` defaults to `auto` and picks from the environment (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OLLAMA_API_KEY`, `OLLAMA_HOST`); `--mode self`/`--no-logprobs` force the JSON self-estimate path when the endpoint exposes no token logprobs. Add `--json` for machine-readable output.

### Providers

| CLI provider | endpoint default | key vars |
|---|---|---|
| `openai` | `https://api.openai.com/v1` | `OPENAI_API_KEY` (required) |
| `openai_compatible_cloud` | `https://api.openai.com/v1` (`OPENAI_BASE_URL`/`--base-url`) | `OPENAI_API_KEY` / `OLLAMA_API_KEY` |
| `openai_compatible_local` | `http://localhost:8000/v1` (`OLLAMA_HOST`) | `OLLAMA_API_KEY` / `OPENAI_API_KEY` |
| `anthropic` | `https://api.anthropic.com` | `ANTHROPIC_API_KEY` (required) |
| `ollama` | `http://localhost:11434` (`OLLAMA_HOST`) | none |
| `mock` | — | none |