from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

from dotenv import load_dotenv

load_dotenv()

DEFAULT_AI_PROVIDER: Final[str] = "groq"
DEFAULT_OPENAI_MODEL: Final[str] = "gpt-4o-mini"
DEFAULT_GROQ_MODEL: Final[str] = "llama3-70b-8192"
DEFAULT_SYSTEM_PROMPT: Final[str] = (
    "Você é um especialista em seleção de currículos e análise de talentos. "
    "Avalie o alinhamento entre o currículo do candidato e a vaga informada, "
    "fornecendo uma análise objetiva, pontos fortes, lacunas e uma nota de adequação."
)
DEFAULT_TEMPERATURE: Final[float] = 0.7
DEFAULT_MAX_RETRIES: Final[int] = 2
DEFAULT_TIMEOUT_SECONDS: Final[int] = 60
DEFAULT_ENABLE_DEBUG: Final[bool] = False
DEFAULT_LOG_LEVEL: Final[str] = "INFO"

SUPPORTED_PROVIDERS: Final[set[str]] = {"groq", "openai"}


class ConfigError(Exception):
    """Erro de configuração da aplicação."""


@dataclass(frozen=True)
class AppConfig:
    ai_provider: str
    groq_model: str
    openai_model: str
    default_system_prompt: str
    temperature: float
    max_retries: int
    timeout_seconds: int | None
    enable_debug: bool
    log_level: str


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    temperature: float
    max_retries: int
    timeout_seconds: int | None


def _normalize_text(value: str) -> str:
    return value.strip()


def normalize_provider(provider: str) -> str:
    normalized = _normalize_text(provider).lower()
    if normalized not in SUPPORTED_PROVIDERS:
        raise ConfigError(
            f"Provider inválido: {provider!r}. Use um destes: "
            f"{', '.join(sorted(SUPPORTED_PROVIDERS))}."
        )
    return normalized


def _get_env_str(
    key: str,
    default: str | None = None,
    *,
    required: bool = False,
) -> str:
    value = os.getenv(key, default)

    if value is None:
        if required:
            raise ConfigError(f"Variável de ambiente obrigatória ausente: {key}.")
        raise ConfigError(f"Variável de ambiente não encontrada: {key}.")

    normalized = value.strip()
    if required and not normalized:
        raise ConfigError(f"Variável de ambiente obrigatória vazia: {key}.")

    if not normalized:
        if default is not None:
            return default
        raise ConfigError(f"Variável de ambiente vazia: {key}.")

    return normalized


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
                f"Variável {key} deve ser numérica. Valor atual: {raw_value!r}."
            ) from exc

    if min_value is not None and value < min_value:
        raise ConfigError(
            f"Variável {key} deve ser >= {min_value}. Valor atual: {value}."
        )
    if max_value is not None and value > max_value:
        raise ConfigError(
            f"Variável {key} deve ser <= {max_value}. Valor atual: {value}."
        )

    return value


def _get_env_int(
    key: str,
    default: int,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    raw_value = os.getenv(key)
    if raw_value is None or not raw_value.strip():
        value = default
    else:
        try:
            value = int(raw_value.strip())
        except ValueError as exc:
            raise ConfigError(
                f"Variável {key} deve ser inteira. Valor atual: {raw_value!r}."
            ) from exc

    if min_value is not None and value < min_value:
        raise ConfigError(
            f"Variável {key} deve ser >= {min_value}. Valor atual: {value}."
        )
    if max_value is not None and value > max_value:
        raise ConfigError(
            f"Variável {key} deve ser <= {max_value}. Valor atual: {value}."
        )

    return value


def _get_env_bool(key: str, default: bool) -> bool:
    raw_value = os.getenv(key)
    if raw_value is None or not raw_value.strip():
        return default

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on", "sim"}:
        return True
    if normalized in {"0", "false", "no", "n", "off", "nao", "não"}:
        return False

    raise ConfigError(
        f"Variável {key} deve ser booleana. Use true/false, 1/0, yes/no, on/off."
    )


def _get_timeout_seconds() -> int | None:
    raw_value = os.getenv("RH_LLM_TIMEOUT_SECONDS")
    if raw_value is None or not raw_value.strip():
        return DEFAULT_TIMEOUT_SECONDS

    normalized = raw_value.strip().lower()
    if normalized in {"none", "null", "sem_timeout", "no_timeout"}:
        return None

    try:
        timeout = int(normalized)
    except ValueError as exc:
        raise ConfigError(
            "RH_LLM_TIMEOUT_SECONDS deve ser um inteiro positivo ou "
            "um dos valores: none, null, sem_timeout, no_timeout."
        ) from exc

    if timeout <= 0:
        raise ConfigError("RH_LLM_TIMEOUT_SECONDS deve ser maior que zero.")

    return timeout


def get_app_config() -> AppConfig:
    provider = normalize_provider(
        _get_env_str("RH_AI_PROVIDER", DEFAULT_AI_PROVIDER)
    )
    return AppConfig(
        ai_provider=provider,
        groq_model=_get_env_str("RH_GROQ_MODEL", DEFAULT_GROQ_MODEL),
        openai_model=_get_env_str("RH_OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        default_system_prompt=_get_env_str(
            "RH_DEFAULT_SYSTEM_PROMPT",
            DEFAULT_SYSTEM_PROMPT,
        ),
        temperature=_get_env_float(
            "RH_LLM_TEMPERATURE",
            DEFAULT_TEMPERATURE,
            min_value=0.0,
            max_value=2.0,
        ),
        max_retries=_get_env_int(
            "RH_LLM_MAX_RETRIES",
            DEFAULT_MAX_RETRIES,
            min_value=0,
        ),
        timeout_seconds=_get_timeout_seconds(),
        enable_debug=_get_env_bool("RH_ENABLE_DEBUG", DEFAULT_ENABLE_DEBUG),
        log_level=_get_env_str("RH_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper(),
    )


def get_llm_config(provider: str) -> LLMConfig:
    provider = normalize_provider(provider)
    if provider == "groq":
        return LLMConfig(
            provider=provider,
            model=_get_env_str("RH_GROQ_MODEL", DEFAULT_GROQ_MODEL),
            temperature=_get_env_float("RH_LLM_TEMPERATURE", DEFAULT_TEMPERATURE),
            max_retries=_get_env_int("RH_LLM_MAX_RETRIES", DEFAULT_MAX_RETRIES),
            timeout_seconds=_get_timeout_seconds(),
        )

    return LLMConfig(
        provider=provider,
        model=_get_env_str("RH_OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        temperature=_get_env_float("RH_LLM_TEMPERATURE", DEFAULT_TEMPERATURE),
        max_retries=_get_env_int("RH_LLM_MAX_RETRIES", DEFAULT_MAX_RETRIES),
        timeout_seconds=_get_timeout_seconds(),
    )


def validate_provider_environment(provider: str) -> None:
    provider = normalize_provider(provider)
    if provider == "groq":
        if not os.getenv("RH_GROQ_API_KEY"):
            raise ConfigError("RH_GROQ_API_KEY não encontrado para o provider Groq.")
    if provider == "openai":
        if not os.getenv("RH_OPENAI_API_KEY"):
            raise ConfigError("RH_OPENAI_API_KEY não encontrado para o provider OpenAI.")
