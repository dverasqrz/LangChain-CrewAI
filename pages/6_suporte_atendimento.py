from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Suporte e Atendimento", page_icon="🎧", layout="wide")

st.title("Projeto: Suporte e Atendimento")
st.write("Esta é a página do projeto de Suporte e Atendimento.")

if st.button("Voltar para a página principal"):
    st.switch_page("app.py")