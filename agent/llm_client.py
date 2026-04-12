"""
LLM Client — Groq (primary) + OpenRouter (fallback)
=====================================================
Handles communication with the LLM.
Primary: Groq Llama 3.3 70B (fast, reliable)
Fallback: OpenRouter (legacy)
"""

import os
import json
import time
import requests
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

# Groq config
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# OpenRouter fallback
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def groq_chat_completion(
    messages: list,
    temperature: float = 0.1,
    max_tokens: int = 2048,
    json_mode: bool = False,
) -> str:
    """
    Send a chat completion request to Groq (Llama 3.3 70B).

    Args:
        messages: list of {role, content} dicts
        temperature: sampling temperature (low = deterministic Cypher)
        max_tokens: max tokens in response
        json_mode: if True, request JSON response format

    Returns:
        The assistant's response text
    """
    if not GROQ_API_KEY:
        return "[LLM Error] GROQ_API_KEY not set"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                GROQ_URL,
                headers=headers,
                json=payload,
                timeout=60,
            )

            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]
                else:
                    return f"[LLM Error] Unexpected Groq response: {json.dumps(data)[:300]}"

            elif response.status_code == 429:
                wait = RETRY_DELAY * (attempt + 1)
                print(f"  ⏳ Groq rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue

            else:
                error_msg = response.text[:500]
                print(f"  ⚠️ Groq API error ({response.status_code}): {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                return f"[LLM Error] Groq status {response.status_code}: {error_msg}"

        except requests.exceptions.Timeout:
            print(f"  ⏳ Groq request timed out. Retry {attempt + 1}/{MAX_RETRIES}...")
            time.sleep(RETRY_DELAY)
            continue

        except requests.exceptions.ConnectionError as e:
            print(f"  ⚠️ Groq connection error: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                continue
            return f"[LLM Error] Groq connection failed after {MAX_RETRIES} retries"

    return "[LLM Error] Groq: all retries exhausted"


def chat_completion(
    messages: list,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    json_mode: bool = False,
) -> str:
    """
    Send a chat completion — uses Groq by default, falls back to OpenRouter.

    Args:
        messages: list of {role, content} dicts
        temperature: sampling temperature
        max_tokens: max tokens in response
        json_mode: if True, request JSON response format

    Returns:
        The assistant's response text
    """
    # Prefer Groq if key is available
    if GROQ_API_KEY:
        return groq_chat_completion(messages, temperature, min(max_tokens, 2048), json_mode)

    # Fallback: OpenRouter
    if not OPENROUTER_API_KEY:
        return "[LLM Error] No API key found. Set GROQ_API_KEY or OPENROUTER_API_KEY in .env"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Financial Agent",
    }

    payload = {
        "model": OPENROUTER_MODEL,
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
