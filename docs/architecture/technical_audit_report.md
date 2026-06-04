# Relatório de Auditoria Técnica: EdgeHunter v2.1.4

**Data:** 03 de Junho de 2026
**Autor:** Winston (System Architect)
**Escopo:** Avaliação Crítica da Arquitetura, Pipeline de Dados, Motor EV+ e SPOFs.

---

## 1. Stack Tecnológico e Orquestração

A arquitetura do EdgeHunter é construída sobre um monólito modular em Python, focado em estabilidade e execução local/servidor único.

*   **Linguagem Base:** Python 3.10+ (Tipagem estática e assincronicidade nativa suportada).
*   **Camada Web/API:** FastAPI e Flask. Uvicorn atua como servidor ASGI.
*   **Persistência (Database):** SQLite3 (`edge_hunter.db`) com SQLAlchemy ORM e Alembic (Flask-Migrate) para versionamento de schema. Configurado com PRAGMA WAL (Write-Ahead Logging) para mitigar contenção de concorrência.
*   **Machine Learning / Math:** `numpy`, `pandas`, `scikit-learn`, `xgboost` e `river` (aprendizado online) formam a base do modelo de Poisson.
*   **Automação e Orquestração:**
    *   **Background Jobs:** `APScheduler` para agendamentos internos do Flask.
    *   **Runtime Contínuo:** Um loop infinito de orquestração (`scripts/run_runtime.py`) gerenciado pelo **Systemd** (User Service: `edgehunter.service`). Ele garante auto-restart em caso de crash e gerencia o ciclo `Scraper -> IA -> Telegram`.
*   **Integração IA:** SDKs oficiais (`google-generativeai`) e chamadas REST diretas para o Google Gemini Flash.

---

## 2. Pipeline de Ingestão de Dados (Radar)

A ingestão de dados não é orientada a eventos (streaming/websockets), mas sim baseada em **Polling Cronometrado**.

*   **Estratégia de Requisição:** Polling a cada 300 segundos (5 minutos) ditado pela variável `EDGEHUNTER_RUNTIME_INTERVAL_SECONDS`.
*   **Fontes de Dados:** O sistema utiliza adaptadores diretos (`urllib.request` e `requests`) para APIs REST (API-Football, TheOddsAPI, Pinnacle, Bet365 via scrapers customizados).
*   **Tratamento de Latência:**
    *   Chamadas são bloqueantes e síncronas (executadas proceduralmente no ciclo do `orchestrator.py`).
    *   Um atraso artificial (`time.sleep(config["rate_limit"])`, configurado via `SCRAPER_RATE_LIMIT_SECONDS`) é injetado entre requisições para evitar rate-limiting imediato das fontes gratuitas.
*   **Observabilidade:** Tabela `scraper_health` monitora a "frescura" dos dados (*stale odds*) e falhas consecutivas, atribuindo status de `healthy`, `warning` ou `critical` aos conectores.

---

## 3. Motor de Cálculo (+EV)

O `value_detector.py` centraliza a matemática pura. O sistema não utiliza lógicas complexas de precificação em tempo real (como modelos de order book), mas sim detecção estática contra benchmarks (Poisson ou Pinnacle).

*   **Remoção da Margem (Vig / Overround):**
    A função `calculate_normalized_implied_probabilities` utiliza o método de remoção de margem proporcional padrão da indústria.
    ```text
    1. Calcula a Probabilidade Bruta: raw_prob = 1 / odd (Para Home, Draw, Away)
    2. Calcula o Overround (Vig): margin = sum(raw_probs)
    3. Normaliza (True Prob): norm_prob = raw_prob / margin
    ```
    Isso força a soma das probabilidades reais para exatamente 100% (1.0).

*   **Cálculo do Expected Value (EV):**
    A função `calculate_ev` aplica a fórmula canônica:
    `EV = (true_prob * offered_odds) - 1.0`
    *Onde um resultado > 0 representa um Value Bet.*

*   **Cálculo de Stake (Gestão de Banca):**
    **Ausente/Desativado.** Arquiteturalmente, o sistema opera estritamente em *Paper Trading* (Simulação). As flags de segurança (`actionable=False`, `not_operational_advice=True`) estão forçadas (hardcoded) no orquestrador. Cálculos de *Critério de Kelly* ou fracionamento de bankroll não são executados no loop de produção atual.

---

## 4. Pontos Únicos de Falha (SPOF) & Gargalos Técnicos

Se este sistema for submetido a um teste de estresse contínuo, a quebra ocorrerá nestes quatro pilares:

1.  **SPOF de Camada de Dados (Database Lock):**
    O uso de SQLite, mesmo com WAL ativado, é um gargalo crítico se a frequência de polling diminuir (ex: 10 segundos) simultaneamente com operações pesadas de I/O do modelo de ML e do frontend. Há um teste no repositório (`sqlite_contention_benchmark.py`) que já evidencia preocupações com concorrência (`OperationalError: database is locked`).
2.  **SPOF de Rede (IP Ban / Rate Limit Exaustivo):**
    As requisições de scraper saem do mesmo IP do servidor (sem rotação de proxy explícita configurada no core). Dependência pesada de `time.sleep()`. Qualquer endurecimento das defesas da Bet365 ou expiração das cotas gratuitas das APIs (RapidAPI/OddsAPI) paralisa o fluxo completamente (gerando ciclos silenciados contínuos).
3.  **SPOF Cognitivo (Gargalo da LLM):**
    A inteligência contextual depende 100% do *Google Gemini API*. Conforme evidenciado em logs recentes (Erro 404 / 429), mudanças na API do Google, expiração da *API Key* ou exaustão de tokens derrubam a validação final. A ausência do Gemini transforma o sistema em um modelo matemático burro, sujeito a falsos positivos de contexto (lesões, clima).
4.  **SPOF Arquitetural (Orquestrador Monolítico Bloqueante):**
    O loop `run_one_cycle` é síncrono. Um atraso de rede ao ler o scraper de uma liga atrasa a submissão para a IA, que por sua vez atrasa o alerta no Telegram. Não há desacoplamento via fila de mensagens (RabbitMQ, Celery ou Kafka). Um timeout em um scraper sacrifica a janela de oportunidade de mercado inteira (que frequentemente dura segundos).