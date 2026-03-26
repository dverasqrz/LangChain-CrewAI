from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from marketing.config import get_llm_config, validate_provider_environment


class MarketingServiceError(Exception):
    """Erro específico do serviço de marketing."""


def _build_llm(provider: str) -> Any:
    config = get_llm_config(provider)
    validate_provider_environment(provider)

    try:
        if config.provider == "groq":
            from langchain_groq import ChatGroq

            return ChatGroq(
                model=config.model,
                temperature=config.temperature,
            )

        if config.provider == "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=config.model,
                temperature=config.temperature,
            )

        raise ValueError("Provider não suportado.")

    except Exception as exc:
        raise MarketingServiceError(
            f"Falha ao inicializar o modelo '{config.provider}': {exc}"
        ) from exc


def _normalize_text(value: str) -> str:
    return value.strip()


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

    platform = _normalize_text(platform)
    tone = _normalize_text(tone)
    length = _normalize_text(length)
    topic = _normalize_text(topic)
    audience = _normalize_text(audience)
    cta_text = _normalize_text(cta_text)
    keywords = _normalize_text(keywords)

    if not platform:
        raise ValueError("O campo 'platform' é obrigatório.")

    if not tone:
        raise ValueError("O campo 'tone' é obrigatório.")

    if not length:
        raise ValueError("O campo 'length' é obrigatório.")

    if not topic:
        raise ValueError("O campo 'topic' é obrigatório.")

    if not audience:
        raise ValueError("O campo 'audience' é obrigatório.")

    llm = _build_llm(provider)

    keyword_instruction = (
        f"Inclua naturalmente as seguintes palavras-chave no texto: {keywords}."
        if keywords
        else "Não é necessário inserir palavras-chave específicas."
    )

    cta_instruction = (
        f"Inclua uma chamada para ação ao final com a seguinte ideia: {cta_text}."
        if include_cta and cta_text
        else "Não inclua chamada para ação."
    )

    hashtag_instruction = (
        "Ao final, retorne também uma seção separada com hashtags relevantes."
        if return_hashtags
        else "Não retorne hashtags."
    )

    system_prompt = (
        "Você é um especialista sênior em marketing de conteúdo. "
        "Crie textos claros, estratégicos, coerentes com a plataforma e adequados ao público-alvo. "
        "Evite promessas exageradas, evite linguagem genérica e adapte o estilo ao canal."
    )

    user_prompt = f"""
Crie um conteúdo de marketing com as seguintes especificações:

Plataforma de destino: {platform}
Tom da mensagem: {tone}
Comprimento do texto: {length}
Tema ou tópico: {topic}
Público-alvo: {audience}

Regras adicionais:
- Adeque a estrutura ao canal informado.
- O texto deve ser útil, natural e convincente.
- {cta_instruction}
- {hashtag_instruction}
- {keyword_instruction}

Formato esperado:
1. Título ou abertura
2. Conteúdo principal
3. CTA (somente se solicitado)
4. Hashtags (somente se solicitado)
""".strip()

    try:
        response = llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )

        content = getattr(response, "content", None)

        if not content or not isinstance(content, str):
            raise MarketingServiceError(
                "A resposta do modelo veio vazia ou em formato inválido."
            )

        return content.strip()

    except MarketingServiceError:
        raise
    except Exception as exc:
        raise MarketingServiceError(
            f"Erro ao gerar conteúdo de marketing: {exc}"
        ) from exc