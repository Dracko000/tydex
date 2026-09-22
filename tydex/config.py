from __future__ import annotations

import os


def load_env(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
            elif ":" in line:
                key, _, val = line.partition(":")
            else:
                continue
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and val:
                os.environ.setdefault(key, val)


def env_api_key(*names: str) -> str | None:
    load_env()
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None