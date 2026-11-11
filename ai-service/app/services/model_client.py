# model_client.py
"""
Centralized AI Model Client for the NBA Accreditation Readiness System.

Responsibilities:
1. Initialize the Groq / OpenAI-compatible API client securely from environment variables.
2. Provide a single unified `call_model` interface for all specialized agents.
3. Support offline / mock testing mode (via MOCK_LLM env var or argument) for fast,
   deterministic tests without burning API tokens.
4. Protect secrets: never log or expose API keys in exceptions or logs.
"""

import os
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

# Load .env variables
load_dotenv()

_client: Optional[OpenAI] = None


def get_model_client() -> OpenAI:
    """
    Get or initialize the shared OpenAI-compatible client connected to Groq.
    """
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is not set. Please configure it in your .env file."
            )
        base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        _client = OpenAI(api_key=api_key, base_url=base_url)
    return _client


def call_model(
    prompt: str,
    max_output_tokens: int = 2500,
    model: str = "openai/gpt-oss-20b",
    reasoning_effort: str = "low",
    mock_response: Optional[str] = None
) -> str:
    """
    Execute a model completion call using Groq.

    Args:
        prompt: The fully constructed, grounded prompt text.
        max_output_tokens: Max tokens to generate.
        model: Model identifier (default: openai/gpt-oss-20b).
        reasoning_effort: Reasoning effort level ('low', 'medium', etc.).
        mock_response: If provided, immediately returns this string without network calls.

    Returns:
        The generated text response.
    """
    # 1. Check if mock mode is requested (for unit tests and offline viva demos)
    if mock_response is not None:
        return mock_response

    if os.getenv("MOCK_LLM", "false").lower() in ("true", "1", "yes"):
        return f"[MOCK_RESPONSE: LLM call simulated for testing]\n{prompt[:200]}..."

    # 2. Make live API call
    client = get_model_client()

    try:
        response = client.responses.create(
            model=model,
            input=prompt,
            max_output_tokens=max_output_tokens,
            reasoning={"effort": reasoning_effort}
        )
        return response.output_text

    except Exception as error:
        # Fallback to standard chat completions if responses endpoint fails
        try:
            chat_response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_output_tokens
            )
            return chat_response.choices[0].message.content or ""
        except Exception:
            # Re-raise clean error without exposing secrets
            clean_msg = str(error).replace(os.getenv("GROQ_API_KEY", ""), "[REDACTED]")
            raise RuntimeError(f"AI model provider call failed: {clean_msg}") from None
