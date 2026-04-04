# 📦 Estrutura de Dependências do Projeto

## Visão Geral

O projeto está organizado em **3 módulos independentes e desacoplados**, cada um com suas próprias dependências otimizadas:

```
Curso-LangChain-CrewAI-Udemy
├── requirements.txt (RAIZ - todas as dependências)
├── marketing/
│   ├── requirements.txt (específicas do Marketing)
│   ├── config.py
│   ├── service.py
│   └── __init__.py
├── suporte_atendimento/
│   ├── requirements.txt (específicas de Suporte)
│   ├── config.py
│   ├── service.py
│   └── __init__.py
├── rh/
│   ├── requirements.txt (específicas de RH)
│   ├── config.py
│   ├── service.py
│   └── __init__.py
└── pages/
    ├── 3_marketing.py (usa marketing.service)
    ├── 5_rh.py (usa rh.service)
    └── 6_suporte_atendimento.py (usa suporte_atendimento.service)
```

---

## 📋 Detalhes de Cada Módulo

### 1️⃣ **Marketing** (`marketing/requirements.txt`)

**Propósito:** Geração de conteúdo de marketing com LLM

**Dependências principais:**
- Streamlit + dotenv (UI + configuração)
- LangChain Core + OpenAI + Groq (processamento de prompts)
- Tiktoken + Tenacity (tokenização + retry)
- LangSmith (logging)

**Instalar apenas este módulo:**
```bash
pip install -r marketing/requirements.txt
```

---

### 2️⃣ **Suporte e Atendimento** (`suporte_atendimento/requirements.txt`)

**Propósito:** RAG (Retrieval Augmented Generation) com Pinecone para atendimento

**Dependências principais:**
- Streamlit + dotenv (UI + configuração)
- LangChain Core + Pinecone (busca semântica)
- Ollama (embeddings locais)
- PyPDF + python-docx (processamento de docs)
- OpenAI + Groq (LLMs)

**Instalar apenas este módulo:**
```bash
pip install -r suporte_atendimento/requirements.txt
```

---

### 3️⃣ **RH** (`rh/requirements.txt`)

**Propósito:** Análise de currículos para alinhamento com vagas

**Dependências principais:**
- Streamlit + dotenv (UI + configuração)
- PyPDF + python-docx (extração de texto de currículo)
- LangChain Core + OpenAI + Groq (análise com LLM)
- Tenacity + LangSmith (retry + logging)

**Instalar apenas este módulo:**
```bash
pip install -r rh/requirements.txt
```

---

## 🔄 Dependências Compartilhadas

Todos os módulos usam:
- ✅ `streamlit` (interface web)
- ✅ `python-dotenv` (variáveis de ambiente)
- ✅ `langchain-core` (núcleo de orquestração)
- ✅ `tenacity` (retry automático)
- ✅ `langsmith` (logging/debug)

---

## 📦 Instalar Tudo

Para instalar **todas as dependências** do workspace (raiz + todos os módulos):

```bash
pip install -r requirements.txt
```

Este arquivo `requirements.txt` da raiz contém:
- Todas as dependências individuais dos 3 módulos
- Dependências extras (pandas, plotly, etc. para análise)
- Versões compatíveis e testadas

---

## 🧪 Verificar Conformidade

Para garantir que cada módulo está funcional:

```bash
# Marketing
python -c "from marketing.config import get_app_config; from marketing.service import generate_marketing_content_with_metadata; print('✅ Marketing OK')"

# Suporte e Atendimento
python -c "from suporte_atendimento.config import get_app_config; from suporte_atendimento.service import SuporteAtendimentoService; print('✅ Suporte OK')"

# RH
python -c "from rh.config import get_app_config; from rh.service import RHService; print('✅ RH OK')"
```

---

## 🚀 Executar Projetos Específicos

```bash
# Apenas Marketing
streamlit run pages/3_marketing.py

# Apenas Suporte
streamlit run pages/6_suporte_atendimento.py

# Apenas RH
streamlit run pages/5_rh.py

# Todos (via app.py)
streamlit run app.py
```

---

## ⚠️ Importante: Configuração de Ambiente

Cada módulo requer variáveis de ambiente específicas. Crie um arquivo `.env`:

```env
# Comum
RH_GROQ_API_KEY=seu_groq_key
RH_OPENAI_API_KEY=sua_openai_key
OLLAMA_BASE_URL=http://localhost:11434

# Suporte (se usar Pinecone)
PINECONE_API_KEY=sua_pinecone_key
PINECONE_ENVIRONMENT=sua_region
OLLAMA_BASE_URL=http://localhost:11434

# Marketing (se usar Groq/OpenAI)
RH_GROQ_API_KEY=seu_groq_key
RH_OPENAI_API_KEY=sua_openai_key
```

---

## 📝 Resumo de Design

| Aspecto | Implementação |
|--------|-------------|
| **Desacoplamento** | Cada módulo é independente com service + config próprios |
| **Reutilização** | Base comum em requirements.txt, customizações em subpastas |
| **Manutenção** | Atualizações isoladas por módulo, sem impacto cruzado |
| **Teste** | Cada projeto pode ser testado/rodado independentemente |
| **Escalability** | Fácil adicionar novos módulos seguindo o padrão |

---

✅ **Status:** Todos os módulos configurados, otimizados e prontos para uso.
