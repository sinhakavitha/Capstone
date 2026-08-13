import json
import os
import urllib.request

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

def call_llm(prompt: str) -> str:
    """Optional real-LLM path (MOCK_LLM=0), using Groq's free-tier API."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        # Fail loudly rather than silently falling back to mock output —
        # this function is only ever called when MOCK_LLM=0 was chosen on purpose.
        raise RuntimeError(
            "GROQ_API_KEY is not set. This code path only runs when MOCK_LLM=0, "
            "which is an optional, ungraded extension."
        )

    body = json.dumps(
        {
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
    ).encode()

    request = urllib.request.Request(
        GROQ_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    return payload["choices"][0]["message"]["content"]
