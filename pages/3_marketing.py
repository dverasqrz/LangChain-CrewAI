from __future__ import annotations

import streamlit as st

from marketing.service import MarketingServiceError, generate_marketing_content

st.set_page_config(
    page_title="Marketing",
    page_icon="📢",
    layout="wide",
)

st.title("Projeto: Marketing")
st.write(
    "Gere conteúdo de marketing com LangChain usando Groq ou OpenAI."
)

with st.form("marketing_form"):
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
            options=["Blog", "Instagram", "LinkedIn", "E-mail"],
        )

        tone = st.selectbox(
            "Tom da mensagem",
            options=["Informativo", "Inspirador", "Urgente", "Informal"],
        )

        length = st.selectbox(
            "Comprimento do texto",
            options=["Curto", "Médio", "Longo"],
        )

    with col2:
        topic = st.text_input(
            "Tema ou tópico",
            placeholder="Ex.: saúde mental, exames de rotina, alimentação",
        )

        audience = st.selectbox(
            "Público-alvo",
            options=["Jovens adultos", "Famílias", "Idosos", "Geral"],
        )

        include_cta = st.checkbox("Incluir chamada para ação", value=True)

        cta_text = st.text_input(
            "Texto da chamada para ação",
            placeholder='Ex.: Agendar consulta ou Converse com um especialista',
            disabled=not include_cta,
        )

        return_hashtags = st.checkbox("Retornar hashtags", value=True)

        keywords = st.text_input(
            "Palavras-chave",
            placeholder="Ex.: prevenção, check-up, bem-estar",
        )

    submitted = st.form_submit_button("Gerar conteúdo")

if submitted:
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

        st.success("Conteúdo gerado com sucesso.")
        st.markdown("### Resultado")
        st.write(result)

    except ValueError as exc:
        st.warning(str(exc))

    except EnvironmentError as exc:
        st.error(str(exc))

    except MarketingServiceError as exc:
        st.error(str(exc))

    except Exception as exc:
        st.error(f"Erro inesperado: {exc}")

st.divider()

if st.button("Voltar para a página principal"):
    st.switch_page("app.py")