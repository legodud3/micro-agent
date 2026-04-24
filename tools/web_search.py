"""Tavily web-search tool."""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

MAX_RESULTS = 5
MAX_SNIPPET_CHARS = 500


def web_search_tool_definition() -> dict[str, Any]:
    """OpenAI-style schema that tells the model this tool exists."""

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


def tavily_web_search(query: str, max_results: int = 5, dry_run: bool = False) -> dict[str, Any]:
    """Call Tavily search and return small normalized results."""

    max_results = max(1, min(max_results, MAX_RESULTS))

    if dry_run:
        return {
            "query": query,
            "results": [],
            "note": "(dry-run) would call Tavily.",
        }

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("Missing TAVILY_API_KEY in environment.")

    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
    }

    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url="https://api.tavily.com/search",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read().decode("utf-8")
        resp = json.loads(raw)

    results_out: list[dict[str, str]] = []
    for item in resp.get("results", []) or []:
        results_out.append(
            {
                "title": str(item.get("title", "")),
                "url": str(item.get("url", "")),
                "snippet": str(
                    item.get("content") or item.get("snippet") or item.get("description") or ""
                )[:MAX_SNIPPET_CHARS],
            }
        )

    return {
        "query": query,
        "results": results_out,
    }
