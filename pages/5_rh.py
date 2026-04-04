from __future__ import annotations

import json
import logging
from pathlib import Path

import streamlit as st

from rh.config import ConfigError, get_app_config
from rh.service import RHAnalysisResult, RHService, RHServiceError

logger = logging.getLogger(__name__)
ANALYSIS_FILE = Path("rh_curriculos.json")


def _init_session_state() -> None:
    defaults = {
        "rh_analysis_result": None,
        "rh_analysis_error": "",
        "rh_analysis_debug": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _render_header() -> None:
    st.set_page_config(page_title="RH", page_icon="", layout="wide")
    st.title("Projeto: RH")
    st.write(
        "Analise currículos e identifique os candidatos que mais se alinham com a vaga. "
        "Envie um ou mais currículos em PDF, DOCX ou TXT e informe os detalhes da vaga para avaliação em lote."
    )


def _show_analysis_result(result: RHAnalysisResult) -> None:
    st.success("Currículo analisado com sucesso.")

    info_columns = st.columns(3)
    info_columns[0].metric("Modelo", result.model)
    info_columns[1].metric("Provider", result.provider)
    info_columns[2].metric("Score", f"{result.alignment_score:.1f}")

    st.markdown("### Resumo do candidato")
    st.write(result.summarization or "Nenhum resumo fornecido pelo modelo.")

    with st.expander("Detalhes completos da análise"):
        st.markdown("**Experiência**")
        st.write(result.details.get("experience_overview", "-"))
        st.markdown("**Habilidades**")
        st.write(result.details.get("skills", "-"))
        st.markdown("**Formação**")
        st.write(result.details.get("education", "-"))
        st.markdown("**Pontos fortes**")
        st.write(result.details.get("strengths", "-"))
        st.markdown("**Pontos de desenvolvimento**")
        st.write(result.details.get("development_opportunities", "-"))
        st.markdown("**Recomendações**")
        st.write(result.details.get("recommendations", "-"))

    with st.expander("JSON da análise"):
        st.json(
            {
                "candidate_name": result.candidate_name,
                "job_title": result.job_title,
                "alignment_score": result.alignment_score,
                "details": result.details,
            }
        )


def _load_saved_analyses() -> list[dict[str, object]]:
    return RHService.load_analyses(ANALYSIS_FILE)


def _render_saved_analyses(analyses: list[dict[str, object]]) -> None:
    if not analyses:
        st.info("Nenhum currículo analisado ainda.")
        return

    st.markdown("---")
    st.subheader("Currículos já avaliados")
    sorted_analyses = RHService.get_top_matches(analyses, top_n=10)

    for index, entry in enumerate(sorted_analyses, start=1):
        score = float(entry.get("alignment_score", 0.0) or 0.0)
        st.markdown(
            f"**{index}. {entry.get('candidate_name', 'Nome não identificado')}** "
            f" vaga: {entry.get('job_title', 'Não informada')}  **Score: {score:.1f}**"
        )
        st.write(entry.get("summarization", "Sem resumo disponível."))
        if index <= 1:
            st.markdown("---")

    if st.button("Baixar avaliações como JSON", use_container_width=True):
        st.download_button(
            label=" Baixar arquivo JSON",
            data=json.dumps(analyses, ensure_ascii=False, indent=2),
            file_name=ANALYSIS_FILE.name,
            mime="application/json",
            key="download_rh_json",
        )


def main() -> None:
    _init_session_state()
    _render_header()

    app_config = get_app_config()
    service = RHService(app_config=app_config)

    with st.form("rh_analysis_form"):
        st.subheader("Dados da vaga")
        job_title = st.text_input("Título da vaga", value="Desenvolvedor(a) Full Stack")
        job_description = st.text_area(
            "Descrição da vaga",
            value=(
                "Buscamos profissional para atuar em projetos de desenvolvimento web, "
                "construção de APIs, colaboração com times multifuncionais e entrega de soluções escaláveis."
            ),
            height=150,
        )
        job_details = st.text_area(
            "Detalhes adicionais da vaga",
            value=(
                "Requisitos: Python, JavaScript, Django ou Flask, experiência com cloud, "
                "boa comunicação e capacidade de trabalhar em equipe."
            ),
            height=120,
        )

        uploaded_files = st.file_uploader(
            "Faça upload de currículos (PDF, DOCX ou TXT)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            help="Envie um ou mais currículos. Cada candidato será analisado e classificado com base na vaga.",
        )

        col_submit, col_clear = st.columns([2, 1])
        with col_submit:
            submit_button = st.form_submit_button("Analisar currículos")
        with col_clear:
            clear_button = st.form_submit_button("Limpar resultados")

    if clear_button:
        st.session_state.rh_analysis_result = None
        st.session_state.rh_analysis_error = ""
        st.experimental_rerun()

    if submit_button:
        if not uploaded_files:
            st.error("Envie pelo menos um currículo em PDF, DOCX ou TXT antes de analisar.")
        elif not job_title.strip() or not job_description.strip():
            st.error("Informe o título e a descrição da vaga.")
        else:
            try:
                results: list[RHAnalysisResult] = []
                error_count = 0
                
                with st.spinner(f"Analisando {len(uploaded_files)} currículo(s)..."):
                    for uploaded_file in uploaded_files:
                        try:
                            candidate_path = Path(uploaded_file.name)
                            candidate_bytes = uploaded_file.read()
                            candidate_path.write_bytes(candidate_bytes)
                            resume_text = service.parse_resume(str(candidate_path))

                            analysis = service.analyze_candidate(
                                job_title=job_title,
                                job_description=job_description,
                                job_details=job_details,
                                resume_text=resume_text,
                            )
                            service.save_analysis(analysis, ANALYSIS_FILE)
                            results.append(analysis)
                            
                            if candidate_path.exists():
                                candidate_path.unlink(missing_ok=True)

                        except Exception as exc:
                            error_count += 1
                            logger.warning(f"Erro ao processar {uploaded_file.name}: {exc}")

                if results:
                    st.success(
                        f"✅ {len(results)} currículo(s) analisado(s) com sucesso!"
                        + (f" ({error_count} erro(s))" if error_count > 0 else "")
                    )
                    
                    # Exibir resultados organizados por score
                    st.markdown("### Resultados da análise em lote")
                    sorted_results = sorted(results, key=lambda r: r.alignment_score, reverse=True)
                    
                    for idx, result in enumerate(sorted_results, start=1):
                        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                        with col1:
                            st.markdown(f"**{idx}. {result.candidate_name}**")
                        with col2:
                            st.metric("Score", f"{result.alignment_score:.1f}")
                        with col3:
                            st.metric("Modelo", result.model.split("-")[0][:8])
                        with col4:
                            with st.expander("📋 Detalhes"):
                                st.write(result.summarization)
                                st.json(result.details)
                    
                    # Opção de download dos resultados
                    results_dict = [
                        {
                            "rank": idx,
                            "candidate_name": r.candidate_name,
                            "alignment_score": r.alignment_score,
                            "summarization": r.summarization,
                            "details": r.details,
                        }
                        for idx, r in enumerate(sorted_results, start=1)
                    ]
                    
                    st.download_button(
                        label="📥 Baixar resultados em JSON",
                        data=json.dumps(results_dict, ensure_ascii=False, indent=2),
                        file_name=f"rh_analise_{job_title.replace(' ', '_')[:30]}.json",
                        mime="application/json",
                        use_container_width=True,
                    )
                    
                else:
                    st.error(f"Nenhum currículo pôde ser processado. {error_count} erro(s) encontrado(s).")

            except ConfigError as exc:
                st.session_state.rh_analysis_error = f"Erro de configuração: {exc}"
                logger.exception("Erro de configuração de RH")
            except Exception as exc:
                st.session_state.rh_analysis_error = (
                    "Erro inesperado ao processar currículos. "
                    "Verifique os logs e tente novamente."
                )
                logger.exception("Erro inesperado no projeto RH")

    if st.session_state.rh_analysis_error:
        st.error(st.session_state.rh_analysis_error)

    saved_analyses = _load_saved_analyses()
    _render_saved_analyses(saved_analyses)

    if st.button("Voltar para a página principal"):
        st.switch_page("app.py")


if __name__ == "__main__":
    main()
