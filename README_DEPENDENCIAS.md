# Estrutura de Dependências por Projeto

## 📁 Visão Geral

Esta aplicação foi reorganizada para ter dependências separadas por projeto, facilitando a migração e o deploy independente de cada módulo.

## 🏗️ Estrutura de Arquivos

```
Curso-LangChain-CrewAI-Udemy/
├── requirements.txt                 # Dependências globais (Streamlit, etc.)
├── marketing/
│   ├── requirements.txt            # Dependências do projeto de Marketing
│   ├── config.py
│   └── service.py
├── suporte_atendimento/
│   ├── requirements.txt            # Dependências do projeto de Suporte (RAG)
│   ├── config.py
│   └── service.py
└── pages/
    ├── 3_marketing.py
    └── 6_suporte_atendimento.py
```

## 🚀 Como Usar

### 1. Instalação Completa (Todos os Projetos)

```bash
# Instalar dependências globais
pip install -r requirements.txt

# Instalar dependências do Marketing
pip install -r marketing/requirements.txt

# Instalar dependências do Suporte
pip install -r suporte_atendimento/requirements.txt

# Rodar aplicação completa
streamlit run app.py
```

### 2. Instalação por Projeto Individual

#### Marketing apenas:
```bash
# Instalar dependências globais + marketing
pip install -r requirements.txt
pip install -r marketing/requirements.txt

# Rodar apenas a página de marketing
streamlit run pages/3_marketing.py
```

#### Suporte e Atendimento apenas:
```bash
# Instalar dependências globais + suporte
pip install -r requirements.txt
pip install -r suporte_atendimento/requirements.txt

# Rodar apenas a página de suporte
streamlit run pages/6_suporte_atendimento.py
```

### 3. Migração de Projeto

Para migrar apenas o projeto de Marketing para outro ambiente:

```bash
# Copiar apenas a pasta marketing/
cp -r marketing/ /novo/projeto/

# No novo ambiente, instalar dependências
pip install -r marketing/requirements.txt

# Rodar o projeto
streamlit run pages/3_marketing.py
```

## 📦 Dependências por Projeto

### 🔧 Globais (`requirements.txt`)
- **Streamlit**: Interface web
- **Python-dotenv**: Variáveis de ambiente
- **Altair**: Visualizações
- **Pandas**: Manipulação de dados
- **Pydantic**: Validação de dados

### 📢 Marketing (`marketing/requirements.txt`)
- **LangChain**: Orquestração de LLMs
- **Groq**: LLM provider (Llama)
- **OpenAI**: LLM provider (GPT)
- **Tiktoken**: Tokenização
- **LangSmith**: Monitoramento

### 🎧 Suporte e Atendimento (`suporte_atendimento/requirements.txt`)
- **LangChain**: Orquestração de RAG
- **FAISS**: Vector store para busca semântica
- **Sentence-transformers**: Embeddings
- **PyPDF**: Leitura de PDFs
- **Docx2txt**: Leitura de Word documents

## 🔄 Benefícios

1. **🚀 Deploy Independente**: Cada projeto pode ser implantado separadamente
2. **📦 Ambientes Leves**: Instale apenas o que precisa usar
3. **🔧 Manutenção Facilitada**: Dependências isoladas por funcionalidade
4. **🚀 Migração Simples**: Copie apenas a pasta do projeto desejado
5. **📊 Escalabilidade**: Fácil adicionar novos projetos com suas próprias dependências

## 🎯 Exemplo de Novo Projeto

Para criar um novo projeto (ex: "finanças"):

1. Criar pasta: `financas/`
2. Adicionar `financas/requirements.txt` com dependências específicas
3. Criar página: `pages/2_financas.py`
4. Atualizar `app.py` para incluir o novo projeto

## 📝 Notas

- As dependências globais são necessárias para qualquer projeto
- Cada requirements.txt específico inclui apenas o que aquele projeto precisa
- A estrutura permite fácil versionamento e CI/CD por projeto
- Para produção, considere usar ambientes virtuais separados por projeto
