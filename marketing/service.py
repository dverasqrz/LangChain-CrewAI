from __future__ import annotations

import logging
import time
import uuid
from dataclasses import asdict, dataclass

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from marketing.config import (
    ConfigError,
    SUPPORTED_AUDIENCES,
    SUPPORTED_LENGTHS,
    SUPPORTED_PLATFORMS,
    SUPPORTED_TONES,
    get_app_config,
    get_llm_config,
    normalize_provider,
    validate_provider_environment,
)

logger = logging.getLogger(__name__)


class MarketingServiceError(Exception):
    """Erro de negócio ou execução do serviço de marketing."""


@dataclass(frozen=True)
class MarketingContentRequest:
    provider: str
    platform: str
    tone: str
    length: str
    topic: str
    audience: str
    include_cta: bool
    cta_text: str
    return_hashtags: bool
    keywords: str


@dataclass(frozen=True)
class MarketingGenerationResult:
    request_id: str
    provider: str
    model: str
    content: str
    prompt_preview: str
    elapsed_ms: int


def _normalize_text(value: str) -> str:
    return value.strip()


def _normalize_option(value: str) -> str:
    return _normalize_text(value).lower()


def _truncate_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars].rstrip()}..."


def _normalize_request(
    *,
    provider: str,
    platform: str,
    tone: str,
    length: str,
    topic: str,
    audience: str,
    include_cta: bool,
    cta_text: str,
    return_hashtags: bool,
    keywords: str,
) -> MarketingContentRequest:
    return MarketingContentRequest(
        provider=normalize_provider(provider),
        platform=_normalize_text(platform),
        tone=_normalize_text(tone),
        length=_normalize_text(length),
        topic=_normalize_text(topic),
        audience=_normalize_text(audience),
        include_cta=include_cta,
        cta_text=_normalize_text(cta_text),
        return_hashtags=return_hashtags,
        keywords=_normalize_text(keywords),
    )


def _validate_option(
    *,
    field_name: str,
    value: str,
    allowed_values: set[str],
) -> None:
    normalized = _normalize_option(value)
    if normalized not in allowed_values:
        raise ValueError(
            f"Valor inválido para '{field_name}': {value!r}. "
            f"Valores aceitos: {', '.join(sorted(allowed_values))}."
        )


def _validate_request(data: MarketingContentRequest) -> None:
    if not data.topic:
        raise ValueError("O campo 'Tema ou tópico' é obrigatório.")

    if len(data.topic) < 3:
        raise ValueError("O campo 'Tema ou tópico' deve ter ao menos 3 caracteres.")

    if len(data.topic) > 300:
        raise ValueError("O campo 'Tema ou tópico' não pode exceder 300 caracteres.")

    if not data.audience:
        raise ValueError("O campo 'Público-alvo' é obrigatório.")

    _validate_option(
        field_name="Plataforma de destino",
        value=data.platform,
        allowed_values=SUPPORTED_PLATFORMS,
    )
    _validate_option(
        field_name="Tom da mensagem",
        value=data.tone,
        allowed_values=SUPPORTED_TONES,
    )
    _validate_option(
        field_name="Comprimento do texto",
        value=data.length,
        allowed_values=SUPPORTED_LENGTHS,
    )
    _validate_option(
        field_name="Público-alvo",
        value=data.audience,
        allowed_values=SUPPORTED_AUDIENCES,
    )

    if data.include_cta and not data.cta_text:
        raise ValueError(
            "O campo 'Texto da chamada para ação' é obrigatório "
            "quando 'Incluir chamada para ação' estiver marcado."
        )

    if len(data.cta_text) > 200:
        raise ValueError(
            "O campo 'Texto da chamada para ação' não pode exceder 200 caracteres."
        )

    if len(data.keywords) > 500:
        raise ValueError(
            "O campo 'Palavras-chave' não pode exceder 500 caracteres."
        )


def _build_llm(provider: str):
    config = get_llm_config(provider)
    validate_provider_environment(provider)

    try:
        if config.provider == "groq":
            from langchain_groq import ChatGroq

            return ChatGroq(
                model=config.model,
                temperature=config.temperature,
                max_tokens=None,
                timeout=config.timeout_seconds,
                max_retries=config.max_retries,
            )

        if config.provider == "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=config.model,
                temperature=config.temperature,
                timeout=config.timeout_seconds,
                max_retries=config.max_retries,
            )

        raise MarketingServiceError("Provider não suportado.")

    except ConfigError as exc:
        raise MarketingServiceError(
            f"Erro de configuração ao inicializar a LLM: {exc}"
        ) from exc
    except Exception as exc:
        raise MarketingServiceError(
            f"Falha ao inicializar o modelo do provider '{provider}': {exc}"
        ) from exc


def _build_system_prompt() -> str:
    app_config = get_app_config()
    return app_config.default_system_prompt


def _build_cta_instruction(data: MarketingContentRequest) -> str:
    if not data.include_cta:
        return "Não inclua chamada para ação."

    return (
        f"Inclua uma chamada para ação ao final com a seguinte orientação: "
        f"{data.cta_text}."
    )


def _build_hashtag_instruction(data: MarketingContentRequest) -> str:
    if data.return_hashtags:
        return "Ao final, inclua uma seção separada com hashtags relevantes."

    return "Não inclua hashtags."


def _build_keyword_instruction(data: MarketingContentRequest) -> str:
    if not data.keywords:
        return "Não é necessário incluir palavras-chave específicas."

    return (
        "Inclua naturalmente as seguintes palavras-chave ao longo do texto, "
        f"sem forçar repetição: {data.keywords}."
    )


def _build_platform_instruction(data: MarketingContentRequest) -> str:
    normalized_platform = _normalize_option(data.platform)

    if normalized_platform == "instagram":
        return (
            "Escreva em formato adequado para legenda de Instagram, "
            "com abertura forte e leitura rápida."
        )

    if normalized_platform == "facebook":
        return (
            "Escreva em formato adequado para Facebook, equilibrando proximidade "
            "e clareza."
        )

    if normalized_platform == "linkedin":
        return (
            "Escreva em formato adequado para LinkedIn, com tom mais profissional, "
            "objetivo e orientado a valor."
        )

    if normalized_platform == "blog":
        return (
            "Escreva em formato adequado para blog, com estrutura mais desenvolvida, "
            "boa fluidez e maior densidade informativa."
        )

    if normalized_platform == "e-mail":
        return (
            "Escreva em formato adequado para e-mail marketing, com assunto implícito, "
            "clareza, escaneabilidade e CTA relevante."
        )

    return "Adapte a estrutura ao canal informado."


def _build_length_instruction(data: MarketingContentRequest) -> str:
    normalized_length = _normalize_option(data.length)

    if normalized_length == "curto":
        return "Mantenha o texto conciso."

    if normalized_length in {"médio", "medio"}:
        return "Mantenha o texto em tamanho intermediário, equilibrando concisão e detalhe."

    return "Desenvolva mais o conteúdo, mantendo boa clareza e organização."


def _build_user_prompt(data: MarketingContentRequest) -> str:
    return f"""
Crie um conteúdo de marketing com as seguintes especificações:

Plataforma de destino: {data.platform}
Tom da mensagem: {data.tone}
Comprimento do texto: {data.length}
Tema ou tópico: {data.topic}
Público-alvo: {data.audience}

Regras adicionais:
- {_build_platform_instruction(data)}
- {_build_length_instruction(data)}
- O texto deve ser útil, natural, convincente e alinhado ao público-alvo.
- Evite excesso de adjetivos, clichês e promessas exageradas.
- {_build_cta_instruction(data)}
- {_build_hashtag_instruction(data)}
- {_build_keyword_instruction(data)}

Formato esperado:
1. Título ou abertura
2. Conteúdo principal
3. CTA (somente se solicitado)
4. Hashtags (somente se solicitado)
""".strip()


def _build_chain(provider: str):
    llm = _build_llm(provider)

    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", "{system_prompt}"),
            ("human", "{user_prompt}"),
        ]
    )

    return prompt_template | llm | StrOutputParser()


def _sanitize_model_output(content: str) -> str:
    app_config = get_app_config()

    normalized = content.strip()

    if not normalized:
        raise MarketingServiceError("A resposta do modelo veio vazia.")

    if len(normalized) > app_config.max_output_chars:
        return _truncate_text(normalized, app_config.max_output_chars)

    return normalized


def generate_marketing_content(
    *,
    provider: str,
    platform: str,
    tone: str,
    length: str,
    topic: str,
    audience: str,
    include_cta: bool,
    cta_text: str,
    return_hashtags: bool,
    keywords: str,
) -> str:
    result = generate_marketing_content_with_metadata(
        provider=provider,
        platform=platform,
        tone=tone,
        length=length,
        topic=topic,
        audience=audience,
        include_cta=include_cta,
        cta_text=cta_text,
        return_hashtags=return_hashtags,
        keywords=keywords,
    )
    return result.content


def generate_marketing_content_with_metadata(
    *,
    provider: str,
    platform: str,
    tone: str,
    length: str,
    topic: str,
    audience: str,
    include_cta: bool,
    cta_text: str,
    return_hashtags: bool,
    keywords: str,
) -> MarketingGenerationResult:
    request_id = str(uuid.uuid4())
    start_time = time.perf_counter()

    data = _normalize_request(
        provider=provider,
        platform=platform,
        tone=tone,
        length=length,
        topic=topic,
        audience=audience,
        include_cta=include_cta,
        cta_text=cta_text,
        return_hashtags=return_hashtags,
        keywords=keywords,
    )

    _validate_request(data)

    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(data)
    chain = _build_chain(data.provider)
    llm_config = get_llm_config(data.provider)

    try:
        raw_response = chain.invoke(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            }
        )

        if not isinstance(raw_response, str):
            raise MarketingServiceError(
                "A resposta do modelo veio em formato inválido."
            )

        content = _sanitize_model_output(raw_response)
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        logger.info(
            "Marketing content generated successfully",
            extra={
                "request_id": request_id,
                "provider": data.provider,
                "model": llm_config.model,
                "elapsed_ms": elapsed_ms,
                "request_payload": asdict(data),
            },
        )

        return MarketingGenerationResult(
            request_id=request_id,
            provider=data.provider,
            model=llm_config.model,
            content=content,
            prompt_preview=_truncate_text(user_prompt, 1200),
            elapsed_ms=elapsed_ms,
        )

    except MarketingServiceError:
        raise
    except ValueError:
        raise
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        logger.exception(
            "Unexpected error while generating marketing content",
            extra={
                "request_id": request_id,
                "provider": data.provider,
                "model": llm_config.model,
                "elapsed_ms": elapsed_ms,
            },
        )

        raise MarketingServiceError(
            f"Erro ao gerar conteúdo de marketing. "
            f"request_id={request_id}; provider={data.provider}; "
            f"model={llm_config.model}; detalhe={exc}"
        ) from exc