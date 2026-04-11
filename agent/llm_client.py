"""
LLM Client — OpenRouter API Wrapper
====================================
Handles communication with the LLM (Nemotron via OpenRouter).
Supports JSON mode for structured tool calls.
"""

import os
import json
import time
import requests
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "nvidia/nemotron-3-super-120b-a12b:free"

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def chat_completion(
    messages: list,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    json_mode: bool = False,
) -> str:
    """
    Send a chat completion request to OpenRouter.

    Args:
        messages: list of {role, content} dicts
        temperature: sampling temperature
        max_tokens: max tokens in response
        json_mode: if True, request JSON response format

    Returns:
        The assistant's response text
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Financial Agent",
    }

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=120,
            )

            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]
                else:
                    return f"[LLM Error] Unexpected response structure: {json.dumps(data)[:300]}"

            elif response.status_code == 429:
                # Rate limited
                wait = RETRY_DELAY * (attempt + 1)
                print(f"  ⏳ Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue

            else:
                error_msg = response.text[:500]
                print(f"  ⚠️ API error ({response.status_code}): {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                return f"[LLM Error] Status {response.status_code}: {error_msg}"

        except requests.exceptions.Timeout:
            print(f"  ⏳ Request timed out. Retry {attempt + 1}/{MAX_RETRIES}...")
            time.sleep(RETRY_DELAY)
            continue

        except requests.exceptions.ConnectionError as e:
            print(f"  ⚠️ Connection error: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                continue
            return f"[LLM Error] Connection failed after {MAX_RETRIES} retries"

    return "[LLM Error] All retries exhausted"


def parse_json_response(response_text: str) -> dict:
    """
    Try to parse a JSON response from the LLM.
    Handles cases where LLM wraps JSON in markdown code blocks.
    """
    text = response_text.strip()

    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

        return {"error": "Failed to parse JSON", "raw": response_text[:500]}
