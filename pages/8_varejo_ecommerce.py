from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Varejo e E-commerce", page_icon="🛒", layout="wide")

st.title("Projeto: Varejo e E-commerce")
st.write("Esta é a página do projeto de Varejo e E-commerce.")

if st.button("Voltar para a página principal"):
    st.switch_page("app.py")