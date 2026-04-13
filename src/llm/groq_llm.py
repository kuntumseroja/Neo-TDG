"""Groq LLM provider — ultra-fast cloud inference (free tier available).

Groq provides blazing-fast LLM inference via their LPU hardware.
Free tier: 30 requests/minute, 14,400 requests/day.
Models: llama-3.3-70b-versatile, gemma2-9b-it, mixtral-8x7b-32768

Get your API key at: https://console.groq.com/keys
"""

import os
import logging
from src.llm.base import BaseLLM

logger = logging.getLogger(__name__)


class GroqLLM(BaseLLM):
    """Groq cloud LLM provider using the Groq Python SDK."""

    def __init__(
        self,
        api_key: str = None,
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.3,
        max_tokens: int = 4000,
    ):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "Groq API key required. Set GROQ_API_KEY environment variable "
                "or pass api_key parameter. Get a free key at https://console.groq.com/keys"
            )

        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        try:
            from groq import Groq
            self.client = Groq(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "groq package required. Install with: pip install groq"
            )

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Groq generate failed: {e}")
            raise

    def generate_stream(self, prompt: str, system_prompt: str = None):
        """Stream tokens from Groq API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
            )
            for chunk in response:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
        except Exception as e:
            logger.error(f"Groq stream failed: {e}")
            raise

    def __repr__(self):
        return f"GroqLLM(model={self.model})"
