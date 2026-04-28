"""Tiny OpenRouter chat-completions client."""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Optional


def build_messages(system_prompt: str, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Put the system prompt before the current conversation history.

    OpenRouter follows the OpenAI-style role set (system/user/assistant/tool).
    Internally we may store additional roles (e.g. "verifier") for orchestration
    and map them to a supported role when sending.
    """

    mapped_history: list[dict[str, Any]] = []
    for m in history:
        role = m.get("role")
        if role == "verifier":
            mapped_history.append({"role": "user", "content": m.get("content", "")})
        else:
            mapped_history.append(m)

    return [{"role": "system", "content": system_prompt}] + mapped_history


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


def validate_chat_response(resp_json: dict[str, Any]) -> dict[str, Any]:
    """Return the first assistant message or raise a clear API-shape error."""

    if "error" in resp_json:
        raise ValueError(f"OpenRouter error: {resp_json['error']}")

    choices = resp_json.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError(f"OpenRouter returned no choices: {resp_json}")

    msg = choices[0].get("message")
    if not isinstance(msg, dict):
        raise ValueError(f"OpenRouter returned no message: {resp_json}")

    return msg


def call_openrouter(payload: dict[str, Any], api_key: str, base_url: str) -> dict[str, Any]:
    """Send one chat request to OpenRouter and return parsed JSON."""

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


def parse_assistant_text(resp_json: dict[str, Any]) -> str:
    """Extract assistant text from an OpenRouter response."""

    try:
        return validate_chat_response(resp_json)["content"]
    except Exception as e:  # noqa: BLE001 - clear beginner-facing error
        raise ValueError(f"Unexpected response shape from OpenRouter: {e}") from e
