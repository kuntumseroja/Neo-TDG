"""Base LLM interface — standalone replacement for TechDocGen's BaseLLM."""

from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseLLM(ABC):
    """Abstract base class for LLM providers.

    All providers must implement generate() with this signature.
    Compatible with both TechDocGen and Neo-TDG standalone usage.
    """

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: The user prompt / question.
            system_prompt: Optional system-level instruction.

        Returns:
            The LLM's text response.
        """
        pass

    def generate_stream(self, prompt: str, system_prompt: str = None):
        """Stream a response token-by-token.

        Providers that support incremental output should override this
        to yield string chunks as they arrive. The default implementation
        falls back to the blocking `generate()` and yields the full
        response as one chunk, so call sites can always use streaming
        API regardless of provider.
        """
        yield self.generate(prompt, system_prompt)

    def __repr__(self):
        return f"{self.__class__.__name__}()"
