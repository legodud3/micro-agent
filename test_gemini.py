import os
import json
import urllib.request

api_key = os.environ.get("OPENROUTER_API_KEY")
url = "https://openrouter.ai/api/v1/chat/completions"

with open("micro_agent/agents/verifier_system_prompt.txt", "r") as f:
    sys_prompt = f.read()

payload = {
    "model": "google/gemini-3.1-flash-lite-preview",
    "messages": [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": "draft: Hormuz stays open."}
    ]
}

req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req) as r:
        resp = json.loads(r.read().decode("utf-8"))
        print(json.dumps(resp, indent=2))
except Exception as e:
    print(e)
    if hasattr(e, "read"):
        print(e.read().decode())
