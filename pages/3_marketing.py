from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Marketing", page_icon="📢", layout="wide")

st.title("Projeto: Marketing")
st.write("Esta é a página do projeto de Marketing.")

if st.button("Voltar para a página principal"):
    st.switch_page("app.py")