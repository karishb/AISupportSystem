"""LLM integration via Groq (free tier) with key rotation and OpenAI fallback.

Uses Groq's Llama 3.3 70B for:
- Ticket categorization + sentiment in a single call (saves API quota)
- Response generation (with RAG context from similar tickets)

Key rotation: cycles through multiple Groq API keys when rate-limited.
Rate limiting: auto-throttles to stay within Groq free tier (30 req/min per key).
"""
import json
import time
import threading
from typing import Dict, Optional
from backend.config import GROQ_API_KEYS, OPENAI_API_KEY, GROQ_MODEL, GROQ_BASE_URL

# --- Multi-key client pool ---
_clients = []
_current_key_idx = 0
_key_lock = threading.Lock()
_model = GROQ_MODEL
_provider = "none"

try:
    from openai import OpenAI

    for key in GROQ_API_KEYS:
        _clients.append(OpenAI(api_key=key, base_url=GROQ_BASE_URL))
    if _clients:
        _provider = f"Groq (Llama 3.3 70B) x{len(_clients)} keys"
    elif OPENAI_API_KEY:
        _clients.append(OpenAI(api_key=OPENAI_API_KEY))
        _model = "gpt-4o-mini"
        _provider = "OpenAI (GPT-4o-mini)"
except ImportError:
    pass

# --- Rate limiter (per-key tracking) ---
_key_last_call = {}  # key_idx -> last call timestamp
_key_cooldown = {}   # key_idx -> cooldown until timestamp
_MIN_INTERVAL = 2.2  # seconds between calls per key


def _get_client():
    """Get the next available client, rotating on rate limits."""
    global _current_key_idx
    if not _clients:
        return None, -1

    with _key_lock:
        now = time.time()
        # Try each key, starting from current
        for attempt in range(len(_clients)):
            idx = (_current_key_idx + attempt) % len(_clients)

            # Skip keys in cooldown
            cooldown_until = _key_cooldown.get(idx, 0)
            if now < cooldown_until:
                continue

            # Rate limit per key
            last_call = _key_last_call.get(idx, 0)
            elapsed = now - last_call
            if elapsed < _MIN_INTERVAL:
                time.sleep(_MIN_INTERVAL - elapsed)

            _key_last_call[idx] = time.time()
            _current_key_idx = idx
            return _clients[idx], idx

        # All keys in cooldown — wait for the shortest one
        min_wait = min(_key_cooldown.values()) - now
        if min_wait > 0:
            time.sleep(min(min_wait, 10))
        idx = _current_key_idx
        _key_last_call[idx] = time.time()
        return _clients[idx], idx


def _mark_rate_limited(key_idx: int, wait_seconds: float = 60):
    """Put a key in cooldown after a rate limit hit."""
    with _key_lock:
        _key_cooldown[key_idx] = time.time() + wait_seconds
        # Rotate to next key immediately
        global _current_key_idx
        _current_key_idx = (key_idx + 1) % len(_clients)


def _parse_wait_time(error_msg: str) -> float:
    """Extract wait time from Groq rate limit error message."""
    import re
    match = re.search(r'try again in (\d+)m([\d.]+)s', str(error_msg))
    if match:
        return int(match.group(1)) * 60 + float(match.group(2))
    match = re.search(r'try again in ([\d.]+)s', str(error_msg))
    if match:
        return float(match.group(1))
    return 60


CATEGORIES = [
    "Billing Inquiry", "Technical Issue", "Product Inquiry",
    "Refund Request", "Account Access", "Shipping Issue",
    "Cancellation", "General Inquiry"
]


def is_available() -> bool:
    return len(_clients) > 0


def get_provider() -> str:
    return _provider


def categorize_and_analyze(message: str) -> Dict:
    """Combined categorization + sentiment in a SINGLE API call (saves quota).

    Returns: {category, confidence, sentiment, frustration_score, reasoning}
    """
    client, key_idx = _get_client()
    if not client:
        return None

    try:
        resp = client.chat.completions.create(
            model=_model,
            messages=[
                {"role": "system", "content": (
                    "You are a customer support analyst. Analyze the ticket and return valid JSON:\n"
                    "{\n"
                    '  "category": "one of: ' + ", ".join(CATEGORIES) + '",\n'
                    '  "confidence": 0.0-1.0,\n'
                    '  "sentiment": "positive|neutral|negative",\n'
                    '  "frustration_score": 0.0-1.0,\n'
                    '  "reasoning": "brief 1-sentence explanation"\n'
                    "}\n"
                    "Respond with valid JSON only, no other text."
                )},
                {"role": "user", "content": message[:1000]}
            ],
            temperature=0,
            max_tokens=150,
        )
        text = resp.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1].removeprefix("json").strip()
        result = json.loads(text)

        # Validate category
        cat = result.get("category", "General Inquiry")
        if cat not in CATEGORIES:
            for c in CATEGORIES:
                if c.lower() in cat.lower():
                    cat = c
                    break
            else:
                cat = "General Inquiry"

        return {
            "category": cat,
            "confidence": min(1.0, max(0.0, float(result.get("confidence", 0.8)))),
            "sentiment": result.get("sentiment", "neutral") if result.get("sentiment") in ("positive", "neutral", "negative") else "neutral",
            "frustration_score": min(1.0, max(0.0, float(result.get("frustration_score", 0.5)))),
            "reasoning": result.get("reasoning", ""),
        }
    except Exception as e:
        error_str = str(e)
        print(f"LLM analyze error (key {key_idx}): {e}")
        if "429" in error_str or "rate" in error_str.lower():
            wait = _parse_wait_time(error_str)
            _mark_rate_limited(key_idx, wait)
            # Retry with next key
            return categorize_and_analyze(message) if any(
                time.time() >= _key_cooldown.get(i, 0) for i in range(len(_clients))
            ) else None
        return None


def generate_response(message: str, category: str, similar_context: str = "") -> str:
    """Generate a suggested agent response using LLM with optional RAG context."""
    client, key_idx = _get_client()
    if not client:
        return None

    context_block = ""
    if similar_context:
        context_block = f"\n\nSimilar resolved cases for reference:\n{similar_context}"

    try:
        resp = client.chat.completions.create(
            model=_model,
            messages=[
                {"role": "system", "content": (
                    "You are a professional customer support agent. Generate a helpful, "
                    "empathetic response to the customer's issue. Be concise (2-3 sentences). "
                    "Acknowledge the issue and provide concrete next steps."
                )},
                {"role": "user", "content": (
                    f"Category: {category}\n"
                    f"Customer message: {message[:500]}"
                    f"{context_block}"
                )}
            ],
            temperature=0.7,
            max_tokens=200,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        error_str = str(e)
        print(f"LLM response error (key {key_idx}): {e}")
        if "429" in error_str or "rate" in error_str.lower():
            wait = _parse_wait_time(error_str)
            _mark_rate_limited(key_idx, wait)
            # Retry with next key
            return generate_response(message, category, similar_context) if any(
                time.time() >= _key_cooldown.get(i, 0) for i in range(len(_clients))
            ) else None
        return None
