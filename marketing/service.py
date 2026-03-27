from __future__ import annotations

from dataclasses import dataclass

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from marketing.config import ConfigError, get_llm_config, validate_provider_environment


class MarketingServiceError(Exception):
    """Erro específico do serviço de marketing."""


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


def _normalize_text(value: str) -> str:
    return value.strip()


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
        provider=_normalize_text(provider).lower(),
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


def _validate_request(data: MarketingContentRequest) -> None:
    if not data.provider:
        raise ValueError("O campo 'provider' é obrigatório.")

    if data.provider not in {"groq", "openai"}:
        raise ValueError("O campo 'provider' deve ser 'groq' ou 'openai'.")

    if not data.platform:
        raise ValueError("O campo 'platform' é obrigatório.")

    if not data.tone:
        raise ValueError("O campo 'tone' é obrigatório.")

    if not data.length:
        raise ValueError("O campo 'length' é obrigatório.")

    if not data.topic:
        raise ValueError("O campo 'topic' é obrigatório.")

    if not data.audience:
        raise ValueError("O campo 'audience' é obrigatório.")

    if data.include_cta and not data.cta_text:
        raise ValueError(
            "O campo 'cta_text' é obrigatório quando 'include_cta' estiver marcado."
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
            f"Falha ao inicializar o modelo '{config.provider}': {exc}"
        ) from exc


def _build_system_prompt() -> str:
    return (
        "Você é um redator profissional especializado em marketing de conteúdo. "
        "Sua tarefa é produzir textos claros, estratégicos, coerentes com a plataforma, "
        "com o público-alvo e com o objetivo de comunicação. "
        "Evite clichês, promessas exageradas, linguagem artificial ou vazia. "
        "Adapte vocabulário, estrutura e intensidade ao canal informado. "
        "Quando solicitado, inclua CTA e hashtags de forma natural e útil."
    )


def _build_cta_instruction(data: MarketingContentRequest) -> str:
    if not data.include_cta:
        return "Não inclua chamada para ação."

    return (
        f"Inclua uma chamada para ação ao final com a seguinte orientação: "
        f"{data.cta_text}."
    )


def _build_hashtag_instruction(data: MarketingContentRequest) -> str:
    if data.return_hashtags:
        return "Ao final, retorne também uma seção separada com hashtags relevantes."

    return "Não retorne hashtags."


def _build_keyword_instruction(data: MarketingContentRequest) -> str:
    if data.keywords:
        return (
            "Inclua naturalmente as seguintes palavras-chave ao longo do texto: "
            f"{data.keywords}."
        )

    return "Não é necessário inserir palavras-chave específicas."


def _build_user_prompt(data: MarketingContentRequest) -> str:
    cta_instruction = _build_cta_instruction(data)
    hashtag_instruction = _build_hashtag_instruction(data)
    keyword_instruction = _build_keyword_instruction(data)

    return f"""
Crie um conteúdo de marketing com as seguintes especificações:

Plataforma de destino: {data.platform}
Tom da mensagem: {data.tone}
Comprimento do texto: {data.length}
Tema ou tópico: {data.topic}
Público-alvo: {data.audience}

Regras adicionais:
- Adeque a estrutura ao canal informado.
- O texto deve ser útil, natural e convincente.
- Mantenha consistência com o público-alvo e com o tom escolhido.
- Evite excesso de adjetivos, frases genéricas e exageros publicitários.
- {cta_instruction}
- {hashtag_instruction}
- {keyword_instruction}

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


def _invoke_chain(
    *,
    provider: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    chain = _build_chain(provider)

    try:
        response = chain.invoke(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            }
        )
    except Exception as exc:
        raise MarketingServiceError(
            f"Erro ao invocar a chain do provider '{provider}': {exc}"
        ) from exc

    if not response or not isinstance(response, str):
        raise MarketingServiceError(
            "A resposta do modelo veio vazia ou em formato inválido."
        )

    return response.strip()


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
    """
    Gera conteúdo de marketing com base nos parâmetros da interface.
    """

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

    try:
        return _invoke_chain(
            provider=data.provider,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
    except MarketingServiceError:
        raise
    except Exception as exc:
        raise MarketingServiceError(
            f"Erro ao gerar conteúdo de marketing: {exc}"
        ) from exc