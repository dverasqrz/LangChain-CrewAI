from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Portfólio de Projetos",
    page_icon="📁",
    layout="wide",
)

PROJECTS = [
    {
        "name": "Educação",
        "page": "pages/1_educacao.py",
        "description": "Projeto voltado para soluções educacionais.",
    },
    {
        "name": "Finanças",
        "page": "pages/2_financas.py",
        "description": "Projeto relacionado a análise e automação financeira.",
    },
    {
        "name": "Marketing",
        "page": "pages/3_marketing.py",
        "description": "Projeto com foco em estratégias e automações de marketing.",
    },
    {
        "name": "Medicina",
        "page": "pages/4_medicina.py",
        "description": "Projeto para casos de uso na área de saúde.",
    },
    {
        "name": "RH",
        "page": "pages/5_rh.py",
        "description": "Projeto para recrutamento, seleção e gestão de pessoas.",
    },
    {
        "name": "Suporte e Atendimento",
        "page": "pages/6_suporte_atendimento.py",
        "description": "Projeto para atendimento ao cliente e suporte automatizado.",
    },
    {
        "name": "Turismo",
        "page": "pages/7_turismo.py",
        "description": "Projeto para experiências e serviços do setor de turismo.",
    },
    {
        "name": "Varejo e E-commerce",
        "page": "pages/8_varejo_ecommerce.py",
        "description": "Projeto para vendas, catálogo e experiência do cliente.",
    },
]

st.title("Página Principal de Projetos")
st.write(
    "Selecione um projeto abaixo para abrir a respectiva página no Streamlit."
)

for project in PROJECTS:
    with st.container(border=True):
        st.subheader(project["name"])
        st.write(project["description"])
        st.page_link(project["page"], label=f"Abrir {project['name']}", icon="🚀")