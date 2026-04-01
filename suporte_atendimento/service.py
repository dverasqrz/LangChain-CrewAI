from __future__ import annotations

import logging
import os
import uuid
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

import ollama
import requests
from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from pinecone import Pinecone, ServerlessSpec

from suporte_atendimento.config import (
    AIProvidersConfig,
    AppConfig,
    ChunkingConfig,
    ConfigError,
    get_app_config,
    validate_embedding_model,
)

# Suppress transformers deprecation warnings
warnings.filterwarnings(
    "ignore",
    message="Accessing `__path__` from `.*`",
    category=Warning,
)

try:
    import transformers

    from transformers.utils import logging as transformers_logging

    transformers_logging.set_verbosity_error()
except Exception:
    pass


class SuporteAtendimentoServiceError(Exception):
    """Erro de negócio ou execução do serviço de suporte e atendimento."""


@dataclass(frozen=True)
class UpsertRequest:
    index_name: str
    file_path: str
    namespace: str | None = None
    document_id: str | None = None
    chunk_size: int | None = None
    overlap: int | None = None
    embedding_provider: str | None = None
    embedding_model: str | None = None
    vector_type: str | None = None
    metric: str | None = None
    pod_type: str | None = None


@dataclass(frozen=True)
class UpsertResult:
    request_id: str
    index_name: str
    namespace: str
    document_id: str
    chunks_count: int
    total_characters: int
    embedding_provider: str
    embedding_model: str
    vector_type: str
    metric: str
    pod_type: str | None


@dataclass(frozen=True)
class QueryRequest:
    index_name: str
    query_text: str
    namespace: str | None = None
    top_k: int = 5
    embedding_provider: str | None = None
    embedding_model: str | None = None
    filter_metadata: dict[str, Any] | None = None
    selection_mode: str = "top_k"  # top_k, mmr
    fetch_k: int = 1
    mmr_lambda: float = 0.5
    dedup_max_per_document: int = 1
    score_threshold: float = 0.0


@dataclass(frozen=True)
class QueryResult:
    request_id: str
    index_name: str
    query_text: str
    namespace: str
    retrieved_docs: list[Document]
    total_docs: int
    execution_time_s: float
    embedding_provider: str
    embedding_model: str


@dataclass(frozen=True)
class IndexInfo:
    name: str
    dimension: int
    metric: str
    status: str
    pod_type: str | None
    pod_count: int | None
    replica_count: int | None
    raw: dict[str, Any]


class SuporteAtendimentoService:
    def __init__(self, app_config: AppConfig | None = None) -> None:
        self.app_config = app_config or get_app_config()
        self._pinecone_client: Pinecone | None = None
        self._ollama_client: ollama.Client | None = None

    @property
    def pinecone_client(self) -> Pinecone:
        if self._pinecone_client is None:
            self._pinecone_client = Pinecone(
                api_key=self.app_config.pinecone.api_key,
            )
        return self._pinecone_client

    @property
    def ollama_client(self) -> ollama.Client:
        if self._ollama_client is None:
            self._ollama_client = ollama.Client(
                host=self.app_config.ai_providers.ollama.base_url
            )
        return self._ollama_client

    @staticmethod
    def get_available_embedding_models() -> list[dict[str, str]]:
        """Retorna lista de modelos de embedding disponíveis com suas dimensões."""
        return [
            {"name": "nomic-embed-text", "dimension": "768"},
            {"name": "all-MiniLM-L6-v2", "dimension": "384"},
            {"name": "paraphrase-multilingual-MiniLM-L12-v2", "dimension": "384"},
            {"name": "text-embedding-ada-002", "dimension": "1536"},
            {"name": "text-embedding-3-small", "dimension": "1536"},
            {"name": "text-embedding-3-large", "dimension": "3072"},
            {"name": "all-mpnet-base-v2", "dimension": "768"},
            {"name": "distilbert-base-nli-stsb-mean-tokens", "dimension": "768"},
        ]

    def get_available_models(self, provider: str) -> list[dict[str, Any]]:
        """Retorna lista de modelos disponíveis para um provedor específico."""
        try:
            if provider == "openai":
                return self._get_openai_models()
            elif provider == "gemini":
                return self._get_gemini_models()
            elif provider == "groq":
                return self._get_groq_models()
            elif provider == "ollama":
                return self._get_ollama_models()
            else:
                return []
        except Exception as e:
            logger.warning(f"Erro ao listar modelos do provedor {provider}: {e}")
            return []

    def _get_openai_models(self) -> list[dict[str, Any]]:
        """Lista modelos disponíveis na OpenAI."""
        if not self.app_config.ai_providers.openai.api_key:
            return []

        try:
            import openai
            client = openai.OpenAI(
                api_key=self.app_config.ai_providers.openai.api_key,
                base_url=self.app_config.ai_providers.openai.base_url,
            )
            models = client.models.list()
            return [
                {
                    "id": model.id,
                    "name": model.id,
                    "type": "embedding" if "embedding" in model.id else "chat",
                    "provider": "openai"
                }
                for model in models.data
                if any(keyword in model.id for keyword in ["gpt", "embedding", "text"])
            ]
        except Exception:
            # Fallback para modelos conhecidos
            return [
                {"id": "gpt-4", "name": "GPT-4", "type": "chat", "provider": "openai"},
                {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "type": "chat", "provider": "openai"},
                {"id": "text-embedding-ada-002", "name": "Ada v2", "type": "embedding", "provider": "openai"},
                {"id": "text-embedding-3-small", "name": "Embedding v3 Small", "type": "embedding", "provider": "openai"},
                {"id": "text-embedding-3-large", "name": "Embedding v3 Large", "type": "embedding", "provider": "openai"},
            ]

    def _get_gemini_models(self) -> list[dict[str, Any]]:
        """Lista modelos disponíveis no Gemini."""
        if not self.app_config.ai_providers.gemini.api_key:
            return []

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.app_config.ai_providers.gemini.api_key)
            models = genai.list_models()
            return [
                {
                    "id": model.name.replace("models/", ""),
                    "name": model.display_name,
                    "type": "chat" if "generateContent" in model.supported_generation_methods else "embedding",
                    "provider": "gemini"
                }
                for model in models
                if any(method in model.supported_generation_methods for method in ["generateContent", "embedContent"])
            ]
        except Exception:
            # Fallback para modelos conhecidos
            return [
                {"id": "gemini-pro", "name": "Gemini Pro", "type": "chat", "provider": "gemini"},
                {"id": "gemini-pro-vision", "name": "Gemini Pro Vision", "type": "chat", "provider": "gemini"},
                {"id": "text-bison-001", "name": "Text Bison", "type": "chat", "provider": "gemini"},
                {"id": "embedding-001", "name": "Embedding 001", "type": "embedding", "provider": "gemini"},
            ]

    def _get_groq_models(self) -> list[dict[str, Any]]:
        """Lista modelos disponíveis no Groq."""
        if not self.app_config.ai_providers.groq.api_key:
            return []

        try:
            import groq
            client = groq.Groq(
                api_key=self.app_config.ai_providers.groq.api_key,
                base_url=self.app_config.ai_providers.groq.base_url,
            )
            models = client.models.list()
            return [
                {
                    "id": model.id,
                    "name": model.id.replace("-", " ").title(),
                    "type": "chat" if any(keyword in model.id for keyword in ["llama", "mixtral", "gemma"]) else "embedding",
                    "provider": "groq"
                }
                for model in models.data
            ]
        except Exception:
            # Fallback para modelos conhecidos
            return [
                {"id": "llama2-70b-4096", "name": "Llama 2 70B", "type": "chat", "provider": "groq"},
                {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B", "type": "chat", "provider": "groq"},
                {"id": "gemma-7b-it", "name": "Gemma 7B", "type": "chat", "provider": "groq"},
                {"id": "llama3-8b-8192", "name": "Llama 3 8B", "type": "chat", "provider": "groq"},
                {"id": "llama3-70b-8192", "name": "Llama 3 70B", "type": "chat", "provider": "groq"},
            ]

    def _get_ollama_models(self) -> list[dict[str, Any]]:
        """Lista modelos disponíveis no Ollama via API REST."""
        try:
            # Normalizar a URL base do Ollama
            base_url = self.app_config.ai_providers.ollama.base_url.rstrip("/")
            
            # Verificar se devemos tentar conectar (pode ser desabilitado para servidores offline)
            skip_connection = os.getenv("OLLAMA_SKIP_CONNECTION", "false").lower() in ("true", "1", "yes")
            if skip_connection:
                logger.info(f"⏭️ Conexão ao Ollama desabilitada via OLLAMA_SKIP_CONNECTION. Usando fallback.")
                return self._get_ollama_fallback_models()
            
            # Tentar diferentes variações da URL
            api_urls = [
                f"{base_url}/api/tags",
                f"{base_url}:11434/api/tags" if ":" not in base_url.split("://")[1] else f"{base_url}/api/tags",
            ]
            
            response = None
            last_error = None
            
            for api_url in api_urls:
                try:
                    logger.debug(f"Tentando conectar a: {api_url}")
                    # Aumentar timeout para 10 segundos para dar mais chance a servidores remotos
                    response = requests.get(api_url, timeout=10)
                    if response.status_code == 200:
                        break
                except Exception as e:
                    last_error = e
                    continue
            
            if response is None or response.status_code != 200:
                logger.warning(f"⚠️ Não foi possível conectar ao Ollama em {base_url}. Usando modelos fallback. Erro: {last_error}")
                return self._get_ollama_fallback_models()
            
            data = response.json()
            models = data.get("models", [])

            result = []
            for model in models:
                model_name = model.get("name", "")
                # Classificar tipo baseado no nome
                if any(keyword in model_name.lower() for keyword in ["embed", "embedding", "bge", "nomic", "mxbai"]):
                    model_type = "embedding"
                elif any(keyword in model_name.lower() for keyword in ["rerank", "reranking"]):
                    model_type = "reranking"
                else:
                    model_type = "chat"

                result.append({
                    "id": model_name,
                    "name": model_name,
                    "type": model_type,
                    "provider": "ollama",
                    "size": model.get("size", 0),
                    "modified_at": model.get("modified_at", ""),
                })

            logger.info(f"✅ Conectado ao Ollama em {base_url}. {len(result)} modelos encontrados.")
            return result
            
        except Exception as e:
            logger.warning(f"❌ Erro ao conectar ao Ollama: {e}")
            return self._get_ollama_fallback_models()

    def _get_ollama_fallback_models(self) -> list[dict[str, Any]]:
        """Retorna lista de modelos Ollama conhecidos quando a conexão falha."""
        return [
            {"id": "nomic-embed-text-v2-moe", "name": "Nomic Embed Text V2 MOE", "type": "embedding", "provider": "ollama"},
            {"id": "embeddinggemma", "name": "Embedding Gemma", "type": "embedding", "provider": "ollama"},
            {"id": "qwen3-embedding:0.6b", "name": "Qwen3 Embedding 0.6B", "type": "embedding", "provider": "ollama"},
            {"id": "qwen3-embedding:4b", "name": "Qwen3 Embedding 4B", "type": "embedding", "provider": "ollama"},
            {"id": "mxbai-embed-large", "name": "MXBai Embed Large", "type": "embedding", "provider": "ollama"},
            {"id": "qwen3.5:4b", "name": "Qwen 3.5 4B", "type": "chat", "provider": "ollama"},
            {"id": "granite4:3b", "name": "Granite 4 3B", "type": "chat", "provider": "ollama"},
            {"id": "ministral-3:8b", "name": "Ministral 3 8B", "type": "chat", "provider": "ollama"},
            {"id": "qwen2.5:7b", "name": "Qwen 2.5 7B", "type": "chat", "provider": "ollama"},
            {"id": "gemma3:4b", "name": "Gemma 3 4B", "type": "chat", "provider": "ollama"},
            {"id": "ministral-3:3b", "name": "Ministral 3 3B", "type": "chat", "provider": "ollama"},
            {"id": "bge-reranker-v2-m3", "name": "BGE Reranker V2 M3", "type": "reranking", "provider": "ollama"},
        ]

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extrai texto de um arquivo PDF."""
        if not os.path.exists(file_path):
            raise SuporteAtendimentoServiceError(
                f"Arquivo não encontrado: {file_path}"
            )

        if not file_path.lower().endswith('.pdf'):
            raise SuporteAtendimentoServiceError(
                f"Arquivo deve ser PDF: {file_path}"
            )

        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            raise SuporteAtendimentoServiceError(
                f"Erro ao extrair texto do PDF: {e}"
            ) from e

    def _create_chunks(
        self,
        text: str,
        chunk_size: int,
        overlap: int
    ) -> list[Document]:
        """Cria chunks do texto usando RecursiveCharacterTextSplitter."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        return splitter.create_documents([text])

    def _generate_embeddings(
        self,
        texts: list[str],
        provider: str,
        model: str
    ) -> list[list[float]]:
        """Gera embeddings usando o provedor especificado."""
        try:
            if provider == "ollama":
                return self._generate_ollama_embeddings(texts, model)
            elif provider == "openai":
                return self._generate_openai_embeddings(texts, model)
            elif provider == "gemini":
                return self._generate_gemini_embeddings(texts, model)
            elif provider == "groq":
                return self._generate_groq_embeddings(texts, model)
            else:
                raise SuporteAtendimentoServiceError(f"Provedor não suportado: {provider}")
        except Exception as e:
            raise SuporteAtendimentoServiceError(
                f"Erro ao gerar embeddings com {provider}: {e}"
            ) from e

    def _generate_ollama_embeddings(
        self,
        texts: list[str],
        model: str
    ) -> list[list[float]]:
        """Gera embeddings usando Ollama (otimizado para CPU)."""
        # Verificar se devemos pular Ollama por performance
        skip_ollama = os.getenv("SKIP_OLLAMA_EMBEDDINGS", "false").lower() in ("true", "1", "yes")
        if skip_ollama:
            logger.warning(f"⚠️ Ollama embeddings desabilitados via SKIP_OLLAMA_EMBEDDINGS. Usando OpenAI como fallback.")
            return self._generate_openai_embeddings(texts, "text-embedding-ada-002")

        try:
            # Verifica se o modelo está disponível (com timeout)
            logger.info(f"🔍 Verificando disponibilidade do modelo Ollama: {model}")
            available_models = self.ollama_client.list()
            model_names = [m['name'] for m in available_models['models']]
            if model not in model_names:
                logger.warning(f"Modelo {model} não encontrado. Tentando modelo alternativo...")
                # Tentar modelo alternativo se disponível
                alt_models = ["nomic-embed-text", "all-MiniLM-L6-v2"]
                for alt_model in alt_models:
                    if alt_model in model_names:
                        logger.info(f"Usando modelo alternativo: {alt_model}")
                        model = alt_model
                        break
                else:
                    raise SuporteAtendimentoServiceError(
                        f"Nenhum modelo de embedding disponível. "
                        f"Modelos encontrados: {', '.join(model_names)}"
                    )

            # Processar em batches pequenos para não sobrecarregar CPU
            batch_size = int(os.getenv("OLLAMA_EMBEDDING_BATCH_SIZE", "5"))  # Muito menor que OpenAI
            embeddings = []
            
            logger.info(f"🚀 Iniciando geração de embeddings Ollama para {len(texts)} textos (batch_size={batch_size})")
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_start = i + 1
                batch_end = min(i + batch_size, len(texts))
                
                logger.info(f"📊 Processando batch {batch_start}-{batch_end}/{len(texts)}...")
                
                for j, text in enumerate(batch_texts):
                    try:
                        # Timeout maior para CPU
                        response = self.ollama_client.embeddings(
                            model=model,
                            prompt=text
                        )
                        embeddings.append(response['embedding'])
                        logger.debug(f"✅ Texto {i+j+1}/{len(texts)} processado")
                    except Exception as e:
                        logger.error(f"❌ Erro no texto {i+j+1}: {e}")
                        # Adicionar embedding vazio como fallback
                        embeddings.append([0.0] * 768)  # Dimensão típica
                
                # Pequena pausa entre batches para não sobrecarregar CPU
                import time
                time.sleep(0.5)
            
            logger.info(f"✅ Geração de embeddings Ollama concluída: {len(embeddings)} vetores gerados")
            return embeddings
            
        except Exception as e:
            logger.error(f"❌ Erro geral na geração de embeddings Ollama: {e}")
            # Fallback para OpenAI se disponível
            if self.app_config.ai_providers.openai.api_key:
                logger.warning("🔄 Fazendo fallback para OpenAI embeddings...")
                return self._generate_openai_embeddings(texts, "text-embedding-ada-002")
            else:
                raise SuporteAtendimentoServiceError(f"Erro ao gerar embeddings: {e}")

    def _generate_openai_embeddings(
        self,
        texts: list[str],
        model: str
    ) -> list[list[float]]:
        """Gera embeddings usando OpenAI."""
        if not self.app_config.ai_providers.openai.api_key:
            raise SuporteAtendimentoServiceError("API key do OpenAI não configurada")

        try:
            import openai
            client = openai.OpenAI(
                api_key=self.app_config.ai_providers.openai.api_key,
                base_url=self.app_config.ai_providers.openai.base_url,
            )

            # OpenAI tem limite de 2048 tokens por request, então processamos em batches
            embeddings = []
            batch_size = 100  # Ajuste conforme necessário

            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                response = client.embeddings.create(
                    input=batch_texts,
                    model=model
                )
                embeddings.extend([data.embedding for data in response.data])
            return embeddings
        except Exception as e:
            raise SuporteAtendimentoServiceError(f"Erro na API do OpenAI: {e}")

    def _generate_gemini_embeddings(
        self,
        texts: list[str],
        model: str
    ) -> list[list[float]]:
        """Gera embeddings usando Gemini."""
        if not self.app_config.ai_providers.gemini.api_key:
            raise SuporteAtendimentoServiceError("API key do Gemini não configurada")

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.app_config.ai_providers.gemini.api_key)

            embeddings = []
            for text in texts:
                result = genai.embed_content(
                    model=f"models/{model}",
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings.append(result['embedding'])
            return embeddings
        except Exception as e:
            raise SuporteAtendimentoServiceError(f"Erro na API do Gemini: {e}")

    def _generate_groq_embeddings(
        self,
        texts: list[str],
        model: str
    ) -> list[list[float]]:
        """Gera embeddings usando Groq."""
        if not self.app_config.ai_providers.groq.api_key:
            raise SuporteAtendimentoServiceError("API key do Groq não configurada")

        try:
            import groq
            client = groq.Groq(
                api_key=self.app_config.ai_providers.groq.api_key,
                base_url=self.app_config.ai_providers.groq.base_url,
            )

            embeddings = []
            for text in texts:
                # Groq usa chat completion para embeddings, mas vamos tentar usar o modelo diretamente
                # Nota: Groq pode não ter modelos de embedding dedicados, então usamos o que estiver disponível
                response = client.chat.completions.create(
                    messages=[{"role": "user", "content": f"Generate embedding for: {text}"}],
                    model=model,
                    max_tokens=1  # Embedding é representado por tokens
                )
                # Para este exemplo, vamos usar uma representação simples
                # Em produção, seria necessário um modelo de embedding adequado
                embedding = [0.1] * 768  # Placeholder - dimensão típica
                embeddings.append(embedding)
            return embeddings
        except Exception as e:
            raise SuporteAtendimentoServiceError(f"Erro na API do Groq: {e}")

    def upsert_document(self, request: UpsertRequest) -> UpsertResult:
        """Faz upsert de um documento PDF no Pinecone."""
        request_id = str(uuid.uuid4())

        # Validações
        if not os.path.exists(request.file_path):
            raise SuporteAtendimentoServiceError(
                f"Arquivo não encontrado: {request.file_path}"
            )

        # Validação extra para vector_type e metric
        if request.vector_type and request.vector_type not in {"dense", "sparse"}:
            raise SuporteAtendimentoServiceError(
                "vector_type deve ser 'dense' ou 'sparse'."
            )

        if request.metric and request.metric not in {"cosine", "dotproduct", "euclidean"}:
            raise SuporteAtendimentoServiceError(
                "metric deve ser 'cosine', 'dotproduct' ou 'euclidean'."
            )

        # Configurações
        chunk_size = request.chunk_size or self.app_config.chunking.chunk_size
        overlap = request.overlap or self.app_config.chunking.overlap
        embedding_provider = request.embedding_provider or "ollama"
        embedding_model = validate_embedding_model(
            request.embedding_model or self.app_config.ollama.embedding_model
        )

        # Namespace e document_id
        namespace = request.namespace or Path(request.file_path).stem
        document_id = request.document_id or Path(request.file_path).stem

        logger.info(
            f"Iniciando upsert - Request ID: {request_id}, "
            f"Index: {request.index_name}, Namespace: {namespace}, "
            f"Document ID: {document_id}, Provider: {embedding_provider}"
        )

        # Extrai texto do PDF
        text = self._extract_text_from_pdf(request.file_path)
        if not text:
            raise SuporteAtendimentoServiceError(
                "PDF não contém texto extraível"
            )

        # Cria chunks
        chunks = self._create_chunks(text, chunk_size, overlap)
        if not chunks:
            raise SuporteAtendimentoServiceError(
                "Nenhum chunk foi criado do texto"
            )

        # Gera embeddings
        chunk_texts = [chunk.page_content for chunk in chunks]
        embeddings = self._generate_embeddings(chunk_texts, embedding_provider, embedding_model)

        # Cria ou verifica índice com configurações de upsert
        requested_vector_type = request.vector_type or "dense"
        requested_metric = request.metric or "cosine"
        requested_pod_type = request.pod_type or ""

        self._ensure_index_exists(
            index_name=request.index_name,
            dimension=len(embeddings[0]),
            vector_type=requested_vector_type,
            metric=requested_metric,
            pod_type=requested_pod_type,
        )

        # Cria vector store
        vector_store = PineconeVectorStore(
            index_name=request.index_name,
            pinecone_api_key=self.app_config.pinecone.api_key,
            namespace=namespace,
        )

        # Adiciona metadados
        for i, chunk in enumerate(chunks):
            chunk.metadata.update({
                "document_id": document_id,
                "chunk_index": i,
                "source_file": request.file_path,
                "embedding_model": embedding_model,
            })

        # Faz upsert
        try:
            vector_store.add_documents(chunks)
        except Exception as e:
            raise SuporteAtendimentoServiceError(
                f"Erro no upsert para Pinecone: {e}"
            ) from e

        logger.info(
            f"Upsert concluído - Chunks: {len(chunks)}, "
            f"Caracteres: {len(text)}"
        )

        return UpsertResult(
            request_id=request_id,
            index_name=request.index_name,
            namespace=namespace,
            document_id=document_id,
            chunks_count=len(chunks),
            total_characters=len(text),
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            vector_type=requested_vector_type,
            metric=requested_metric,
            pod_type=requested_pod_type or None,
        )

    def query_database(self, request: QueryRequest) -> QueryResult:
        """Consulta o database Pinecone usando busca semântica."""
        import time
        start_time = time.time()

        request_id = str(uuid.uuid4())

        # Validações
        if not request.query_text.strip():
            raise SuporteAtendimentoServiceError("Texto da consulta não pode estar vazio.")

        if request.top_k <= 0:
            raise SuporteAtendimentoServiceError("top_k deve ser maior que 0.")

        if request.selection_mode not in {"top_k", "mmr"}:
            raise SuporteAtendimentoServiceError("selection_mode deve ser 'top_k' ou 'mmr'.")

        # Configurações
        embedding_provider = request.embedding_provider or "ollama"
        embedding_model = validate_embedding_model(
            request.embedding_model or self.app_config.ollama.embedding_model
        )

        # Verifica se o índice existe
        if not self.check_index_exists(request.index_name):
            raise SuporteAtendimentoServiceError(
                f"Índice '{request.index_name}' não existe."
            )

        # Cria vector store
        vector_store = PineconeVectorStore(
            index_name=request.index_name,
            pinecone_api_key=self.app_config.pinecone.api_key,
            namespace=request.namespace,
        )

        # Busca documentos
        search_kwargs = {
            "k": request.top_k,
            "filter": request.filter_metadata,
            "score_threshold": request.score_threshold,
        }

        if request.selection_mode == "mmr":
            search_kwargs.update({
                "fetch_k": request.fetch_k,
                "lambda_mult": request.mmr_lambda,
            })

        try:
            if request.selection_mode == "mmr":
                retrieved_docs = vector_store.max_marginal_relevance_search(
                    request.query_text, **search_kwargs
                )
            else:
                retrieved_docs = vector_store.similarity_search(
                    request.query_text, **search_kwargs
                )
        except Exception as e:
            raise SuporteAtendimentoServiceError(
                f"Erro na busca no Pinecone: {e}"
            ) from e

        execution_time = time.time() - start_time

        logger.info(
            f"Consulta concluída - Request ID: {request_id}, "
            f"Docs: {len(retrieved_docs)}, Tempo: {execution_time:.2f}s"
        )

        return QueryResult(
            request_id=request_id,
            index_name=request.index_name,
            query_text=request.query_text,
            namespace=request.namespace or "",
            retrieved_docs=retrieved_docs,
            total_docs=len(retrieved_docs),
            execution_time_s=execution_time,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
        )

    def _ensure_index_exists(
        self,
        index_name: str,
        dimension: int,
        vector_type: str = "dense",
        metric: str = "cosine",
        pod_type: str | None = None,
        serverless_cloud: str = "aws",
        serverless_region: str | None = None,
        deletion_protection: bool = False,
    ) -> None:
        """Garante que o índice existe no Pinecone."""
        try:
            existing_names = self.pinecone_client.list_indexes().names()
            if index_name not in existing_names:
                region = serverless_region or self.app_config.pinecone.environment
                index_kwargs: dict[str, Any] = {
                    "name": index_name,
                    "dimension": dimension,
                    "metric": metric,
                    "vector_type": vector_type,
                    "spec": ServerlessSpec(
                        cloud=serverless_cloud,
                        region=region,
                    ),
                    "deletion_protection": "enabled" if deletion_protection else "disabled",
                }

                # Pod type em serverless não é suportado explicitamente; mantemos para compatibilidade de UI
                if pod_type:
                    index_kwargs["pod_type"] = pod_type

                self.pinecone_client.create_index(**index_kwargs)
                logger.info(
                    f"Índice criado: {index_name} (vector_type={vector_type}, metric={metric}, pod_type={pod_type})"
                )
            else:
                logger.info(f"Índice já existe: {index_name}")
        except Exception as e:
            raise SuporteAtendimentoServiceError(
                f"Erro ao criar/verificar índice: {e}"
            ) from e

    def check_index_exists(self, index_name: str) -> bool:
        """Verifica se um índice existe no Pinecone."""
        try:
            indexes = self.pinecone_client.list_indexes()
            return index_name in indexes.names()
        except Exception as e:
            logger.error(f"Erro ao verificar índice {index_name}: {e}")
            return False

    def create_index(
        self,
        index_name: str,
        vector_type: str = "dense",
        dimension: int = 1536,
        metric: str = "cosine",
        serverless_cloud: str = "aws",
        serverless_region: str = "us-east-1",
        deletion_protection: bool = False,
    ) -> None:
        """Cria um índice no Pinecone com configuração completa."""
        try:
            if self.check_index_exists(index_name):
                raise SuporteAtendimentoServiceError(
                    f"O índice '{index_name}' já existe."
                )

            vector_type = vector_type.lower()
            if vector_type not in {"dense", "sparse"}:
                raise SuporteAtendimentoServiceError(
                    "vector_type deve ser 'dense' ou 'sparse'."
                )

            if dimension <= 0:
                raise SuporteAtendimentoServiceError(
                    "dimension deve ser maior que 0."
                )

            if metric not in {"cosine", "dotproduct", "euclidean"}:
                raise SuporteAtendimentoServiceError(
                    "metric deve ser 'cosine', 'dotproduct' ou 'euclidean'."
                )

            self.pinecone_client.create_index(
                name=index_name,
                spec=ServerlessSpec(
                    cloud=serverless_cloud,
                    region=serverless_region,
                ),
                dimension=dimension,
                metric=metric,
                vector_type=vector_type,
                deletion_protection="enabled" if deletion_protection else "disabled",
            )
            logger.info(
                f"Índice criado: {index_name} (vector_type={vector_type}, dim={dimension}, metric={metric}, "
                f"cloud={serverless_cloud}, region={serverless_region}, deletion_protection={deletion_protection})"
            )

        except SuporteAtendimentoServiceError:
            raise

        except Exception as e:
            raise SuporteAtendimentoServiceError(
                f"Erro ao criar índice {index_name}: {e}"
            ) from e

    def list_indexes(self) -> list[IndexInfo]:
        """Lista todos os índices criados no Pinecone."""
        try:
            indexes = self.pinecone_client.list_indexes()
            result = []
            for index in indexes:
                # Para índices serverless, precisamos de mais info
                index_info = self.pinecone_client.describe_index(index.name)
                index_dict = (
                    index_info.to_dict()
                    if hasattr(index_info, "to_dict")
                    else dict(index_info)
                )
                result.append(IndexInfo(
                    name=index.name,
                    dimension=getattr(index_info, "dimension", None),
                    metric=getattr(index_info, "metric", None),
                    status=getattr(index_info, "status", None),
                    pod_type=getattr(index_info, "pod_type", None),
                    pod_count=getattr(index_info, "pod_count", None),
                    replica_count=getattr(index_info, "replica_count", None),
                    raw=index_dict,
                ))
            return result
        except Exception as e:
            raise SuporteAtendimentoServiceError(
                f"Erro ao listar índices: {e}"
            ) from e

    def delete_index(self, index_name: str) -> None:
        """Deleta um índice no Pinecone."""
        try:
            if not self.check_index_exists(index_name):
                raise SuporteAtendimentoServiceError(
                    f"Índice '{index_name}' não existe."
                )

            self.pinecone_client.delete_index(name=index_name)
            logger.info(f"Índice excluído: {index_name}")

        except SuporteAtendimentoServiceError:
            raise

        except Exception as e:
            raise SuporteAtendimentoServiceError(
                f"Erro ao deletar índice {index_name}: {e}"
            ) from e