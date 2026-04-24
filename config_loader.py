"""Load local config files for the chat agent."""

from __future__ import annotations

import json
import os
from typing import Any


def parse_env_file(path: str = ".env") -> None:
    """Read KEY=VALUE lines from a .env file into os.environ."""

    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def load_config(path: str = "config.json") -> dict[str, Any]:
    """Load config.json and fill in small defaults."""

    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing {path}. Create it or adjust the path.")

    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    cfg.setdefault("temperature", 0.7)
    cfg.setdefault("max_tokens", 800)
    cfg.setdefault("base_url", "https://openrouter.ai/api/v1/chat/completions")
    cfg.setdefault("model", None)

    if not cfg.get("model"):
        raise ValueError("config.json must include a non-empty 'model' field.")

    return cfg


def load_system_prompt(path: str = "system_prompt.txt") -> str:
    """Load the system prompt text as one string."""

    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing {path}. Create it.")

    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip("\n")
