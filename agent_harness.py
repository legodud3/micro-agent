"""OpenRouter terminal chat agent (Python stdlib only) with a Tavily web-search tool.

Design goals (per your request):
- Keep the code small.
- Keep it modular: small functions you can read.
- No 3rd-party dependencies.

Tool calling loop:
- The model may request a tool via `tool_calls`.
- We execute the tool, append the tool result to `messages`, and ask the model again.
- We stop when the model returns a normal assistant message (no further tool calls) or when
  we hit `max_tool_iterations`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from typing import Any, Optional


# -----------------------------
# ELI5 helpers: configuration
# -----------------------------


def parse_env_file(path: str = ".env") -> None:
    """Read KEY=VALUE lines from a .env file and put them into os.environ."""

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

    cfg.setdefault("temperature", 0.7)
    cfg.setdefault("max_tokens", 800)
    cfg.setdefault("base_url", "https://openrouter.ai/api/v1/chat/completions")
    cfg.setdefault("model", None)

    if not cfg.get("model"):
        raise ValueError("config.json must include a non-empty 'model' field.")

    return cfg


def load_system_prompt(path: str = "system_prompt.txt") -> str:
    """Load the system prompt text as a single string."""

    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing {path}. Create it.")

    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip("\n")


# -----------------------------
# Chat building (kept for tests)
# -----------------------------


def build_messages(
    system_prompt: str,
    history: list[dict[str, str]],
    user_text: str,
) -> list[dict[str, str]]:
    """Create the OpenRouter `messages` array for ONE request."""

    return (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": user_text}]
    )


def build_request_payload(
    cfg: dict[str, Any],
    messages: list[dict[str, Any]],
    tools: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Build the JSON payload to send to OpenRouter."""

    payload: dict[str, Any] = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": cfg["temperature"],
        "max_tokens": cfg["max_tokens"],
    }

    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    return payload


# -----------------------------
# Response parsing (kept for tests)
# -----------------------------


def parse_assistant_text(resp_json: dict[str, Any]) -> str:
    """Extract assistant text from an OpenRouter chat completion response."""

    try:
        return resp_json["choices"][0]["message"]["content"]
    except Exception as e:  # noqa: BLE001 - want a clear error for humans
        raise ValueError(f"Unexpected response shape from OpenRouter: {e}") from e


# -----------------------------
# Tool calling helpers
# -----------------------------


def web_search_tool_definition() -> dict[str, Any]:
    """OpenAI-style tool schema for OpenRouter."""

    return {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the public web for up-to-date information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    }


def parse_tool_calls(resp_json: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract tool calls from an OpenRouter response."""

    try:
        msg = resp_json["choices"][0]["message"]
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"Unexpected response shape: {e}") from e

    tool_calls = msg.get("tool_calls")
    if not tool_calls:
        return []
    if not isinstance(tool_calls, list):
        raise ValueError("tool_calls is not a list")
    return tool_calls


def parse_tool_call_arguments(tool_call: dict[str, Any]) -> dict[str, Any]:
    """Parse tool call function arguments JSON into a dict."""

    fn = tool_call.get("function")
    if not isinstance(fn, dict):
        raise ValueError("tool_call.function missing or not an object")

    args_raw = fn.get("arguments")
    if args_raw is None:
        return {}

    if isinstance(args_raw, dict):
        return args_raw

    if not isinstance(args_raw, str):
        raise ValueError("tool_call.function.arguments must be str or object")

    try:
        return json.loads(args_raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Tool call arguments are not valid JSON: {e}") from e


# -----------------------------
# Network call helpers
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


# -----------------------------
# Tavily web search tool
# -----------------------------


def tavily_web_search(query: str, max_results: int = 5, dry_run: bool = False) -> dict[str, Any]:
    """Call Tavily's search endpoint and normalize results."""

    if dry_run:
        return {
            "query": query,
            "results": [],
            "note": "(dry-run) would call Tavily.",
        }

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("Missing TAVILY_API_KEY in environment.")

    # Tavily docs (commonly used): POST https://api.tavily.com/search
    # Body typically includes: { api_key, query, max_results, search_depth }
    url = "https://api.tavily.com/search"

    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
    }

    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url=url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read().decode("utf-8")
        resp = json.loads(raw)

    # Normalize to a small list.
    results_out: list[dict[str, str]] = []
    for item in resp.get("results", []) or []:
        results_out.append(
            {
                "title": str(item.get("title", "")),
                "url": str(item.get("url", "")),
                "snippet": str(
                    item.get("content") or item.get("snippet") or item.get("description") or ""
                ),
            }
        )

    return {
        "query": query,
        "results": results_out,
    }


# -----------------------------
# Tool loop over assistant calls
# -----------------------------


def run_assistant_with_tools(
    *,
    cfg: dict[str, Any],
    system_prompt: str,
    history: list[dict[str, Any]],
    api_key: str | None,
    base_url: str,
    dry_run: bool,
    max_tool_iterations: int = 5,
) -> str:
    """Run OpenRouter until a final assistant message is produced."""

    tools = [web_search_tool_definition()]

    for iteration in range(max_tool_iterations):
        if dry_run:
            content = "(dry-run) Tool-enabled agent: I would answer using web_search if needed."
            history.append({"role": "assistant", "content": content})
            return content

        if not api_key:
            raise ValueError("Missing OPENROUTER_API_KEY in environment.")

        messages = [{"role": "system", "content": system_prompt}] + history
        payload = build_request_payload(cfg, messages, tools=tools)
        resp_json = call_openrouter(payload, api_key=api_key, base_url=base_url)

        assistant_msg: dict[str, Any] = resp_json["choices"][0]["message"]
        tool_calls = parse_tool_calls(resp_json)

        # No tool calls -> final assistant message.
        if not tool_calls:
            content = assistant_msg.get("content") or ""
            history.append({"role": "assistant", "content": content})
            return content

        # Tool calls present -> execute them and append tool results.
        history.append(
            {
                "role": "assistant",
                "content": assistant_msg.get("content") or "",
                "tool_calls": tool_calls,
            }
        )

        for tc in tool_calls:
            tool_name = (tc.get("function") or {}).get("name")
            tool_call_id = tc.get("id")
            args = parse_tool_call_arguments(tc)

            try:
                if tool_name == "web_search":
                    tool_result = tavily_web_search(
                        query=str(args.get("query", "")),
                        max_results=int(args.get("max_results", 5)),
                        dry_run=dry_run,
                    )
                else:
                    tool_result = {"error": f"Unknown tool: {tool_name}"}
            except Exception as e:  # noqa: BLE001
                tool_result = {"error": f"Tool execution failed: {e}"}

            history.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": json.dumps(tool_result),
                }
            )

    # Safety stop.
    fallback = "(I hit the tool-call iteration limit; I may not have all needed info.)"
    history.append({"role": "assistant", "content": fallback})
    return fallback


# -----------------------------
# Terminal loop
# -----------------------------


def should_exit(user_text: str) -> bool:
    """Decide whether the user wants to quit."""

    t = user_text.strip().lower()
    return t in {"exit", "quit"}


def run_chat(dry_run: bool = False, max_tool_iterations: int = 5) -> int:
    """Run the terminal chat loop."""

    parse_env_file(".env")
    cfg = load_config("config.json")
    system_prompt = load_system_prompt("system_prompt.txt")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    base_url = cfg["base_url"]

    history: list[dict[str, Any]] = []

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

        # Add user message.
        history.append({"role": "user", "content": user_text})

        # Model/tool loop until we get a final assistant message.
        assistant_text = run_assistant_with_tools(
            cfg=cfg,
            system_prompt=system_prompt,
            history=history,
            api_key=api_key,
            base_url=base_url,
            dry_run=dry_run,
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
        "--max-tool-iterations",
        type=int,
        default=5,
        help="Safety cap for how many tool-call iterations the model can request.",
    )
    args = parser.parse_args(argv)

    return run_chat(dry_run=args.dry_run, max_tool_iterations=args.max_tool_iterations)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
