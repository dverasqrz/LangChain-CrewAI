from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

from dotenv import load_dotenv

load_dotenv()


DEFAULT_GROQ_MODEL: Final[str] = "llama3-70b-8192"
DEFAULT_OPENAI_MODEL: Final[str] = "gpt-4o-mini"
DEFAULT_TEMPERATURE: Final[float] = 0.7
DEFAULT_MAX_RETRIES: Final[int] = 2
DEFAULT_TIMEOUT_SECONDS: Final[int] = 60


class ConfigError(Exception):
    """Erro específico de configuração da aplicação."""


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    temperature: float
    max_retries: int
    timeout_seconds: int | None


def _normalize_provider(provider: str) -> str:
    normalized_provider = provider.strip().lower()

    if normalized_provider not in {"groq", "openai"}:
        raise ConfigError("Provider inválido. Use 'groq' ou 'openai'.")

    return normalized_provider


def _get_env_str(
    key: str,
    default: str | None = None,
    *,
    required: bool = False,
) -> str:
    value = os.getenv(key, default)

    if value is None:
        if required:
            raise ConfigError(
                f"Variável de ambiente obrigatória ausente: {key}."
            )
        raise ConfigError(
            f"Variável de ambiente '{key}' não encontrada."
        )

    normalized_value = value.strip()

    if required and not normalized_value:
        raise ConfigError(
            f"Variável de ambiente obrigatória vazia: {key}."
        )

    if not normalized_value:
        if default is not None:
            return default
        raise ConfigError(
            f"Variável de ambiente '{key}' está vazia."
        )

    return normalized_value


def _get_env_float(
    key: str,
    default: float,
    *,
    min_value: float | None = None,
    max_value: float | None = None,
) -> float:
    raw_value = os.getenv(key)

    if raw_value is None or not raw_value.strip():
        value = default
    else:
        try:
            value = float(raw_value.strip())
        except ValueError as exc:
            raise ConfigError(
                f"Variável '{key}' deve ser numérica. Valor atual: {raw_value!r}"
            ) from exc

    if min_value is not None and value < min_value:
        raise ConfigError(
            f"Variável '{key}' deve ser >= {min_value}. Valor atual: {value}"
        )

    if max_value is not None and value > max_value:
        raise ConfigError(
            f"Variável '{key}' deve ser <= {max_value}. Valor atual: {value}"
        )

    return value


def _get_env_int(
    key: str,
    default: int,
    *,
    min_value: int | None = None,
    allow_zero: bool = True,
) -> int:
    raw_value = os.getenv(key)

    if raw_value is None or not raw_value.strip():
        value = default
    else:
        try:
            value = int(raw_value.strip())
        except ValueError as exc:
            raise ConfigError(
                f"Variável '{key}' deve ser inteira. Valor atual: {raw_value!r}"
            ) from exc

    if not allow_zero and value == 0:
        raise ConfigError(
            f"Variável '{key}' não pode ser zero."
        )

    if min_value is not None and value < min_value:
        raise ConfigError(
            f"Variável '{key}' deve ser >= {min_value}. Valor atual: {value}"
        )

    return value


def _get_timeout_seconds() -> int | None:
    raw_value = os.getenv("LLM_TIMEOUT_SECONDS")

    if raw_value is None or not raw_value.strip():
        return DEFAULT_TIMEOUT_SECONDS

    normalized = raw_value.strip().lower()

    if normalized in {"none", "null", "sem_timeout"}:
        return None

    try:
        timeout = int(normalized)
    except ValueError as exc:
        raise ConfigError(
            "LLM_TIMEOUT_SECONDS deve ser um inteiro positivo "
            "ou um dos valores: none, null, sem_timeout."
        ) from exc

    if timeout <= 0:
        raise ConfigError(
            "LLM_TIMEOUT_SECONDS deve ser maior que zero."
        )

    return timeout


def get_llm_config(provider: str) -> LLMConfig:
    normalized_provider = _normalize_provider(provider)

    temperature = _get_env_float(
        "LLM_TEMPERATURE",
        DEFAULT_TEMPERATURE,
        min_value=0.0,
        max_value=2.0,
    )
    max_retries = _get_env_int(
        "LLM_MAX_RETRIES",
        DEFAULT_MAX_RETRIES,
        min_value=0,
    )
    timeout_seconds = _get_timeout_seconds()

    if normalized_provider == "groq":
        model = _get_env_str("GROQ_MODEL", DEFAULT_GROQ_MODEL)
        return LLMConfig(
            provider="groq",
            model=model,
            temperature=temperature,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
        )

    if normalized_provider == "openai":
        model = _get_env_str("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
        return LLMConfig(
            provider="openai",
            model=model,
            temperature=temperature,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
        )

    raise ConfigError("Provider inválido. Use 'groq' ou 'openai'.")


def validate_provider_environment(provider: str) -> None:
    normalized_provider = _normalize_provider(provider)

    if normalized_provider == "groq":
        _get_env_str("GROQ_API_KEY", required=True)
        return

    if normalized_provider == "openai":
        _get_env_str("OPENAI_API_KEY", required=True)
        return

    raise ConfigError("Provider inválido. Use 'groq' ou 'openai'.")


def get_masked_provider_key(provider: str) -> str:
    """
    Retorna a chave mascarada apenas para debug seguro.
    Ex.: sk-abc********xyz
    """
    normalized_provider = _normalize_provider(provider)

    if normalized_provider == "groq":
        key = _get_env_str("GROQ_API_KEY", required=True)
    elif normalized_provider == "openai":
        key = _get_env_str("OPENAI_API_KEY", required=True)
    else:
        raise ConfigError("Provider inválido. Use 'groq' ou 'openai'.")

    if len(key) <= 8:
        return "*" * len(key)

    return f"{key[:6]}{'*' * (len(key) - 9)}{key[-3:]}"