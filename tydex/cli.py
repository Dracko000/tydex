from __future__ import annotations

import argparse
import json
import os
import sys
import time
from urllib.error import URLError

from .backends import (
    AnthropicCompatibleBackend,
    MockBackend,
    OllamaBackend,
    OpenAIBackend,
    OpenAICompatibleBackend,
)
from .config import env_api_key
from .core import SchemaError, Tydex

PROVIDERS = ("auto", "openai", "openai_compatible_local", "openai_compatible_cloud", "anthropic", "ollama", "mock")


class CliError(Exception):
    pass


def _auto_provider() -> str:
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OLLAMA_API_KEY"):
        return "openai_compatible_cloud"
    if os.environ.get("OLLAMA_HOST"):
        return "ollama"
    return "mock"


def resolve_backend(
    provider: str,
    *,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    supports_logprobs: bool = True,
):
    provider = _auto_provider() if provider == "auto" else provider
    if provider == "openai":
        model = model or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
        api_key = api_key or env_api_key("OPENAI_API_KEY")
        if not api_key:
            raise CliError("OpenAI needs an API key: set OPENAI_API_KEY or pass --api-key")
        return OpenAIBackend(model=model, api_key=api_key, base_url=base_url)
    if provider == "openai_compatible_local":
        model = model or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
        api_key = api_key or env_api_key("OLLAMA_API_KEY", "OPENAI_API_KEY")
        base_url = base_url or os.environ.get("OLLAMA_HOST") or "http://localhost:8000/v1"
        return OpenAICompatibleBackend(model=model, api_key=api_key, base_url=base_url, supports_logprobs=supports_logprobs)
    if provider == "openai_compatible_cloud":
        model = model or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
        api_key = api_key or env_api_key("OPENAI_API_KEY", "OLLAMA_API_KEY")
        base_url = base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        return OpenAICompatibleBackend(model=model, api_key=api_key, base_url=base_url, supports_logprobs=supports_logprobs)
    if provider == "anthropic":
        model = model or os.environ.get("ANTHROPIC_MODEL") or "claude-3-5-haiku-latest"
        api_key = api_key or env_api_key("ANTHROPIC_API_KEY")
        if not api_key:
            raise CliError("Anthropic needs an API key: set ANTHROPIC_API_KEY or pass --api-key")
        return AnthropicCompatibleBackend(model=model, api_key=api_key, base_url=base_url or "https://api.anthropic.com")
    if provider == "ollama":
        model = model or os.environ.get("OLLAMA_MODEL") or "llama3.1:8b"
        base_url = base_url or os.environ.get("OLLAMA_HOST") or "http://localhost:11434"
        return OllamaBackend(model=model, base_url=base_url)
    if provider == "mock":
        return MockBackend()
    raise CliError(f"unknown provider {provider!r} (expected {'|'.join(PROVIDERS)})")


def cmd_providers(args: argparse.Namespace) -> int:
    names = ("openai", "openai_compatible_local", "openai_compatible_cloud", "anthropic", "ollama", "mock")
    headers = ("provider", "api-key", "endpoint", "model", "configured")
    configured = {
        "openai": env_api_key("OPENAI_API_KEY"),
        "openai_compatible_local": env_api_key("OLLAMA_API_KEY", "OPENAI_API_KEY"),
        "openai_compatible_cloud": env_api_key("OPENAI_API_KEY", "OLLAMA_API_KEY"),
        "anthropic": env_api_key("ANTHROPIC_API_KEY"),
        "ollama": "local",
        "mock": "always",
    }
    models = {
        "openai": os.environ.get("OPENAI_MODEL") or "gpt-4o-mini",
        "openai_compatible_local": os.environ.get("OPENAI_MODEL") or "gpt-4o-mini",
        "openai_compatible_cloud": os.environ.get("OPENAI_MODEL") or "gpt-4o-mini",
        "anthropic": os.environ.get("ANTHROPIC_MODEL") or "claude-3-5-haiku-latest",
        "ollama": os.environ.get("OLLAMA_MODEL") or "llama3.1:8b",
        "mock": "mock",
    }
    endpoints = {
        "openai": "https://api.openai.com/v1",
        "openai_compatible_local": os.environ.get("OLLAMA_HOST") or "http://localhost:8000/v1",
        "openai_compatible_cloud": os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1",
        "anthropic": "https://api.anthropic.com",
        "ollama": os.environ.get("OLLAMA_HOST") or "http://localhost:11434",
        "mock": "-",
    }
    keys = {
        "openai": "OPENAI_API_KEY",
        "openai_compatible_local": "OLLAMA_API_KEY / OPENAI_API_KEY",
        "openai_compatible_cloud": "OPENAI_API_KEY / OLLAMA_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "ollama": "none",
        "mock": "none",
    }
    rows = [
        (name, keys[name], endpoints[name], models[name], "yes" if configured[name] else "no")
        for name in names
    ]
    widths = [max(len(headers[i]), max(len(row[i]) for row in rows)) for i in range(5)]
    print("  ".join(headers[i].ljust(widths[i]) for i in range(5)))
    print("  ".join("-" * widths[i] for i in range(5)))
    for row in rows:
        print("  ".join(row[i].ljust(widths[i]) for i in range(5)))
    print(f"\nauto-detect resolves to: {_auto_provider()}")
    return 0


def _csv(flag: str, raw: str | None) -> list[str]:
    if raw is None:
        raise CliError(f"missing required argument: {flag}")
    items = [item.strip() for item in raw.split(",") if item.strip()]
    if len(items) < 2:
        raise CliError(f"{flag} needs at least 2 comma-separated values")
    return items


def _run(tdex: Tydex, args: argparse.Namespace, state: object):
    start = time.perf_counter()
    if args.type == "choice":
        res_c = tdex.choice(state, _csv("--options", args.options), question=args.question, mode=args.mode, temperature=args.temperature)
        return res_c, "choice", res_c.choice, res_c.probabilities, time.perf_counter() - start
    if args.type == "score":
        res_s = tdex.score(state, _csv("--levels", args.levels), question=args.question, mode=args.mode, temperature=args.temperature)
        return res_s, "score", res_s.score, res_s.probabilities, time.perf_counter() - start
    if not args.statement:
        raise CliError("missing required argument: --statement")
    res_n = tdex.noul(state, args.statement, mode=args.mode, temperature=args.temperature)
    probs = {"true": res_n.probability, "false": round(1.0 - res_n.probability, 6)}
    return res_n, "probability", res_n.bool_value, probs, time.perf_counter() - start


def cmd_ask(args: argparse.Namespace) -> int:
    backend = resolve_backend(
        args.provider,
        model=args.model,
        base_url=args.base_url,
        api_key=args.api_key,
        supports_logprobs=not args.no_logprobs,
    )
    try:
        state = json.loads(args.state) if args.state else {}
    except json.JSONDecodeError as exc:
        raise CliError(f"invalid --state JSON: {exc}") from exc
    tdex = Tydex(backend, model=getattr(backend, "model", args.model or "default"))
    result, key, value, probs, elapsed = _run(tdex, args, state)

    if args.json:
        payload = {
            "provider": args.provider,
            "model": tdex.model,
            "type": args.type,
            key: value,
            "probabilities": probs,
            "confidence": result.confidence,
            "source": result.source,
            "elapsed_s": round(elapsed, 3),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"{args.provider} ({tdex.model}) :: {args.type}  [{result.source}]")
    if args.type == "noul":
        print(f"  probability={result.probability:.3f}  bool_value={value}")
    else:
        print(f"  {key}={value!r}  confidence={result.confidence:.3f}")
    ordered = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
    print("  probs: " + "  ".join(f"{opt}={p:.3f}" for opt, p in ordered))
    print(f"  elapsed={elapsed:.2f}s")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tydex", description="Tydex decision engine CLI: connect to AI providers and run typed primitives.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_providers = sub.add_parser("providers", help="list AI providers with configured status and default models")
    p_providers.set_defaults(func=cmd_providers)

    p_ask = sub.add_parser("ask", help="run a choice/score/noul query against a provider")
    p_ask.add_argument("--provider", choices=PROVIDERS, default="auto", help="provider adapter (default: auto-detect from env)")
    p_ask.add_argument("--model", default=None, help="model name; falls back to provider env/model default")
    p_ask.add_argument("--base-url", default=None, help="override the provider endpoint base URL")
    p_ask.add_argument("--api-key", default=None, help="API key; falls back to provider env key (never echoed)")
    p_ask.add_argument("--no-logprobs", action="store_true", help="force an openai-compatible provider to self-estimate (no token logprobs)")
    p_ask.add_argument("--type", choices=["choice", "score", "noul"], required=True)
    p_ask.add_argument("--state", default="{}", help="JSON object as decision context")
    p_ask.add_argument("--options", default=None, help="comma-separated options (for choice)")
    p_ask.add_argument("--levels", default=None, help="comma-separated ordered levels (for score)")
    p_ask.add_argument("--statement", default=None, help="statement to accept/reject (for noul)")
    p_ask.add_argument("--question", default=None, help="optional instruction; defaults per primitive")
    p_ask.add_argument("--temperature", type=float, default=1.0, help="soften (<1) or sharpen (>1) the distribution")
    p_ask.add_argument("--mode", choices=["auto", "logprobs", "self"], default="auto", help="probability source")
    p_ask.add_argument("--json", action="store_true", help="emit JSON result")
    p_ask.set_defaults(func=cmd_ask)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (CliError, SchemaError, OSError, URLError, KeyboardInterrupt) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"error: invalid model response: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())