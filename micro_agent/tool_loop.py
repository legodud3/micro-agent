"""Model -> tool -> model loop."""

from __future__ import annotations

import json
from typing import Any

from .openrouter_client import (
    build_messages,
    build_request_payload,
    call_openrouter,
    validate_chat_response,
)
from .tools.registry import get_tool_schemas
from .tools.web_search import tavily_web_search
from .agents.verifier_agent import QC_STATUS_APPROVE, QC_STATUS_REJECT, run_verifier


def trace_line(enabled: bool, text: str) -> None:
    """Print one trace line when tracing is enabled."""

    if enabled:
        print(f"[trace] {text}")


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
    """Parse tool-call arguments into a dict."""

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


def run_assistant_with_tools(
    *,
    cfg: dict[str, Any],
    system_prompt: str,
    history: list[dict[str, Any]],
    api_key: str | None,
    base_url: str,
    dry_run: bool,
    trace: bool = False,
    max_tool_iterations: int = 50,
    verifier_cfg: dict[str, Any] | None = None,
    verifier_system_prompt: str | None = None,
) -> str:
    """Run OpenRouter with tools, then optionally QC-verify and retry."""

    tools = get_tool_schemas()

    for iteration in range(1, max_tool_iterations + 1):
        trace_line(trace, f"iteration {iteration}: calling model")

        if dry_run:
            content = "(dry-run) Tool-enabled agent: I would answer using web_search if needed."
            history.append({"role": "assistant", "content": content})
            trace_line(trace, f"iteration {iteration}: dry-run final answer")
            return content

        if not api_key:
            raise ValueError("Missing OPENROUTER_API_KEY in environment.")

        messages = build_messages(system_prompt, history)
        payload = build_request_payload(cfg, messages, tools=tools)
        resp_json = call_openrouter(payload, api_key=api_key, base_url=base_url)

        try:
            assistant_msg = validate_chat_response(resp_json)
        except ValueError as e:
            content = f"(OpenRouter returned an error: {e})"
            history.append({"role": "assistant", "content": content})
            trace_line(trace, f"iteration {iteration}: OpenRouter error")
            return content

        tool_calls = parse_tool_calls(resp_json)

        if not tool_calls:
            content = assistant_msg.get("content") or ""
            history.append({"role": "assistant", "content": content})

            # Optional: run the verifier QC and ask the main agent to revise on reject.
            if verifier_cfg and verifier_system_prompt:
                qc = run_verifier(
                    verifier_cfg=verifier_cfg,
                    verifier_system_prompt=verifier_system_prompt,
                    main_system_prompt=system_prompt,
                    history=history,
                    api_key=api_key,
                    base_url=base_url,
                    dry_run=dry_run,
                    trace=trace,
                )

                if qc.get("status") == QC_STATUS_APPROVE:
                    trace_line(trace, f"iteration {iteration}: final answer (verified)")
                    return content

                issues = qc.get("issues") or []
                feedback_text = "Verifier QC rejected. Issues:\n" + "\n".join(
                    f"- {i}" for i in issues
                )
                history.append({"role": "verifier", "content": feedback_text})
                trace_line(trace, f"iteration {iteration}: verifier rejected ({len(issues)} issue(s)); retrying")
                continue

            trace_line(trace, f"iteration {iteration}: final answer")
            return content

        history.append(
            {
                "role": "assistant",
                "content": assistant_msg.get("content") or "",
                "tool_calls": tool_calls,
            }
        )

        trace_line(trace, f"iteration {iteration}: {len(tool_calls)} tool call(s)")

        for tc in tool_calls:
            tool_name = (tc.get("function") or {}).get("name")
            tool_call_id = tc.get("id")
            args = parse_tool_call_arguments(tc)

            trace_line(trace, f"iteration {iteration}: running {tool_name} {args}")

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

            result_count = len(tool_result.get("results", []) or [])
            trace_line(trace, f"iteration {iteration}: {tool_name} returned {result_count} result(s)")

            history.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": json.dumps(tool_result),
                }
            )

    fallback = "(I hit the tool-call iteration limit; I may not have all needed info.)"
    history.append({"role": "assistant", "content": fallback})
    trace_line(trace, f"stopped after {max_tool_iterations} iteration(s)")
    return fallback
