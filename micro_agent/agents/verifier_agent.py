"""Verifier (QC) sub-agent.

This module is responsible for asking a separate model to judge whether the
main agent's latest draft should be approved or rejected.

It does *not* call tools.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from ..openrouter_client import (
    build_messages,
    build_request_payload,
    call_openrouter,
    validate_chat_response,
)


QC_STATUS_APPROVE = "approve"
QC_STATUS_REJECT = "reject"


def parse_qc_json(text: str) -> dict[str, Any]:
    """Parse verifier JSON output with a small amount of robustness."""

    s = text.strip()
    if not s:
        return {"status": QC_STATUS_REJECT, "issues": ["Empty response"]}

    # Try direct JSON first.
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        # Fall back to extracting the first JSON object in the string.
        # Handle cases where model adds markdown code block markers.
        if s.startswith("```json"):
            s = s[7:]
        if s.startswith("```"):
            s = s[3:]
        if s.endswith("```"):
            s = s[:-3]
        
        start = s.find("{")
        end = s.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Verifier did not return a JSON object")
        obj = json.loads(s[start : end + 1])

    if not isinstance(obj, dict):
        raise ValueError("Verifier JSON must be an object")

    status = obj.get("status")
    if status not in {QC_STATUS_APPROVE, QC_STATUS_REJECT}:
        raise ValueError("Verifier JSON missing/invalid 'status'")

    issues = obj.get("issues")
    if status == QC_STATUS_APPROVE:
        if issues not in (None, [], ""):
            # Be strict: approve should have no issues.
            raise ValueError("Verifier JSON must have empty 'issues' when approved")
        return {"status": QC_STATUS_APPROVE, "issues": []}

    # Reject path
    if issues is None:
        raise ValueError("Verifier JSON missing 'issues' when rejecting")

    if isinstance(issues, str):
        issues_list = [issues] if issues.strip() else []
    elif isinstance(issues, list):
        issues_list = [str(x) for x in issues]
    else:
        raise ValueError("Verifier JSON 'issues' must be a string or list")

    if not issues_list:
        raise ValueError("Verifier JSON must include at least one issue when rejecting")

    return {"status": QC_STATUS_REJECT, "issues": issues_list}


def run_verifier(
    *,
    verifier_cfg: dict[str, Any],
    verifier_system_prompt: str,
    main_system_prompt: str,
    history: list[dict[str, Any]],
    api_key: str | None,
    base_url: str,
    dry_run: bool,
    trace: bool = False,
) -> dict[str, Any]:
    """Run QC verification and return a parsed {status, issues} object."""

    if dry_run:
        return {"status": QC_STATUS_APPROVE, "issues": []}

    if not api_key:
        raise ValueError("Missing OPENROUTER_API_KEY in environment.")

    # Instead of sending the entire raw history, we extract the core components
    # to prevent "Role Bleed" where the verifier starts chatting with the user.
    user_query = ""
    last_assistant_draft = ""
    tool_results = []

    for m in history:
        role = m.get("role")
        if role == "user":
            user_query = m.get("content", "")
        elif role == "assistant":
            last_assistant_draft = m.get("content", "")
        elif role == "tool":
            try:
                # Store the raw content or a summary of the tool result
                tool_results.append(m.get("content", ""))
            except Exception:
                pass

    verifier_history = [
        {
            "role": "user",
            "content": (
                f"MAIN AGENT SYSTEM PROMPT:\n{main_system_prompt}\n\n"
                f"ORIGINAL USER QUERY:\n{user_query}\n\n"
                f"TOOL RESULTS (EVIDENCE):\n{json.dumps(tool_results)}\n\n"
                f"ASSISTANT DRAFT TO VERIFY:\n{last_assistant_draft}"
            ),
        }
    ]

    messages = build_messages(verifier_system_prompt, verifier_history)
    payload = build_request_payload(verifier_cfg, messages, tools=None)

    if trace:
        print("[trace] verifier: calling model")

    resp_json = call_openrouter(payload, api_key=api_key, base_url=base_url)
    if trace:
        print(f"[trace] verifier raw resp: {json.dumps(resp_json)}")

    msg = validate_chat_response(resp_json)
    content = msg.get("content") or ""

    if trace:
        print(f"[trace] verifier response: {repr(content)}")

    try:
        qc = parse_qc_json(content)
    except ValueError as e:
        if trace:
            print(f"[trace] verifier json parse failed: {e}")
        # If the verifier fails to return JSON, we treat it as a rejection so the main agent tries again.
        # (Alternatively, we could approve, but failing safe is usually better).
        qc = {"status": QC_STATUS_REJECT, "issues": [f"Verifier returned invalid format: {content.strip() or 'Empty response'}"]}

    if trace:
        print(f"[trace] verifier: {qc['status']} ({len(qc['issues'])} issue(s))")

    return qc
