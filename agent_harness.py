"""Minimal OpenRouter terminal chat harness (Python stdlib only).

Design goals (per your request):
- Keep the code small.
- Keep it modular: small functions you can read.
- No tools yet: just chat.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from typing import Any


# -----------------------------
# ELI5 helpers: configuration
#.env
#  → secret API key
#
#config.json
#  → model and settings#
#
#system_prompt.txt
#  → assistant instructions

# -----------------------------

def parse_env_file(path: str = ".env") -> None:
    """Read KEY=VALUE lines from a .env file and put them into os.environ.

    This is intentionally tiny (stdlib-only). It supports:
    - blank lines
    - lines starting with #
    - simple KEY=VALUE assignments
    """

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
    """Load config.json and return a dict with defaults filled in."""

    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing {path}. Create it or adjust the path.")

    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Provide a couple safe defaults so config changes are easy.
    cfg.setdefault("temperature", 0.7)
    cfg.setdefault("max_tokens", 800)
    cfg.setdefault(
        "base_url", "https://openrouter.ai/api/v1/chat/completions"
    )
    cfg.setdefault("model", None)

    if not cfg.get("model"):
        raise ValueError("config.json must include a non-empty 'model' field.")

    return cfg


def load_system_prompt(path: str = "system_prompt.txt") -> str:
    """Load the system prompt text as a single string."""

    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing {path}. Create it.")

    with open(path, "r", encoding="utf-8") as f:
        # Keep newlines so the model sees the exact 5-line text.
        return f.read().strip("\n")


# -----------------------------
# ELI5 helpers: chat building. Package up the conversation into the format OpenRouter expects
# Functions
# 1. build_messages
# 2. build_request_payload
# -----------------------------

def build_messages(system_prompt: str, history: list[dict[str, str]], user_text: str) -> list[dict[str, str]]:
    """Create the OpenRouter `messages` array for ONE request.

    - The system message goes first.
    - Then we replay prior turns from `history`.
    - Then we add the newest user message at the end.
    """

    return (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": user_text}]
    )


def build_request_payload(cfg: dict[str, Any], messages: list[dict[str, str]]) -> dict[str, Any]:
    """Build the JSON payload to send to OpenRouter."""

    return {
        "model": cfg["model"],
        "messages": messages,
        "temperature": cfg["temperature"],
        "max_tokens": cfg["max_tokens"],
    }


# -----------------------------
# ELI5 helpers: response parsing
# -----------------------------

def parse_assistant_text(resp_json: dict[str, Any]) -> str:
    """Extract assistant text from an OpenRouter chat completion response.

    Expected shape (simplified):
    {
      "choices": [
        {"message": {"content": "..."}}
      ]
    }
    """

    try:
        return resp_json["choices"][0]["message"]["content"]
    except Exception as e:  # noqa: BLE001 - want a clear error for humans
        raise ValueError(f"Unexpected response shape from OpenRouter: {e}") from e


# -----------------------------
# ELI5 helpers: network call
# -----------------------------

def call_openrouter(payload: dict[str, Any], api_key: str, base_url: str) -> dict[str, Any]:
    """Send the chat completion request to OpenRouter and return parsed JSON."""

    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url=base_url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read().decode("utf-8")
        return json.loads(raw)


def call_openrouter_or_dry_run(
    payload: dict[str, Any],
    api_key: str | None,
    base_url: str,
    dry_run: bool,
) -> str:
    """Wrapper so tests/manual use can avoid network."""

    if dry_run:
        return "(dry-run) I would call OpenRouter here."

    if not api_key:
        raise ValueError("Missing OPENROUTER_API_KEY in environment.")

    resp_json = call_openrouter(payload, api_key=api_key, base_url=base_url)
    return parse_assistant_text(resp_json)


# -----------------------------
# Terminal loop
# -----------------------------

def should_exit(user_text: str) -> bool:
    """Decide whether the user wants to quit."""

    t = user_text.strip().lower()
    return t in {"exit", "quit"}


def run_chat(dry_run: bool = False) -> int:
    """Run the terminal chat loop."""

    # Load .env first (if present), then config/prompt.
    parse_env_file(".env")
    cfg = load_config("config.json")
    system_prompt = load_system_prompt("system_prompt.txt")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    base_url = cfg["base_url"]

    history: list[dict[str, str]] = []

    print("Chat agent ready. Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            user_text = input("> ")
        except EOFError:
            print("\nBye.")
            return 0

        if should_exit(user_text):
            print("Bye.")
            return 0

        messages = build_messages(system_prompt, history, user_text)
        payload = build_request_payload(cfg, messages)

        assistant_text = call_openrouter_or_dry_run(
            payload=payload,
            api_key=api_key,
            base_url=base_url,
            dry_run=dry_run,
        )

        print(assistant_text)
        print()  # blank line between turns

        # Keep history across turns.
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": assistant_text})


def main(argv: list[str]) -> int:
    """CLI entry point."""

    parser = argparse.ArgumentParser(description="Minimal OpenRouter chat agent")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not call the network; return a dummy assistant message.",
    )
    args = parser.parse_args(argv)
    return run_chat(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
