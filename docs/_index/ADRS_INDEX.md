# ADRS_INDEX

> ⚠️ ARQUIVO AUTO-GERADO - NAO EDITAR MANUALMENTE
> Gerado por: python scripts/generate_index.py
> Fonte primaria: ver docs/prd/*.md e docs/architecture/*.md
> Ultima geracao: 2026-06-02 10:03 UTC

Total de documentos: 5

## Sumario

1. `ADR-001: Usar modelo Poisson Clássico` - `Accepted` - `docs/architecture/adr_001_poisson_choice.md`
2. `ADR-002: Usar Pinnacle como Sharp Benchmark` - `Accepted` - `docs/architecture/adr_002_pinnacle_benchmark.md`
3. `ADR-003: Estratégia Híbrida (Lógica + IA)` - `Accepted` - `docs/architecture/adr_003_hybrid_logic_ai.md`
4. `ADR-004: SQLite como Banco de Dados Principal` - `Accepted` - `docs/architecture/adr_004_database_choice.md`
5. `ADR-005: Gemini 2.0 Flash como LLM Principal` - `Accepted` - `docs/architecture/adr_005_llm_choice.md`

---

## ADR-001: Usar modelo Poisson Clássico

- Fonte: `docs/architecture/adr_001_poisson_choice.md`
- Status: `Accepted`
- Metadados:
  - Status: Accepted
  - Date: 2025-05-15
  - Deciders: Rafael
  - Consulted: Claude, Gemini
  - Informed: -

### Resumo

A escolha do modelo estatístico para prever resultados de futebol é crucial para a eficácia do sistema de value betting. Precisamos de um modelo que seja preciso o suficiente para identificar "valor", mas que também seja prático e interpretável, especialmente nas fases iniciais de operação com dados limitados.

---

## ADR-002: Usar Pinnacle como Sharp Benchmark

- Fonte: `docs/architecture/adr_002_pinnacle_benchmark.md`
- Status: `Accepted`
- Metadados:
  - Status: Accepted
  - Date: 2025-05-15
  - Deciders: Rafael
  - Consulted: Claude, Gemini
  - Informed: -

### Resumo

Para validar a eficácia da detecção de "value" em apostas, precisamos de um benchmark confiável e eficiente. As odds oferecidas por diferentes casas de apostas variam significativamente devido às suas margens de lucro (overround) e à forma como ajustam suas linhas. Escolher o benchmark correto é fundamental para garantir que o sistema esteja comparando suas previsões com uma representação justa do "mercado eficiente".
A decisão de usar a Pinnacle como benchmark introduz uma dependência crítica do scraper. Para garantir a testabilidade e a confiabilidade do sistema, as seguintes estratégias serão adotadas:
Para garantir a alta disponibilidade e a resiliência do sistema frente à dependência do scraper da Pinnacle, serão adotadas as seguintes medidas:

---

## ADR-003: Estratégia Híbrida (Lógica + IA)

- Fonte: `docs/architecture/adr_003_hybrid_logic_ai.md`
- Status: `Accepted`
- Metadados:
  - Status: Accepted
  - Date: 2025-05-15
  - Deciders: Rafael
  - Consulted: Claude, Gemini
  - Informed: -

### Resumo

O sistema de value betting precisa ser capaz de identificar oportunidades de forma rápida e consistente, mas também com inteligência suficiente para se adaptar a cenários complexos ou anômalos. A escolha entre uma abordagem puramente lógica (baseada em regras), puramente de Inteligência Artificial (IA) ou uma combinação híbrida é fundamental para equilibrar custo, performance, determinismo e adaptabilidade do sistema. O `AutoEvolution` (PRD-05) atua como o motor de decisão operacional, necessitando dessa estratégia para orientar suas ações.
A estratégia híbrida, embora otimizada, introduz complexidade na garantia de qualidade. As seguintes abordagens serão adotadas para mitigar os riscos e garantir a robustez:

---

## ADR-004: SQLite como Banco de Dados Principal

- Fonte: `docs/architecture/adr_004_database_choice.md`
- Status: `Accepted`
- Metadados:
  - Status: Accepted
  - Date: 2025-05-15
  - Deciders: Rafael
  - Consulted: Claude, Gemini
  - Informed: -

### Resumo

A escolha do sistema de gerenciamento de banco de dados (SGBD) é fundamental para o desempenho, escalabilidade e facilidade de manutenção do sistema. Dado que o EdgeHunter atualmente opera em um ambiente de máquina única (`single-machine deploy`) e tem um volume de dados estimado que não exige alta concorrência inicialmente, precisamos decidir qual tecnologia de banco de dados melhor atende a essas restrições e objetivos.
A escolha do SQLite, embora prática para o estágio inicial, exige atenção a certas implicações para testabilidade e confiabilidade:
Esta seção fornece exemplos práticos de como interagir com o banco de dados SQLite, ilustrando operações CRUD (Create, Read, Update, Delete) e gerenciamento. Os exemplos são representativos das interações via camada de persistência (ORM/SQL direto).

---

## ADR-005: Gemini 2.0 Flash como LLM Principal

- Fonte: `docs/architecture/adr_005_llm_choice.md`
- Status: `Accepted`
- Metadados:
  - Status: Accepted
  - Date: 2025-05-15
  - Deciders: Rafael
  - Consulted: Claude, Gemini
  - Informed: -

### Resumo

A integração de modelos de linguagem grandes (LLMs) é um componente chave para funcionalidades como validação de oportunidades, detecção de anomalias e sugestões de evolução no sistema. A escolha do LLM impacta diretamente o custo, a latência, a qualidade das respostas e a sustentabilidade do projeto, especialmente considerando um volume limitado de chamadas de IA inicialmente.
A dependência de um LLM externo, embora vantajosa em termos de custo e latência, introduz desafios em testabilidade, segurança e confiabilidade. As seguintes medidas serão adotadas:
Esta seção fornece exemplos práticos de interação com a API do Gemini 2.0 Flash, ilustrando o formato esperado dos prompts de entrada e as respostas em diversos cenários, incluindo sucesso, falha e degradação.
