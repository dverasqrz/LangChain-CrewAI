from __future__ import annotations

import streamlit as st

from marketing.service import MarketingServiceError, generate_marketing_content


st.set_page_config(
    page_title="Marketing",
    page_icon="📢",
    layout="wide",
)


def _init_session_state() -> None:
    if "marketing_result" not in st.session_state:
        st.session_state.marketing_result = ""

    if "marketing_last_payload" not in st.session_state:
        st.session_state.marketing_last_payload = {}

    if "marketing_last_error" not in st.session_state:
        st.session_state.marketing_last_error = ""


def _validate_form_input(
    *,
    topic: str,
    audience: str,
    include_cta: bool,
    cta_text: str,
) -> list[str]:
    errors: list[str] = []

    if not topic.strip():
        errors.append("O campo 'Tema ou tópico' é obrigatório.")

    if not audience.strip():
        errors.append("O campo 'Público-alvo' é obrigatório.")

    if include_cta and not cta_text.strip():
        errors.append(
            "O campo 'Texto da chamada para ação' é obrigatório quando o CTA estiver habilitado."
        )

    return errors


def _render_last_generation_details() -> None:
    payload = st.session_state.get("marketing_last_payload", {})

    if not payload:
        return

    with st.expander("Ver parâmetros da última geração"):
        st.json(payload)


def _clear_result() -> None:
    st.session_state.marketing_result = ""
    st.session_state.marketing_last_payload = {}
    st.session_state.marketing_last_error = ""


_init_session_state()

st.title("Projeto: Marketing")
st.write(
    "Gere conteúdo de marketing com LangChain usando Groq ou OpenAI."
)

with st.form("marketing_form"):
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
        placeholder="Ex.: saúde mental, alimentação saudável, prevenção, exames de rotina",
    )

    keywords = st.text_area(
        "Palavras-chave (SEO)",
        placeholder="Ex.: bem-estar, medicina preventiva, qualidade de vida",
        height=90,
    )

    cta_text = st.text_input(
        "Texto da chamada para ação",
        placeholder="Ex.: Agende uma consulta hoje mesmo.",
        disabled=not include_cta,
    )

    submitted = st.form_submit_button("Gerar conteúdo")

if submitted:
    st.session_state.marketing_last_error = ""

    validation_errors = _validate_form_input(
        topic=topic,
        audience=audience,
        include_cta=include_cta,
        cta_text=cta_text,
    )

    if validation_errors:
        st.session_state.marketing_result = ""
        for error in validation_errors:
            st.warning(error)
    else:
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
                result = generate_marketing_content(
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

            st.session_state.marketing_result = result
            st.session_state.marketing_last_payload = payload
            st.session_state.marketing_last_error = ""

            st.success("Conteúdo gerado com sucesso.")

        except ValueError as exc:
            st.session_state.marketing_result = ""
            st.session_state.marketing_last_error = str(exc)
            st.warning(str(exc))

        except EnvironmentError as exc:
            st.session_state.marketing_result = ""
            st.session_state.marketing_last_error = str(exc)
            st.error(str(exc))

        except MarketingServiceError as exc:
            st.session_state.marketing_result = ""
            st.session_state.marketing_last_error = str(exc)
            st.error(str(exc))

        except Exception as exc:
            st.session_state.marketing_result = ""
            st.session_state.marketing_last_error = str(exc)
            st.error(f"Erro inesperado: {exc}")

if st.session_state.marketing_result:
    st.markdown("### Resultado")
    st.write(st.session_state.marketing_result)

    _render_last_generation_details()

    col_action_1, col_action_2 = st.columns(2)

    with col_action_1:
        if st.button("Limpar resultado"):
            _clear_result()
            st.rerun()

    with col_action_2:
        st.download_button(
            label="Baixar resultado em TXT",
            data=st.session_state.marketing_result,
            file_name="conteudo_marketing.txt",
            mime="text/plain",
        )

elif st.session_state.marketing_last_error:
    with st.expander("Detalhes do último erro"):
        st.write(st.session_state.marketing_last_error)

st.divider()

if st.button("Voltar para a página principal"):
    st.switch_page("app.py")