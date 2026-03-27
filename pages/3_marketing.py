from __future__ import annotations

import logging

import streamlit as st

from marketing.config import ConfigError, get_app_config, get_llm_config
from marketing.service import (
    MarketingGenerationResult,
    MarketingServiceError,
    generate_marketing_content_with_metadata,
)

logger = logging.getLogger(__name__)


def _init_session_state() -> None:
    defaults = {
        "marketing_result": None,
        "marketing_last_error": "",
        "marketing_debug_data": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _clear_generation_state() -> None:
    st.session_state.marketing_result = None
    st.session_state.marketing_last_error = ""
    st.session_state.marketing_debug_data = None


def _validate_form_input(
    *,
    topic: str,
    include_cta: bool,
    cta_text: str,
    keywords: str,
) -> list[str]:
    errors: list[str] = []

    normalized_topic = topic.strip()
    normalized_cta = cta_text.strip()
    normalized_keywords = keywords.strip()

    if not normalized_topic:
        errors.append("O campo 'Tema ou tópico' é obrigatório.")
    elif len(normalized_topic) < 3:
        errors.append("O campo 'Tema ou tópico' deve ter ao menos 3 caracteres.")
    elif len(normalized_topic) > 300:
        errors.append("O campo 'Tema ou tópico' não pode exceder 300 caracteres.")

    if include_cta and not normalized_cta:
        errors.append(
            "Informe o texto da chamada para ação quando o CTA estiver habilitado."
        )

    if len(normalized_cta) > 200:
        errors.append(
            "O texto da chamada para ação não pode exceder 200 caracteres."
        )

    if len(normalized_keywords) > 500:
        errors.append("O campo 'Palavras-chave' não pode exceder 500 caracteres.")

    return errors


def _render_header() -> None:
    st.set_page_config(
        page_title="Marketing",
        page_icon="📢",
        layout="wide",
    )

    st.title("Projeto: Marketing")
    st.write(
        "Gere conteúdo de marketing com LangChain usando Groq ou OpenAI."
    )


def _render_generation_result(result: MarketingGenerationResult) -> None:
    st.success("Conteúdo gerado com sucesso.")

    info_col_1, info_col_2, info_col_3 = st.columns(3)
    info_col_1.metric("Provider", result.provider)
    info_col_2.metric("Modelo", result.model)
    info_col_3.metric("Tempo", f"{result.elapsed_ms} ms")

    st.markdown("### Resultado")
    st.write(result.content)

    action_col_1, action_col_2 = st.columns(2)

    with action_col_1:
        if st.button("Limpar resultado", use_container_width=True):
            _clear_generation_state()
            st.rerun()

    with action_col_2:
        st.download_button(
            label="Baixar resultado em TXT",
            data=result.content,
            file_name="conteudo_marketing.txt",
            mime="text/plain",
            use_container_width=True,
        )

    debug_data = st.session_state.get("marketing_debug_data")
    app_config = get_app_config()

    if app_config.enable_debug and debug_data:
        with st.expander("Diagnóstico técnico"):
            st.json(debug_data)


def _render_last_error() -> None:
    last_error = st.session_state.get("marketing_last_error", "")

    if not last_error:
        return

    with st.expander("Detalhes do último erro"):
        st.write(last_error)


def _build_debug_data(
    *,
    provider: str,
    result: MarketingGenerationResult,
    payload: dict[str, object],
) -> dict[str, object]:
    llm_config = get_llm_config(provider)

    return {
        "request_id": result.request_id,
        "provider": result.provider,
        "model": result.model,
        "elapsed_ms": result.elapsed_ms,
        "prompt_preview": result.prompt_preview,
        "llm_config": {
            "provider": llm_config.provider,
            "model": llm_config.model,
            "temperature": llm_config.temperature,
            "max_retries": llm_config.max_retries,
            "timeout_seconds": llm_config.timeout_seconds,
        },
        "input_payload": payload,
    }


def _render_form() -> None:
    with st.form("marketing_form", clear_on_submit=False):
        st.subheader("Configuração do conteúdo")

        col1, col2 = st.columns(2)

        with col1:
            provider = st.selectbox(
                "Provedor da LLM",
                options=["groq", "openai"],
                index=0,
                help="Groq como padrão; OpenAI como alternativa.",
            )

            platform = st.selectbox(
                "Plataforma de destino",
                options=["Instagram", "Facebook", "LinkedIn", "Blog", "E-mail"],
            )

            tone = st.selectbox(
                "Tom da mensagem",
                options=[
                    "Normal",
                    "Informativo",
                    "Inspirador",
                    "Urgente",
                    "Informal",
                ],
            )

            length = st.selectbox(
                "Comprimento do texto",
                options=["Curto", "Médio", "Longo"],
            )

        with col2:
            audience = st.selectbox(
                "Público-alvo",
                options=[
                    "Geral",
                    "Jovens adultos",
                    "Famílias",
                    "Idosos",
                    "Adolescentes",
                ],
            )

            include_cta = st.checkbox(
                "Incluir chamada para ação",
                value=True,
            )

            return_hashtags = st.checkbox(
                "Retornar hashtags",
                value=True,
            )

        topic = st.text_input(
            "Tema ou tópico",
            placeholder=(
                "Ex.: saúde mental, alimentação saudável, prevenção, "
                "exames de rotina"
            ),
        )

        keywords = st.text_area(
            "Palavras-chave (SEO)",
            placeholder=(
                "Ex.: bem-estar, medicina preventiva, qualidade de vida"
            ),
            height=90,
        )

        cta_text = st.text_input(
            "Texto da chamada para ação",
            placeholder="Ex.: Agende uma consulta hoje mesmo.",
            disabled=not include_cta,
        )

        submitted = st.form_submit_button(
            "Gerar conteúdo",
            use_container_width=True,
        )

    if not submitted:
        return

    _clear_generation_state()

    validation_errors = _validate_form_input(
        topic=topic,
        include_cta=include_cta,
        cta_text=cta_text,
        keywords=keywords,
    )

    if validation_errors:
        for error in validation_errors:
            st.warning(error)
        return

    payload = {
        "provider": provider,
        "platform": platform,
        "tone": tone,
        "length": length,
        "topic": topic.strip(),
        "audience": audience,
        "include_cta": include_cta,
        "cta_text": cta_text.strip(),
        "return_hashtags": return_hashtags,
        "keywords": keywords.strip(),
    }

    try:
        with st.spinner("Gerando conteúdo..."):
            result = generate_marketing_content_with_metadata(**payload)

        st.session_state.marketing_result = result
        st.session_state.marketing_debug_data = _build_debug_data(
            provider=provider,
            result=result,
            payload=payload,
        )

    except ValueError as exc:
        st.session_state.marketing_last_error = str(exc)
        st.warning(str(exc))

    except ConfigError as exc:
        st.session_state.marketing_last_error = str(exc)
        st.error(f"Erro de configuração: {exc}")

    except MarketingServiceError as exc:
        st.session_state.marketing_last_error = str(exc)
        st.error(str(exc))

    except Exception as exc:
        logger.exception("Unexpected UI error during marketing generation")
        st.session_state.marketing_last_error = str(exc)
        st.error(f"Erro inesperado na interface: {exc}")


def _render_navigation() -> None:
    st.divider()

    if st.button("Voltar para a página principal", use_container_width=True):
        st.switch_page("app.py")


def main() -> None:
    _init_session_state()
    _render_header()
    _render_form()

    result = st.session_state.get("marketing_result")
    if result is not None:
        _render_generation_result(result)
    else:
        _render_last_error()

    _render_navigation()


if __name__ == "__main__":
    main()