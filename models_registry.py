"""Live model registry for OpenRouter (with stdlib-only HTTP and caching).

- Fetches latest models from OpenRouter (derived from cfg["base_url"]).
- Filters to text/coding/agentic models (excludes audio/video/image-like).
- Returns compact summaries: {id, name, description}.
- Caches results for a short TTL to avoid repeated network calls.
- Falls back to a small static list on errors.
"""

from __future__ import annotations

import json
import time
import urllib.request
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlunparse

# TTL for caching live model list (seconds)
_CACHE_TTL = 600  # 10 minutes
_cache: Dict[str, Any] = {"ts": 0.0, "models": []}

# Substrings that hint at non-text modalities we want to exclude.
_EXCLUDE_HINTS = {
    "image", "vision", "video", "audio", "speech", "multimodal",
}
# Substrings that hint at text/coding/agentic. We only use these as a mild boost if needed.
_INCLUDE_HINTS = {"text", "code", "coding", "agent", "agentic", "chat"}


def _derive_models_url(base_url: str) -> str:
    """Derive the OpenRouter models endpoint URL from a chat-completions base URL.

    Typical base_url example: https://openrouter.ai/api/v1/chat/completions
    We turn it into:           https://openrouter.ai/api/v1/models
    """

    p = urlparse(base_url)
    # Try to keep scheme+netloc, preserve "/api/v1" prefix if present, then append "/models".
    path = p.path
    idx = path.find("/api/")
    if idx != -1:
        # Keep up to the version segment, then /models
        # E.g., /api/v1/chat/completions -> /api/v1/models
        prefix = path[: path.find("/", idx + 5)]  # after "/api/"
        if not prefix:  # fallback
            new_path = "/api/v1/models"
        else:
            new_path = f"{prefix}/models"
    else:
        # Fallback to /models at root
        new_path = "/models"

    return urlunparse((p.scheme, p.netloc, new_path, "", "", ""))


def _fetch_live_models(base_url: str, api_key: Optional[str]) -> List[Dict[str, Any]]:
    """Fetch raw model list from OpenRouter models endpoint.

    Expected (simplified) response:
    {
      "data": [
        {"id": "provider/model", "name": "...", "description": "...", ...},
        ...
      ]
    }
    """

    url = _derive_models_url(base_url)
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(url=url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode("utf-8")
        data = json.loads(raw)

    items = data.get("data") or data.get("models") or []
    if not isinstance(items, list):
        return []
    return items


def _looks_like_text_model(rec: Dict[str, Any]) -> bool:
    """Heuristic filter: include text/coding/agentic, exclude audio/video/image.

    Uses id/name/description to decide. Conservative: if we see clear multimedia hints, exclude.
    """

    fields = []
    for k in ("id", "name", "description"):
        v = rec.get(k)
        if isinstance(v, str):
            fields.append(v.lower())

    blob = " ".join(fields)

    # Exclude if any hard hint is present
    if any(h in blob for h in _EXCLUDE_HINTS):
        return False

    # Prefer if we see helpful include hints, otherwise still allow (default text)
    # Many text models won't explicitly say "text".
    return True


def _summarize(rec: Dict[str, Any]) -> Dict[str, str]:
    mid = str(rec.get("id") or rec.get("name") or "unknown-model")
    name = str(rec.get("name") or mid)
    desc = str(rec.get("description") or "")
    if not desc:
        # Construct a tiny, safe default description.
        desc = "Text/coding/agentic model"
    return {"id": mid, "name": name, "description": desc}


def _fallback_models() -> List[Dict[str, str]]:
    """Static fallback list (12 entries)."""
    return [
        {"id": "openrouter/auto", "name": "openrouter/auto", "description": "Auto-selects a capable text model"},
        {"id": "anthropic/claude-3-haiku", "name": "anthropic/claude-3-haiku", "description": "Fast Claude 3 for text/coding"},
        {"id": "anthropic/claude-3-5-sonnet", "name": "anthropic/claude-3-5-sonnet", "description": "Claude 3.5 Sonnet for advanced text"},
        {"id": "openai/gpt-4o-mini", "name": "openai/gpt-4o-mini", "description": "Fast GPT-4-class mini for text"},
        {"id": "google/gemini-1.5-flash", "name": "google/gemini-1.5-flash", "description": "Gemini Flash for quick text tasks"},
        {"id": "google/gemini-1.5-pro", "name": "google/gemini-1.5-pro", "description": "Gemini Pro for stronger reasoning"},
        {"id": "mistralai/mistral-nemo", "name": "mistralai/mistral-nemo", "description": "Mistral Nemo text/coding"},
        {"id": "deepseek/deepseek-chat", "name": "deepseek/deepseek-chat", "description": "DeepSeek chat/coding"},
        {"id": "meta-llama/llama-3.1-8b-instruct", "name": "meta-llama/llama-3.1-8b-instruct", "description": "Llama 3.1 8B Instruct"},
        {"id": "meta-llama/llama-3.1-70b-instruct", "name": "meta-llama/llama-3.1-70b-instruct", "description": "Llama 3.1 70B Instruct"},
        {"id": "cohere/command-r", "name": "cohere/command-r", "description": "Cohere Command-R for text/coding"},
        {"id": "qwen/qwen2.5-7b-instruct", "name": "qwen/qwen2.5-7b-instruct", "description": "Qwen 2.5 7B Instruct"},
    ]


def get_model_summaries(base_url: str, api_key: Optional[str], limit: int = 15) -> List[Dict[str, str]]:
    """Return up to `limit` latest text/coding/agentic model summaries.

    Falls back to a static list on errors.
    Results are cached briefly to avoid frequent network calls.
    """

    # Cache check
    now = time.time()
    if _cache["models"] and (now - _cache["ts"]) < _CACHE_TTL:
        # Return a sliced copy so callers can't mutate our cache
        return list(_cache["models"])[:limit]

    models: List[Dict[str, str]] = []
    try:
        raw = _fetch_live_models(base_url, api_key)
        filtered = [r for r in raw if _looks_like_text_model(r)]
        summarized = [_summarize(r) for r in filtered]
        # Keep order from API; assume it's recent-first. If not, we could sort by recency fields here.
        models = summarized
        if not models:
            models = _fallback_models()
    except Exception:
        models = _fallback_models()

    # Update cache
    _cache["models"] = models
    _cache["ts"] = now
    return list(models)[:limit]
