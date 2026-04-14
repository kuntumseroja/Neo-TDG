"""LLM Factory — creates Ollama LLM provider from config.

This is the standalone factory for local Ollama deployment.
For cloud providers (Groq, OpenAI, Together), see the feature-full-cloud branch.
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
            provider_name: Currently only 'ollama' is supported on main.
            config: Full application config dict

        Returns:
            BaseLLM instance
        """
        provider_config = config.get("llm_providers", {}).get(provider_name, {})

        if provider_name == "ollama":
            from src.llm.ollama_llm import OllamaLLM
            base_url = provider_config.get(
                "base_url",
                os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            )
            return OllamaLLM(
                base_url=base_url,
                model=provider_config.get("model", "llama3.2"),
                temperature=provider_config.get("temperature", 0.3),
                max_tokens=provider_config.get("max_tokens", 8192),
            )

        else:
            raise ValueError(
                f"Unknown LLM provider: '{provider_name}'. "
                f"Supported on main branch: ollama. "
                f"For cloud providers (groq, openai, together), "
                f"see the feature-full-cloud branch."
            )

    @staticmethod
    def available_providers() -> list:
        """List available provider names."""
        return ["ollama"]
