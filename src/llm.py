"""OpenAI client abstraction using environment-configured base URL and API key.

Adheres to:
- Guideline 1: Strict built-in typing using TypedDict schemas.
- Guideline 2: Functional split for LLM inference execution.
- Strictly uses OpenAIClient (mock provider removed).
- Base URL and API key loaded strictly from environment (.env).
- Model identifier configured strictly in config.json (model_config.agent_model).
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

    Model is configured strictly in config.json.
    API key and base URL credentials are loaded strictly from the environment (.env).
    """

    def __init__(
        self,
        model: str,
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

        if not model:
            raise ValueError(
                "Missing required model configuration: 'agent_model' in model_config of config.json. "
                "The model must be specified in config.json."
            )

        self.model: str = model
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
        choice = response.choices[0]
        msg = choice.message
        content = msg.content or ""
        if not content:
            # Fallback for reasoning models that place thinking/tokens in reasoning_content
            reasoning = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None)
            if reasoning:
                content = str(reasoning)
        return content


def get_llm_client(
    config: ModelConfig,
    is_judge: bool = False
) -> OpenAIClient:
    """Factory function returning configured OpenAIClient reading endpoint credentials directly from .env."""
    model = config.get("agent_model")
    if not model:
        raise ValueError(
            "Missing required configuration: 'agent_model' in model_config of config.json. "
            "The model must be specified in config.json."
        )

    return OpenAIClient(model=model)
