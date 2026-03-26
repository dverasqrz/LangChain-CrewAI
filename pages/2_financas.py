from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Finanças", page_icon="💰", layout="wide")

st.title("Projeto: Finanças")
st.write("Esta é a página do projeto de Finanças.")

if st.button("Voltar para a página principal"):
    st.switch_page("app.py")