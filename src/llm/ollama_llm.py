"""Ollama LLM provider — standalone implementation."""

import json
import logging
import os

import requests

from src.llm.base import BaseLLM

logger = logging.getLogger(__name__)


class OllamaLLM(BaseLLM):
    """Ollama LLM provider. Connects to a local or remote Ollama instance.

    Uses HTTP streaming (`/api/generate` with `stream=True`) internally so
    that long "trace" / multi-paragraph RAG answers don't trip the 120s
    read-timeout that the non-streaming call used to fail on. Each token
    chunk resets the per-read clock, so as long as Ollama is producing
    output we won't time out. A ceiling is still enforced via
    `OLLAMA_MAX_WALL_SECONDS` (default 900s) to avoid a wedged server
    hanging the UI forever.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        temperature: float = 0.3,
        max_tokens: int = 4000,
        connect_timeout: float = 10.0,
        read_timeout: float = 600.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        # Allow env overrides without touching callers.
        self.connect_timeout = float(
            os.environ.get("OLLAMA_CONNECT_TIMEOUT", connect_timeout)
        )
        self.read_timeout = float(
            os.environ.get("OLLAMA_READ_TIMEOUT", read_timeout)
        )
        self.max_wall_seconds = float(
            os.environ.get("OLLAMA_MAX_WALL_SECONDS", 900)
        )

    def _iter_tokens(self, prompt: str, system_prompt: str = None):
        """Low-level streaming generator over Ollama's /api/generate.

        Yields raw token chunks as they arrive from the HTTP stream.
        Shared by `generate()` and `generate_stream()` so both paths
        use identical timeout / error handling.
        """
        import time

        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        start = time.monotonic()
        produced_any = False
        try:
            with requests.post(
                url,
                json=payload,
                timeout=(self.connect_timeout, self.read_timeout),
                stream=True,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        logger.debug(
                            "Skipping non-JSON ollama line: %r", line[:120]
                        )
                        continue
                    piece = obj.get("response", "")
                    if piece:
                        produced_any = True
                        yield piece
                    if obj.get("done"):
                        return
                    if time.monotonic() - start > self.max_wall_seconds:
                        logger.warning(
                            "Ollama stream exceeded max_wall_seconds=%.0f; "
                            "stopping early.",
                            self.max_wall_seconds,
                        )
                        return
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"Could not connect to Ollama at {self.base_url}. "
                "Ensure Ollama is running: ollama serve"
            )
        except requests.exceptions.ReadTimeout as e:
            elapsed = time.monotonic() - start
            logger.error(
                "Ollama read timeout after %.1fs (read_timeout=%.0f). "
                "Model '%s' may be cold-loading or the prompt is too large. "
                "Set OLLAMA_READ_TIMEOUT=1200 to extend, or switch to a "
                "smaller model.",
                elapsed, self.read_timeout, self.model,
            )
            if produced_any:
                yield "\n\n[response truncated: read timeout]"
                return
            raise RuntimeError(
                f"Ollama read timeout after {elapsed:.0f}s on model "
                f"'{self.model}'. The model is likely cold-loading — "
                f"retry the query, or set OLLAMA_READ_TIMEOUT to a higher "
                f"value (current: {self.read_timeout:.0f}s)."
            ) from e
        except Exception as e:
            logger.error(f"Ollama generate failed: {e}")
            raise

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        chunks = list(self._iter_tokens(prompt, system_prompt))
        return "".join(chunks).strip()

    def generate_stream(self, prompt: str, system_prompt: str = None):
        """Yield token chunks live for UI streaming (e.g. st.write_stream)."""
        yield from self._iter_tokens(prompt, system_prompt)

    def __repr__(self):
        return f"OllamaLLM(model={self.model}, base_url={self.base_url})"
