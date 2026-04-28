"""Load local config files for the chat agent."""

from __future__ import annotations

import json
import os
from typing import Any


def write_config(cfg: dict[str, Any], path: str = "config.json") -> None:
    """Persist the config dict back to JSON (pretty-printed)."""

    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")


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
    """Load config.json and fill in small defaults.

    New schema (recommended):
    {
      "base_url": "...",
      "micro_agent": {"model": "...", "temperature": 0.7, "max_tokens": 8000},
      "verifier": {"model": "...", "temperature": 0.2, "max_tokens": 800}
    }

    Legacy schema (flat): {"model": "...", "temperature": ..., "max_tokens": ...}
    is automatically mapped to micro_agent, and verifier defaults to the same model.
    """

    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing {path}. Create it or adjust the path.")

    with open(path, "r", encoding="utf-8") as f:
        raw_cfg = json.load(f)

    base_url = raw_cfg.get("base_url") or "https://openrouter.ai/api/v1/chat/completions"

    micro_agent = raw_cfg.get("micro_agent")
    verifier = raw_cfg.get("verifier")

    # Backward compatibility: map legacy flat keys to micro_agent.
    if micro_agent is None and "model" in raw_cfg:
        micro_agent = {
            "model": raw_cfg.get("model"),
            "temperature": raw_cfg.get("temperature"),
            "max_tokens": raw_cfg.get("max_tokens"),
        }

    micro_agent = micro_agent or {}
    verifier = verifier or {}

    micro_agent.setdefault("temperature", 0.7)
    micro_agent.setdefault("max_tokens", 800)

    micro_model = micro_agent.get("model")
    if not micro_model:
        raise ValueError("config.json must include micro_agent.model (or legacy flat 'model').")

    # Defaults for verifier. We keep it intentionally smaller than the main model.
    verifier.setdefault("model", micro_model)
    verifier.setdefault("temperature", 0.2)
    verifier.setdefault("max_tokens", 800)

    return {
        "base_url": base_url,
        "micro_agent": micro_agent,
        "verifier": verifier,
    }


def load_system_prompt(path: str = "system_prompt.txt") -> str:
    """Load the system prompt text as one string."""

    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing {path}. Create it.")

    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip("\n")
