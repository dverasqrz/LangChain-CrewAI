from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

from dotenv import load_dotenv

load_dotenv()


DEFAULT_OLLAMA_EMBEDDING_MODEL: Final[str] = "nomic-embed-text"
DEFAULT_CHUNK_SIZE: Final[int] = 350
DEFAULT_OVERLAP: Final[int] = 70
DEFAULT_MAX_CHUNK_SIZE: Final[int] = 900
DEFAULT_MAX_OVERLAP: Final[int] = 200
DEFAULT_ENABLE_DEBUG: Final[bool] = False
DEFAULT_LOG_LEVEL: Final[str] = "INFO"

SUPPORTED_EMBEDDING_MODELS: Final[set[str]] = {
    "nomic-embed-text",
    "all-MiniLM-L6-v2",
    "paraphrase-multilingual-MiniLM-L12-v2",
}


class ConfigError(Exception):
    """Erro de configuração da aplicação."""


@dataclass(frozen=True)
class PineconeConfig:
    api_key: str
    environment: str
    index_name: str | None


@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str
    base_url: str | None


@dataclass(frozen=True)
class GeminiConfig:
    api_key: str


@dataclass(frozen=True)
class GroqConfig:
    api_key: str
    base_url: str | None


@dataclass(frozen=True)
class OllamaConfig:
    base_url: str
    embedding_model: str


@dataclass(frozen=True)
class AIProvidersConfig:
    openai: OpenAIConfig
    gemini: GeminiConfig
    groq: GroqConfig
    ollama: OllamaConfig
    default_provider: str


@dataclass(frozen=True)
class ChunkingConfig:
    chunk_size: int
    overlap: int


@dataclass(frozen=True)
class AppConfig:
    pinecone: PineconeConfig
    ai_providers: AIProvidersConfig
    chunking: ChunkingConfig
    enable_debug: bool
    log_level: str


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
        f"Variável {key} deve ser booleana. "
        "Use true/false, 1/0, yes/no, on/off."
    )


def get_pinecone_config() -> PineconeConfig:
    return PineconeConfig(
        api_key=_get_env_str("PINECONE_API_KEY", required=True),
        environment=_get_env_str("PINECONE_ENVIRONMENT", required=True),
        index_name=_get_env_str("PINECONE_INDEX_NAME"),
    )


def get_openai_config() -> OpenAIConfig:
    return OpenAIConfig(
        api_key=_get_env_str("OPENAI_API_KEY", ""),
        base_url=os.getenv("OPENAI_BASE_URL"),
    )


def get_gemini_config() -> GeminiConfig:
    return GeminiConfig(
        api_key=_get_env_str("GEMINI_API_KEY", ""),
    )


def get_groq_config() -> GroqConfig:
    return GroqConfig(
        api_key=_get_env_str("GROQ_API_KEY", ""),
        base_url=os.getenv("GROQ_BASE_URL"),
    )


def get_ollama_config() -> OllamaConfig:
    return OllamaConfig(
        base_url=_get_env_str("OLLAMA_BASE_URL", required=True),
        embedding_model=_get_env_str("OLLAMA_EMBEDDING_MODEL", DEFAULT_OLLAMA_EMBEDDING_MODEL),
    )


def get_ai_providers_config() -> AIProvidersConfig:
    return AIProvidersConfig(
        openai=get_openai_config(),
        gemini=get_gemini_config(),
        groq=get_groq_config(),
        ollama=get_ollama_config(),
        default_provider=_get_env_str("DEFAULT_AI_PROVIDER", "groq"),
    )


def get_chunking_config() -> ChunkingConfig:
    return ChunkingConfig(
        chunk_size=_get_env_int(
            "CHUNK_SIZE",
            DEFAULT_CHUNK_SIZE,
            min_value=100,
            max_value=DEFAULT_MAX_CHUNK_SIZE,
        ),
        overlap=_get_env_int(
            "CHUNK_OVERLAP",
            DEFAULT_OVERLAP,
            min_value=0,
            max_value=DEFAULT_MAX_OVERLAP,
        ),
    )


def get_app_config() -> AppConfig:
    return AppConfig(
        pinecone=get_pinecone_config(),
        ai_providers=get_ai_providers_config(),
        chunking=get_chunking_config(),
        enable_debug=_get_env_bool("APP_ENABLE_DEBUG", DEFAULT_ENABLE_DEBUG),
        log_level=_get_env_str("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper(),
    )


def validate_embedding_model(model: str) -> str:
    normalized = model.strip()

    if normalized not in SUPPORTED_EMBEDDING_MODELS:
        raise ConfigError(
            f"Modelo de embedding inválido: {model!r}. Use um destes: "
            f"{', '.join(sorted(SUPPORTED_EMBEDDING_MODELS))}."
        )

    return normalized


def get_masked_pinecone_key() -> str:
    key_value = _get_env_str("PINECONE_API_KEY", required=True)

    if len(key_value) <= 8:
        return "*" * len(key_value)

    return f"{key_value[:6]}{'*' * (len(key_value) - 9)}{key_value[-3:]}"