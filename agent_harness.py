"""Minimal OpenRouter terminal chat agent with Tavily web search.

This file owns terminal UX only:
- read one user input at a time
- route slash commands locally
- route normal chat messages through the model/tool loop
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Optional

from config_loader import load_config, load_system_prompt, parse_env_file, write_config
from openrouter_client import (
    build_messages,
    build_request_payload,
    call_openrouter,
    parse_assistant_text,
    validate_chat_response,
)
from tool_loop import parse_tool_call_arguments, parse_tool_calls, run_assistant_with_tools
from tools.registry import get_tool_summaries
from models_registry import get_model_summaries
from tools.web_search import tavily_web_search, web_search_tool_definition


def should_exit(user_text: str) -> bool:
    """Decide whether the user wants to quit."""

    t = user_text.strip().lower()
    return t in {"exit", "quit", "/exit", "/quit"}


def setup_line_editing() -> None:
    """Enable nicer terminal editing when readline is available."""

    try:
        import readline  # noqa: F401
    except ImportError:
        pass


def print_intro() -> None:
    """Print a tiny startup intro."""

    print("micro-agent v0.2")
    print("OpenRouter chat with Tavily web search.")
    print("Use --trace to watch model/tool iterations.")
    print("Type 'exit' or 'quit' to stop.")
    print("Type '/' to list slash commands.\n")


def parse_slash_command(user_text: str) -> tuple[str, str]:
    """Parse slash-command text into command and argument pieces."""

    # Non-command user messages go through the normal chat path.
    t = user_text.strip()
    if not t.startswith("/"):
        return "", ""

    # The first whitespace-delimited token is the command; the rest is its argument.
    parts = t.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""
    return cmd, arg


def slash_commands_text() -> str:
    """Format the list of supported slash commands."""

    # Keep this list short: slash commands are terminal UX, not model tools.
    return "\n".join(
        [
            "Slash commands:",
            "- /tool — list tools the model can call",
            "- /model — list 10-15 live OpenRouter text/coding/agentic models",
            "- /model set <id> — set active model and persist to config.json",
            "- /help — print docs/help.md",
            "- /exit or /quit — quit the chat",
        ]
    )


def tools_list_text() -> str:
    """Format the list of model tools for /tool."""

    # Tool names/descriptions come from the registry so /tool matches model tools.
    tools = get_tool_summaries()
    if not tools:
        return "No tools are currently registered."

    lines = ["Model tools:"]
    for t in tools:
        name = t.get("name", "")
        desc = t.get("description", "")
        lines.append(f"- {name}: {desc}")
    return "\n".join(lines)


def model_list_text(*, cfg: dict[str, Any], api_key: Optional[str], base_url: str, limit: int = 15) -> str:
    """Render a short model list from the live OpenRouter registry (with fallback)."""

    models = get_model_summaries(base_url, api_key, limit=limit)
    if not models:
        return "No models available."

    current = (cfg.get("model") or "").lower().strip()
    lines = ["Models (live):"]
    for m in models:
        mid = m.get("id") or m.get("name") or "(unknown)"
        desc = m.get("description") or ""
        tag = " (current)" if current and current == str(mid).lower().strip() else ""
        lines.append(f"- {mid}{tag} — {desc}")
    return "\n".join(lines)


def try_set_model(
    *,
    cfg: dict[str, Any],
    api_key: Optional[str],
    base_url: str,
    name_or_id: str,
    limit: int = 15,
) -> str:
    """Try to set cfg['model'] to a live model id, persist to config.json, and report status."""

    wanted = name_or_id.strip().lower()
    if not wanted:
        return "Usage: /model set <id>\n\n" + model_list_text(cfg=cfg, api_key=api_key, base_url=base_url, limit=limit)

    models = get_model_summaries(base_url, api_key, limit=limit)
    # Find case-insensitive match by id or name
    matched_id: Optional[str] = None
    for m in models:
        mid = str(m.get("id") or "").strip()
        mname = str(m.get("name") or "").strip()
        if wanted == mid.lower() or (mname and wanted == mname.lower()):
            matched_id = mid or mname
            break

    if not matched_id:
        return f"Model not found: {name_or_id}\n\n" + model_list_text(cfg=cfg, api_key=api_key, base_url=base_url, limit=limit)

    cfg["model"] = matched_id
    write_config(cfg, path="config.json")
    return f"Active model set to: {matched_id} (persisted to config.json)"


def load_help_md(path: str = "docs/help.md") -> str:
    """Load the local help document used by /help."""

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Missing {path}. Create docs/help.md (required for /help)."
        )

    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip("\n")



def handle_slash_command(
    user_text: str,
    *,
    cfg: dict[str, Any],
    api_key: str | None,
    base_url: str,
    dry_run: bool,
    trace: bool,
) -> Optional[str]:
    """Handle slash commands locally and return output text when handled."""

    cmd, arg = parse_slash_command(user_text)
    if not cmd:
        return None

    # A bare slash is a command discovery shortcut.
    if cmd == "/":
        return slash_commands_text()

    # /tool shows user-visible tools only; it does not alter model/tool state.
    if cmd == "/tool":
        return tools_list_text()

    # /model: list or set the active model via live OpenRouter registry.
    if cmd == "/model":
        a = arg.strip()
        if not a:
            return model_list_text(cfg=cfg, api_key=api_key, base_url=base_url, limit=15)
        if a.lower().startswith("set "):
            return try_set_model(
                cfg=cfg,
                api_key=api_key,
                base_url=base_url,
                name_or_id=a[4:].strip(),
                limit=15,
            )
        # Shorthand: "/model <id>" means set directly
        return try_set_model(
            cfg=cfg,
            api_key=api_key,
            base_url=base_url,
            name_or_id=a,
            limit=15,
        )

    # /help is intentionally simple: print docs/help.md and return to chat.
    if cmd == "/help":
        return load_help_md()

    # Unknown slash commands are handled locally so they do not pollute chat history.
    if cmd.startswith("/"):
        return f"Unknown command: {cmd}\n\n{slash_commands_text()}"

    return None


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

        # Slash commands are local terminal controls, not normal chat messages.
        slash_out = handle_slash_command(
            user_text,
            cfg=cfg,
            api_key=api_key,
            base_url=base_url,
            dry_run=dry_run,
            trace=trace,
        )
        if slash_out is not None:
            print(slash_out)
            continue

        # Normal chat messages enter conversation history and can trigger model tools.
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

    parser = argparse.ArgumentParser(
        description="OpenRouter chat agent with Tavily web search"
    )
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
