from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    temperature: float


def get_llm_config(provider: str) -> LLMConfig:
    normalized_provider = provider.strip().lower()

    if normalized_provider == "groq":
        return LLMConfig(
            provider="groq",
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        )

    if normalized_provider == "openai":
        return LLMConfig(
            provider="openai",
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        )

    raise ValueError(
        "Provider inválido. Use 'groq' ou 'openai'."
    )


def validate_provider_environment(provider: str) -> None:
    normalized_provider = provider.strip().lower()

    if normalized_provider == "groq":
        if not os.getenv("GROQ_API_KEY"):
            raise EnvironmentError(
                "GROQ_API_KEY não encontrada no arquivo .env."
            )
        return

    if normalized_provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise EnvironmentError(
                "OPENAI_API_KEY não encontrada no arquivo .env."
            )
        return

    raise ValueError(
        "Provider inválido. Use 'groq' ou 'openai'."
    )