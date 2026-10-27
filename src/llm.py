"""OpenAI client abstraction using environment-configured base URL and API key.

Adheres to:
- Guideline 1: Strict built-in typing using TypedDict schemas.
- Guideline 2: Functional split for LLM inference execution.
- Strictly uses OpenAIClient (mock provider removed).
- Base URL and API key loaded strictly from environment (.env).
- Default models fallback from environment (AGENT_MODEL, JUDGE_MODEL, MODEL_LLAMA, MODEL_GEMMA, DEFAULT_AGENT_MODEL).
"""

import abc
import os
from typing import Optional
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

try:
    from dotenv import load_dotenv  # pyright: ignore[reportUnknownVariableType]
    _ = load_dotenv()
except ImportError:
    pass

from src.schemas import ModelConfig


class BaseLLMClient(abc.ABC):
    """Abstract base class for LLM inference."""

    @abc.abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
        seed: Optional[int] = None,
    ) -> str:
        """Generate text from prompt and system prompt."""
        pass


class OpenAIClient(BaseLLMClient):
    """Client for OpenAI and OpenAI-compatible endpoints (Together AI, vLLM, Ollama, OpenRouter).

    If the primary model specified in config.json is not available on the endpoint,
    it automatically falls back to default models configured in the environment (.env).
    """

    def __init__(
        self,
        model: str,
        fallback_model: Optional[str] = None
    ):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "Missing required environment variable: OPENAI_API_KEY. "
                "Please configure your API key in .env as instructed in README.md."
            )

        base_url = os.environ.get("OPENAI_BASE_URL")
        if not base_url:
            raise ValueError(
                "Missing required environment variable: OPENAI_BASE_URL. "
                "Please configure your base URL in .env as instructed in README.md."
            )

        self.model: str = model
        self.fallback_model: Optional[str] = fallback_model
        self.client: OpenAI = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
        seed: Optional[int] = None,
    ) -> str:
        messages: list[ChatCompletionMessageParam] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            if seed is not None:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    seed=seed,
                )
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            return response.choices[0].message.content or ""
        except Exception as primary_err:
            err_str = str(primary_err).lower()
            # If primary model is unavailable / not found, fall back to environment default model
            if (
                self.fallback_model
                and self.fallback_model != self.model
                and any(keyword in err_str for keyword in ["not found", "does not exist", "invalid model", "model", "404", "400"])
            ):
                print(f"⚠️ Model '{self.model}' not available on endpoint ({primary_err}). Falling back to '{self.fallback_model}' from environment...")
                try:
                    if seed is not None:
                        fallback_response = self.client.chat.completions.create(
                            model=self.fallback_model,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            seed=seed,
                        )
                    else:
                        fallback_response = self.client.chat.completions.create(
                            model=self.fallback_model,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )
                    return fallback_response.choices[0].message.content or ""
                except Exception as fallback_err:
                    print(f"❌ Fallback model '{self.fallback_model}' also failed: {fallback_err}")
                    raise fallback_err
            raise primary_err


def resolve_fallback_model(is_judge: bool = False) -> Optional[str]:
    """Retrieve fallback default model from environment variables (.env)."""
    return (
        os.environ.get("AGENT_MODEL")
        or os.environ.get("DEFAULT_AGENT_MODEL")
        or os.environ.get("MODEL_GPT_OSS")
        or os.environ.get("MODEL_LLAMA")
        or os.environ.get("MODEL_GEMMA")
        or "openai/gpt-oss-120b"
    )


def get_llm_client(
    config: ModelConfig,
    is_judge: bool = False
) -> OpenAIClient:
    """Factory function returning configured OpenAIClient reading endpoint credentials directly from .env."""
    fallback_model = resolve_fallback_model(is_judge=is_judge)
    model = config.get("agent_model") or fallback_model or "openai/gpt-oss-120b"

    return OpenAIClient(
        model=model,
        fallback_model=fallback_model
    )
