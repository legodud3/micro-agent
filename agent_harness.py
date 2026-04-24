"""Minimal OpenRouter terminal chat agent with Tavily web search."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from config_loader import load_config, load_system_prompt, parse_env_file
from openrouter_client import (
    build_messages,
    build_request_payload,
    call_openrouter,
    parse_assistant_text,
    validate_chat_response,
)
from tool_loop import parse_tool_call_arguments, parse_tool_calls, run_assistant_with_tools
from tools.web_search import tavily_web_search, web_search_tool_definition


def should_exit(user_text: str) -> bool:
    """Decide whether the user wants to quit."""

    t = user_text.strip().lower()
    return t in {"exit", "quit"}


def setup_line_editing() -> None:
    """Enable nicer terminal editing when readline is available."""

    try:
        import readline  # noqa: F401
    except ImportError:
        pass


def print_intro() -> None:
    """Print a tiny startup intro."""

    print("micro-agent v0.1")
    print("OpenRouter chat with Tavily web search.")
    print("Use --trace to watch model/tool iterations.")
    print("Type 'exit' or 'quit' to stop.\n")


def run_chat(
    dry_run: bool = False,
    trace: bool = False,
    max_tool_iterations: int = 5,
) -> int:
    """Run the terminal chat loop."""

    parse_env_file(".env")
    cfg = load_config("config.json")
    system_prompt = load_system_prompt("system_prompt.txt")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    base_url = cfg["base_url"]
    history: list[dict[str, Any]] = []

    setup_line_editing()

    print_intro()

    while True:
        try:
            user_text = input("> ")
        except EOFError:
            print("\nBye.")
            return 0

        if should_exit(user_text):
            print("Bye.")
            return 0

        history.append({"role": "user", "content": user_text})

        assistant_text = run_assistant_with_tools(
            cfg=cfg,
            system_prompt=system_prompt,
            history=history,
            api_key=api_key,
            base_url=base_url,
            dry_run=dry_run,
            trace=trace,
            max_tool_iterations=max_tool_iterations,
        )

        print(assistant_text)
        print()


def main(argv: list[str]) -> int:
    """CLI entry point."""

    parser = argparse.ArgumentParser(description="OpenRouter chat agent with Tavily web search")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not call the network; return a dummy assistant message.",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Print model/tool loop iterations.",
    )
    parser.add_argument(
        "--max-tool-iterations",
        type=int,
        default=5,
        help="Safety cap for how many tool-call iterations the model can request.",
    )
    args = parser.parse_args(argv)

    return run_chat(
        dry_run=args.dry_run,
        trace=args.trace,
        max_tool_iterations=args.max_tool_iterations,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
