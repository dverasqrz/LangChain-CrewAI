from __future__ import annotations

import logging
from pathlib import Path

import streamlit as st

from suporte_atendimento.config import ConfigError, get_app_config
from suporte_atendimento.service import (
    IndexInfo,
    SuporteAtendimentoService,
    SuporteAtendimentoServiceError,
    UpsertRequest,
    UpsertResult,
    QueryRequest,
    QueryResult,
)

logger = logging.getLogger(__name__)


def _init_session_state() -> None:
    defaults = {
        "upsert_result": None,
        "upsert_last_error": "",
        "index_check_result": None,
        "index_list_result": None,
        "query_result": None,
        "query_last_error": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _clear_upsert_state() -> None:
    st.session_state.upsert_result = None
    st.session_state.upsert_last_error = ""


def _validate_upsert_input(
    *,
    index_name: str,
    uploaded_file: object,
    chunk_size: int,
    overlap: int,
) -> list[str]:
    errors: list[str] = []

    if not index_name.strip():
        errors.append("O nome do índice é obrigatório.")
    elif len(index_name.strip()) < 3:
        errors.append("O nome do índice deve ter pelo menos 3 caracteres.")
    elif len(index_name.strip()) > 100:
        errors.append("O nome do índice não pode exceder 100 caracteres.")

    if uploaded_file is None:
        errors.append("Selecione um arquivo PDF para upload.")

    if chunk_size < 100 or chunk_size > 900:
        errors.append("O tamanho do chunk deve estar entre 100 e 900 caracteres.")

    if overlap < 0 or overlap > 200:
        errors.append("A sobreposição deve estar entre 0 e 200 caracteres.")

    if overlap >= chunk_size:
        errors.append("A sobreposição deve ser menor que o tamanho do chunk.")

    return errors


def _render_header() -> None:
    st.set_page_config(
        page_title="Suporte e Atendimento",
        page_icon="🎧",
        layout="wide",
    )

    st.title("Projeto: Suporte e Atendimento")
    st.write(
        "Faça upload de documentos PDF e indexe-os no Pinecone para busca semântica."
    )


def _render_upsert_result(result: UpsertResult) -> None:
    st.success("Documento indexado com sucesso no Pinecone.")

    col1, col2, col3 = st.columns(3)
    col1.metric("Índice", result.index_name)
    col2.metric("Namespace", result.namespace)
    col3.metric("Chunks", result.chunks_count)

    col4, col5 = st.columns(2)
    col4.metric("Caracteres", f"{result.total_characters:,}")
    col5.metric("Provedor/Modelo", f"{result.embedding_provider}/{result.embedding_model}")

    col6, col7, col8 = st.columns(3)
    col6.metric("Tipo de Vetor", result.vector_type)
    col7.metric("Métrica", result.metric)
    col8.metric("Pod Type", result.pod_type or "padrão")

    st.markdown("### Detalhes do Indexamento")
    st.write(f"**ID do Documento:** {result.document_id}")
    st.write(f"**ID da Requisição:** {result.request_id}")

    if st.button("Limpar resultado", use_container_width=True):
        _clear_upsert_state()
        st.rerun()


def _render_index_check_result(exists: bool, index_name: str) -> None:
    if exists:
        st.success(f"O índice '{index_name}' existe no Pinecone.")
    else:
        st.warning(f"O índice '{index_name}' não foi encontrado no Pinecone.")


def _render_index_list_result(indexes: list[IndexInfo]) -> None:
    if not indexes:
        st.info("Nenhum índice encontrado no Pinecone.")
        return

    st.markdown("### Índices no Pinecone")
    for index in indexes:
        with st.expander(f"📁 {index.name}"):
            col1, col2, col3 = st.columns(3)
            col1.metric("Dimensão", index.dimension)
            col2.metric("Métrica", index.metric)
            st.write("**Status:**", str(index.status))
            st.write("**Pod Type:**", str(index.pod_type))
            st.write("**Pod Count:**", str(index.pod_count))
            st.write("**Replica Count:**", str(index.replica_count))
            st.markdown("**Informações completas do índice (raw)**")
            st.json(index.raw)


def _render_last_error() -> None:
    last_error = st.session_state.get("upsert_last_error", "")

    if not last_error:
        return

    with st.expander("Detalhes do último erro"):
        st.write(last_error)


def _render_upsert_form() -> None:
    service = SuporteAtendimentoService()
    app_config = get_app_config()

    # ===== SELEÇÃO DE PROVIDER E MODELOS (FORA DO FORM) =====
    st.subheader("Configuração do Indexamento")
    
    col_provider, col_model = st.columns(2)
    
    with col_provider:
        embedding_provider = st.selectbox(
            "🤖 Provedor de Embedding",
            options=["groq", "openai", "gemini", "ollama"],
            index=0,
            key="upsert_provider",
            help="Provedor de IA para gerar embeddings.",
        )

    # Carregar modelos disponíveis para o provedor selecionado
    available_models = service.get_available_models(embedding_provider)
    embedding_model_options = [model["id"] for model in available_models if model.get("type") == "embedding"]
    
    if not embedding_model_options:
        # Fallback para modelos conhecidos se não conseguir carregar
        embedding_model_options = [model["name"] for model in service.get_available_embedding_models()]

    with col_model:
        embedding_model = st.selectbox(
            "🧠 Modelo de Embedding",
            options=embedding_model_options,
            index=0,
            key="upsert_model",
            help="Modelo usado para gerar embeddings.",
        )

    # ===== FORM COMEÇA AQUI =====
    with st.form("upsert_form", clear_on_submit=False):
        col1, col2 = st.columns(2)

        # Seleção automatizada do índice (não digitar manualmente)
        existing_indexes = []
        try:
            existing_indexes = [idx.name for idx in service.list_indexes()]
        except SuporteAtendimentoServiceError:
            existing_indexes = []

        if existing_indexes:
            index_name = st.selectbox(
                "Nome do Índice Pinecone",
                options=existing_indexes,
                index=0,
                help="Selecione o índice para usar em upload de documentos.",
            )
            create_new_index = False
        else:
            st.warning("Nenhum índice disponível. Você pode criar um novo abaixo.")
            create_new_index = st.checkbox("Criar novo índice", value=True)
            if create_new_index:
                index_name = st.text_input(
                    "Nome do Novo Índice",
                    placeholder="Ex.: suporte-docs",
                    help="Nome do novo índice a ser criado.",
                )
                new_vector_type = st.selectbox(
                    "Tipo de Vetor (novo índice)",
                    options=["dense", "sparse"],
                    index=0,
                    help="Tipo de vetor para o novo índice.",
                )
                new_dimension = st.number_input(
                    "Dimensão (novo índice)",
                    min_value=1,
                    max_value=2048,
                    value=1536,
                    help="Comprimento do vetor para o novo índice.",
                )
                new_metric = st.selectbox(
                    "Métrica (novo índice)",
                    options=["cosine", "dotproduct", "euclidean"],
                    index=0,
                    help="Métrica para o novo índice.",
                )
                new_cloud = st.selectbox(
                    "Cloud (novo índice)",
                    options=["aws"],
                    index=0,
                    help="Nuvem para o novo índice.",
                )
                new_region = st.selectbox(
                    "Região (novo índice)",
                    options=["us-east-1"],
                    index=0,
                    help="Região para o novo índice.",
                )
                new_deletion_protection = st.checkbox(
                    "Bloqueio de exclusão (novo índice)",
                    value=False,
                    help="Proteção contra exclusão para o novo índice.",
                )
            else:
                index_name = ""
                new_vector_type = "dense"
                new_dimension = 1536
                new_metric = "cosine"
                new_cloud = "aws"
                new_region = "us-east-1"
                new_deletion_protection = False

        # Parâmetros adicionais com valores padrão
        namespace = st.text_input(
            "Namespace (opcional)",
            placeholder="Ex.: faq-clientes",
            value="default",
            help="Namespace para organizar os vetores. Se vazio, usa o nome do arquivo.",
        )

        document_id = st.text_input(
            "ID do Documento (opcional)",
            placeholder="Ex.: manual-atendimento-v1",
            value="",
            help="Identificador único do documento. Se vazio, usa o nome do arquivo.",
        )

        vector_type = st.selectbox(
            "Tipo de Vetor",
            options=["dense", "sparse"],
            index=0,
            help="Tipo de vetor: dense (padrão) ou sparse.",
        )

        metric = st.selectbox(
            "Métrica",
            options=["cosine", "dotproduct", "euclidean"],
            index=0,
            help="Métrica de similaridade para consulta.",
        )

        pod_type = st.selectbox(
            "Pod type (opcional)",
            options=["", "p1", "p2", "p4"],
            index=0,
            help="Tipo de pod (se não souber, deixe em branco).",
        )

        with col2:
            chunk_size = st.number_input(
                "Tamanho do Chunk",
                min_value=100,
                max_value=900,
                value=app_config.chunking.chunk_size,
                help="Tamanho máximo de cada chunk em caracteres.",
            )

            overlap = st.number_input(
                "Sobreposição",
                min_value=0,
                max_value=200,
                value=app_config.chunking.overlap,
                help="Sobreposição entre chunks em caracteres.",
            )

        uploaded_file = st.file_uploader(
            "Selecione o arquivo PDF",
            type=["pdf"],
            help="Arquivo PDF a ser processado e indexado.",
        )

        submitted = st.form_submit_button(
            "Indexar Documento",
            use_container_width=True,
        )

    if not submitted:
        return

    _clear_upsert_state()

    # Validação do índice
    if create_new_index:
        if not index_name.strip():
            st.warning("Informe o nome do novo índice.")
            return
        # Criar o índice primeiro
        try:
            service.create_index(
                index_name=index_name.strip(),
                vector_type=new_vector_type,
                dimension=new_dimension,
                metric=new_metric,
                serverless_cloud=new_cloud,
                serverless_region=new_region,
                deletion_protection=new_deletion_protection,
            )
            st.success(f"Índice '{index_name.strip()}' criado com sucesso.")
        except SuporteAtendimentoServiceError as exc:
            st.error(f"Erro ao criar índice: {exc}")
            return
    else:
        if not index_name.strip():
            st.warning("Selecione um índice existente.")
            return

    validation_errors = _validate_upsert_input(
        index_name=index_name,
        uploaded_file=uploaded_file,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    if validation_errors:
        for error in validation_errors:
            st.warning(error)
        return

    # Salva o arquivo temporariamente
    temp_path = f"temp_{uploaded_file.name}"
    try:
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        request = UpsertRequest(
            index_name=index_name.strip(),
            file_path=temp_path,
            namespace=namespace.strip() or None,
            document_id=document_id.strip() or None,
            chunk_size=chunk_size,
            overlap=overlap,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            vector_type=vector_type,
            metric=metric,
            pod_type=pod_type or None,
        )

        with st.spinner("Processando documento e indexando..."):
            result = service.upsert_document(request)

        st.session_state.upsert_result = result

    except ValueError as exc:
        st.session_state.upsert_last_error = str(exc)
        st.warning(str(exc))

    except ConfigError as exc:
        st.session_state.upsert_last_error = str(exc)
        st.error(f"Erro de configuração: {exc}")

    except SuporteAtendimentoServiceError as exc:
        st.session_state.upsert_last_error = str(exc)
        st.error(str(exc))

    except Exception as exc:
        logger.exception("Unexpected UI error during document upsert")
        st.session_state.upsert_last_error = str(exc)
        st.error(f"Erro inesperado na interface: {exc}")

    finally:
        # Remove arquivo temporário
        if Path(temp_path).exists():
            Path(temp_path).unlink()


def _render_index_management() -> None:
    service = SuporteAtendimentoService()

    st.subheader("Gerenciamento de Índices")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Verificar Índice")
        check_index_name = st.text_input(
            "Nome do índice para verificar",
            key="check_index_input",
        )

        if st.button("Verificar", use_container_width=True):
            if not check_index_name.strip():
                st.warning("Informe o nome do índice.")
            else:
                exists = service.check_index_exists(check_index_name.strip())
                st.session_state.index_check_result = (exists, check_index_name.strip())

    with col2:
        st.markdown("### Criar Índice")
        create_index_name = st.text_input("Nome do Índice a Criar", key="create_index_name")
        create_vector_type = st.selectbox(
            "Tipo de Vetor",
            options=["dense", "sparse"],
            index=0,
            help="Dense é o padrão; Sparse para índices esparsos.",
            key="create_index_vector_type",
        )
        create_dimension = st.number_input(
            "Dimensão",
            min_value=1,
            max_value=2048,
            value=1536,
            key="create_index_dimension",
            help="Comprimento do vetor. Quanto maior, mais consumo de memória.",
        )
        create_metric = st.selectbox(
            "Métrica",
            options=["cosine", "dotproduct", "euclidean"],
            index=0,
            key="create_index_metric",
            help="Como medir similaridade entre vetores.",
        )

        create_cloud = st.selectbox(
            "Cloud Provider",
            options=["aws"],
            index=0,
            key="create_index_cloud",
            help="Nuvem onde o Pinecone será provisionado.",
        )
        create_region = st.selectbox(
            "Região",
            options=["us-east-1"],
            index=0,
            key="create_index_region",
            help="Região AWS onde o indexador será criado.",
        )
        create_deletion_protection = st.checkbox(
            "Bloqueio de exclusão (deletion protection)",
            value=False,
            key="create_index_deletion_protection",
            help="Evita exclusão acidental; padrão false.",
        )

        if st.button("Criar Índice", use_container_width=True):
            try:
                if not create_index_name.strip():
                    st.warning("Informe o nome do índice para criar.")
                else:
                    service.create_index(
                        index_name=create_index_name.strip(),
                        vector_type=create_vector_type,
                        dimension=create_dimension,
                        metric=create_metric,
                        serverless_cloud=create_cloud,
                        serverless_region=create_region,
                        deletion_protection=create_deletion_protection,
                    )
                    st.success(
                        f"Índice '{create_index_name.strip()}' criado: "
                        f"vector_type={create_vector_type}, dim={create_dimension}, "
                        f"metric={create_metric}, cloud={create_cloud}, region={create_region}, "
                        f"deletion_protection={create_deletion_protection}."
                    )
            except SuporteAtendimentoServiceError as exc:
                st.error(str(exc))

        st.markdown("### Listar Índices")
        if st.button("Listar todos os índices", use_container_width=True):
            try:
                indexes = service.list_indexes()
                st.session_state.index_list_result = indexes
            except SuporteAtendimentoServiceError as exc:
                st.error(str(exc))

        st.markdown("### Deletar Índice(s)")
        delete_index_names = st.text_input(
            "Nome(s) do(s) índice(s) a deletar (separado por vírgula)",
            key="delete_index_names",
        )

        if st.button("Deletar Índices", use_container_width=True):
            if not delete_index_names.strip():
                st.warning("Informe pelo menos um índice para deletar.")
            else:
                raw_names = [n.strip() for n in delete_index_names.split(",") if n.strip()]
                success = []
                errors = []

                for name in raw_names:
                    try:
                        service.delete_index(name)
                        success.append(name)
                    except SuporteAtendimentoServiceError as exc:
                        errors.append(f"{name}: {exc}")

                if success:
                    st.success("Índice(s) deletado(s): " + ", ".join(success))

                if errors:
                    st.error("Erros: " + "; ".join(errors))

    # Resultados
    check_result = st.session_state.get("index_check_result")
    if check_result:
        exists, name = check_result
        _render_index_check_result(exists, name)

    list_result = st.session_state.get("index_list_result")
    if list_result is not None:
        _render_index_list_result(list_result)


def _render_query_assistant() -> None:
    service = SuporteAtendimentoService()

    st.subheader("🔍 Consulta ao Database Pinecone")

    st.markdown("""
    Esta ferramenta permite fazer **busca semântica** no seu database vetorial do Pinecone.
    Digite uma pergunta ou texto, e o sistema encontrará os documentos mais relevantes
    baseados no significado, não apenas nas palavras exatas.
    """)

    # Carregar índices existentes
    existing_indexes = []
    try:
        existing_indexes = [idx.name for idx in service.list_indexes()]
    except SuporteAtendimentoServiceError:
        existing_indexes = []

    if not existing_indexes:
        st.warning("Nenhum índice disponível. Crie um índice primeiro.")
        return

    # Modelos de embedding disponíveis
    available_embedding_models = service.get_available_embedding_models()

    # Seção explicativa dos parâmetros
    with st.expander("📚 Entenda os Parâmetros de Busca", expanded=False):
        st.markdown("""
        ### 🎯 **Top K**
        Número máximo de documentos a retornar.
        - **Exemplo:** Se Top K = 3, você verá os 3 documentos mais relevantes
        - **Quando usar:** Para limitar resultados e focar nos mais importantes

        ### 🔄 **Modo de Seleção**
        - **top_k:** Busca simples por similaridade (mais rápido)
        - **mmr:** Relevância Marginal Máxima - equilibra relevância e diversidade

        ### 🎲 **Fetch K (apenas para MMR)**
        Número de documentos candidatos antes de aplicar MMR.
        - **Exemplo:** Fetch K = 10, Top K = 3 → Seleciona os 3 mais diversos dos 10 mais relevantes
        - **Quando usar:** Para evitar que documentos muito similares dominem os resultados

        ### ⚖️ **MMR Lambda**
        Balanceia entre relevância e diversidade (0.0 a 1.0):
        - **0.0:** Só relevância (pode retornar documentos muito similares)
        - **0.5:** Equilíbrio ideal
        - **1.0:** Só diversidade (pode retornar documentos menos relevantes)

        ### 📄 **Dedup Max por Documento**
        Máximo de trechos (chunks) por documento único.
        - **Exemplo:** Se um documento foi dividido em 10 chunks e Dedup = 2, no máximo 2 chunks desse documento aparecerão

        ### 🎯 **Score Threshold**
        Limite mínimo de similaridade (0.0 a 1.0):
        - **Exemplo:** 0.7 → Só retorna documentos com similaridade ≥ 70%
        - **Quando usar:** Para filtrar resultados muito distantes da consulta

        ### 🏷️ **Filtro de Metadados**
        Busca apenas em documentos com metadados específicos.
        - **Exemplo:** Document ID = "manual-rh" → Só busca no manual de RH
        """)

    # ===== SELEÇÃO DE PROVIDER E MODELOS (FORA DO FORM) =====
    col_provider_query, col_model_query = st.columns(2)
    
    with col_provider_query:
        embedding_provider = st.selectbox(
            "🤖 Provedor de Embedding",
            options=["groq", "openai", "gemini", "ollama"],
            index=0,
            key="query_provider",
            help="Provedor de IA para gerar embeddings da consulta.",
        )

    # Carregar modelos disponíveis para o provedor selecionado
    available_models = service.get_available_models(embedding_provider)
    embedding_model_options = [model["id"] for model in available_models if model.get("type") == "embedding"]
    
    if not embedding_model_options:
        # Fallback para modelos conhecidos se não conseguir carregar
        embedding_model_options = [model["name"] for model in service.get_available_embedding_models()]

    with col_model_query:
        embedding_model = st.selectbox(
            "🧠 Modelo de Embedding",
            options=embedding_model_options,
            index=0,
            key="query_model",
            help="Modelo usado para gerar embeddings da consulta.",
        )

    # ===== FORM COMEÇA AQUI =====
    with st.form("query_form", clear_on_submit=False):
        col1, col2 = st.columns(2)

        with col1:
            index_name = st.selectbox(
                "📁 Nome do Índice Pinecone",
                options=existing_indexes,
                index=0,
                help="Selecione o índice onde estão armazenados seus documentos vetoriais.",
            )

            query_text = st.text_area(
                "🔍 Texto da Consulta",
                placeholder="Ex.: Como funciona o processo de recrutamento?\nEx.: Quais são os benefícios oferecidos?",
                help="Digite sua pergunta ou descrição. O sistema buscará documentos com significado similar.",
                height=100,
            )

            namespace = st.text_input(
                "🏷️ Namespace (opcional)",
                placeholder="Ex.: rh, vendas, suporte",
                value="",
                help="Agrupamento lógico dos documentos. Deixe vazio para buscar em todos os namespaces.",
            )

            top_k = st.number_input(
                "🎯 Top K",
                min_value=1,
                max_value=20,
                value=5,
                help="Quantos documentos você quer ver? Recomendado: 3-7 para análise focada.",
            )

        with col2:
            selection_mode = st.selectbox(
                "🔄 Modo de Seleção",
                options=["top_k", "mmr"],
                index=0,
                help="Top K: busca rápida por similaridade. MMR: evita repetições e aumenta diversidade.",
            )

            fetch_k = st.number_input(
                "🎲 Fetch K (para MMR)",
                min_value=1,
                max_value=50,
                value=10,
                help="Candidatos iniciais para MMR. Deve ser maior que Top K. Ex: 20 candidatos → 5 finais.",
            )

            mmr_lambda = st.slider(
                "⚖️ MMR Lambda",
                min_value=0.0,
                max_value=1.0,
                value=0.5,
                step=0.1,
                help="0.0 = só relevância, 1.0 = só diversidade. 0.5 = equilíbrio perfeito.",
            )

            dedup_max_per_document = st.number_input(
                "📄 Dedup Max por Documento",
                min_value=1,
                max_value=10,
                value=2,
                help="Máximo de trechos por documento. Evita que um documento domine os resultados.",
            )

            score_threshold = st.slider(
                "🎯 Score Threshold",
                min_value=0.0,
                max_value=1.0,
                value=0.0,
                step=0.01,
                help="Filtra documentos pouco relevantes. 0.0 = todos, 0.8 = só muito similares.",
            )

        # Filtro de metadados (simplificado)
        st.markdown("### 🏷️ Filtro de Metadados (opcional)")
        col3, col4 = st.columns(2)
        with col3:
            filter_document_id = st.text_input(
                "Document ID",
                placeholder="Ex.: manual-rh-2024, contrato-vendas",
                help="Busque apenas em documentos específicos. Útil para consultas direcionadas.",
            )
        with col4:
            st.markdown("""
            **💡 Dica:** Use filtros para consultas precisas:
            - Document ID: "politica-rh" → só política de RH
            - Namespace: "vendas" → só documentos de vendas
            """)

        submitted = st.form_submit_button(
            "🔍 Consultar Database",
            use_container_width=True,
        )

    if not submitted:
        return

    # Construir filtro
    filter_metadata = None
    if filter_document_id.strip():
        filter_metadata = {"document_id": {"$eq": filter_document_id.strip()}}

    request = QueryRequest(
        index_name=index_name,
        query_text=query_text.strip(),
        namespace=namespace.strip() or None,
        top_k=top_k,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        filter_metadata=filter_metadata,
        selection_mode=selection_mode,
        fetch_k=fetch_k,
        mmr_lambda=mmr_lambda,
        dedup_max_per_document=dedup_max_per_document,
        score_threshold=score_threshold,
    )

    try:
        with st.spinner("Consultando database..."):
            result = service.query_database(request)

        st.success("Consulta realizada com sucesso!")

        col1, col2, col3 = st.columns(3)
        col1.metric("Índice", result.index_name)
        col2.metric("Namespace", result.namespace)
        col3.metric("Documentos", result.total_docs)

        if result.retrieved_docs:
            st.markdown("### Documentos Recuperados")
            for i, doc in enumerate(result.retrieved_docs, 1):
                with st.expander(f"Documento {i} - Score: {getattr(doc, 'score', 'N/A'):.3f}"):
                    st.write(f"**Conteúdo:** {doc.page_content}")
                    st.write(f"**Metadados:** {doc.metadata}")
        else:
            st.info("Nenhum documento encontrado para a consulta.")

        st.write(f"**Tempo de Execução:** {result.execution_time_s:.2f}s")

        # Dicas práticas baseadas nos resultados
        if result.total_docs > 0:
            with st.expander("💡 Dicas para Melhorar suas Consultas", expanded=False):
                st.markdown(f"""
                ### 📊 **Análise dos Resultados**
                - **Documentos encontrados:** {result.total_docs}
                - **Tempo de resposta:** {result.execution_time_s:.2f}s

                ### 🎯 **Otimização de Parâmetros**
                - **Poucos resultados?** → Diminua Score Threshold ou aumente Top K
                - **Muitos resultados similares?** → Use MMR com Lambda = 0.7
                - **Resultados irrelevantes?** → Aumente Score Threshold para 0.6-0.8
                - **Documento específico?** → Use filtros de Document ID ou Namespace

                ### 🔧 **Configurações Recomendadas**
                - **Busca geral:** Top K = 5, Score Threshold = 0.0, Modo = top_k
                - **Busca precisa:** Top K = 3, Score Threshold = 0.7, Modo = mmr
                - **Exploração:** Top K = 10, MMR Lambda = 0.3, Fetch K = 20
                """)

    except SuporteAtendimentoServiceError as exc:
        st.error(f"Erro na consulta: {exc}")
    except Exception as exc:
        logger.exception("Unexpected query error")
        st.error(f"Erro inesperado: {exc}")


def _render_navigation() -> None:
    st.divider()

    if st.button("Voltar para a página principal", use_container_width=True):
        st.switch_page("app.py")


def main() -> None:
    _init_session_state()
    _render_header()

    tab1, tab2, tab3 = st.tabs(["📄 Indexar Documento", "📁 Gerenciar Índices", "🔍 Consultar Database"])

    with tab1:
        _render_upsert_form()

        result = st.session_state.get("upsert_result")
        if result is not None:
            _render_upsert_result(result)
        else:
            _render_last_error()

    with tab2:
        _render_index_management()

    with tab3:
        _render_query_assistant()

    _render_navigation()


if __name__ == "__main__":
    main()