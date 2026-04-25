"""Tool registry.

Keeps a single source of truth for:
- which tools the model is allowed to call
- short 1-line descriptions for the user
"""

from __future__ import annotations

from typing import Any

from tools.web_search import web_search_tool_definition


def get_tool_schemas() -> list[dict[str, Any]]:
    """Return OpenAI-style tool schemas to advertise to the model."""

    return [web_search_tool_definition()]


def get_tool_summaries() -> list[dict[str, str]]:
    """Return short user-friendly descriptions of tools."""

    tool = web_search_tool_definition()["function"]
    return [{"name": str(tool["name"]), "description": str(tool["description"])}]
