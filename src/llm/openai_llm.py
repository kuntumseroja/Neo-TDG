"""OpenAI LLM provider — GPT-4o, GPT-4o-mini, etc.

Also works with OpenAI-compatible APIs (Together AI, Fireworks, etc.)
by changing the base_url parameter.

Together AI: base_url="https://api.together.xyz/v1", model="meta-llama/Llama-3.3-70B-Instruct-Turbo"
Fireworks:   base_url="https://api.fireworks.ai/inference/v1", model="accounts/fireworks/models/llama-v3p1-70b-instruct"
"""

import os
import logging
from src.llm.base import BaseLLM

logger = logging.getLogger(__name__)


class OpenAILLM(BaseLLM):
    """OpenAI-compatible LLM provider. Works with OpenAI, Together AI, Fireworks, etc."""

    def __init__(
        self,
        api_key: str = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        max_tokens: int = 4000,
        base_url: str = None,
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url

        try:
            from openai import OpenAI
            client_kwargs = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            self.client = OpenAI(**client_kwargs)
        except ImportError:
            raise ImportError(
                "openai package required. Install with: pip install openai"
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
            logger.error(f"OpenAI generate failed: {e}")
            raise

    def generate_stream(self, prompt: str, system_prompt: str = None):
        """Stream tokens from OpenAI-compatible API."""
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
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI stream failed: {e}")
            raise

    def __repr__(self):
        prefix = f"base_url={self.base_url}, " if self.base_url else ""
        return f"OpenAILLM({prefix}model={self.model})"
