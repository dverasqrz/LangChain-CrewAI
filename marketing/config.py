from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

from dotenv import load_dotenv

load_dotenv()


DEFAULT_GROQ_MODEL: Final[str] = "llama3-70b-8192"
DEFAULT_OPENAI_MODEL: Final[str] = "gpt-4o-mini"
DEFAULT_SYSTEM_PROMPT: Final[str] = (
    "Você é um redator profissional especializado em marketing de conteúdo. "
    "Escreva de forma estratégica, clara, persuasiva e adequada ao canal, "
    "ao público e ao objetivo do texto. Evite clichês, exageros, promessas "
    "irreais e jargões desnecessários."
)

DEFAULT_TEMPERATURE: Final[float] = 0.7
DEFAULT_MAX_RETRIES: Final[int] = 2
DEFAULT_TIMEOUT_SECONDS: Final[int] = 60
DEFAULT_MAX_OUTPUT_CHARS: Final[int] = 12_000
DEFAULT_ENABLE_DEBUG: Final[bool] = False
DEFAULT_LOG_LEVEL: Final[str] = "INFO"

SUPPORTED_PROVIDERS: Final[set[str]] = {"groq", "openai"}
SUPPORTED_PLATFORMS: Final[set[str]] = {
    "instagram",
    "facebook",
    "linkedin",
    "blog",
    "e-mail",
}
SUPPORTED_TONES: Final[set[str]] = {
    "normal",
    "informativo",
    "inspirador",
    "urgente",
    "informal",
}
SUPPORTED_LENGTHS: Final[set[str]] = {
    "curto",
    "médio",
    "medio",
    "longo",
}
SUPPORTED_AUDIENCES: Final[set[str]] = {
    "geral",
    "jovens adultos",
    "famílias",
    "familias",
    "idosos",
    "adolescentes",
}


class ConfigError(Exception):
    """Erro de configuração da aplicação."""


@dataclass(frozen=True)
class AppConfig:
    groq_model: str
    openai_model: str
    default_system_prompt: str
    temperature: float
    max_retries: int
    timeout_seconds: int | None
    max_output_chars: int
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
            raise ConfigError(
                f"Variável de ambiente obrigatória ausente: {key}."
            )
        raise ConfigError(
            f"Variável de ambiente não encontrada: {key}."
        )

    normalized = value.strip()

    if required and not normalized:
        raise ConfigError(
            f"Variável de ambiente obrigatória vazia: {key}."
        )

    if not normalized:
        if default is not None:
            return default
        raise ConfigError(
            f"Variável de ambiente vazia: {key}."
        )

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
        f"Variável {key} deve ser booleana. "
        "Use true/false, 1/0, yes/no, on/off."
    )


def _get_timeout_seconds() -> int | None:
    raw_value = os.getenv("LLM_TIMEOUT_SECONDS")

    if raw_value is None or not raw_value.strip():
        return DEFAULT_TIMEOUT_SECONDS

    normalized = raw_value.strip().lower()

    if normalized in {"none", "null", "sem_timeout", "no_timeout"}:
        return None

    try:
        timeout = int(normalized)
    except ValueError as exc:
        raise ConfigError(
            "LLM_TIMEOUT_SECONDS deve ser um inteiro positivo ou "
            "um dos valores: none, null, sem_timeout, no_timeout."
        ) from exc

    if timeout <= 0:
        raise ConfigError(
            "LLM_TIMEOUT_SECONDS deve ser maior que zero."
        )

    return timeout


def get_app_config() -> AppConfig:
    return AppConfig(
        groq_model=_get_env_str("GROQ_MODEL", DEFAULT_GROQ_MODEL),
        openai_model=_get_env_str("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        default_system_prompt=_get_env_str(
            "DEFAULT_SYSTEM_PROMPT",
            DEFAULT_SYSTEM_PROMPT,
        ),
        temperature=_get_env_float(
            "LLM_TEMPERATURE",
            DEFAULT_TEMPERATURE,
            min_value=0.0,
            max_value=2.0,
        ),
        max_retries=_get_env_int(
            "LLM_MAX_RETRIES",
            DEFAULT_MAX_RETRIES,
            min_value=0,
        ),
        timeout_seconds=_get_timeout_seconds(),
        max_output_chars=_get_env_int(
            "LLM_MAX_OUTPUT_CHARS",
            DEFAULT_MAX_OUTPUT_CHARS,
            min_value=1000,
        ),
        enable_debug=_get_env_bool(
            "APP_ENABLE_DEBUG",
            DEFAULT_ENABLE_DEBUG,
        ),
        log_level=_get_env_str("APP_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper(),
    )


def get_llm_config(provider: str) -> LLMConfig:
    normalized_provider = normalize_provider(provider)
    app_config = get_app_config()

    if normalized_provider == "groq":
        return LLMConfig(
            provider="groq",
            model=app_config.groq_model,
            temperature=app_config.temperature,
            max_retries=app_config.max_retries,
            timeout_seconds=app_config.timeout_seconds,
        )

    if normalized_provider == "openai":
        return LLMConfig(
            provider="openai",
            model=app_config.openai_model,
            temperature=app_config.temperature,
            max_retries=app_config.max_retries,
            timeout_seconds=app_config.timeout_seconds,
        )

    raise ConfigError("Provider inválido.")


def validate_provider_environment(provider: str) -> None:
    normalized_provider = normalize_provider(provider)

    if normalized_provider == "groq":
        _get_env_str("GROQ_API_KEY", required=True)
        return

    if normalized_provider == "openai":
        _get_env_str("OPENAI_API_KEY", required=True)
        return

    raise ConfigError("Provider inválido.")


def get_masked_provider_key(provider: str) -> str:
    normalized_provider = normalize_provider(provider)

    key_name = "GROQ_API_KEY" if normalized_provider == "groq" else "OPENAI_API_KEY"
    key_value = _get_env_str(key_name, required=True)

    if len(key_value) <= 8:
        return "*" * len(key_value)

    return f"{key_value[:6]}{'*' * (len(key_value) - 9)}{key_value[-3:]}"