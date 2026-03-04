"""LLM Factory — creates LLM providers from config.

Supports: ollama, groq, openai, together
This is the standalone factory that works without TechDocGen.
"""

import os
import logging
from src.llm.base import BaseLLM

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory for creating LLM provider instances from configuration."""

    @staticmethod
    def create(provider_name: str, config: dict) -> BaseLLM:
        """Create an LLM instance based on provider name and config.

        Args:
            provider_name: One of 'ollama', 'groq', 'openai', 'together'
            config: Full application config dict

        Returns:
            BaseLLM instance
        """
        provider_config = config.get("llm_providers", {}).get(provider_name, {})

        if provider_name == "ollama":
            from src.llm.ollama_llm import OllamaLLM
            base_url = provider_config.get("base_url", os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))
            return OllamaLLM(
                base_url=base_url,
                model=provider_config.get("model", "llama3.2"),
                temperature=provider_config.get("temperature", 0.3),
                max_tokens=provider_config.get("max_tokens", 4000),
            )

        elif provider_name == "groq":
            from src.llm.groq_llm import GroqLLM
            return GroqLLM(
                api_key=provider_config.get("api_key", os.environ.get("GROQ_API_KEY")),
                model=provider_config.get("model", "llama-3.3-70b-versatile"),
                temperature=provider_config.get("temperature", 0.3),
                max_tokens=provider_config.get("max_tokens", 4000),
            )

        elif provider_name == "openai":
            from src.llm.openai_llm import OpenAILLM
            return OpenAILLM(
                api_key=provider_config.get("api_key", os.environ.get("OPENAI_API_KEY")),
                model=provider_config.get("model", "gpt-4o-mini"),
                temperature=provider_config.get("temperature", 0.3),
                max_tokens=provider_config.get("max_tokens", 4000),
                base_url=provider_config.get("base_url"),
            )

        elif provider_name == "together":
            from src.llm.openai_llm import OpenAILLM
            return OpenAILLM(
                api_key=provider_config.get("api_key", os.environ.get("TOGETHER_API_KEY")),
                model=provider_config.get("model", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
                temperature=provider_config.get("temperature", 0.3),
                max_tokens=provider_config.get("max_tokens", 4000),
                base_url=provider_config.get("base_url", "https://api.together.xyz/v1"),
            )

        else:
            raise ValueError(
                f"Unknown LLM provider: '{provider_name}'. "
                f"Supported: ollama, groq, openai, together"
            )

    @staticmethod
    def available_providers() -> list:
        """List available provider names."""
        return ["ollama", "groq", "openai", "together"]
