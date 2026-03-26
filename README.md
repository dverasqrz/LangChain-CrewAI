# LangChain + CrewAI - Portfólio de Projetos com IA

Este repositório reúne uma coleção de aplicações práticas utilizando **LangChain**, **CrewAI** e **Streamlit**, com foco em resolver problemas reais em diferentes áreas de negócio por meio de agentes inteligentes, automação e integração de dados.

A proposta é demonstrar, de forma aplicada, como construir soluções com IA que vão além de protótipos, explorando conceitos como:
- Multiagentes
- RAG (Retrieval-Augmented Generation)
- Integração com bases de dados
- Processamento de documentos
- Automação de fluxos

---

## 🧠 Estrutura do Projeto

A aplicação principal é construída com **Streamlit**, funcionando como um hub central onde o usuário pode acessar diferentes projetos.

Cada domínio representa um caso de uso real de IA aplicada:

- app.py # Página principal (hub de projetos)
- pages/ # Interfaces de cada projeto (Streamlit)
- educacao/ # Lógica e serviços do domínio Educação
- financas/ # Lógica e serviços do domínio Finanças
- marketing/ # Lógica e serviços do domínio Marketing
- medicina/ # Lógica e serviços do domínio Medicina
- rh/ # Lógica e serviços do domínio RH
- suporte-atendimento/ # Lógica e serviços de suporte com RAG
- turismo/ # Lógica e serviços de turismo (multiagentes)
- varejo-ecommerce/ # Lógica e serviços de varejo


---

## 🚀 Projetos

### 📢 Marketing
Assistente de marketing com IA para escalar a criação de conteúdo.

- Adaptação de textos para diferentes públicos
- Ajuste para múltiplos canais (Instagram, e-mail, blog, etc.)
- Geração orientada a objetivos (vendas, engajamento, branding)

---

### 🎧 Atendimento e Suporte
Chatbots inteligentes com uso de **RAG (Retrieval-Augmented Generation)**.

- Consulta a documentos reais (PDFs, manuais, bases internas)
- Respostas contextualizadas e precisas
- Redução de dependência de atendimento humano

---

### 🧑‍💼 Recursos Humanos
Análise automatizada de currículos e classificação de candidatos.

- Extração de dados estruturados (skills, experiência, formação)
- Ranking de candidatos
- Geração de insights para tomada de decisão

---

### 📘 Educação
Geração de conteúdo educacional personalizado.

- Criação de exercícios com base no nível do aluno
- Explicações detalhadas com suporte contínuo (tutor 24/7)
- Exportação automática para formatos editáveis

---

### 💰 Finanças
Interpretação e análise automatizada de relatórios financeiros.

- Geração de resumos executivos
- Consulta em linguagem natural
- Transparência na explicação dos resultados

---

### ✈️ Turismo
Sistema multiagentes para criação de roteiros personalizados.

- Definição de papéis para diferentes agentes (planejamento, orçamento, logística)
- Geração de itinerários completos
- Personalização baseada em preferências do usuário

---

### 🛒 Varejo / E-commerce
Análise inteligente de dados e avaliações de produtos.

- Resumo de reviews de clientes
- Integração com banco SQL
- Consulta via linguagem natural

---

### 🩺 Medicina
Automação na análise de dados médicos.

- Processamento de imagens médicas
- Geração de relatórios detalhados
- Busca de referências para embasar resultados

> ⚠️ Observação: este projeto é experimental e não substitui avaliação médica profissional.

---

## 🛠️ Tecnologias Utilizadas

- Python 3.x
- Streamlit
- LangChain
- CrewAI
- SQL (para consultas estruturadas)
- RAG (com bases documentais)
- APIs de modelos de linguagem (LLMs)

---
