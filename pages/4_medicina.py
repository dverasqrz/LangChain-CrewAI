from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Medicina", page_icon="🩺", layout="wide")

st.title("Projeto: Medicina")
st.write("Esta é a página do projeto de Medicina.")

if st.button("Voltar para a página principal"):
    st.switch_page("app.py")