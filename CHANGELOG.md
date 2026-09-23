# Changelog

All notable changes to tydex are documented here. Releases are tagged `vX.Y.Z` and published to PyPI (`tydex`) and GitHub Container Registry (`ghcr.io/dracko000/tydex`).

## [Unreleased]

### Changed
- Public API is fully async (`await` `choice`/`score`/`noul` on `Tydex`, `CalibratedTydex`, `EnsembleTydex`, `RefiningTydex`, and `RoutedTydex`); the CLI wraps calls via `asyncio.run`.
- HTTP transports moved to `httpx` (now the single runtime dependency); the HTTP server lives behind the optional `server` extra (`fastapi` + `uvicorn`).
- `Recorder` restored its in-memory `_entries` cache (`load()`/`save_entry()`/`label()`/`reset()`), powering drift monitoring, label suggestions, and reports.
- Unit tests migrated to async (`IsolatedAsyncioTestCase`) and `test_server.py` now exercises the FastAPI `build_app` via `TestClient`.

## [Unreleased]

### Changed
- `choice` / `score` / `noul` are now async: the primitives are coroutines and every public engine (`Tydex`, `EnsembleTydex`, `RefiningTydex`, `RoutedTydex`, `CalibratedTydex`, `CalibrationSystem`, `AutoCalibrator`) returns an awaitable. The CLI and HTTP server wrap them via `asyncio.run` / the FastAPI async call stack (no breaking call site changes through the server; the Python API now requires `await`).
- Runtime dependency story updated: the core now requires `httpx` (async HTTP transports); the OpenAI/Anthropic/Ollama/OllamaHTTP backends are thin async HTTP clients on top of it Mesa (no vendor SDKs). The HTTP server moves to the optional `server` extra (`fastapi` + `uvicorn`).
- `Recorder` now keeps an in-memory entry cache (`load()` populates it from SQLite; `label()` updates the in-DB + cache copy) so `pending` / drift / label suggestions work without reopening the log.
- `RoutedTydex` accepts a `min_confidence` per call, and `RoutedTydexServer` wires `PaperQuestion.min_confidence` through so escalation is actually reachable via the HTTP API.
- Fix `tydex` CLI: `ask` runs the async decision path through `asyncio.run` (no more `RuntimeWarning: coroutine never awaited` on non-ask commands).

## [0.1.3] - 2026-09-22

### Added
- `tydex --version` CLI flag and `tydex.__version__` package attribute (single version source via `importlib.metadata`).
- PyPI `keywords` metadata (llm, decision-engine, calibration, probability, choice, score, noul, routing).

### Changed
- `data/tickets.jsonl` expanded from 40 to 60 labeled samples (24 choice, 21 noul, 15 score).
- README: refreshed bench results table (gemma4:31b / Ollama cloud), new Contributing section, updated test count.
- Added `CHANGELOG.md`.

## [0.1.2] - 2026-09-22

### Changed
- README badges (PyPI version / Python versions / format / license / CI); dropped the stale GitHub release badge.

## [0.1.1] - 2026-09-22

### Changed
- Split the single `openai-compatible` provider into `openai_compatible_cloud` (default endpoint `https://api.openai.com/v1`, `OPENAI_BASE_URL` override) and `openai_compatible_local` (default `http://localhost:8000/v1`, `OLLAMA_HOST` override).
- `--provider auto` now maps `OLLAMA_API_KEY` → `openai_compatible_cloud` instead of the ambiguous legacy name.
- Added `.env.example` with every supported environment variable (also documented in README).

## [0.1.0] - 2026-09-22

### Added
- Initial open-source release: typed decision primitives (`choice`/`score`/`noul`) with probabilities from token logprobs or self-estimated JSON.
- Open/Anthropic-compatible, Ollama, and Mock backends over stdlib HTTP (no third-party runtime dependencies).
- Temperature scaling (ECE-driven tuning), isotonic (PAV) recalibration with identity blend, and per-primitive calibration system.
- Confident escalation routing (`RoutedTydex`, `Tier`, `RequiresHuman`) and a feedback loop / `AutoCalibrator`.
- HTTP API (`/evaluate`, `/label`, `/refit`, `/calibration`, `/health`, `/openapi.json`) with optional bearer/X-Api-Key auth and CORS.
- CLI (`tydex ask`, `tydex providers`), labeled benchmark dataset, Dockerfile, CI, and packaging.